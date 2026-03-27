from game.models.game_models import Player, Faction
from game.models.crows.tokens import PlotToken
from game.models.birds.turn import BirdEvening
from game.models.cats.turn import CatEvening
from game.models.wa.turn import WAEvening
from game.queries.general import player_has_pieces_in_clearing, get_current_phase


def can_attempt_exposure(player: Player) -> bool:
    """
    Returns True if:
    - It is the player's turn
    - The player is not Faction.CROWS
    - They haven't drawn in evening yet
    - At least one facedown plot token exists on the board in a clearing where they have pieces
    """
    if player.faction == Faction.CROWS:
        return False

    game = player.game
    if game.current_turn != player.turn_order:
        return False

    phase = get_current_phase(player)

    if isinstance(phase, BirdEvening):
        if phase.step in [
            BirdEvening.BirdEveningSteps.DISCARDING,
            BirdEvening.BirdEveningSteps.COMPLETED,
        ]:
            return False
    elif isinstance(phase, CatEvening):
        if phase.step in [
            CatEvening.CatEveningSteps.DISCARDING,
            CatEvening.CatEveningSteps.COMPLETED,
        ]:
            return False
    elif isinstance(phase, WAEvening):
        if phase.step in [
            WAEvening.WAEveningSteps.DISCARDING,
            WAEvening.WAEveningSteps.COMPLETED,
        ]:
            return False

    crows_player = Player.objects.filter(game=game, faction=Faction.CROWS).first()
    if not crows_player:
        return False

    facedown_plots = PlotToken.objects.filter(
        player=crows_player, is_facedown=True, clearing__isnull=False
    )
    for plot in facedown_plots:
        if player_has_pieces_in_clearing(player, plot.clearing):
            return True

    return False
