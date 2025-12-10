from django.urls import path

from game.views.DevLoginView import DevLoginView
from game.views.action_views.battle import BattleActionView
from game.views.action_views.cats.birdsong import CatPlaceWoodView
from game.views.action_views.cats.daylight import CatActionsView, CatCraftStepView
from game.views.action_views.cats.evening import CatsDrawCardsView
from game.views.action_views.setup.birds import (
    BirdsChooseLeaderInitialView,
    BirdsConfirmCompletedSetupView,
    BirdsPickCornerView,
)
from game.views.gamestate_views import (
    get_bird_player_public,
    get_cat_player_public,
    get_clearings,
    get_discard_pile,
    get_player_hand,
    get_wa_player_public,
)

from game.views.gamestate_views.general import get_current_action, get_turn_info
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


urlpatterns = [
    path("api/dev/login/", DevLoginView.as_view()),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/cats/player-info/<int:game_id>/", get_cat_player_public),
    path("api/wa/player-info/<int:game_id>/", get_wa_player_public),
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
    path(  # get steps
        "api/cats/setup/pick-corner/",
        CatsPickCornerView.as_view(),
        name="cats-setup-pick-corner",
    ),
    path(  # step validation and final confirmation
        "api/cats/setup/pick-corner/<int:game_id>/<str:route>/",
        CatsPickCornerView.as_view(),
    ),
    path(
        "api/cats/setup/place-initial-building/",
        CatsPlaceBuildingView.as_view(),
        name="cats-setup-place-initial-building",
    ),
    path(
        "api/cats/setup/place-initial-building/<int:game_id>/<str:route>/",
        CatsPlaceBuildingView.as_view(),
    ),
    path(
        "api/cats/setup/confirm-completed-setup/",
        CatsConfirmCompletedSetupView.as_view(),
        name="cats-setup-confirm-completed-setup",
    ),
    path(
        "api/cats/setup/confirm-completed-setup/<int:game_id>/<str:route>/",
        CatsConfirmCompletedSetupView.as_view(),
    ),
    # birds
    path(  # get steps
        "api/birds/setup/pick-corner/",
        BirdsPickCornerView.as_view(),
        name="birds-setup-pick-corner",
    ),
    path(  # step validation and final confirmation
        "api/birds/setup/pick-corner/<int:game_id>/<str:route>/",
        BirdsPickCornerView.as_view(),
    ),
    path(
        "api/birds/setup/choose-leader/",
        BirdsChooseLeaderInitialView.as_view(),
        name="birds-setup-choose-leader",
    ),
    path(
        "api/birds/setup/choose-leader/<int:game_id>/<str:route>/",
        BirdsChooseLeaderInitialView.as_view(),
    ),
    path(
        "api/birds/setup/confirm-completed-setup/",
        BirdsConfirmCompletedSetupView.as_view(),
        name="birds-setup-confirm-completed-setup",
    ),
    path(
        "api/birds/setup/confirm-completed-setup/<int:game_id>/<str:route>/",
        BirdsConfirmCompletedSetupView.as_view(),
    ),
    # path(
    #     "api/cats/pick-corner/<int:game_id>/<int:clearing_number>/",
    #     cats.pick_corner_view,
    # ),
    # path(
    #     "api/cats/place-initial-building/<int:game_id>/<int:clearing_number>/<str:building_type>/",
    #     cats.place_initial_building_view,
    # ),
    # path(
    #     "api/cats/confirm-completed-setup/<int:game_id>/",
    #     cats.confirm_completed_setup_view,
    # ),
    # path(
    #     "api/birds/pick-corner/<int:game_id>/<int:clearing_number>/",
    #     birds.pick_corner,
    # ),
    # path(
    #     "api/birds/choose-leader-initial/<int:game_id>/<str:leader>/",
    #     birds.choose_leader_initial,
    # ),
    # path(
    #     "api/birds/confirm-completed-setup/<int:game_id>/",
    #     birds.confirm_completed_setup,
    # ),
    path(
        "api/cats/birdsong/place-wood/",
        CatPlaceWoodView.as_view(),
        name="cats-birdsong-place-wood",
    ),
    path(
        "api/cats/birdsong/place-wood/<int:game_id>/<str:route>/",
        CatPlaceWoodView.as_view(),
    ),
    path(
        "api/cats/daylight/craft/",
        CatCraftStepView.as_view(),
        name="cats-daylight-craft",
    ),
    path(
        "api/cats/daylight/craft/<int:game_id>/<str:route>/",
        CatCraftStepView.as_view(),
    ),
    path(
        "api/cats/daylight/actions/",
        CatActionsView.as_view(),
        name="cats-daylight-actions",
    ),
    path(
        "api/cats/daylight/actions/<int:game_id>/<str:route>/",
        CatActionsView.as_view(),
    ),
    path(
        "api/cats/evening/draw-cards/",
        CatsDrawCardsView.as_view(),
        name="cats-evening-draw-cards",
    ),
    path(
        "api/cats/evening/draw-cards/<int:game_id>/<str:route>/",
        CatsDrawCardsView.as_view(),
    ),
    path(
        "api/cats/evening/discard-cards/",
        CatsDrawCardsView.as_view(),
        name="cats-evening-discard-cards",
    ),
    path(
        "api/cats/evening/discard-cards/<int:game_id>/<str:route>/",
        CatsDrawCardsView.as_view(),
    ),
    path(
        "api/battle/",
        BattleActionView.as_view(),
        name="battle",
    ),
    path(
        "api/battle/<int:game_id>/<str:route>/",
        BattleActionView.as_view(),
    ),
]
