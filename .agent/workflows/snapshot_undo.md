---
description: Guidelines for updating the Game State Snapshot and Undo system
---

# Game State Snapshot & Undo/Redo System

The game's Undo/Redo functionality relies on a **Snapshot/restore** mechanism.

- **Capture**: The entire game state (all relevant database models) is serialized into a JSON blob (a Checkpoint).
- **Restore**: To undo, we find the previous Checkpoint, delete _current_ game objects that didn't exist then, and restore/update the ones that did.

## 🚨 Critical Rule: All Game State Models Must Be Captured

If you add a **new Database Model** that stores game state (e.g., a new token type, a new card supply, a tracking table), you **MUST** add it to `game/utils/snapshot.py`.

### What happens if you forget?

1.  **Ghost Objects**: If an action creates a new object (e.g., `DominanceSupplyEntry`), and you undo that action, the system won't know this object "shouldn't exist" in the past state. It will fail to delete it.
2.  **Missing Data**: If you restore a game, the new objects won't be re-created, leading to corrupted game states.

---

## Implementation Checklist

When implementing a new feature involving new Models:

1.  **Open `game/utils/snapshot.py`**
2.  **Import the Model** at the top of the file.
3.  **Add to `get_all_game_objects(game)`**:
    - Locate the appropriate section (Global, Player-specific, etc.).
    - Add an `objects.extend(...)` call.
    - **Maintain Dependency Order**:
      - Parents MUST come before Children.
      - _Example_: `Player` must be saved before `HandEntry` (which FKs to Player).
      - _Example_: `Game` must be saved before `Player`.

### Code Example

```python
# game/utils/snapshot.py

# 1. Import
from game.models.new_feature import NewToken, NewSupply

def get_all_game_objects(game: Game):
    objects = []
    # ... existing global objects ...

    # 2. Add Global Objects (if related to Game)
    objects.extend(NewSupply.objects.filter(game=game))

    # ... existing player loop ...
    for player in players:
        # 3. Add Player Objects (if related to Player)
        objects.extend(NewToken.objects.filter(player=player))
```

---

## Testing Undo Compliance

Always verify that your new model participates in the undo system correctly.

**Test Pattern:**

1.  **Setup**: Create a game state with your Object (or just before creating it).
2.  **Snapshot**: Manually trigger a snapshot (or use a view that does it).
3.  **Mutate**: Delete the object, or Change its state, or Create it (if testing creation undo).
4.  **Restore**: Load the snapshot.
5.  **Verify**: Assert the object has returned to its original state.

```python
from game.utils.snapshot import capture_gamestate
from game.utils.loader import load_gamestate

def test_new_feature_undo(self):
    # 1. State A
    instance = NewModel.objects.create(player=self.player, value=10)

    # 2. Capture State A
    snapshot = capture_gamestate(self.game)

    # 3. Mutate -> State B
    instance.value = 20
    instance.save()
    # OR: instance.delete()

    # 4. Restore State A
    load_gamestate(self.game.id, snapshot)

    # 5. Verify State A returned
    instance.refresh_from_db()
    self.assertEqual(instance.value, 10)
```

## Troubleshooting

- **IntegrityError / ForeignKey Constraint Failed**:
  - You likely put the Child object _before_ the Parent object in the `get_all_game_objects` list. The loader tries to create the Child, but the Parent doesn't exist yet. Move the Parent higher in the list.
- **Object not deleting on Undo**:
  - You likely forgot to add the model to `get_all_game_objects`. The loader calculates the "diff" between DB and Snapshot; if the model isn't in the snapshot logic at all, it's ignored during the cull phase.
