Table of Contents

- [Introduction](#introduction)
  - [Tech Stack and design philosophy](#tech-stack-and-design-philosophy)
    - [Project Structure](#project-structure)
    - [Action Flow](#action-flow)
  - [State of the Project](#state-of-the-project)

# Introduction

This is a web-based adaptation of the board game Root by Cole Wehrle. Root is a complex board game with many different factions, each with their own unique rules and mechanics.

The eventual aim is to implement all current factions and one day, maybe fan-made factions as well.

## Tech Stack and design philosophy

This project is built using Python 3.10 and Django 4.0. The frontend is built using React 18 using Tanstack Query for interaction with the API.
<br>
Eventually, django-channels backed by Redis will be used to allow for real-time updates.
<br>
The project is designed such that the server handles all game logic and the frontend handles all user interaction. The frontend will not be responsible for any game logic, as that would mean duplicating the logic in the frontend and backend in different languages, which is hard to maintain and likely to lead to bugs and inconsistencies.

### Project Structure

<ul>
<li>The database will hold all state for the game, which is defined in the models module.</li>
<li>The queries module holds logic that queries the database, but does not modify it.</li>
<li>The transactions module holds logic that modifies the database, checking for game state using queries.</li>
<li> views provide gamestate information and post methods to submit moves. These moves are validated (with queries) and then executed using transactions.</li>
</ul>

### Action Flow

<ul>
<li>The client requests the endpoint corresponding to the current action step, which may be a step of a player's turn, or resolving their part of an event like battle.</li>

<li>
That endpoint will return a JSON object with the next action step to take and the data the client should send.</li>
<li>
When the user interacts with the UI, the client sends a POST request to the endpoint corresponding to the action step. If it is a multistep process, the server will validate the first step and send back the next one, or provide the error if the first step is invalid. This continues until the server sends back a "completed" step.
</li>
<li>
If the server sends back a "completed" step, the client will know that the action is complete. The client again requests the endpoint corresponding to the next action step, and the cycle repeats.
<li>
Validation of timing and player making requests is handled by the custom GameActionView base class. Anything corresponding to a player action is subclassed from this class.
</li>
</ul>

## State of the Project

Currently, 3 factions have been fully implemented: Cats, Birds, and Woodland Alliance.
Cards can be crafted. Those with passive effects are checked for and handled in the appropriate business logic. Those with active effects also work, launching events if the action has a narrow timing window or are simply made available when usable if they have a broader timing window.

Not yet implemented:

- endgame scoring and win checks
- game browser in the front end to create, join, and switch between games
- login screen
- undo functionality (partially done)

### Frontend

The frontend is minimal, but will be augmented over time. Components such as cards and clearings are clickable and can be used to submit actions to the server.

#### MAP

Clearings are clickable for actions that require a clearing to be selected.

![Screenshot of the frontend](images/map_1-29-2026.png)

#### Action Prompter

Displays the current action step and the faction that needs to take an action. If options have been provided, they will be displayed as buttons that submit to the server.

![Screenshot of the frontend](images/prompter.png)

#### Cards In Hand

Mousing over the hand of cards will expand them, and the hovered card will be brought to the front. Clicking a card will submit it to the server if relevant.

![Screenshot of the frontend](images/cards.png)

#### Player Badges

Player badges with facton, name, crafted cards, and score. Clicking a badge will show that player's board. Clicking crafted cards will display the crafted cards.
![Screenshot of the frontend](images/player_icons.png)

#### Player Boards

When a piece on a track covers information, that info is displayed in a tooltip.
![Screenshot of the frontend](images/cat_board.png)
![Screenshot of the frontend](images/bird_board.png)
Decree actions have a checkbox to indicate if the decree is used.
![Screenshot of the frontend](images/wa_board.png)
Only the woodland alliance player can see the details of their supporter stack.
