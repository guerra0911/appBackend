from django.db import models
from django.contrib.auth.models import User
from django.conf import settings 
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

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
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics')

    def update_profile(self, username=None):
        if username:
            self.user.username = username
            self.user.save()
            logger.debug(f"Username updated to {username} for user {self.user.id}")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        logger.debug(f"Profile created for new user {instance.id}")
    instance.profile.save()
    logger.debug(f"Profile saved for user {instance.id}")

