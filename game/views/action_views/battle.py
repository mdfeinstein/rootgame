from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.battle import Battle
from game.models.events.event import EventType
from game.models.game_models import Faction, Player
from game.queries.current_action.events import get_current_event
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.battle import attacker_ambush_choice, defender_ambush_choice
from game.utility.textchoice import get_choice_label_by_value
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.views import Response


class BattleActionView(GameActionView):
    action_name = "BATTLE"
    faction = None
    faction_string = None

    def get(self, request):
        # get current battle event
        game_id = int(request.query_params.get("game_id"))
        game = self.game(game_id)
        event = get_current_event(game)
        if event is None:
            raise ValidationError("No events")
        if event.type != EventType.BATTLE:
            raise ValidationError("Not a battle event")
        battle = Battle.objects.get(event=event)

        attacker_faction_label = get_choice_label_by_value(Faction, battle.attacker)
        defender_faction_label = get_choice_label_by_value(Faction, battle.defender)
        match battle.step:
            case Battle.BattleSteps.DEFENDER_AMBUSH_CHECK:
                self.first_step = {
                    "faction": defender_faction_label,
                    "name": "ambush-check-defender",
                    "prompt": "as defender, select ambush card to play, or submit blank to choose not to ambush",
                    "endpoint": "ambush-check-defender",
                    "payload_details": [
                        {"type": "card", "name": "ambush_card"},
                    ],
                }

            case Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK:
                self.first_step = {
                    "faction": attacker_faction_label,
                    "name": "ambush-cancel-check-attacker",
                    "prompt": "as attacker, select ambush card to cancel ambush, or submit blank to choose not to cancel ambush",
                    "endpoint": "ambush-check-attacker",
                    "payload_details": [
                        {"type": "card", "name": "ambush_card"},
                    ],
                }

            case Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS:
                raise ValidationError("Not yet implemented")

            case Battle.BattleSteps.DEFENDER_CHOOSE_HITS:
                raise ValidationError("Not yet implemented")

            case Battle.BattleSteps.ATTACKER_CHOOSE_HITS:
                raise ValidationError("Not yet implemented")

            case Battle.BattleSteps.COMPLETED:
                # battle.event.is_resolved = True
                # battle.event.save()
                raise ValidationError("Battle complete, this shouldn't be accessed")
            case _:
                raise ValidationError("Invalid battle step")

        return super().get(request)

    def route_post(self, request, game_id: int, route: str):
        match route:
            case "ambush-check-defender":
                return self.post_ambush_check_defender(request, game_id)
            case "ambush-check-attacker":
                return self.post_ambush_check_attacker(request, game_id)
            case _:
                return ValidationError("Invalid route")

    def post_ambush_check_defender(self, request, game_id: int):
        card_name = request.data["ambush_card"]
        if card_name == "":
            card = None
        else:
            try:
                card = CardsEP[card_name]
            except KeyError:
                raise ValidationError("Invalid card")

        game = self.game(game_id)
        event = get_current_event(game)
        battle = Battle.objects.get(event=event)
        try:
            defender_ambush_choice(game, battle, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        serializer = GameActionStepSerializer({"name": "completed"})
        return Response(serializer.data)

    def post_ambush_check_attacker(self, request, game_id: int):
        card_name = request.data["ambush_card"]
        if card_name == "":
            card = None
        else:
            try:
                card = CardsEP[card_name]
            except KeyError:
                raise ValidationError("Invalid card")

        game = self.game(game_id)
        event = get_current_event(game)
        battle = Battle.objects.get(event=event)
        attacker_ambush_choice(game, battle, card)
        serializer = GameActionStepSerializer({"name": "completed"})
        return Response(serializer.data)

    def validate_player(self, request, game_id, route, *args, **kwargs):
        game = self.game(game_id)
        event = get_current_event(game)
        battle = Battle.objects.get(event=event)
        defender_faction = Faction(battle.defender)
        attacker_faction = Faction(battle.attacker)

        def validate(faction: Faction):
            valid_player = Player.objects.get(game=game, faction=faction)
            if valid_player != self.player(request, game_id):
                raise ValidationError("Not this player's turn")

        if route == "ambush-check-defender":
            validate(defender_faction)
        elif route == "ambush-check-attacker":
            validate(attacker_faction)
        else:
            raise ValidationError("Not yet implemented")

    def validate_timing(self, request, game_id: int, route, *args, **kwargs):
        """raises if not the correct step"""
        game = self.game(game_id)
        player = self.player(request, game_id)
        battle = Battle.objects.get(event=get_current_event(game))
        mapping = {  # route -> step
            "ambush-check-defender": Battle.BattleSteps.DEFENDER_AMBUSH_CHECK,
            "ambush-check-attacker": Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK,
        }
        if battle.step != mapping[route]:
            raise ValidationError("Not the correct step")
