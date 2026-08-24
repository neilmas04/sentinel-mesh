import csv
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.simulation.leakage import run_leakage_checks
from src.simulation.m01_world import SCENARIOS, SimulationConfig, generate_dataset


SMALL_CONFIG = SimulationConfig(
    seed=17,
    dataset_version="m01-test-world",
    train_days=4,
    validation_days=2,
    test_days=2,
    merchant_count=25,
    accounts_per_cohort=110,
    devices_per_cohort=90,
    networks_per_cohort=45,
    baseline_events_per_day=35,
    high_volume_events=20,
    family_events=16,
    corporate_events=18,
    cross_merchant_burst_events=22,
    single_merchant_events=20,
    distributed_abuse_events=28,
    sleeper_activation_events=20,
    accelerating_cluster_events=28,
)


class M01SyntheticWorldTests(unittest.TestCase):
    def test_same_configuration_produces_identical_model_and_truth_data(self) -> None:
        with tempfile.TemporaryDirectory() as first_root, tempfile.TemporaryDirectory() as second_root:
            first = generate_dataset(first_root, SMALL_CONFIG)
            second = generate_dataset(second_root, SMALL_CONFIG)
            self.assertEqual(_fingerprint(first), _fingerprint(second))

    def test_transaction_contract_hides_ground_truth_and_leakage_report_passes(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            dataset_dir = generate_dataset(root, SMALL_CONFIG)
            report = run_leakage_checks(dataset_dir)
            self.assertEqual("pass", report["status"], report["violations"])
            for cohort in ("train", "validation", "test"):
                with (dataset_dir / "cohorts" / cohort / "transactions.csv").open(encoding="utf-8", newline="") as handle:
                    headers = set(csv.DictReader(handle).fieldnames or [])
                self.assertFalse({"is_abuse", "is_fraud", "scenario", "campaign_id", "cohort"}.intersection(headers))

    def test_every_cohort_has_the_required_scenario_families(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            dataset_dir = generate_dataset(root, replace(SMALL_CONFIG, seed=91))
            with (dataset_dir / "ground_truth" / "event_labels.csv").open(encoding="utf-8", newline="") as handle:
                labels = list(csv.DictReader(handle))
            for cohort in ("train", "validation", "test"):
                scenarios = {row["scenario"] for row in labels if row["cohort"] == cohort}
                self.assertEqual(set(SCENARIOS), scenarios)


def _fingerprint(dataset_dir: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for path in sorted(dataset_dir.rglob("*")):
        if not path.is_file() or path.name == "leakage_report.json":
            continue
        fingerprints[str(path.relative_to(dataset_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprints


if __name__ == "__main__":
    unittest.main()
