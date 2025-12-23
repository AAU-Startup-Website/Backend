from django.core.management.base import BaseCommand
from startups.models import Phase

class Command(BaseCommand):
    help = 'Seeds the database with initial Phase data'

    def handle(self, *args, **options):
        phases_data = [
            {'name': 'Ideation', 'order': 1},
            {'name': 'Validation', 'order': 2},
            {'name': 'MVP', 'order': 3},
            {'name': 'Growth', 'order': 4},
            {'name': 'Maturity', 'order': 5},
        ]

        for data in phases_data:
            phase, created = Phase.objects.get_or_create(
                name=data['name'],
                defaults={'order': data['order']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created phase: {phase.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Phase already exists: {phase.name}'))

        self.stdout.write(self.style.SUCCESS('Phase seeding completed!'))
