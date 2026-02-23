# Faction Frontend Components

The frontend is responsible for rendering the game board, the unique player boards for each faction, and capturing user input for actions.

## Location in Codebase

Frontend parts are heavily modular, living in `frontend/src/`. Key areas include:

- `frontend/src/components/playerboards/` (The visual player board)
- `frontend/src/components/prompts/` (Interactive action prompts)
- `frontend/src/components/board/` (Rendering specific pieces on clearings)

## Structure

1. **Player Boards**: Each faction has a custom `[Faction]PlayerBoard.tsx` component.
   - It reads the game state (via Zustand store from `useGameActionQuery`) and displays the current resources (wood, specific cards, VP track).
   - _Example: `CatPlayerBoard.tsx`, `WaPlayerBoard.tsx`._
   - It conditionally enables buttons for actions if it's the player's turn and the action is legal based on the current Phase.

2. **Actions & API Calls**: The frontend makes POST requests to the backend Views when a player takes an action. These are typically organized in a `useAction` hook or specific context/service.

3. **Prompts**: For complex actions (e.g., selecting cards to discard or building in a specific clearing), the frontend uses shared Prompt components (`OptionPrompt.tsx`, `NumberPrompt.tsx`) to walk the user through the selection flow before sending the final API request.

4. **Board Elements**: The main game board needs to know how to render the new faction's pieces. `frontend/src/components/board/` manages rendering tokens and buildings. For a new faction, SVGs/icons for their specific troops and buildings must be integrated into the rendering loop for a Clearing.

## Implementing a New Faction UI

1. Create the core `[Faction]PlayerBoard.tsx`.
2. Add rendering for their specific pieces on the main board map.
3. Hook up API calls from custom UI action buttons to the backend endpoints.
4. Ensure the faction is integrated into setup flows and game-end screens.
