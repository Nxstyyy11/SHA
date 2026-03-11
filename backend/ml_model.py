"""
ML model training and prediction for diabetes risk assessment.
Uses RandomForestClassifier trained on the Pima Indians Diabetes Dataset.
Also compares against Logistic Regression for model evaluation.
"""
import os
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "diabetes_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "diabetes_scaler.pkl")
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CSV_PATH = os.path.join(DATA_DIR, "diabetes.csv")

FEATURE_COLS = [
    "pregnancies", "glucose", "blood_pressure", "skin_thickness",
    "insulin", "bmi", "dpf", "age"
]

FEATURE_LABELS = [
    "Pregnancies", "Glucose", "Blood Pressure", "Skin Thickness",
    "Insulin", "BMI", "Diabetes Pedigree", "Age"
]

# Cache for model metrics so we don't recompute every request
_metrics_cache: dict = {}


def _load_and_clean_data():
    """Load and clean the diabetes CSV, returning X, y arrays."""
    df = pd.read_csv(CSV_PATH)
    col_map = {
        "Pregnancies": "pregnancies",
        "Glucose": "glucose",
        "BloodPressure": "blood_pressure",
        "SkinThickness": "skin_thickness",
        "Insulin": "insulin",
        "BMI": "bmi",
        "DiabetesPedigreeFunction": "dpf",
        "Age": "age",
        "Outcome": "outcome",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    X = df[FEATURE_COLS].values
    y = df["outcome"].values
    # Replace 0s in certain columns with median (data cleaning)
    zero_cols = [1, 2, 3, 4, 5]  # glucose, bp, skin, insulin, bmi
    for col in zero_cols:
        median_val = np.median(X[X[:, col] != 0, col])
        X[X[:, col] == 0, col] = median_val
    return X, y


def _compute_metrics(model, X_test_scaled, y_test, model_name: str) -> dict:
    """Compute full classification metrics for a model."""
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    return {
        "model": model_name,
        "accuracy": round(float(accuracy_score(y_test, y_pred)) * 100, 1),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)) * 100, 1),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)) * 100, 1),
        "f1_score": round(float(f1_score(y_test, y_pred, zero_division=0)) * 100, 1),
        "auc_roc": round(float(roc_auc_score(y_test, y_prob)) * 100, 1),
    }


def train_model():
    """Train and save the RandomForest model; also trains Logistic Regression for comparison."""
    global _metrics_cache
    X, y = _load_and_clean_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # --- Random Forest ---
    rf_model = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=42, class_weight="balanced"
    )
    rf_model.fit(X_train_scaled, y_train)

    # --- Logistic Regression ---
    lr_model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    lr_model.fit(X_train_scaled, y_train)

    rf_metrics = _compute_metrics(rf_model, X_test_scaled, y_test, "Random Forest")
    lr_metrics = _compute_metrics(lr_model, X_test_scaled, y_test, "Logistic Regression")
    print(f"Random Forest accuracy: {rf_metrics['accuracy']}%")
    print(f"Logistic Regression accuracy: {lr_metrics['accuracy']}%")

    _metrics_cache = {
        "random_forest": rf_metrics,
        "logistic_regression": lr_metrics,
        "feature_importance": [
            {"feature": FEATURE_LABELS[i], "importance": round(float(v) * 100, 2)}
            for i, v in enumerate(rf_model.feature_importances_)
        ]
    }

    joblib.dump(rf_model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"Model saved to {MODEL_PATH}")

    return rf_model, scaler


def load_model():
    """Load the saved model, train if not exists. Always populates _metrics_cache."""
    global _metrics_cache
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        # Populate metrics cache if empty (e.g. after server restart)
        if not _metrics_cache:
            _populate_metrics_cache(model, scaler)
    else:
        model, scaler = train_model()
    return model, scaler


def _populate_metrics_cache(rf_model, scaler):
    """Recompute metrics on the existing dataset without retraining RF."""
    global _metrics_cache
    try:
        X, y = _load_and_clean_data()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        X_train_sc = scaler.transform(X_train)
        X_test_sc = scaler.transform(X_test)

        lr_model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
        lr_model.fit(X_train_sc, y_train)

        rf_metrics = _compute_metrics(rf_model, X_test_sc, y_test, "Random Forest")
        lr_metrics = _compute_metrics(lr_model, X_test_sc, y_test, "Logistic Regression")

        _metrics_cache = {
            "random_forest": rf_metrics,
            "logistic_regression": lr_metrics,
            "feature_importance": [
                {"feature": FEATURE_LABELS[i], "importance": round(float(v) * 100, 2)}
                for i, v in enumerate(rf_model.feature_importances_)
            ]
        }
    except Exception as e:
        print(f"Warning: could not populate metrics cache: {e}")


def get_feature_importance():
    """Return feature importances sorted descending."""
    load_model()
    items = _metrics_cache.get("feature_importance", [])
    return sorted(items, key=lambda x: x["importance"], reverse=True)


def get_model_accuracy():
    """Return the Random Forest accuracy as a percentage."""
    load_model()
    return _metrics_cache.get("random_forest", {}).get("accuracy", 0.0)


def get_model_comparison():
    """Return metrics for Random Forest and Logistic Regression side by side."""
    load_model()
    return [
        _metrics_cache.get("random_forest", {}),
        _metrics_cache.get("logistic_regression", {}),
    ]


def predict(features: dict):
    """
    Predict diabetes risk.
    features: dict with keys matching FEATURE_COLS
    Returns: {"prediction": 0 or 1, "probability": float 0-100}
    """
    model, scaler = load_model()

    X = np.array([[
        features.get("pregnancies", 0),
        features.get("glucose", 0),
        features.get("blood_pressure", 0),
        features.get("skin_thickness", 0),
        features.get("insulin", 0),
        features.get("bmi", 0),
        features.get("dpf", 0),
        features.get("age", 0),
    ]])

    X_scaled = scaler.transform(X)
    prediction = int(model.predict(X_scaled)[0])
    probability = float(model.predict_proba(X_scaled)[0][1]) * 100

    return {
        "prediction": prediction,
        "probability": round(probability, 1),
        "risk_level": (
            "High" if probability >= 60
            else "Medium" if probability >= 40
            else "Low"
        )
    }
