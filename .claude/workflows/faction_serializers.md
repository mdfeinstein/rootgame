---
description: Workflow for faction serializers
---

# Faction Serializers Workflow

Serializers translate the faction's Django models into JSON format so the frontend can read the game state. They also validate incoming API data.

1. **Create the Serializer File**: In `game/serializers/`, create a new file named `[faction]_serializers.py`.
2. **Piece Serialization**: Create model serializers for Building and Token models (e.g., `[Faction]BuildingSerializer`, `[Faction]TokenSerializer`).
3. **Turn State Serialization**: Create a model serializer for the `[Faction]Turn` model to expose the current phase, remaining actions, and temporary turn flags.
4. **Action Validation**: Use serializers to validate incoming requests from the API endpoints (e.g., ensuring a `clearing_id` exists before the transaction runs).
5. **GameState Integration (IMPORTANT)**:
   - Open `game/serializers/game_state_serializer.py`.
   - Add fields for the faction's board pieces and player state to the `GameStateSerializer` class.
   - Without this step, the frontend will never receive or see the faction's data when it boots up or parses a turn.
6. **Event Serialization**:
   - If the faction uses `Event` models (from step 1), build serializers for them in `game/serializers/event_serializers.py`.
7. **Private State (Hidden Info)**:
   - If the faction has hidden components (like facedown tokens or unrevealed cards), create a `[Faction]PrivateSerializer` in `game/serializers/[faction]_serializers.py`.
   - Build a matching private API view (e.g., `get_[faction]_player_private`) inside `game/views/gamestate_views/[faction].py` and register it in `game/urls.py`.
8. **Schema Tagging (CRITICAL)**:
    - Use `@extend_schema` and `@extend_schema_view` from `drf_spectacular.utils` to document all views and serializers.
    - Explicitly tag the `responses` for all methods so `openapi-typescript` generates correct interfaces in `frontend/src/api/types.ts`.
    - Correct schema tagging ensures the frontend can use `components["schemas"]["[YourModel]"]` without manual type definitions.
    - If a field is a ChoiceField (like faction), ensure the label and value are both clear in the schema.
