"""RAG 问答页面（Streamlit）。

用法：
    streamlit run apps/rag_app.py --server.address 0.0.0.0 --server.port 8502

没有 API Key 也能演示：会展示"检索到哪些片段"和"拼装好的 prompt"，
这正好能讲清楚 RAG 的两段结构（先检索，再生成）。
"""

import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.rag_core import KnowledgeBase, answer  # noqa: E402

st.set_page_config(page_title="AI 实训助教", page_icon="📚", layout="wide")


@st.cache_resource
def load_kb():
    return KnowledgeBase(os.path.join(ROOT, "data", "kb")).build()


kb = load_kb()
stats = kb.stats()

with st.sidebar:
    st.subheader("模型设置")
    use_llm = st.toggle("启用大模型回答", value=True)
    base_url = st.text_input("Base URL", value="http://ollama:11434/v1")
    model = st.selectbox(
        "模型",
        ["qwen2.5-coder:1.5b", "deepseek-chat", "deepseek-reasoner"],
        accept_new_options=True,
    )
    top_k = st.slider("检索片段数", 1, 6, 3)
    st.divider()
    st.caption(f"知识库：{stats['documents']} 篇文档 / {stats['chunks']} 个片段")
    st.caption(f"向量维度：{stats['dim']}")

# 关掉开关时不带 Key，answer() 只返回检索结果与拼装好的 prompt
api_key = os.environ.get("RAG_API_KEY", "ollama") if use_llm else ""

st.title("AI 实训助教")

examples = ["矩阵维度不匹配怎么排查", "怎么防止过拟合", "模型上线怎么回滚"]
cols = st.columns(len(examples))
picked = None
for col, text in zip(cols, examples):
    if col.button(text, use_container_width=True):
        picked = text

question = st.text_input("提问", value=picked or "", placeholder="例如：梯度爆炸怎么处理")

if st.button("提问", type="primary") or picked:
    q = picked or question
    if not q:
        st.warning("先输入一个问题")
        st.stop()

    with st.spinner("检索知识库…"):
        result = answer(q, kb, api_key, base_url=base_url, model=model, k=top_k)

    left, right = st.columns([3, 2])

    with left:
        st.subheader("回答")
        if result.get("error"):
            st.error(result["error"])
        elif result["answer"]:
            st.markdown(result["answer"])
        else:
            st.code(result["prompt"], language="text")

    with right:
        st.subheader(f"检索到 {len(result['hits'])} 个片段")
        for i, hit in enumerate(result["hits"], 1):
            with st.expander(f"{i}. {hit['title']}（{hit['score']:.3f}）"):
                st.caption(f"来源：{hit['source']}")
                st.text(hit["text"][:900])

st.divider()
st.caption(
    "向量化用的是 TF-IDF 字符 n-gram，不依赖任何嵌入模型，断网可用。"
    "生产环境换成 bge / text-embedding 之类的语义嵌入即可，检索接口不变。"
)
