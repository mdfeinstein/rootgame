---
description: Rules for frontend
---

Frontend is React with typescript.
Use Mantine Components.
location:
frontend/src

folders:

- hooks: mediate the interaction with backend, usually using react query. **ALWAYS tag query return types with schema-generated types from `../api/types`.**
- contexts: makes use of hooks to provide high level information. Use schema types for data structures.
- components: Use Mantine for UI. Use `labelToRoute` from `factionUtils` for any faction-specific URL generation.

## Best Practices
- **Schema Types**: Use `components["schemas"][...]` from `frontend/src/api/types.ts` for all data models.
- **Faction Slugs**: API routes should use kebab-case faction labels (e.g., `woodland-alliance` instead of `wa`). Use `labelToRoute(faction.label)` for consistency.
- **Loading State**: The app uses a `GlobalCursor` component. Favor TanStack Query for data fetching so the global progress cursor activates automatically.
frontend\src\components\cards\Hand.tsx
frontend\src\components\board\Prompter.tsx
