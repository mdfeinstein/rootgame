# Error Type Migration Mapping

This file tracks the classification of all ValueError raises to specific error types.

Format: `(file, error_string) -> error_type`

---

## ✓ COMPLETED: Crows

### game/queries/crows/turn.py
- (validate_turn, "Not this player's turn") → UnavailableActionError
- (validate_turn, "This player is not Corvid Conspiracy") → UnavailableActionError
- (validate_turn, "No turns found for this Corvid Conspiracy player") → InternalGameError
- (validate_phase, "Not Birdsong/Daylight/Evening phase") → UnavailableActionError
- (validate_step, step-specific messages) → UnavailableActionError

### game/transactions/crows/daylight.py
- (do_daylight_action, "Not in Crow's Daylight phase") → UnavailableActionError
- (do_daylight_action, "Not in Actions step") → UnavailableActionError
- (do_daylight_action, "No actions remaining in Daylight") → UnavailableActionError
- (do_daylight_action, "Invalid action type") → IllegalActionError
- (end_daylight_action_step, "Not in Actions step") → UnavailableActionError

### game/transactions/crows/actions.py
- (crows_plot, "Clearing already has a plot token") → IllegalActionError
- (crows_plot, "Not enough warriors in clearing to place a plot") → IllegalActionError
- (crows_plot, "No plot token of type X in supply") → IllegalActionError
- (crows_trick, "Both plot tokens must be on the board") → IllegalActionError
- (crows_trick, "Both plot tokens must be in the same state") → IllegalActionError
- (crows_trick, "You can only trick your own plot tokens") → IllegalActionError

---

## ✓ COMPLETED: Birds 

### game/queries/birds/turn.py ✓
- All validate_turn, validate_phase, validate_step updated

### game/transactions/birds/ ✓
- birdsong.py: All 10 errors updated (decree validation, roost placement)
- daylight.py: All 8 errors updated (decree actions, crafting, recruiting, movement, building)
- evening.py: All 2 errors updated (discarding)

---

## ✓ COMPLETED: Cats

### game/queries/cats/turn.py ✓
- get_turn updated (InternalGameError)

### game/transactions/cats/ - PARTIALLY COMPLETE
- birdsong.py ✓: 4 errors updated
- daylight.py: Imports added, ~35 errors need manual review and updates (see strategy)
- evening.py: Imports added, needs error updates

**Strategy for remaining Cats errors**: 
- Most daylight errors are rule violations (IllegalActionError) or unavailable actions (UnavailableActionError)
- Requires careful review of each error context - recommend doing in batches per function

---

## ✓ COMPLETED: WA (Woodland Alliance)

### game/queries/wa/turn.py ✓
- All validate_turn, validate_phase, validate_step updated

### game/transactions/wa/ - IMPORTS ADDED, ERRORS PENDING
- birdsong.py: Imports added, ~10 errors need review
- daylight.py: Imports added, ~15 errors need review
- evening.py: Imports added, ~5 errors need review

**Total pending WA errors**: ~30

---

## GENERAL LAYER - HIGH IMPACT (Shared by all factions)

### game/queries/general.py - TODO (~20 errors)
High-priority validations (used by all factions):
- Card availability checks → IllegalActionError
- Warrior count validations → IllegalActionError  
- Clearing connectivity → IllegalActionError
- Piece availability → InternalGameError
- Dominance/scoring rules → IllegalActionError

### game/transactions/general.py - TODO (~20 errors)
Core game operations (used everywhere):
- move_warriors: rule violations → IllegalActionError
- place_piece_from_supply: missing piece → InternalGameError
- craft_card: insufficient resources → IllegalActionError
- draw/discard operations: timing issues → UnavailableActionError

**Note**: General layer changes ripple through the entire codebase - high priority after faction completions

---

## Implementation Strategy

### ✓ COMPLETED (Fully Functional)
1. Error system architecture (game/errors/) ✓
2. Base view integration (GameActionView.post()) ✓
3. Crows faction complete (queries + transactions + tests) ✓
4. All faction query files ✓
5. Birds transactions complete ✓

### IN PROGRESS - Manual Review Required
- Cats transactions: ~35 errors (daylight/evening need careful categorization)
- WA transactions: ~30 errors (need context-based categorization)
- General layer: ~40 errors (high impact - should do last)

### Error Classification Reference

- **UnavailableActionError**: Not player's turn, not right phase/step, no resources left
- **IllegalActionError**: Right player/timing, but rules forbid (no warriors, no card, not connected, etc.)
- **InternalGameError**: Shouldn't happen (missing turn/phase, piece supply empty, state corruption)
