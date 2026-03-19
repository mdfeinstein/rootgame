from rest_framework import serializers

from game.models.game_models import Faction
from game.serializers.general_serializers import CardSerializer, LabeledChoiceField

class RevealedCardSerializer(serializers.Serializer):
    """
    Serializer to represent a card revealed through Outrage or Exposure.
    """
    card = CardSerializer()
    faction = LabeledChoiceField(choices=Faction.choices)
    event_type = serializers.CharField()
    turns_ago = serializers.IntegerField()
