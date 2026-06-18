import json
import time
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)


RESULT_PATH = Path("benchmark_result.json")
DATA_PATH = Path("creditcard.csv")


def load_or_generate_data():
    start = time.perf_counter()

    if DATA_PATH.exists():
        print("Loading real Kaggle dataset: creditcard.csv")
        df = pd.read_csv(DATA_PATH)

        if "Class" not in df.columns:
            raise ValueError("creditcard.csv must contain a 'Class' target column.")

        y = df["Class"].astype(int)
        X = df.drop(columns=["Class"])

        source = "kaggle_creditcard_csv"
    else:
        print("creditcard.csv not found. Generating synthetic fraud-like dataset.")
        X_np, y_np = make_classification(
            n_samples=284_807,
            n_features=30,
            n_informative=20,
            n_redundant=5,
            n_repeated=0,
            n_classes=2,
            weights=[0.998, 0.002],
            class_sep=2.0,
            random_state=42,
        )

        X = pd.DataFrame(X_np, columns=[f"V{i}" for i in range(1, 31)])
        y = pd.Series(y_np, name="Class")

        source = "synthetic_fraud_like"

    load_time = time.perf_counter() - start
    return X, y, source, load_time


def main():
    print("=" * 80)
    print("LightGBM CPU Benchmark — Day 16 Cloud Infrastructure Lab")
    print("=" * 80)

    X, y, dataset_source, load_time = load_or_generate_data()

    print(f"Dataset source: {dataset_source}")
    print(f"Rows: {len(X):,}")
    print(f"Features: {X.shape[1]}")
    print(f"Positive class count: {int(y.sum()):,}")
    print(f"Positive class ratio: {float(y.mean()):.6f}")
    print(f"Load/generation time: {load_time:.4f} sec")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42,
    )

    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=64,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining LightGBM...")
    train_start = time.perf_counter()

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        eval_metric="auc",
        callbacks=[
            lgb.early_stopping(stopping_rounds=30),
            lgb.log_evaluation(period=50),
        ],
    )

    training_time = time.perf_counter() - train_start

    print("\nRunning inference...")
    pred_start = time.perf_counter()
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)
    inference_time_all = time.perf_counter() - pred_start

    single_start = time.perf_counter()
    _ = model.predict_proba(X_test.iloc[[0]])[:, 1]
    single_latency_ms = (time.perf_counter() - single_start) * 1000

    batch_size = min(1000, len(X_test))
    batch_start = time.perf_counter()
    _ = model.predict_proba(X_test.iloc[:batch_size])[:, 1]
    batch_time = time.perf_counter() - batch_start
    throughput_rows_per_sec = batch_size / batch_time if batch_time > 0 else None

    auc = roc_auc_score(y_test, y_proba)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()

    result = {
        "dataset_source": dataset_source,
        "rows": int(len(X)),
        "features": int(X.shape[1]),
        "positive_class_count": int(y.sum()),
        "positive_class_ratio": float(y.mean()),
        "load_time_sec": round(load_time, 4),
        "training_time_sec": round(training_time, 4),
        "best_iteration": int(getattr(model, "best_iteration_", 0) or 0),
        "auc_roc": round(float(auc), 6),
        "accuracy": round(float(accuracy), 6),
        "f1_score": round(float(f1), 6),
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "confusion_matrix": cm,
        "inference_time_all_test_rows_sec": round(inference_time_all, 6),
        "inference_latency_1_row_ms": round(float(single_latency_ms), 6),
        "inference_throughput_1000_rows_per_sec": round(float(throughput_rows_per_sec), 2),
        "machine": {
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    print("\n" + "=" * 80)
    print("Benchmark Results")
    print("=" * 80)
    for key, value in result.items():
        if key != "machine":
            print(f"{key}: {value}")

    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved results to: {RESULT_PATH.resolve()}")


if __name__ == "__main__":
    main()
