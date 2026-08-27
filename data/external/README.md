# External Benchmark Dataset

This directory is intended to hold external datasets used for independent benchmarking of transaction-level fraud detection.

## Kaggle Credit Card Fraud Detection (ULB)

We use the standard Kaggle Credit Card Fraud Detection dataset for the external benchmark.

- **Source**: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- **Expected Filename**: `creditcard.csv`
- **Expected Schema**:
  - `Time`: Number of seconds elapsed between this transaction and the first transaction in the dataset.
  - `V1` ... `V28`: Principal components obtained with PCA.
  - `Amount`: Transaction amount.
  - `Class`: 1 for fraudulent transactions, 0 otherwise.

**Note**: The actual dataset (`creditcard.csv`) is NOT committed to Git due to size and licensing constraints. You must download it manually from Kaggle and place it in this directory.
