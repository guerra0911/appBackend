from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import Profile

class Command(BaseCommand):
    help = 'Clean up duplicate profiles'

    def handle(self, *args, **kwargs):
        users_with_multiple_profiles = Profile.objects.values('user').annotate(count=Count('id')).filter(count__gt=1)
        for user_profile in users_with_multiple_profiles:
            user_profiles = Profile.objects.filter(user=user_profile['user'])
            for profile in user_profiles[1:]:  # Keep the first profile, delete the rest
                profile.delete()
        self.stdout.write(self.style.SUCCESS('Successfully cleaned up duplicate profiles'))
