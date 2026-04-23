---
description: Workflow for setup of action views and get_current_action
---

# Faction Views & Game Action Hooks Workflow

To connect the frontend to the backend game engine:

1. **Hook into `get_current_action` (CRITICAL)**:
   - Look precisely at `game/queries/get_current_action.py` (or similar location where the active game state/prompt is determined).
   - The query needs to look at the Game's active player/faction and the active Event queue.
   - If an Event exists (from Step 4 of the Transaction workflow), the `get_current_action` should return the action payload for _that_ event (so the responder sees the prompt), pausing the active turn UI.
   - Otherwise, ensure it correctly delegates to the `[Faction]Turn` phase to determine what moves are allowed.
2. **Build API Views**:
   - Under `game/views/action_views/[faction]/`, create DRF `APIView` components.
   - These views parse standard HTTP POST payloads, fetching the necessary `Game` object, unpacking parameters (`card_id`, `clearing_id`, etc.), and invoking the specific transaction functions from `faction_transactions.md`.
3. **Route the Views**: Add URLs mapping the API endpoints in the relevant `urls.py`. Keep URL names predictable: `/api/game/<game_id>/action/[faction]/[action_name]`.
4. **Provide Context**: Ensure standard DRF validation responses are clear, as the frontend uses them for generic error throwing.
