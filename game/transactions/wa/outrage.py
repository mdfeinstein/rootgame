from django.db import transaction

from game.game_data.cards.exiles_and_partisans import CardsEP
from game.models.events.wa import OutrageEvent
from game.models.events.event import Event
from game.models.game_models import Player
from game.queries.wa.outrage import validate_card_can_pay_outrage
from game.transactions.wa.supporters import add_supporter


@transaction.atomic
def pay_outrage(outrage_event: OutrageEvent, card: CardsEP):
    """player pays card to Woodland Alliance player
    -- transfers card from hand to supporter stack
    -- resolves event
    """
    outrageous_player: Player = outrage_event.outrageous_player
    outraged_player: Player = outrage_event.outraged_player
    card_in_hand = validate_card_can_pay_outrage(outrage_event, card)
    card = card_in_hand.card

    add_supporter(outraged_player, card)
    card_in_hand.delete()

    event: Event = outrage_event.event
    event.is_resolved = True
    event.save()
    outrage_event.card_given = True

    from game.models.game_log import GameLog

    log = GameLog.objects.filter(outrage_event=outrage_event).first()
    if log:
        from game.serializers.logs.wa import WAOutrageLogDetailsSerializer
        from game.serializers.general_serializers import CardSerializer

        details = dict(log.details)
        details["card_given"] = True
        details["card"] = CardSerializer(card).data
        log.details = details
        log.save()

    outrage_event.save()
