# Todo List
- [ ] Frontend typing: player boards should use types
- [x] Critical Feature: Crafted items
    - [x] Frontend: display of crafted items box
    - [x] Backend: endpoint to get crafted items, with exhausted or not status
- [x] Bug, WA, Frontend: Bases are displaying on player board whether or not they are on the map (should not be on player board if on the map)
- [ ] 
- [ ] Cats turn queries
  - [ ] add queries to validate timing, turn
  - [ ] refactor transactions to use these validators 

- [ ] review transaction file split refactors. code is in strange places
- [ ] review all transactions to use validators
  - [ ] perhaps we can make a timing decorator. maybe one to cross check that args are part of the same game too.

Game Lobby:

- [x] Reduce Unnessecary API calls
  - [x] During setup: calls to turn-info
  - [x] Fewer than all factions: calls to player-info for factions not in game

- [x] More instructions for the player
  - [x] actions prompts: tooltips on the option buttons providing relevant info
  - [x] Playerboards: as much info as actual playerbaords. use tooltips to conserve space
  - [x] tooltips for board components.

- [ ] Appearance
  - [ ] icons for warriors, tokens, buildings
  - [x] better way to display token counts for wood

- [x] Revealed Cards Functionality
  - [x] Endpoint and serializer to package revealed cards and the events that reveal them
  - [x] Frontend display of revealed cards
- [x] Discard Pile: Frontend display
- [x] Items: Frontend display and backend implementation
- [x] Game Log
- [x] Custom Errors

- [ ] New Factions
  - [ ] Moles

- [ ] owners can delete games

- [x] Undo/checkpoints/replay
- [x] add ruins to the board and the frontend display
- [x] Battle
- [x] Dominance
- [x] Endgame
- [x] Crafted Cards
- [x] Game Browser
- [x] Login Screen
- [ ] Manual refresh button within game.
