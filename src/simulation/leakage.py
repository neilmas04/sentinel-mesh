"""Static leakage and synthetic-artifact checks for a generated M01 dataset."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


COHORTS = ("train", "validation", "test")
FORBIDDEN_MODEL_FIELDS = {"is_abuse", "is_fraud", "scenario", "campaign_id", "cohort", "label", "target"}
OPAQUE_ID = re.compile(r"^id_[0-9a-f]{20}$")


def run_leakage_checks(dataset_dir: Path | str) -> dict[str, Any]:
    """Check the M01 data contract without reading labels into model inputs."""

    dataset_dir = Path(dataset_dir)
    checks: list[dict[str, Any]] = []
    violations: list[str] = []
    split_manifest = _read_json(dataset_dir / "manifests" / "split_manifest.json")
    windows = {item["name"]: (datetime.fromisoformat(item["start"]), datetime.fromisoformat(item["end"])) for item in split_manifest["cohorts"]}
    transaction_rows: dict[str, list[dict[str, str]]] = {}
    transaction_by_id: dict[str, dict[str, str]] = {}

    forbidden_headers: dict[str, list[str]] = {}
    duplicate_ids: list[str] = []
    bad_order: list[str] = []
    out_of_window: list[str] = []
    for cohort in COHORTS:
        path = dataset_dir / "cohorts" / cohort / "transactions.csv"
        rows, headers = _read_csv(path)
        transaction_rows[cohort] = rows
        leaked = sorted(FORBIDDEN_MODEL_FIELDS.intersection(headers))
        if leaked:
            forbidden_headers[cohort] = leaked
        timestamps = [datetime.fromisoformat(row["timestamp"]) for row in rows]
        if timestamps != sorted(timestamps):
            bad_order.append(cohort)
        start, end = windows[cohort]
        if any(timestamp < start or timestamp >= end for timestamp in timestamps):
            out_of_window.append(cohort)
        for row in rows:
            transaction_id = row["transaction_id"]
            if transaction_id in transaction_by_id:
                duplicate_ids.append(transaction_id)
            transaction_by_id[transaction_id] = row
    _record(checks, violations, "model_input_has_no_ground_truth_fields", not forbidden_headers, forbidden_headers)
    _record(checks, violations, "transaction_ids_are_unique", not duplicate_ids, {"duplicate_count": len(duplicate_ids)})
    _record(checks, violations, "transactions_are_time_sorted", not bad_order, {"bad_cohorts": bad_order})
    _record(checks, violations, "transactions_stay_inside_temporal_cohorts", not out_of_window, {"bad_cohorts": out_of_window})

    labels, _ = _read_csv(dataset_dir / "ground_truth" / "event_labels.csv")
    label_ids = {row["transaction_id"] for row in labels}
    coverage_ok = label_ids == set(transaction_by_id) and len(label_ids) == len(labels)
    _record(
        checks, violations, "ground_truth_has_exactly_one_label_per_event", coverage_ok,
        {"events": len(transaction_by_id), "labels": len(labels), "unique_label_ids": len(label_ids)},
    )
    label_by_id = {row["transaction_id"]: row for row in labels}
    misplaced_labels = [transaction_id for transaction_id, row in transaction_by_id.items() if label_by_id.get(transaction_id, {}).get("cohort") not in COHORTS]
    _record(checks, violations, "labels_have_valid_cohorts", not misplaced_labels, {"invalid_count": len(misplaced_labels)})

    accounts, _ = _read_csv(dataset_dir / "entities" / "accounts.csv")
    devices, _ = _read_csv(dataset_dir / "entities" / "devices.csv")
    networks, _ = _read_csv(dataset_dir / "entities" / "network_groups.csv")
    account_cohort = {row["account_id"]: row["cohort"] for row in accounts}
    device_cohort = {row["device_id"]: row["cohort"] for row in devices}
    network_cohort = {row["network_group_id"]: row["cohort"] for row in networks}
    entity_cohort_mismatches: list[str] = []
    invalid_ids: list[str] = []
    for cohort, rows in transaction_rows.items():
        for row in rows:
            if account_cohort.get(row["account_id"]) != cohort or device_cohort.get(row["device_id"]) != cohort or network_cohort.get(row["network_group_id"]) != cohort:
                entity_cohort_mismatches.append(row["transaction_id"])
            for field in ("transaction_id", "merchant_id", "account_id", "device_id", "network_group_id"):
                if not OPAQUE_ID.fullmatch(row[field]):
                    invalid_ids.append(row[field])
    _record(checks, violations, "account_device_network_entities_are_cohort_disjoint", not entity_cohort_mismatches, {"mismatch_count": len(entity_cohort_mismatches)})
    _record(checks, violations, "identifiers_are_opaque_and_scenario_neutral", not invalid_ids, {"invalid_count": len(invalid_ids)})

    campaigns, _ = _read_csv(dataset_dir / "ground_truth" / "campaigns.csv")
    campaign_by_id = {row["campaign_id"]: row for row in campaigns}
    campaign_violations: list[str] = []
    campaign_event_ids: dict[str, list[str]] = defaultdict(list)
    for label in labels:
        if label["campaign_id"]:
            campaign_event_ids[label["campaign_id"]].append(label["transaction_id"])
            campaign = campaign_by_id.get(label["campaign_id"])
            if campaign is None or campaign["cohort"] != label["cohort"] or campaign["scenario"] != label["scenario"]:
                campaign_violations.append(label["transaction_id"])
    for campaign_id, event_ids in campaign_event_ids.items():
        campaign = campaign_by_id[campaign_id]
        if int(campaign["event_count"]) != len(event_ids):
            campaign_violations.append(campaign_id)
    _record(checks, violations, "campaigns_do_not_cross_cohorts", not campaign_violations, {"violation_count": len(campaign_violations)})

    artifact_violations: list[str] = []
    for campaign_id, event_ids in campaign_event_ids.items():
        campaign = campaign_by_id[campaign_id]
        if campaign["is_abuse"] != "1":
            continue
        events = sorted((transaction_by_id[event_id] for event_id in event_ids), key=lambda row: row["timestamp"])
        amounts = {row["amount"] for row in events}
        timestamps = [datetime.fromisoformat(row["timestamp"]) for row in events]
        intervals = {
            round((current - previous).total_seconds(), 6)
            for previous, current in zip(timestamps, timestamps[1:])
        }
        if len(amounts) < min(3, len(events)) or len(intervals) < min(3, max(1, len(events) - 1)):
            artifact_violations.append(campaign_id)
    _record(checks, violations, "abuse_campaigns_do_not_use_constant_amount_or_interval_signatures", not artifact_violations, {"violation_count": len(artifact_violations)})

    scenario_by_cohort: dict[str, set[str]] = defaultdict(set)
    for label in labels:
        scenario_by_cohort[label["cohort"]].add(label["scenario"])
    scenario_coverage_ok = all(len(scenario_by_cohort[cohort]) == 9 for cohort in COHORTS)
    _record(checks, violations, "each_cohort_contains_all_required_scenario_families", scenario_coverage_ok, {key: sorted(value) for key, value in scenario_by_cohort.items()})

    return {
        "status": "pass" if not violations else "fail",
        "dataset_dir": str(dataset_dir),
        "checks": checks,
        "violations": violations,
    }


def _read_csv(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), set(reader.fieldnames or [])


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _record(checks: list[dict[str, Any]], violations: list[str], name: str, passed: bool, details: dict[str, Any]) -> None:
    checks.append({"name": name, "status": "pass" if passed else "fail", "details": details})
    if not passed:
        violations.append(name)
