# src/simulation/scenarios.py
import random
from datetime import datetime, timedelta
from typing import List, Tuple
import numpy as np

from src.simulation.schemas import Merchant, Account, Device, Transaction
from src.simulation.behavior import generate_id, get_lognormal_amount, get_stochastic_timedelta


# ==========================================
# 1. BENIGN SCENARIOS & HARD NEGATIVES (Label = 0)
# ==========================================

def generate_benign_baseline(
    merchants: List[Merchant],
    accounts: List[Account],
    devices: List[Device],
    start_time: datetime,
    duration_hours: int = 24,
) -> List[Transaction]:
    """
    Generates standard background transactions across merchants.
    Each transaction picks a random account, device, and merchant with realistic spending amounts.
    """
    transactions = []
    current_time = start_time
    end_time = start_time + timedelta(hours=duration_hours)

    while current_time < end_time:
        # Step forward in time stochastically (e.g., average 30 seconds between network-wide events)
        current_time += get_stochastic_timedelta(mean_minutes=0.5, std_minutes=0.2)
        if current_time >= end_time:
            break

        merchant = random.choice(merchants)
        account = random.choice(accounts)
        device = random.choice(devices)
        network_id = generate_id("net_home")

        amount = get_lognormal_amount(
            mean=merchant.avg_txn_amount,
            std=merchant.std_txn_amount
        )

        tx = Transaction(
            transaction_id=generate_id("txn"),
            timestamp=current_time,
            merchant_id=merchant.merchant_id,
            account_id=account.account_id,
            device_id=device.device_id,
            network_id=network_id,
            amount=amount,
            scenario_name="benign_baseline",
            is_fraud=0,
            campaign_id=None
        )
        transactions.append(tx)

    return transactions


def generate_family_device_scenario(
    merchants: List[Merchant],
    start_time: datetime,
    num_family_members: int = 4
) -> Tuple[List[Transaction], List[Account], Device]:
    """
    HARD NEGATIVE: Multiple family members sharing one household tablet (1 device, multiple accounts).
    This must NOT be flagged as coordinated fraud.
    """
    shared_device = Device(device_id=generate_id("dev_family_ipad"), device_type="tablet")
    home_network = generate_id("net_home_fiber")
    
    family_accounts = [
        Account(account_id=generate_id("acc_fam"), creation_time=start_time - timedelta(days=random.randint(30, 300)))
        for _ in range(num_family_members)
    ]

    transactions = []
    current_time = start_time

    # Generate benign staggered purchases over an 8-hour period
    for _ in range(12):
        current_time += get_stochastic_timedelta(mean_minutes=35.0, std_minutes=15.0)
        account = random.choice(family_accounts)
        merchant = random.choice(merchants)
        amount = get_lognormal_amount(mean=merchant.avg_txn_amount, std=merchant.std_txn_amount)

        tx = Transaction(
            transaction_id=generate_id("txn"),
            timestamp=current_time,
            merchant_id=merchant.merchant_id,
            account_id=account.account_id,
            device_id=shared_device.device_id,
            network_id=home_network,
            amount=amount,
            scenario_name="benign_family_device",
            is_fraud=0,
            campaign_id=None
        )
        transactions.append(tx)

    return transactions, family_accounts, shared_device


def generate_corporate_vpn_scenario(
    merchants: List[Merchant],
    start_time: datetime,
    num_employees: int = 25
) -> Tuple[List[Transaction], List[Account], str]:
    """
    HARD NEGATIVE: Many distinct users sharing a single office/VPN IP address.
    """
    shared_vpn_net = generate_id("net_corp_vpn")
    employee_accounts = [
        Account(account_id=generate_id("acc_corp"), creation_time=start_time - timedelta(days=random.randint(60, 400)))
        for _ in range(num_employees)
    ]

    transactions = []
    current_time = start_time

    for _ in range(40):
        current_time += get_stochastic_timedelta(mean_minutes=10.0, std_minutes=4.0)
        account = random.choice(employee_accounts)
        merchant = random.choice(merchants)
        device = Device(device_id=generate_id("dev_corp_laptop"), device_type="laptop")
        amount = get_lognormal_amount(mean=merchant.avg_txn_amount, std=merchant.std_txn_amount)

        tx = Transaction(
            transaction_id=generate_id("txn"),
            timestamp=current_time,
            merchant_id=merchant.merchant_id,
            account_id=account.account_id,
            device_id=device.device_id,
            network_id=shared_vpn_net,
            amount=amount,
            scenario_name="benign_corporate_vpn",
            is_fraud=0,
            campaign_id=None
        )
        transactions.append(tx)

    return transactions, employee_accounts, shared_vpn_net


# ==========================================
# 2. MALICIOUS ATTACK SCENARIOS (Label = 1)
# ==========================================

def generate_distributed_card_testing(
    target_merchants: List[Merchant],
    start_time: datetime,
    num_mules: int = 8,
    num_devices: int = 3,
    target_tx_count: int = 30
) -> Tuple[List[Transaction], List[Account], List[Device], str]:
    """
    PRIMARY TARGET: Coordinated ring testing stolen cards across multiple merchants.
    Each merchant individually sees normal volume, but the cross-merchant graph
    shows dense device & network reuse with synchronized micro-transactions.
    """
    campaign_id = generate_id("cmp_dist_testing")
    mule_accounts = [
        Account(account_id=generate_id("acc_mule"), creation_time=start_time - timedelta(hours=random.randint(1, 24)), is_compromised=True)
        for _ in range(num_mules)
    ]
    bot_devices = [
        Device(device_id=generate_id("dev_bot_vm"), device_type="desktop_vm", is_compromised=True)
        for _ in range(num_devices)
    ]
    shared_proxy_network = generate_id("net_datacenter_proxy")

    transactions = []
    current_time = start_time

    for _ in range(target_tx_count):
        # Rapid micro-transactions spread across merchants
        current_time += get_stochastic_timedelta(mean_minutes=3.5, std_minutes=1.2)
        
        account = random.choice(mule_accounts)
        device = random.choice(bot_devices)
        merchant = random.choice(target_merchants)
        
        # Card testing typically uses small probing amounts (e.g., $1.00 to $5.50)
        amount = round(float(np.random.uniform(1.0, 5.5)), 2)

        tx = Transaction(
            transaction_id=generate_id("txn"),
            timestamp=current_time,
            merchant_id=merchant.merchant_id,
            account_id=account.account_id,
            device_id=device.device_id,
            network_id=shared_proxy_network,
            amount=amount,
            scenario_name="distributed_card_testing",
            is_fraud=1,
            campaign_id=campaign_id
        )
        transactions.append(tx)

    return transactions, mule_accounts, bot_devices, campaign_id


def generate_accelerating_cluster(
    target_merchants: List[Merchant],
    start_time: datetime,
    initial_accounts: int = 2,
    final_accounts: int = 16
) -> Tuple[List[Transaction], List[Account], List[Device], str]:
    """
    TEMPORAL ACCELERATION ATTACK:
    Starts quietly with 2 accounts, but exponentially scales account/device linking
    over a 6-hour window.
    """
    campaign_id = generate_id("cmp_accelerating")
    all_accounts = [
        Account(account_id=generate_id("acc_ring"), creation_time=start_time, is_compromised=True)
        for _ in range(final_accounts)
    ]
    bot_device = Device(device_id=generate_id("dev_emulated_phone"), device_type="mobile", is_compromised=True)
    shared_net = generate_id("net_proxy_mesh")

    transactions = []
    current_time = start_time
    
    # Staged rollout: accounts get unlocked in waves
    active_pool_size = initial_accounts
    while active_pool_size <= final_accounts:
        current_active = all_accounts[:active_pool_size]
        
        for _ in range(active_pool_size * 2):
            # Timing gets tighter as attack accelerates
            mean_delay = max(0.5, 8.0 / active_pool_size)
            current_time += get_stochastic_timedelta(mean_minutes=mean_delay, std_minutes=mean_delay * 0.3)
            
            account = random.choice(current_active)
            merchant = random.choice(target_merchants)
            amount = round(float(np.random.uniform(10.0, 45.0)), 2)

            tx = Transaction(
                transaction_id=generate_id("txn"),
                timestamp=current_time,
                merchant_id=merchant.merchant_id,
                account_id=account.account_id,
                device_id=bot_device.device_id,
                network_id=shared_net,
                amount=amount,
                scenario_name="accelerating_cluster",
                is_fraud=1,
                campaign_id=campaign_id
            )
            transactions.append(tx)

        active_pool_size *= 2  # Exponential growth

    return transactions, all_accounts, [bot_device], campaign_id