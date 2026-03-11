---
name: Generate OpenAPI Types
description: A skill to regenerate the TypeScript API contract definitions using the Django backend drf-spectacular schema.
---

# Generate OpenAPI Types

This skill provides the standard workflow for regenerating the TypeScript frontend API types from the Django backend definitions. This should be run anytime a serializer or a django view is updated in a way that would alter the API contract.

## Prerequisites

- You must activate the python virtual environment (if one exists) before running these commands.
- `drf-spectacular` must be installed in the Django backend.
- `openapi-typescript` must be installed in the React frontend.

## The Generation Script

A single command handles both generating the backend schema and building the frontend typescript bindings.

Inside the frontend directory, there is an `npm run generate-types` script. To execute the end-to-end update:

```bash
# Enter the frontend folder and run the generation script
cd frontend
npm run generate-types
```

## How It Works

The script runs the following sequence of commands under the hood:

1. `python manage.py spectacular --file schema.yml`
   - This scans the django project's views and `@extend_schema` decorators to emit a `schema.yml` openAPI document in the project root.
2. `npx openapi-typescript ../schema.yml -o src/api/types.ts`
   - This parses the generated YAML OpenApi specification and builds TypeScript definitions out of the components and routes, outputting them directly into the React `src/api/types.ts` bundle.

## Validating Types

After regeneration, it is highly recommended to run the TypeScript compiler to ensure the newly generated API contract has not broken any existing frontend code.

```bash
cd frontend
npx tsc -b
```

Review and manually address any resulting TypeScript compilation errors by tracking down the React Components breaking the new contract.
