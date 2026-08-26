import pandas as pd
from datetime import datetime

class AgentTools:
    def __init__(self, transactions_df: pd.DataFrame):
        self.df = transactions_df
        self.evidence_counter = 0

    def _generate_evidence_id(self) -> str:
        self.evidence_counter += 1
        return f"E{self.evidence_counter}"

    def _get_history(self, as_of_timestamp: str) -> pd.DataFrame:
        """Strictly returns only events BEFORE the as_of_timestamp."""
        cutoff = pd.to_datetime(as_of_timestamp)
        return self.df[self.df['timestamp'] < cutoff].copy()

    def get_transaction_context(self, transaction_id: str, as_of_timestamp: str) -> dict:
        """Returns the raw details of the transaction being investigated."""
        cutoff = pd.to_datetime(as_of_timestamp)
        tx_row = self.df[(self.df['transaction_id'] == transaction_id) & (self.df['timestamp'] <= cutoff)]
        
        if tx_row.empty:
            return {"error": f"Transaction {transaction_id} not found or is beyond as_of_timestamp."}
            
        row = tx_row.iloc[0]
        evidence_id = self._generate_evidence_id()
        return {
            "evidence_id": evidence_id,
            "source_tool": "get_transaction_context",
            "observation": {
                "transaction_id": transaction_id,
                "amount": float(row['amount']),
                "merchant_id": str(row['merchant_id']),
                "account_id": str(row['account_id']),
                "device_id": str(row['device_id']),
                "network_group_id": str(row['network_group_id']),
                "timestamp": str(row['timestamp'])
            }
        }

    def get_account_history(self, account_id: str, as_of_timestamp: str) -> dict:
        """Returns historical transactions for an account strictly before as_of_timestamp."""
        history = self._get_history(as_of_timestamp)
        acc_txs = history[history['account_id'] == account_id]
        
        evidence_id = self._generate_evidence_id()
        return {
            "evidence_id": evidence_id,
            "source_tool": "get_account_history",
            "observation": {
                "account_id": account_id,
                "historical_transaction_count": len(acc_txs),
                "historical_total_amount": float(acc_txs['amount'].sum() if not acc_txs.empty else 0),
                "historical_merchant_count": int(acc_txs['merchant_id'].nunique()),
                "merchants_used": list(acc_txs['merchant_id'].unique())
            }
        }

    def get_device_relationships(self, device_id: str, as_of_timestamp: str) -> dict:
        """Returns accounts and merchants historically linked to a device before as_of_timestamp."""
        history = self._get_history(as_of_timestamp)
        dev_txs = history[history['device_id'] == device_id]
        
        evidence_id = self._generate_evidence_id()
        return {
            "evidence_id": evidence_id,
            "source_tool": "get_device_relationships",
            "observation": {
                "device_id": device_id,
                "historical_account_count": int(dev_txs['account_id'].nunique()),
                "historical_merchant_count": int(dev_txs['merchant_id'].nunique()),
                "historical_transaction_count": len(dev_txs)
            }
        }

    def get_network_relationships(self, network_group_id: str, as_of_timestamp: str) -> dict:
        """Returns devices, accounts, and merchants linked to a network cluster before as_of_timestamp."""
        history = self._get_history(as_of_timestamp)
        net_txs = history[history['network_group_id'] == network_group_id]
        
        evidence_id = self._generate_evidence_id()
        return {
            "evidence_id": evidence_id,
            "source_tool": "get_network_relationships",
            "observation": {
                "network_group_id": network_group_id,
                "historical_device_count": int(net_txs['device_id'].nunique()),
                "historical_account_count": int(net_txs['account_id'].nunique()),
                "historical_merchant_count": int(net_txs['merchant_id'].nunique()),
                "historical_transaction_count": len(net_txs)
            }
        }