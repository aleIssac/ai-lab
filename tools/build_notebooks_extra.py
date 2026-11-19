"""生成需求④的另外两个专项 notebook：大数据应用开发、大模型应用开发。

只使用标准库：
    python tools/build_notebooks_extra.py

产物：
    courses/02-bigdata/01-Spark数据清洗.ipynb
    courses/02-bigdata/02-SparkML训练.ipynb
    courses/03-llm-app/01-文档切块与向量化.ipynb
    courses/03-llm-app/02-RAG问答链路.ipynb
    courses/03-llm-app/03-Streamlit发布.ipynb
"""

import json
import os
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "courses")

META = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
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


def write(subdir, name, cells):
    out = os.path.join(BASE, subdir)
    os.makedirs(out, exist_ok=True)
    nb = {"cells": cells, "metadata": META, "nbformat": 4, "nbformat_minor": 5}
    path = os.path.join(out, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"已生成: {path}")


# ---------------------------------------------------------------- 大数据专项

def nb_spark_clean():
    return [
        md(
            "# 01 Spark 数据清洗\n\n"
            "**目标**：用 Spark DataFrame API 处理同一份客户流失数据。\n\n"
            "和 pandas 版本相比，写法几乎一样，区别在于两点：\n"
            "1. 数据是**分布式**的，操作会被翻译成执行计划，延迟到 action 才真正计算\n"
            "2. 有 **Web UI**（默认 4040 端口），能看到 DAG、Stage、Shuffle 读写量\n\n"
            "第二点是「大数据」与「单机」最直观的区别——验收演示时务必打开看一眼。"
        ),
        code(
            "from pyspark.sql import SparkSession\n"
            "from pyspark.sql import functions as F\n"
            "from pyspark.sql.types import IntegerType, DoubleType\n\n"
            "spark = (SparkSession.builder\n"
            "         .appName('churn-clean')\n"
            "         .master('local[*]')\n"
            "         .config('spark.sql.shuffle.partitions', '8')\n"
            "         .getOrCreate())\n"
            "spark.sparkContext.setLogLevel('ERROR')\n"
            "print('Spark 版本:', spark.version)\n"
            "print('Spark UI :', spark.sparkContext.uiWebUrl)"
        ),
        md("## 1. 读取原始数据\n\n注意 CSV 带 BOM，第一列名会多一个不可见字符，需要清掉。"),
        code(
            "df = (spark.read\n"
            "      .option('header', True)\n"
            "      .option('inferSchema', True)\n"
            "      .option('encoding', 'UTF-8')\n"
            "      .csv('../../data/raw/customer_churn.csv'))\n\n"
            "df = df.toDF(*[c.replace('\\ufeff', '').strip() for c in df.columns])\n"
            "df.printSchema()"
        ),
        code(
            "print('原始行数:', df.count())\n"
            "df.select('customer_id', 'age', 'monthly_charge', 'total_charge', 'churn').show(5)"
        ),
        md(
            "## 2. 清洗\n\n"
            "Spark 里 `cast` 遇到无法转换的值会返回 null，效果等价于 pandas 的 `errors='coerce'`。\n"
            "所以类型转换本身就是一步缺失值清洗。"
        ),
        code(
            "df2 = (df\n"
            "       .withColumn('age', F.col('age').cast(DoubleType()))\n"
            "       .withColumn('monthly_charge', F.col('monthly_charge').cast(DoubleType()))\n"
            "       .withColumn('total_charge', F.col('total_charge').cast(DoubleType()))\n"
            "       .withColumn('tenure_months', F.col('tenure_months').cast(DoubleType()))\n"
            "       .withColumn('support_calls', F.col('support_calls').cast(DoubleType()))\n"
            "       .withColumn('is_active', F.col('is_active').cast(DoubleType()))\n"
            "       .withColumn('churn', F.col('churn').cast(IntegerType())))\n\n"
            "df2.select([F.count(F.when(F.col(c).isNull(), c)).alias(c)\n"
            "            for c in ['age', 'monthly_charge', 'total_charge']]).show()"
        ),
        md("## 3. 异常值过滤与去重\n\nSpark 是惰性求值，这里只是构建执行计划，直到 `count()` 才真正跑。"),
        code(
            "df3 = (df2\n"
            "       .filter((F.col('age').isNull()) | (F.col('age') <= 100))\n"
            "       .filter((F.col('monthly_charge').isNull()) | (F.col('monthly_charge') >= 0))\n"
            "       .filter((F.col('churn').isNotNull()))\n"
            "       .dropDuplicates(['customer_id']))\n\n"
            "print('清洗后行数:', df3.count())\n"
            "print('流失比例:', df3.select(F.avg('churn')).first()[0])"
        ),
        md("## 4. 衍生特征"),
        code(
            "df4 = (df3\n"
            "       .withColumn('avg_monthly',\n"
            "                   F.when(F.col('tenure_months') > 0,\n"
            "                          F.col('total_charge') / F.col('tenure_months'))\n"
            "                    .otherwise(F.col('monthly_charge')))\n"
            "       .withColumn('support_per_year',\n"
            "                   F.col('support_calls') /\n"
            "                   F.greatest(F.col('tenure_months') / 12, F.lit(1))))\n\n"
            "df4.select('customer_id', 'tenure_months', 'total_charge',\n"
            "           'avg_monthly', 'support_per_year').show(5)"
        ),
        md(
            "## 5. 写出 Parquet\n\n"
            "> Windows 下 PySpark 写文件需要 Hadoop 的 `winutils.exe`，容器（Linux）里不需要。\n"
            "> 如果在 Windows 本地跑报 `HADOOP_HOME` 相关错误，直接在容器里跑这一格。"
        ),
        code(
            "import os\n"
            "out = '../../data/processed/spark_clean.parquet'\n"
            "os.makedirs('../../data/processed', exist_ok=True)\n\n"
            "try:\n"
            "    (df4.repartition(4)\n"
            "        .write.mode('overwrite')\n"
            "        .parquet(out))\n"
            "    print('已写入:', out)\n"
            "except Exception as e:\n"
            "    print('写入失败（Windows 常见，缺 winutils）:', type(e).__name__)\n"
            "    print('容器内运行即可正常写出')"
        ),
        md(
            "## 小结\n\n"
            "- Spark 的 API 和 pandas 很像，但**执行是惰性的**：`filter`/`withColumn` 只建计划，`count`/`show`/`write` 才触发计算\n"
            "- 打开 `http://localhost:4040` 能看到 DAG 图、Stage 划分、Shuffle 读写量——这是大数据作业的「体检报告」\n"
            "- 下一步：用 Spark MLlib 训练，走完整的 Pipeline"
        ),
    ]


def nb_spark_ml():
    return [
        md(
            "# 02 Spark MLlib 训练\n\n"
            "**目标**：用 Spark ML 的 Pipeline 完成特征编码与模型训练。\n\n"
            "和 sklearn 的核心差异：\n"
            "- Spark 要求所有特征先拼成一个 **Vector 列**（`VectorAssembler`）\n"
            "- 类别特征用 `StringIndexer` 转索引，再 `OneHotEncoder` 编码\n"
            "- 整个流程也是一个 Pipeline，可以整体保存和加载"
        ),
        code(
            "from pyspark.sql import SparkSession\n"
            "from pyspark.ml import Pipeline\n"
            "from pyspark.ml.feature import (StringIndexer, OneHotEncoder,\n"
            "                                VectorAssembler, StandardScaler)\n"
            "from pyspark.ml.classification import LogisticRegression, RandomForestClassifier\n"
            "from pyspark.ml.evaluation import BinaryClassificationEvaluator\n\n"
            "spark = (SparkSession.builder\n"
            "         .appName('churn-mllib')\n"
            "         .master('local[*]')\n"
            "         .config('spark.sql.shuffle.partitions', '8')\n"
            "         .getOrCreate())\n"
            "spark.sparkContext.setLogLevel('ERROR')\n"
            "print('Spark', spark.version)"
        ),
        md("## 1. 载入清洗后的数据"),
        code(
            "import os\n"
            "path = '../../data/processed/spark_clean.parquet'\n"
            "if os.path.exists(path):\n"
            "    data = spark.read.parquet(path)\n"
            "else:\n"
            "    # 上一步没写成功时，退回从 CSV 快速重建\n"
            "    from pyspark.sql import functions as F\n"
            "    data = spark.read.option('header', True).option('inferSchema', True) \\\n"
            "        .csv('../../data/raw/customer_churn.csv')\n"
            "    data = data.toDF(*[c.replace('\\ufeff','').strip() for c in data.columns])\n"
            "    data = data.dropDuplicates(['customer_id']).dropna(subset=['churn'])\n"
            "    data = data.withColumn('avg_monthly', F.col('monthly_charge')) \\\n"
            "               .withColumn('support_per_year', F.col('support_calls'))\n\n"
            "print('样本数:', data.count())\n"
            "data.select('customer_id', 'contract_type', 'payment_method', 'churn').show(5)"
        ),
        md("## 2. 构建特征处理阶段"),
        code(
            "num_cols = ['age', 'tenure_months', 'monthly_charge', 'total_charge',\n"
            "            'support_calls', 'is_active', 'avg_monthly', 'support_per_year']\n"
            "cat_cols = ['contract_type', 'payment_method']\n\n"
            "stages = []\n"
            "for c in num_cols:\n"
            "    data = data.withColumn(c, data[c].cast('double'))\n"
            "    data = data.fillna({c: 0.0})\n\n"
            "for c in cat_cols:\n"
            "    data = data.fillna({c: 'unknown'})\n"
            "    idx = StringIndexer(inputCol=c, outputCol=c + '_idx', handleInvalid='keep')\n"
            "    enc = OneHotEncoder(inputCol=c + '_idx', outputCol=c + '_vec')\n"
            "    stages += [idx, enc]\n\n"
            "assembler = VectorAssembler(\n"
            "    inputCols=num_cols + [c + '_vec' for c in cat_cols],\n"
            "    outputCol='features')\n"
            "scaler = StandardScaler(inputCol='features', outputCol='scaled',\n"
            "                        withMean=True, withStd=True)\n"
            "stages += [assembler, scaler]\n"
            "print(f'特征阶段: {len(stages)} 个')"
        ),
        md("## 3. 划分数据集并训练两个模型"),
        code(
            "train, test = data.randomSplit([0.8, 0.2], seed=42)\n"
            "print(f'训练 {train.count()} / 测试 {test.count()}')\n\n"
            "evaluator = BinaryClassificationEvaluator(labelCol='churn', metricName='areaUnderROC')\n"
            "results = {}\n\n"
            "for name, clf in [\n"
            "    ('LogisticRegression', LogisticRegression(featuresCol='scaled', labelCol='churn', maxIter=50)),\n"
            "    ('RandomForest', RandomForestClassifier(featuresCol='scaled', labelCol='churn',\n"
            "                                            numTrees=50, maxDepth=6, seed=42)),\n"
            "]:\n"
            "    pipe = Pipeline(stages=stages + [clf])\n"
            "    model = pipe.fit(train)\n"
            "    pred = model.transform(test)\n"
            "    auc = evaluator.evaluate(pred)\n"
            "    acc = pred.filter(pred.churn == pred.prediction).count() / pred.count()\n"
            "    results[name] = {'AUC': round(auc, 4), 'Accuracy': round(acc, 4)}\n"
            "    print(f'{name:20s} AUC={auc:.4f}  Acc={acc:.4f}')"
        ),
        md("## 4. 保存 Pipeline\n\n整个 Pipeline 一起保存，推理时不用再手动拼特征。"),
        code(
            "import json\n"
            "best_name = max(results, key=lambda k: results[k]['AUC'])\n"
            "print('最优模型:', best_name, results[best_name])\n\n"
            "os.makedirs('../../models', exist_ok=True)\n"
            "try:\n"
            "    pipe_model.write().overwrite().save('../../models/spark_pipeline')\n"
            "    print('Pipeline 已保存: models/spark_pipeline')\n"
            "except Exception as e:\n"
            "    print('保存失败（Windows 缺 winutils）:', type(e).__name__)\n\n"
            "with open('../../models/spark_metrics.json', 'w', encoding='utf-8') as f:\n"
            "    json.dump(results, f, ensure_ascii=False, indent=2)\n"
            "print(json.dumps(results, ensure_ascii=False, indent=2))"
        ),
        md(
            "## 小结\n\n"
            "- Spark ML 的 Pipeline 和 sklearn 的思路一致：把编码、缩放、模型串成一条链，整体 fit、整体 save\n"
            "- 区别在于数据始终是分布式的 DataFrame，`features` 必须是一列 Vector\n"
            "- `http://localhost:4040` 里能看到训练过程的 Stage 划分和 Shuffle 量"
        ),
    ]


# ------------------------------------------------------------ 大模型应用专项

def nb_chunk_vector():
    return [
        md(
            "# 01 文档切块与向量化\n\n"
            "**目标**：把非结构化文档变成可检索的向量。这是 RAG 的第一步，也是决定效果上限的一步。\n\n"
            "三个关键决策：\n"
            "1. **切多大**——太小丢上下文，太大检索不准。本课按小节切，保证语义完整\n"
            "2. **怎么向量化**——本例用 TF-IDF 字符 n-gram，不依赖任何嵌入模型，断网可跑\n"
            "3. **怎么算相似**——L2 归一化后点积即余弦相似度"
        ),
        code(
            "import sys, os\n"
            "sys.path.insert(0, '../..')\n\n"
            "from src.rag_core import load_documents, chunk_documents\n\n"
            "docs = load_documents('../../data/kb')\n"
            "print(f'载入 {len(docs)} 篇文档')\n"
            "for d in docs:\n"
            "    print(f\"  {d['source']:24s} {len(d['text']):5d} 字\")"
        ),
        md("## 1. 切块\n\n按二级标题切，标题保留在块内，这样检索时能带上上下文。"),
        code(
            "chunks = chunk_documents(docs)\n"
            "print(f'切成 {len(chunks)} 个片段\\n')\n"
            "for c in chunks[:5]:\n"
            "    print(f\"[{c['source']}] {c['title']}  ({len(c['text'])} 字)\")"
        ),
        md(
            "## 2. 向量化\n\n"
            "中文没有空格，`TfidfVectorizer` 默认的按词切分会失效（整句被当成一个词）。\n"
            "改用 `analyzer='char_wb'` 走字符 n-gram，这是中文场景最简单有效的办法。"
        ),
        code(
            "from sklearn.feature_extraction.text import TfidfVectorizer\n"
            "from sklearn.preprocessing import normalize\n\n"
            "texts = [c['text'] for c in chunks]\n"
            "vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 3),\n"
            "                      max_features=20000, sublinear_tf=True)\n"
            "matrix = normalize(vec.fit_transform(texts))\n\n"
            "print('向量矩阵形状:', matrix.shape)\n"
            "print('每个片段是一个', matrix.shape[1], '维向量')"
        ),
        md("## 3. 检索\n\n归一化之后，两个向量的点积就是余弦相似度。"),
        code(
            "import numpy as np\n\n"
            "def search(query, k=3):\n"
            "    q = normalize(vec.transform([query]))\n"
            "    scores = np.asarray((matrix @ q.T).todense()).ravel()\n"
            "    for i in np.argsort(-scores)[:k]:\n"
            "        print(f\"  {scores[i]:.3f}  {chunks[i]['source']} · {chunks[i]['title']}\")\n\n"
            "for q in ['矩阵维度不匹配怎么排查', '怎么防止过拟合', '上线后怎么回滚']:\n"
            "    print(f'问题：{q}')\n"
            "    search(q)\n"
            "    print()"
        ),
        md(
            "## 小结\n\n"
            "- 切块策略直接决定检索质量：切碎了丢上下文，切大了噪声多\n"
            "- TF-IDF 是「词面匹配」，好处是完全离线、可解释；缺点是同义词检索不到\n"
            "- 生产环境换成 `bge-m3`、`text-embedding-3` 这类语义嵌入，**检索接口不变**，只是把 `vec.transform` 换成调嵌入 API\n"
            "- 下一步：把检索结果拼进 prompt，交给大模型生成答案"
        ),
    ]


def nb_rag():
    return [
        md(
            "# 02 RAG 问答链路\n\n"
            "**目标**：检索 → 拼 prompt → 生成。\n\n"
            "RAG 的价值不在「用了大模型」，而在**答案有出处、可追溯**。\n"
            "所以 prompt 里必须强制模型只依据资料回答，并列出引用。"
        ),
        code(
            "import sys, os\n"
            "sys.path.insert(0, '../..')\n"
            "from src.rag_core import KnowledgeBase, build_prompt, call_llm\n\n"
            "kb = KnowledgeBase('../../data/kb').build()\n"
            "print(kb.stats())"
        ),
        md("## 1. 检索"),
        code(
            "question = '训练时 loss 突然变成 NaN，可能是什么原因？'\n"
            "hits = kb.search(question, k=3)\n\n"
            "for i, h in enumerate(hits, 1):\n"
            "    print(f\"[{i}] {h['score']:.3f}  {h['source']} · {h['title']}\")"
        ),
        md(
            "## 2. 拼装 prompt\n\n"
            "注意三条约束：只依据资料、不知道就说不知道、必须列出处。\n"
            "**不加这三条，模型就会开始编。**"
        ),
        code(
            "prompt = build_prompt(question, hits)\n"
            "print(prompt[:1200])"
        ),
        md(
            "## 3. 调用大模型\n\n"
            "下面这段需要 API Key。没有 Key 也不影响理解——\n"
            "**上面那个 prompt 就是 RAG 的全部输入**，模型只是最后一环。"
        ),
        code(
            "API_KEY = os.environ.get('RAG_API_KEY', '')\n"
            "BASE_URL = 'https://api.deepseek.com/v1'\n"
            "MODEL = 'deepseek-chat'\n\n"
            "if API_KEY:\n"
            "    answer = call_llm(prompt, API_KEY, base_url=BASE_URL, model=MODEL)\n"
            "    print(answer)\n"
            "else:\n"
            "    print('未设置 RAG_API_KEY 环境变量，跳过生成')\n"
            "    print('设置方法（PowerShell）：$env:RAG_API_KEY=\"sk-xxx\"')"
        ),
        md(
            "## 4. 对比：不给资料的模型会怎么答\n\n"
            "同一句话直接问，模型会凭记忆给一个泛泛的答案；\n"
            "RAG 之后，答案里会带上具体文档的说法和出处。**这是可验证性的差别。**"
        ),
        code(
            "if API_KEY:\n"
            "    raw = call_llm(question, API_KEY, base_url=BASE_URL, model=MODEL)\n"
            "    print('=== 无资料直接问 ===')\n"
            "    print(raw[:400])\n"
            "    print()\n"
            "    print('=== 给了资料的 RAG ===')\n"
            "    print(answer[:400])\n"
            "else:\n"
            "    print('需要 API Key 才能做这个对比')"
        ),
        md(
            "## 小结\n\n"
            "- RAG = 检索 + 拼装 + 生成，前两步做得不好，换再强的模型也救不回来\n"
            "- 强制引用出处，是 RAG 相对于纯对话最实际的工程价值\n"
            "- 下一步：把这个链路包成页面"
        ),
    ]


def nb_llm_deploy():
    return [
        md(
            "# 03 发布成页面\n\n"
            "**目标**：把 RAG 链路包成业务人员能直接用的页面。\n\n"
            "`apps/rag_app.py` 已经写好，这里只演示怎么起、怎么验。"
        ),
        md(
            "## 1. 启动\n\n"
            "在**终端**（不是 notebook）执行：\n\n"
            "```bash\n"
            "streamlit run apps/rag_app.py --server.address 0.0.0.0 --server.port 8502\n"
            "```\n\n"
            "然后打开 http://localhost:8502 。\n\n"
            "> 注意 `--server.address 0.0.0.0`：默认只监听 localhost，容器外访问不到。"
        ),
        md(
            "## 2. 页面能做什么\n\n"
            "| 区域 | 功能 |\n"
            "|---|---|\n"
            "| 侧边栏 | 填 API Key、选模型、调检索片段数 |\n"
            "| 主区 | 提问 → 答案 + 引用来源 |\n"
            "| 右侧 | 展开每个检索片段看原文和相似度 |\n\n"
            "**没填 Key 也能演示**：页面会展示「检索到了什么」和「拼好的 prompt」，\n"
            "这反而更适合讲清楚 RAG 的结构。"
        ),
        md("## 3. 健康检查"),
        code(
            "import requests\n\n"
            "try:\n"
            "    r = requests.get('http://localhost:8502/_stcore/health', timeout=5)\n"
            "    print('Streamlit 状态:', r.status_code, r.text[:50])\n"
            "except Exception as e:\n"
            "    print('服务未启动:', type(e).__name__)\n"
            "    print('先在终端执行 streamlit run apps/rag_app.py --server.port 8502')"
        ),
        md(
            "## 小结\n\n"
            "- 部署的本质是让不懂模型的人也能用模型，所以交互设计比模型参数重要\n"
            "- 这一条链路（文档 → 切块 → 向量化 → 检索 → 生成 → 页面）就是大模型应用的标准形态\n"
            "- 到这里，需求④的三个专项（AI 应用 / 大数据 / 大模型）全部闭环"
        ),
    ]


def main():
    write("02-bigdata", "01-Spark数据清洗.ipynb", nb_spark_clean())
    write("02-bigdata", "02-SparkML训练.ipynb", nb_spark_ml())
    write("03-llm-app", "01-文档切块与向量化.ipynb", nb_chunk_vector())
    write("03-llm-app", "02-RAG问答链路.ipynb", nb_rag())
    write("03-llm-app", "03-Streamlit发布.ipynb", nb_llm_deploy())


if __name__ == "__main__":
    main()
