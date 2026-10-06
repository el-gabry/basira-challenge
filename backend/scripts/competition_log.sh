#!/usr/bin/env bash
set -euo pipefail

STEP="${1:?STEP required}"
TITLE="${2:?TITLE required}"

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

LOG="docs/competition/BUILD_LOG.md"

TS="$(date --iso-8601=seconds)"
BRANCH="$(git branch --show-current)"
HEAD="$(git rev-parse --short HEAD)"

cat >> "$LOG" <<EOF2

---

## ${STEP} — ${TITLE}

**Timestamp:** ${TS}
**Branch:** \`${BRANCH}\`
**Starting HEAD:** \`${HEAD}\`

### Objective

TODO

### Novelty hypothesis

TODO

### Pre-mortem / critique

TODO

### Implementation

TODO

### Adversarial checks

TODO

### Evaluation / metrics

TODO

### Failure analysis

TODO

### Result

TODO

### Decision

KEEP / MODIFY / KILL
EOF2

echo "✅ ${STEP} added to ${LOG}"
