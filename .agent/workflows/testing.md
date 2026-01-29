---
description: Rules for Testing
---

Setup:
Use factories in tests/my_factories.py. May be best to start with the full setup provided by GameSetupWithFactionsFactory

For view tests, use RootGameClient in game/tests/client.py

example:
game\tests\test_wa_turn_flow.py
game\tests\test_eyrie_emigre.py

to test:
C:\Users\Mati\miniconda3\condabin\conda.bat run -n spyderweb python manage.py test tests.test_wa_turn_flow
