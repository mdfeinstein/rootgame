# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code Intelligence

**Workflow: Grep to locate, LSP to navigate**

1. Use **Grep** to find a symbol definition by pattern (e.g. `class GameActionView`, `def foo_bar`)
2. Once you have the file & line, use **LSP** to explore:
   - `findReferences` to see all usages across the codebase
   - `goToDefinition` / `goToImplementation` to jump to source
   - `documentSymbol` to list all symbols in a file
   - `hover` for type info without reading
   - `incomingCalls` / `outgoingCalls` for call hierarchy

Before renaming or changing a function signature, use
`findReferences` to find all call sites first.

Use Grep/Glob only for text/pattern searches (comments,
strings, config values) where LSP doesn't help.

After writing or editing code, check LSP diagnostics before
moving on. Fix any type errors or missing imports immediately.

## Project Overview

A Django/React web adaptation of the board game *Root* by Cole Wehrle. Live at https://root.mattdf.net/

**Stack**: Django 5.0 + Django REST Framework + Django Channels (WebSockets) | React 19 + TypeScript + Vite + Mantine UI + TanStack Query | Redis | Docker + Daphne (ASGI)

## Development Commands

### Backend
```bash
# Activate venv first
source F:/python/envs/.venv_web/Scripts/activate  # or use the conda env

python manage.py runserver        # Django dev server
python manage.py migrate
python manage.py spectacular --file schema.yml   # Regenerate OpenAPI schema
```

### Frontend
```bash
cd frontend
npm run dev           # Vite dev server (port 5173)
npm run build
npm run lint
npm run generate-types  # MUST run after any API changes (see Type Generation below)
```

### Running Tests
```bash
# Use the agent script — output is redirected to test_output.txt automatically
python .agent/scripts/run_tests.py game.tests.test_module_name

# Run a single test class or method
python .agent/scripts/run_tests.py game.tests.test_module_name.TestClass.test_method
```

### Type Generation (Critical)
After any backend API change, regenerate frontend types:
```bash
python manage.py spectacular --file schema.yml
cd frontend && npm run generate-types
# Equivalent: npx openapi-typescript ../schema.yml -o src/api/types.ts
```

## Architecture

### Backend Layering (strict — do not skip layers)

| Layer | Location | Purpose |
|---|---|---|
| Models | `game/models/` | Database schema only |
| Selectors | `game/queries/` | Read-only queries and business logic |
| Services | `game/transactions/` | Atomic DB mutations with validation |
| API | `game/views/` | REST endpoints — thin, delegate to queries/transactions |

**Current factions**: Marquise de Cats (`cats/`), Eyrie Dynasties (`birds/`), Woodland Alliance (`wa/`), Corvid Conspiracy (`crows/`)

Each faction has its own subdirectory under `models/`, `queries/`, `transactions/`, `views/action_views/`, `serializers/`, and `tests/`.

### Key Files

- **`game/serializers/game_state_serializer.py`** — Master payload sent to frontend on load. Add new faction state here.
- **`game/utils/snapshot.py`** — Undo/redo backbone. Every new model MUST be registered here or undo corrupts state.
- **`game/views/action_views/general.py`** — Base `GameActionView` class all action endpoints inherit from.
- **`game/queries/current_action/`** — Determines which action the frontend should display (router for the entire action flow).
- **`game/decorators/`** — `@atomic_game_action` decorator wraps action views.
- **`frontend/src/api/types.ts`** — Auto-generated TypeScript types from OpenAPI schema. Never hand-edit.

### Action View Pattern

All action endpoints:
1. Inherit from `GameActionView`
2. Use `@atomic_game_action` decorator
3. Use `@extend_schema` for OpenAPI documentation (required)
4. Validate phase before mutating
5. Return updated game state via serializer

Game logs are written via factory functions in `game/serializers/logs/<faction>.py`, not via a `record_action()` call.

Routes use kebab-case: `/api/woodland-alliance/` not `/api/wa/`.

### Frontend Architecture

- **`src/api/types.ts`** — Generated types; always use these, never hardcode API types
- **`src/hooks/`** — TanStack Query hooks for all server state
- **`src/contexts/`** — `PlayerProvider`, `GameProvider` for high-level state
- **`src/components/playerboards/`** — Per-faction `[Faction]PlayerBoard.tsx`
- **`src/components/prompts/`** — Multi-step action UI driven by `current_action` response

The frontend is purely presentational — all game logic lives server-side.

### Undo/Redo System

Snapshots capture full game state before mutations. `game/utils/snapshot.py` serializes all related models to JSON; `game/utils/loader.py` restores them. **When adding any new model that stores game state, add it to snapshot.py immediately.**

## GameLog System

The GameLog system gives players a readable history of game actions — not a debug log. Each entry corresponds to a meaningful game event (a move, a build, a battle) and renders as a human-readable sentence in the UI.

### Data Model (`game/models/game_log.py`)

`GameLog` has a self-referential `parent` FK, producing a tree:

```
TURN
  └─ PHASE
      ├─ ACTION (e.g. CATS_MARCH)
      │    └─ MOVE (sub-action)
      └─ ACTION (e.g. BATTLE)
           ├─ DICE_ROLL
           └─ PIECE_REMOVAL
```

Key fields: `game`, `player` (optional FK), `log_type` (from `LogType` enum), `details` (JSONField), `parent` (self-FK, nullable).

`LogType` is a string enum with 66+ entries grouped by faction prefix: `CATS_*`, `BIRDS_*`, `WA_*`, `CROWS_*`, plus general types (`TURN`, `PHASE`, `MOVE`, `BATTLE`, etc.).

### Serializer Layer (`game/serializers/logs/`)

Each file handles one faction's log types:

| File | Covers |
|---|---|
| `general.py` | `TURN`, `PHASE`, `MOVE`, `BATTLE`, `CRAFT`, `DRAW`, `DISCARD`, `AMBUSH`, `DICE_ROLL`, `PIECE_REMOVAL` |
| `cats.py` | `CATS_*` log types |
| `birds.py` | `BIRDS_*` log types |
| `wa.py` | `WA_*` log types |
| `crows.py` | `CROWS_*` log types |
| `crafted_cards.py` | `CRAFTED_CARD_ACTION` (dispatches per card type internally) |
| `main.py` | `GameLogSerializer` — top-level serializer, dispatches `get_details()` to the above |

Each log type has:
1. A **`DetailsSerializer`** — validates the `details` JSON and exposes a `text` field (a `SerializerMethodField` returning a human-readable sentence).
2. A **factory function** `log_<action>(game, player, ..., parent=None) -> GameLog` — instantiates the serializer, calls `is_valid()`, then creates the `GameLog`.

`main.py`'s `GameLogSerializer.get_details()` dispatches to the correct serializer based on `log_type`. `get_children()` recursively serializes the `_children` list attached by the view.

**Privacy/redaction**: Some serializers define `get_redacted_details()` to hide sensitive fields (e.g. cards in hand, WA supporters, Crows plot types) from non-owning players. This is applied at serialization time in the view context.

### Log Creation (transaction layer)

Factory functions are imported from `game/serializers/logs/<faction>.py` and called inside transaction functions:

```python
from game.serializers.logs.cats import log_cats_march
from game.serializers.logs.general import log_move, get_current_phase_log

phase_log = get_current_phase_log(game, player)   # fetches the open PHASE log
march_log = log_cats_march(game, player, parent=phase_log)
log_move(game, player, origin, dest, count, parent=march_log)
```

`get_current_phase_log()` in `general.py` retrieves the most recent open phase log to use as parent. Always capture model references (e.g. a card object) **before** deleting them if you'll need them for logging.

### Log Consumption (frontend)

`GET /game/{game_id}/logs/` (in `game/views/gamestate_views/general.py`) fetches all logs for the game in one query, reconstructs the parent-child tree in memory by attaching `_children` lists, then serializes only root nodes — the recursive serializer walks the tree.

The frontend receives a nested JSON structure: each node has `id`, `parent_id`, `player_faction`, `log_type`, `details` (including the rendered `text` string), and `children`.

### Adding Logs for a New Action

1. **Add a `LogType` entry** in `game/models/game_log.py` (e.g. `NEW_FACTION_ACTION = "NEW_FACTION_ACTION"`).
2. **Create a `DetailsSerializer`** in `game/serializers/logs/<faction>.py` with fields matching what the transaction will pass, and a `get_text()` method returning the display string. Use `serializers.DictField()` for card objects, not `CardSerializer`.
3. **Create a factory function** `log_<action>(game, player, ..., parent=None)` in the same file — validate with the serializer, then call `GameLog.objects.create(...)`.
4. **Register in the dispatcher** — add an `elif log_type == LogType.<NEW_TYPE>:` branch in `GameLogSerializer.get_details()` in `main.py`.
5. **Call the factory** from the relevant transaction function, passing the phase log as `parent`.

### Adding Logs for a New Faction

Follow the same steps above, but create a new `game/serializers/logs/<faction>.py` file with all the faction's serializers and factories. Import and wire them into `main.py`'s dispatcher.

## Agent Workflows

The `.agent/workflows/` directory contains detailed step-by-step guides for common development tasks:

| File | When to use |
|---|---|
| `faction_overview.md` | Adding a new faction (start here) |
| `faction_models.md` | Database layer for a faction |
| `faction_serializers.md` | Serialization + GameStateSerializer integration |
| `faction_transactions.md` | Atomic game actions + phase hooks |
| `faction_views.md` | API endpoints + `get_current_action` wiring |
| `faction_frontend.md` | React components + PlayerBoard + Prompts |
| `action-views.md` | Action view structure and multi-step routing |
| `transactions.md` | Transaction function patterns |
| `snapshot_undo.md` | Undo/redo integration for new state |
| `testing.md` | Test setup with `GameSetupWithFactionsFactory` |
| `frontend.md` | React/TypeScript/Mantine patterns |
| `logging.md` | Game log models, serializers, factory methods |

`.agent/skills/` contains reusable skill definitions (git operations, openapi type generation, test execution).

## Environment

- Python venv: `F:/python/envs/.venv_web`
- Redis required for WebSocket support (run via Docker: `docker-compose up -d`)
- `.env.dev` / `.env.prod` for environment-specific config (`REDIS_HOST`, `DEBUG`, etc.)
- `pyrightconfig.json` — Pyright type checking in basic mode, Python 3.10
