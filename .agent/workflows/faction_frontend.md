---
description: Workflow for Faction Frontend Integration
---

# Faction Frontend Implementation Workflow

After the backend is prepared, you must connect the new faction to the React frontend.

1. **Player Board**:
   - Navigate to `frontend/src/components/playerboards/`.
   - Create a specific `[Faction]PlayerBoard.tsx`.
   - This board must connect to the `useGameActionQuery` hook to render the faction's active state.
   - For private state, create a `use[Faction]PlayerQuery` hook tagged with types from `frontend/src/api/types.ts`.
   - **CRITICAL**: The `PlayerProvider` now resolves faction names directly from the schema provided in the `/player/` info response. Ensure the backend serializer returns the correct `FactionLabel`.
2. **Prompts and UI State**:
   - For complex queries (e.g., choosing a specific number of items, selecting clearings), use or build Prompt components in `frontend/src/components/prompts/`.
   - Ensure these prompts hook into the active action fetched by `get_current_action`.
3. **Board Elements**:
   - Add map rendering logic in `frontend/src/components/board/`.
   - Use `factionToColor` in `WarriorTroop.tsx` for visual consistency.
4. **Triggering the API**:
   - Wrap interactive buttons on the Player Board in the standard action hooks.
   - **Naming Convention**: Faction routes must be in kebab-case. Use `labelToRoute(faction.label)` (e.g. `woodland-alliance` for "Woodland Alliance") when constructing query keys or URL strings.
