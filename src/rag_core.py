"""RAG（检索增强生成）核心逻辑。

设计取舍：
- 向量化用 TF-IDF + SVD 降维，**不下载任何嵌入模型**，保证内网可离线运行
- 向量检索用 numpy 余弦相似度，教学上能讲清每一步；生产环境可换 Chroma / Milvus
- 生成走 OpenAI 兼容的 HTTP 接口，不绑定具体厂商

用法：
    from src.rag_core import KnowledgeBase
    kb = KnowledgeBase("data/kb")
    kb.build()
    hits = kb.search("矩阵维度不匹配怎么办", k=3)
"""

import json
import os
import re

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


def load_documents(kb_dir):
    """读取目录下所有 markdown 文档。"""
    docs = []
    for name in sorted(os.listdir(kb_dir)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(kb_dir, name)
        with open(path, encoding="utf-8") as f:
            docs.append({"source": name, "text": f.read()})
    return docs


def split_sections(text):
    """按二级标题切分，保留标题作为上下文。"""
    parts = re.split(r"\n(?=## )", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_documents(docs, min_len=80):
    """把文档切成语义完整的小节作为检索单元。"""
    chunks = []
    for doc in docs:
        for i, section in enumerate(split_sections(doc["text"])):
            if len(section) < min_len:
                continue
            title = section.splitlines()[0].lstrip("# ").strip()
            chunks.append(
                {
                    "id": f"{doc['source']}#{i}",
                    "source": doc["source"],
                    "title": title,
                    "text": section,
                }
            )
    return chunks


class KnowledgeBase:
    """一个极简的向量检索库，行为对齐 Chroma 的常用接口。

    中文没有空格，TF-IDF 默认分词会失效，因此用字符 n-gram（2~3 字）。
    分块数量少时不做降维，直接在高维稀疏向量上算余弦，避免信息损失。
    """

    def __init__(self, kb_dir, n_components=None):
        self.kb_dir = kb_dir
        self.n_components = n_components
        self.chunks = []
        self.vectorizer = None
        self.svd = None
        self.matrix = None

    def build(self):
        docs = load_documents(self.kb_dir)
        self.chunks = chunk_documents(docs)

        texts = [c["text"] for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 3),
            max_features=20000,
            sublinear_tf=True,
        )
        matrix = self.vectorizer.fit_transform(texts)

        if self.n_components and len(texts) > self.n_components * 3:
            self.svd = TruncatedSVD(n_components=self.n_components, random_state=42)
            matrix = self.svd.fit_transform(matrix)
            matrix = normalize(matrix)
            self.matrix = np.asarray(matrix)
        else:
            self.matrix = normalize(matrix)

        return self

    def _embed_query(self, query):
        vec = self.vectorizer.transform([query])
        if self.svd is not None:
            vec = normalize(self.svd.transform(vec))
        else:
            vec = normalize(vec)
        return vec

    def search(self, query, k=3):
        if self.matrix is None:
            raise RuntimeError("请先调用 build()")
        q = self._embed_query(query)
        prod = self.matrix @ q.T
        if hasattr(prod, "toarray"):
            scores = prod.toarray().ravel()
        else:
            scores = np.asarray(prod).ravel()
        order = np.argsort(-scores)[:k]
        return [
            {
                "score": float(scores[i]),
                "source": self.chunks[i]["source"],
                "title": self.chunks[i]["title"],
                "text": self.chunks[i]["text"],
            }
            for i in order
        ]

    def stats(self):
        return {
            "documents": len({c["source"] for c in self.chunks}),
            "chunks": len(self.chunks),
            "dim": int(self.matrix.shape[1]) if self.matrix is not None else 0,
            "reduced": self.svd is not None,
        }


# 规则单独作为 system 消息下发：小参数量模型（如 1.5B）更容易分清"规则"和"资料"，
# 不会把规则末行的「依据：」当成唯一要输出的内容。
SYSTEM_RULES = (
    "你是 AI 实训平台的助教。请严格依据用户给出的资料回答问题：\n"
    "1. 只使用资料中的信息，资料里没有的内容不要补充，不要编造；\n"
    "2. 资料不足时也要先回答资料里已有的部分，不要只回一句结论；\n"
    "3. 先分条写排查步骤或做法，最后单独一行用「依据：」列出引用的来源文件名。"
)


def build_context(question, hits, max_chars=1800):
    """资料 + 问题（不含规则），作为 user 消息下发。"""
    context = "\n\n".join(
        f"[资料{i+1}] 来源：{h['source']} · {h['title']}\n{h['text']}"
        for i, h in enumerate(hits)
    )
    context = context[:max_chars]
    return f"{context}\n\n问题：{question}"


def build_prompt(question, hits, max_chars=1800):
    """完整可读的 prompt（规则 + 资料 + 问题），用于展示和 notebook 演示。"""
    return f"{SYSTEM_RULES}\n\n{build_context(question, hits, max_chars)}\n回答："


def call_llm(prompt, api_key, base_url="https://api.deepseek.com/v1",
             model="deepseek-chat", timeout=60, system=None):
    """调用 OpenAI 兼容接口。prompt 可为字符串，也可直接传 messages 列表。

    失败时抛出异常，由调用方处理。
    """
    import requests

    if isinstance(prompt, (list, tuple)):
        messages = list(prompt)
    else:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 800,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def answer(question, kb, api_key, **kwargs):
    """检索 + 生成。没有 API Key 时返回检索结果和待发送的 prompt，便于离线演示。

    调用失败（URL 写错、模型名不存在、超时、鉴权失败）不抛异常，
    改为返回 error 字段，由页面友好提示，避免 Streamlit 直接红屏。
    """
    hits = kb.search(question, k=kwargs.pop("k", 3))
    prompt = build_prompt(question, hits)
    base = {"hits": hits, "prompt": prompt, "error": None}

    if not api_key:
        return {
            **base,
            "answer": None,
            "note": "未提供 API Key，仅返回检索结果与拼装好的 prompt",
        }

    try:
        text = call_llm(build_context(question, hits), api_key, system=SYSTEM_RULES, **kwargs)

        # 小参数量模型（1.5B）偶尔会跳过正文、只吐一行「依据：xxx」（实测三次里有一次）。
        # 这种情况重试一次，取更长的结果；云端模型不会触发这条分支。
        if len(text.strip()) < 40:
            retry = call_llm(build_context(question, hits), api_key, system=SYSTEM_RULES, **kwargs)
            if len(retry.strip()) > len(text.strip()):
                text = retry
    except Exception as exc:  # noqa: BLE001 - 面向使用者，任何失败都要可读
        return {**base, "answer": None, "note": "err", "error": describe_error(exc, kwargs)}

    return {**base, "answer": text, "note": "ok"}


def describe_error(exc, kwargs):
    """把常见调用失败翻译成能照着改的中文提示。"""
    import requests

    base_url = str(kwargs.get("base_url", "")).rstrip("/")
    model = kwargs.get("model", "")
    raw = str(exc)

    if isinstance(exc, requests.exceptions.Timeout):
        return f"请求超时（{base_url}）。本地模型首次加载较慢，等半分钟再试；或把模型换成更小的。"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return (
            f"连不上 {base_url}。检查 Base URL 是否写对：本地模型应为 http://ollama:11434/v1 "
            "（不是 localhost，也不要漏掉 /v1）。"
        )

    resp = getattr(exc, "response", None)
    if resp is not None:
        code = resp.status_code
        body = ""
        try:
            body = resp.text[:200]
        except Exception:  # noqa: BLE001
            pass
        if code == 404:
            return (
                f"接口 404：{base_url} 下找不到 /chat/completions。"
                "本地模型请填 http://ollama:11434/v1；DeepSeek 填 https://api.deepseek.com/v1。"
            )
        if code in (401, 403):
            return f"鉴权失败（{code}）：Key 与 {base_url} 不匹配。本地模型 Key 可填任意非空值；云端要填真实 Key。"
        if code == 400 and "not found" in body.lower():
            return f"模型不存在：{model}。改名或用下拉框里列出的模型。"
        return f"接口返回 {code}：{body or raw}"

    return f"调用失败：{raw}"


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kb = KnowledgeBase(os.path.join(root, "data", "kb")).build()
    print(json.dumps(kb.stats(), ensure_ascii=False))

    for q in ["矩阵维度不匹配怎么排查", "怎么防止过拟合", "模型上线怎么回滚"]:
        print(f"\n问题：{q}")
        for h in kb.search(q, k=2):
            print(f"  {h['score']:.3f}  {h['source']} · {h['title']}")
