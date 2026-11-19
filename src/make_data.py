"""生成一份带脏数据的客户流失数据集。

只使用标准库，不需要安装任何依赖，可单独运行：
    python src/make_data.py

生成的 CSV 故意包含缺失值、异常值、类型不一致和重复行，
用于演示「数据清洗」环节的处理效果。
"""

import csv
import math
import os
import random

random.seed(42)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "raw")
OUT_FILE = os.path.join(OUT_DIR, "customer_churn.csv")

N_ROWS = 1500

CONTRACTS = ["按月付费", "一年合约", "两年合约"]
CONTRACT_W = [0.55, 0.25, 0.20]
PAYMENTS = ["电子支票", "信用卡", "银行转账", "邮寄支票"]
PAYMENT_W = [0.40, 0.30, 0.20, 0.10]


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def pick(seq, weights):
    return random.choices(seq, weights=weights, k=1)[0]


def make_row(idx):
    age = random.randint(18, 70)
    tenure = random.randint(1, 72)
    monthly = round(random.uniform(20, 150), 2)
    support_calls = random.randint(0, 10)
    is_active = 1 if random.random() < 0.75 else 0
    contract = pick(CONTRACTS, CONTRACT_W)
    payment = pick(PAYMENTS, PAYMENT_W)

    total = round(monthly * tenure, 2)

    score = (
        0.35 * support_calls
        - 0.02 * tenure
        + (0.9 if contract == "按月付费" else -0.3)
        + (0.5 if payment == "电子支票" else 0.0)
        - 0.6 * is_active
        + random.gauss(0, 0.6)
        - 2.7
    )
    churn = 1 if sigmoid(score) > 0.5 else 0

    return {
        "customer_id": f"C{idx:05d}",
        "age": age,
        "tenure_months": tenure,
        "monthly_charge": monthly,
        "total_charge": f"{total:.2f}",
        "contract_type": contract,
        "payment_method": payment,
        "support_calls": support_calls,
        "is_active": is_active,
        "churn": churn,
    }


def dirty(rows):
    """注入四类常见脏数据问题。"""
    for row in rows:
        r = random.random()
        if r < 0.05:
            row["age"] = ""
        elif r < 0.07:
            row["age"] = "999"
        if random.random() < 0.04:
            row["monthly_charge"] = ""
        elif random.random() < 0.02:
            row["monthly_charge"] = "-10.00"
        if random.random() < 0.05:
            row["total_charge"] = "N/A"

    for _ in range(int(len(rows) * 0.03)):
        rows.append(dict(random.choice(rows)))

    return rows


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = dirty([make_row(i + 1) for i in range(N_ROWS)])
    random.shuffle(rows)

    fields = list(rows[0].keys())
    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    churn_rate = sum(int(r["churn"]) for r in rows) / len(rows)
    print(f"已生成: {OUT_FILE}")
    print(f"行数: {len(rows)}  流失率: {churn_rate:.1%}")


if __name__ == "__main__":
    main()
