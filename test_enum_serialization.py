import django
import os
import sys

# Setup Django environment
sys.path.append('f:/rootGame')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rootGame.settings')
django.setup()

from game.models.birds.player import DecreeEntry
from game.serializers.action_serializer import ActionSerializer
from enum import Enum

def test_serialization():
    print("Testing Django TextChoices Serialization...")
    
    # 1. Get an enum member
    val = DecreeEntry.Column.RECRUIT
    print(f"Original Value: {val} (Type: {type(val)})")
    
    # 2. Serialize
    serialized = ActionSerializer.serialize_arg(val)
    print(f"Serialized: {serialized}")
    
    # 3. Deserialize
    deserialized = ActionSerializer.deserialize_arg(serialized)
    print(f"Deserialized: {deserialized} (Type: {type(deserialized)})")
    
    if deserialized == val:
        print("SUCCESS: Round trip valid.")
    else:
        print("FAILURE: Round trip invalid.")

try:
    test_serialization()
except Exception as e:
    print(e)
