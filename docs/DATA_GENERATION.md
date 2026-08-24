# M01 data generation

## Version and reproducibility

The generator is `src.simulation.m01_world` and currently emits dataset version
`m01-world-v1`. Its only random source is `random.Random(seed)`; identifiers
are deterministic SHA-256-derived opaque IDs, not UUIDs. The full seed and
configuration are saved to `manifests/generation_config.json`.

## Persistent entity model

- **Merchant:** category, normal amount distribution, and baseline volume.
- **Account:** creation time, spending segment, merchant preferences, and
  persistent device/network relationships.
- **Device:** persistent type, cohort, home network, and associated-account
  count.
- **Network group:** synthetic-only identifier, type, cohort, and associated
  account count.
- **Transaction:** timestamped decision-time fields only.

Account, device, and network-group identifiers are cohort-disjoint. Merchants
are shared intentionally because the research question is cross-merchant.

## Scenarios

Each temporal cohort contains all of the following:

1. normal baseline;
2. legitimate high-volume event;
3. benign family/shared device;
4. benign corporate/shared network;
5. legitimate cross-merchant burst;
6. single-merchant anomaly;
7. distributed coordinated abuse;
8. sleeper-account activation; and
9. accelerating coordinated cluster.

Campaign sizes, timings, merchants, accounts, devices, networks, and amounts
are sampled from seeded distributions. The leakage checker rejects abuse
campaigns with constant amounts or constant inter-event intervals.

The default M01 artifact has 46,296 transactions: 23,160 train, 11,568
validation, and 11,568 test. It contains 2,340 labelled abuse events and 45
merchants, 2,700 accounts, 2,222 devices, and 1,106 network groups. Exact
scenario counts are saved in `manifests/summary.json` rather than copied into
application code.

## Ground truth separation

`cohorts/*/transactions.csv` has no label, scenario, campaign, or cohort
field. `ground_truth/event_labels.csv` contains those fields for offline
evaluation only. `ground_truth/campaigns.csv` contains campaign boundaries,
affected entities, and generation parameters.

Never join ground truth into a training or inference feature frame. M02 will
enforce that constraint in the feature pipeline and tests.
