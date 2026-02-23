# Faction Models

The database models for a faction define its physical presence on the board (pieces) and its temporary state during a turn.

## Location in Codebase

Models are located in `game/models/[faction_name]/`. For example:

- `game/models/cats/`
- `game/models/birds/`
- `game/models/wa/`

## Standard Structure

A typical faction model directory contains the following files:

1. **`buildings.py`**: Defines models for the faction's buildings. Typically inherits from a base `Building` class or standard Django `Model`. Includes fields like the clearing it's in, whether it's built, etc.
   _Example: `CatSawmill`, `BirdRoost`, `WaBase`._

2. **`tokens.py`**: Defines models for the faction's tokens. Similar to buildings, these represent mobile or static non-building pieces.
   _Example: `CatWood`, `WaSympathy`._

3. **`turn.py`**: The critical `[Faction]Turn` model. This model stores the state of the active turn for the player. It tracks phase progress (Birdsong, Daylight, Evening), remaining actions, crafted cards this turn, and temporary flags (e.g., "has_marched", "actions_remaining").
   _Example: `CatTurn`, `BirdTurn`, `WaTurn`._

4. **`setup.py`**: Contains models or logic specific to the initial setup of the faction if it requires database state before the game starts (e.g., choosing starting clearings).

## Integration

When creating a new faction, these models must be linked back to the main `Game` or `Player` models as necessary, often via OneToOne or ForeignKey relationships, and their creation must be handled during the game initialization phase.
