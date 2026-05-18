---
description: Workflow for faction transactions and game loop
---

# Faction Transactions & Game Loop Workflow

Transactions are the mutating functions that execute valid game logic.

1. **Create the File**: Create `game/transactions/[faction].py`.
2. **Turn Phases**: Implement standard phase hook functions like `[faction]_birdsong(game)`, `[faction]_daylight(game)`, and `[faction]_evening(game)`. These functions must transition the `[Faction]Turn` object correctly.
3. **Action Transactions**: Write functions for each discrete legal action (e.g., `[faction]_build()`, `[faction]_recruit()`).
   - Validate inputs explicitly (check enough resources, check clearing rule, check phase state).
   - Mutate piece/turn models safely.
   - Use `record_action()` from `action_serializer.py` at the end to generate undoable actions and logs.
4. **Integrating Events & Interrupts**:
   - When a player triggers a mechanic requiring a response, the transaction should _not_ resolve the action entirely. Instead, it should create the relevant `Event` model and pause the standard turn state.
   - _Example_: If you move and trigger Outrage, you create an Outrage event.
5. **Global Hooks**: The faction may need to override or participate in shared modules (e.g., `battle.py`, `removal.py`). Search for `game.faction` checks in these modules and ensure the new faction handles generic damage or destruction logic correctly.
