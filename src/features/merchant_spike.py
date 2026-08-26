import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class MerchantSpikeDetector:
    def __init__(self, bucket_size: str = '1h', lookback_window: int = 6):
        self.bucket_size = bucket_size
        self.lookback_window = lookback_window

    def compute_spike(self, merchant_id: str, current_time: pd.Timestamp, 
                      transactions_df: pd.DataFrame, flagged_tx_ids: set,
                      live_observation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        
        # Filter for merchant
        df_m = transactions_df[transactions_df['merchant_id'] == merchant_id].copy()
        if df_m.empty:
            return self._empty_result(merchant_id, current_time)
            
        df_m['timestamp'] = pd.to_datetime(df_m['timestamp'])
        
        # Mark flagged
        df_m['is_flagged'] = df_m['transaction_id'].isin(flagged_tx_ids).astype(int)
        
        # Define buckets based on current_time
        # We need to create buckets of size `bucket_size` ending at `current_time`
        freq = pd.Timedelta(self.bucket_size)
        
        # Filter out future transactions
        df_m = df_m[df_m['timestamp'] <= current_time]
        
        # Filter out the live transaction from the historical dataframe to prevent double counting
        if live_observation:
            df_m = df_m[df_m['transaction_id'] != live_observation['live_tx_id']]
        
        if df_m.empty and not live_observation:
            return self._empty_result(merchant_id, current_time)
            
        # Assign each transaction to a bucket relative to current_time
        # bucket index 0 is the current bucket (current_time - freq, current_time]
        # bucket index 1 is (current_time - 2*freq, current_time - freq], etc.
        
        # Calculate time difference from current_time
        time_diff = current_time - df_m['timestamp']
        
        # Bucket index: 0 for (0, freq], 1 for (freq, 2*freq], etc.
        # We use math.ceil(time_diff / freq) - 1. 
        # If time_diff == 0 (exact current_time), it should be in bucket 0.
        # Let's use floor division on (time_diff - epsilon) to handle exact boundaries.
        epsilon = pd.Timedelta(microseconds=1)
        bucket_indices = ((time_diff - epsilon) // freq)
        
        df_m['bucket_idx'] = bucket_indices
        
        # We only care about bucket 0 (current) and buckets 1 to lookback_window (baseline)
        df_current = df_m[df_m['bucket_idx'] == 0]
        df_baseline = df_m[(df_m['bucket_idx'] >= 1) & (df_m['bucket_idx'] <= self.lookback_window)]
        
        current_total = len(df_current)
        current_flagged = df_current['is_flagged'].sum()
        
        # Explicitly inject the live observation into bucket 0
        if live_observation:
            current_total += 1
            if live_observation.get('is_flagged', False):
                current_flagged += 1
                
        current_rate = current_flagged / current_total if current_total > 0 else 0.0
        
        # Calculate baseline stats
        baseline_buckets = df_baseline.groupby('bucket_idx').agg(
            total=('transaction_id', 'count'),
            flagged=('is_flagged', 'sum')
        )
        
        # We must ensure all baseline buckets are accounted for, even empty ones
        # up to the maximum bucket index found, or up to lookback_window?
        # The prompt says: "If fewer than the required lookback buckets exist, return an explicit baseline_insufficient flag"
        # Wait, if a merchant has no transactions in a bucket, the rate is 0.
        # But if the merchant didn't exist (first transaction was 3 hours ago), do we have 6 buckets?
        # Let's check the oldest transaction for this merchant.
        oldest_tx_time = df_m['timestamp'].min()
        merchant_age = current_time - oldest_tx_time
        available_buckets = (merchant_age // freq) + 1
        
        if available_buckets <= self.lookback_window:
            # Baseline insufficient
            return self._insufficient_baseline_result(
                merchant_id, current_time, current_total, current_flagged, current_rate
            )
            
        # Fill missing buckets with 0
        all_baseline_indices = range(1, self.lookback_window + 1)
        baseline_buckets = baseline_buckets.reindex(all_baseline_indices, fill_value=0)
        
        # Calculate rates for baseline buckets
        # If total == 0, rate is 0
        baseline_buckets['rate'] = np.where(
            baseline_buckets['total'] > 0, 
            baseline_buckets['flagged'] / baseline_buckets['total'], 
            0.0
        )
        
        baseline_mean = float(baseline_buckets['rate'].mean())
        baseline_std = float(baseline_buckets['rate'].std(ddof=0)) # Population std for the window
        
        # Zero baseline handling
        if baseline_mean == 0:
            if current_rate == 0:
                rate_multiplier = 1.0
                spike_score = 0.0
                severity = "NORMAL"
            else:
                rate_multiplier = None
                spike_score = None
                severity = "CRITICAL" # Zero-baseline emergence
        else:
            rate_multiplier = current_rate / baseline_mean
            if baseline_std == 0:
                # If std is 0 but mean > 0, any deviation is technically infinite score.
                # Let's handle it gracefully.
                if current_rate == baseline_mean:
                    spike_score = 0.0
                else:
                    # If current_rate > baseline_mean and std is 0, it's a huge spike.
                    spike_score = float('inf') if current_rate > baseline_mean else float('-inf')
            else:
                spike_score = (current_rate - baseline_mean) / baseline_std
                
            severity = self._classify_severity(spike_score, rate_multiplier)
            
        return {
            "merchant_id": merchant_id,
            "timestamp": current_time.isoformat(),
            "total_transactions": int(current_total),
            "flagged_transactions": int(current_flagged),
            "flagged_rate": float(current_rate),
            "baseline_mean": float(baseline_mean),
            "baseline_std": float(baseline_std),
            "rate_multiplier": float(rate_multiplier) if rate_multiplier is not None else None,
            "spike_score": float(spike_score) if spike_score is not None else None,
            "severity": severity,
            "baseline_insufficient": False
        }
        
    def _classify_severity(self, spike_score: float, rate_multiplier: float) -> str:
        if spike_score is None or rate_multiplier is None:
            return "NORMAL" # Should not happen unless zero-baseline emergence, which is handled earlier
            
        if spike_score >= 4 or rate_multiplier >= 5:
            return "CRITICAL"
        elif spike_score >= 3 or rate_multiplier >= 3:
            return "HIGH"
        elif spike_score >= 2 or rate_multiplier >= 1.5:
            return "ELEVATED"
        return "NORMAL"
        
    def _empty_result(self, merchant_id: str, current_time: pd.Timestamp) -> Dict[str, Any]:
        return {
            "merchant_id": merchant_id,
            "timestamp": current_time.isoformat(),
            "total_transactions": 0,
            "flagged_transactions": 0,
            "flagged_rate": 0.0,
            "baseline_mean": 0.0,
            "baseline_std": 0.0,
            "rate_multiplier": 1.0,
            "spike_score": 0.0,
            "severity": "NORMAL",
            "baseline_insufficient": True
        }
        
    def _insufficient_baseline_result(self, merchant_id: str, current_time: pd.Timestamp, 
                                      total: int, flagged: int, rate: float) -> Dict[str, Any]:
        return {
            "merchant_id": merchant_id,
            "timestamp": current_time.isoformat(),
            "total_transactions": int(total),
            "flagged_transactions": int(flagged),
            "flagged_rate": float(rate),
            "baseline_mean": None,
            "baseline_std": None,
            "rate_multiplier": None,
            "spike_score": None,
            "severity": "NORMAL",
            "baseline_insufficient": True
        }
