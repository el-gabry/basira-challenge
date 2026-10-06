# Trust Shield test report

Implemented the Trust Shield inside the result card.

## Checks completed in the artifact environment

- TypeScript/TSX syntax transpilation: passed for `App.tsx`, `basira.ts`, `BasiraLogo.tsx`, and `main.tsx`.
- CSS parse validation with `tinycss2`: passed with zero parse errors.
- Source assertions: Trust Shield replaces the old trust strip and remains driven by backend response fields.
- The shield uses only existing backend truth: literal citation integrity, requirement resolution, conflicts, semantic verification, and `experience.can_publish`.
- Hadith weak/conflict UI remains intact and is not re-graded by the frontend.
- Desktop/tablet/mobile responsive rules are included.

## Full npm build note

A full `npm ci` could not complete in the artifact container because package fetching timed out. A partial install therefore caused `vite/client` and `node` type-definition lookup errors. This is an environment/dependency-install issue, not a TypeScript syntax error in the Trust Shield changes.

Run locally from the project folder:

```bash
npm install
npm run build
npm run lint
npm run dev -- --host 0.0.0.0
```
