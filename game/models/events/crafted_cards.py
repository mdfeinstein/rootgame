from game.models.game_models import Card
from game.models import Player
from game.models import Clearing
from game.models.events.event import Event, EventType
from django.db import models
from game.models.game_models import CraftedCardEntry

class InformantsEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="informants"
    )
    crafted_card_entry = models.ForeignKey(
        CraftedCardEntry, on_delete=models.CASCADE, related_name="informants_events"
    )
    @property
    def game(self):
        return self.event.game
    @classmethod
    def create(cls, crafted_card_entry: CraftedCardEntry):
        event = Event.objects.create(type=EventType.INFORMANTS, game=crafted_card_entry.player.game)
        return cls.objects.create(event=event, crafted_card_entry=crafted_card_entry)

class EyrieEmigreEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="eyrie_emigre"
    )
    crafted_card_entry = models.ForeignKey(
        CraftedCardEntry, on_delete=models.CASCADE, related_name="eyrie_emigre_events"
    )
    move_completed = models.BooleanField(default=False)
    move_destination = models.ForeignKey(
        Clearing, on_delete=models.CASCADE, related_name="eyrie_emigre_moves",
        default=None, null=True
    )
    battle_initiated = models.BooleanField(default=False)
    @property
    def game(self):
        return self.event.game
    @classmethod
    def create(cls, crafted_card_entry: CraftedCardEntry):
        event = Event.objects.create(type=EventType.EYRIE_EMIGRE, game=crafted_card_entry.player.game)
        return cls.objects.create(event=event, crafted_card_entry=crafted_card_entry)

class SaboteursEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="saboteurs"
    )
    crafted_card_entry = models.ForeignKey(
        CraftedCardEntry, on_delete=models.CASCADE, related_name="saboteurs_events"
    )
    @property
    def game(self):
        return self.event.game
    @classmethod
    def create(cls, crafted_card_entry: CraftedCardEntry):
        event = Event.objects.create(type=EventType.SABOTEURS, game=crafted_card_entry.player.game)
        return cls.objects.create(event=event, crafted_card_entry=crafted_card_entry)

class CharmOffensiveEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="charm_offensive"
    )
    crafted_card_entry = models.ForeignKey(
        CraftedCardEntry, on_delete=models.CASCADE, related_name="charm_offensive_events"
    )
    @property
    def game(self):
        return self.event.game
    @classmethod
    def create(cls, crafted_card_entry: CraftedCardEntry):
        event = Event.objects.create(type=EventType.CHARM_OFFENSIVE, game=crafted_card_entry.player.game)
        return cls.objects.create(event=event, crafted_card_entry=crafted_card_entry)

class PartisansEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="partisans"
    )
    battle = models.ForeignKey(
        "game.Battle", on_delete=models.CASCADE, related_name="partisan_events"
    )
    crafted_card_entry = models.ForeignKey(
        CraftedCardEntry, on_delete=models.CASCADE, related_name="partisan_events"
    )

    @classmethod
    def create(cls, battle, crafted_card_entry: CraftedCardEntry):
        event = Event.objects.create(type=EventType.PARTISANS, game=battle.clearing.game)
        return cls.objects.create(event=event, battle=battle, crafted_card_entry=crafted_card_entry)

class SwapMeetEvent(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="swap_meet"
    )
    taking_player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="swap_meet_take_events"
    )
    taken_from_player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="swap_meet_given_events"
    )
    taken_card = models.ForeignKey(
        Card, on_delete=models.CASCADE, related_name="swap_meet_taken_cards",
        null=True, blank=True
    )
    @property
    def game(self):
        return self.event.game

    @classmethod
    def create(cls, taking_player, taken_from_player):
        event = Event.objects.create(type=EventType.SWAP_MEET, game=taking_player.game)
        return cls.objects.create(
            event=event,
            taking_player=taking_player,
            taken_from_player=taken_from_player
        )