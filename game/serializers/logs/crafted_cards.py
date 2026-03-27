from rest_framework import serializers
from game.models.game_log import GameLog, LogType
from game.models.game_models import Game, Player, Card
from .general import CardSerializer

class CraftedCardActionLogDetailsSerializer(serializers.Serializer):
    card = CardSerializer()
    action_type = serializers.CharField()
    details = serializers.DictField(required=False)
    text = serializers.SerializerMethodField()

    def get_text(self, obj):
        card_name = obj['card']['title']
        action = obj['action_type']
        details = obj.get('details', {})
        
        if card_name == "Eyrie Emigre":
            if action == "move":
                return f"Used {card_name} to move {details.get('count')} warriors from {details.get('origin')} to {details.get('destination')}"
            if action == "battle":
                return f"Used {card_name} to battle {details.get('defender_faction')} in {details.get('clearing')}"
            if action == "failure":
                return f"{card_name} failed (no battle)! Discarded card."
            if action == "skip":
                return f"Skipped {card_name} action."

        if card_name == "False Orders":
            return f"Used {card_name} to move {details.get('count')} of {details.get('faction')}'s warriors from {details.get('origin')} to {details.get('destination')}"

        if card_name == "Swap Meet":
            return f"Used {card_name} to take a card from {details.get('target_faction')}'s hand and give them one back."

        if card_name == "Informants":
            return f"Used {card_name} to take an ambush from the discard pile instead of drawing."

        if card_name == "Murine Brokers":
            return f"{card_name}: Drew an extra card because another player crafted an item."

        if card_name == "Master Engravers":
            return f"{card_name}: Scored 1 extra point for crafting an item."

        if card_name == "Saboteurs":
            return f"Used {card_name} to discard {details.get('target_faction')}'s {details.get('card_name')}."

        if card_name == "Propaganda Bureau":
            return f"Used {card_name} to replace an enemy warrior with a WA warrior in {details.get('clearing')}."

        if card_name == "Charm Offensive":
            return f"Used {card_name} to give a card to {details.get('target_faction')} and score 1 VP."

        if card_name == "League of Adventurers":
            return f"Used {card_name} to score {details.get('points')} VP for items."

        if card_name == "Coffin Makers":
            if action == "score":
                return f"Used {card_name} to score {details.get('points')} VP for {details.get('warrior_count')} warriors."
            if action == "release":
                return f"Released {details.get('warrior_count')} warriors from {card_name} back to supplies."

        return f"Used {card_name} action."

def log_crafted_card_action(game: Game, player: Player, card: Card, action_type: str, details: dict = None, parent: GameLog | None = None) -> GameLog:
    serializer = CraftedCardActionLogDetailsSerializer(data={
        "card": CardSerializer(card).data,
        "action_type": action_type,
        "details": details or {}
    })
    serializer.is_valid(raise_exception=True)
    return GameLog.objects.create(
        game=game, player=player, log_type=LogType.CRAFTED_CARD_ACTION, details=serializer.validated_data, parent=parent
    )


def get_serializer_data(log: GameLog, details: dict, request=None):
    if log.log_type == LogType.CRAFTED_CARD_ACTION:
        return CraftedCardActionLogDetailsSerializer(details).data
    return None
