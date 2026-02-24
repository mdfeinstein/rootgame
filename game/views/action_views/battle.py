from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.battle import Battle
from game.models.events.event import EventType
from game.models.game_models import Faction, Player, Token, Building
from game.queries.current_action.events import get_current_event
from game.serializers.general_serializers import GameActionStepSerializer
from game.transactions.battle import (
    attacker_ambush_choice, 
    defender_ambush_choice,
    defender_chooses_hit,
    attacker_chooses_hit,
    attacker_choose_ambush_hit
)
from game.utility.textchoice import get_choice_label_by_value
from game.views.action_views.general import GameActionView
from rest_framework.exceptions import ValidationError
from rest_framework.views import Response


from game.decorators.transaction_decorator import atomic_game_action

class BattleActionView(GameActionView):
    action_name = "BATTLE"

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

        self.faction = Faction(battle.defender) if battle.step in [
            Battle.BattleSteps.DEFENDER_AMBUSH_CHECK, 
            Battle.BattleSteps.DEFENDER_CHOOSE_HITS
        ] else Faction(battle.attacker)
        
        attacker_faction_label = get_choice_label_by_value(Faction, battle.attacker)
        defender_faction_label = get_choice_label_by_value(Faction, battle.defender)

        match battle.step:
            case Battle.BattleSteps.DEFENDER_AMBUSH_CHECK:
                return self.generate_step(
                    name="ambush-check-defender",
                    prompt="as defender, select ambush card to play, or submit blank to choose not to ambush",
                    endpoint="ambush-check-defender",
                    payload_details=[{"type": "card", "name": "ambush_card"}],
                    options=[{"value": "", "label": "Refuse to ambush"}]
                )

            case Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK:
                return self.generate_step(
                    name="ambush-cancel-check-attacker",
                    prompt="as attacker, select ambush card to cancel ambush, or submit blank to choose not to cancel ambush",
                    endpoint="ambush-check-attacker",
                    payload_details=[{"type": "card", "name": "ambush_card"}],
                    options=[{"value": "", "label": "Refuse to cancel ambush"}]
                )

            case Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS:
                return self._generate_choose_hit_step(
                    player_faction=battle.attacker, 
                    battle=battle, 
                    name="choose-ambush-hit-attacker",
                    endpoint="choose-ambush-hit-attacker",
                    prompt="as attacker, you lost your last warriors to an ambush. Select a token or building to remove."
                )

            case Battle.BattleSteps.DEFENDER_CHOOSE_HITS:
                hits_needed = battle.defender_hits_taken - battle.defender_hits_assigned
                return self._generate_choose_hit_step(
                    player_faction=battle.defender, 
                    battle=battle, 
                    name="choose-hit-defender",
                    endpoint="choose-hit-defender",
                    prompt=f"as defender, select a token or building to remove ({hits_needed} hit(s) remaining)."
                )

            case Battle.BattleSteps.ATTACKER_CHOOSE_HITS:
                hits_needed = battle.attacker_hits_taken - battle.attacker_hits_assigned
                return self._generate_choose_hit_step(
                    player_faction=battle.attacker, 
                    battle=battle, 
                    name="choose-hit-attacker",
                    endpoint="choose-hit-attacker",
                    prompt=f"as attacker, select a token or building to remove ({hits_needed} hit(s) remaining)."
                )

            case Battle.BattleSteps.COMPLETED:
                raise ValidationError("Battle complete, this shouldn't be accessed")
            case _:
                raise ValidationError("Invalid battle step")



    def _generate_choose_hit_step(self, player_faction, battle, name, endpoint, prompt):
        player = Player.objects.get(game=battle.clearing.game, faction=player_faction)
        
        tokens = Token.objects.filter(clearing=battle.clearing, player=player)
        buildings = Building.objects.filter(building_slot__clearing=battle.clearing, player=player)
        
        options = []
        added_piece_names = set()
        
        for token in tokens:
            token_type_str = self._get_piece_name(token)
            if token_type_str not in added_piece_names:
                added_piece_names.add(token_type_str)
                options.append({"value": token_type_str, "label": token_type_str})
                
        for building in buildings:
            building_type_str = self._get_piece_name(building)
            if building_type_str not in added_piece_names:
                added_piece_names.add(building_type_str)
                options.append({"value": building_type_str, "label": building_type_str})

        return self.generate_step(
            name=name,
            prompt=prompt,
            endpoint=endpoint,
            payload_details=[{"type": "piece", "name": "piece", "clearing_number": battle.clearing.clearing_number}],
            options=options
        )

    def route_post(self, request, game_id: int, route: str, *args, **kwargs):
        match route:
            case "ambush-check-defender":
                return self.post_ambush_check_defender(request, game_id)
            case "ambush-check-attacker":
                return self.post_ambush_check_attacker(request, game_id)
            case "choose-ambush-hit-attacker":
                return self.post_choose_ambush_hit_attacker(request, game_id)
            case "choose-hit-defender":
                return self.post_choose_hit_defender(request, game_id)
            case "choose-hit-attacker":
                return self.post_choose_hit_attacker(request, game_id)
            case _:
                raise ValidationError("Invalid route")

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
            atomic_game_action(defender_ambush_choice, undoable=False)(game, battle, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

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
        try:
            atomic_game_action(attacker_ambush_choice, undoable=False)(game, battle, card)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def _process_hit_choice(self, request, game_id, faction_val, hit_func):
        game = self.game(game_id)
        event = get_current_event(game)
        battle = Battle.objects.get(event=event)
        player = Player.objects.get(game=game, faction=faction_val)
        
        piece_type_str = request.data["piece"]
        
        # Find the actual piece based on the string name
        tokens = Token.objects.filter(clearing=battle.clearing, player=player)
        buildings = Building.objects.filter(building_slot__clearing=battle.clearing, player=player)
        
        piece_to_remove = None
        for token in tokens:
            if self._get_piece_name(token) == piece_type_str:
                piece_to_remove = token
                break
                
        if not piece_to_remove:
            for building in buildings:
                if self._get_piece_name(building) == piece_type_str:
                    piece_to_remove = building
                    break
                    
        if not piece_to_remove:
            raise ValidationError(f"Piece of type {piece_type_str} not found in battle clearing")

        try:
            atomic_game_action(hit_func, undoable=False)(game, battle, piece_to_remove)
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return self.generate_completed_step()

    def post_choose_ambush_hit_attacker(self, request, game_id: int):
        event = get_current_event(self.game(game_id))
        battle = Battle.objects.get(event=event)
        return self._process_hit_choice(request, game_id, battle.attacker, attacker_choose_ambush_hit)

    def post_choose_hit_defender(self, request, game_id: int):
        event = get_current_event(self.game(game_id))
        battle = Battle.objects.get(event=event)
        return self._process_hit_choice(request, game_id, battle.defender, defender_chooses_hit)

    def post_choose_hit_attacker(self, request, game_id: int):
        event = get_current_event(self.game(game_id))
        battle = Battle.objects.get(event=event)
        return self._process_hit_choice(request, game_id, battle.attacker, attacker_chooses_hit)

    def validate_timing(self, request, game_id: int, route, *args, **kwargs):
        """raises if not the correct step"""
        game = self.game(game_id)
        battle = Battle.objects.get(event=get_current_event(game))
        mapping = {  # route -> step
            "ambush-check-defender": Battle.BattleSteps.DEFENDER_AMBUSH_CHECK,
            "ambush-check-attacker": Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK,
            "choose-ambush-hit-attacker": Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS,
            "choose-hit-defender": Battle.BattleSteps.DEFENDER_CHOOSE_HITS,
            "choose-hit-attacker": Battle.BattleSteps.ATTACKER_CHOOSE_HITS,
        }
        if battle.step != mapping[route]:
            raise ValidationError("Not the correct step")

    # validate_player is handled natively by GameActionView, since we dynamically set self.faction in get()
    def validate_player(self, request, game_id: int, route: str, *args, **kwargs):
        game = self.game(game_id)
        battle = Battle.objects.get(event=get_current_event(game))
        
        # Dynamically set faction based on route for POST validation
        if route in ["ambush-check-defender", "choose-hit-defender"]:
            self.faction = Faction(battle.defender)
        elif route in ["ambush-check-attacker", "choose-ambush-hit-attacker", "choose-hit-attacker"]:
            self.faction = Faction(battle.attacker)
            
        super().validate_player(request, game_id, route, *args, **kwargs)

    def _get_piece_name(self, piece) -> str:
        from game.models.game_models import Token, Building
        if isinstance(piece, Token):
            if hasattr(piece, "keep"): return "Keep"
            if hasattr(piece, "wood"): return "Wood"
            if hasattr(piece, "sympathy"): return "Sympathy"
            return "Token"
        elif isinstance(piece, Building):
            if hasattr(piece, "sawmill"): return "Sawmill"
            if hasattr(piece, "workshop"): return "Workshop"
            if hasattr(piece, "recruiter"): return "Recruiter"
            if hasattr(piece, "birdroost"): return "BirdRoost"
            if hasattr(piece, "wabasefox"): return "WaBaseFox"
            if hasattr(piece, "wabaserabbit"): return "WaBaseRabbit"
            if hasattr(piece, "wabasemouse"): return "WaBaseMouse"
            return "Building"
        return "Unknown"