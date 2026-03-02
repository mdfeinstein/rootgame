from typing import Union, cast
from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import Faction, Piece, Player, Suit, Card, Warrior
from game.models.crows.tokens import PlotToken
from game.models.events.crows import CrowRecruitEvent
from game.utility.textchoice import next_choice
from game.models.crows.turn import CrowBirdsong, CrowDaylight, CrowEvening
from game.queries.crows.turn import get_phase, validate_step
from game.queries.crows.crafting import validate_crafting_pieces_satisfy_requirements
from game.queries.general import validate_player_has_card_in_hand
from game.transactions.general import (
    craft_card,
    discard_card_from_hand,
    draw_card_from_deck_to_hand,
    place_piece_from_supply_into_clearing,
    raise_score,
)
from game.transactions.removal import player_removes_warriors, player_removes_token, player_removes_building


from .turn import next_step, step_effect


@transaction.atomic
def crows_craft_card(player: Player, card: CardsEP, plot_tokens: list[PlotToken]):
    """crafts a card with the given face down plot tokens."""
    validate_step(player, CrowBirdsong.CrowBirdsongSteps.CRAFT)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    if not validate_crafting_pieces_satisfy_requirements(player, card, plot_tokens):
        raise ValueError("Not enough plot tokens to craft card")
    craft_card(card_in_hand, cast(list[Piece], plot_tokens))


@transaction.atomic
def resolve_bomb(player: Player, token: PlotToken):
    """resolves a bomb plot token"""
    from game.models.game_models import Building, Token
    clearing = token.clearing
    # remove all enemy pieces
    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            count = Warrior.objects.filter(clearing=clearing, player=player_).count()
            if count > 0:
                player_removes_warriors(clearing, player_, player_, count)
            for enemy_token in Token.objects.filter(clearing=clearing, player=player_):
                player_removes_token(player.game, enemy_token, player)
            for enemy_building in Building.objects.filter(
                building_slot__clearing=clearing, player=player_
            ):
                player_removes_building(player.game, enemy_building, player)
    
    # remove the bomb token itself
    token.clearing = None
    token.save()


@transaction.atomic
def resolve_extortion(player: Player, token: PlotToken):
    """resolves an extortion plot token"""
    from game.models.game_models import HandEntry
    import random
    clearing = token.clearing
    # take a random card from each player with pieces in the clearing
    for player_ in Player.objects.filter(game=player.game):
        if player_ != player:
            has_pieces = False
            if Warrior.objects.filter(clearing=clearing, player=player_).exists():
                has_pieces = True
            elif Piece.objects.filter(clearing=clearing, player=player_).exists():
                has_pieces = True
            
            if has_pieces:
                enemy_hand = list(HandEntry.objects.filter(player=player_))
                if enemy_hand:
                    stolen_card = random.choice(enemy_hand)
                    stolen_card.player = player
                    stolen_card.save()


@transaction.atomic
def flip_plot(player: Player, token: PlotToken):
    """flips a plot token face up"""
    validate_step(player, CrowBirdsong.CrowBirdsongSteps.FLIP)
    if not token.is_facedown:
        raise ValueError("Token is already face up")
    if token.player != player:
        raise ValueError("Cannot flip someone else's token")
    if token.clearing is None:
        raise ValueError("Token is not on the board")

    if not Warrior.objects.filter(clearing=token.clearing, player=player).exists():
        raise ValueError("Must have a Crow warrior present to flip a plot token")

    token.is_facedown = False
    token.save()

    # score one point for each face up plot token
    face_up_count = PlotToken.objects.filter(
        player=player, is_facedown=False, clearing__isnull=False
    ).count()
    raise_score(player, face_up_count)

    if token.plot_type == PlotToken.PlotType.BOMB:
        resolve_bomb(player, token)
    elif token.plot_type == PlotToken.PlotType.EXTORTION:
        resolve_extortion(player, token)


@transaction.atomic
def end_flip_step(player: Player):
    validate_step(player, CrowBirdsong.CrowBirdsongSteps.FLIP)
    next_step(player)


@transaction.atomic
def end_craft_step(player: Player):
    validate_step(player, CrowBirdsong.CrowBirdsongSteps.CRAFT)
    next_step(player)


@transaction.atomic
def crows_recruit(player: Player, card: CardsEP, suit: Suit | None = None):
    """recruits crows from supply into clearings of matching suit"""
    from game.models.game_models import Clearing
    validate_step(player, CrowBirdsong.CrowBirdsongSteps.RECRUIT)
    card_in_hand = validate_player_has_card_in_hand(player, card)
    
    card_suit = Suit(card_in_hand.card.suit)
    if card_suit == Suit.WILD:
        if suit is None:
            raise ValueError("Must provide a suit when recruiting with a bird card")
        target_suit = suit
    else:
        target_suit = card_suit
        
    discard_card_from_hand(player, card_in_hand)

    valid_clearings = list(Clearing.objects.filter(game=player.game, suit=target_suit.value))
    
    # exclude the cat keep clearing
    from game.models.cats.tokens import CatKeep
    try:
        keep = CatKeep.objects.get(player__game=player.game)
        if keep.clearing in valid_clearings:
            valid_clearings.remove(keep.clearing)
    except CatKeep.DoesNotExist:
        pass

    warriors_in_supply = Warrior.objects.filter(player=player, clearing__isnull=True).count()
    if warriors_in_supply < len(valid_clearings):
        # launch event
        from game.models.events.event import Event, EventType
        from game.models.events.crows import CrowRecruitEvent
        event = Event.objects.create(
            game=player.game,
            type=EventType.CROW_RECRUIT
        )
        recruit_event = CrowRecruitEvent.objects.create(
            event=event,
            suit=target_suit.value
        )
        return

    # otherwise, place them if able
    for clearing in valid_clearings:
        warrior = Warrior.objects.filter(player=player, clearing__isnull=True).first()
        if warrior:
            try:
                place_piece_from_supply_into_clearing(warrior, clearing)
            except ValueError:
                pass
            
    next_step(player)

@transaction.atomic
def manual_recruit(player: Player, clearing: Clearing, event: Event):
    """manually recruits a warrior during a CrowRecruitEvent"""
    from game.models.events.crows import CrowRecruitEvent
    from game.models.game_models import Clearing

    validate_step(player, CrowBirdsong.CrowBirdsongSteps.RECRUIT)
    
    if event.originating_player != player:
        raise ValueError("Cannot resolve another player's event")
        
    recruit_event = CrowRecruitEvent.objects.get(event=event)
    
    if clearing.suit != recruit_event.suit:
        raise ValueError("Clearing does not match the recruit suit")
        
    if clearing in recruit_event.recruited_clearings.all():
        raise ValueError("Already recruited in this clearing this turn")
        
    from game.models.cats.tokens import CatKeep
    try:
        keep = CatKeep.objects.get(player__game=player.game)
        if keep.clearing == clearing:
            raise ValueError("Cannot recruit in the keep clearing")
    except CatKeep.DoesNotExist:
        pass

    warrior = Warrior.objects.filter(player=player, clearing__isnull=True).first()
    if not warrior:
        raise ValueError("No warriors left in supply")
        
    place_piece_from_supply_into_clearing(warrior, clearing)
    recruit_event.recruited_clearings.add(clearing)
    
    warriors_left = Warrior.objects.filter(player=player, clearing__isnull=True).count()
    valid_clearings_left = Clearing.objects.filter(game=player.game, suit=recruit_event.suit).exclude(id__in=recruit_event.recruited_clearings.all().values_list('id', flat=True))
    
    try:
        keep = CatKeep.objects.get(player__game=player.game)
        if keep.clearing:
            valid_clearings_left = valid_clearings_left.exclude(id=keep.clearing.id)
    except CatKeep.DoesNotExist:
        pass

    if warriors_left == 0 or not valid_clearings_left.exists():
        event.is_resolved = True
        event.save()
        next_step(player)

@transaction.atomic
def end_recruit_step(player: Player):
    validate_step(player, CrowBirdsong.CrowBirdsongSteps.RECRUIT)
    next_step(player)
