# Faction Transactions & Game Loop

Transactions are where the core game logic lives. They are atomic operations that mutate the game state, representing a successful, legal action by a player.

## Location in Codebase

Transactions are located in `game/transactions/`. Each faction typically gets its own file for its specific rules:

- `game/transactions/cats.py`
- `game/transactions/birds.py`
- `game/transactions/wa.py`

## Structure

### The Game Loop Integration

The root engine is built around player turns progressing through distinct phases (Birdsong, Daylight, Evening). A faction's transaction file must define how it behaves in these phases.

1. **Birdsong, Daylight, Evening**: The main turn structure requires functions to handle the "start" or "end" of each phase, setting up the required state for the next phase.
   _Example: `cat_birdsong(game)`, `wa_evening(game)`._

### Specific Actions

Every action a player can take (e.g., Cat Build, Bird Recruit, WA Mobilize) is a transaction function.

- It receives the `Game` state and the specific parameters from the view (e.g., `clearing_id`, `card_ids`).
- It validates the legality of the move (e.g., "does the player have enough wood?", "is the clearing ruled?").
- If valid, it mutates the database models (moves pieces, deducts cards, adds VP).
- It calls `record_action()` to save the move to the `Action` history, allowing for undo/redo and logging.

### `general.py` and Shared Transactions

Some actions, like Battle, Movement, and Crafting, are handled by the core rulebook and usually live in `general.py` or specific topic files like `battle.py`. Faction implementations hook into these via shared functions, overriding or supplying specific parameters (e.g., Birds taking an extra hit in battle).

## Implementing a New Faction

To add a new faction, you must:

1. Write transaction functions for every unique action on their board.
2. Implement phase transitions (handling end-of-turn cleanup, drawing cards).
3. Ensure their actions utilize `record_action()` for state history.
