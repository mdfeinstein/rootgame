from game.views.gamestate_views.wa import get_wa_player_private
from django.urls import URLPattern, path

from game.views.DevLoginView import DevLoginView
from game.views.action_views.battle import BattleActionView
from game.views.action_views.birds.birdsong import AddToDecreeView, EmergencyDrawingView
from game.views.action_views.birds.daylight import (
    BirdBattleView,
    BirdBuildingView,
    BirdCraftingView,
    BirdMoveView,
    BirdRecruitView,
)
from game.views.action_views.birds.turmoil import TurmoilView
from game.views.action_views.cats.birdsong import CatPlaceWoodView
from game.views.action_views.cats.daylight import CatActionsView, CatCraftStepView
from game.views.action_views.cats.evening import CatsDrawCardsView
from game.views.action_views.cats.field_hospital import FieldHospitalView
from game.views.action_views.setup.birds import (
    BirdsChooseLeaderInitialView,
    BirdsConfirmCompletedSetupView,
    BirdsPickCornerView,
)
from game.views.action_views.wa.birdsong import RevoltView, SpreadSympathyView
from game.views.action_views.wa.daylight import WADaylightActionsView
from game.views.action_views.wa.evening import WAOperationsView
from game.views.action_views.wa.outrage import OutrageView
from game.views.gamestate_views import (
    get_bird_player_public,
    get_cat_player_public,
    get_clearings,
    get_discard_pile,
    get_player_hand,
    get_wa_player_public,
)

from game.views.gamestate_views.general import (
    get_current_action,
    get_players,
    get_turn_info,
    undo_last_action_view,
)
from game.views.gamestate_views.cards import GetCraftedCardsView
from game.views.setup_views import (
    create_game,
    join_game,
    pick_faction,
    start_game_view,
    cats,
    birds,
)
from game.views.action_views.setup.cats import (
    CatsConfirmCompletedSetupView,
    CatsPickCornerView,
    CatsPlaceBuildingView,
)

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.views import APIView

from game.views.user_info import get_player_info, get_user_info


def register_action(
    name: str, view: type[APIView], url: str, urlpatterns: list[URLPattern]
):
    get_path = path(url, view.as_view(), name=name)
    post_path = path(url + "<int:game_id>/<str:route>/", view.as_view(), name=name)
    urlpatterns.append(get_path)
    urlpatterns.append(post_path)


urlpatterns = [
    path("api/dev/login/", DevLoginView.as_view()),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/user/", get_user_info, name="user"),
    path("api/player/<int:game_id>/", get_player_info, name="player"),
    path("api/players/<int:game_id>/", get_players, name="players"),
    path("api/cats/player-info/<int:game_id>/", get_cat_player_public),
    path("api/wa/player-info/<int:game_id>/", get_wa_player_public),
    path("api/wa/player-private-info/<int:game_id>/", get_wa_player_private),
    path("api/birds/player-info/<int:game_id>/", get_bird_player_public),
    path("api/clearings/<int:game_id>/", get_clearings),
    path("api/discard-pile/<int:game_id>/", get_discard_pile),
    path("api/player-hand/", get_player_hand),
    path("api/turn-info/<int:game_id>/", get_turn_info),
    # setup views
    path("api/game/create/", create_game),
    path("api/game/join/<int:game_id>/", join_game),
    path("api/game/pick-faction/<int:game_id>/", pick_faction),
    path("api/game/start/<int:game_id>/", start_game_view),
    path(
        "api/game/current-action/<int:game_id>/",
        get_current_action,
        name="get-current-action",
    ),
    path("api/game/undo/<int:game_id>/", undo_last_action_view, name="undo-action"),
    path("api/crafted-cards/<int:game_id>/<str:faction>/", GetCraftedCardsView.as_view(), name="get-crafted-cards"),
]
register_action(
    "cats-setup-pick-corner",
    CatsPickCornerView,
    "api/cats/setup/pick-corner/",
    urlpatterns,
)
register_action(
    "cats-setup-place-initial-building",
    CatsPlaceBuildingView,
    "api/cats/setup/place-initial-building/",
    urlpatterns,
)
register_action(
    "cats-setup-confirm-completed-setup",
    CatsConfirmCompletedSetupView,
    "api/cats/setup/confirm-completed-setup/",
    urlpatterns,
)
# birds
register_action(
    "birds-setup-pick-corner",
    BirdsPickCornerView,
    "api/birds/setup/pick-corner/",
    urlpatterns,
)

register_action(
    "birds-setup-choose-leader",
    BirdsChooseLeaderInitialView,
    "api/birds/setup/choose-leader/",
    urlpatterns,
)
register_action(
    "birds-setup-confirm-completed-setup",
    BirdsConfirmCompletedSetupView,
    "api/birds/setup/confirm-completed-setup/",
    urlpatterns,
)
register_action(
    "cats-birdsong-place-wood",
    CatPlaceWoodView,
    "api/cats/birdsong/place-wood/",
    urlpatterns,
)
register_action(
    "cats-daylight-craft",
    CatCraftStepView,
    "api/cats/daylight/craft/",
    urlpatterns,
)

register_action(
    "cats-daylight-actions",
    CatActionsView,
    "api/cats/daylight/actions/",
    urlpatterns,
)
register_action(
    "cats-evening-draw-cards",
    CatsDrawCardsView,
    "api/cats/evening/draw-cards/",
    urlpatterns,
)
register_action(
    "cats-evening-discard-cards",
    CatsDrawCardsView,
    "api/cats/evening/discard-cards/",
    urlpatterns,
)

register_action(
    "birds-emergency-draw",
    EmergencyDrawingView,
    "api/birds/birdsong/emergency-draw/",
    urlpatterns,
)
register_action(
    "birds-add-to-decree",
    AddToDecreeView,
    "api/birds/birdsong/add-to-decree/",
    urlpatterns,
)
register_action(
    "birds-craft",
    BirdCraftingView,
    "api/birds/daylight/craft/",
    urlpatterns,
)
register_action(
    "birds-recruit",
    BirdRecruitView,
    "api/birds/daylight/recruit/",
    urlpatterns,
)
register_action(
    "birds-move",
    BirdMoveView,
    "api/birds/daylight/move/",
    urlpatterns,
)
register_action(
    "birds-battle",
    BirdBattleView,
    "api/birds/daylight/battle/",
    urlpatterns,
)
register_action(
    "birds-build",
    BirdBuildingView,
    "api/birds/daylight/building/",
    urlpatterns,
)
register_action("wa-revolt", RevoltView, "api/wa/birdsong/revolt/", urlpatterns)
register_action(
    "wa-spread-sympathy",
    SpreadSympathyView,
    "api/wa/birdsong/spread-sympathy/",
    urlpatterns,
)
register_action(
    "wa-daylight", WADaylightActionsView, "api/wa/daylight/actions/", urlpatterns
)
register_action(
    "wa-operations", WAOperationsView, "api/wa/evening/operations/", urlpatterns
)
register_action(
    "battle",
    BattleActionView,
    "api/battle/",
    urlpatterns,
)
register_action(
    "outrage",
    OutrageView,
    "api/outrage/",
    urlpatterns,
)
register_action(
    "field-hospital",
    FieldHospitalView,
    "api/cats/field-hospital/",
    urlpatterns,
)
register_action(
    "turmoil",
    TurmoilView,
    "api/birds/turmoil/",
    urlpatterns,
)

from game.views.action_views.crafted_cards.propaganda_bureau import PropagandaBureauView
from game.views.action_views.crafted_cards.saboteurs import SaboteursView
from game.views.action_views.crafted_cards.charm_offensive import CharmOffensiveView
from game.views.action_views.crafted_cards.league_of_adventurers import LeagueOfAdventurersView
from game.views.action_views.crafted_cards.informants import InformantsView
from game.views.action_views.crafted_cards.eyrie_emigre import EyrieEmigreView

register_action(
    "propaganda-bureau",
    PropagandaBureauView,
    "api/action/card/propaganda-bureau/",
    urlpatterns,
)
register_action(
    "saboteurs",
    SaboteursView,
    "api/action/card/saboteurs/",
    urlpatterns,
)
register_action(
    "charm-offensive",
    CharmOffensiveView,
    "api/action/card/charm-offensive/",
    urlpatterns,
)
register_action(
    "league-of-adventurers",
    LeagueOfAdventurersView,
    "api/action/card/league-of-adventurers/",
    urlpatterns,
)
register_action(
    "informants",
    InformantsView,
    "api/action/card/informants/",
    urlpatterns,
)
register_action(
    "eyrie-emigre",
    EyrieEmigreView,
    "api/action/card/eyrie-emigre/",
    urlpatterns,
)

