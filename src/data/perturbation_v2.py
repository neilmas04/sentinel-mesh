import pandas as pd
import numpy as np
import hashlib
from typing import Dict, Any, Tuple

def _hash_id(prefix: str, original_id: str, seed: int) -> str:
    digest = hashlib.sha256(f"{prefix}|{original_id}|{seed}".encode()).hexdigest()
    return f"{prefix}_{digest[:16]}"

def apply_perturbation(
    test_df: pd.DataFrame, 
    labels_df: pd.DataFrame, 
    campaigns_df: pd.DataFrame,
    scenario: str,
    strength: Any,
    seed: int
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Applies a specific perturbation to the test dataset.
    Returns: (perturbed_df, perturbed_campaigns_df, mapping_df, label_status_dict)
    """
    np.random.seed(seed)
    
    # Merge labels to identify abuse transactions
    full_df = test_df.merge(labels_df[['transaction_id', 'is_abuse', 'campaign_id']], on='transaction_id', how='left')
    
    df_pert = full_df.copy()
    camp_pert = campaigns_df.copy()
    
    # Ensure datetime types for timestamps
    camp_pert['start_timestamp'] = pd.to_datetime(camp_pert['start_timestamp'])
    camp_pert['end_timestamp'] = pd.to_datetime(camp_pert['end_timestamp'])
    
    abuse_mask = df_pert['is_abuse'] == 1
    
    label_status = {
        "scenario": scenario,
        "strength": strength,
        "label_status": "PRESERVED",
        "rationale": "Default assumption, overridden by specific scenarios if needed."
    }
    
    mapping_records = []
    
    if scenario == "clean":
        pass # No changes
        
    elif scenario == "timing_jitter":
        max_jitter = strength
        jitter_mins = np.random.uniform(-max_jitter, max_jitter, size=abuse_mask.sum())
        jitter_td = pd.to_timedelta(jitter_mins, unit='m')
        
        new_ts = df_pert.loc[abuse_mask, 'timestamp'] + jitter_td
        df_pert.loc[abuse_mask, 'timestamp'] = pd.to_datetime(new_ts).astype(df_pert['timestamp'].dtype)
        
        label_status["rationale"] = f"Timing jitter of +/- {max_jitter}m preserves campaign intent."
        
    elif scenario == "low_and_slow":
        expansion_factor = strength
        
        def expand_campaign(group):
            if group['is_abuse'].iloc[0] == 0:
                return group
            group = group.sort_values('timestamp')
            start_time = group['timestamp'].iloc[0]
            deltas = group['timestamp'] - start_time
            group['timestamp'] = start_time + (deltas * expansion_factor)
            return group
            
        abuse_only = df_pert[abuse_mask].groupby('campaign_id', group_keys=False).apply(expand_campaign)
        df_pert.loc[abuse_mask, 'timestamp'] = pd.to_datetime(abuse_only['timestamp']).astype(df_pert['timestamp'].dtype)
        
        label_status["rationale"] = f"Time expansion by {expansion_factor}x preserves campaign intent but evades velocity rules."
        
    elif scenario == "merchant_hopping":
        switch_prob = strength
        all_merchants = df_pert['merchant_id'].unique()
        
        def hop_merchants(group):
            if group['is_abuse'].iloc[0] == 0:
                return group
            
            # For each transaction, decide whether to switch
            switch_mask = np.random.random(len(group)) < switch_prob
            
            # Pick random replacement merchants from the global pool
            # In a real scenario, we might want to ensure we don't pick merchants involved in other active campaigns
            # For this smoke test, we just pick randomly from all merchants.
            replacements = np.random.choice(all_merchants, size=switch_mask.sum())
            
            group.loc[switch_mask, 'merchant_id'] = replacements
            return group
            
        abuse_only = df_pert[abuse_mask].groupby('campaign_id', group_keys=False).apply(hop_merchants)
        df_pert.loc[abuse_mask, 'merchant_id'] = abuse_only['merchant_id']
        
        label_status["rationale"] = f"Merchant hopping with prob {switch_prob} preserves campaign intent. Replacements selected from global pool."
        
    elif scenario == "device_rotation":
        rotation_rate = strength
        
        def rotate_devices(group):
            if group['is_abuse'].iloc[0] == 0:
                return group
                
            switch_mask = np.random.random(len(group)) < rotation_rate
            
            # Generate synthetic identities
            # We use the transaction ID to ensure unique synthetic devices if needed, or just random hashes
            replacements = [_hash_id("synth_device", str(i), seed) for i in range(switch_mask.sum())]
            
            group.loc[switch_mask, 'device_id'] = replacements
            return group
            
        abuse_only = df_pert[abuse_mask].groupby('campaign_id', group_keys=False).apply(rotate_devices)
        df_pert.loc[abuse_mask, 'device_id'] = abuse_only['device_id']
        
        label_status["rationale"] = f"Device rotation with prob {rotation_rate} uses isolated synthetic identities."
        
    elif scenario == "account_rotation":
        rotation_rate = strength
        
        def rotate_accounts(group):
            if group['is_abuse'].iloc[0] == 0:
                return group
                
            switch_mask = np.random.random(len(group)) < rotation_rate
            
            replacements = [_hash_id("synth_account", str(i), seed) for i in range(switch_mask.sum())]
            
            group.loc[switch_mask, 'account_id'] = replacements
            return group
            
        abuse_only = df_pert[abuse_mask].groupby('campaign_id', group_keys=False).apply(rotate_accounts)
        df_pert.loc[abuse_mask, 'account_id'] = abuse_only['account_id']
        
        label_status["rationale"] = f"Account rotation with prob {rotation_rate} uses isolated synthetic identities."
        
    elif scenario == "fragmented_bursts":
        num_fragments, gap_hours = strength
        
        def fragment_campaign(group):
            if group['is_abuse'].iloc[0] == 0:
                return group
                
            group = group.sort_values('timestamp')
            n_tx = len(group)
            
            if n_tx < num_fragments:
                # Can't fragment more than we have transactions
                return group
                
            # Split into fragments
            fragment_indices = np.array_split(np.arange(n_tx), num_fragments)
            
            gap_td = pd.Timedelta(hours=gap_hours)
            
            for i, indices in enumerate(fragment_indices):
                if i > 0:
                    # Add gap to all subsequent fragments
                    group.iloc[indices[0]:, group.columns.get_loc('timestamp')] += gap_td
                    
            return group
            
        abuse_only = df_pert[abuse_mask].groupby('campaign_id', group_keys=False).apply(fragment_campaign)
        df_pert.loc[abuse_mask, 'timestamp'] = pd.to_datetime(abuse_only['timestamp']).astype(df_pert['timestamp'].dtype)
        
        label_status["rationale"] = f"Fragmented into {num_fragments} bursts with {gap_hours}h gaps. Preserves intent."
        
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
        
    # Re-sort by timestamp
    df_pert = df_pert.sort_values('timestamp').reset_index(drop=True)
    
    # Update transaction IDs and create mapping
    # We only update IDs for transactions that were actually modified, or all abuse transactions?
    # The plan says: "transformed_transaction_id (which will be the original ID + a suffix, e.g., _jitter)"
    # Let's update all abuse transactions for simplicity and traceability.
    if scenario != "clean":
        suffix = f"_{scenario}"
        
        # Create mapping
        abuse_indices = df_pert[df_pert['is_abuse'] == 1].index
        
        for idx in abuse_indices:
            orig_id = df_pert.loc[idx, 'transaction_id']
            new_id = f"{orig_id}{suffix}"
            
            mapping_records.append({
                "original_transaction_id": orig_id,
                "transformed_transaction_id": new_id,
                "original_campaign_id": df_pert.loc[idx, 'campaign_id'],
                "perturbation_type": scenario,
                "perturbation_strength": str(strength),
                "seed": seed
            })
            
            df_pert.loc[idx, 'transaction_id'] = new_id
            
    mapping_df = pd.DataFrame(mapping_records)
    
    # Recompute campaign start/end times and affected entities
    if scenario != "clean":
        for idx, camp in camp_pert.iterrows():
            camp_id = camp['campaign_id']
            camp_txs = df_pert[df_pert['campaign_id'] == camp_id]
            
            if not camp_txs.empty:
                camp_pert.loc[idx, 'start_timestamp'] = camp_txs['timestamp'].min()
                camp_pert.loc[idx, 'end_timestamp'] = camp_txs['timestamp'].max()
                
                # Update affected entities if they changed
                if scenario == "merchant_hopping":
                    import json
                    merchants = sorted(camp_txs['merchant_id'].unique().tolist())
                    camp_pert.loc[idx, 'affected_merchants'] = json.dumps(merchants)
                elif scenario == "device_rotation":
                    import json
                    devices = sorted(camp_txs['device_id'].unique().tolist())
                    camp_pert.loc[idx, 'affected_devices'] = json.dumps(devices)
                elif scenario == "account_rotation":
                    import json
                    accounts = sorted(camp_txs['account_id'].unique().tolist())
                    camp_pert.loc[idx, 'affected_accounts'] = json.dumps(accounts)
                    
    # Do not drop the joined columns so they can be used for evaluation
    return df_pert, camp_pert, mapping_df, label_status
