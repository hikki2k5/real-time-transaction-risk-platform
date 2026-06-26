# Model Card

## Model

The local training pipeline trains two tree-based gradient boosting candidates:

- LightGBM binary classifier with fraud class weighting.
- XGBoost binary classifier with fraud class weighting.

The best candidate is selected by PR-AUC and registered in local MLflow as `fraud-risk-model`.

## Intended Use

Fraud detection model for local transaction risk scoring experiments and decision support prototyping.

This model is not production-ready. The current pipeline can generate synthetic labels for local workflow testing only.

## Training Data

- `core.cleaned_transactions`
- `features.customer_transaction_features`
- `core.fraud_labels`

If `core.fraud_labels` is empty, the pipeline creates synthetic labels using simple heuristics and random sampling.

## Metrics

The pipeline evaluates:

- ROC-AUC
- PR-AUC
- Precision
- Recall
- F1
- Confusion matrix

Fraud detection is imbalanced, so PR-AUC and fraud recall are more informative than accuracy for this phase.

## Artifacts

- MLflow experiment: `fraud-risk-training`
- Registered model: `fraud-risk-model`
- Local fallback artifact: `model-artifacts/fraud-risk-model/`

## Limitations

- Synthetic labels do not represent real fraud outcomes.
- Metrics are pipeline smoke-test metrics, not production accuracy claims.
- Feature definitions are early local development baselines.

## TODO

- TODO Phase 7: Replace synthetic labels with real adjudicated fraud labels.
- TODO Phase 7: Add model validation thresholds and promotion workflow.
- TODO Phase 7: Document bias, drift, and monitoring considerations.
- TODO Phase 6: Document serving behavior and known limitations.
