# Evaluation protocol — v0.1 (locked before M02)

## Primary hypothesis

Adding cross-merchant relationship and temporal/emerging-risk signals can
reduce time-to-detection for coordinated synthetic payment abuse relative to a
merchant-local baseline while maintaining an acceptable false-positive rate.
This is falsifiable; no result target is guaranteed.

## Cohorts

M01 uses consecutive UTC windows:

| Cohort | Window |
| --- | --- |
| Train | 2026-01-01T00:00:00Z to 2026-01-15T00:00:00Z |
| Validation | 2026-01-15T00:00:00Z to 2026-01-22T00:00:00Z |
| Held-out test | 2026-01-22T00:00:00Z to 2026-01-29T00:00:00Z |

Campaigns never cross cohorts. Accounts, devices, and network groups are
cohort-disjoint; merchants remain shared. The held-out test must not influence
feature choices, model selection, threshold selection, or economic assumptions.

## Planned model comparison

- **System A:** merchant-local decision-time features only.
- **System B:** System A plus cross-merchant relationship features.
- **System C:** System B plus temporal/emerging-cluster features.

Thresholds will be selected exclusively on validation data and frozen before
the held-out test is evaluated.

## Metrics

M02+ must report precision, recall, F1, FPR, confusion matrix, PR-AUC where
appropriate, and threshold. TTD is the first qualifying alert timestamp minus
the first ground-truth campaign event timestamp. Missed campaigns are reported
as misses and excluded only from the *detected-campaign* TTD median, never
silently dropped from detection coverage.

Economic metrics will be introduced in a versioned pre-test cost-assumption
table before Experiment 001. No monetary or performance claim exists in M01.

## Leakage checks

M01 checks label/scenario/campaign separation, time ordering, temporal cohort
boundaries, entity disjointness, duplicate transactions, opaque IDs, campaign
cohort containment, and constant abuse-signature artifacts. M02 adds feature
as-of-time tests; M03/M04 extend them for graph and temporal features.
