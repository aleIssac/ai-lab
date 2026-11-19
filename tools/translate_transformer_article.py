# -*- coding: utf-8 -*-
"""
把 apps/transformer-explainer/build/index.html 里 <div class="article ..."> 的
英文正文替换为中文。保留全部 HTML 结构、链接、KaTeX 公式与专有名词。

用法：
    python tools/translate_transformer_article.py           # 试运行，只报告
    python tools/translate_transformer_article.py --apply   # 实际写入

设计：
- 只处理标签之间的纯文本片段（>...<），不碰属性、不碰 <script>
- 用「片段开头前 N 个字符」匹配，取最长命中，避免整段逐字比对出错
- 中文片段按需补一个前导空格（前面是英文单词时）
"""

import io
import re
import sys

PATH = "apps/transformer-explainer/build/index.html"

CJK_PUNCT = "：，。、；！？（）「」“”‘’"

# key（英文片段开头）-> 中文
T = {
    # ---------- 开篇 ----------
    "Transformer is a neural network": "Transformer 是一种神经网络架构，它从根本上改变了人工智能的技术路线。Transformer 最早出现在 2017 年的开创性论文",
    "in 2017 and has since become": "中，此后成为深度学习模型的首选架构，支撑了 OpenAI 的",
    ", Meta's": "、Meta 的",
    ", and Google's": "、Google 的",
    ". Beyond text, Transformer is also applied in": " 等文本生成模型。除文本之外，Transformer 还被用于",
    "audio generation": "音频生成",
    "image recognition": "图像识别",
    "protein structure prediction": "蛋白质结构预测",
    ", and even": "，乃至",
    "game playing": "游戏博弈",
    ", demonstrating its versatility": "，展现出在众多领域上的通用性。",

    "Fundamentally, text-generative Transformer models": "本质上，文本生成类 Transformer 模型遵循的是",
    "next-token prediction": "下一 token 预测",
    ": given a text prompt from the user": "：给定用户输入的一段文本提示，紧随其后的",
    "most probable next token": "最可能的那个 token（一个词，或词的一部分）",
    "that will follow this input?": "是什么？Transformer 的核心创新与能力，在于它使用自注意力（self-attention）机制，能够一次性处理整个序列，比以往的架构更有效地捕获长距离依赖关系。",

    "GPT-2 family of models are prominent": "GPT-2 系列模型是文本生成类 Transformer 的典型代表。Transformer Explainer 由",
    "(small) model which has 124 million": "（small）模型驱动，该模型有 1.24 亿个参数。它虽然不是最新、最强的 Transformer 模型，但与当前最先进的模型共享许多相同的架构组件与设计原理，因此是理解基础概念的理想起点。",

    # ---------- 三个组件 ----------
    "Every text-generative Transformer consists": "每一个文本生成类 Transformer 都由以下",
    "three key components": "三个关键组件",
    ": Text input is divided into smaller units": "：文本输入被切分为更小的单元（token），可以是一个词，也可以是子词。这些 token 会被转换为数值向量（embedding），用来承载词的语义。",
    "is the fundamental building block": "是模型的基本构建单元，负责处理和变换输入数据。每个块包含：",
    ", the core component of the Transformer block": "，这是 Transformer 块的核心组件。它让 token 之间可以相互通信，从而捕获上下文信息以及词与词之间的关系。",
    "MLP (Multilayer Perceptron) Layer": "MLP（多层感知机）层",
    ", a feed-forward network that operates": "，这是一个前馈网络，对每个 token 独立运算。注意力层负责在 token 之间传递信息，而 MLP 的目标是细化每个 token 的表示。",
    ": The final linear and softmax": "：最后的线性层与 softmax 层把处理后的 embedding 转换为概率，使模型能够对序列中的下一个 token 作出预测。",

    # ---------- 词嵌入 ----------
    "Let's say you want to generate text": "假设你要用 Transformer 生成文本。你输入这样一段提示：",
    ". This input needs to be converted": "。这段输入必须先转换成模型能理解和处理的格式，这正是 embedding 的作用：把文本变成模型可以运算的数值表示。要把提示转换为 embedding，需要 1）对输入分词，2）取得 token embedding，3）加入位置信息，4）把 token 编码与位置编码相加得到最终的 embedding。下面逐步来看。",

    # 图注
    "Figure": "图",
    ". Expanding the Embedding layer view": " 展开 Embedding 层后的视图，展示输入提示如何被转换为向量表示。整个过程包含",
    "Tokenization, (2) Token Embedding": "分词（Tokenization）、（2）token embedding、（3）位置编码、（4）最终 embedding。",

    # ---------- 分词 ----------
    "Tokenization is the process of breaking": "分词（tokenization）是把输入文本切分为更小、更易处理的单元（token）的过程。token 可以是一个完整的词，也可以是子词。",
    "correspond to unique tokens": "分别对应独立的 token，而",
    "is split into two tokens": "被拆成了两个 token。完整的词表在训练前就已确定：GPT-2 的词表包含",
    "unique tokens. Now that we split": "个互不相同的 token。既然输入文本已被切成带唯一 ID 的 token，就可以从 embedding 中取得它们的向量表示。",

    # ---------- 词嵌入向量 ----------
    "GPT-2 (small) represents each token": "GPT-2（small）把词表中的每个 token 表示为一个 768 维向量；具体维度取决于模型。这些 embedding 向量存放在一个形状为",
    ", containing approximately 39 million": " 的矩阵中，包含约 3900 万个参数！这个庞大的矩阵让模型能为每个 token 赋予语义：语义或用法相近的 token 在高维空间中彼此靠近，不相似的则相距较远。",

    # ---------- 位置编码 ----------
    "The Embedding layer also encodes": "Embedding 层同时编码每个 token 在输入提示中的位置信息。不同模型使用不同的位置编码方法。GPT-2 从零训练自己的位置编码矩阵，并把它直接纳入训练过程。",
    "Finally, we sum the token and positional": "最后，把 token 编码与位置编码相加，得到最终的 embedding 表示。这个合成表示既包含 token 的语义，也包含它在输入序列中的位置。",

    # ---------- Transformer 块 ----------
    "The core of the Transformer's processing": "Transformer 的全部处理都发生在 Transformer 块中，它由多头自注意力与多层感知机层组成。多数模型由多个这样的块依次堆叠而成。token 的表示会随层数逐层演化，从第一块到最后一个块，模型由此逐步构建对每个 token 的细致理解，形成更高阶的表示。我们正在观察的 GPT-2（small）由",
    "such blocks.": " 个这样的块组成。",
    "The self-attention mechanism enables": "自注意力机制让模型能够捕获序列中 token 之间的关联，使每个 token 的表示都受其他 token 影响。多个注意力头让模型从不同视角考察这些关联：例如一个头关注短距离的句法联系，另一个头跟踪更宽泛的语义上下文。下一节将逐步演示多头自注意力的计算过程。",

    # QKV 图注
    ". Computing Query, Key, and Value matrices": " 从原始 embedding 计算 Query、Key、Value 矩阵。",
    "Each token's embedding vector is transformed": "每个 token 的 embedding 向量会被转换为三个向量：",
    ". These vectors are derived by multiplying": "。这三个向量由输入 embedding 矩阵与可学习的权重矩阵相乘得到，分别对应",
    ". Here's a web search analogy": "。可以用网络搜索来类比，帮助理解这三个矩阵的作用：",
    "is the search text you type": "是你在搜索框里输入的检索词，也就是",
    "\"find more information about\"": "“想了解更多信息”",
    "is the title of each web page": "是搜索结果窗口中每个网页的标题，代表 query 可以去关注的候选 token。",
    "is the actual content of web pages": "是网页的实际内容。当检索词（Query）匹配到相关结果（Key）之后，我们要取的就是最相关页面的内容（Value）。",
    "By using these QKV values": "借助 Q、K、V，模型可以计算注意力分数，从而决定生成预测时每个 token 应该获得多少关注。",

    # 多头
    "vectors are split into multiple heads": " 三个向量会被拆分到多个头上——在 GPT-2（small）中是",
    "heads. Each head processes a segment": " 个头。每个头独立处理一部分 embedding，捕获不同的句法与语义关系。这种设计让模型可以并行学习多样的语言特征，增强表示能力。",

    # 掩码自注意力
    "In each head, we perform masked": "在每个头里，我们执行带掩码的自注意力计算。这个机制让模型在关注输入中相关部分的同时，无法访问未来的 token，从而逐步生成序列。",
    ". Using Query, Key, and Value matrices to calculate": " 使用 Query、Key、Value 矩阵计算掩码自注意力。",
    ": The dot product of": "：",
    "matrices determines the": "两个矩阵的点积决定",
    "attention score": "注意力分数",
    ", producing a square matrix": "，得到一个方阵，反映所有输入 token 之间的关系。",
    ": The attention scores are scaled": "：先对注意力分数做缩放，再把注意力矩阵的上三角遮蔽掉，使模型无法访问未来的 token，这些位置被置为负无穷。模型必须在“不偷看”未来的前提下学会预测下一个 token。",
    ": After masking and scaling": "：掩码与缩放之后，注意力分数经 softmax 转换为概率，可选地再用 dropout 正则化。矩阵每一行之和为 1，表示它左侧每个 token 与它的相关程度。",

    # 输出与拼接
    "The model uses the masked self-attention": "模型用带掩码的注意力分数乘以",
    "matrix to get the": "矩阵，得到自注意力机制的",
    "final output": "最终输出",
    "of the self-attention mechanism. GPT-2 has": "。GPT-2 有",
    "self-attention heads, each capturing": " 个自注意力头，各自捕获 token 之间不同的关系。这些头的输出被拼接起来，再经过一次线性投影。",

    # MLP
    ". Using MLP layer to project": " 用 MLP 层把自注意力的表示投影到更高维空间，以增强模型的表示能力。",
    "After the multiple heads of self-attention": "自注意力的多个头捕获输入 token 之间的多样关系后，拼接后的输出会送入多层感知机（MLP）层，以增强模型的表示能力。MLP 块由两次线性变换组成，中间夹着一个",
    "activation function in between.": " 激活函数。",
    "The first linear transformation expands": "第一次线性变换把输入维度扩大四倍，从",
    "to": "到",
    ". This expansion step allows": "。扩维使模型可以把 token 表示投影到更高维的空间，在那里捕获原始维度下看不见的更丰富、更复杂的模式。",
    "The second linear transformation then reduces": "第二次线性变换再把维度压回原来的",
    ".This compression step brings": "。压缩把表示恢复到可处理的规模，同时保留扩维阶段引入的有用的非线性变换。",
    "Unlike the self-attention mechanism": "自注意力机制在 token 之间整合信息，而 MLP 对每个 token 独立处理，只是把每个 token 的表示从一个空间映射到另一个空间，从而扩充模型的整体容量。",

    # ---------- 输出概率 ----------
    "After the input has been processed": "输入经过全部 Transformer 块之后，输出会送入最后的线性层，为 token 预测做准备。该层把最终表示投影到",
    "dimensional space, where every token": " 维空间，词表中的每个 token 都对应一个值，称为",
    ". Any token can be the next word": "。任何 token 都可能成为下一个词，因此这一步相当于按“成为下一个词”的可能性对全部 token 排序。随后用 softmax 把 logit 转换为和为 1 的概率分布，据此采样下一个 token。",
    ". Each token in the vocabulary is assigned": " 词表中每个 token 都根据模型输出的 logit 获得一个概率，这些概率决定它成为序列中下一个词的可能性。",
    "The final step is to generate the next token": "最后一步是从该分布中采样，生成下一个 token。",
    "hyperparameter plays a critical role": " 这个超参数在此过程中起关键作用。从数学上看操作非常简单：把模型输出的 logit 直接除以",
    ": Dividing logits by one": "：除以 1 不改变 softmax 的输出。",
    ": Lower temperature makes the model": "：温度越低，概率分布越尖锐，模型更自信、更确定，输出更可预测。",
    ": Higher temperature creates": "：温度越高，概率分布越平缓，生成文本的随机性更强，也就是常说的模型",
    "“creativity”": "“创造力”",
    "In addition, the sampling process": "此外，还可以用",
    "parameters:": " 两个参数进一步约束采样过程：",
    ": Limits the candidate tokens": "：只在概率最高的 k 个 token 中选取，过滤掉可能性较低的候选。",
    ": Considers the smallest set of tokens": "：取累积概率刚超过阈值 p 的最小 token 集合，只让最可能的 token 参与，同时保留一定多样性。",
    "By tuning": "通过调整",
    ", you can balance between deterministic": "，可以在确定性与多样性之间取得平衡，把模型行为调整到符合具体需求。",

    # ---------- 辅助特性 ----------
    "There are several auxiliary architectural": "还有一些辅助架构特性可以提升 Transformer 的表现。它们对模型整体性能很重要，但对理解架构的核心概念没那么关键。层归一化、Dropout 与残差连接是 Transformer 中的关键组件，尤其在训练阶段：层归一化稳定训练、帮助模型更快收敛；Dropout 通过随机失活神经元防止过拟合；残差连接让梯度直接流过网络，缓解梯度消失问题。",
    "Layer Normalization helps to stabilize": "层归一化有助于稳定训练过程、改善收敛。它沿特征维度对输入做归一化，使激活值的均值与方差保持一致，从而缓解内部协变量偏移问题，让模型学得更有效，也降低对初始权重的敏感度。每个 Transformer 块中会用到两次层归一化：一次在自注意力之前，一次在 MLP 层之前。",
    "Dropout is a regularization technique": "Dropout 是一种正则化手段，通过在训练时随机把一部分模型权重置零来防止过拟合。这会促使模型学到更稳健的特征，降低对特定神经元的依赖，从而在新数据上泛化更好。推理阶段 dropout 会被关闭，这相当于对训练出的众多子网络做集成，因此效果更佳。",
    "Residual connections were first introduced": "残差连接最早出现在 2015 年的 ResNet 中。这一架构创新使极深的神经网络可以被训练，从而推动了深度学习的发展。本质上，残差连接是一条跳过一层或多层的捷径，把某层的输入加到它的输出上。这有助于缓解梯度消失，使堆叠多个 Transformer 块的深层网络更容易训练。在 GPT-2 中，每个 Transformer 块内会用到两次残差连接：一次在 MLP 之前，一次在其后，使梯度更容易流动，让靠前的层在反向传播时也能获得足够的更新。",

    # ---------- 交互功能 ----------
    "Transformer Explainer is built to be interactive": "Transformer Explainer 以交互为核心，让你可以亲手探索 Transformer 的内部运作。下面是一些可以动手尝试的功能：",
    "Input your own text sequence": "输入自己的文本序列",
    "to see how the model processes it": "，观察模型如何处理这段文本并预测下一个词。你可以查看注意力权重、中间计算过程，以及最终输出概率是如何得出的。",
    "Use temperature slider": "拖动 temperature 滑块",
    "to control the randomness of the model": "，控制模型预测的随机程度，体会改变 temperature 会让输出更确定还是更有创造性。",
    "Select top-k and top-p sampling methods": "选择 top-k 与 top-p 采样方法",
    "to adjust sampling behavior during inference": "，调整推理时的采样行为；试着换不同取值，观察概率分布如何变化、又如何影响模型的预测。",
    "Interact with attention maps": "与注意力图交互",
    "to see how the model focuses on different tokens": "，观察模型如何聚焦输入序列中的不同 token。把鼠标悬停在 token 上即可高亮其注意力权重，探索模型如何捕获上下文以及词与词之间的关系。",

    # ---------- 实现与作者 ----------
    "Transformer Explainer features a live": "Transformer Explainer 在浏览器内直接运行一个真实的 GPT-2（small）模型。该模型来自 Andrej Karpathy 的 PyTorch 版 GPT 实现（即",
    "nanoGPT project": "nanoGPT 项目",
    "and has been converted to": "），并已转为",
    "for seamless in-browser execution": "，以便在浏览器中无缝执行。界面用 JavaScript 构建，前端框架为",
    "as a front-end framework and": "，动态可视化由",
    "for creating dynamic visualizations": " 实现。所有数值都会随用户输入实时更新。",
    "Transformer Explainer was created by": "Transformer Explainer 由佐治亚理工学院的",
    "at the Georgia Institute of Technology.": " 等人开发。",
    ", and": "、",
    "and": "和",
}

# 保持英文的片段（专有名词 / 论文名 / 代码值 / 公式标签）
KEEP = {
    "\"Attention is All You Need\"", "GPT", "Llama", "Gemini", "GPT-2", "Embedding", "Weights",
    "Bias", "ij", "Transformer Block", "Attention Mechanism", "Output Probabilities",
    "Query (Q)", "Key (K)", "Value (V)", "Query", "key", "Value", "Dot Product",
    "Scaling · Mask", "Softmax · Dropout", "logit", "temperature", "temperature = 1",
    "temperature &lt; 1", "top-k", "top-p", "top-k sampling", "top-p sampling", "GELU",
    "SVELTE", "Svelte", "D3.js", "ONNX Runtime", "Aeree Cho", "Grace C. Kim",
    "Alexander Karpekov", "Alec Helbling", "Jay Wang", "Seongmin Lee", "Benjamin Hoover",
    "Polo Chau", "“Data visualization empowers users to”", "\"Data\"", "\"visualization\"",
    "\"empowers\"",
}


def norm(text):
    return " ".join(text.split())


def pick(text):
    """精确匹配优先；前缀匹配要求 key 足够长，避免 "to" 命中 "top-k" 这类词"""
    if text in T:
        return text
    best = None
    for k in T:
        if len(k) < 8:
            continue
        if text.startswith(k) and (best is None or len(k) > len(best)):
            best = k
    return best


def prev_is_latin(prefix):
    m = re.search(r">([^<>]*)</[A-Za-z0-9]+>$", prefix)
    if not m:
        return False
    t = m.group(1).rstrip()
    return bool(t) and (t[-1].isascii() and (t[-1].isalnum() or t[-1] in ")]\"'"))


def polish(region):
    """中英标点与间距收尾（只作用于正文，不含尾部 <script>）"""
    cut = region.find("<script")
    head, tail = (region, "") if cut < 0 else (region[:cut], region[cut:])

    # 链接/强调/代码之间的英文逗号改成顿号
    for tag in ("a", "span", "code", "strong", "em"):
        head = re.sub(r"</%s>,\s*" % tag, "</%s>、" % tag, head)
    # 标签紧跟的半角冒号、句号
    for tag in ("a", "span", "code", "strong", "em"):
        head = re.sub(r"</%s>\s*:" % tag, "</%s>：" % tag, head)
        head = re.sub(r"</%s>\s*\.\s*(?=<|[\u4e00-\u9fff])" % tag, "</%s>。" % tag, head)
    # 中文后的半角冒号、句号
    head = re.sub(r"([\u4e00-\u9fff”])\s*:\s*", r"\1：", head)
    head = re.sub(r"([\u4e00-\u9fff”])\s*\.\s*(?=<|[\u4e00-\u9fff])", r"\1。", head)
    # 中文与“行内元素里的英文/数字”之间补空格（跨标签，规则 7 管不到）
    inline = r"(?:a|code|strong|em|span)"
    head = re.sub(r"([\u4e00-\u9fff])(<(?:%s)\b[^>]*>)(?=[A-Za-z0-9(\"'])" % inline, r"\1 \2", head)
    head = re.sub(r"([A-Za-z0-9)\"'])(</(?:%s)>)([\u4e00-\u9fff])" % inline, r"\1\2 \3", head)
    # 中文与英文/数字之间补空格
    head = re.sub(r"([\u4e00-\u9fff])([A-Za-z0-9])", r"\1 \2", head)
    head = re.sub(r"([A-Za-z0-9])([\u4e00-\u9fff])", r"\1 \2", head)
    # 「图 1」这类图注编号
    head = re.sub(r"图(\d)", r"图 \1", head)
    return head + tail


def main():
    apply = "--apply" in sys.argv
    s = io.open(PATH, encoding="utf-8").read()

    start = s.find('<div class="article h-auto w-full')
    end = s.find("</body>", start)
    region = s[start:end]

    out = []
    pos = 0
    hit = 0
    skipped = []
    for m in re.finditer(r">([^<>]+)<", region):
        raw = m.group(1)
        n = norm(raw)
        if not n or not re.search(r"[A-Za-z]", n):
            continue
        key = pick(n)
        if key is None:
            if n not in KEEP:
                skipped.append(n)
            continue
        zh = T[key]
        gap = region[pos : m.start(1)]
        if not zh.startswith(" "):
            gap = gap.rstrip()
        out.append(gap)
        out.append(zh)
        pos = m.end(1)
        hit += 1
    out.append(region[pos:])
    new_region = polish("".join(out))

    print(f"替换片段: {hit}")
    if skipped:
        print(f"未处理片段 {len(skipped)} 条（需确认是否漏译）:")
        for t in skipped[:40]:
            print("   -", t[:90])
    if apply:
        io.open(PATH, "w", encoding="utf-8", newline="\n").write(s[:start] + new_region + s[end:])
        print("已写入", PATH)
    else:
        print("（试运行，未写入；加 --apply 生效）")
        # 抽样看效果
        for t in re.findall(r"<p[^>]*>([\s\S]{0,160}?)</p>", new_region)[:3]:
            print("样例:", re.sub(r"<[^>]+>", "", t)[:120])


if __name__ == "__main__":
    main()
