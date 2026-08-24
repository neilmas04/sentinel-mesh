# src/simulation/engine.py
import os
import random
from datetime import datetime, timedelta
from typing import List
import pandas as pd

from src.simulation.schemas import Merchant, Account, Device, Transaction
from src.simulation.behavior import generate_id
from src.simulation.scenarios import (
    generate_benign_baseline,
    generate_family_device_scenario,
    generate_corporate_vpn_scenario,
    generate_distributed_card_testing,
    generate_accelerating_cluster,
)


def initialize_merchants(num_merchants: int = 20) -> List[Merchant]:
    """
    Creates a diverse set of synthetic merchants with different volume and pricing baselines.
    """
    categories = [
        ("digital_goods", 8.0, 4.0),
        ("food_delivery", 15.0, 6.0),
        ("electronics", 120.0, 60.0),
        ("gaming_credits", 5.0, 2.0),
        ("fashion_retail", 45.0, 20.0),
    ]
    
    merchants = []
    for i in range(num_merchants):
        cat_name, avg_amt, std_amt = random.choice(categories)
        merchants.append(
            Merchant(
                merchant_id=f"mer_{i+1:03d}",
                category=cat_name,
                base_velocity_mean=round(random.uniform(5.0, 30.0), 1),
                avg_txn_amount=avg_amt,
                std_txn_amount=std_amt
            )
        )
    return merchants


def initialize_entities(num_accounts: int = 1000, num_devices: int = 800, start_time: datetime = datetime(2026, 1, 1)):
    """
    Initializes background customer accounts and standard user devices.
    """
    accounts = [
        Account(
            account_id=generate_id("acc_user"),
            creation_time=start_time - timedelta(days=random.randint(10, 180))
        )
        for _ in range(num_accounts)
    ]
    
    device_types = ["mobile", "desktop", "tablet"]
    devices = [
        Device(
            device_id=generate_id("dev_user"),
            device_type=random.choice(device_types)
        )
        for _ in range(num_devices)
    ]
    return accounts, devices


def build_synthetic_world(
    start_time: datetime = datetime(2026, 1, 1, 0, 0, 0),
    duration_days: int = 7
) -> pd.DataFrame:
    """
    Assembles the entire synthetic payment timeline:
    - 7 days of realistic baseline traffic
    - Multiple benign false-positive traps (Family devices, Corporate VPNs)
    - Multiple coordinated attack campaigns (Card testing, Accelerating clusters)
    """
    random.seed(42)  # Fixed seed for reproducibility

    print("Initializing merchants, accounts, and devices...")
    merchants = initialize_merchants(num_merchants=25)
    accounts, devices = initialize_entities(num_accounts=1500, num_devices=1200, start_time=start_time)

    all_transactions: List[Transaction] = []

    # 1. Generate 7 days of benign baseline background traffic
    print(f"Generating {duration_days} days of benign baseline transactions...")
    for day in range(duration_days):
        day_start = start_time + timedelta(days=day)
        baseline_txs = generate_benign_baseline(
            merchants=merchants,
            accounts=accounts,
            devices=devices,
            start_time=day_start,
            duration_hours=24
        )
        all_transactions.extend(baseline_txs)

    # 2. Inject Benign Hard Negatives across the timeline
    print("Injecting benign hard negatives (Family iPads & Corporate VPNs)...")
    for day in range(duration_days):
        day_start = start_time + timedelta(days=day, hours=10)
        
        # Daily family device activity
        fam_txs, _, _ = generate_family_device_scenario(merchants=merchants, start_time=day_start)
        all_transactions.extend(fam_txs)
        
        # Corporate VPN activity on weekdays
        if day < 5:
            vpn_txs, _, _ = generate_corporate_vpn_scenario(merchants=merchants, start_time=day_start)
            all_transactions.extend(vpn_txs)

    # 3. Inject Coordinated Malicious Campaigns (Target Scenarios)
    print("Injecting malicious coordinated abuse campaigns...")
    # Campaign 1: Distributed Card Testing on Day 2
    card_test_txs, _, _, _ = generate_distributed_card_testing(
        target_merchants=merchants[:8],
        start_time=start_time + timedelta(days=2, hours=14, minutes=30),
        num_mules=10,
        num_devices=3,
        target_tx_count=45
    )
    all_transactions.extend(card_test_txs)

    # Campaign 2: Accelerating Cluster on Day 4
    accel_txs, _, _, _ = generate_accelerating_cluster(
        target_merchants=merchants[5:15],
        start_time=start_time + timedelta(days=4, hours=9, minutes=15),
        initial_accounts=2,
        final_accounts=16
    )
    all_transactions.extend(accel_txs)

    # Campaign 3: Another Distributed Card Testing attack on Day 6 (Held-out evaluation window)
    card_test_txs_2, _, _, _ = generate_distributed_card_testing(
        target_merchants=merchants[10:20],
        start_time=start_time + timedelta(days=6, hours=18, minutes=0),
        num_mules=12,
        num_devices=4,
        target_tx_count=50
    )
    all_transactions.extend(card_test_txs_2)

    # 4. Convert to DataFrame and STRICTLY SORT CHRONOLOGICALLY
    print("Formatting and sorting dataset by timestamp...")
    records = [tx.model_dump() for tx in all_transactions]
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    return df


def generate_and_save_dataset():
    """Generates the full dataset and splits temporally into train, validation, and test."""
    start_date = datetime(2026, 1, 1)
    df = build_synthetic_world(start_time=start_date, duration_days=7)

    output_dir = os.path.join("data", "generated")
    os.makedirs(output_dir, exist_ok=True)

    # Full dataset
    full_path = os.path.join(output_dir, "transactions_full.csv")
    df.to_csv(full_path, index=False)
    print(f"\n[SUCCESS] Full dataset saved: {full_path} ({len(df)} transactions)")

    # Temporal Partitioning (Anti-leakage):
    # Train: Days 1-4
    # Validation: Day 5
    # Test: Days 6-7
    train_end = start_date + timedelta(days=4)
    val_end = start_date + timedelta(days=5)

    train_df = df[df["timestamp"] < train_end]
    val_df = df[(df["timestamp"] >= train_end) & (df["timestamp"] < val_end)]
    test_df = df[df["timestamp"] >= val_end]

    train_df.to_csv(os.path.join(output_dir, "train.csv"), index=False)
    val_df.to_csv(os.path.join(output_dir, "val.csv"), index=False)
    test_df.to_csv(os.path.join(output_dir, "test.csv"), index=False)

    print(f"  - Train Set: {len(train_df)} rows ({train_df['is_fraud'].sum()} fraud)")
    print(f"  - Val Set:   {len(val_df)} rows ({val_df['is_fraud'].sum()} fraud)")
    print(f"  - Test Set:  {len(test_df)} rows ({test_df['is_fraud'].sum()} fraud)")
    print("\nGround truth breakdown across scenarios:")
    print(df["scenario_name"].value_counts())


if __name__ == "__main__":
    generate_and_save_dataset()