from typing import cast
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from django.contrib.auth.models import User

from game.models.birds.player import BirdLeader
from game.models.birds.setup import BirdsSimpleSetup
from game.models.cats.tokens import CatKeep
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Clearing, Faction, Game, Player
from game.transactions.birds_setup import (
    pick_corner as pick_corner_transaction,
    choose_leader_initial as choose_leader_initial_transaction,
    confirm_completed_setup as confirm_completed_setup_transaction,
)
from game.utility.textchoice import get_choice_value_by_label_or_value


@api_view(["PATCH"])
def pick_corner(request: Request, game_id: int, clearing_number: int | None = None):
    """
    If keep is in the game, birds automatically pick opposite corner.
    if keep is not in the game, birds pick a corner.
    If clearing_number is None, that is presumed to be because the keep is placed.
    """
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to pick a corner")
    user = cast(User, request.user)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise NotFound("Game does not exist")
    try:
        player = Player.objects.get(game=game, user=user)
    except Player.DoesNotExist:
        raise NotFound("Player does not exist")

    # check if keep is in the game and what clearing it is
    try:
        cat_player = Player.objects.get(game=game, faction=Faction.CATS)
        keep = CatKeep.objects.get(player=cat_player)
        keep_clearing_number = keep.clearing.clearing_number
        opposite_clearing_number = (keep_clearing_number + 2) % 4
    except (Player.DoesNotExist, CatKeep.DoesNotExist):
        opposite_clearing_number = None
    # check passed clearing number consistent with keep existence/position
    if clearing_number is not None:
        if (
            opposite_clearing_number is not None
            and clearing_number != opposite_clearing_number
        ):
            raise ValidationError("Clearing number does not match opposite corner")
    elif opposite_clearing_number is None:
        raise ValidationError("No clearing number provided")
    else:
        clearing_number = opposite_clearing_number
    try:
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
    except Clearing.DoesNotExist:
        raise NotFound("Clearing does not exist")
    pick_corner_transaction(player, clearing)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def choose_leader_initial(request: Request, game_id: int, leader: str):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to choose a leader")
    user = cast(User, request.user)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise NotFound("Game does not exist")
    try:
        player = Player.objects.get(game=game, user=user)
    except Player.DoesNotExist:
        raise NotFound("Player does not exist")

    # check that it is birds setup
    simple_setup = GameSimpleSetup.objects.get(game=game)
    if simple_setup.status != GameSimpleSetup.GameSetupStatus.BIRDS_SETUP:
        raise ValidationError("Not this player's turn")
    # check that the step is choosing a leader
    birds_setup = BirdsSimpleSetup.objects.get(player=player)
    if birds_setup.step != BirdsSimpleSetup.Steps.CHOOSING_LEADER:
        raise ValidationError(
            f"This has been called at the wrong step: {birds_setup.step}"
        )
    # check leader is valid
    try:
        leader_value = get_choice_value_by_label_or_value(
            BirdLeader.BirdLeaders, leader
        )
    except ValueError:
        raise ValidationError("Leader label not recognized")
    try:
        choose_leader_initial_transaction(player, BirdLeader.BirdLeaders(leader_value))
    except ValueError as e:
        raise ValidationError({"detail": str(e)})

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def confirm_completed_setup(request: Request, game_id: int):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to confirm setup")
    user = cast(User, request.user)
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        raise NotFound("Game does not exist")
    try:
        player = Player.objects.get(game=game, user=user)
    except Player.DoesNotExist:
        raise NotFound("Player does not exist")
    try:
        confirm_completed_setup_transaction(player)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})
    return Response(status=status.HTTP_204_NO_CONTENT)
