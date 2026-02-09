# Todo List

Game Lobby:

- [ ] owners can delete games

- [x] Undo/checkpoints/replay
  - [x] Basic functionality
  - [x] some actions (like Battle) are not undoable
- [x] add ruins to the board and the frontend display
- [ ] Battle:
  - [ ] Choosing Hits (views, transactions, url)
- [ ] Dominance:
  - [ ] Dominance discards go to special pool
  - [ ] Player can select dominance when >=10 points
  - [ ] Players can swap from dominance cards in pool
  - [ ] Player no longer has a "score" and can't win by getting to 30 points
  - [ ] Check for dominance condition at beginning of turn
  - [ ] Frontend display of available dominances and any actively chosen dominance cards
- [ ] Endgame
  - [x] check for win when scoring
  - [ ] frontend display game over state
- [x] Crafted Cards
  - [x] Backend Support
  - [x] Frontend
    - [x] Display crafted cards in crafting area
    - [x] Display usable crafted cards on main screen. Make clickable to use. (will replace contents of prompter)
- [x] Game Browser
  - [x] Display games user is in
  - [x] Display games user can join
  - [x] Create Game option
  - [x] Click to go to game screen
- [x] Login Screen
- [ ] Manual refresh button within game.
- [ ] Employ custom errors
- [ ] Game Log
- [ ] Known Business Logic Bugs
  - [x] Woodland Alliance:
    - [x] Supporter stack limits not enforced
  - [x] Crafted Cards:
    - [x] Swap Meet: Initial card grab should not be undoable.
    - [x] Enforce unique named cards in crafting entry (i.e., no two swap meets for single player allowed)
  - [x] Cats:
    - [x] Keep does not prevent other faction piece placements (make general transaction for placing a piece that checks for keep, use in piece placement logic)
- [ ] Known Frontend Bugs
  - [ ] hand not updating when cards are spent (query should refetch. backend probably not always sending completed step.)
    - [x] Fixed for WA crafting

Testing

- [ ] organize tests (transaction level, view level)
- [ ] add tests for all transactions
- [ ] add tests for all views
