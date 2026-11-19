# -*- coding: utf-8 -*-
"""
把 Transformer Explainer 导读弹窗（20 条「Read more」卡片）的 HTML 正文替换为中文。
专有名词保留英文：Transformer / Query / Key / Value / MLP / Top-k / top-p / GELU / logit / RoPE 等。

用法：
    python tools/translate_transformer_popups.py           # 试运行
    python tools/translate_transformer_popups.py --apply   # 写入
"""

import io
import json
import re
import sys

PATH = "apps/transformer-explainer/build/_app/immutable/chunks/BUHqZIDc.js"

ZH = {
"what-is-transformer": """<p><strong>Transformer</strong> 是现代 AI 的核心架构，驱动着 ChatGPT、Gemini 等模型。它于 2017 年被提出，彻底改变了 AI 处理信息的方式。同一个架构既用于在海量数据上训练，也用于推理时生成输出。这里我们使用 GPT-2（small）：它比新模型简单，却正好适合学习基本原理。</p>
""",

"how-transformers-work": """<p>Transformer 并不神秘——它通过不断回答下面这个问题，一步一步把文本生成出来：</p>
	<blockquote class="question">
		“紧跟这段输入之后，最可能的那个词是什么？”
	</blockquote>
	<p>下面演示训练好的模型如何生成文本。你可以自己写一段文字，或直接用示例，然后点击 <strong>生成</strong> 查看效果。如果模型还没准备好，可以换一个 <strong>示例</strong>。</p>""",

"transformer-architecture": """<p>Transformer 由三部分组成：</p><div class="numbered-list"><div class="numbered-item"><span class="number-circle">1</span><div class="item-content"><strong>Embeddings</strong> 把文本转换成数字。</div></div><div class="numbered-item"><span class="number-circle">2</span><div class="item-content"><strong>Transformer blocks</strong> 用自注意力（Self-Attention）混合信息，再用 MLP 精炼。</div></div><div class="numbered-item"><span class="number-circle">3</span><div class="item-content"><strong>Probabilities</strong> 决定每个候选 token 成为下一个词的可能性。</div></div></div>""",

"embedding": """<p>Transformer 在使用文本之前，先把它切成小单元，并把每个单元表示成一串数字（向量）。这个过程称为 <strong>embedding</strong>，这个词既可以指这个过程，也可以指得到的向量。</p><p>在本工具中，每个向量显示为一个矩形，鼠标悬停即可看到它的维度。</p>""",

"token-embedding": """<p><strong>Tokenization</strong> 把输入文本切成 token——它可以是一个词，也可以是词的一部分。GPT-2（small）的词表有 50,257 个 token，每个都有唯一 ID。</p><p>在 <strong>token embedding</strong> 这一步，每个 token 会从一张大型查找表中取出对应的 768 维向量。这些向量在训练中学习得到，用来最好地表达每个 token 的含义。</p>""",

"positional-encoding": """<p>语言中，词序很重要。<strong>Positional encoding</strong> 为每个 token 提供它在序列中所处位置的信息。</p><p>GPT-2 的做法是把一个可学习的位置 embedding 加到 token 的 embedding 上；更新的模型可能采用别的方法，例如 RoPE——通过旋转特定向量来编码位置。这些方法的目标都是让模型理解文本中的顺序。</p>""",

"blocks": """<p><strong>Transformer block</strong> 是模型中的主要处理单元，包含两部分：</p><ul><li><strong>Multi-head self-attention</strong>——让 token 之间共享信息</li><li><strong>MLP</strong>——精炼每个 token 的细节</li></ul><p>模型会把许多块堆叠起来，token 表示经过一层层处理后越来越丰富。GPT-2（small）有 12 个这样的块。</p>""",

"self-attention": """<p><strong>Self-attention</strong> 让模型判断输入中哪些部分与每个 token 最相关，从而捕获含义与关系，即使两个词相隔很远也能关联起来。</p><p>在 <strong>multi-head</strong> 形式下，模型并行运行多个注意力过程，每个关注文本中不同的模式。</p>""",

"qkv": """ 	<p>为了做自注意力，每个 token 的 embedding 会被转换成 
  <span class="highlight">三个新的 embedding</span>——
  <span class="blue">Query</span>、  
  <span class="red">Key</span> 和  
  <span class="green">Value</span>。
  这一步通过给每个 token 的 embedding 施加不同的权重与偏置完成，这些参数（权重与偏置）在训练中不断优化。</p>

<p>生成之后，<span class="blue">Query</span> 与 <span class="red">Key</span> 比较来衡量相关性，再用这个相关性给 <span class="green">Value</span> 加权。</p>
""",

"multi-head": """<p>生成 <span class="blue">Q</span>、<span class="red">K</span>、<span class="green">V</span> 三个 embedding 后，模型把它们拆分到若干个 <strong>heads</strong>（GPT-2 small 中是 12 个）。每个头各自使用一组更小的 <span class="blue">Q</span>/<span class="red">K</span>/<span class="green">V</span>，关注文本中的不同模式——例如语法、语义或远距离关联。</p><p>多个头让模型并行学习多种关系，理解因而更丰富。</p>""",

"masked-self-attention": """<p>在每个头里，模型决定每个 token 对其他 token 的关注程度：</p><ul><li><strong>Dot Product</strong>——把 <span class="blue">Query</span>/<span class="red">Key</span> 向量中对应的数字相乘并求和，得到 <span class="purple">注意力分数</span>。</li><li><strong>Mask</strong>——遮蔽未来的 token，让它无法提前偷看。</li><li><strong>Softmax</strong>——把分数转换为概率，每行之和为 1，表示对前面各个 token 的关注程度。</li></ul>""",

"output-concatenation": """<p>每个头<span class="highlight">把自身的 <span class="purple">注意力分数</span> 与 <span class="green">Value</span> embedding 相乘，得到该头的注意力输出</span>——这是在考虑上下文之后，对每个 token 更精细的表示。</p><p>GPT-2（small）有 12 个这样的输出，它们被拼接成一个原始维度的向量（768 个数字）。</p>""",

"mlp": """<p>注意力输出会经过 <strong>MLP</strong> 来精炼 token 表示。Linear 层用学到的权重与偏置改变 embedding 的取值和维度，再由非线性激活决定每个值通过多少。</p><p>激活函数有多种，GPT-2 使用的是 <strong>GELU</strong>：小的值部分通过，大的值完整通过，因而既能捕获细微模式，也能捕获强烈模式。</p>""",

"output-logit": """<p>经过全部 Transformer 块后，最后一个 token 的输出 embedding 已经融合了前面所有 token 的上下文，它会在最后一层与学到的权重相乘。</p><p>由此得到 <strong>logit</strong>——50,257 个数字，对应 GPT-2 词表中的每个 token，表示它成为下一个词的可能性。</p>""",

"output-probabilities": """<p>logit 只是原始分数。为了便于解读，我们把它转换成 0 到 1 之间的<strong>概率</strong>，总和为 1，表示每个 token 成为下一个词的可能性。</p><p>我们可以不总是挑概率最高的 token，而用不同的选择策略，在生成文本的稳妥与创造性之间取得平衡。</p>""",

"temperature": """<p><strong>Temperature</strong> 的作用是在把 logit 转成概率之前先做缩放。<strong>较低的温度</strong>（例如 0.2）会让大的 logit 更大、小的更小，倾向得分最高的 token，结果更<strong>可预测</strong>；<strong>较高的温度</strong>（例如 1.0 或更高）则抹平差异，让原本可能性低的 token 更有竞争力，结果更<strong>有创造性</strong>。</p>""",

"sampling": """<p>最后需要一个挑选下一个 token 的策略。常见的有：贪心搜索（greedy）直接取概率最高的一个；<strong>Top-k</strong> 只在最可能的 k 个 token 中选；<strong>top-p</strong> 取累积概率刚达到 p 的最小集合——提前裁掉可能性低的候选。</p><p>随后 softmax 把剩下的 logit 转成概率，再从允许的集合中随机抽一个 token。</p>""",

"residual": """<p>Transformer 还有一些辅助特性来提升性能。例如<strong>残差连接</strong>把某一层的输入加到它的输出上，避免信息在多层传递中衰减。在 GPT-2 中，每个块会用两次，以便有效训练更深的堆叠。</p>""",

"layer-normalization": """<p><strong>Layer Normalization</strong> 通过调整输入的数值，让均值和方差保持一致，从而稳定训练与推理。这使模型对初始权重不那么敏感，学习也更有效。在 GPT-2 中，它在自注意力之前、MLP 之前各用一次，最终输出前再用一次。</p>""",

"dropout": """<p>训练时，<strong>dropout</strong> 随机断开一部分连接，避免模型过拟合特定模式，从而学到泛化更好的特征。GPT-2 采用了它；但更新的 LLM 往往不用，因为它们训练数据极大，过拟合不再是主要问题。推理阶段 dropout 会关闭。</p>""",
}


def find_items(s):
    i = s.find('ab=[{id:"what-is-transformer"')
    j = s.find("]}];", i)
    seg = s[i : j + 3] if j > 0 else s[i : i + 40000]
    out = []
    for m in re.finditer(r'\{id:"([^"]+)",title:"([^"]+)"', seg):
        iid = m.group(1)
        ci = seg.find("content:", m.start())
        if ci < 0:
            continue
        q = seg[ci + 8]
        if q not in "\"'`":
            continue
        p0 = ci + 9
        k = p0
        while k < len(seg):
            if seg[k] == "\\":
                k += 2
                continue
            if seg[k] == q:
                break
            k += 1
        out.append({"id": iid, "quote": q, "start": i + p0, "end": i + k, "html": seg[p0:k]})
    return out


def main():
    apply = "--apply" in sys.argv
    s = io.open(PATH, encoding="utf-8").read()
    items = find_items(s)
    print("找到条目:", len(items))

    miss = [it["id"] for it in items if it["id"] not in ZH]
    if miss:
        print("缺少译文:", miss)

    # 引用符安全检查：新文本不能包含所在字符串的定界符
    bad = []
    for it in items:
        zh = ZH.get(it["id"])
        if zh is None:
            continue
        q = it["quote"]
        if q in zh:
            bad.append((it["id"], q))
        if q == "`" and ("${" in zh):
            bad.append((it["id"], "${"))
    if bad:
        print("存在会破坏字符串的字符:", bad)
        sys.exit(1)

    if not apply:
        print("（试运行，未写入）")
        return

    # 从后往前替换，避免偏移错乱
    for it in sorted(items, key=lambda x: -x["start"]):
        zh = ZH.get(it["id"])
        if zh is None:
            continue
        s = s[: it["start"]] + zh + s[it["end"] :]
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(s)
    print("已写入", PATH)


if __name__ == "__main__":
    main()
