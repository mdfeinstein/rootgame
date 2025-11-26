from typing import cast
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from django.contrib.auth.models import User

from game.models.cats.buildings import CatBuildingTypes
from game.models.cats.setup import CatsSimpleSetup
from game.models.events.setup import GameSimpleSetup
from game.models.game_models import Clearing, Faction, Game, Player
from game.transactions.cats_setup import (
    pick_corner,
    place_garrison,
    place_initial_building,
    confirm_completed_setup,
)


@api_view(["PATCH"])
def pick_corner_view(request: Request, game_id: int, clearing_number: int):
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
    if player.faction != Faction.CATS:
        raise PermissionDenied("User is not a cats player")

    # check clearing is correct and ifnd opposite corner. for now, assume all maps follow same convention
    corner_pair1 = (1, 3)
    corner_pair2 = (2, 4)
    if clearing_number not in [*corner_pair1, *corner_pair2]:
        raise ValidationError("Clearing is not a corner")
    opposite_corner_number = (clearing_number + 2) % 4
    try:
        pick_corner(player, Clearing.objects.get(clearing_number=clearing_number))
    except ValueError as e:
        raise ValidationError({"detail": str(e)})
    try:
        place_garrison(
            player, Clearing.objects.get(clearing_number=opposite_corner_number)
        )
    except ValueError as e:
        raise ValidationError({"detail": str(e)})
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def place_initial_building_view(
    request: Request, game_id: int, clearing_number: int, building_type: str
):
    if request.user.is_anonymous:
        raise PermissionDenied("User must be logged in to place a building")
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
        clearing = Clearing.objects.get(game=game, clearing_number=clearing_number)
    except Clearing.DoesNotExist:
        raise NotFound("Clearing does not exist")

    building_type_name = None
    for b in CatBuildingTypes:
        if b.value == building_type:
            building_type_name = b
    if building_type_name is None:
        raise ValidationError("Invalid building type: " + building_type)
    try:
        place_initial_building(player, clearing, building_type_name)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def confirm_completed_setup_view(request: Request, game_id: int):
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
        confirm_completed_setup(player)
    except ValueError as e:
        raise ValidationError({"detail": str(e)})

    return Response(status=status.HTTP_204_NO_CONTENT)
