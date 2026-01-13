from rest_framework import serializers
from game.models.events.event import Event, EventType
from game.models.events.battle import Battle
from game.models.events.wa import OutrageEvent
from game.models.events.birds import TurmoilEvent
from game.models.events.cats import FieldHospitalEvent

class BattleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Battle
        fields = [
            "attacker", "defender", "clearing", "step",
            "defender_ambush", "attacker_cancel_ambush",
            "attacker_ambush_hits_taken", "attacker_ambush_hits_assigned",
            "defender_hits_taken", "defender_hits_assigned",
            "attacker_hits_taken", "attacker_hits_assigned"
        ]

class OutrageEventSerializer(serializers.ModelSerializer):
    suit = serializers.CharField()
    outraged_player_id = serializers.IntegerField(source='outraged_player.id')
    outrageous_player_id = serializers.IntegerField(source='outrageous_player.id')
    
    class Meta:
        model = OutrageEvent
        fields = [
            "outraged_player_id", "outrageous_player_id", "suit", 
            "card_given", "hand_shown", "hand"
        ]

class TurmoilEventSerializer(serializers.ModelSerializer):
    player_id = serializers.IntegerField(source='player.id')
    class Meta:
        model = TurmoilEvent
        fields = ["new_leader_chosen", "player_id"]

class FieldHospitalEventSerializer(serializers.ModelSerializer):
    player_id = serializers.IntegerField(source='player.id')
    clearing_id = serializers.IntegerField(source='clearing.id', allow_null=True)
    
    class Meta:
        model = FieldHospitalEvent
        fields = ["player_id", "clearing_id", "warriors_lost"]


class EventSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["id", "type", "is_resolved", "details"]

    def get_details(self, event):
        if event.type == EventType.BATTLE:
             try:
                 return BattleSerializer(event.battle).data
             except Battle.DoesNotExist:
                 return None
        elif event.type == EventType.OUTRAGE:
             try:
                 return OutrageEventSerializer(event.outrage).data
             except OutrageEvent.DoesNotExist:
                 return None
        elif event.type == EventType.TURMOIL:
             try:
                 return TurmoilEventSerializer(event.turmoil).data
             except TurmoilEvent.DoesNotExist:
                 return None
        elif event.type == EventType.FIELD_HOSPITAL:
             try:
                 return FieldHospitalEventSerializer(event.field_hospital).data
             except FieldHospitalEvent.DoesNotExist:
                 return None
        return None
