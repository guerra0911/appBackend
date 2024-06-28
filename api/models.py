from django.db import models
from django.contrib.auth.models import User
from django.conf import settings 
from django.db.models.signals import post_save
from django.dispatch import receiver
from storages.backends.s3boto3 import S3Boto3Storage
from django.db.models import Count
import logging
from django.contrib.postgres.fields import JSONField

logger = logging.getLogger(__name__)

class Comment(models.Model):
    note = models.ForeignKey('Note', related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Note(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    likes = models.ManyToManyField(User, related_name='liked_notes', default=0)
    dislikes = models.ManyToManyField(User, related_name='disliked_notes', default=0)

    def __str__(self):
        return f"Note by {self.author.username} on {self.created_at}"

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    following = models.ManyToManyField('self', related_name='followers', symmetrical=False, blank=True)
    image = models.ImageField(upload_to='profile_pics', default='profile_pics/default.jpg')

    def update_profile(self, username=None, image=None):
        if username:
            self.user.username = username
            self.user.save()
        if image:
            self.image = image
            self.save()
    
    def calculate_rating(self):
        likes_count = Note.objects.filter(author=self.user).aggregate(total_likes=Count('likes'))['total_likes']
        dislikes_count = Note.objects.filter(author=self.user).aggregate(total_dislikes=Count('dislikes'))['total_dislikes']
        self.rating = (likes_count or 0) - (dislikes_count or 0)
        self.save()

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

def tournament_upload_path(instance, filename):
    return f'tournaments/{instance.id}/{filename}'

def team_upload_path(instance, filename):
    return f'tournaments/{instance.tournament.id}/{filename}'

class Team(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to=team_upload_path)
    tournament = models.ForeignKey('Tournament', related_name='teams', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Bracket(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tournament = models.ForeignKey('Tournament', related_name='brackets', on_delete=models.CASCADE)
    is_actual = models.BooleanField(default=False)
    left_side_round_of_16_teams = models.JSONField(default=list, blank=True)
    left_side_quarter_finals = models.JSONField(default=list, blank=True)
    left_side_semi_finals = models.JSONField(default=list, blank=True)
    finals = models.JSONField(default=list, blank=True)
    right_side_semi_finals = models.JSONField(default=list, blank=True)
    right_side_quarter_finals = models.JSONField(default=list, blank=True)
    right_side_round_of_16_teams = models.JSONField(default=list, blank=True)
    winner = models.ForeignKey(Team, related_name='winner', on_delete=models.SET_NULL, null=True, blank=True)
    score = models.IntegerField(default=0)
    team_size = models.IntegerField(default=16)  # New field to distinguish team sizes

    def __str__(self):
        return f"Bracket by {self.author.username}"


class Tournament(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    banner = models.ImageField(upload_to=tournament_upload_path)
    logo = models.ImageField(upload_to=tournament_upload_path)
    point_system = models.JSONField(default=list)
    correct_score_bonus = models.IntegerField(default=0)
    winner_reward = models.TextField()
    loser_forfeit = models.TextField()
    actual_bracket = models.OneToOneField('Bracket', related_name='actual_bracket', on_delete=models.CASCADE, null=True, blank=True)  # Use string reference
    predicted_brackets = models.ManyToManyField(Bracket, related_name='predicted_brackets', blank=True)
    team_size = models.IntegerField(default=16)
    
    def __str__(self):
        return self.name