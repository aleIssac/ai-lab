"""六个模块的功能验收脚本（不含 Tab 补全）。

在容器内运行：
    docker exec -it ai-lab /opt/venv/bin/python /home/coder/project/tools/acceptance_check.py

输出 Markdown 报告到 docs/验收报告.md
"""

import json
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

RESULTS = []


def check(module, name, fn):
    t0 = time.time()
    try:
        detail = fn()
        RESULTS.append({
            "module": module, "name": name, "ok": True,
            "detail": detail, "seconds": round(time.time() - t0, 2),
        })
        print(f"[PASS] {module} / {name}  {detail}  ({time.time()-t0:.1f}s)")
    except Exception as exc:  # noqa: BLE001
        RESULTS.append({
            "module": module, "name": name, "ok": False,
            "detail": f"{type(exc).__name__}: {exc}",
            "seconds": round(time.time() - t0, 2),
            "trace": traceback.format_exc()[-500:],
        })
        print(f"[FAIL] {module} / {name}  {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- 模块一：AI 应用

def t_data():
    import pandas as pd
    df = pd.read_parquet(os.path.join(ROOT, "data", "processed", "clean.parquet"))
    assert len(df) > 1000, f"行数异常 {len(df)}"
    return f"{len(df)} 行 × {len(df.columns)} 列"


def t_model():
    import joblib
    import pandas as pd

    model = joblib.load(os.path.join(ROOT, "models", "model.pkl"))
    prep = joblib.load(os.path.join(ROOT, "models", "preprocessor.pkl"))
    df = pd.read_parquet(os.path.join(ROOT, "data", "processed", "clean.parquet"))

    X = prep.transform(df.drop(columns=["churn"]))
    proba = model.predict_proba(X)[:, 1]
    return f"预测 {len(proba)} 条，平均流失概率 {proba.mean():.3f}"


def t_api():
    import requests

    payload = {
        "age": 29, "tenure_months": 3, "monthly_charge": 130, "total_charge": 390,
        "contract_type": "按月付费", "payment_method": "电子支票",
        "support_calls": 9, "is_active": 0,
    }
    r = requests.post("http://127.0.0.1:8000/predict", json=payload, timeout=15)
    r.raise_for_status()
    d = r.json()
    return f"高风险客户 → churn={d['churn']}, p={d['probability']}, 等级={d['risk_level']}"


# ---------------------------------------------------------------- 模块二：大数据

def t_spark():
    from pyspark.sql import SparkSession

    spark = (SparkSession.builder.master("local[2]").appName("acceptance")
             .config("spark.ui.enabled", "false").getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    try:
        path = os.path.join(ROOT, "data", "raw", "customer_churn.csv")
        df = spark.read.option("header", True).option("inferSchema", True).csv(path)
        df = df.toDF(*[c.replace("\ufeff", "").strip() for c in df.columns])
        raw = df.count()
        clean = df.dropDuplicates(["customer_id"]).dropna(subset=["churn"]).count()
        version = spark.version
    finally:
        spark.stop()
    return f"Spark {version}：原始 {raw} 行 → 清洗后 {clean} 行"


# ---------------------------------------------------------------- 模块三：大模型

def t_rag():
    from src.rag_core import KnowledgeBase

    kb = KnowledgeBase(os.path.join(ROOT, "data", "kb")).build()
    hits = kb.search("矩阵维度不匹配怎么排查", k=3)
    assert hits, "检索无结果"
    assert hits[0]["score"] > 0.05, f"相似度过低 {hits[0]['score']}"
    return (f"{kb.stats()['documents']} 篇文档 / {kb.stats()['chunks']} 块，"
            f"top1={hits[0]['title']}({hits[0]['score']:.3f})")


def t_rag_page():
    import requests

    r = requests.get("http://127.0.0.1:8502/_stcore/health", timeout=10)
    return f"RAG 页面 HTTP {r.status_code}"


# ---------------------------------------------------------------- 模块四：可视化

def t_pages():
    import requests

    targets = {
        "门户": "http://host.docker.internal:3000/",
        "code-server": "http://127.0.0.1:8080/",
        "MLflow": "http://127.0.0.1:5001/",
        "预测页面": "http://127.0.0.1:8501/",
        "playground": "http://host.docker.internal:3000/nn-playground/",
        "transformer": "http://host.docker.internal:3000/transformer-explainer/",
        "convnetjs": "http://host.docker.internal:3000/convnetjs/demo/mnist.html",
    }
    ok, bad = [], []
    for name, url in targets.items():
        try:
            r = requests.get(url, timeout=8, allow_redirects=False)
            (ok if r.status_code < 400 else bad).append(f"{name}({r.status_code})")
        except Exception:  # noqa: BLE001
            bad.append(name)
    if bad:
        raise RuntimeError(f"不可达: {bad}")
    return f"{len(ok)} 个页面全部可达"


def main():
    check("AI 应用开发", "数据清洗产物", t_data)
    check("AI 应用开发", "模型加载与批量预测", t_model)
    check("AI 应用开发", "在线预测 API", t_api)
    check("大数据应用开发", "Spark 读取与清洗", t_spark)
    check("大模型应用开发", "RAG 检索链路", t_rag)
    check("大模型应用开发", "RAG 页面", t_rag_page)
    check("可视化模块", "七个页面可达性", t_pages)

    passed = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)
    print(f"\n=== {passed}/{total} 通过 ===")

    # 写报告
    out = os.path.join(ROOT, "docs", "验收报告.md")
    lines = [
        "# 功能验收报告",
        "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"结果：**{passed}/{total} 通过**",
        "",
        "| 模块 | 检查项 | 结果 | 详情 | 耗时 |",
        "|---|---|---|---|---|",
    ]
    for r in RESULTS:
        mark = "✅" if r["ok"] else "❌"
        lines.append(
            f"| {r['module']} | {r['name']} | {mark} | {r['detail']} | {r['seconds']}s |"
        )

    lines += ["", "## 说明", "",
              "- 检查项均为真实调用，不是页面截图",
              "- Tab 补全（需求②）因 code-server 渲染问题未包含在本报告"]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"报告已写入: {out}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
