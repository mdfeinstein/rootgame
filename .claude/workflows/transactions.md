---
description: Rules and examples for writing transactions.
---

Transactions are functions that modify the database, usually decorated with @transaction.atomic. Transactions live in the game/transactions folder

Arguments are preferentially model instances, or perhaps enum values, rather than primary keys or other identifiers.

To read from the database and make common calculations, transactions should use queries from game/queries wherever possible, so as to centralize logic and improve readability. If no query exists and database querying is relatively easy, transaction functions may write their own query logic. If the logic is more involved, consider writing a query function for the transaction function so that the logic can be used in the future.

Also, check for existing transaction functions to compose into the desired functionality.

Transaction functions should typically validate conditions before making database changes. For instance, we should check that the current game phase or event aligns with the transaction being called, or that the player is in the same game as other objects being affected. These checks should often be handled in a query, since the associated Action Views will likely need to make the same checks.
