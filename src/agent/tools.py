# src/agent/tools.py
import pandas as pd
from typing import Dict

class InvestigationTools:
    """
    Bounded, read-only tools for the AI Agent.
    The AI cannot query the raw database directly; it must use these strict endpoints.
    """
    def __init__(self, dataset_path: str = "data/generated/transactions_full.csv"):
        self.df = pd.read_csv(dataset_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def get_device_cluster_summary(self, device_id: str) -> Dict:
        """Returns the number of unique accounts and merchants linked to a device."""
        cluster = self.df[self.df['device_id'] == device_id]
        if cluster.empty:
            return {"error": "Device not found."}
        
        return {
            "device_id": device_id,
            "total_transactions": len(cluster),
            "unique_accounts": cluster['account_id'].nunique(),
            "unique_merchants": cluster['merchant_id'].nunique(),
            "time_span_hours": round((cluster['timestamp'].max() - cluster['timestamp'].min()).total_seconds() / 3600, 2)
        }
        
    def get_merchant_exposure(self, device_id: str) -> Dict:
        """Returns the financial volume spread across merchants for a given device."""
        cluster = self.df[self.df['device_id'] == device_id]
        exposure = cluster.groupby('merchant_id')['amount'].sum().to_dict()
        return {"merchant_volumes": exposure}