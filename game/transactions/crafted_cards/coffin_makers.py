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
    
    from game.models import CraftedCardEntry
    from game.game_data.cards.exiles_and_partisans import CardsEP
    coffin_card = CraftedCardEntry.objects.filter(player=player, card__card_type=CardsEP.COFFIN_MAKERS.name).first()
    if coffin_card:
        from game.serializers.logs.general import get_active_phase_log
        from game.serializers.logs.crafted_cards import log_crafted_card_action
        log_crafted_card_action(
            game,
            player,
            coffin_card.card,
            "score",
            details={
                "points": points,
                "warrior_count": count
            },
            parent=get_active_phase_log(game)
        )

@transaction.atomic
def release_warriors(game: Game):
    """Returns all warriors in the coffin back to their owners' supply."""
    coffins = CoffinWarrior.objects.filter(player__game=game)
    count = coffins.count()
    for coffin in coffins:
        coffin.coffin_to_warrior()

    from game.models import CraftedCardEntry
    from game.game_data.cards.exiles_and_partisans import CardsEP
    # Coffin Makers belongs to one player in the game
    coffin_entry = CraftedCardEntry.objects.filter(player__game=game, card__card_type=CardsEP.COFFIN_MAKERS.name).first()
    if coffin_entry:
        from game.serializers.logs.general import get_active_phase_log
        from game.serializers.logs.crafted_cards import log_crafted_card_action
        log_crafted_card_action(
            game,
            coffin_entry.player,
            coffin_entry.card,
            "release",
            details={
                "warrior_count": count
            },
            parent=get_active_phase_log(game)
        )
