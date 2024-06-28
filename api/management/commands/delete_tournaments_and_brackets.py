from django.core.management.base import BaseCommand
from api.models import Tournament, Bracket

class Command(BaseCommand):
    help = 'Delete all tournaments and brackets'

    def handle(self, *args, **kwargs):
        self.stdout.write('Deleting all brackets...')
        Bracket.objects.all().delete()
        self.stdout.write('Deleting all tournaments...')
        Tournament.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully deleted all tournaments and brackets.'))
