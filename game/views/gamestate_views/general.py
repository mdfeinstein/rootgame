from django.urls import reverse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from game.models.birds.setup import BirdsSimpleSetup
from game.models.cats.setup import CatsSimpleSetup
from game.models.cats.turn import CatBirdsong, CatDaylight, CatTurn
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import (
    Clearing,
    DiscardPileEntry,
    Faction,
    Game,
    HandEntry,
    Player,
)
from game.queries.cats.turn import get_phase as get_cat_phase
from game.queries.general import get_current_player
from game.serializers.general_serializers import (
    CardSerializer,
    ClearingSerializer,
    GameStatusSerializer,
)


@api_view(["GET"])
def get_discard_pile(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    # add auth: valid player or spectator
    discarded_cards = DiscardPileEntry.objects.filter(game=game)
    serializer = CardSerializer([card.card for card in discarded_cards], many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_player_hand(request, player_id: int):
    # TODO: add auth: valid player or spectator
    # grab player
    try:
        player = Player.objects.get(pk=player_id)
    except Player.DoesNotExist:
        return Response(
            {"message": "Player does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    hand_cards = HandEntry.objects.filter(player=player)
    serializer = CardSerializer([card.card for card in hand_cards], many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_clearings(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return Response(
            {"message": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    clearings = Clearing.objects.filter(game=game)
    serializer = ClearingSerializer(clearings, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_turn_info(request, game_id: int):
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise ValidationError("Game does not exist")
    serializer = GameStatusSerializer.from_game(game)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_current_action(request, game_id: int):
    """provides the route for the current action"""
    # grab game
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise ValidationError("Game does not exist")
    player = Player.objects.get(game=game, user=request.user)
    setup = GameSimpleSetup.objects.get(game=game)
    if setup.status == GameSimpleSetup.GameSetupStatus.CATS_SETUP:
        cat_player = Player.objects.get(game=game, faction=Faction.CATS)
        cats_setup = CatsSimpleSetup.objects.get(player=cat_player)
        if cats_setup.step == CatsSimpleSetup.Steps.PICKING_CORNER:
            return Response({"route": reverse("cats-setup-pick-corner")})
        elif cats_setup.step == CatsSimpleSetup.Steps.PLACING_BUILDINGS:
            return Response({"route": reverse("cats-setup-place-initial-building")})
        elif cats_setup.step == CatsSimpleSetup.Steps.PENDING_CONFIRMATION:
            return Response({"route": reverse("cats-setup-confirm-completed-setup")})
        else:
            raise ValidationError("Invalid cats setup step")
    elif setup.status == GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
        bird_player = Player.objects.get(game=game, faction=Faction.BIRDS)
        birds_setup = BirdsSimpleSetup.objects.get(player=bird_player)
        if birds_setup.step == BirdsSimpleSetup.Steps.PICKING_CORNER:
            return Response({"route": reverse("birds-setup-pick-corner")})
        elif birds_setup.step == BirdsSimpleSetup.Steps.CHOOSING_LEADER:
            return Response({"route": reverse("birds-setup-choose-leader")})
        elif birds_setup.step == BirdsSimpleSetup.Steps.PENDING_CONFIRMATION:
            return Response({"route": reverse("birds-setup-confirm-completed-setup")})
        else:
            raise ValidationError("Invalid birds setup step")

    elif setup.status == GameSimpleSetup.GameSetupStatus.ALL_SETUP_COMPLETED:
        # figure out whose turn it is
        player = get_current_player(game)

        if player.faction == Faction.CATS:
            phase = get_cat_phase(player)
            if type(phase) == CatBirdsong:
                if phase.step == CatBirdsong.CatBirdsongSteps.PLACING_WOOD:
                    return Response({"route": reverse("cats-birdsong-place-wood")})
                else:
                    raise ValidationError("Not yet implemented")
            elif type(phase) == CatDaylight:
                if phase.step == CatDaylight.CatDaylightSteps.CRAFTING:
                    return Response({"route": reverse("cats-daylight-craft")})
                elif phase.step == CatDaylight.CatDaylightSteps.ACTIONS:
                    return Response({"route": reverse("cats-daylight-actions")})
                else:
                    raise ValidationError("Not yet implemented")
            else:
                raise ValidationError("Not yet implemented")

    else:
        raise ValidationError("Not yet implemented")
