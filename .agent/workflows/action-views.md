---
description: Rules and examples for writing Action Views
---

Purpose:
Corresponds with a game action that can be taken. The view walks the user through the choices they need to make to do the game action. In the final step, the view will call a transaction function to modify the game state and respond with "completed" so that the client knows something has changed.

Inspect the base definition:
An Action View inherits from GameActionView (game\views\action_views\general.py)

Structure:

- Provides client with the first step of an action via get request. By default, will use self.first_step if it's static. If the first step may vary, calculate it in get request and return. If faction is static, provide it as self.faction. Else, calculate it in the get or post methods
- Post requests are routed to the appropriate method (route_post) and provide the next step or a "completed" message.
- validation methods to validate player and timing can be overridden and shoudl be used.
- generate_step and generate_completed_step methods provide interface for generating correct step structure.

Errors:
transactions should be called in try except blocks that raise the error as ValidationError (rest_framework)

payload_details:

- clearings are communicated with clearing_number
- cards are communicated with their name and looked up in CardsEP textchoice
- factions/players are communicated via the faction name and looked up in Faction textchoice
- in geenral, primary keys are not used in action views.

Inspect examples:
game\views\action_views\battle.py
game\views\action_views\wa\daylight.py
