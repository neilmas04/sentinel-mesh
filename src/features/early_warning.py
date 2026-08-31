import os
import json
import pandas as pd

class EarlyWarningDetector:
    """
    A deterministic early-warning detector designed to flag transactions
    that exhibit strong causal network/growth anomalies, even if short-term
    synchronization features are weak (e.g., during low-and-slow attacks).
    
    This detector operates in parallel with Candidate D and is designed
    to trigger an investigation candidate (Risk Case) without auto-blocking.
    """
    def __init__(self, config_path: str = "artifacts/models/early_warning/config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.version = self.config.get("detector_version", "unknown")
        self.rule_type = self.config.get("rule_type", "OR")
        self.signals = self.config.get("signals", [])
        
    def _load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Early Warning config not found at {self.config_path}")
        with open(self.config_path, "r") as f:
            return json.load(f)
            
    def evaluate(self, tx_features: pd.Series) -> dict:
        """
        Evaluates a single transaction's features against the early-warning rules.
        
        Returns:
            dict: {
                "triggered": bool,
                "signals": list of dicts detailing which signals triggered,
                "detector_version": str
            }
        """
        triggered_signals = []
        
        for signal in self.signals:
            feature = signal["feature"]
            operator = signal["operator"]
            threshold = signal["threshold"]
            
            if feature not in tx_features:
                continue
                
            val = tx_features[feature]
            
            is_triggered = False
            if operator == ">":
                is_triggered = val > threshold
            elif operator == ">=":
                is_triggered = val >= threshold
            elif operator == "<":
                is_triggered = val < threshold
            elif operator == "<=":
                is_triggered = val <= threshold
                
            if is_triggered:
                triggered_signals.append({
                    "feature": feature,
                    "value": float(val),
                    "threshold": threshold,
                    "operator": operator
                })
                
        is_triggered = False
        if self.rule_type == "OR":
            is_triggered = len(triggered_signals) > 0
        elif self.rule_type == "AND":
            is_triggered = len(triggered_signals) == len(self.signals)
            
        return {
            "triggered": is_triggered,
            "signals": triggered_signals,
            "detector_version": self.version
        }
        
    def evaluate_batch(self, df: pd.DataFrame) -> pd.Series:
        """
        Evaluates a batch of transactions. Returns a boolean Series.
        """
        results = []
        for _, row in df.iterrows():
            res = self.evaluate(row)
            results.append(res["triggered"])
        return pd.Series(results, index=df.index)
