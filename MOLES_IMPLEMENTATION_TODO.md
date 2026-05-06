# Moles Backend Implementation - Remaining Work

## Overview
As of now: All transaction functions are implemented and tested. All action view patterns exist for daylight/minister actions. Core infrastructure is in place.

---

## Phase 1: Evening & Price of Failure (Action Layer)

### Evening Transaction Testing
- [x] Test `process_revealed_cards()` 
- [x] Test `draw_cards()`
- [x] Test `end_moles_turn()` and `reset_moles_turn()`
- [x] Test integration of evening steps (PROCESS_REVEALED → CRAFT → DRAW → DISCARD → BEFORE_END → COMPLETED)
- [ ] Coverage goal: Get `moles/evening.py` from 45% to 90%+

### Price of Failure Testing
- [x] Verify `trigger_price_of_failure()` under various state conditions
- [x] Test cascading effects when multiple pieces must be removed
- **Status**: Transaction already has 100% coverage ✓

---

## Phase 2: Evening & Sway Minister Action Views

### Evening Action Views
**File**: `game/views/action_views/moles/evening.py` (create new)
- [ ] `MolesCraftView` — card selection for crafting (iterate selected cards, validate, craft)
- [ ] `MolesDiscardView` — discard excess cards (if hand > 5)
  - Multi-step: iterate through hand, allow user to select discards
  - Validation: can only submit once discard count == hand size - 5

### Sway Minister Action View
**File**: `game/views/action_views/moles/sway_minister.py` (create new)
**Endpoint**: `api/moles/daylight/sway-minister/`

### Action View Testing
- [x] Test evening views: card reveal processing, crafting, drawing, discarding
- [x] Test sway minister view: minister selection, card gathering, step advancement
- [x] Test full flows: daylight → minister actions → sway minister → evening
- **Pattern to follow**: `game/views/action_views/moles/daylight.py` (existing)

---

## Phase 3: Price of Failure & Game State

### Price of Failure Action View
**File**: `game/views/action_views/moles/price_of_failure.py` (create new)
- [x] `MolesPriceOfFailureView` — confirmation when triggered
  - Show what pieces must be removed
  - Allow player to choose which pieces to remove
- [x] Testing: verify removal, state updates

### Moles Game State Serializer
**File**: `game/serializers/moles_game_state.py` (create new)
- [ ] Serialize all moles-specific state for `GameStateSerializer`
  - Warriors count by clearing
  - Buildings (citadels/markets) by clearing
  - Tunnels by clearing
  - Minister states (swayed, used, name)
  - Crown states (tier, used)
  - Daylight phase state (actions_left, brigadier_action, step)
  - Evening phase state (cards_drawn, step)
  - Burrow contents (warrior count)
- [ ] Add to `game/serializers/game_state_serializer.py` dispatcher
- **Reference**: `game/serializers/cats_game_state.py` pattern

---

## Phase 4: URL Registration & Routing

### URL Registration
**File**: `game/urls.py`
- [ ] Register evening action endpoints:
  - `/api/moles/evening/process-revealed-cards/`
  - `/api/moles/evening/craft/`
  - `/api/moles/evening/draw/`
  - `/api/moles/evening/discard/`
- [ ] Register sway minister endpoints:
  - `/api/moles/sway-minister/` (dispatcher)
  - `/api/moles/sway-minister/<minister>/` (per-minister flows)
- [ ] Register price of failure endpoint:
  - `/api/moles/price-of-failure/`

### Current Action Router
**File**: `game/queries/current_action/turns.py`
- [ ] Add `SWAY_MINISTER` step → `reverse("moles-sway-minister")`
- [ ] Add `EVENING` → `MoleEvening` dispatcher:
  - `PROCESS_REVEALED_CARDS` → `reverse("moles-evening-process-revealed")`
  - `CRAFT` → `reverse("moles-evening-craft")`
  - `DRAW` → `reverse("moles-evening-draw")`
  - `DISCARD` → (conditional based on hand size)
  - `BEFORE_END` → None
  - `COMPLETED` → None
- [ ] Add price of failure trigger check (if flagged, redirect to price-of-failure view)

---

## Phase 5: Game Logging

### Log Types (game/models/game_log.py)
- [ ] Add to `LogType` enum (if not already present):
  - `MOLES_SWAY_MARSHAL`, `MOLES_SWAY_CAPTAIN`, etc.
  - `MOLES_CRAFT`, `MOLES_DISCARD`, `MOLES_DRAW`
  - `MOLES_PRICE_OF_FAILURE`
  - `MOLES_TURN_END`

### Log Serializers
**File**: `game/serializers/logs/moles.py` (create new)
- [ ] Sway minister logs (per minister) with:
  - Minister name
  - Crown tier awarded
  - Cards played
  - Points awarded
- [ ] Evening logs:
  - Reveal processing (which cards were revealed)
  - Craft action (which cards, how many points)
  - Draw action (how many drawn, which cards)
  - Discard action (which cards discarded)
- [ ] Price of failure log:
  - What triggered it
  - What pieces were removed
- [ ] Register all serializers in `game/serializers/logs/main.py` dispatcher

---

## Phase 6: Integration & Testing

### End-to-End Flow Testing
- [ ] Full turn cycle: Birdsong → Daylight (actions → minister actions → sway minister) → Evening (process → craft → draw → discard) → next player
- [ ] Test with crafted cards active (saboteurs, charm offensive, etc.)
- [ ] Test undo/redo with evening and sway minister actions
- [ ] Test snapshot consistency throughout all phases

### Frontend Contract Alignment
- [ ] Verify game state serializer matches frontend expectations
- [ ] Verify action response format matches frontend action handling
- [ ] Verify error messages are user-friendly

### Performance & Edge Cases
- [ ] Test with max warriors, max buildings, max tunnels on map
- [ ] Test discard flows with large hand sizes
- [ ] Test evening phase with many revealed cards
- [ ] Verify no N+1 queries in game state serialization

---

## Checklist Summary

**Completed** ✓
- [x] All transaction functions (actions, minister_actions, sway_minister, price_of_failure)
- [x] Transaction testing (90%+ coverage for daylight/minister actions)
- [x] Daylight & minister action views
- [x] URL registration for daylight/minister actions
- [x] Current action routing for daylight/minister actions
- [x] Basic game log types for moles

**Not Started** 
- [ ] Evening transactions testing
- [ ] Evening action views (4 views)
- [ ] Sway minister action view (dispatcher + per-minister)
- [ ] Price of failure action view
- [ ] Moles game state serializer
- [ ] Evening/sway/price-of-failure URL registration
- [ ] Evening/sway/price-of-failure current action routing
- [ ] Detailed game log serializers for all moles actions
- [ ] End-to-end integration testing
- [ ] Frontend contract verification

---

## Estimated Effort

- **Phase 1** (Evening testing): 3-4 hours
- **Phase 2** (Evening/Sway views): 4-5 hours  
- **Phase 3** (Price of failure + state): 2-3 hours
- **Phase 4** (URL routing): 1-2 hours
- **Phase 5** (Logging): 2-3 hours
- **Phase 6** (Integration): 3-4 hours

**Total**: ~18-24 hours for a complete Moles backend implementation

---

## Notes

- All transaction business logic is complete and tested
- View patterns are established (reference: birds, cats, wa, crows)
- Main remaining work is views, serialization, routing, and logging
- Evening implementation is partially done but untested (noted as 45% coverage)
- Mayor view is implemented but not listed in original TODO — may be oversight
