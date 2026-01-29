---
description: Rules for frontend
---

Frontend is React with typescript.
Use Mantine Components.
location:
frontend/src

folders:

- hooks: mediate the interaction with backend, usually using react query.
- contexts: makes use of hooks to provide high level information to any component that may need it.
- components

inspect examples:
frontend\src\components\cards\Hand.tsx
frontend\src\components\board\Prompter.tsx
