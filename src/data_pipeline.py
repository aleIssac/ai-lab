"""数据清洗 + 特征工程。

用法：
    python src/data_pipeline.py

产物：
    data/processed/clean.parquet   清洗并加工后的数据
    models/preprocessor.pkl        固化好的预处理器（训练与推理共用，避免不一致）
"""

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "customer_churn.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed")
MODEL_DIR = os.path.join(ROOT, "models")

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


def load_raw():
    df = pd.read_csv(RAW, encoding="utf-8-sig")
    print(f"[1/5] 读取原始数据: {df.shape[0]} 行 x {df.shape[1]} 列")
    return df


def clean(df):
    """四类典型脏数据处理。"""
    before = df.shape[0]

    df = df.drop_duplicates(subset=["customer_id"]).copy()
    dropped = before - df.shape[0]

    for col in ["age", "monthly_charge", "total_charge"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.loc[df["age"] > 100, "age"] = np.nan
    df.loc[df["monthly_charge"] < 0, "monthly_charge"] = np.nan
    df.loc[df["total_charge"] < 0, "total_charge"] = np.nan

    df = df.dropna(subset=["churn"]).copy()
    df["churn"] = df["churn"].astype(int)

    print(
        f"[2/5] 清洗完成：去重 {dropped} 行，"
        f"年龄缺失 {df['age'].isna().sum()}，"
        f"月费缺失 {df['monthly_charge'].isna().sum()}，"
        f"总费用缺失 {df['total_charge'].isna().sum()}"
    )
    return df


def engineer(df):
    """特征工程：衍生比率类特征。"""
    df["avg_monthly"] = df["total_charge"] / df["tenure_months"].replace(0, np.nan)
    df["support_per_year"] = df["support_calls"] / (df["tenure_months"] / 12).replace(0, np.nan)

    df["avg_monthly"] = df["avg_monthly"].fillna(df["monthly_charge"])
    df["support_per_year"] = df["support_per_year"].fillna(0)

    print(f"[3/5] 特征工程完成：新增 avg_monthly, support_per_year，共 {df.shape[1]} 列")
    return df


def build_preprocessor():
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUM_COLS),
            ("cat", categorical, CAT_COLS),
        ],
        remainder="drop",
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = load_raw()
    df = clean(df)
    df = engineer(df)

    out_path = os.path.join(OUT_DIR, "clean.parquet")
    df.to_parquet(out_path, index=False)
    print(f"[4/5] 已保存: {out_path}  ({df.shape[0]} 行, {df.shape[1]} 列)")

    prep = build_preprocessor()
    prep.fit(df[NUM_COLS + CAT_COLS])
    prep_path = os.path.join(MODEL_DIR, "preprocessor.pkl")
    joblib.dump(prep, prep_path)
    print(f"[5/5] 预处理器已固化: {prep_path}")


if __name__ == "__main__":
    main()
