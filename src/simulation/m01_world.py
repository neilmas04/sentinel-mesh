"""Deterministic, versioned synthetic payment world for Sentinel Mesh M01.

The transaction files written by this module are safe model inputs: they contain
only fields that may be known at a transaction decision time.  Labels,
scenarios, campaign membership, cohort assignments, and generator parameters
are intentionally written to separate ground-truth and manifest files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DATASET_VERSION = "m01-world-v1"
GENERATOR_VERSION = "1.0.0"
COHORT_NAMES = ("train", "validation", "test")
SCENARIOS = (
    "normal_baseline",
    "legitimate_high_volume_event",
    "benign_family_shared_device",
    "benign_corporate_shared_network",
    "legitimate_cross_merchant_burst",
    "single_merchant_anomaly",
    "distributed_coordinated_abuse",
    "sleeper_account_activation",
    "accelerating_coordinated_cluster",
)


@dataclass(frozen=True)
class SimulationConfig:
    """The complete, serializable configuration for one M01 dataset."""

    seed: int = 20_260_824
    dataset_version: str = DATASET_VERSION
    start_at: str = "2026-01-01T00:00:00+00:00"
    train_days: int = 14
    validation_days: int = 7
    test_days: int = 7
    merchant_count: int = 45
    accounts_per_cohort: int = 900
    devices_per_cohort: int = 720
    networks_per_cohort: int = 360
    baseline_events_per_day: int = 1_500
    high_volume_events: int = 280
    family_events: int = 72
    corporate_events: int = 120
    cross_merchant_burst_events: int = 180
    single_merchant_events: int = 130
    distributed_abuse_events: int = 260
    sleeper_activation_events: int = 150
    accelerating_cluster_events: int = 240

    @property
    def start_datetime(self) -> datetime:
        return datetime.fromisoformat(self.start_at)


@dataclass(frozen=True)
class CohortWindow:
    name: str
    start: datetime
    end: datetime


@dataclass
class Campaign:
    campaign_id: str
    cohort: str
    scenario: str
    is_abuse: int
    parameters: dict[str, Any]
    transaction_ids: list[str] = field(default_factory=list)
    merchant_ids: set[str] = field(default_factory=set)
    account_ids: set[str] = field(default_factory=set)
    device_ids: set[str] = field(default_factory=set)
    network_ids: set[str] = field(default_factory=set)


class StableIdFactory:
    """Creates opaque, deterministic identifiers without scenario-specific names."""

    def __init__(self, dataset_version: str, seed: int) -> None:
        self._prefix = f"{dataset_version}|{seed}"
        self._counts: dict[str, int] = {}

    def next(self, namespace: str) -> str:
        index = self._counts.get(namespace, 0)
        self._counts[namespace] = index + 1
        digest = hashlib.sha256(f"{self._prefix}|{namespace}|{index}".encode()).hexdigest()
        return f"id_{digest[:20]}"


class SyntheticPaymentWorld:
    """Builds a relationship-consistent payment world using only ``random.Random``.

    NumPy is deliberately not used: this keeps M01 executable in the current
    environment and leaves a single seeded random source to control.
    """

    _CATEGORY_PROFILES = (
        ("digital_goods", 14.0, 0.48),
        ("food_delivery", 24.0, 0.40),
        ("fashion_retail", 58.0, 0.55),
        ("electronics", 185.0, 0.62),
        ("travel", 240.0, 0.68),
        ("subscription", 18.0, 0.34),
    )
    _DEVICE_TYPES = ("mobile", "desktop", "tablet")
    _PAYMENT_CATEGORIES = ("card_purchase", "wallet_purchase", "recurring_purchase")

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.ids = StableIdFactory(config.dataset_version, config.seed)
        self.windows = self._build_windows()
        self.merchants: dict[str, dict[str, Any]] = {}
        self.accounts: dict[str, dict[str, Any]] = {}
        self.devices: dict[str, dict[str, Any]] = {}
        self.networks: dict[str, dict[str, Any]] = {}
        self.transactions: list[dict[str, Any]] = []
        self.labels: list[dict[str, Any]] = []
        self.campaigns: list[Campaign] = []
        self.cohort_accounts: dict[str, list[str]] = {name: [] for name in COHORT_NAMES}
        self.cohort_devices: dict[str, list[str]] = {name: [] for name in COHORT_NAMES}
        self.cohort_networks: dict[str, list[str]] = {name: [] for name in COHORT_NAMES}

    def _build_windows(self) -> tuple[CohortWindow, ...]:
        start = self.config.start_datetime.astimezone(timezone.utc)
        train_end = start + timedelta(days=self.config.train_days)
        validation_end = train_end + timedelta(days=self.config.validation_days)
        test_end = validation_end + timedelta(days=self.config.test_days)
        return (
            CohortWindow("train", start, train_end),
            CohortWindow("validation", train_end, validation_end),
            CohortWindow("test", validation_end, test_end),
        )

    def build(self) -> None:
        self._create_merchants()
        for window in self.windows:
            self._create_cohort_entities(window)
        for window in self.windows:
            self._generate_cohort(window)
        self._sort_records()
        self._finalize_entity_relationship_counts()

    def _create_merchants(self) -> None:
        profiles = list(self._CATEGORY_PROFILES)
        for index in range(self.config.merchant_count):
            category, amount_mean, amount_sigma = profiles[index % len(profiles)]
            merchant_id = self.ids.next("entity")
            self.merchants[merchant_id] = {
                "merchant_id": merchant_id,
                "category": category,
                "amount_mean": round(amount_mean * self.rng.uniform(0.85, 1.15), 2),
                "amount_log_sigma": round(amount_sigma, 3),
                "base_daily_volume": self.rng.randint(180, 1_500),
            }

    def _create_cohort_entities(self, window: CohortWindow) -> None:
        for _ in range(self.config.networks_per_cohort):
            network_id = self._create_network(window.name, self.rng.choice(("residential", "mobile", "office")))
            self.cohort_networks[window.name].append(network_id)

        for _ in range(self.config.devices_per_cohort):
            network_id = self.rng.choice(self.cohort_networks[window.name])
            device_id = self._create_device(window.name, self.rng.choice(self._DEVICE_TYPES), network_id)
            self.cohort_devices[window.name].append(device_id)

        merchant_ids = list(self.merchants)
        for account_index in range(self.config.accounts_per_cohort):
            account_id = self.ids.next("entity")
            segment = "sleeper" if account_index < max(24, self.config.accounts_per_cohort // 25) else self.rng.choices(
                ("regular", "frequent", "occasional"), weights=(0.72, 0.18, 0.10), k=1
            )[0]
            primary_device = self.rng.choice(self.cohort_devices[window.name])
            primary_network = self.devices[primary_device]["home_network_group_id"]
            device_ids = [primary_device]
            if self.rng.random() < 0.16:
                device_ids.append(self.rng.choice(self.cohort_devices[window.name]))
            preferences = self.rng.sample(merchant_ids, k=min(3, len(merchant_ids)))
            created_at = window.start - timedelta(days=self.rng.randint(30, 720), minutes=self.rng.randint(0, 1_440))
            self.accounts[account_id] = {
                "account_id": account_id,
                "created_at": _iso(created_at),
                "cohort": window.name,
                "account_segment": segment,
                "primary_network_group_id": primary_network,
                "primary_device_id": primary_device,
                "device_ids": list(dict.fromkeys(device_ids)),
                "merchant_preferences": preferences,
                "spend_multiplier": round(self.rng.uniform(0.75, 1.35), 3),
            }
            self.cohort_accounts[window.name].append(account_id)

    def _create_network(self, cohort: str, network_type: str) -> str:
        network_id = self.ids.next("entity")
        self.networks[network_id] = {
            "network_group_id": network_id,
            "cohort": cohort,
            "network_type": network_type,
        }
        return network_id

    def _create_device(self, cohort: str, device_type: str, network_id: str) -> str:
        device_id = self.ids.next("entity")
        self.devices[device_id] = {
            "device_id": device_id,
            "cohort": cohort,
            "device_type": device_type,
            "home_network_group_id": network_id,
        }
        return device_id

    def _generate_cohort(self, window: CohortWindow) -> None:
        self._generate_normal_baseline(window)
        self._generate_high_volume_event(window)
        self._generate_family_shared_device(window)
        self._generate_corporate_shared_network(window)
        self._generate_legitimate_cross_merchant_burst(window)
        self._generate_single_merchant_anomaly(window)
        self._generate_distributed_coordinated_abuse(window)
        self._generate_sleeper_account_activation(window)
        self._generate_accelerating_cluster(window)

    def _generate_normal_baseline(self, window: CohortWindow) -> None:
        accounts = [account_id for account_id in self.cohort_accounts[window.name] if self.accounts[account_id]["account_segment"] != "sleeper"]
        weights = [2.8 if self.accounts[account_id]["account_segment"] == "frequent" else 0.65 if self.accounts[account_id]["account_segment"] == "occasional" else 1.0 for account_id in accounts]
        event_count = self.config.baseline_events_per_day * int((window.end - window.start).days)
        for _ in range(event_count):
            account_id = self.rng.choices(accounts, weights=weights, k=1)[0]
            account = self.accounts[account_id]
            merchant_id = self._merchant_for_account(account)
            device_id = self.rng.choice(account["device_ids"])
            network_id = self.devices[device_id]["home_network_group_id"] if self.rng.random() < 0.91 else account["primary_network_group_id"]
            timestamp = self._customer_timestamp(window)
            amount = self._sample_amount(merchant_id, account["spend_multiplier"])
            self._add_transaction(
                timestamp, merchant_id, account_id, device_id, network_id, amount, window.name, "normal_baseline", 0, None
            )

    def _generate_high_volume_event(self, window: CohortWindow) -> None:
        merchant_id = max(self.merchants, key=lambda item: self.merchants[item]["base_daily_volume"])
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(260, len(self.cohort_accounts[window.name])))
        campaign = self._start_campaign(window.name, "legitimate_high_volume_event", 0, {"merchant_count": 1})
        start, end = self._event_window(window, duration_hours=8)
        for _ in range(self.config.high_volume_events):
            account_id = self.rng.choice(accounts)
            account = self.accounts[account_id]
            device_id = self.rng.choice(account["device_ids"])
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, device_id,
                self.devices[device_id]["home_network_group_id"], self._sample_amount(merchant_id, account["spend_multiplier"]),
                window.name, campaign.scenario, 0, campaign,
            )
        self._close_campaign(campaign)

    def _generate_family_shared_device(self, window: CohortWindow) -> None:
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(self.rng.randint(4, 7), len(self.cohort_accounts[window.name])))
        shared_network = self._create_network(window.name, "residential_shared")
        shared_device = self._create_device(window.name, "tablet", shared_network)
        self.cohort_networks[window.name].append(shared_network)
        self.cohort_devices[window.name].append(shared_device)
        for account_id in accounts:
            self.accounts[account_id]["device_ids"].append(shared_device)
        campaign = self._start_campaign(window.name, "benign_family_shared_device", 0, {"household_accounts": len(accounts)})
        start, end = self._event_window(window, duration_hours=14)
        for _ in range(self.config.family_events):
            account_id = self.rng.choice(accounts)
            merchant_id = self._merchant_for_account(self.accounts[account_id])
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, shared_device, shared_network,
                self._sample_amount(merchant_id, self.accounts[account_id]["spend_multiplier"]), window.name,
                campaign.scenario, 0, campaign,
            )
        self._close_campaign(campaign)

    def _generate_corporate_shared_network(self, window: CohortWindow) -> None:
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(self.rng.randint(20, 35), len(self.cohort_accounts[window.name])))
        office_network = self._create_network(window.name, "corporate_shared")
        self.cohort_networks[window.name].append(office_network)
        campaign = self._start_campaign(window.name, "benign_corporate_shared_network", 0, {"employee_accounts": len(accounts)})
        start, end = self._event_window(window, duration_hours=9)
        for _ in range(self.config.corporate_events):
            account_id = self.rng.choice(accounts)
            account = self.accounts[account_id]
            merchant_id = self._merchant_for_account(account)
            device_id = self.rng.choice(account["device_ids"])
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, device_id, office_network,
                self._sample_amount(merchant_id, account["spend_multiplier"]), window.name, campaign.scenario, 0, campaign,
            )
        self._close_campaign(campaign)

    def _generate_legitimate_cross_merchant_burst(self, window: CohortWindow) -> None:
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(self.rng.randint(38, 58), len(self.cohort_accounts[window.name])))
        merchants = self.rng.sample(list(self.merchants), k=min(self.rng.randint(5, 9), len(self.merchants)))
        campaign = self._start_campaign(window.name, "legitimate_cross_merchant_burst", 0, {"merchant_count": len(merchants)})
        start, end = self._event_window(window, duration_hours=5)
        for _ in range(self.config.cross_merchant_burst_events):
            account_id = self.rng.choice(accounts)
            account = self.accounts[account_id]
            device_id = self.rng.choice(account["device_ids"])
            merchant_id = self.rng.choice(merchants)
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, device_id,
                self.devices[device_id]["home_network_group_id"], self._sample_amount(merchant_id, account["spend_multiplier"]),
                window.name, campaign.scenario, 0, campaign,
            )
        self._close_campaign(campaign)

    def _generate_single_merchant_anomaly(self, window: CohortWindow) -> None:
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(self.rng.randint(12, 22), len(self.cohort_accounts[window.name])))
        merchant_id = self.rng.choice(list(self.merchants))
        devices, networks = self._shared_attack_infrastructure(window.name, device_count=self.rng.randint(2, 5), network_count=self.rng.randint(1, 3))
        campaign = self._start_campaign(window.name, "single_merchant_anomaly", 1, {"merchant_count": 1, "account_count": len(accounts)})
        start, end = self._event_window(window, duration_hours=self.rng.randint(2, 5))
        for _ in range(self.config.single_merchant_events):
            account_id = self.rng.choice(accounts)
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, self.rng.choice(devices), self.rng.choice(networks),
                self._sample_amount(merchant_id, self.rng.uniform(0.65, 1.85)), window.name, campaign.scenario, 1, campaign,
            )
        self._close_campaign(campaign)

    def _generate_distributed_coordinated_abuse(self, window: CohortWindow) -> None:
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(self.rng.randint(20, 38), len(self.cohort_accounts[window.name])))
        min_merchants, max_merchants = (7, 13) if window.name == "test" else (4, 10)
        merchants = self.rng.sample(list(self.merchants), k=min(self.rng.randint(min_merchants, max_merchants), len(self.merchants)))
        devices, networks = self._shared_attack_infrastructure(window.name, device_count=self.rng.randint(2, 6), network_count=self.rng.randint(1, 3))
        campaign = self._start_campaign(
            window.name, "distributed_coordinated_abuse", 1,
            {"merchant_count": len(merchants), "account_count": len(accounts), "device_count": len(devices), "network_count": len(networks)},
        )
        start, end = self._event_window(window, duration_hours=self.rng.randint(3, 7))
        for _ in range(self.config.distributed_abuse_events):
            account_id = self.rng.choice(accounts)
            merchant_id = self.rng.choice(merchants)
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, self.rng.choice(devices), self.rng.choice(networks),
                self._sample_amount(merchant_id, self.rng.uniform(0.45, 1.45)), window.name, campaign.scenario, 1, campaign,
            )
        self._close_campaign(campaign)

    def _generate_sleeper_account_activation(self, window: CohortWindow) -> None:
        sleepers = [account_id for account_id in self.cohort_accounts[window.name] if self.accounts[account_id]["account_segment"] == "sleeper"]
        accounts = self.rng.sample(sleepers, k=min(self.rng.randint(18, 28), len(sleepers)))
        merchants = self.rng.sample(list(self.merchants), k=min(self.rng.randint(3, 7), len(self.merchants)))
        devices, networks = self._shared_attack_infrastructure(window.name, device_count=self.rng.randint(2, 5), network_count=self.rng.randint(1, 3))
        campaign = self._start_campaign(
            window.name, "sleeper_account_activation", 1,
            {"merchant_count": len(merchants), "sleeper_account_count": len(accounts)},
        )
        start, end = self._event_window(window, duration_hours=self.rng.randint(4, 8))
        for _ in range(self.config.sleeper_activation_events):
            account_id = self.rng.choice(accounts)
            merchant_id = self.rng.choice(merchants)
            self._add_transaction(
                self._timestamp_between(start, end), merchant_id, account_id, self.rng.choice(devices), self.rng.choice(networks),
                self._sample_amount(merchant_id, self.rng.uniform(0.70, 1.60)), window.name, campaign.scenario, 1, campaign,
            )
        self._close_campaign(campaign)

    def _generate_accelerating_cluster(self, window: CohortWindow) -> None:
        accounts = self.rng.sample(self.cohort_accounts[window.name], k=min(self.rng.randint(28, 48), len(self.cohort_accounts[window.name])))
        merchants = self.rng.sample(list(self.merchants), k=min(self.rng.randint(5, 11), len(self.merchants)))
        devices, networks = self._shared_attack_infrastructure(window.name, device_count=self.rng.randint(3, 7), network_count=self.rng.randint(1, 3))
        campaign = self._start_campaign(
            window.name, "accelerating_coordinated_cluster", 1,
            {"merchant_count": len(merchants), "max_account_count": len(accounts), "waves": 4},
        )
        start, end = self._event_window(window, duration_hours=self.rng.randint(5, 10))
        wave_sizes = [max(3, len(accounts) // 8), max(6, len(accounts) // 4), max(10, len(accounts) // 2), len(accounts)]
        event_budget = self.config.accelerating_cluster_events
        for wave_index, active_count in enumerate(wave_sizes):
            wave_start = start + (end - start) * (wave_index / len(wave_sizes))
            wave_end = start + (end - start) * ((wave_index + 1) / len(wave_sizes))
            wave_events = event_budget // len(wave_sizes) + (1 if wave_index < event_budget % len(wave_sizes) else 0)
            for _ in range(wave_events):
                account_id = self.rng.choice(accounts[:active_count])
                merchant_id = self.rng.choice(merchants)
                self._add_transaction(
                    self._timestamp_between(wave_start, wave_end), merchant_id, account_id, self.rng.choice(devices), self.rng.choice(networks),
                    self._sample_amount(merchant_id, self.rng.uniform(0.55, 1.70)), window.name, campaign.scenario, 1, campaign,
                )
        self._close_campaign(campaign)

    def _shared_attack_infrastructure(self, cohort: str, device_count: int, network_count: int) -> tuple[list[str], list[str]]:
        networks = [self._create_network(cohort, "shared_service") for _ in range(network_count)]
        devices = [self._create_device(cohort, self.rng.choice(self._DEVICE_TYPES), self.rng.choice(networks)) for _ in range(device_count)]
        self.cohort_networks[cohort].extend(networks)
        self.cohort_devices[cohort].extend(devices)
        return devices, networks

    def _start_campaign(self, cohort: str, scenario: str, is_abuse: int, parameters: dict[str, Any]) -> Campaign:
        campaign = Campaign(self.ids.next("campaign"), cohort, scenario, is_abuse, parameters)
        self.campaigns.append(campaign)
        return campaign

    def _close_campaign(self, campaign: Campaign) -> None:
        if not campaign.transaction_ids:
            raise ValueError(f"Campaign {campaign.campaign_id} generated no events")

    def _add_transaction(
        self,
        timestamp: datetime,
        merchant_id: str,
        account_id: str,
        device_id: str,
        network_id: str,
        amount: float,
        cohort: str,
        scenario: str,
        is_abuse: int,
        campaign: Campaign | None,
    ) -> None:
        transaction_id = self.ids.next("transaction")
        transaction = {
            "transaction_id": transaction_id,
            "timestamp": _iso(timestamp),
            "merchant_id": merchant_id,
            "account_id": account_id,
            "device_id": device_id,
            "network_group_id": network_id,
            "amount": f"{amount:.2f}",
            "payment_category": self.rng.choices(self._PAYMENT_CATEGORIES, weights=(0.76, 0.17, 0.07), k=1)[0],
            "status": self.rng.choices(("authorized", "declined"), weights=(0.965, 0.035), k=1)[0],
        }
        self.transactions.append(transaction)
        self.labels.append(
            {
                "transaction_id": transaction_id,
                "is_abuse": is_abuse,
                "campaign_id": campaign.campaign_id if campaign else "",
                "scenario": scenario,
                "cohort": cohort,
            }
        )
        if campaign:
            campaign.transaction_ids.append(transaction_id)
            campaign.merchant_ids.add(merchant_id)
            campaign.account_ids.add(account_id)
            campaign.device_ids.add(device_id)
            campaign.network_ids.add(network_id)

    def _merchant_for_account(self, account: dict[str, Any]) -> str:
        if self.rng.random() < 0.78:
            return self.rng.choice(account["merchant_preferences"])
        return self.rng.choice(list(self.merchants))

    def _sample_amount(self, merchant_id: str, multiplier: float) -> float:
        merchant = self.merchants[merchant_id]
        amount = self.rng.lognormvariate(math.log(merchant["amount_mean"] * multiplier), merchant["amount_log_sigma"])
        return max(1.0, min(round(amount, 2), 2_500.0))

    def _event_window(self, window: CohortWindow, duration_hours: int) -> tuple[datetime, datetime]:
        available_seconds = max(1, int((window.end - window.start).total_seconds() - duration_hours * 3_600 - 3_600))
        start = window.start + timedelta(seconds=self.rng.randint(3_600, available_seconds + 3_600))
        return start, min(start + timedelta(hours=duration_hours), window.end - timedelta(seconds=1))

    def _customer_timestamp(self, window: CohortWindow) -> datetime:
        day = window.start + timedelta(days=self.rng.randrange(max(1, (window.end - window.start).days)))
        hour = int(self.rng.triangular(7, 23, 14))
        return day.replace(hour=hour, minute=self.rng.randrange(60), second=self.rng.randrange(60), microsecond=self.rng.randrange(1_000_000))

    def _timestamp_between(self, start: datetime, end: datetime) -> datetime:
        seconds = max(1, int((end - start).total_seconds()))
        return start + timedelta(seconds=self.rng.randrange(seconds), microseconds=self.rng.randrange(1_000_000))

    def _sort_records(self) -> None:
        self.transactions.sort(key=lambda item: (item["timestamp"], item["transaction_id"]))
        label_by_transaction = {label["transaction_id"]: label for label in self.labels}
        self.labels = [label_by_transaction[transaction["transaction_id"]] for transaction in self.transactions]

    def _finalize_entity_relationship_counts(self) -> None:
        device_accounts: dict[str, set[str]] = {device_id: set() for device_id in self.devices}
        network_accounts: dict[str, set[str]] = {network_id: set() for network_id in self.networks}
        for account in self.accounts.values():
            for device_id in account["device_ids"]:
                device_accounts.setdefault(device_id, set()).add(account["account_id"])
            network_accounts.setdefault(account["primary_network_group_id"], set()).add(account["account_id"])
        for device_id, device in self.devices.items():
            device["associated_account_count"] = len(device_accounts.get(device_id, set()))
        for network_id, network in self.networks.items():
            network["associated_account_count"] = len(network_accounts.get(network_id, set()))

    def transaction_rows_by_cohort(self) -> dict[str, list[dict[str, Any]]]:
        labels = {label["transaction_id"]: label for label in self.labels}
        rows = {name: [] for name in COHORT_NAMES}
        for transaction in self.transactions:
            rows[labels[transaction["transaction_id"]]["cohort"]].append(transaction)
        return rows

    def campaign_rows(self) -> list[dict[str, Any]]:
        transaction_by_id = {transaction["transaction_id"]: transaction for transaction in self.transactions}
        rows: list[dict[str, Any]] = []
        for campaign in self.campaigns:
            timestamps = sorted(transaction_by_id[transaction_id]["timestamp"] for transaction_id in campaign.transaction_ids)
            rows.append(
                {
                    "campaign_id": campaign.campaign_id,
                    "cohort": campaign.cohort,
                    "scenario": campaign.scenario,
                    "is_abuse": campaign.is_abuse,
                    "start_timestamp": timestamps[0],
                    "end_timestamp": timestamps[-1],
                    "event_count": len(campaign.transaction_ids),
                    "affected_merchants": json.dumps(sorted(campaign.merchant_ids)),
                    "affected_accounts": json.dumps(sorted(campaign.account_ids)),
                    "affected_devices": json.dumps(sorted(campaign.device_ids)),
                    "affected_network_groups": json.dumps(sorted(campaign.network_ids)),
                    "parameters": json.dumps(campaign.parameters, sort_keys=True),
                }
            )
        return rows

    def entity_rows(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "merchants": list(self.merchants.values()),
            "accounts": [
                {key: value for key, value in account.items() if key not in {"device_ids", "merchant_preferences", "spend_multiplier"}}
                for account in self.accounts.values()
            ],
            "devices": list(self.devices.values()),
            "network_groups": list(self.networks.values()),
        }

    def summary(self) -> dict[str, Any]:
        labels_by_scenario: dict[str, int] = {}
        labels_by_cohort: dict[str, dict[str, int]] = {name: {} for name in COHORT_NAMES}
        for label in self.labels:
            labels_by_scenario[label["scenario"]] = labels_by_scenario.get(label["scenario"], 0) + 1
            bucket = labels_by_cohort[label["cohort"]]
            bucket[label["scenario"]] = bucket.get(label["scenario"], 0) + 1
        return {
            "dataset_version": self.config.dataset_version,
            "generator_version": GENERATOR_VERSION,
            "seed": self.config.seed,
            "transaction_count": len(self.transactions),
            "abuse_event_count": sum(label["is_abuse"] for label in self.labels),
            "entity_counts": {
                "merchants": len(self.merchants),
                "accounts": len(self.accounts),
                "devices": len(self.devices),
                "network_groups": len(self.networks),
            },
            "scenario_counts": labels_by_scenario,
            "cohort_scenario_counts": labels_by_cohort,
        }


def generate_dataset(output_root: Path | str = Path("data/generated"), config: SimulationConfig | None = None) -> Path:
    """Generate M01 data, manifests, and a leakage report; return its directory."""

    config = config or SimulationConfig()
    world = SyntheticPaymentWorld(config)
    world.build()
    dataset_dir = Path(output_root) / config.dataset_version
    entities_dir = dataset_dir / "entities"
    truth_dir = dataset_dir / "ground_truth"
    manifests_dir = dataset_dir / "manifests"
    for directory in (entities_dir, truth_dir, manifests_dir, *(dataset_dir / "cohorts" / name for name in COHORT_NAMES)):
        directory.mkdir(parents=True, exist_ok=True)

    transaction_fields = (
        "transaction_id", "timestamp", "merchant_id", "account_id", "device_id", "network_group_id", "amount", "payment_category", "status",
    )
    for cohort, rows in world.transaction_rows_by_cohort().items():
        _write_csv(dataset_dir / "cohorts" / cohort / "transactions.csv", transaction_fields, rows)

    entity_fields = {
        "merchants": ("merchant_id", "category", "amount_mean", "amount_log_sigma", "base_daily_volume"),
        "accounts": ("account_id", "created_at", "cohort", "account_segment", "primary_network_group_id", "primary_device_id"),
        "devices": ("device_id", "cohort", "device_type", "home_network_group_id", "associated_account_count"),
        "network_groups": ("network_group_id", "cohort", "network_type", "associated_account_count"),
    }
    for name, rows in world.entity_rows().items():
        _write_csv(entities_dir / f"{name}.csv", entity_fields[name], rows)

    _write_csv(
        truth_dir / "event_labels.csv",
        ("transaction_id", "is_abuse", "campaign_id", "scenario", "cohort"),
        world.labels,
    )
    _write_csv(
        truth_dir / "campaigns.csv",
        (
            "campaign_id", "cohort", "scenario", "is_abuse", "start_timestamp", "end_timestamp", "event_count",
            "affected_merchants", "affected_accounts", "affected_devices", "affected_network_groups", "parameters",
        ),
        world.campaign_rows(),
    )
    split_manifest = {
        "method": "temporal cohorts with account/device/network disjointness; merchants are shared intentionally",
        "cohorts": [{"name": window.name, "start": _iso(window.start), "end": _iso(window.end)} for window in world.windows],
        "test_policy": "The test cohort is held out. Campaigns and account/device/network entities are not shared with train or validation.",
    }
    _write_json(manifests_dir / "generation_config.json", {"generator_version": GENERATOR_VERSION, "config": asdict(config)})
    _write_json(manifests_dir / "split_manifest.json", split_manifest)
    _write_json(manifests_dir / "summary.json", world.summary())

    from src.simulation.leakage import run_leakage_checks

    leakage_report = run_leakage_checks(dataset_dir)
    _write_json(manifests_dir / "leakage_report.json", leakage_report)
    if leakage_report["status"] != "pass":
        raise RuntimeError(f"Leakage checks failed: {leakage_report['violations']}")
    return dataset_dir


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Sentinel Mesh M01 synthetic payment world.")
    parser.add_argument("--output-root", default="data/generated", help="Directory that will contain the versioned dataset.")
    parser.add_argument("--seed", type=int, default=SimulationConfig.seed, help="Deterministic generator seed.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    config = SimulationConfig(seed=args.seed)
    dataset_dir = generate_dataset(args.output_root, config)
    summary = json.loads((dataset_dir / "manifests" / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps({"dataset_dir": str(dataset_dir), **summary}, indent=2, sort_keys=True))
    return 0


def _write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
