from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Profile

User = get_user_model()

class Command(BaseCommand):
    help = "Delete users and profiles with IDs from 10 and up"

    def handle(self, *args, **kwargs):
        # Delete profiles with IDs from 10 and up
        profiles_deleted, _ = Profile.objects.filter(id__gte=10).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {profiles_deleted} profiles with IDs from 10 and up"))

        # Delete users with IDs from 10 and up
        users_deleted, _ = User.objects.filter(id__gte=10).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {users_deleted} users with IDs from 10 and up"))

        self.stdout.write(self.style.SUCCESS("Cleanup complete"))
