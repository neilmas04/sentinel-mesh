import pandas as pd
import numpy as np

def apply_timing_jitter(df: pd.DataFrame, campaigns_df: pd.DataFrame, max_minutes: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applies random timing jitter to abusive transactions and recomputes start times."""
    df = df.copy()
    camp_df = campaigns_df.copy()
    
    # We need to map which transaction belongs to which campaign. 
    # But wait, df doesn't have campaign_id directly. We need to pass the joined labels.
    pass # Implementation requires df with labels

def generate_robustness_variants(test_df: pd.DataFrame, labels_df: pd.DataFrame, campaigns_df: pd.DataFrame) -> dict:
    """Generates perturbed variants of the test set."""
    
    # Join labels to apply targeted perturbation
    full_df = test_df.merge(labels_df[['transaction_id', 'is_abuse', 'campaign_id']], on='transaction_id', how='left')
    
    variants = {}
    
    # --- 1. JITTER ---
    df_jitter = full_df.copy()
    abuse_mask = df_jitter['is_abuse'] == 1
    
    # Add random jitter between -30 and +30 mins
    jitter_mins = np.random.uniform(-30, 30, size=abuse_mask.sum())
    jitter_td = pd.to_timedelta(jitter_mins, unit='m')
    
    new_ts = df_jitter.loc[abuse_mask, 'timestamp'] + jitter_td
    df_jitter.loc[abuse_mask, 'timestamp'] = pd.to_datetime(new_ts).astype(df_jitter['timestamp'].dtype)
    
    # Sort and re-index
    df_jitter = df_jitter.sort_values('timestamp').reset_index(drop=True)
    
    # Recompute campaign start times
    camp_jitter = campaigns_df.copy()
    first_txs = df_jitter[abuse_mask].groupby('campaign_id')['timestamp'].min().reset_index()
    first_txs.rename(columns={'timestamp': 'start_timestamp'}, inplace=True)
    
    # Update start times
    camp_jitter = camp_jitter.drop(columns=['start_timestamp']).merge(first_txs, on='campaign_id', how='left')
    
    variants['jitter'] = (df_jitter.drop(columns=['is_abuse', 'campaign_id']), camp_jitter)
    
    # --- 2. LOW AND SLOW ---
    df_slow = full_df.copy()
    # For each campaign, expand time deltas by 5x
    
    def expand_campaign(group):
        if group['is_abuse'].iloc[0] == 0:
            return group
        group = group.sort_values('timestamp')
        start_time = group['timestamp'].iloc[0]
        deltas = group['timestamp'] - start_time
        group['timestamp'] = start_time + (deltas * 5)
        return group
    
    # We only apply this to abuse transactions
    abuse_only = df_slow[abuse_mask].groupby('campaign_id', group_keys=False).apply(expand_campaign)
    df_slow.loc[abuse_mask, 'timestamp'] = pd.to_datetime(abuse_only['timestamp']).astype(df_slow['timestamp'].dtype)
    
    df_slow = df_slow.sort_values('timestamp').reset_index(drop=True)
    
    camp_slow = campaigns_df.copy()
    first_txs_slow = df_slow[abuse_mask].groupby('campaign_id')['timestamp'].min().reset_index()
    first_txs_slow.rename(columns={'timestamp': 'start_timestamp'}, inplace=True)
    camp_slow = camp_slow.drop(columns=['start_timestamp']).merge(first_txs_slow, on='campaign_id', how='left')
    
    variants['low_and_slow'] = (df_slow.drop(columns=['is_abuse', 'campaign_id']), camp_slow)
    
    # --- 3. VARIED AMOUNTS ---
    df_amount = full_df.copy()
    # Multiply amounts by random factors [0.5, 2.0]
    amount_factors = np.random.uniform(0.5, 2.0, size=abuse_mask.sum())
    df_amount.loc[abuse_mask, 'amount'] = df_amount.loc[abuse_mask, 'amount'] * amount_factors
    
    variants['amount'] = (df_amount.drop(columns=['is_abuse', 'campaign_id']), campaigns_df.copy())
    
    return variants
