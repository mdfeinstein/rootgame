from game.models.game_models import CraftedCardEntry, Game, Player
from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.game_models import CoffinWarrior

def get_coffin_makers_player(game: Game) -> Player | None:
    """Returns the player who has Coffin Makers crafted, or None if it's not crafted."""
    entry = CraftedCardEntry.objects.filter(
        player__game=game, 
        card__card_type=CardsEP.COFFIN_MAKERS.name
    ).first()
    return entry.player if entry else None

def get_coffin_warriors_count(game: Game) -> int:
    """Returns the total number of warriors in the coffin for the game."""
    return CoffinWarrior.objects.filter(player__game=game).count()
