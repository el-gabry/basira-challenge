# Basira Competition Decision Log

Every major architectural or research decision is recorded here.

---

## D-001 — Preserve, do not hide, prior work

Prior implementation is frozen as an explicit Git baseline instead of
being presented as competition-period work.

Reason:
Scientific and competition auditability.

---

## D-002 — New evaluation namespace

Historical evaluation files remain part of the imported baseline.

All competition-period baselines, experiments and results are stored
under:

evaluation/competition/

Reason:
Prevent accidental mixing of pre-competition and competition metrics.

---

## D-003 — Continuous criticism

No feature is kept because it sounds innovative.

Each major branch must define:

- exact problem;
- novelty hypothesis;
- failure modes;
- measurable success criterion;
- adversarial test;
- kill condition.
