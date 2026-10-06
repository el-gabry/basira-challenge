# Basira Competition Build Log

This document is updated continuously during the competition.

The final submission documentation will be generated from this log,
Git history, decisions, experiments, and evaluation results.

---

## STEP 00 — Competition baseline boundary

**Timestamp:** 2026-10-03T23:20:26-07:00

### Objective

Create an auditable boundary between prior Basira R&D and
competition-period development.

### Starting source

- Old branch: `eval/shamela-dense-holdout-once`
- Old SHA: `aac63608564e603654b1d0793897249856e41903`

### Competition baseline

- Commit: `59be46136f68e6ee2e148f5ef6c69e18702d31c0`
- Tag: `competition-import-baseline`

### Important classification

Existing retrieval benchmarks, dense experiments, rescue experiments
and historical evaluation JSON files are PRE-COMPETITION results.

They are not counted as competition improvements.

### Result

PASS.

### Decision

KEEP.

---

## STEP 01 — Baseline runtime health

**Timestamp:** 2026-10-03T23:22:04-07:00

### Objective

Verify that the imported pre-competition implementation runs
reproducibly before competition behavior is changed.

### Test result

- pytest exit code: `0`
- runtime seconds: `2`

### Interpretation

This establishes regression health only.

It does not establish competition-period performance for retrieval,
source eligibility, evidence sufficiency, semantic claim support,
Quran integrity, false-consensus detection, disagreement preservation,
or safe failure learning.

### Decision

KEEP — baseline runtime is healthy.

---

## STEP 02 — Freeze measurable competition baseline

**Timestamp:** 2026-10-03T23:22:04-07:00
**Branch:** `feat/competition-core`
**Starting HEAD:** `b9adaa1`

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

---

## STEP 02A — Audit imported core before competition changes

**Timestamp:** 2026-10-03T23:24:31-07:00
**Branch:** `feat/competition-core`
**Starting HEAD:** `b2912ef`

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

### STEP 02A audit result

**Completed:** 2026-10-03T23:24:31-07:00

#### Objective

Determine exactly which competition-core capabilities already exist in
the imported baseline before implementing new architecture.

#### Scope inspected

- religious reasoning contracts;
- religious routing;
- evidence decisions;
- retrieval sufficiency;
- source policy;
- API orchestration;
- structured answer contracts;
- claim-source integrity;
- Quran integrity;
- Quran verification.

#### Targeted test result

- exit code: `0`
- runtime: `0s`

#### Artifact

`docs/competition/CORE_BASELINE_AUDIT.md`

#### Critique

Existing functionality is not automatically treated as a competition
innovation.

Competition work must identify a measurable delta over this imported
baseline instead of reimplementing capabilities that already exist.

#### Decision

KEEP baseline core and build competition deltas on top.

---

## STEP 02B — Freeze competition benchmark before innovation

**Timestamp:** 2026-10-03T23:28:00-07:00
**Branch:** `feat/competition-core`
**Starting HEAD:** `6021391`

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

### STEP 02B result

**Completed:** 2026-10-03T23:28:00-07:00

#### Frozen benchmark

- ID: `basira-trust-core-v1`
- Cases: `10`
- SHA256: `222c6ef8cb9a8fc115f652ae1e7fd5b4b8d9572e5bb1be6a5e85681d34853cba`

#### Frozen before innovation

The case set was committed before implementing the new competition
trust architecture.

#### Baseline gaps targeted

- official A/B/C/D sensitivity;
- explicit source eligibility;
- witness-aware Quran attestation;
- semantic claim/evidence verification;
- false-consensus detection;
- failure certification;
- pluralism-safe learning.

#### Scientific rule

Future improvements are measured against this frozen benchmark.

Benchmark V1 must not be edited after the freeze tag.

---

## STEP 02C — Run pre-innovation baseline on frozen benchmark

**Timestamp:** 2026-10-03T23:32:40-07:00
**Branch:** `feat/competition-core`
**Starting HEAD:** `9966060`

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

### STEP 02C result

**Completed:** 2026-10-03T23:32:48-07:00

#### Phase

`PRE_INNOVATION`

#### Evaluator

`scripts/evaluate_competition_trust_v1.py`

#### Frozen benchmark

`basira-trust-core-v1`

Benchmark SHA256:

`222c6ef8cb9a8fc115f652ae1e7fd5b4b8d9572e5bb1be6a5e85681d34853cba`

#### Result artifact

`evaluation/competition/results/trust_core_v1_preinnovation.json`

Result SHA256:

`7d5bb65430d77861b1b87a65d73b329c313682a09592e471920b0450c1fe951b`

Runtime:

`8s`

#### Interpretation

The baseline evaluator explicitly separates:

- PASS;
- FAIL;
- NOT_IMPLEMENTED;
- NOT_EXECUTED.

No missing competition capability is credited as success.

Existing literal/structural claim integrity is not counted as semantic
entailment.

#### Next decision

Begin the first competition capability branch only after preserving
this result.

---

## STEP 03 — Build official competition source foundation

**Timestamp:** 2026-10-03T23:38:08-07:00
**Branch:** `feat/official-source-foundation`
**Starting HEAD:** `b6b1234`

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

### STEP 03 result — Official source foundation

#### Competition source rule

Legacy-source eligibility is not inherited.

Every competition source must independently pass:

1. official reference eligibility;
2. source identity verification;
3. exact artifact/version identification;
4. cryptographic integrity;
5. structural audit;
6. optional cross-source attestation;
7. explicit runtime admission.

#### Important design choice

Source verification is itself part of Basira's trust architecture.

The system verifies not only claims against evidence, but also the
evidence artifact before allowing it to support claims.

#### Shamela rule

Admission is per governed book/artifact.

The existence of a work inside a Shamela distribution does not grant
automatic competition eligibility.

#### Decision

KEEP.

---

## STEP 04 — Audit and admit Quranpedia Hafs competition witness

**Timestamp:** 2026-10-03T23:41:21-07:00
**Branch:** `feat/official-source-foundation`
**Starting HEAD:** `a740290`

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

### STEP 04E — Provider metadata schema drift

The verified Quranpedia mushaf-index artifact did not encode witness
identity using the initially assumed field semantics.

Observed:

- `rawi.name` identifies Hafs;
- `rawi.full_name` is the narrator's biographical name;
- qiraa identity is exposed through `qiraa.short_name`
  in the current provider schema.

The source was correctly kept quarantined instead of inferring
"Hafs from Asim" from incomplete assumptions.

The witness resolver was changed to normalize provider metadata
semantically rather than depend on one historical JSON field name.

This is treated as source-schema drift and preserved in the
competition audit trail.

### STEP 04G — Hafs reference semantics corrected

A previous audit hypothesis treated `number_in_hafs` as a
Quran-global integer in the range `1..6236`.

The provider data disproved that hypothesis.

Corpus-wide inspection established:

- 6236 Quran ayah records;
- `number_in_hafs` is an array;
- for Mushaf 1 every array has exactly one item;
- the value is surah-local;
- for every Hafs ayah, `number_in_hafs[0] == ayah.number`;
- `(surah_id, number_in_hafs[0])` produces exactly 6236
  unique Hafs references.

The governed auditor now models Quran references as structured
`(surah, ayah)` identities instead of incorrectly flattening them
into one Quran-global sequence.

This failure was caught before source admission.

### STEP 04 FINAL — First primary competition source governed

**Source:** Quranpedia Hafs
**Release:** `2026-10-04`

Verified:

- official competition eligibility;
- exact provider artifact identity;
- exact SHA-256;
- provider metadata artifact;
- Hafs narrator identity;
- Asim qiraa identity;
- 114 surahs;
- 6236 structured Quran references;
- non-empty Quran text;
- surah-local Hafs reference semantics.

Explicitly unresolved:

- independent rasm attestation;
- independent dabt attestation;
- independent cross-source attestation.

Runtime status:

`ELIGIBLE`

Update policy:

`candidate → verify → promote`

A new provider release MUST NOT automatically replace the current
governed snapshot.

---

## STEP 05A — Add update-aware source governance

**Timestamp:** 2026-10-04T00:13:37-07:00
**Branch:** `feat/source-update-sentinel`
**Starting HEAD:** `2aab92b`

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

### STEP 05A result — Update-aware source governance

Basira now treats governed religious evidence as a versioned
evidence supply chain.

A newly observed provider release is never promoted automatically.

States include:

- CURRENT;
- UPDATE_AVAILABLE;
- SAME_RELEASE_ARTIFACT_DRIFT;
- PROVIDER_UNAVAILABLE.

When an update is detected:

current governed snapshot
→ remains active

new provider release
→ becomes candidate
→ artifact verification
→ structural/schema audit
→ applicable attestation
→ promotion decision.

If the provider is unavailable, Basira retains the last governed
eligible snapshot.

If the same provider release suddenly exposes a different artifact
SHA-256, Basira quarantines the candidate rather than silently
replacing the trusted artifact.

### STEP 05B — Release ordering / rollback awareness

The first live Source Update Sentinel probe observed:

- governed Quranpedia release: `2026-10-04`;
- provider-observed release: `2026-10-03`.

The initial sentinel incorrectly classified any different release ID
as `UPDATE_AVAILABLE`.

This was rejected as unsafe.

A different release identifier does not imply a newer release.

The source trust model now separates release ordering into:

- SAME;
- NEWER;
- OLDER;
- UNORDERED.

An older provider view is classified as:

`OLDER_PROVIDER_VIEW`

Possible causes include provider rollback, stale cache, or an
inconsistent provider mirror.

In that state Basira keeps the last governed snapshot and never
downgrades automatically.

Release ordering is provider-specific. The generic trust engine does
not guess chronology from arbitrary version strings.

---

## STEP 06A — Discover direct KFGQPC Hafs witness

**Timestamp:** 2026-10-04T00:19:03-07:00
**Branch:** `feat/quran-kfgqpc-witness`
**Starting HEAD:** `2124c3a`

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

### STEP 06A result — KFGQPC second Quran witness

#### Result

`DEFERRED_EXTERNAL_AVAILABILITY`

The King Fahd Complex was selected as the intended second direct
Quran witness.

The official developer/download endpoints were not reachable from
the competition environment within the bounded acquisition timeout.

No artifact was admitted and no provenance claim was fabricated.

#### Competition decision

Do not spend additional competition time retrying the same external
dependency.

The current governed Quran runtime remains:

- Quranpedia Hafs;
- artifact integrity VERIFIED;
- structural integrity VERIFIED;
- witness identity VERIFIED;
- update-aware source governance enabled.

Independent/correlated second-source Quran attestation remains a
documented future enhancement.

#### Future feature

`Independent Quran Witness Attestation`

Planned verification:

source lineage
→ riwaya
→ rawi
→ rasm
→ dabt
→ reference alignment
→ verse/word comparison
→ independent vs correlated classification.

#### Decision

DEFER.

---

## STEP 07 — Onboard Dorar Hadith as primary competition source

**Timestamp:** 2026-10-04T00:26:56-07:00
**Branch:** `feat/official-hadith-dorar`
**Starting HEAD:** `e152604`

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

### STEP 07A — Dorar Hadith API schema characterization

The official Dorar Hadith API was reachable.

The live response schema differs from the historical structured-object
assumption.

Observed live shape:

`ahadith.result -> HTML string`

Therefore Basira does not deserialize the search response directly
into one hadith assertion.

The competition adapter parses every result separately and preserves:

- hadith text;
- narrator;
- muhaddith;
- cited source;
- page/number;
- muhaddith verdict;
- additional returned metadata.

Critical safety rule:

Multiple Dorar search hits that contain similar matn but different
narrators, sources, chains, or verdicts are NOT merged by majority
vote and are NOT collapsed into one grading.

Provider authority and adapter correctness are treated separately.

Dorar is an approved competition source family, while the live API
adapter remains subject to explicit schema and retrieval audits before
runtime admission.

### STEP 07B — Adversarial Dorar retrieval audit

Basira evaluated Dorar retrieval against real captured responses.

Safety invariants:

1. Similar or identical matn results remain separate attestations
   when narrator, muhaddith, source, reference, or verdict differs.

2. Search-result frequency is not evidence of scholarly consensus.

3. No majority vote is applied to hadith grading.

4. A returned hadith without attribution metadata is not converted
   into usable evidence.

5. Zero search hits are represented as:

   `NO_HITS_FOR_QUERY`

   not as:

   `NO_HADITH_EXISTS`

   and not as:

   `RESOLVED_ABSENCE`.

This preserves the distinction between retrieval observation and
religious/source-level absence.

The adversarial audit must pass before Dorar can receive a runtime
Source Trust Passport.

### STEP 07C/D — Official Hadith priority policy

The competition Hadith policy is now explicit in code.

Priority:

1. Sahih al-Bukhari;
2. Sahih Muslim;
3. other Sunnah collections only after verification.

Verification paths for non-Sahihain material include:

- Dorar Hadith;
- approved Shamela editions.

Dorar is therefore modeled as a:

`HADITH_VERIFICATION_AND_GRADING_AUTHORITY`

rather than as the sole canonical Hadith corpus.

Fail-closed rules:

- missing source/reference:
  `NOT_USABLE_AS_HADITH_EVIDENCE`;

- non-Sahihain material without verification:
  `RETRIEVE_MORE`;

- zero search hits:
  `NO_HITS_FOR_QUERY`;

- conflicting attributed gradings:
  preserve all gradings;

- majority-vote grading:
  prohibited;

- consensus inference from search frequency:
  prohibited.

A verified authentic Hadith still requires a separate semantic
claim-evidence check. Authenticity does not automatically imply that
a downstream claim is entailed by the Hadith.

Competition decision:

Hadith source-policy foundation is complete for v1.

Full Sahihain ingestion and expanded Shamela Hadith editions remain
future source-coverage work.

---

## STEP 08A — Implement official competition Fiqh policy

**Timestamp:** 2026-10-04T00:50:01-07:00
**Branch:** `feat/official-fiqh-dorar`
**Starting HEAD:** `7034af4`

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

### STEP 08A — Official Fiqh policy

The competition Fiqh policy is now explicit in code.

Eligible evidence families:

1. governed approved books from the four Sunni madhhabs;
2. Dorar Fiqh Encyclopedia.

A book is not automatically eligible merely because it belongs to
one of the four madhhabs. It must still pass source governance.

Hard rules:

- no independent personal fatwa;
- no automated tarjih;
- no majority-vote jurisprudence;
- no collapse of documented madhhab disagreement;
- no unsupported consensus claim;
- preserve madhhab attribution;
- preserve conditions;
- preserve exceptions.

Personal cases are routed to:

`ESCALATE_TO_QUALIFIED_SCHOLAR`

with general information only.

General comparative Fiqh may present multiple documented positions
without selecting a winner automatically.

Fiqh evidence authenticity/source eligibility remains separate from
semantic claim-evidence support.

---

## STEP 08B — Discover Dorar Fiqh live retrieval structure

**Timestamp:** 2026-10-04T00:50:02-07:00
**Branch:** `feat/official-fiqh-dorar`
**Starting HEAD:** `697081d`

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

### STEP 08B — Dorar Fiqh live discovery started

A live Dorar Fiqh search response was captured for a comparative
Fiqh-friendly query.

No Fiqh adapter has been written yet.

This is intentional.

Basira first characterizes the provider response to determine how the
live site exposes:

- Fiqh positions;
- madhhab attribution;
- cited sources;
- conditions;
- exceptions;
- disagreement;
- consensus claims.

No result is admitted merely because it appears in the live search.

The next step is to build the adapter against the observed provider
structure and then adversarially test disagreement preservation and
the no-automated-tarjih rule.

### STEP 08A.1 — Fiqh source-family semantics corrected

The official Fiqh reference allows two source families:

1. a recognized/authoritative Fiqh book within one of the four
   madhhabs;
2. Dorar Fiqh Encyclopedia.

Basira now explicitly separates:

`SOURCE FAMILY PERMISSION`

from:

`RUNTIME SOURCE ELIGIBILITY`

The earlier enum name:

`APPROVED_MADHHAB_BOOK`

was too ambiguous because it could imply that the competition supplied
a fixed whitelist of named books.

It has been corrected to:

`MADHHAB_FIQH_BOOK`

A concrete madhhab book must still have a known madhhab identity and
must pass Basira source governance before runtime use.

The same governance distinction applies to Dorar:

the official reference allows the Dorar Fiqh source family, while the
live provider adapter and captured evidence still require technical
governance before runtime admission.

This gives the source model two independent questions:

1. Is this an officially allowed Fiqh source family?
2. Has this exact source instance passed Basira governance?

Only when both are satisfied may the evidence become runtime-usable.

### STEP 08C — Dorar Fiqh canonical article adapter

The live Dorar search page is treated as a retrieval locator rather
than as final Fiqh evidence.

Canonical `/feqhia/<id>` article pages are captured and hashed before
their content is converted into evidence.

The adapter preserves:

- canonical article identity;
- full article text;
- explicit disagreement language;
- separately expressed positions;
- madhhab attribution;
- cited book/reference strings.

The adapter deliberately does NOT perform:

- automated tarjih;
- majority voting between madhhabs;
- consensus inference from the number of madhhab mentions;
- personal fatwa generation.

Explicit disagreement is preserved as disagreement.

Consensus is recognized only when the provider text explicitly
contains consensus/agreement language; it is never inferred from
search frequency or source counts.

Dorar search snippets are not treated as sufficient final evidence
when a canonical article page is available.

### STEP 08C — Dorar Fiqh canonical article adapter

The live Dorar search page is treated as a retrieval locator rather
than as final Fiqh evidence.

Canonical `/feqhia/<id>` article pages are captured and hashed before
their content is converted into evidence.

The adapter preserves:

- canonical article identity;
- full article text;
- explicit disagreement language;
- separately expressed positions;
- madhhab attribution;
- cited book/reference strings.

The adapter deliberately does NOT perform:

- automated tarjih;
- majority voting between madhhabs;
- consensus inference from the number of madhhab mentions;
- personal fatwa generation.

Explicit disagreement is preserved as disagreement.

Consensus is recognized only when the provider text explicitly
contains consensus/agreement language; it is never inferred from
search frequency or source counts.

Dorar search snippets are not treated as sufficient final evidence
when a canonical article page is available.

### STEP 08C.4 — Diacritic-aware madhhab attribution

The canonical Dorar Fiqh article was structurally parsed as two
positions, but the second position initially exposed only the Hanbali
madhhab even though the source explicitly attributes that position to
the Shafii and Hanbali madhhabs.

Cause:

madhhab detection was literal and did not normalize Arabic tashkeel.

The matcher now performs diacritic-insensitive structural matching
while preserving the original source text unchanged.

The frozen comparative source audit now requires:

- position 1: Hanafi + Maliki;
- position 2: Shafii + Hanbali;
- citations on both positions;
- exact ordinal sequence `[1, 2]`.

### STEP 08A.2 — Madhhab Book Authority Registry

Basira now separates:

1. madhhab/source family;
2. scholarly authority status;
3. technical runtime eligibility.

For the future Hybrid Fiqh Agent:

`DISCOVERED != AUTHORIZED`

`FAMOUS != MUTAMAD`

`CITED != MUTAMAD`

`DORAR_REFERENCE_LISTED != MUTAMAD`

A book may be used as primary madhhab-book evidence only when:

- the madhhab identity is known;
- authority is explicitly VERIFIED_MUTAMAD;
- authority evidence is recorded;
- the exact edition/provider artifact is governed;
- the source is runtime ELIGIBLE.

The initial registry is intentionally empty rather than inventing an
unsupported whitelist.

### STEP 08D — Fiqh competition v1 admission

Dorar Fiqh is admitted as:

`ELIGIBLE_LIVE_CANONICAL_ARTICLE`

Search results remain locators only.

The system preserves disagreement, madhhab attribution and citations,
and prohibits automated tarjih, majority voting, unsupported consensus
claims and independent personal fatwa.

### STEP 09A — Official Tafsir Authority Foundation

Basira now models the official Tafsir source rule as two independent
source families:

1. Islamic sources verified to belong to the first three centuries;
2. Dorar Tafsir.

The first family is intentionally broader than "early Tafsir books".
However, an early-source claim must itself be verified.

Author death year alone is not sufficient to classify a source as
belonging to the first three centuries.

A governed early-source record requires source/work period evidence,
identity/provenance and runtime artifact governance.

### STEP 09A.1 — Tafsir evidence-type boundary

Tafsir material is typed rather than stored as one undifferentiated
text class:

- Quran text;
- Prophetic Tafsir narration;
- Companion Athar;
- Tabi'i Athar;
- early scholar explanation;
- linguistic explanation;
- scholarly reasoning;
- Asbab al-Nuzul.

Hard semantic boundaries:

`QURAN TEXT != TAFSIR`

`COMPANION ATHAR != PROPHETIC HADITH`

`SCHOLARLY EXPLANATION != PROPHETIC REPORT`

A Quran verse displayed inside a Tafsir source is context only and
cannot replace the governed canonical Quran witness.

### STEP 09A.2 — Narration Quality Layer

Basira does not independently authenticate isnads.

It preserves quality judgments reported by governed authorities.

Quality states include:

- accepted by authority;
- weak by authority;
- rejected by authority;
- conflicting authority grades;
- ungraded;
- not applicable.

Hard invariants:

`FOUND IN EARLY SOURCE != AUTHENTICALLY ATTRIBUTED`

`MULTIPLE TRANSMISSIONS != AUTOMATICALLY AUTHENTIC`

`NO GRADE FOUND != WEAK`

`WEAK != FABRICATED`

Weak narrations are not primary Tafsir evidence.

Rejected narrations are blocked.

Conflicting grades are preserved rather than majority-voted.

Ungraded narrations remain explicitly ungraded and supporting-only.

### STEP 09A.3 — Fiqh safety boundary

Tafsir evidence does not directly establish a Fiqh ruling.

When a claim requires a ruling, Basira must route to the dedicated
Fiqh and Hadith evidence architecture.

This prevents a weak or unverified Tafsir narration from silently
becoming the basis of a legal ruling.

### Future Hybrid Tafsir Agent

The Hybrid Agent will be allowed to discover broadly, but evidence use
will remain gated:

discovery
→ official source family
→ period/source identity
→ narration/attribution quality
→ exact artifact governance
→ claim-evidence verification
→ usable explanation.

The initial Tafsir source registry is deliberately empty. No early
source is pre-authorized without evidence.

### STEP 09B — Dorar Tafsir live characterization

Dorar Tafsir was characterized before any runtime adapter or source
admission was implemented.

Observed live surfaces include:

- Tafsir home/search;
- approved references;
- methodology;
- surah-level pages;
- nested passage/ayah pages.

The search surface exposes semantically distinct scopes including:

- Quran verses;
- surah introductions;
- unfamiliar-word explanation;
- grammar;
- general meaning;
- Tafsir of verses;
- educational benefits;
- scholarly benefits and subtleties;
- rhetoric.

The approved-reference surface exposes bibliographic metadata such as:

- author;
- editor/verifier;
- publisher;
- edition.

Dorar's methodology explicitly includes:

- reliance on authenticated Prophetic and mawquf reports;
- recording who authenticated those reports;
- Asbab al-Nuzul when established;
- Salaf statements with attribution to original sources.

Characterization initially produced false-negative assertions because
the audit oracle inspected a truncated text preview and used
inconsistent Arabic orthographic normalization.

The source itself had not failed.

The characterization oracle was corrected to:

- inspect full captured page text;
- normalize Arabic Alef variants for structural matching;
- preserve original evidence text unchanged;
- use canonical Arabic search markers.

No search result, citation count, repeated transmission, or source
frequency is treated as an authenticity grade.

Runtime admission remains:

`PENDING_AUDIT`

Adapter status remains:

`NOT_IMPLEMENTED`

### STEP 09C — Canonical Dorar Tafsir evidence adapter

The Dorar Tafsir adapter was built from observed live DOM structure,
not inferred from search labels.

Canonical passage structure is identified under:

`div#cntnt`

with evidence sections represented by canonical `article` elements.

The frozen Fatiha passage preserves seven section roles:

- `tt9` — general meaning;
- `tt7` — unfamiliar-word explanation;
- `tt8` — grammar;
- `tt4` — Tafsir of verses;
- `tt16` — educational benefits;
- `tt17` — scholarly benefits and subtleties;
- `tt18` — rhetoric.

Search-form labels and sticky-navigation labels are not evidence
sections.

#### HTML void-element hardening

The first real audit exposed an HTML parsing defect caused by global
numeric DOM-depth tracking.

Dorar content contains many void elements such as `<br>` with no
matching closing tag.

Canonical article closure was therefore changed to semantic
`<article> ... </article>` state rather than synthetic global depth.

A regression test reproduces the real repeated-`<br>` failure mode.

#### Quran / Tafsir provenance boundary

Quran material inside `span.aaya` is routed to a Quran-context channel.

Quran references inside `span.sora` are routed to a Quran-reference
channel.

Neither role replaces Basira's governed canonical Quran witness.

The audit originally compared Quran strings lexically against Tafsir
explanation text. Real data demonstrated that this is invalid.

For example, short Quran words such as `مالِك`, `مَلِك`, `لله`, and
`إِيَّاكَ` may legitimately occur again in ordinary explanatory prose.

Therefore:

`SAME STRING != SAME PROVENANCE`

The production boundary is now audited using source-node routing:

`QURAN SOURCE NODE -> QURAN CONTEXT`

and never:

`QURAN SOURCE NODE -> TAFSIR EXPLANATION`

Lexical overlaps remain diagnostic information only.

#### Citation and narration provenance

`span.tip` is preserved separately from explanatory prose.

Citation material containing explicit transmission-source language
such as `رواه` or `أخرجه` is preserved as narration-source evidence.

Explicit grading language is preserved only as a reported judgment
with its citation provenance.

Basira does not independently grade isnads.

Citation frequency and repeated transmission do not create an
authenticity score.

#### STEP 09C state

The adversarial real-source audit verifies:

- seven canonical section roles;
- canonical article identities;
- Quran source-node routing;
- Quran reference preservation;
- citation preservation;
- narration-source preservation;
- reported grading provenance;
- no independent isnad grading;
- no authenticity-by-frequency.

Runtime admission remains:

`PENDING_AUDIT`

Source Trust Passport remains:

`NOT_ISSUED`

### STEP 09D — Controlled Dorar Tafsir runtime admission

Dorar Tafsir is now admitted as a governed runtime source under a
narrow evidence-use contract.

Admission does not cover the whole Dorar website.

V1 runtime evidence scope is limited to canonical passage pages:

`https://dorar.net/tafseer/{surah}/{passage}`

The following remain discovery-only:

- Tafsir home/search;
- surah-level pages;
- approved-reference pages;
- methodology pages.

This enforces the Basira retrieval invariant:

`DISCOVER BROADLY != USE BROADLY`

#### Runtime Source Trust Passport

The Dorar Tafsir Source Trust Passport records:

- official source family;
- controlled runtime scope;
- successful live characterization;
- successful adversarial adapter audit;
- baseline characterized response SHA-256;
- hashes of the policy, adapter, characterization, audit and runtime
  admission manifest;
- safety boundaries and documented limitations.

Runtime admission fails closed if governed artifact hashes drift.

#### Exact live-response provenance

Admission of a live canonical passage produces a runtime evidence
envelope containing:

- canonical URL;
- passport ID;
- source family;
- runtime eligibility;
- exact response SHA-256;
- response byte size;
- adapter contract;
- structured Tafsir passage.

This does not claim that every future Dorar response is byte-identical
to the characterized baseline.

Instead, every retrieved live response receives its own exact artifact
hash for traceability.

#### Safety boundaries retained

Runtime eligibility does not permit:

- treating Quran text inside Tafsir as a canonical Quran witness;
- independent Basira isnad grading;
- authenticity scoring from citation frequency;
- using Tafsir directly as a Fiqh ruling authority;
- promoting search results or surah pages into admitted passage
  evidence.

Reported narration grading remains attributed evidence only.

Dorar Tafsir V1 is therefore:

`ELIGIBLE — CANONICAL PASSAGE SCOPE ONLY`

### STEP 10A — Official domain coverage matrix

Basira now maintains a machine-readable coverage matrix for the
official competition directions.

The matrix distinguishes:

- governed runtime coverage;
- governed discovery-only coverage;
- governed policy-only coverage;
- approved source families not yet implemented;
- uncovered domains;
- explicitly out-of-scope requests.

Current governed runtime foundations:

- Quran;
- Tafsir;
- Hadith;
- general Fiqh.

Official directions still requiring implementation are represented
explicitly rather than silently falling back to arbitrary retrieval.

A global invariant is now frozen:

`NO_OFFICIAL_DOMAIN_MAY_FALL_BACK_DIRECTLY_TO_GENERIC_SHAMELA_SEARCH`

Shamela is a digital library/container, not a universal source
authority.

When a permitted source is retrieved through Shamela, Basira must
already know:

domain
→ approved source family
→ exact book
→ source authority eligibility
→ exact governed edition/artifact
→ runtime evidence.

The coverage matrix intentionally remains NOT READY for V1 closure
until every required official direction has a governed retrieval path.

### STEP 10B — Official Aqeedah authority foundation

Basira now models the official Aqeedah / introduction-to-Islam rule
as two independent source families:

1. Islamic sources verified to belong to the first three centuries;
2. Dorar Aqeedah.

The first family is not equivalent to "any famous early-looking book".

Primary use requires:

- verified source/work period;
- explicit period evidence;
- verified source identity;
- exact governed artifact;
- runtime source eligibility.

Author death year alone is insufficient.

The early-source registry is deliberately empty until actual source
identity, period, edition and provenance evidence is collected.

#### Cross-domain evidence boundaries

Quran text found inside an Aqeedah source cannot become Basira's
canonical Quran witness.

Prophetic reports found inside an Aqeedah source are not independently
authenticated by the Aqeedah layer and must route through the governed
Hadith foundation.

Companion and Tabi'i reports preserve their attribution identity.

Source count does not establish consensus.

Detailed Aqeedah questions require a disagreement check and cannot
silently become categorical merely because multiple retrieved texts
look similar.

#### Shamela boundary

Generic Shamela search is prohibited as an Aqeedah fallback.

A future Shamela-backed Aqeedah source must first have:

domain authority
→ exact approved source/work
→ exact governed edition
→ source-period/provenance evidence
→ runtime eligibility.

#### Runtime state

Aqeedah is now:

`GOVERNED_POLICY_ONLY`

Dorar Aqeedah remains:

`PENDING_AUDIT`

No Dorar Aqeedah Source Trust Passport has been issued.

The next Aqeedah step must perform empirical live structure
characterization before any adapter or runtime admission.

### STEP 10B.1 — Dorar Aqeedah live characterization

Dorar Aqeedah was characterized empirically before implementing a
runtime adapter or issuing a Source Trust Passport.

Observed live surfaces include:

- Aqeedah home and hierarchical topic tree;
- approved references;
- Dorar Aqeedah methodology;
- introductory canonical article;
- basic-definition canonical article;
- evidence-heavy detailed canonical article;
- search-result locator surface.

The current methodology explicitly includes:

- scientific topic selection;
- source collection;
- selection of approved sources;
- comparison of sources by quality, breadth and coverage;
- consideration of preferred editions;
- documentation of selected material to source, volume and page;
- specialist scientific editing.

The approved-reference surface exposes bibliographic metadata including
author, editor/verifier, publisher, edition and publication year.

The live characterization also confirms an important cross-domain
property:

Aqeedah pages may contain Quran quotations and Hadith evidence.

These are not promoted automatically.

Quran material must route to Basira's governed Quran foundation when a
canonical Quran witness is required.

Prophetic reports must route to Basira's governed Hadith foundation
when authenticity or attribution is required.

Search results are locator surfaces only and are not runtime evidence.

Generic Shamela fallback remains prohibited.

Runtime state remains:

`PENDING_AUDIT`

Adapter status remains:

`NOT_IMPLEMENTED`

Source Trust Passport remains:

`NOT_ISSUED`

The next step must inspect the observed canonical Aqeedah article DOM
before building a structured evidence adapter.

### STEP 10B.1.5 — Aqeedah period/authority separation

A critical semantic vulnerability was identified before building the
Dorar Aqeedah adapter.

The official Aqeedah source rule permits Islamic sources from the first
three centuries, but historical period eligibility alone does not prove
that an individual source should be treated as primary Aqeedah
authority.

Basira therefore freezes the invariant:

`PERIOD ELIGIBILITY != AQEEDAH AUTHORITY ELIGIBILITY`

Additional hard invariants:

`EARLY != AUTHORIZED`

`FAMOUS != AUTHORIZED`

`CITED != PRIMARY`

`DORAR-LISTED != PRIMARY`

`SHAMELA-HOSTED != AUTHORIZED`

`SOURCE COUNT != CONSENSUS`

#### Aqeedah authority registry

First-three-centuries Aqeedah sources now require a separate governed
authority state.

Supported authority states include:

- verified primary;
- verified supporting;
- Dorar reference-listed;
- pending authority review;
- quarantined;
- unknown.

Primary authority requires explicit authority evidence.

A Dorar bibliography/reference listing is preserved as useful
provenance but does not automatically promote a work to primary
authority.

The authority registry remains intentionally empty until actual source
authority evidence is collected.

Basira does not autonomously classify theological orthodoxy.

Authority status must come from governed evidence, cataloging or
scholarly review.

#### Cross-domain isolation

The first-three-centuries Aqeedah rule is explicitly prohibited from
propagating into general Fiqh retrieval.

General Fiqh continues to use its independent source contract:

`MADHHAB_FIQH_BOOK OR DORAR_FIQH`

and its separate madhhab authority registry.

Later authoritative madhhab works are therefore not rejected merely
because they were written after the first three centuries.

#### Runtime state

Aqeedah remains:

`GOVERNED_POLICY_ONLY`

Dorar Aqeedah remains:

`PENDING_AUDIT`

No runtime admission or Source Trust Passport has been issued.

### STEP 10B.3 — Canonical Dorar Aqeedah evidence adapter

The Dorar Aqeedah adapter was implemented from the empirically observed
canonical DOM rather than from lexical assumptions.

The frozen article contract is:

`ROOT = div#cntnt.card-body`

`TITLE = #cntnt .card-title h1`

`BODY = direct div.w-100.mt-4`

Typed source nodes inside the canonical body are:

`span.aaya -> Quran context`

`span.sora -> Quran reference`

`span.tip -> source note`

Ordinary body text is preserved as Dorar Aqeedah explanatory prose.

#### Provenance routing

Evidence roles are determined from originating DOM nodes.

They are not inferred from ancestor or aggregated full-text content.

The adversarial audit observed zero provenance-routing violations.

#### Quran boundary

Quran text embedded in Dorar Aqeedah is Quran context only.

It is never promoted to Basira's canonical Quran witness.

The audited page contains five Quran-context nodes and four
Quran-reference nodes, so automatic one-to-one pairing is prohibited.

Canonical Quran verification remains the responsibility of Basira's
Quran foundation.

#### Hadith boundary

Dorar Aqeedah source notes may contain Hadith attribution, reported
Hadith grading and bibliographic references.

Reported grading is preserved as attributed provenance only.

The Aqeedah adapter never independently authenticates a Hadith.

The observed DOM does not reliably delimit Hadith matn from surrounding
Aqeedah prose, so the adapter does not fabricate a structured
Hadith-matn channel.

#### Bibliographic authority boundary

A citation inside `span.tip` does not promote a cited work to primary
Aqeedah authority.

Authority remains governed separately by the Aqeedah authority registry.

`CITED != PRIMARY`

`EARLY != AUTHORIZED`

#### Runtime state

Adapter state:

`AUDITED`

Dorar Aqeedah runtime:

`NOT_ADMITTED`

Source Trust Passport:

`NOT_ISSUED`

### STEP 10B.4 — Controlled Dorar Aqeedah runtime admission

Dorar Aqeedah was admitted only after:

- official source-family policy;
- live empirical characterization;
- period/authority separation;
- canonical DOM probing;
- source-node provenance probing;
- structured adapter implementation;
- adversarial evidence-boundary audit.

The runtime scope is:

`canonical_article_only`

Canonical runtime URLs must match:

`https://dorar.net/aqeeda/{positive_integer_id}`

Search, home, reference, methodology, query-bearing, fragment-bearing
and slug-expanded URLs are not runtime evidence surfaces.

Each admitted response carries its exact SHA-256 in the evidence
envelope.

The adversarially audited `/aqeeda/420` artifact is frozen as a baseline
sentinel; hash drift on that audited baseline fails closed.

Runtime parsing requires:

- exactly one canonical `#cntnt.card-body` root;
- exactly one direct `div.w-100.mt-4` article body;
- zero provenance-routing violations.

The Source Trust Passport freezes the adapter contract and governed
artifact hashes.

Cross-domain boundaries remain unchanged:

- Aqeedah Quran text is context, not canonical Quran evidence;
- Hadith authenticity remains owned by the Hadith foundation;
- Hadith matn is not fabricated from unstructured prose;
- bibliographic citation does not promote Aqeedah authority;
- generic Shamela fallback is prohibited.

The first-three-centuries Aqeedah authority registry remains empty and
independently gated.

Only the official Dorar Aqeedah source-family path is runtime admitted.

Aqeedah coverage is now:

`GOVERNED_RUNTIME`

### STEP 10C.1 — Seerah and History evidence policy

Basira now models Seerah / History as an independent governed evidence
domain.

The official source-family paths are:

`FIRST_THREE_CENTURIES_ISLAMIC_SOURCE`

or:

`DORAR_HISTORY`

A source being early does not establish that every report within it is
historically established.

Basira freezes the invariants:

`EARLY SOURCE != VERIFIED HISTORICAL EVENT`

`SOURCE REPORT != ESTABLISHED FACT`

`MULTIPLE RETRIEVED REPORTS != AUTOMATIC CORROBORATION`

`SOURCE COUNT != CONSENSUS`

`AUTHOR DEATH <= 300 AH != SOURCE PROVEN EARLY`

`SHAMELA HIT != GOVERNED HISTORY EVIDENCE`

#### Historical report assessment

Historical report state is separate from source eligibility.

Governed report states include:

- established by governed authority;
- corroborated by governed authority;
- disputed by governed authority;
- requires caution by governed authority;
- rejected by governed authority;
- unassessed.

Basira does not manufacture these states from retrieval counts,
semantic similarity, repetition or model confidence.

For categorical historical claims, a governed historical report
assessment is required.

An unassessed early report can be preserved as a report in narrative
context, but it cannot silently become an established event.

Disputed or cautionary reports retain explicit caution.

#### Cross-domain boundaries

Quran text inside a historical source is not Basira's canonical Quran
witness.

Prophetic reports inside historical sources are not independently
authenticated by the History layer.

Hadith authenticity must route through the governed Hadith foundation.

#### Runtime state

History is now:

`GOVERNED_POLICY_ONLY`

Dorar History remains:

`PENDING_AUDIT`

The first-three-centuries History registry remains intentionally empty.

Generic Shamela fallback remains prohibited.

The next step is empirical live characterization of Dorar History before
any adapter or runtime admission.

### STEP 10C.1.5 — History retrieval and entity hardening

Before live Dorar History characterization, Basira hardened the
first-three-centuries History path against raw-report promotion,
historical entity mismatch and provenance loss.

#### Source-use mode

Historical source eligibility is now separate from source-use mode.

Governed source-use modes include:

- curated history reference;
- raw report collection;
- primary historical narrative;
- biographical source;
- chronicle.

Basira freezes:

`RAW REPORT COLLECTION != CURATED HISTORY`

and:

`SOURCE USE MODE != EVENT TRUTH`

A raw report collection is report-only by default.

It cannot independently establish a categorical historical event.

A raw report can contribute to a categorical claim only when a separate
governed historical report assessment supplies the event status.

#### Historical entity resolution

A governed historical entity layer now supports retrieval expansion for
historical names, modern names, alternative names, transliterations,
administrative successors and geographic overlap.

The entity resolver is retrieval infrastructure only.

Basira freezes:

`ALIAS MATCH != IDENTITY PROOF`

`ENTITY RESOLUTION != FINAL ANSWER REWRITE`

`ADMINISTRATIVE SUCCESSOR != HISTORICAL IDENTITY`

`GEOGRAPHIC OVERLAP != IDENTITY`

Historical aliases may carry time ranges and geographic scope.

Time-dependent or ambiguous mappings preserve ambiguity.

Multiple matching entities cannot produce a silent winner.

The production historical entity registry remains intentionally empty
until individual aliases have governed evidence.

#### Chunk provenance

History chunk construction preserves:

- source family;
- source title;
- source reference;
- source-use mode;
- material type;
- explicit attribution;
- governed report status.

The chunker does not infer missing attribution from prose.

A chunk cannot independently promote itself to historical fact.

This prevents source attribution from disappearing during RAG chunking
and later being rewritten by the language model as an unqualified fact.

#### Historical confidence

Basira does not use an LLM probability or numeric confidence score as a
historical truth grade.

Historical status remains a governed categorical evidence state.

This preserves the distinction between:

`HADITH AUTHENTICITY`

and:

`HISTORICAL REPORT STATUS`

#### Runtime state

History remains:

`GOVERNED_POLICY_ONLY`

Dorar History remains:

`PENDING_AUDIT`

No Dorar History adapter or Source Trust Passport has been issued.

The next step remains empirical live characterization of Dorar History.

### STEP 10C.2 — Dorar History live characterization

Dorar History was empirically characterized before runtime adapter
implementation.

Observed source governance includes:

- events must come from a reliable source;
- events are scientifically edited;
- a History-specific review section is exposed;
- the History review panel contains specialists identified as
  researchers/professors of Islamic history;
- bibliographic reference metadata is available.

The methodology-review document contains content belonging to multiple
Dorar encyclopedias.

Basira therefore freezes:

`OTHER ENCYCLOPEDIA REVIEW TEXT != HISTORY REVIEW EVIDENCE`

History review evidence is scoped to the History-specific content
subtree.

The observed History review section contains `راجع الموسوعة`, a
researcher in Islamic/contemporary history, and multiple professors of
Islamic history.

Previously assumed generic review phrases were absent from the captured
document and their absence is preserved.

#### Historical disagreement

A sampled Seerah event contains source-reported disagreement and
agreement.

These narrative qualifications are preserved.

Lexical disagreement markers do not independently create a historical
truth grade.

#### Prophetic reports

A sampled Seerah event contains Prophetic-report material.

`HISTORICAL PLACEMENT != HADITH AUTHENTICATION`

Authentication remains owned by the governed Hadith foundation.

#### Route discovery

Both event route families were observed:

`/history/{id}`

and:

`/history/event/{id}`

The runtime route contract remains deliberately unfrozen pending the
canonical DOM/route probe.

#### State

History remains:

`GOVERNED_POLICY_ONLY`

Dorar History remains:

`PENDING_AUDIT`

Adapter:

`NOT_IMPLEMENTED`

Source Trust Passport:

`NOT_ISSUED`

### STEP 10C.4 — Canonical Dorar History event adapter

The Dorar History adapter was implemented only after live
characterization and a read-only DOM/route probe.

Two self-canonical event route families are preserved:

`/history/{id}`

and:

`/history/event/{id}`

They are not collapsed into one invented URL scheme.

Across the audited samples, both route families share the same canonical
event structure.

#### Canonical event subtree

The adapter scopes event evidence strictly to:

`div#cntnt.card-body`

then:

`direct div#accordionEx`

then exactly one:

`direct div.event-container`

then:

`direct div.card.scroll-pos.z-depth-0.mb-0`

The canonical accordion is fail-closed against structural ambiguity.

There must be exactly one `event-container` anywhere in the entire
canonical accordion subtree, and that container must be its direct
child.

A nested duplicate event container therefore fails closed rather than
creating ambiguous provenance.

The event title is tied to:

`headingTwo{event_id}`

and the event body to:

`collapseTwo{event_id}`

The event ID in the canonical URL must match the DOM event ID.

Hijri and Gregorian year fields are required.

The lunar month field is optional because the audited samples contain
both present and absent cases.

#### Search-form contamination

The page contains search/interface text using the same label
`تفاصيل الحدث`.

The adapter does not use global lexical matching for event extraction.

Only the canonical event subtree may supply event details.

#### Historical disagreement

Disagreement wording may be preserved as a lexical routing signal.

It does not independently produce a historical truth grade.

Adapter output remains:

`UNASSESSED`

unless a separate governed historical report assessment supplies a
stronger state.

#### Prophetic reports

Prophetic wording inside historical prose does not become a structured
authenticated Hadith.

The History adapter does not independently authenticate Hadith and does
not fabricate a Hadith-matn channel from plain narrative.

Hadith authentication remains owned by the governed Hadith foundation.

#### References and Quran

The DOM probe did not establish a canonical per-event bibliographic
reference channel.

Global History reference links and methodology UI therefore do not
become event citations.

Quran-like structural material is likewise never promoted by the
History adapter into Basira's canonical Quran witness.

#### Adversarial audit

Six captured History events were audited across:

- direct `/history/{id}` routing;
- `/history/event/{id}` routing;
- Seerah;
- medieval history;
- early-modern history;
- contemporary history.

The audit confirmed:

- characterized artifact hashes match;
- both route families parse;
- lunar month is correctly optional;
- zero provenance-routing violations;
- zero event-reference promotions;
- zero Quran-witness promotions;
- zero independent Hadith authentications;
- zero machine historical truth grades;
- every adapter-produced event remains `UNASSESSED`.

#### Runtime state

Adapter:

`AUDITED`

History coverage:

`GOVERNED_POLICY_ONLY`

Dorar History:

`PENDING_AUDIT / NOT_ADMITTED`

Source Trust Passport:

`NOT_ISSUED`

Controlled runtime admission remains a separate step.

### STEP 10C.5 — Controlled Dorar History runtime admission

Dorar History was admitted to governed runtime only after:

- official History source-family policy;
- raw-source and entity-resolution hardening;
- live Dorar History characterization;
- History-specific methodology provenance verification;
- canonical DOM and route probing;
- structured event adapter implementation;
- adversarial provenance audit.

Runtime admission applies only to canonical event surfaces matching one
of the two observed self-canonical families:

`/history/{positive_integer_id}`

or:

`/history/event/{positive_integer_id}`

Both route families remain distinct.

Each admitted response carries its exact SHA-256.

The six captured events used in the adversarial audit are frozen as
drift sentinels. If one of those audited URLs is encountered at runtime,
its response hash must still match the audited artifact.

New canonical event URLs may be admitted only when they satisfy the same
strict structural contract.

#### Critical semantic distinction

History becoming:

`GOVERNED_RUNTIME`

does not mean:

`EVERY DORAR EVENT = ESTABLISHED HISTORICAL FACT`

Runtime eligibility governs source retrieval and structural provenance.

Adapter-produced History events remain:

`UNASSESSED`

by default.

They carry:

`may_state_as_established_fact = false`

For categorical historical claims, Basira still requires a separate
governed historical report assessment.

This preserves:

`SOURCE ELIGIBILITY != EVENT TRUTH`

and:

`RUNTIME ADMISSION != HISTORICAL CERTAINTY`

#### Hadith boundary

Prophetic wording in History does not authenticate Hadith.

The History runtime cannot independently authenticate Hadith or
fabricate Hadith matn from narrative prose.

Hadith authenticity remains owned by the governed Hadith foundation.

#### Quran boundary

Quran-like material in History does not become Basira's canonical Quran
witness.

Canonical Quran verification remains owned by the Quran foundation.

#### References

The audited History DOM did not establish a canonical per-event
bibliographic reference channel.

Global reference UI is therefore never promoted into event citation
evidence.

#### Early historical sources

The official first-three-centuries History source path remains
independently gated.

No early raw historical work is admitted merely because it is old.

The production early-source registry remains empty pending individual
source/work/artifact audit.

#### Historical entities

The historical entity framework remains available for time-aware,
ambiguity-preserving retrieval expansion.

The production entity registry remains empty until individual entity
mappings have governed evidence.

Entity resolution remains retrieval-only.

#### Coverage state

History is now:

`GOVERNED_RUNTIME`

via:

`dorar-history-v1`

The first-three-centuries source path remains independently unopened.

### STEP 10D.1 — Shubuhat and FAQ evidence policy

Basira now models Shubuhat / FAQ as a governed conversational domain.

The official primary conversational source is:

`BAYYINAT — Questions and Answers about Islam`

Official locator:

`dawa.center/file/7937`

Bayyinat is not yet runtime admitted.

#### Source-role separation

Basira freezes:

`BAYYINAT = PRIMARY CONVERSATIONAL SOURCE`

but:

`BAYYINAT != UNIVERSAL PRIMARY EVIDENCE`

A conversational source may organize, explain, clarify and structure an
answer without inheriting evidentiary authority over every factual or
religious claim inside that answer.

Therefore:

`CONVERSATIONAL FRAMING != EVIDENTIARY AUTHORITY`

#### Claim decomposition

Shubuhat answers must be decomposed into claims before evidence
selection.

Cross-domain claims route to their governed primary evidence domains:

- Quran claims -> Quran foundation;
- Tafsir claims -> Tafsir foundation;
- Hadith claims -> Hadith foundation;
- Aqeedah claims -> Aqeedah foundation;
- Fiqh claims -> Fiqh foundation;
- Seerah / History claims -> History foundation;
- sensitive terminology claims -> Translation / Terminology domain;
- general Da'wah claims -> Da'wah domain.

Bayyinat may still provide conversational framing around those claims.

It cannot replace their primary evidence.

This prevents:

`CROSS-DOMAIN EVIDENCE LAUNDERING`

where a fluent FAQ answer would otherwise be treated as direct authority
for every embedded Quranic, Hadith, historical, Aqeedah or Fiqh claim.

#### Consensus

Bayyinat wording does not establish scholarly consensus.

A source saying or implying "the scholars agree" cannot be converted
into machine consensus without support from the governed primary domain.

Basira freezes:

`SOURCE WORDING != CONSENSUS`

and:

`RETRIEVAL COUNT != CONSENSUS`

#### Hostile questions

Hostile or accusatory wording in the user's question does not authorize
Basira to mirror hostility.

The response remains civil, wise and evidence-led.

Basira freezes:

`HOSTILE QUESTION != HOSTILE RESPONSE LICENSE`

#### Personal fatwa

A personal case requiring an individualized ruling remains outside
Shubuhat / FAQ autonomous scope.

Basira may provide general information and qualified referral.

It must not manufacture an individualized ruling.

#### Fallbacks

Generic Shamela search cannot replace a primary evidence domain.

Generic web search cannot replace the governed Quran, Hadith, Tafsir,
Aqeedah, Fiqh or History path.

#### Runtime state

Shubuhat / FAQ coverage is now:

`GOVERNED_POLICY_ONLY`

Bayyinat remains:

`PENDING_AUDIT`

Adapter:

`NOT_IMPLEMENTED`

Source Trust Passport:

`NOT_ISSUED`

The next step is empirical acquisition and characterization of the
official Bayyinat artifact before any adapter or runtime admission.

### STEP 10D.2 — Official Bayyinat artifact characterization

Official locator:

`https://dawa.center/file/7937`

The official landing page resolved to the Bayyinat PDF without an
external substitute.

Frozen artifact:

- format: PDF
- pages: 1259
- SHA-256:
  `619b7201833419b8fbf86c463208462b9a2a7f02ad2306a2667490f3b410ad4e`
- extraction: usable Arabic text layer through pypdf

Arabic-normalized characterization confirms substantial embedded material
related to Quran, Hadith, Aqeedah, Fiqh and Seerah / History.

These signals do not promote Bayyinat into universal primary evidence.

Bayyinat remains the official primary conversational source for
Shubuhat / FAQ, while cross-domain evidentiary claims continue to route
to their governed primary domains.

Citation-like signals are present, but no stable citation channel has
yet been frozen.

Runtime remains pending.

### STEP 10D.3B — Bayyinat exact Q/A heading structure

A read-only structural probe was run against the exact frozen official
Bayyinat PDF.

Arabic-normalized exact heading matching established:

- exact `السؤال` / `سؤال` headings: 263
- exact `الجواب` / `جواب` / `الإجابة` headings: 263
- direct Q -> A pairs: 263
- Q -> A pair failures: 0
- Q -> A transitions: 263
- A -> Q transitions: 262
- Q -> Q transitions: 0
- A -> A transitions: 0
- pairing ratio: 1.0

Eight narrative lines beginning with forms of `السؤال ...` were observed
and explicitly excluded from structural heading classification.

Therefore:

`EXPLICIT_QA_HEADING_CONTRACT = STRUCTURALLY_STABLE`

This result does not yet define the full question unit.

The PDF also contains a numbered/title layer before each question
heading. That numbered-title boundary remains to be characterized.

Therefore:

`QUESTION_BOUNDARY_CONTRACT = NOT_YET_FROZEN`

and:

`NUMBERED_QUESTION_BOUNDARY_CONTRACT = NOT_YET_FROZEN`

No adapter, runtime admission, or Source Trust Passport is issued at this
stage.

### STEP 10D.3B.1 — Bayyinat characterization variable-isolation fix

A post-characterization audit found that the Q/A heading comprehension
reused the variable name `kind`, which was also used for the resolved
artifact type.

Because the assignment expression binds in the surrounding scope, Q/A
characterization could overwrite the previously detected PDF artifact
type.

The Q/A-local variable was renamed to `qa_kind`.

This was a metadata implementation defect only. The official artifact
identity, 263/263 Q/A heading structure, cross-domain observations, and
governance conclusions were unchanged.

A regression guard now requires:

`artifact.kind == "pdf"`

after Q/A characterization.

Bayyinat remains `PENDING_AUDIT`.

### STEP 10D.3F — Bayyinat complete unit-boundary contract

The official frozen Bayyinat PDF was audited globally after establishing
the exact Q/A heading structure.

The extracted numbered-title marker:

`الم<ordinal>س`

is treated strictly as an extraction artifact marker. No semantic
interpretation of the `الم` / `س` glyph sequence is asserted.

Observed structural invariants:

- numbered markers: 263
- ordinal sequence: exactly 1 through 263
- duplicate markers: 0
- missing markers: 0
- exact question headings: 263
- exact answer headings: 263
- global event cycle: `M -> Q -> A` repeated 263 times
- one-line title blocks: 173
- two-line title blocks: 90

For units 1 through 262, the next numbered marker provides a deterministic
exclusive end boundary:

`M(N) -> Q -> A -> ... -> M(N+1)`

validated for 262/262 non-final units.

A proposed universal `كلمات دلالية` footer rule was rejected.

Only 243 of 263 units expose a footer matching the normalized footer
classifier; 20 units do not. Therefore keyword footers MUST NOT be used
as the universal unit terminator.

The final unit, number 263, does itself expose one unambiguous keyword
footer after its answer at PDF page 1253 line 8.

After that footer, the artifact enters end matter:

- references begin on page 1255
- development questionnaire begins on page 1257

Therefore the complete frozen boundary strategy is:

- start: numbered title marker, inclusive
- units 1..262 end: next numbered title marker, exclusive
- unit 263 end: its final keyword footer, inclusive

EOF is not used as the semantic boundary for unit 263.

`BAYYINAT_UNIT_BOUNDARY_CONTRACT = FROZEN`

This structural result does not promote Bayyinat into universal primary
evidence and does not admit it to runtime.

State remains:

- Bayyinat: `PENDING_AUDIT`
- Adapter: `NOT_IMPLEMENTED`
- Source Trust Passport: `NOT_ISSUED`
- Internal citation channel: not frozen

### STEP 10D.4 — Bayyinat governed content schema and snapshot

The internal Bayyinat structure was closed after targeted anomaly
analysis rather than continuing broad heuristic probing.

Four apparent anomalies were resolved as extraction/classification
effects:

- units 173 and 182 expose `مختصر الجواب` as an alternate short-answer
  heading form;
- units 160 and 260 contain narrative phrases mentioning
  `الجواب التفصيلي` in their answer bodies, while each still exposes one
  independent structural detailed-answer heading;
- unit 100 uses a reversed extracted detailed-heading order;
- unit 50 contains a body reference containing `مختصر`, which is not a
  structural short-answer heading.

The frozen content contract therefore establishes:

Mandatory in 263/263 units:

- title
- question text
- short answer
- detailed answer
- page/line provenance

Optional:

- similar formulations: 253/263
- question gist: 178/263
- conclusion/recommendation: 119/263
- keywords: 243/263
- related questions: 74/263

Keywords and related questions are independent optional metadata.
They are not an XOR pair. Units 95 and 227 expose neither.

A governed derived snapshot containing 263 units is generated from the
frozen official PDF and deterministic unit-boundary contract.

A standalone Bayyinat search adapter is available for conversational
retrieval.

Governance remains intentionally strict:

- Bayyinat is the primary conversational source for Shubuhat / FAQ.
- Bayyinat is NOT universal primary evidence.
- Quran, Hadith, Aqeedah, Fiqh, and History claims continue to require
  their governed primary-domain evidence.
- internal citation-like strings remain lexical-only;
  no Bayyinat internal citation contract is frozen.
- router admission and Source Trust Passport are deferred to the unified
  Trust Shield stage rather than duplicated per remaining domain.

This closes the Bayyinat source-characterization and governed-snapshot
work for official-domain coverage.

### STEP 10D.4 — Bayyinat competition-sufficient retrieval contract

Bayyinat was closed at the canonical-unit level rather than overfitting
runtime correctness to every PDF text-layer header variant.

The stronger invariants are:

- exact official Bayyinat artifact
- 263 deterministic numbered units
- frozen unit-boundary contract
- searchable complete unit representation
- stable ordinal and page provenance
- governed conversational retrieval

Internal fields such as question gist, short answer, detailed answer,
conclusion, keywords and related questions are optional enrichment.
Extraction variation in those fields does not invalidate a canonical
Bayyinat unit.

Retrieval ranking uses generic multi-concept coverage over the governed
candidate pool, with higher weight for title/question matches and
rare-query concepts. This prevents a broad topical term from dominating
a more specific unit that covers the complete user query.

Bayyinat remains a conversational source, not universal primary evidence.

Embedded Quran, Hadith, Aqeedah, Fiqh and History claims must continue
to route to their corresponding governed primary domains.

No evidentiary authority is inferred from retrieval rank.
