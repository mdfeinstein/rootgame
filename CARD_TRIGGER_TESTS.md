# Card Trigger Tests Implementation Plan

This document tracks the implementation of card trigger tests for Moles and Crows factions, following the pattern from Birds tests.

## Summary

✅ **COMPLETE: 11 tests, 100% passing**
- 5 Moles tests (was 3)
- 6 Crows tests (was 3)

## Moles Card Trigger Tests

| Card | Phase | Trigger | Test | Status | Notes |
|------|-------|---------|------|--------|-------|
| Saboteurs | Birdsong NOT_STARTED | saboteurs_check() | test_moles_saboteurs_flow | ✅ DONE | Works for all factions |
| Eyrie Emigre | Birdsong BEFORE_END | is_emigre() | test_moles_eyrie_emigre_flow | ✅ DONE | Generic Birdsong phase check works |
| Charm Offensive | Evening NOT_STARTED | check_charm_offensive() | test_moles_charm_offensive_flow | ✅ DONE | Added Moles support to can_use_card() |
| Informants | Not triggered in Moles | N/A | N/A | N/A | Not used by Moles faction |

## Crows Card Trigger Tests

| Card | Phase | Trigger | Test | Status | Notes |
|------|-------|---------|------|--------|-------|
| Saboteurs | Birdsong NOT_STARTED | saboteurs_check() | test_crows_saboteurs_flow | ✅ DONE | Works for all factions |
| Eyrie Emigre | Birdsong BEFORE_END | is_emigre() | test_crows_eyrie_emigre_flow | ✅ DONE | Generic Birdsong phase check works |
| Charm Offensive | Daylight BEFORE_END | check_charm_offensive() | test_crows_charm_offensive_flow | ✅ DONE | Added Crows-specific logic to can_use_card() |
| Informants | Evening DRAWING | informants_check() | test_crows_informants_flow | ✅ DONE | Faction-specific support already existed |

## Test Pattern

Each test follows this pattern:
1. Create card and give to player as CraftedCardEntry
2. Set phase and step to test scenario
3. Call step_effect() to trigger card checks
4. Call get_action() and verify card route
5. Submit appropriate action to skip card
6. Verify next route or game state change

## Implementation Status

**All Tests Passing (11/11):**

**Moles (5 tests):**
- ✅ test_moles_turn_structure
- ✅ test_moles_daylight_actions_available
- ✅ test_moles_saboteurs_flow
- ✅ test_moles_eyrie_emigre_flow
- ✅ test_moles_charm_offensive_flow

**Crows (6 tests):**
- ✅ test_crows_turn_structure
- ✅ test_crows_birdsong_route
- ✅ test_crows_saboteurs_flow
- ✅ test_crows_eyrie_emigre_flow
- ✅ test_crows_charm_offensive_flow
- ✅ test_crows_informants_flow

## Changes Made

### 1. Added Faction Support to `game/queries/cards/active_effects.py`
- Added Moles import: `from game.models.moles.turn import MoleBirdsong, MoleDaylight, MoleEvening`
- **SABOTEURS**: Added Moles faction case for Birdsong NOT_STARTED check
- **CHARM_OFFENSIVE**: 
  - Added Moles faction case for Evening NOT_STARTED check
  - Added Crows faction-specific logic for Daylight BEFORE_END check

### 2. Added Moles Support to `game/queries/general.py`
- Extended `get_current_phase()` function to support Moles faction
- This was critical - without this, `is_start_of_phase()` would fail for Moles

### 3. Updated Test Files
- **Moles**: Added `test_moles_eyrie_emigre_flow` and `test_moles_charm_offensive_flow`
- **Crows**: Added `test_crows_eyrie_emigre_flow`, `test_crows_charm_offensive_flow`, and `test_crows_informants_flow`
- All tests call `step_effect()` after setting phase state to ensure card triggers are properly evaluated

## Key Implementation Details

- **Eyrie Emigre**: Uses generic `is_phase(player, "Birdsong")` check in can_use_card, works for all factions
- **Charm Offensive**: Different timing per faction:
  - Birds/WA/Cats/Moles: Evening NOT_STARTED
  - Crows: Daylight BEFORE_END
- **Informants**: Faction-specific step checks in Evening phase
- **Saboteurs**: Generic start-of-phase check, works for all factions

## Success Criteria Met

✅ All 11 tests passing
✅ Card triggers properly detected and routed
✅ Faction-specific timing handled correctly
✅ Tests follow established pattern from Birds implementation
✅ No manual phase stepping issues - uses step_effect() for proper state transitions
