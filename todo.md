# Todo List

## Frontend
- [ ] Frontend typing: 
  - [x] player boards should use types
  - [ ] look for uses of ": any" and see if there is a schema generated type instead
- [ ] Animations (movement, placement)
- [ ] Choice Highlighting
  - [ ] clearings
  - [ ] cards
- [ ] Appearance
  - [ ] icons for warriors, tokens, buildings
  - [x] better way to display token counts for wood

## Refactoring
- [ ] Cats turn queries
  - [ ] add queries to validate timing, turn
  - [ ] refactor transactions to use these validators 

- [ ] Use SubGameActionViews to split monoliths for cats, WA, crows when they have choices between actions
- [ ] Make use of "redirect" to simplify the crafted card action selection 

- [ ] review transaction file split refactors. code is in strange places
- [ ] review all transactions to use validators
  - [ ] perhaps we can make a timing decorator. maybe one to cross check that args are part of the same game too.


## Factions
- [ ] New Factions
  - [x] Moles
  - [ ] Rats
  - [ ] Lizards
  - [ ] Otters
  - [ ] Badgers
  - [ ] VB
  - [ ] Frogs
  - [ ] Bats
  - [ ] Knaves

## Features
- [ ] owners can delete games

## Completed

- [x] Undo/checkpoints/replay
- [x] add ruins to the board and the frontend display
- [x] Battle
- [x] Dominance
- [x] Endgame
- [x] Crafted Cards
- [x] Game Browser
- [x] Login Screen
- [x] Critical Feature: Crafted items
- [x] Bug, WA, Frontend: Bases are displaying on player board whether or not they are on the map
- [x] Reduce Unnecessary API calls
- [x] More instructions for the player
- [x] Revealed Cards Functionality
- [x] Discard Pile: Frontend display
- [x] Items: Frontend display and backend implementation
- [x] Game Log
- [x] Custom Errors
