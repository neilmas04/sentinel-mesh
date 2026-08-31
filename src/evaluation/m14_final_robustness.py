import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from src.data.perturbation_v2 import apply_perturbation
from src.features.local_features import LocalFeatureExtractor
from src.features.network_features import NetworkFeatureExtractor
from src.features.temporal_features import TemporalFeatureExtractor
from src.features.merchant_spike import MerchantSpikeDetector
from src.features.early_warning import EarlyWarningDetector
from src.models.m04_temporal import calculate_metrics, evaluate_ttd

def extract_all_features(df: pd.DataFrame) -> pd.DataFrame:
    df = LocalFeatureExtractor().extract_features(df)
    df = NetworkFeatureExtractor().extract_features(df)
    df = TemporalFeatureExtractor().extract_features(df)
    return df

def run_final_robustness():
    print("Loading datasets...")
    labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
    campaigns_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/campaigns.csv")
    campaigns_df['start_timestamp'] = pd.to_datetime(campaigns_df['start_timestamp'])
    
    tx_path = "data/generated/m01-world-v1/cohorts/test/transactions.csv"
    raw_test_df = pd.read_csv(tx_path)
    raw_test_df['timestamp'] = pd.to_datetime(raw_test_df['timestamp'])
    test_campaigns = campaigns_df[campaigns_df['cohort'] == 'test'].copy()
    
    print("Loading Candidate D model...")
    model_dir = "artifacts/models/candidate_d"
    model = joblib.load(os.path.join(model_dir, "model.pkl"))
    with open(os.path.join(model_dir, "metadata.json"), "r") as f:
        metadata = json.load(f)
        
    features = metadata['features']
    threshold = metadata['threshold']
    
    print("Loading Early Warning Detector...")
    ew_detector = EarlyWarningDetector()
    
    # Full Grid
    configs = [
        {"scenario": "clean", "strength": None}
    ]
    
    for s in [5, 15, 30, 60, 120]:
        configs.append({"scenario": "timing_jitter", "strength": s})
        
    for s in [2, 5, 10, 24]:
        configs.append({"scenario": "low_and_slow", "strength": s})
        
    for s in [0.1, 0.3, 0.5, 0.8, 1.0]:
        configs.append({"scenario": "merchant_hopping", "strength": s})
        configs.append({"scenario": "device_rotation", "strength": s})
        configs.append({"scenario": "account_rotation", "strength": s})
        
    for f in [2, 3, 5, 10]:
        for g in [1, 6, 12, 24]:
            configs.append({"scenario": "fragmented_bursts", "strength": (f, g)})
            
    output_dir = "artifacts/experiments/m14_robustness/early_warning"
    os.makedirs(output_dir, exist_ok=True)
    
    baseline_results = {}
    ew_results = {}
    comparison = {}
    
    seed = 42
    
    # Pre-calculate clean baseline for FPR
    print("Calculating clean baseline for FPR...")
    clean_df, _, _, _ = apply_perturbation(raw_test_df, labels_df, test_campaigns, "clean", None, seed)
    clean_ext_df = extract_all_features(clean_df)
    clean_cand_d_probs = model.predict_proba(clean_ext_df[features])[:, 1]
    clean_cand_d_preds = (clean_cand_d_probs >= threshold).astype(int)
    clean_ew_preds = ew_detector.evaluate_batch(clean_ext_df).astype(int)
    clean_combined_preds = (clean_cand_d_preds | clean_ew_preds).astype(int)
    
    base_clean_fp = ((clean_ext_df['is_abuse'] == 0) & (clean_cand_d_preds == 1)).sum()
    ew_clean_fp = ((clean_ext_df['is_abuse'] == 0) & (clean_combined_preds == 1)).sum()
    total_clean = (clean_ext_df['is_abuse'] == 0).sum()
    
    for config in configs:
        scenario = config["scenario"]
        strength = config["strength"]
        strength_str = str(strength) if strength is not None else "None"
        if isinstance(strength, tuple):
            strength_str = f"{strength[0]}_{strength[1]}"
            
        print(f"\nRunning: {scenario} {strength_str}")
        
        pert_df, pert_camp, mapping_df, label_status = apply_perturbation(
            raw_test_df, labels_df, test_campaigns, scenario, strength, seed
        )
        
        ext_df = extract_all_features(pert_df)
        
        # Candidate D Inference
        X = ext_df[features]
        y_true = ext_df['is_abuse']
        
        y_prob = model.predict_proba(X)[:, 1]
        y_pred = (y_prob >= threshold).astype(int)
        
        ext_df['predicted_fraud'] = y_pred
        
        # Early Warning Inference
        ew_preds = ew_detector.evaluate_batch(ext_df).astype(int)
        ext_df['combined_signal'] = (y_pred | ew_preds).astype(int)
        
        # --- Metrics Calculation ---
        
        # A. Candidate D Only
        tx_metrics_A = calculate_metrics(y_true, y_pred, y_prob)
        camp_metrics_A = evaluate_ttd(ext_df, pert_camp)
        
        # B. Candidate D + Early Warning
        tx_metrics_B = calculate_metrics(y_true, ext_df['combined_signal'], y_prob) # y_prob doesn't matter for combined
        
        ext_df_temp = ext_df.copy()
        ext_df_temp['predicted_fraud'] = ext_df_temp['combined_signal']
        camp_metrics_B = evaluate_ttd(ext_df_temp, pert_camp)
        
        # False Positives & FPR
        fp_A = ((y_true == 0) & (y_pred == 1)).sum()
        fp_B = ((y_true == 0) & (ext_df['combined_signal'] == 1)).sum()
        
        if scenario == "clean":
            fpr_A = fp_A / total_clean if total_clean > 0 else 0
            fpr_B = fp_B / total_clean if total_clean > 0 else 0
        else:
            fpr_A = base_clean_fp / total_clean if total_clean > 0 else 0
            fpr_B = ew_clean_fp / total_clean if total_clean > 0 else 0
            
        # Risk Case & Spike Simulation
        spike_detector = MerchantSpikeDetector(bucket_size='1h', lookback_window=6)
        
        cases_A = set()
        cases_B = set()
        spikes_A = set()
        spikes_B = set()
        
        flagged_tx_ids_A = set(ext_df[ext_df['predicted_fraud'] == 1]['transaction_id'])
        flagged_tx_ids_B = set(ext_df[ext_df['combined_signal'] == 1]['transaction_id'])
        
        for _, camp in pert_camp.iterrows():
            camp_id = camp['campaign_id']
            camp_txs = ext_df[ext_df['campaign_id'] == camp_id]
            if camp_txs.empty: continue
            
            # Risk Cases
            if camp_txs['predicted_fraud'].sum() > 0:
                cases_A.add(camp_id)
            if camp_txs['combined_signal'].sum() > 0:
                cases_B.add(camp_id)
                
            # Spikes A
            for _, tx in camp_txs.iterrows():
                res = spike_detector.compute_spike(tx['merchant_id'], tx['timestamp'], ext_df, flagged_tx_ids_A)
                if res['severity'] in ['HIGH', 'CRITICAL']:
                    spikes_A.add(camp_id)
                    cases_A.add(camp_id)
                    break
                    
            # Spikes B
            for _, tx in camp_txs.iterrows():
                res = spike_detector.compute_spike(tx['merchant_id'], tx['timestamp'], ext_df, flagged_tx_ids_B)
                if res['severity'] in ['HIGH', 'CRITICAL']:
                    spikes_B.add(camp_id)
                    cases_B.add(camp_id)
                    break
                    
        total_campaigns = len(pert_camp)
        
        # Expected Cost
        # Cost = (FN * 100) + (FP * 10)
        cost_A = (tx_metrics_A['confusion_matrix']['fn'] * 100) + (fp_A * 10)
        cost_B = (tx_metrics_B['confusion_matrix']['fn'] * 100) + (fp_B * 10)
        
        # Populate Results
        if scenario not in baseline_results:
            baseline_results[scenario] = {}
            ew_results[scenario] = {}
            comparison[scenario] = {}
            
        baseline_results[scenario][strength_str] = {
            "precision": tx_metrics_A["precision"],
            "recall": tx_metrics_A["recall"],
            "f1": tx_metrics_A["f1"],
            "fp": int(fp_A),
            "fn": tx_metrics_A['confusion_matrix']["fn"],
            "clean_fpr": float(fpr_A),
            "campaign_coverage": camp_metrics_A["coverage"],
            "median_ttd": camp_metrics_A["median_ttd_mins"],
            "spike_detection_rate": len(spikes_A) / total_campaigns if total_campaigns > 0 else 0,
            "risk_case_rate": len(cases_A) / total_campaigns if total_campaigns > 0 else 0,
            "expected_cost": int(cost_A)
        }
        
        ew_results[scenario][strength_str] = {
            "precision": tx_metrics_B["precision"],
            "recall": tx_metrics_B["recall"],
            "f1": tx_metrics_B["f1"],
            "fp": int(fp_B),
            "fn": tx_metrics_B['confusion_matrix']["fn"],
            "clean_fpr": float(fpr_B),
            "campaign_coverage": camp_metrics_B["coverage"],
            "median_ttd": camp_metrics_B["median_ttd_mins"],
            "spike_detection_rate": len(spikes_B) / total_campaigns if total_campaigns > 0 else 0,
            "risk_case_rate": len(cases_B) / total_campaigns if total_campaigns > 0 else 0,
            "expected_cost": int(cost_B)
        }
        
        comparison[scenario][strength_str] = {
            "incremental_detections": int(tx_metrics_A['confusion_matrix']["fn"] - tx_metrics_B['confusion_matrix']["fn"]),
            "incremental_fp": int(fp_B - fp_A),
            "ttd_improvement": (camp_metrics_A["median_ttd_mins"] or 0) - (camp_metrics_B["median_ttd_mins"] or 0),
            "cost_delta": int(cost_B - cost_A)
        }
        
    with open(os.path.join(output_dir, "baseline_results.json"), "w") as f:
        json.dump(baseline_results, f, indent=2)
        
    with open(os.path.join(output_dir, "early_warning_results.json"), "w") as f:
        json.dump(ew_results, f, indent=2)
        
    with open(os.path.join(output_dir, "comparison.json"), "w") as f:
        json.dump(comparison, f, indent=2)
        
    with open(os.path.join(output_dir, "config.json"), "w") as f:
        json.dump({"detector_version": ew_detector.version, "timestamp": datetime.utcnow().isoformat()}, f, indent=2)
        
    print("\nFinal robustness evaluation complete. Results saved to artifacts/experiments/m14_robustness/early_warning/")

if __name__ == "__main__":
    run_final_robustness()
