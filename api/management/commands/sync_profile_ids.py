from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from api.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Ensure profile IDs match their corresponding user IDs and remove orphaned profiles'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # Remove orphaned profiles first
            orphaned_profiles = Profile.objects.exclude(user__in=User.objects.all())
            orphaned_count = orphaned_profiles.count()
            orphaned_profiles.delete()
            self.stdout.write(self.style.SUCCESS(f"Removed {orphaned_count} orphaned profiles"))

            # Update profiles to have IDs matching their user IDs
            for user in User.objects.all():
                profile, created = Profile.objects.get_or_create(user=user)
                if profile.id != user.id:
                    self.stdout.write(self.style.WARNING(f"Updating profile id for user {user.id}. Old profile id: {profile.id}"))

                    # Create a new profile with the correct id if it does not exist
                    Profile.objects.filter(id=user.id).delete()
                    profile.delete()

                    new_profile = Profile(
                        id=user.id,
                        user=user,
                        bio=profile.bio,
                        location=profile.location,
                        birthday=profile.birthday,
                        spotify_url=profile.spotify_url,
                        imdb_url=profile.imdb_url,
                        website_url=profile.website_url,
                        privacy_flag=profile.privacy_flag,
                        notification_flag=profile.notification_flag,
                        rating=profile.rating,
                        image=profile.image,
                    )
                    new_profile.save()

                    self.stdout.write(self.style.SUCCESS(f"Profile id updated for user {user.id}"))

            self.stdout.write(self.style.SUCCESS("All profile IDs have been synced with their user IDs"))
