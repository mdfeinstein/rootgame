---
description: General workflow for implementing a new faction
---

# Faction Implementation Workflow

When tasked with adding a new faction to the game, follow these sequential steps to ensure all layers of the stack are properly integrated.

1. **Define Models & Events (`/faction_models`)**: Create the database tables (`Building`, `Token`, `Turn` models) and any special `Event` models needed for out-of-turn actions or interruptions (like Ambush or Informants). Include them in `game/models/`.
2. **Setup Serializers (`/faction_serializers`)**: Build serializers for the models. Integrate them deeply into `game/serializers/game_state_serializer.py` so the faction's pieces and turn state appear in the master payload.
3. **Core Logic & Transactions (`/faction_transactions`)**: Write the faction's atomic transactions inside `game/transactions/[faction].py`. Implement Phase hooks (Birdsong, Daylight, Evening).
4. **Current Action & Game Loop (`/faction_views`)**: You MUST hook the faction's logic into `game/queries/get_current_action.py` (or related query). This dictates what the client sees as their "active" action (e.g., standard turn vs. resolving an event).
5. **API Endpoints (`/faction_views`)**: Stand up DRF views in `game/views/action_views/[faction]/` and connect them to urls, linking frontend requests to your transactions.
6. **Frontend Integration (`/faction_frontend`)**: Create `[Faction]PlayerBoard.tsx`, map specific pieces physically on the `Clearing` components, and write user Prompts to handle complex inputs.

_Refer to the other faction-specific workflow guides using `view_file` on them to dive into the technical execution of each step._
