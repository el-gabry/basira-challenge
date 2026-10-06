# Basira Competition UI Redesign

This redesign consumes the backend `experience` contract introduced after the runtime publication gate.

## What changed

- Rebuilt the landing screen around the warm Basira visual language shown in the competition mockup.
- Rebuilt the result screen as an evidence-first conversation workspace.
- Added one visible trust state driven by `response.experience.state`.
- Added publication, evidence/source count, semantic verification, and resolution indicators.
- Added explicit states for verified, grounded, limited, conflict, needs-more-evidence, regenerate, blocked, expert review, and abstention.
- Added a five-step verification trace based on `response.experience.trace`.
- Added evidence cards with source/reference/provenance and claim linkage.
- Added explicit weak-Hadith and Hadith-grade disagreement presentation using attributed `claim_type=hadith_grade` / `claim_value` evidence.
- Preserved conflicts rather than flattening them into one result.
- Kept technical IDs behind expandable trace details instead of showing raw enums in the primary UX.
- Added responsive/mobile behavior inspired by the supplied mockup.

## Important UX rule

The frontend does not promote `grounded` to `verified`, does not infer religious authority, does not recompute Hadith grades, and does not hide backend conflict/blocked states.

## Local validation

```bash
npm ci
npm run build
npm run lint
```

Set the API endpoint with `VITE_BASIRA_API_URL` if it is not `http://127.0.0.1:8000`.

## Trust Shield

Added a backend-truth-driven Trust Shield to the result card. It summarizes four presentation-safe layers without inventing religious authority: citation integrity, evidence obligations, preserved disagreement, and publication gate. Its center state follows `experience.state` / `experience.can_publish`, and semantic verification is shown exactly as returned by the API.
