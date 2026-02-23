---
description: Workflow for Faction Frontend Integration
---

# Faction Frontend Implementation Workflow

After the backend is prepared, you must connect the new faction to the React frontend.

1. **Player Board**:
   - Navigate to `frontend/src/components/playerboards/`.
   - Create a specific `[Faction]PlayerBoard.tsx`.
   - This board must connect to the `useGameActionQuery` Zustand hook to render the faction's active state (resources, victory points, remaining actions).
2. **Prompts and UI State**:
   - For complex queries (e.g., choosing a specific number of items, selecting clearings), you must use or build Prompt components in `frontend/src/components/prompts/`.
   - Ensure these prompts hook into the active action fetched by `get_current_action` (from backend) so the correct player sees the prompt while others see a waiting screen.
3. **Board Elements**:
   - Add map rendering logic in `frontend/src/components/board/`. The `Clearing` or `Token` components must know how to render the new faction's SVGs/Icons physically on the screen.
4. **Triggering the API**:
   - Wrap interactive buttons on the Player Board in the standard `useAction` hook (or equivalent abstraction). Ensure these requests map exactly to the DRF API Views created in your `faction_views.md` workflow.
