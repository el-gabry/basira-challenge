# Basira

> **Governed Evidence & Publication for Islamic Knowledge**
> Competition Release — October 2026

**Live demo:** https://basiramuslim.com
**Repository:** https://github.com/el-gabry/basira-challenge
**Default branch:** `main`

---

## Why Basira

Basira is a governed evidence and publication system for high-stakes Islamic knowledge.

It is not designed to maximize answer rate. It is designed to prevent unsupported, incomplete, misattributed, or structurally unsafe religious claims from reaching publication.

The central engineering question is:

> **Can this specific claim be published from this specific governed evidence under this specific contract?**

Basira therefore separates:

```text
retrieved
    !=
verified
    !=
eligible
    !=
sufficient
    !=
publishable
```

A source being found does not make it answer-bearing.
A source passing an audit does not make it runtime-eligible.
A generated answer does not make it safe to display.

**Core invariant:**

> **PASS != ELIGIBLE**

---

## Architecture

```text
User Question
      |
      v
Query Understanding
      |
      v
Claim / Issue Planning
      |
      v
Governed Retrieval
      |
      v
Source Admission
      |
      v
Structural Evidence Acceptance
      |
      v
Claim <-> Evidence Relation
      |
      v
Sufficiency + Dependencies
      |
      v
Draft
      |
      v
Literal Integrity
      |
      v
Semantic Verification
      |
      v
Publication Firewall
      |
      +---- PASS --------> Publish
      +---- REGENERATE --> Retry safely
      +---- BLOCK -------> Fail closed
```

The final answer is built only from claims that survive the governed publication path.

---

## Trust Shield and Self-Hardening

Basira follows a strict principle:

> **Basira does not learn beliefs; it learns constraints.**

Confirmed system failures may become deterministic repair constraints, replay plans, and adversarial regression cases.

They may **never** become:

- Quran evidence
- Hadith evidence
- Tafsir evidence
- Fiqh evidence
- a religious ruling
- a source of religious truth

Learned memory can constrain future behavior, but it cannot supply religious authority.

This enables a deterministic **Trust-to-Learn / Self-Hardening** loop without allowing previous generated output to become evidence.

Relevant implementation:

```text
backend/src/basira/trust/
backend/data/trust/self-hardening/
backend/scripts/run_self_hardening_replay.py
backend/scripts/promote_self_hardening_constraints.py
```

---

## Fiqh: Issue-Complete Publication

For Fiqh, publication is:

> **issue-complete, not node-count-complete**

If a comparative issue contains multiple relevant madhhab positions, publication must preserve the complete issue structure and the structural children required for those positions.

A generic evidence-node limit must not silently truncate the religious issue.

---

## Bilingual Safety

Changing the UI language does not authorize Basira to relabel old religious evidence.

A language switch may require:

```text
new governed retrieval
    -> new verification
    -> new publication decision
```

The Trust Shield includes deterministic constraints for Quran, Tafsir, and Hadith language-switch failures.

---

# Quick Start for Judges

## Tested release environment

The competition release was built and tested with:

```text
Python 3.12
Node.js 22.23.3
npm 10.9.9
```

Recommended environment:

```text
Ubuntu / Linux / WSL2
```

---

## 1. Clone

```bash
git clone https://github.com/el-gabry/basira-challenge.git
cd basira-challenge
```

---

# Backend

## 2. Create the Python environment

```bash
cd backend

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

### API keys / secrets

**No private API key is required for the default competition judge path included in this release.**

Do not add real credentials, tokens, private keys, or `.env` secrets to the repository.

Governed source identity is controlled through repository passports, manifests, audits, and exact release artifacts rather than hidden credentials.

---

## 3. Start the backend

From `backend/`:

```bash
source .venv/bin/activate

python -m uvicorn basira.api.app:app \
  --host 127.0.0.1 \
  --port 8001
```

Backend:

```text
http://127.0.0.1:8001
```

Main public query endpoint:

```text
POST /api/v1/query
```

Evidence detail endpoint:

```text
GET /api/v1/evidence/{evidence_id}
```

---

## 4. Verify the API

```bash
curl -sS \
  -X POST \
  'http://127.0.0.1:8001/api/v1/query' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "question": "هل حديث إنما الأعمال بالنيات صحيح؟",
    "language": "ar"
  }'
```

A governed response can expose fields including:

```text
action
has_answer
answer
citations
claims
evidence
requirements
conflicts
integrity_report
experience
unavailable_domains
expert_review
```

A `BLOCK`, `REGENERATE`, `needs_more_evidence`, `conflict`, `expert_review`, or abstained response can be a valid Basira outcome when publication requirements are not satisfied.

---

# Frontend

## 5. Configure and install

Open another terminal from the repository root:

```bash
cd frontend
cp .env.example .env
npm ci
```

Default frontend environment:

```env
VITE_BASIRA_API_URL=http://127.0.0.1:8001
```

No frontend secret or API key is required.

---

## 6. Start the UI

```bash
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173
```

---

# Fast Competition QA

With the backend running:

```bash
cd frontend
npm run qa:domains
```

The real-API QA flow exercises the same public `/api/v1/query` path used by the UI.

Expected domain behavior includes:

- Quran question -> governed Quran evidence
- Tafsir question -> Quran anchor + Tafsir evidence
- Hadith question -> governed Hadith evidence
- Fiqh question -> governed Fiqh structure and publication rules

A blocked response is not automatically a failed smoke test; fail-closed behavior is part of the trust model.

---

## Focused backend release tests

From `backend/`:

```bash
source .venv/bin/activate

python -m pytest -q \
  tests/unit/answer/test_runtime_publication_gate.py \
  tests/unit/api/test_governed_public_runtime.py \
  tests/unit/competition/test_dorar_hadith_english_adapter.py \
  tests/unit/competition/test_dorar_fiqh_public_adapter.py \
  tests/unit/trust/test_self_hardening.py \
  tests/unit/trust/test_runtime_language_switch_causal_guards.py
```

Fiqh publication regression:

```bash
python -m pytest -q \
  tests/unit/answer/test_fiqh_group_complete_publication.py \
  tests/unit/answer/test_governed_fiqh_publication.py \
  tests/unit/competition/test_dorar_fiqh_public_adapter.py
```

Frontend production build:

```bash
cd frontend
npm run build
```

---

# Governed Sources

The competition release includes governed source paths for:

| Domain | Governed source |
|---|---|
| Quran | Quranpedia — Hafs |
| English Quran translation | Quranpedia — Sahih International |
| Tafsir | Governed Tafsir retrieval and admission |
| Hadith | Dorar al-Sunniyyah |
| Fiqh | Dorar al-Sunniyyah |

Source governance records live under:

```text
backend/data/competition/passports/
backend/data/competition/manifests/
backend/data/competition/audits/
```

Important examples include source IDs such as:

```text
quranpedia:mushaf:1
quranpedia:translation:en:13638
dorar:hadith:en
dorar:fiqh
```

Some release paths use exact captured source artifacts with governed SHA-256 identities.

These are **not generic caches** and must not be silently replaced with arbitrary downloaded content.

Raw discovery material is intentionally kept separate from answer-bearing authority.

---

# Publication Firewall

Basira may intentionally refuse publication for reasons such as:

- missing required evidence
- invalid canonical source identity
- source not explicitly runtime-eligible
- artifact hash mismatch
- unresolved source conflict
- unsafe language reuse
- incomplete Fiqh issue structure
- failed literal integrity
- failed semantic verification
- unresolved dependencies

This is expected behavior.

The safety objective is not:

> "Can the system produce an answer?"

It is:

> **"Can the system justify publishing this answer?"**

---

# Repository Map

```text
basira-challenge/
|
+-- backend/
|   +-- src/basira/
|   |   +-- api/             # public API and presentation
|   |   +-- competition/     # governed source adapters/admission
|   |   +-- evidence/        # evidence structures
|   |   +-- orchestration/   # requirements and dependencies
|   |   +-- reasoning/       # reasoning contracts
|   |   +-- retrieval/       # governed retrieval
|   |   +-- sources/         # source-specific integrations
|   |   +-- trust/           # Trust Shield / self-hardening
|   |   +-- verification/    # integrity and semantic checks
|   |
|   +-- data/
|   |   +-- competition/
|   |   |   +-- passports/
|   |   |   +-- manifests/
|   |   |   +-- audits/
|   |   +-- trust/self-hardening/
|   |
|   +-- scripts/
|   +-- tests/
|
+-- frontend/
    +-- src/
    +-- public/
    +-- package.json
    +-- .env.example
```

---

# Suggested Technical Review Path

For a fast review of the competition architecture, start with:

```text
backend/src/basira/api/service.py
backend/src/basira/api/presenter.py

backend/src/basira/competition/dorar_transport.py
backend/src/basira/competition/dorar_fiqh_adapter.py
backend/src/basira/competition/dorar_hadith_english_adapter.py
backend/src/basira/competition/quranpedia_translation_adapter.py

backend/src/basira/trust/runtime_constraints.py
backend/src/basira/trust/self_hardening.py

backend/tests/unit/answer/test_runtime_publication_gate.py
backend/tests/unit/api/test_governed_public_runtime.py
backend/tests/unit/trust/test_runtime_language_switch_causal_guards.py
```

---

## Competition Principle

> **We are not trying to build more Basira. We are making the Basira we already built impossible to bypass.**
