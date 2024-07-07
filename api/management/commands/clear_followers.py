from django.core.management.base import BaseCommand
from api.models import Profile

class Command(BaseCommand):
    help = 'Clear all followers, following, requests, and requesting relationships'

    def handle(self, *args, **kwargs):
        profiles = Profile.objects.all()
        for profile in profiles:
            profile.followers.clear()
            profile.following.clear()
            profile.requests.clear()
            profile.requesting.clear()
            profile.save()
        self.stdout.write(self.style.SUCCESS('Successfully cleared all relationships'))