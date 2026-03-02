from django.core.management.base import BaseCommand
from game.models.events.setup import GameSimpleSetup

class Command(BaseCommand):
    help = 'Migrates existing GameSimpleSetup status values from old codes to new abbreviated codes.'

    def handle(self, *args, **options):
        # Mapping from old status codes to new ones
        mapping = {
            "0": "INIT",
            "a": "CAT",
            "b": "BIRD",
            "c": "WA",
            "2": "COMP",
        }

        self.stdout.write("Starting migration of GameSimpleSetup status values...")
        
        updated_count = 0
        skipped_count = 0
        
        # We need to use update() for efficiency, or loop if we need to check values
        for old_code, new_code in mapping.items():
            count = GameSimpleSetup.objects.filter(status=old_code).update(status=new_code)
            updated_count += count
            if count > 0:
                self.stdout.write(self.style.SUCCESS(f'Updated {count} entries from "{old_code}" to "{new_code}"'))

        # Also check for any values that are already correct or unknown
        all_entries = GameSimpleSetup.objects.all().count()
        self.stdout.write(f"Migration complete. Total updated: {updated_count}. Total entries in DB: {all_entries}")
