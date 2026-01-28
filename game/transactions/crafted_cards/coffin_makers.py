from django.db import transaction
from game.models.game_models import Player, Game, CoffinWarrior
from game.queries.crafted_cards import get_coffin_warriors_count

@transaction.atomic
def score_coffins(player: Player):
    """Scores 1 VP per 5 warriors in the coffin (round down)."""
    game = player.game
    count = get_coffin_warriors_count(game)
    points = count // 5
    if points > 0:
        player.score += points
        player.save()

@transaction.atomic
def release_warriors(game: Game):
    """Returns all warriors in the coffin back to their owners' supply."""
    coffins = CoffinWarrior.objects.filter(player__game=game)
    for coffin in coffins:
        coffin.coffin_to_warrior()
