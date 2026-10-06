# Retrieval Rescue Evaluation Results

`retrieval_rescue_holdout_v1_pre.json` was produced from commit
`af6cad7`, after the evaluation diagnostics existed but before the
atomic-query retrieval rescue.

`retrieval_rescue_holdout_v1_post.json` was produced using the frozen
retrieval implementation completed at commit `20e29cf`.

The holdout was frozen and committed before either result was run.
It must not be used for further retrieval tuning.

The benchmark contains two conceptual slices:

- `iv_unseen_wording`: concepts represented in the planner but phrased
  differently from DEV.
- `oov_concept`: concepts with no dedicated atomic-query rule in the
  frozen planner.

Candidate depth is 100 per retrieval domain for candidate-recall
diagnostics. Exact-anchor behavior remains a regression control.
