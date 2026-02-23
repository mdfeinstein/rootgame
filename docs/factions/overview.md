# Faction Implementation Overview

Adding a new faction to the game requires integrating it across several layers of the application, from the backend database models to the frontend React components. This document serves as a guide for understanding how the existing factions (Cats, Birds, Woodland Alliance) are structured, and what is needed to implement a new one.

The architecture is divided into the following key components:

1. **[Models](models.md)**: Defines the database tables for the faction's specific pieces (buildings, tokens) and turn state.
2. **[Serializers](serializers.md)**: Handles converting the Django models into JSON for the frontend, and parses incoming data.
3. **[Transactions & Game Loop](transactions.md)**: The core game logic. Contains the functions that execute specific faction actions and hook into the main game event loop.
4. **[Views (Endpoints)](views.md)**: Django REST Framework views that receive player actions from the frontend and trigger transactions.
5. **[Frontend](frontend.md)**: React components for the player board, specific piece rendering, and interactive prompts.

### Broad Strokes of Implementing a New Faction

1. **Database Schema**: Create the necessary models for the faction's pieces (e.g., `[Faction]Building`, `[Faction]Token`) and its turn state (`[Faction]Turn`).
2. **Game State Serialization**: Create a `[faction]_serializers.py` file to serialize the faction's specific models and add them to the main `GameStateSerializer`.
3. **Game Setup Logic**: Add the faction to the initial setup scripts and define its starting pieces/locations.
4. **Action Transactions**: Write the `game/transactions/[faction].py` file containing all the legal moves and actions for the faction.
5. **Turn Phase Management**: Integrate the faction's specific Birdsong, Daylight, and Evening phases into the overarching game loop via transactions.
6. **API Endpoints**: Create the action views in `game/views/action_views/[faction]/` allowing the frontend to trigger the faction's transactions.
7. **Frontend UI**: Create the `[Faction]PlayerBoard.tsx` and ensure any unique pieces or mechanics have corresponding visual representations on the board and in the interactive prompts.

---

_For deeply technical guidelines/rules on specific areas, refer to the slash commands in the codebase (e.g., `/frontend`, `/transactions`, etc.)._
