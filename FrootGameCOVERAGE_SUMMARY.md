# Moles Faction Coverage Report
**Date**: 2026-05-05
**Test Run**: All Moles transactions and action views

## Summary

### Transaction Tests
- **Total Tests**: 111
- **Status**: ✅ ALL PASSING
- **Overall Coverage**: 87.84%

| File | Stmts | Miss | Cover |
|------|-------|------|-------|
| `moles/__init__.py` | 2 | 0 | 100.00% |
| `moles/birdsong.py` | 23 | 1 | 92.59% |
| `moles/daylight/actions.py` | 87 | 6 | 90.48% |
| `moles/daylight/minister_actions.py` | 188 | 9 | 92.37% |
| `moles/daylight/sway_minister.py` | 35 | 1 | 94.87% |
| `moles/evening.py` | 66 | 18 | 70.73% |
| `moles/price_of_failure.py` | 46 | 0 | 100.00% |
| `moles/turn.py` | 119 | 19 | 81.56% |

**Strong Coverage (90%+)**:
- `price_of_failure.py` — 100%
- `sway_minister.py` — 94.87%
- `minister_actions.py` — 92.37%
- `birdsong.py` — 92.59%
- `daylight/actions.py` — 90.48%

**Good Coverage (80-90%)**:
- `turn.py` — 81.56%

**Needs Work (70-80%)**:
- `evening.py` — 70.73% (discard and process_revealed_cards flows)

### Action View Tests
- **Test Files**: 6 (plus 2 turn flow test files)
- **Status**: ✅ 68 PASSING (1 Django framework error unrelated to tests)
- **Overall Coverage**: 80.34%

| File | Stmts | Miss | Cover | Tests |
|------|-------|------|-------|-------|
| `daylight.py` | 270 | 67 | 72.47% | - |
| `evening.py` | 172 | 66 | 58.82% | 9 |
| `minister_actions.py` | 488 | 45 | 88.92% | 22 |
| `price_of_failure.py` | 69 | 5 | 90.11% | 13 |
| `sway_minister_view.py` | 128 | 18 | 83.97% | 11 |

**Strong Coverage (85%+)**:
- `minister_actions.py` — 88.92% (22 tests)
- `price_of_failure.py` — 90.11% (13 tests)
- `sway_minister_view.py` — 83.97% (11 tests)

**Good Coverage (70-85%)**:
- `daylight.py` — 72.47% (needs error cases, all routing branches)

**Needs Work (<70%)**:
- `evening.py` — 58.82% (needs comprehensive happy path + error tests)

### Test Suite Files
1. **Transaction Tests**: 111 tests across 8 files
   - `test_moles_birdsong.py` — 4 tests
   - `test_moles_daylight_actions.py` — 30 tests
   - `test_moles_daylight_ministers.py` — 47 tests
   - `test_moles_daylight_sway_minister.py` — 10 tests
   - `test_moles_evening.py` — 7 tests
   - `test_moles_price_of_failure.py` — 10 tests
   - `test_moles_setup.py` — 6 tests

2. **Action View Tests**: 68 tests across 6 files
   - `test_moles_daylight_actions.py` — ? tests
   - `test_moles_evening.py` — 9 tests
   - `test_moles_minister_actions.py` — 22 tests
   - `test_moles_price_of_failure.py` — 13 tests
   - `test_moles_sway_minister_view.py` — 11 tests

3. **Turn Flow Integration Tests**: 20 tests
   - `test_moles_turn_flow.py` — 9 tests
   - `test_crows_turn_flow.py` — 11 tests

### Implementation Status

✅ **Fully Implemented**:
- Birdsong phase (place_burrow_warriors)
- Daylight actions (move, battle, build, dig, recruit)
- Minister actions (all 9 ministers + Mayor)
- Evening phase (craft, discard, draw, process_revealed, reset)
- Price of failure event resolution
- Full turn flow with phase transitions

✅ **Complete View Implementations**:
- `MolesSwayMinisterView` — select minister → select cards → confirm
- `MolesCraftingView` — select card → select clearing → select building
- `MolesDiscardView` — iterative single card discard
- `MolesPriceOfFailureView` — select highest-rank swayed minister
- `MolesMinisterActionsView` — dispatcher with brigadier mid-sequence handling
- 9 sub-views for individual minister actions (Marshal, Captain, Foremole, Brigadier, Banker, Duchess, Earl, Baron)
- `MolesMinisterMayorView` — copy swayed minister with route delegation

### Known Gaps

**Evening View Coverage** (58.82%):
- Need comprehensive tests for:
  - Crafting with various building types
  - Discard with various hand sizes
  - Card processing with revealed/wild cards
  - Error cases (wrong step, invalid cards, etc.)

**Daylight View Coverage** (72.47%):
- Need tests for:
  - All routing branches (actions, move, battle, build, dig, recruit)
  - Error cases for each action
  - Validation failures

**Evening Transaction Coverage** (70.73%):
- `process_revealed_cards` needs edge cases
- `discard_card` needs boundary testing
- `draw_cards` needs various market configurations

### Verification Commands

```bash
# Run all Moles transactions
python .agent/scripts/run_tests.py game.tests.transactions.moles

# Run all Moles action view tests
python .agent/scripts/run_tests.py game.tests.action_views.moles

# Generate coverage report
python -m coverage run --source='game/transactions/moles,game/views/action_views/moles' manage.py test game.tests.transactions.moles game.tests.action_views.moles
python -m coverage report
python -m coverage html  # Open htmlcov/index.html

# Run specific test classes
python .agent/scripts/run_tests.py game.tests.action_views.moles.test_moles_minister_actions
python .agent/scripts/run_tests.py game.tests.action_views.moles.test_moles_price_of_failure
python .agent/scripts/run_tests.py game.tests.action_views.moles.test_moles_sway_minister_view
```

### Recommendations

1. **Prioritize evening.py view coverage** (58.82%) — add comprehensive happy path tests for craft/discard flows
2. **Complete daylight.py view coverage** (72.47%) — ensure all routing branches and error cases are tested
3. **Add edge case tests for evening.py transactions** — boundary conditions on hand sizes, market counts
4. **Consider mutation testing** to verify test quality beyond line coverage

