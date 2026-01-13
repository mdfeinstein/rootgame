import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rootGame.settings")
django.setup()

from game.models.checkpoint_models import Checkpoint
count, _ = Checkpoint.objects.all().delete()
print(f'Deleted {count} checkpoints.')
