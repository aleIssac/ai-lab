"""演示用的前端页面（Streamlit）。

用法：
    streamlit run apps/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

验收时打开 http://localhost:8501，拖动参数即可看到流失概率变化。
"""

import json
import os

import joblib
import pandas as pd
import streamlit as st

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

st.set_page_config(page_title="客户流失预测", page_icon="📉", layout="wide")


@st.cache_resource
def load():
    prep = joblib.load(os.path.join(MODEL_DIR, "preprocessor.pkl"))
    model = joblib.load(os.path.join(MODEL_DIR, "model.pkl"))
    return prep, model


@st.cache_data
def load_metrics():
    path = os.path.join(MODEL_DIR, "metrics.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


prep, model = load()
metrics = load_metrics()

st.title("客户流失预测")
st.caption("输入客户特征，模型实时给出流失概率")

if metrics:
    cols = st.columns(5)
    labels = [
        ("accuracy", "准确率"),
        ("precision", "精确率"),
        ("recall", "召回率"),
        ("f1", "F1"),
        ("roc_auc", "AUC"),
    ]
    for col, (key, label) in zip(cols, labels):
        col.metric(label, f"{metrics.get(key, 0):.3f}")
    st.caption(f"当前模型：{metrics.get('best_run', '-')}")
    st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("客户画像")
    age = st.slider("年龄", 18, 90, 35)
    tenure = st.slider("在网月数", 1, 72, 12)
    monthly = st.slider("月费（元）", 20.0, 200.0, 80.0, step=1.0)
    support = st.slider("客服呼叫次数", 0, 12, 2)
    contract = st.selectbox("合约类型", ["按月付费", "一年合约", "两年合约"])
    payment = st.selectbox("支付方式", ["电子支票", "信用卡", "银行转账", "邮寄支票"])
    is_active = st.radio("是否活跃", [1, 0], format_func=lambda v: "是" if v else "否", horizontal=True)

row = {
    "age": age,
    "tenure_months": tenure,
    "monthly_charge": monthly,
    "total_charge": monthly * tenure,
    "contract_type": contract,
    "payment_method": payment,
    "support_calls": support,
    "is_active": is_active,
}
row["avg_monthly"] = row["total_charge"] / max(tenure, 1)
row["support_per_year"] = support / max(tenure / 12, 1)

X = prep.transform(pd.DataFrame([row])[NUM_COLS + CAT_COLS])
proba = float(model.predict_proba(X)[0, 1])

with right:
    st.subheader("预测结果")
    st.metric("流失概率", f"{proba:.1%}")
    st.progress(min(proba, 1.0))

    if proba >= 0.6:
        st.error("高风险 —— 建议人工介入挽留")
    elif proba >= 0.3:
        st.warning("中风险 —— 建议发送优惠券")
    else:
        st.success("低风险 —— 保持现有运营策略")

    with st.expander("查看本次请求的原始特征"):
        st.json(row)

st.divider()
st.caption("模型、预处理器与指标均由 train.py 产出；本页面只负责交互，不含任何训练逻辑。")
