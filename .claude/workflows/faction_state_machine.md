---
description: Turn state machine architecture for faction turns
---

# Faction State Machine

This document explains how factions manage their turn state machine — the progression through phases and steps that define a player's turn.

## Architecture Overview

The turn state machine is built across three layers:

### 1. **Models** (`game/models/[faction]/turn.py`)
Define the state structure as Django models.

**Pattern:**
- `[Faction]Turn` — root turn model (FK to Player, turn_number counter)
- `[Faction]Birdsong`, `[Faction]Daylight`, `[Faction]Evening` — phase models (FK to Turn, step field with choices)
- Each phase has a `step` field that is a `CharField` with `TextChoices` enum

**Example (Crows):**
```python
class CrowTurn(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    turn_number = models.PositiveSmallIntegerField()

class CrowBirdsong(models.Model):
    class CrowBirdsongSteps(models.TextChoices):
        NOT_STARTED = "0", "Not Started"
        CRAFT = "1", "Craft"
        FLIP = "2", "Flip"
        RECRUIT = "3", "Recruit"
        BEFORE_END = "z", "Before End"
        COMPLETED = "4", "Completed"
    
    turn = models.ForeignKey(CrowTurn, on_delete=models.CASCADE, related_name="birdsong")
    step = models.CharField(max_length=1, choices=CrowBirdsongSteps.choices, default=CrowBirdsongSteps.NOT_STARTED)
```

**Key invariant:** A turn's three phases are created atomically in `[Faction]Turn.create_turn()`. All three exist for the duration of the turn.

### 2. **Queries** (`game/queries/[faction]/turn.py`)
Read the state without mutation.

**Essential functions:**

| Function | Purpose |
|---|---|
| `validate_turn(player)` | Assert it's the player's turn, return their current turn |
| `get_phase(player)` | Return the current active phase (Birdsong/Daylight/Evening) by finding first non-COMPLETED |
| `validate_phase(player, phase_type)` | Assert we're in a specific phase, raise UnavailableActionError if not |
| `validate_step(player, step)` | Assert we're in a specific step, raise UnavailableActionError if not |

**Logic of `get_phase()`:**
```python
# Iterate through phases in order; return the first one that isn't COMPLETED
birdsong = get_phase(turn)
if birdsong.step != COMPLETED:
    return birdsong
elif daylight.step != COMPLETED:
    return daylight
else:
    return evening
```

This establishes **phase ordering** without explicit state: as long as Birdsong is not COMPLETED, it is active. Once Birdsong is COMPLETED, Daylight becomes active, and so on.

### 3. **Transactions** (`game/transactions/[faction]/turn.py`)
Mutate the state atomically.

**Core functions:**

| Function | Purpose |
|---|---|
| `next_step(player)` | Move to next step in the current phase, trigger `step_effect()` |
| `step_effect(player, phase=None)` | Execute passive/event effects for the current step (draw cards, trigger ambushes, etc.) |
| `create_[faction]_turn(player)` | Create a new Turn + Phase models, log the turn |
| `end_[faction]_turn(player)` | Mark all phases COMPLETED, reset faction state (e.g., plot tokens), call `next_players_turn()` |

**The `step_effect()` pattern:**
The heart of the state machine. This function runs **after** `next_step()` updates the step value and contains all the "passive" logic for that step:
- Drawing cards (Evening DRAWING step)
- Triggering interrupts (Birdsong NOT_STARTED checks for Saboteurs)
- Advancing automatically (BEFORE_END steps that auto-advance)

```python
def step_effect(player: Player, phase=None):
    if phase is None:
        phase = get_phase(player)
    
    match phase:
        case CrowBirdsong():
            match phase.step:
                case CrowBirdsong.CrowBirdsongSteps.NOT_STARTED:
                    log_phase(...)
                    if not saboteurs_check(player):
                        next_step(player)  # Auto-advance unless blocked
                case CrowBirdsong.CrowBirdsongSteps.CRAFT:
                    score_coffins(...)
        case CrowDaylight():
            # ... etc
```

### 4. **Turn Orchestration** (`game/transactions/general.py`)
The dispatcher that coordinates turn creation and phase transitions across all factions.

**`next_players_turn(game)`** — moves to next player's turn:
1. Increment `game.current_turn` to next player in turn order
2. Fetch new player
3. Call `check_dominance_victory(new_player)` (may end game)
4. Reset any game-state (e.g., reset crafted cards' "used" flag)
5. Call `create_turn(new_player)` — factory that dispatches to faction-specific `create_[faction]_turn()`
6. Call `step_effect(new_player)` — factory that dispatches to faction-specific handler, triggers beginning-of-turn logic

**Faction dispatch (general.py:368-408):**
```python
def next_step(player: Player):
    match player.faction:
        case Faction.CROWS:
            from game.transactions.crows import next_step
            next_step(player)
        # ... other factions

def step_effect(player: Player):
    match player.faction:
        case Faction.CROWS:
            from game.transactions.crows import step_effect
            step_effect(player)
        # ... other factions
```

This factory pattern allows each faction to have **different step sequences and different effects at each step**, while the game loop (`next_players_turn`) remains faction-agnostic.

## State Machine Flow

For a complete turn, the sequence is:

```
next_players_turn() [in general.py]
    ↓
create_turn(new_player) [dispatches to faction-specific]
    ↓
step_effect(new_player) [dispatches to faction-specific]
    ├─ phase.step = NOT_STARTED → logs phase, may auto-advance or wait for action
    └─ If action taken (or auto-advanced):
        next_step(player)
        step_effect(player)
            ├─ phase.step = [ACTION STEP] → handles piece placement, cards, etc.
            ├─ (may call next_step → step_effect recursively)
            └─ Eventually reaches COMPLETED
            
When final phase (Evening) reaches COMPLETED:
end_[faction]_turn(player)
    ↓
reset_[faction]_turn(player) [reset faction state]
    ↓
next_players_turn(game) [loop back to start]
```

## Client Interaction Points

The frontend drives the state machine via action endpoints (e.g., `POST /api/crows/take-action/`). These endpoints:

1. Call `validate_turn(player)` to check it's the player's turn
2. Call `validate_phase()` and/or `validate_step()` to ensure the action is legal
3. Mutate state (move pieces, discard cards, etc.)
4. Call `step_effect()` to handle passive effects (auto-advance, draw, trigger events)
5. Return updated game state

**Example:** A Crow player has advanced to Daylight ACTIONS step. They place warriors via an action endpoint, which calls `step_effect()`. Since ACTIONS is not an auto-advance step, `step_effect()` does nothing and the client polls for its next turn. When finished, the client calls the "End Actions" endpoint, which calls `next_step(player)` → `step_effect(player)`, advancing to BEFORE_END and handling charm offensive checks.

## Implementation Checklist for New Faction

When adding a new faction, follow this pattern:

1. **Models** (`game/models/[faction]/turn.py`)
   - [ ] Create `[Faction]Turn` with player FK and turn_number field
   - [ ] Create phase models (typically 3: Birdsong, Daylight, Evening) with step enums
   - [ ] Implement `[Faction]Turn.create_turn()` to atomically create all three phases
   - [ ] Register in `game/utils/snapshot.py` for undo/redo support

2. **Queries** (`game/queries/[faction]/turn.py`)
   - [ ] `validate_turn(player)` — check faction and current player
   - [ ] `get_phase(player)` — iterate phases, return first non-COMPLETED
   - [ ] `validate_phase(player, phase_type)` — phase type guard
   - [ ] `validate_step(player, step)` — step type guard with error messages

3. **Transactions** (`game/transactions/[faction]/turn.py`)
   - [ ] `create_[faction]_turn(player)` — call Turn.create_turn(), log the turn
   - [ ] `next_step(player)` — advance step using `next_choice()` utility, call `step_effect()`
   - [ ] `step_effect(player, phase=None)` — nested match statements for phases/steps, handle logic
   - [ ] `end_[faction]_turn(player)` — mark phases COMPLETED, reset state, call `next_players_turn()`
   - [ ] `reset_[faction]_turn(player)` — reset any faction-specific tokens/cards (called from end_turn)

4. **General Dispatchers** (`game/transactions/general.py`)
   - [ ] Add faction case to `create_turn()` (lines 296-315)
   - [ ] Add faction case to `next_step()` (lines 368-386)
   - [ ] Add faction case to `step_effect()` (lines 390-408)

5. **Views & API Wiring**
   - [ ] Wire action endpoints to transaction functions
   - [ ] Call `validate_phase()` and `validate_step()` before mutations
   - [ ] Return updated game state via serializer

## Common Patterns

### Auto-advancing Steps
Steps that have no player choice (e.g., a "draw cards" step) should auto-advance:
```python
case Phase.NOT_STARTED:
    # effect happens
    next_step(player)  # Auto-advance within step_effect
```

### Blocking Steps
Steps that await player action should **not** call `next_step()` in `step_effect()`. The action endpoint will call it:
```python
case Phase.ACTIONS:
    pass  # step_effect does nothing; endpoint calls next_step when player is done
```

### Interrupt Checks
Before auto-advancing, check for interrupt conditions:
```python
case Phase.DRAWING:
    if not informants_check(player):  # Informants card blocks
        next_step(player)
```

### BEFORE_END Steps
Many phases include a `BEFORE_END = "z"` step (ordered last alphabetically) to trigger end-of-phase logic:
```python
case Phase.BEFORE_END:
    if not check_charm_offensive(player):  # Check for effect
        next_step(player)  # If no effect, advance to COMPLETED
```

## Undo/Redo Implications

Every new Turn/Phase model **must** be registered in `game/utils/snapshot.py`. The snapshot system captures the entire state before a transaction runs, allowing rollback. Unregistered models corrupt undo/redo.

See `snapshot_undo.md` for details.
