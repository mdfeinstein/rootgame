from django.db import models
from game.models.game_models import Token


class Tunnel(Token):
    """
    A Moles-specific token representing a tunnel.
    Tunnels connect parts of the Moles' network and can be placed on the map.
    """
    pass
