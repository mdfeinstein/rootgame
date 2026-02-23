# Faction Views (Endpoints)

Views act as the bridge between the frontend React application and the backend Django game engine. They parse HTTP requests, extract parameters, and call the appropriate Transaction functions.

## Location in Codebase

Action views are located in `game/views/action_views/`. The structure typically mirrors the faction:

- `game/views/action_views/cats/`
- `game/views/action_views/birds/`
- `game/views/action_views/wa/`

## Structure

Each action a faction can perform on its turn needs an endpoint.

1. **API View**: A standard DRF `APIView` (e.g., `CatBuildView`).
2. **Request Validation**: The view must validate the POST payload (e.g., `clearing_id`, `card_id`).
3. **Transaction Invocation**: The view calls the corresponding transaction function in `game/transactions/[faction].py`.
   _Example: `CatBuildView` calls `cat_build(game, clearing)`._
4. **Response**: It returns the serialized, updated `GameState` (or unifies it via WebSocket broadcasting), and an HTTP 200 or 400.

## Integration

To add an endpoint for a new faction action:

1. Create the View class in the faction's `action_views` folder.
2. Register the View in the routing configuration (`game/urls.py` or a dedicated `urls.py` in the module).
3. Ensure the frontend `api` functions are mapped to this URL (e.g., `/api/game/<game_id>/action/faction/specific_move/`).
