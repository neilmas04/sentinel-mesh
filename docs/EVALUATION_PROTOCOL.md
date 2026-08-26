# Evaluation protocol — v0.3 (updated after M03)

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
- **System B:** System A plus cross-merchant relationship features (device, network group, and account features).
- **System C:** System B plus temporal/emerging-cluster features or feedback-loop features.

Thresholds are selected exclusively on validation data using cost-aware thresholding with a maximum False Positive Rate constraint (5%), and are frozen before the held-out test is evaluated.
Ablations for System B are conducted to measure the value of specific network feature groups.

## Metrics

All systems report precision, recall, F1, FPR, confusion matrix, PR-AUC, threshold, expected cost, loss before detection, coverage, and time-to-detection (TTD). 

- **TTD** is the first qualifying alert timestamp minus the first ground-truth campaign event timestamp. 
- **Missed campaigns** are reported as misses and excluded from the detected-campaign TTD median, lowering overall detection coverage.
- **Loss Before Detection** aggregates the total financial volume of fraudulent transactions in a campaign that occurred prior to detection.

## Leakage checks

M01 checks label/scenario/campaign separation, time ordering, temporal cohort
boundaries, entity disjointness, duplicate transactions, opaque IDs, campaign
cohort containment, and constant abuse-signature artifacts. M02 and M03 implemented feature
as-of-time tests and verified strictly causal feature extraction. M04 will extend them for feedback loop features.
