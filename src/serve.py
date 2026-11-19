"""预测服务（FastAPI）。

用法：
    uvicorn src.serve:app --host 0.0.0.0 --port 8000

测试：
    curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "..."
"""

import os

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

app = FastAPI(title="客户流失预测服务", version="1.0.0")

_preprocessor = joblib.load(os.path.join(MODEL_DIR, "preprocessor.pkl"))
_model = joblib.load(os.path.join(MODEL_DIR, "model.pkl"))


class Customer(BaseModel):
    age: float = Field(35, ge=0, le=120, description="年龄")
    tenure_months: int = Field(12, ge=0, le=120, description="在网月数")
    monthly_charge: float = Field(80.0, ge=0, description="月费")
    total_charge: float = Field(960.0, ge=0, description="累计费用")
    contract_type: str = Field("按月付费", description="合约类型")
    payment_method: str = Field("电子支票", description="支付方式")
    support_calls: int = Field(2, ge=0, le=50, description="客服呼叫次数")
    is_active: int = Field(1, ge=0, le=1, description="是否活跃")


class Prediction(BaseModel):
    churn: int
    probability: float
    risk_level: str


def _to_frame(c: Customer) -> pd.DataFrame:
    row = c.model_dump()
    row["avg_monthly"] = row["total_charge"] / max(row["tenure_months"], 1)
    row["support_per_year"] = row["support_calls"] / max(row["tenure_months"] / 12, 1)
    return pd.DataFrame([row])[NUM_COLS + CAT_COLS]


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/predict", response_model=Prediction)
def predict(customer: Customer):
    X = _preprocessor.transform(_to_frame(customer))
    proba = float(_model.predict_proba(X)[0, 1])
    label = int(proba >= 0.5)
    level = "高" if proba >= 0.6 else ("中" if proba >= 0.3 else "低")
    return Prediction(churn=label, probability=round(proba, 4), risk_level=level)


@app.get("/")
def index():
    return {
        "service": "客户流失预测",
        "endpoints": ["/health", "/predict", "/docs"],
        "note": "把 /docs 打开可以交互式调试接口",
    }
