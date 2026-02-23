# Faction Serializers

Serializers are responsible for translating the faction's Django models into JSON format so the frontend can read the game state, and for validating incoming data from the frontend.

## Location in Codebase

Serializers are located in `game/serializers/`. Unlike models, they are typically consolidated into a single file per faction, e.g., `cat_serializers.py`, `bird_serializers.py`, `wa_serializers.py`.

## Key Responsibilities

1. **Piece Serialization**: Converting the `Turn`, `Building`, and `Token` models into JSON. E.g., `CatTurnSerializer`, `WaSympathySerializer`.
2. **Action Validation**: Serializers act as the first line of defense against illegal moves submitted via the API.
3. **Integration with `GameStateSerializer`**: The main `game/serializers/game_state_serializer.py` must be updated to include the new faction's serializers. The game state payload needs to include the faction's unique elements (board state, player board state) so the UI can render them.

## Example Flow

When the frontend requests the current game state, `GameStateSerializer` will invoke `CatWoodSerializer` (for example) to bundle all the wood positions on the board into the JSON response. When adding a new faction, ensure its unique pieces and turn state are aggregated into the main game state payload.
