# Error Classification Patterns by Faction

This guide shows the patterns used for each faction's error classification to guide completion of remaining work.

## CROWS (Complete Reference)

### Pattern 1: Validation Failures → UnavailableActionError
```python
if not validate_turn(player):           # Wrong player/faction
    raise UnavailableActionError(...)
if daylight.step != ACTIONS:            # Wrong step
    raise UnavailableActionError(...)
if actions_remaining <= 0:              # Resources exhausted
    raise UnavailableActionError(...)
```

### Pattern 2: Rule Violations → IllegalActionError
```python
if PlotToken.objects.filter(clearing=clearing).exists():
    raise IllegalActionError("Clearing already has a plot token")
if warrior_count_in_clearing(player, clearing) < cost:
    raise IllegalActionError("Not enough warriors...")
if plot_token is None:
    raise IllegalActionError("No plot token of type X in supply")
```

### Pattern 3: Data Integrity → InternalGameError
```python
if crow_turn is None:  # Turn should exist
    raise InternalGameError("No turns found...")
```

## BIRDS (Complete Reference)

### Decree System (decree_entry)
```python
if decree_entry.fulfilled:
    raise IllegalActionError("This decree card has already been used")
if decree_entry.column != DecreeEntry.Column.RECRUIT:
    raise IllegalActionError("Decree card is not in the recruit column")
if decree_suit != clearing.suit and decree_suit != Suit.WILD:
    raise IllegalActionError("Decree suit does not match roost suit")
```

### Resource Checks (Roosts, Warriors, Cards)
```python
if clearing is None:  # Roost data
    raise IllegalActionError("Roost is not on the board")
if get_all_unused_roosts(player).count() == 0:
    raise UnavailableActionError("No roosts available")  # Resources exhausted
if not validate_crafting_pieces_satisfy_requirements(...):
    raise IllegalActionError("Not enough crafting pieces...")
```

### Game State (Emergency Roost, Decree Count)
```python
if birdsong.cards_added_to_decree > 2:
    raise InternalGameError("More than two cards already added!")
if birdsong.bird_card_added_to_decree:
    raise IllegalActionError("Bird card already added to decree")
```

### Clearing/Game Checks
```python
if player.game != clearing.game:
    raise IllegalActionError("Clearings are not in the same game...")
if determine_clearing_rule(clearing) != player:
    raise IllegalActionError("Player does not rule this clearing")
```

### Hand Size / Evening
```python
if get_player_hand_size(player) <= 5:
    raise UnavailableActionError("Player must have more than 5 cards to discard")
```

## CATS (Apply Same Patterns)

### Wood System (Similar to Decree)
- Sawmill not placed → IllegalActionError
- Sawmill already used → IllegalActionError
- Not owned by player → IllegalActionError
- No wood tokens left → InternalGameError (supply issue)

### Building Validation (Similar to Roosts)
- All objects same game → IllegalActionError
- All tokens same player → IllegalActionError
- Duplicate tokens → IllegalActionError
- No building in supply → InternalGameError
- Not enough wood → IllegalActionError
- Not connected → IllegalActionError

### Actions/Timing
- No actions remaining → UnavailableActionError
- Wrong phase → UnavailableActionError (handled by validate_phase)
- Not Daylight phase → UnavailableActionError

## WA (Apply Same Patterns)

### Sympathy/Officer System (Similar to Decree)
- Already used → IllegalActionError
- Not in right column → IllegalActionError
- Suit mismatch → IllegalActionError

### Base/Officer Management
- No base available → InternalGameError
- Officer already placed → IllegalActionError
- Not enough supporters → IllegalActionError

### Resource Checks
- No clearing available → IllegalActionError
- Not enough warriors → IllegalActionError
- Card not in hand → IllegalActionError

## General Rules

### Always UnavailableActionError
- Wrong player's turn
- Wrong phase (validate_phase catches this)
- Wrong step (validate_step catches this)
- "No X remaining" (where X is a resource that should exist)
- "Must have X to do Y" (precondition not met)

### Always IllegalActionError
- "Already used/placed"
- "Not owned by/available to player"
- "Suit/type mismatch"
- "Not enough X" (where X is a resource)
- "Not connected/adjacent"
- "No Y at X" (resource at location check)
- "Does not rule/control"
- Duplicate/conflicting state

### Always InternalGameError
- "No X found" (for X that should exist)
- "X already/still exists" (when shouldn't)
- "State corruption" scenarios
- Piece/wood supply exhausted unexpectedly

## Quick Classification Checklist

When categorizing a new error:

1. **What triggered the error?**
   - Wrong player or turn → UnavailableActionError
   - Resource exhausted/unavailable → UnavailableActionError
   
2. **Is the player/timing correct?**
   - Yes, but rule forbids → IllegalActionError
   - No → UnavailableActionError
   
3. **Is this a data integrity issue?**
   - Missing record that should exist → InternalGameError
   - State that shouldn't be possible → InternalGameError
