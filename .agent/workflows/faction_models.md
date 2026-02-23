---
description: Workflow for defining faction Models and Events
---

# Faction Models & Events Workflow

When adding the database layer for a new faction, perform the following steps:

1. **Create the App Directory**: Under `game/models/`, create a new folder named for the faction.
2. **Define Buildings and Tokens**:
   - Create `buildings.py` containing models that inherit from a standard `Building` class or `Model`. Include standard fields (e.g., clearing ID, built status).
   - Create `tokens.py` for movable/static tokens specific to the faction.
3. **Define the Turn State**:
   - Create `turn.py`. The `[Faction]Turn` model tracks standard phases (Birdsong, Daylight, Evening), action points/counts, crafted cards, and temporary flags specifically for that turn.
   - Link the Turn model logically back to the central `Game` or `Player`.
4. **Define Events (Crucial for Interruptions)**:
   - Faction mechanics often require interrupting the main game loop or requiring responses from _other_ players on _your_ turn (e.g., asking for Ambush cards, taking hits, Woodland Alliance outrage).
   - If the faction has mechanics like this, define `Event` models (e.g., `game/models/events/[mechanic]_event.py`).
   - The event model should store the state of the interruption (who triggered it, who needs to respond, what data is pending).
5. **Setup Models**: Include any pre-game setup requirements in a `setup.py` file or hook into the core `game_setup.py`.

_Tip for AI_: Always verify model relations (OneToOne vs ForeignKey) and ensure `on_delete` parameters are appropriately set to avoid orphans.
