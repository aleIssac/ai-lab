# -*- coding: utf-8 -*-
"""
把 nodes/0.Br7VsJSJ.js 里内联的文章 HTML 也翻成中文。
index.html 只是 SSR 的首屏产物；页面水合后 Svelte 会用这份 JS 里的字符串重建 DOM，
所以两处必须同时翻译，否则刷新一下又变回英文。

用法：python tools/translate_transformer_article_js.py [--apply]
"""

import importlib.util
import io
import re
import sys

TARGET = "apps/transformer-explainer/build/_app/immutable/nodes/0.Br7VsJSJ.js"

# 标题：与 index.html 中已翻译的标题保持完全一致
HEADINGS = {
    "What is a Transformer?": "Transformer 是什么？",
    "Transformer Architecture": "Transformer 整体架构",
    "Embedding": "词嵌入（Embedding）",
    "Step 1: Tokenization": "第 1 步：分词（Tokenization）",
    "Step 2. Token Embedding": "第 2 步：词嵌入（Token Embedding）",
    "Step 3. Positional Encoding": "第 3 步：位置编码（Positional Encoding）",
    "Step 4. Final Embedding": "第 4 步：最终嵌入",
    "Transformer Block": "Transformer 块（Transformer Block）",
    "Multi-Head Self-Attention": "多头自注意力（Multi-Head Self-Attention）",
    "Step 1: Query, Key, and Value Matrices": "第 1 步：Query / Key / Value 矩阵",
    "Step 2: Multi-Head Splitting": "第 2 步：多头拆分",
    "Step 3: Masked Self-Attention": "第 3 步：掩码自注意力",
    "Step 4: Output and Concatenation": "第 4 步：输出与拼接",
    "MLP: Multi-Layer Perceptron": "MLP：多层感知机",
    "Output Probabilities": "输出概率",
    "Auxiliary Architectural Features": "辅助架构特性",
    "Layer Normalization": "层归一化（Layer Normalization）",
    "Dropout": "Dropout（随机失活）",
    "Residual Connections": "残差连接",
    "Interactive Features": "交互功能",
    "How is Transformer Explainer Implemented?": "Transformer Explainer 是如何实现的？",
}


def load_module():
    spec = importlib.util.spec_from_file_location("ta", "tools/translate_transformer_article.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    apply = "--apply" in sys.argv
    ta = load_module()
    s = io.open(TARGET, encoding="utf-8").read()

    start = s.find('<div class="article-section')
    # 文章 HTML 是一个模板字符串，以 `); 结束；用它做右边界最稳
    end = s.find("`);", start)
    if start < 0 or end < 0:
        raise SystemExit("文章区间定位失败")
    region = s[start:end]

    # 1) 正文段落
    pos, out, hit = 0, [], 0
    for m in re.finditer(r">([^<>]+)<", region):
        raw = m.group(1)
        n = " ".join(raw.split())
        if not n or not re.search(r"[A-Za-z]", n):
            continue
        key = ta.pick(n)
        if key is None:
            continue
        zh = ta.T[key]
        gap = region[pos : m.start(1)]
        if not zh.startswith(" "):
            gap = gap.rstrip()
        out.append(gap)
        out.append(zh)
        pos = m.end(1)
        hit += 1
    out.append(region[pos:])
    new_region = ta.polish("".join(out))

    # 2) 标题（整标签文本替换，避免影响属性）
    h = 0
    for en, zh in HEADINGS.items():
        pat = re.compile(r"(<h[1-4][^>]*>)\s*" + re.escape(en) + r"\s*(</h[1-4]>)")
        new_region, k = pat.subn(lambda m: m.group(1) + zh + m.group(2), new_region)
        h += k

    print(f"段落片段 {hit} 条，标题 {h} 条")

    if not apply:
        print("（试运行，未写入）")
        return
    io.open(TARGET, "w", encoding="utf-8", newline="\n").write(s[:start] + new_region + s[end:])
    print("已写入", TARGET)


if __name__ == "__main__":
    main()
