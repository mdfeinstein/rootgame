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
