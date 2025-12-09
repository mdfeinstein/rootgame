from django.urls import reverse
from game.models.events.battle import Battle
from game.models.events.event import Event, EventType
from game.models.game_models import Game


def get_current_event_action(game: Game) -> str | None:
    """returns the current event action for the game, or None if no event"""
    event = get_current_event(game)
    if event is None:
        return None
    match event.type:
        case EventType.BATTLE:
            return reverse("battle")
        case EventType.FIELD_HOSPITAL:
            return get_field_hospital_action(game, event)
        case _:
            raise ValueError("Invalid event type")


def get_current_event(game: Game) -> Event | None:
    """returns the current event for the game"""
    # get oldest event
    event = (
        Event.objects.filter(game=game, is_resolved=False)
        .order_by("created_at")
        .first()
    )
    return event


# def get_battle_action(game: Game, event: Event) -> str | None:
#     """returns the current battle action for the game, or None if battle completed"""
#     # get the battle
#     battle = Battle.objects.get(event=event)
#     match battle.step:
#         case Battle.BattleSteps.DEFENDER_AMBUSH_CHECK:
#             return reverse("battle-defender-ambush-check")
#         case Battle.BattleSteps.ATTACKER_AMBUSH_CANCEL_CHECK:
#             return reverse("battle-attacker-ambush-cancel-check")
#         case Battle.BattleSteps.ATTACKER_CHOOSE_AMBUSH_HITS:
#             return reverse("battle-attacker-choose-ambush-hits")
#         # roll dice shouldn't be a step that player chooses
#         # case Battle.BattleSteps.ROLL_DICE:
#         #     return reverse("battle-roll-dice")
#         case Battle.BattleSteps.DEFENDER_CHOOSE_HITS:
#             return reverse("battle-defender-choose-hits")
#         case Battle.BattleSteps.ATTACKER_CHOOSE_HITS:
#             return reverse("battle-attacker-choose-hits")
#         case Battle.BattleSteps.COMPLETED:
#             return None
#         case _:
#             raise ValueError("Invalid battle step")


def get_field_hospital_action(game: Game, event: Event) -> str | None:
    """returns the current field hospital action for the game, or None if field hospital completed"""
    raise ValueError("Not yet implemented")
