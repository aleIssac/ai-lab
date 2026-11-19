"""生成验收演示用的四个 notebook。

只使用标准库，不需要安装依赖：
    python tools/build_notebooks.py

产物：
    courses/01-ai-app/01-数据清洗.ipynb
    courses/01-ai-app/02-特征工程.ipynb
    courses/01-ai-app/03-模型训练与MLflow.ipynb
    courses/01-ai-app/04-部署发布.ipynb
"""

import json
import os
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "courses", "01-ai-app")

META = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.11"},
}


def md(text):
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code(text):
    return {
        "cell_type": "code",
        "id": uuid.uuid4().hex[:8],
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def write(name, cells):
    nb = {
        "cells": cells,
        "metadata": META,
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"已生成: {path}")


def nb_clean():
    return [
        md(
            "# 01 数据清洗\n\n"
            "**目标**：把一份「能打开但跑不了模型」的脏数据，整理成可用于训练的数据。\n\n"
            "**数据集**：模拟的电信客户流失数据，1500 条左右，包含四类常见问题：\n"
            "1. 数值列里混入空字符串和 `N/A`\n"
            "2. 年龄出现 999、月费出现负数\n"
            "3. 同一客户重复出现\n"
            "4. 特征缺失"
        ),
        code(
            "import pandas as pd\n"
            "import numpy as np\n\n"
            "pd.set_option('display.max_columns', 20)\n"
            "df = pd.read_csv('../../data/raw/customer_churn.csv', encoding='utf-8-sig')\n"
            "print(df.shape)\n"
            "df.head()"
        ),
        md("## 1. 先看清问题：类型与缺失"),
        code("df.info()"),
        code("df.isna().sum().sort_values(ascending=False).head(10)"),
        md(
            "## 2. 类型问题：`N/A` 让数值列变成了 object\n\n"
            "`errors='coerce'` 会把无法转换的值变成 NaN，而不是直接报错。"
        ),
        code(
            "for col in ['age', 'monthly_charge', 'total_charge']:\n"
            "    df[col] = pd.to_numeric(df[col], errors='coerce')\n\n"
            "df[['age', 'monthly_charge', 'total_charge']].dtypes"
        ),
        md("## 3. 异常值：业务规则比统计规则更可靠"),
        code(
            "print('年龄 > 100:', (df['age'] > 100).sum())\n"
            "print('月费 < 0  :', (df['monthly_charge'] < 0).sum())\n\n"
            "df.loc[df['age'] > 100, 'age'] = np.nan\n"
            "df.loc[df['monthly_charge'] < 0, 'monthly_charge'] = np.nan\n"
            "df.loc[df['total_charge'] < 0, 'total_charge'] = np.nan\n"
            "print('已把异常值置为缺失，交给后续填充策略处理')"
        ),
        md("## 4. 重复行：按业务主键去重"),
        code(
            "before = len(df)\n"
            "df = df.drop_duplicates(subset=['customer_id'])\n"
            "print(f'删除重复 {before - len(df)} 行，剩余 {len(df)} 行')"
        ),
        md("## 5. 清洗前后对比"),
        code(
            "print('缺失值统计:')\n"
            "print(df[['age', 'monthly_charge', 'total_charge']].isna().sum())\n"
            "print()\n"
            "print('流失比例:', f\"{df['churn'].mean():.2%}\")"
        ),
        md(
            "## 小结\n\n"
            "- 清洗的核心不是「用哪个函数」，而是**先定义业务上什么叫不合理**\n"
            "- 异常值处理有两种策略：置为缺失后填充，或直接剔除。本例选前者，避免丢失样本\n"
            "- 下一步：把清洗逻辑固化成脚本 `src/data_pipeline.py`，让流程可复现"
        ),
    ]


def nb_feature():
    return [
        md(
            "# 02 特征工程\n\n"
            "**目标**：构造更有信息量的特征，并**把预处理固化成一个对象**。\n\n"
            "关键点：训练时用的标准化参数，推理时必须一模一样。\n"
            "如果训练用 `StandardScaler().fit_transform(X)`，推理时又新建一个 scaler，\n"
            "两边的均值方差不同，模型会静默地给出错误结果。**这就是要固化 Pipeline 的原因。**"
        ),
        code(
            "import joblib\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.compose import ColumnTransformer\n"
            "from sklearn.impute import SimpleImputer\n"
            "from sklearn.pipeline import Pipeline\n"
            "from sklearn.preprocessing import OneHotEncoder, StandardScaler\n\n"
            "df = pd.read_csv('../../data/raw/customer_churn.csv', encoding='utf-8-sig')\n"
            "for col in ['age', 'monthly_charge', 'total_charge']:\n"
            "    df[col] = pd.to_numeric(df[col], errors='coerce')\n"
            "df = df.drop_duplicates(subset=['customer_id'])\n"
            "df.loc[df['age'] > 100, 'age'] = np.nan\n"
            "df.loc[df['monthly_charge'] < 0, 'monthly_charge'] = np.nan\n"
            "print(df.shape)"
        ),
        md("## 1. 衍生特征：把「绝对值」变成「比率」\n\n月费 100 元对老客户和新客户的含义完全不同，用比率更能体现差异。"),
        code(
            "df['avg_monthly'] = df['total_charge'] / df['tenure_months'].replace(0, np.nan)\n"
            "df['support_per_year'] = df['support_calls'] / (df['tenure_months'] / 12).replace(0, np.nan)\n"
            "df['avg_monthly'] = df['avg_monthly'].fillna(df['monthly_charge'])\n"
            "df['support_per_year'] = df['support_per_year'].fillna(0)\n\n"
            "df[['tenure_months', 'total_charge', 'avg_monthly', 'support_per_year']].head()"
        ),
        md("## 2. 构建预处理器\n\n数值列：中位数填充 → 标准化；类别列：众数填充 → One-Hot。"),
        code(
            "NUM_COLS = ['age', 'tenure_months', 'monthly_charge', 'total_charge',\n"
            "            'support_calls', 'is_active', 'avg_monthly', 'support_per_year']\n"
            "CAT_COLS = ['contract_type', 'payment_method']\n\n"
            "numeric = Pipeline([\n"
            "    ('imputer', SimpleImputer(strategy='median')),\n"
            "    ('scaler', StandardScaler()),\n"
            "])\n"
            "categorical = Pipeline([\n"
            "    ('imputer', SimpleImputer(strategy='most_frequent')),\n"
            "    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),\n"
            "])\n\n"
            "prep = ColumnTransformer([\n"
            "    ('num', numeric, NUM_COLS),\n"
            "    ('cat', categorical, CAT_COLS),\n"
            "])\n"
            "prep"
        ),
        md("## 3. 固化并保存"),
        code(
            "import os\n"
            "os.makedirs('../../models', exist_ok=True)\n\n"
            "X = prep.fit_transform(df[NUM_COLS + CAT_COLS])\n"
            "print('转换后形状:', X.shape)\n\n"
            "joblib.dump(prep, '../../models/preprocessor.pkl')\n"
            "print('预处理器已保存至 models/preprocessor.pkl')"
        ),
        md(
            "## 小结\n\n"
            "- 特征工程的价值在于**引入业务先验**，比如「支持呼叫频率」比「呼叫总次数」更能反映客户情绪\n"
            "- `ColumnTransformer` 把填充、缩放、编码打包成一个对象，训练和推理共用，杜绝数据泄漏和线上不一致\n"
            "- 下一步：训练模型并在 MLflow 中记录每次实验"
        ),
    ]


def nb_train():
    return [
        md(
            "# 03 模型训练与 MLflow 实验记录\n\n"
            "**目标**：训练三个候选模型，把参数、指标、混淆矩阵全部记录到 MLflow，方便横向对比。\n\n"
            "注意数据特点：流失样本只占约 17%，**准确率会骗人**——全预测「不流失」也有 83% 准确率。\n"
            "所以用 `class_weight='balanced'` 并对齐关注 F1 与召回率。"
        ),
        code(
            "import joblib\n"
            "import pandas as pd\n"
            "from sklearn.model_selection import train_test_split\n\n"
            "df = pd.read_parquet('../../data/processed/clean.parquet')\n"
            "prep = joblib.load('../../models/preprocessor.pkl')\n\n"
            "NUM_COLS = ['age', 'tenure_months', 'monthly_charge', 'total_charge',\n"
            "            'support_calls', 'is_active', 'avg_monthly', 'support_per_year']\n"
            "CAT_COLS = ['contract_type', 'payment_method']\n\n"
            "X = prep.transform(df[NUM_COLS + CAT_COLS])\n"
            "y = df['churn'].values\n\n"
            "X_train, X_test, y_train, y_test = train_test_split(\n"
            "    X, y, test_size=0.2, random_state=42, stratify=y)\n"
            "print(f'训练 {X_train.shape[0]} 条 / 测试 {X_test.shape[0]} 条')"
        ),
        md("## 1. 基线：一个不懂业务的模型\n\n先看看「全猜不流失」能拿多少准确率。"),
        code(
            "from sklearn.metrics import accuracy_score, f1_score\n\n"
            "naive = (y_test * 0 + 0)\n"
            "print(f'全猜不流失: accuracy={accuracy_score(y_test, naive):.4f}  f1={f1_score(y_test, naive, zero_division=0):.4f}')"
        ),
        md("## 2. 接入 MLflow"),
        code(
            "import mlflow\n\n"
            "mlflow.set_tracking_uri('sqlite:///../../mlflow.db')\n"
            "mlflow.set_experiment('churn-prediction')\n"
            "print('当前实验:', mlflow.get_experiment_by_name('churn-prediction').name)"
        ),
        md("## 3. 训练三个候选模型"),
        code(
            "from sklearn.ensemble import RandomForestClassifier\n"
            "from sklearn.linear_model import LogisticRegression\n"
            "from sklearn.metrics import (ConfusionMatrixDisplay, precision_score,\n"
            "                             recall_score, roc_auc_score)\n"
            "import matplotlib.pyplot as plt\n\n"
            "candidates = [\n"
            "    ('LogReg-C0.1', LogisticRegression(C=0.1, max_iter=1000, class_weight='balanced'),\n"
            "     {'model': 'LogisticRegression', 'C': 0.1}),\n"
            "    ('LogReg-C1.0', LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced'),\n"
            "     {'model': 'LogisticRegression', 'C': 1.0}),\n"
            "    ('RandomForest-200', RandomForestClassifier(n_estimators=200, max_depth=8,\n"
            "                                                class_weight='balanced', random_state=42),\n"
            "     {'model': 'RandomForest', 'n_estimators': 200, 'max_depth': 8}),\n"
            "]\n\n"
            "results = []\n"
            "for name, model, params in candidates:\n"
            "    with mlflow.start_run(run_name=name):\n"
            "        model.fit(X_train, y_train)\n"
            "        pred = model.predict(X_test)\n"
            "        proba = model.predict_proba(X_test)[:, 1]\n"
            "        m = {\n"
            "            'accuracy': accuracy_score(y_test, pred),\n"
            "            'precision': precision_score(y_test, pred, zero_division=0),\n"
            "            'recall': recall_score(y_test, pred, zero_division=0),\n"
            "            'f1': f1_score(y_test, pred, zero_division=0),\n"
            "            'roc_auc': roc_auc_score(y_test, proba),\n"
            "        }\n"
            "        mlflow.log_params(params)\n"
            "        mlflow.log_metrics(m)\n"
            "        fig, ax = plt.subplots(figsize=(4, 3.2))\n"
            "        ConfusionMatrixDisplay.from_predictions(y_test, pred, ax=ax, colorbar=False, cmap='Blues')\n"
            "        ax.set_title(name)\n"
            "        mlflow.log_figure(fig, 'confusion_matrix.png')\n"
            "        plt.close(fig)\n"
            "        results.append({'模型': name, **{k: round(v, 4) for k, v in m.items()}})\n\n"
            "pd.DataFrame(results).sort_values('f1', ascending=False)"
        ),
        md(
            "## 4. 去 MLflow UI 看对比\n\n"
            "终端执行：\n```bash\nmlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5001\n```\n"
            "打开 http://localhost:5001 ，能直接对比三组实验的参数与指标，点进单个 run 还能看到混淆矩阵图。"
        ),
        md(
            "## 小结\n\n"
            "- 不平衡数据先算基线，否则「83% 准确率」会让人误以为模型很好\n"
            "- F1 与召回率是这类场景的核心指标：漏掉一个流失客户的成本远高于误报\n"
            "- MLflow 的价值是**把每次尝试都留下证据**，而不是凭感觉说「调参后效果更好了」"
        ),
    ]


def nb_deploy():
    return [
        md(
            "# 04 部署发布\n\n"
            "**目标**：把训练好的模型变成一个能被外部调用的服务。\n\n"
            "两种发布形态：\n"
            "1. **REST API**（FastAPI）—— 供其他系统调用\n"
            "2. **交互页面**（Streamlit）—— 供业务人员直接使用"
        ),
        code(
            "import json\n"
            "import joblib\n"
            "import pandas as pd\n\n"
            "prep = joblib.load('../../models/preprocessor.pkl')\n"
            "model = joblib.load('../../models/model.pkl')\n"
            "print('预处理器:', type(prep).__name__)\n"
            "print('模型    :', type(model).__name__)\n"
            "print(json.dumps(json.load(open('../../models/metrics.json', encoding='utf-8')),\n"
            "                 ensure_ascii=False, indent=2))"
        ),
        md("## 1. 本地推理：先确认模型能对单条样本给出合理结果"),
        code(
            "row = {\n"
            "    'age': 29, 'tenure_months': 3, 'monthly_charge': 130.0, 'total_charge': 390.0,\n"
            "    'contract_type': '按月付费', 'payment_method': '电子支票',\n"
            "    'support_calls': 9, 'is_active': 0,\n"
            "}\n"
            "row['avg_monthly'] = row['total_charge'] / row['tenure_months']\n"
            "row['support_per_year'] = row['support_calls'] / (row['tenure_months'] / 12)\n\n"
            "NUM_COLS = ['age', 'tenure_months', 'monthly_charge', 'total_charge',\n"
            "            'support_calls', 'is_active', 'avg_monthly', 'support_per_year']\n"
            "CAT_COLS = ['contract_type', 'payment_method']\n\n"
            "X = prep.transform(pd.DataFrame([row])[NUM_COLS + CAT_COLS])\n"
            "print(f'流失概率: {model.predict_proba(X)[0, 1]:.2%}')"
        ),
        md(
            "## 2. 启动 REST 服务\n\n"
            "在终端（不是 notebook）执行：\n```bash\nuvicorn src.serve:app --host 0.0.0.0 --port 8000\n```\n"
            "然后打开 http://localhost:8000/docs ，可以直接在页面上调试接口。"
        ),
        code(
            "import requests\n\n"
            "payload = {\n"
            "    'age': 29, 'tenure_months': 3, 'monthly_charge': 130.0, 'total_charge': 390.0,\n"
            "    'contract_type': '按月付费', 'payment_method': '电子支票',\n"
            "    'support_calls': 9, 'is_active': 0,\n"
            "}\n"
            "try:\n"
            "    r = requests.post('http://localhost:8000/predict', json=payload, timeout=5)\n"
            "    print(r.status_code, r.json())\n"
            "except requests.exceptions.ConnectionError:\n"
            "    print('服务未启动，请先在终端执行 uvicorn src.serve:app --port 8000')"
        ),
        md(
            "## 3. 启动交互页面\n\n"
            "```bash\nstreamlit run apps/streamlit_app.py --server.address 0.0.0.0 --server.port 8501\n```\n"
            "打开 http://localhost:8501 ，拖动滑块即可看到概率实时变化。"
        ),
        md(
            "## 小结\n\n"
            "- 部署的本质是「让别人不用懂模型也能用模型」\n"
            "- REST API 适合系统集成，交互页面适合业务演示，两者共用同一份 `model.pkl`\n"
            "- 到这一步，一条从原始数据到线上服务的链路就闭环了"
        ),
    ]


def main():
    write("01-数据清洗.ipynb", nb_clean())
    write("02-特征工程.ipynb", nb_feature())
    write("03-模型训练与MLflow.ipynb", nb_train())
    write("04-部署发布.ipynb", nb_deploy())


if __name__ == "__main__":
    main()
