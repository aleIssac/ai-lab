"""模型训练 + MLflow 实验记录。

用法：
    python src/train.py

产物：
    mlflow.db / mlruns/         实验记录（可用 mlflow ui 查看）
    models/model.pkl            最优模型
    models/metrics.json         最优模型的评估指标
"""

import json
import os

import joblib
import matplotlib
import mlflow
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

matplotlib.use("Agg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "processed", "clean.parquet")
MODEL_DIR = os.path.join(ROOT, "models")
DB = os.path.join(ROOT, "mlflow.db")

NUM_COLS = [
    "age",
    "tenure_months",
    "monthly_charge",
    "total_charge",
    "support_calls",
    "is_active",
    "avg_monthly",
    "support_per_year",
]
CAT_COLS = ["contract_type", "payment_method"]
TARGET = "churn"


def candidates():
    """三组候选实验，用于在 MLflow 里做对比。"""
    return [
        (
            "LogReg-C0.1",
            LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced"),
            {"model": "LogisticRegression", "C": 0.1, "class_weight": "balanced"},
        ),
        (
            "LogReg-C1.0",
            LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced"),
            {"model": "LogisticRegression", "C": 1.0, "class_weight": "balanced"},
        ),
        (
            "RandomForest-200",
            RandomForestClassifier(
                n_estimators=200, max_depth=8, class_weight="balanced", random_state=42
            ),
            {
                "model": "RandomForest",
                "n_estimators": 200,
                "max_depth": 8,
                "class_weight": "balanced",
            },
        ),
    ]


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = pd.read_parquet(DATA)
    prep = joblib.load(os.path.join(MODEL_DIR, "preprocessor.pkl"))

    X = prep.transform(df[NUM_COLS + CAT_COLS])
    y = df[TARGET].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"训练集 {X_train.shape[0]} 条 / 测试集 {X_test.shape[0]} 条")

    mlflow.set_tracking_uri(f"sqlite:///{DB}")
    mlflow.set_experiment("churn-prediction")

    best = {"f1": -1.0, "name": None, "model": None, "metrics": None}

    for name, model, params in candidates():
        with mlflow.start_run(run_name=name):
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            proba = model.predict_proba(X_test)[:, 1]

            metrics = {
                "accuracy": accuracy_score(y_test, pred),
                "precision": precision_score(y_test, pred, zero_division=0),
                "recall": recall_score(y_test, pred, zero_division=0),
                "f1": f1_score(y_test, pred, zero_division=0),
                "roc_auc": roc_auc_score(y_test, proba),
            }

            mlflow.log_params(params)
            mlflow.log_metrics(metrics)

            fig, ax = plt.subplots(figsize=(4, 3.2))
            ConfusionMatrixDisplay.from_predictions(
                y_test, pred, ax=ax, colorbar=False, cmap="Blues"
            )
            ax.set_title(name)
            fig.tight_layout()
            mlflow.log_figure(fig, "confusion_matrix.png")
            plt.close(fig)

            path = os.path.join(MODEL_DIR, f"candidate_{name}.pkl")
            joblib.dump(model, path)
            mlflow.log_artifact(path)
            os.remove(path)

            print(
                f"  {name:20s} acc={metrics['accuracy']:.4f} "
                f"f1={metrics['f1']:.4f} auc={metrics['roc_auc']:.4f}"
            )

            if metrics["f1"] > best["f1"]:
                best = {
                    "f1": metrics["f1"],
                    "name": name,
                    "model": model,
                    "metrics": metrics,
                }

    joblib.dump(best["model"], os.path.join(MODEL_DIR, "model.pkl"))
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(
            {"best_run": best["name"], **best["metrics"]}, f, ensure_ascii=False, indent=2
        )

    print(f"\n最优模型: {best['name']} (f1={best['f1']:.4f}) -> models/model.pkl")
    print(f"实验记录: {DB}")
    print("查看实验: mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5001")


if __name__ == "__main__":
    main()
