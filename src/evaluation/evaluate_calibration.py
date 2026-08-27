import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, UTC
from sklearn.calibration import IsotonicRegression, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from src.models.m04_temporal import prepare_data
from src.models.external_benchmark_utils import load_and_split_external_data

def expected_calibration_error(y_true, y_prob, n_bins=10):
    bins = np.linspace(0., 1., n_bins + 1)
    binids = np.digitize(y_prob, bins) - 1
    
    ece = 0.0
    for i in range(n_bins):
        bin_mask = (binids == i)
        if np.sum(bin_mask) > 0:
            bin_prob = y_prob[bin_mask].mean()
            bin_acc = y_true[bin_mask].mean()
            bin_weight = np.sum(bin_mask) / len(y_prob)
            ece += bin_weight * np.abs(bin_prob - bin_acc)
    return float(ece)

def plot_reliability_diagram(y_true, y_prob_uncal, y_prob_cal, selected_method, title, save_path):
    plt.figure(figsize=(8, 8))
    ax1 = plt.subplot2grid((3, 1), (0, 0), rowspan=2)
    ax2 = plt.subplot2grid((3, 1), (2, 0))
    
    ax1.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated")
    
    for y_prob, name, color in [(y_prob_uncal, "Uncalibrated", "blue"), (y_prob_cal, f"Calibrated ({selected_method})", "red")]:
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
        ax1.plot(prob_pred, prob_true, "s-", label=name, color=color)
        ax2.hist(y_prob, range=(0, 1), bins=10, label=name, histtype="step", lw=2, color=color)
        
    ax1.set_ylabel("Fraction of positives")
    ax1.set_ylim([-0.05, 1.05])
    ax1.legend(loc="lower right")
    ax1.set_title(title)
    
    ax2.set_xlabel("Mean predicted value")
    ax2.set_ylabel("Count")
    ax2.legend(loc="upper center", ncol=2)
    
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()

from sklearn.model_selection import KFold

def evaluate_calibration():
    print("Evaluating Probability Calibration (Phase 4C)...")
    exp_dir = "artifacts/experiments/m13_calibration"
    os.makedirs(exp_dir, exist_ok=True)
    
    results = {}
    
    # 1. Candidate D (M01 Dataset)
    print("Processing Candidate D (M01)...")
    m01_model_path = "artifacts/models/candidate_d/model.pkl"
    m01_meta_path = "artifacts/models/candidate_d/metadata.json"
    
    if os.path.exists(m01_model_path) and os.path.exists(m01_meta_path):
        m01_model = joblib.load(m01_model_path)
        with open(m01_meta_path, "r") as f:
            m01_meta = json.load(f)
            
        labels_df = pd.read_csv("data/generated/m01-world-v1/ground_truth/event_labels.csv")
        val_df = prepare_data("validation", labels_df)
        test_df = prepare_data("test", labels_df)
        
        features = m01_meta["features"]
        
        # Uncalibrated predictions
        y_val_prob_uncal = m01_model.predict_proba(val_df[features])[:, 1]
        y_test_prob_uncal = m01_model.predict_proba(test_df[features])[:, 1]
        
        y_val = val_df['is_abuse'].values
        y_test = test_df['is_abuse'].values
        
        # K-Fold CV on Validation Set
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        iso_briers = []
        sig_briers = []
        
        for train_idx, val_idx in kf.split(y_val_prob_uncal):
            y_train_fold = y_val[train_idx]
            y_val_fold = y_val[val_idx]
            prob_train_fold = y_val_prob_uncal[train_idx]
            prob_val_fold = y_val_prob_uncal[val_idx]
            
            # Isotonic
            iso = IsotonicRegression(out_of_bounds='clip')
            iso.fit(prob_train_fold, y_train_fold)
            iso_briers.append(brier_score_loss(y_val_fold, iso.predict(prob_val_fold)))
            
            # Sigmoid
            sig = LogisticRegression()
            sig.fit(prob_train_fold.reshape(-1, 1), y_train_fold)
            sig_briers.append(brier_score_loss(y_val_fold, sig.predict_proba(prob_val_fold.reshape(-1, 1))[:, 1]))
            
        mean_brier_iso = np.mean(iso_briers)
        mean_brier_sig = np.mean(sig_briers)
        
        # Select best method and fit on full validation set
        if mean_brier_iso < mean_brier_sig:
            selected_method = "IsotonicRegression"
            calibrator = IsotonicRegression(out_of_bounds='clip')
            calibrator.fit(y_val_prob_uncal, y_val)
            y_test_prob_cal = calibrator.predict(y_test_prob_uncal)
        else:
            selected_method = "Sigmoid"
            calibrator = LogisticRegression()
            calibrator.fit(y_val_prob_uncal.reshape(-1, 1), y_val)
            y_test_prob_cal = calibrator.predict_proba(y_test_prob_uncal.reshape(-1, 1))[:, 1]
            
        # Save calibrator
        joblib.dump(calibrator, os.path.join(exp_dir, "calibrator_m01.pkl"))
        
        # Metrics
        brier_uncal = brier_score_loss(y_test, y_test_prob_uncal)
        brier_cal = brier_score_loss(y_test, y_test_prob_cal)
        
        ece_uncal = expected_calibration_error(y_test, y_test_prob_uncal)
        ece_cal = expected_calibration_error(y_test, y_test_prob_cal)
        
        plot_path = os.path.join(exp_dir, "reliability_m01.png")
        plot_reliability_diagram(y_test, y_test_prob_uncal, y_test_prob_cal, selected_method, "Reliability Diagram: Candidate D (M01 Test)", plot_path)
        
        results["candidate_d"] = {
            "calibration_method": "KFold CV Selection",
            "cv_fold_count": 5,
            "cv_mean_brier_isotonic": float(mean_brier_iso),
            "cv_mean_brier_sigmoid": float(mean_brier_sig),
            "selected_method": selected_method,
            "test_brier_uncalibrated": float(brier_uncal),
            "test_brier_calibrated": float(brier_cal),
            "test_ece_uncalibrated": float(ece_uncal),
            "test_ece_calibrated": float(ece_cal),
            "reliability_diagram": plot_path,
            "split_information": "m01-world-v1 (train/val/test)",
            "model_identifier": "candidate_d_v1"
        }
    else:
        print("Candidate D model not found, skipping.")
        
    # 2. External Benchmark
    print("Processing External Benchmark...")
    ext_model_path = "artifacts/models/external_benchmark/model.pkl"
    ext_meta_path = "artifacts/models/external_benchmark/metadata.json"
    
    if os.path.exists(ext_model_path) and os.path.exists(ext_meta_path):
        ext_model = joblib.load(ext_model_path)
        with open(ext_meta_path, "r") as f:
            ext_meta = json.load(f)
            
        data_path = "data/external/creditcard.csv"
        _, val_df_ext, test_df_ext, features_ext, target_ext = load_and_split_external_data(data_path)
        
        # Uncalibrated predictions
        y_val_prob_uncal_ext = ext_model.predict_proba(val_df_ext[features_ext])[:, 1]
        y_test_prob_uncal_ext = ext_model.predict_proba(test_df_ext[features_ext])[:, 1]
        
        y_val_ext = val_df_ext[target_ext].values
        y_test_ext = test_df_ext[target_ext].values
        
        # K-Fold CV on Validation Set
        kf_ext = KFold(n_splits=5, shuffle=True, random_state=42)
        iso_briers_ext = []
        sig_briers_ext = []
        
        for train_idx, val_idx in kf_ext.split(y_val_prob_uncal_ext):
            y_train_fold = y_val_ext[train_idx]
            y_val_fold = y_val_ext[val_idx]
            prob_train_fold = y_val_prob_uncal_ext[train_idx]
            prob_val_fold = y_val_prob_uncal_ext[val_idx]
            
            # Isotonic
            iso = IsotonicRegression(out_of_bounds='clip')
            iso.fit(prob_train_fold, y_train_fold)
            iso_briers_ext.append(brier_score_loss(y_val_fold, iso.predict(prob_val_fold)))
            
            # Sigmoid
            sig = LogisticRegression()
            sig.fit(prob_train_fold.reshape(-1, 1), y_train_fold)
            sig_briers_ext.append(brier_score_loss(y_val_fold, sig.predict_proba(prob_val_fold.reshape(-1, 1))[:, 1]))
            
        mean_brier_iso_ext = np.mean(iso_briers_ext)
        mean_brier_sig_ext = np.mean(sig_briers_ext)
        
        # Select best method and fit on full validation set
        if mean_brier_iso_ext < mean_brier_sig_ext:
            selected_method_ext = "IsotonicRegression"
            calibrator_ext = IsotonicRegression(out_of_bounds='clip')
            calibrator_ext.fit(y_val_prob_uncal_ext, y_val_ext)
            y_test_prob_cal_ext = calibrator_ext.predict(y_test_prob_uncal_ext)
        else:
            selected_method_ext = "Sigmoid"
            calibrator_ext = LogisticRegression()
            calibrator_ext.fit(y_val_prob_uncal_ext.reshape(-1, 1), y_val_ext)
            y_test_prob_cal_ext = calibrator_ext.predict_proba(y_test_prob_uncal_ext.reshape(-1, 1))[:, 1]
            
        # Save calibrator
        joblib.dump(calibrator_ext, os.path.join(exp_dir, "calibrator_external.pkl"))
        
        # Metrics
        brier_uncal_ext = brier_score_loss(y_test_ext, y_test_prob_uncal_ext)
        brier_cal_ext = brier_score_loss(y_test_ext, y_test_prob_cal_ext)
        
        ece_uncal_ext = expected_calibration_error(y_test_ext, y_test_prob_uncal_ext)
        ece_cal_ext = expected_calibration_error(y_test_ext, y_test_prob_cal_ext)
        
        plot_path_ext = os.path.join(exp_dir, "reliability_external.png")
        plot_reliability_diagram(y_test_ext, y_test_prob_uncal_ext, y_test_prob_cal_ext, selected_method_ext, "Reliability Diagram: External Benchmark (Test)", plot_path_ext)
        
        results["external_benchmark"] = {
            "calibration_method": "KFold CV Selection",
            "cv_fold_count": 5,
            "cv_mean_brier_isotonic": float(mean_brier_iso_ext),
            "cv_mean_brier_sigmoid": float(mean_brier_sig_ext),
            "selected_method": selected_method_ext,
            "test_brier_uncalibrated": float(brier_uncal_ext),
            "test_brier_calibrated": float(brier_cal_ext),
            "test_ece_uncalibrated": float(ece_uncal_ext),
            "test_ece_calibrated": float(ece_cal_ext),
            "reliability_diagram": plot_path_ext,
            "split_information": "temporal_64_16_20 (train/val/test)",
            "model_identifier": "external_benchmark_v1"
        }
    else:
        print("External benchmark model not found, skipping.")
        
    metadata = {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "calibration_protocol": "K-Fold CV on Validation for Selection, Evaluate on Test",
        "results": results
    }
    
    with open(os.path.join(exp_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Calibration evaluation complete. Results saved to {exp_dir}")

if __name__ == "__main__":
    evaluate_calibration()
