# ai-lab · 离线 AI 开发教学环境

一套**完全离线**的 AI 开发教学环境。一台 Windows 机器装好 Docker Desktop 之后，学生在浏览器里写代码、跑 Notebook、训练模型、调用 API、做 RAG 问答，全程不需要外网，宿主机也不需要装 Python。

- **环境**：Windows 11 · Docker Desktop (WSL2) · 20 核 CPU / 8 GB 内存 · 无 GPU · 无外网
- **形态**：双容器（`ai-lab` + `ollama`），`start.bat` 一键拉起
- **规模**：7 个模块 · 9 个 Notebook · 6 个常驻 Web 服务

---

## 它解决什么问题

实训室的机器不能联网，装不了 Python 和 Node，也没有 GPU。常规做法是让学生在自己电脑上配环境，结果一节课有两节在解决 `pip install` 失败。

这套环境把运行时、数据集、模型、实验跟踪、可视化前端全部固化成离线包：**服务器装一次，学生只开浏览器**。

---

## 七个模块

| # | 模块 | 入口 | 实现 |
|---|---|---|---|
| ① | 浏览器内编码与调试 | `:8080` | code-server 4.141（VS Code 1.141）+ Python / Jupyter 扩展，断点调试可用 |
| ② | Tab 代码补全 | `:8080` 编辑器内 | 自研扩展 + `qwen-coder-fim`，请求经 `:11435` 代理转成 FIM 格式 |
| ③ | 报错诊断 | `:8080` · `Ctrl+Alt+K` | 自研扩展 + 本地 `qwen2.5-coder:1.5b`，选中报错直接给排查方向 |
| ④ | 端到端实训 | `:8080` `:5001` `:8000` `:8501` `:8502` | 数据清洗 → 特征工程 → 训练 → MLflow → FastAPI → Streamlit → RAG |
| ⑤ | 神经网络超参实验 | `:3000` → 神经网络 | TensorFlow Playground，训练在浏览器里真实执行 |
| ⑥ | Transformer 可视化 | `:3000` → Transformer | GPT-2 转 ONNX，ONNX Runtime Web 在浏览器内做真实推理 |
| ⑦ | 经典算法可视化 | `:3000` → 经典算法 | ConvNetJS 系列 demo，含 DQN 与 CIFAR-10 |

模块 ④ 分三个专项，每个都有独立 Notebook：

```
courses/01-ai-app/     数据清洗 · 特征工程 · 训练与 MLflow · 部署发布   （4 个）
courses/02-bigdata/    Spark 数据清洗 · Spark ML 训练                  （2 个）
courses/03-llm-app/    文档切块与向量化 · RAG 问答链路 · Streamlit 发布 （3 个）
```

---

## 架构

```
Windows 宿主机（只装 Docker Desktop）
│
├── 容器 ai-lab
│     :8080  code-server        编辑器（需求 ①②③）
│     :3000  门户               七个模块的入口（Python 也跑在容器里）
│     :5001  MLflow             实验跟踪
│     :8501  Streamlit          流失预测界面
│     :8502  Streamlit          RAG 问答界面
│     :8000  FastAPI            预测接口（/predict /health /docs）
│     :4040  Spark UI           跑 Spark Notebook 后才出现
│     :11435 Ollama 代理        把补全请求改写成 raw:true（容器内，未映射）
│
└── 容器 ollama
      :11434 Ollama             模型服务

模型：qwen2.5-coder:1.5b（对话）· qwen-coder-fim（补全）· gpt2（Transformer 可视化）
数据：全部挂载在项目目录，容器可删可重建
```

---

## 快速开始

### 方式一：有离线部署包

1. 安装 **Docker Desktop**，后端选 WSL2，确认已启动
2. 解压离线包（约 7.4 GB），确认 **C 盘至少 15 GB 空闲**
3. 双击 `install.bat` —— 它会 `docker load` 两个镜像、检查模型仓库、拉起 `ollama`、最后调用 `start.bat`
4. 等 5～10 分钟，浏览器打开 **http://localhost:3000**

`code-server` 的登录密码来自项目根目录 `.env` 的 `CODE_SERVER_PASSWORD`，没有设置时 compose 会直接报错，不会静默使用默认密码。

日常重启只要双击 `start.bat`。**容器重启后 MLflow、两个 Streamlit、API、Ollama 代理、门户都不会自动恢复**，必须重新执行 `start.bat`。

### 方式二：只有这个仓库

这个仓库**不包含镜像和模型权重**（原因见下一节），所以 clone 下来不能直接运行。可以做的事：

- 读 `src/` 的完整实现（数据管道、训练、API、RAG、Ollama 代理）
- 读 `courses/` 的 9 个 Notebook，里面保留了真实执行输出
- 读 `docs/` 的部署方案、演示流程、原理手册
- 单独跑前端页面：`apps/convnetjs`、`nn-playground` 是纯静态的，用任意静态服务器打开即可

---

## 端口

| 端口 | 服务 | 何时可用 |
|---|---|---|
| 3000 | 门户 | `start.bat` 之后 |
| 8080 | code-server | 容器启动后 |
| 5001 | MLflow | `start.bat` 之后 |
| 8501 | 流失预测 | `start.bat` 之后 |
| 8502 | RAG 问答 | `start.bat` 之后 |
| 8000 | 预测 API（Swagger 在 `/docs`） | `start.bat` 之后 |
| 4040 | Spark UI | 跑 Spark Notebook 第一格之后 |
| 11434 | Ollama | `ollama` 容器启动后 |

> Swagger 必须直接访问 `localhost:8000/docs`。走 `localhost:8080/proxy/8000/docs` 会 404，因为 Swagger 请求的是绝对路径 `/openapi.json`。

---

## 目录结构

```
apps/            Streamlit 页面 + 三个前端可视化项目
courses/         9 个 Notebook（AI 应用 / 大数据 / 大模型）
data/            raw 原始数据、processed 清洗结果、kb 知识库
docker/          Dockerfile、自研补全扩展、MLflow 汉化脚本
docs/            部署方案、演示流程、原理手册、截图
models/          预处理器、模型 pkl、Spark Pipeline
portal/          门户首页
src/             数据管道、训练、FastAPI 服务、RAG 核心、Ollama 代理
tools/           部署与验收脚本
docker-compose.yml
start.bat        一键启动（拉起容器 + 五个后台服务 + 门户）
stop.bat
```

---

## 仓库里没有什么

为了让仓库保持在 150 MB 量级，以下内容**没有入库**，需要从离线部署包获取：

| 内容 | 体积 | 缺了会怎样 |
|---|---|---|
| `部署包/images/*.tar` | 5.2 GB | 无法 `docker load`，整套环境起不来 |
| `部署包/.../ollama-models` | 940 MB | Ollama 没有模型，补全和 RAG 不可用 |
| `apps/transformer-explainer/build/model-v2/` | 627 MB | 模块 ⑥ 打不开（GPT-2 权重） |
| `docker/extensions/` | 379 MB | 编辑器缺 Continue / Python / Jupyter 扩展 |
| `config/index/` | 268 MB | VS Code 索引缓存，可重建 |
| `data/_mnist_src/` | 152 MB | ConvNetJS 的 CIFAR 演示缺样本图 |
| `apps/transformer-explainer/build/ort/` | 70 MB | ONNX Runtime wasm，前端另有打包副本 |

---

## 已知限制

- **模型规模**：对话与补全用 1.5B 模型，代码补全和注释够用，复杂推理明显弱于云端大模型
- **并发**：单机 CPU 推理，3～5 人同时使用后响应明显变慢，不适合整班并行
- **无学生隔离**：所有人共用同一个 code-server 实例和同一个工作目录
- **模块 ⑤⑥⑦ 基于开源项目**：本项目做的是离线部署、汉化与缺陷修复，算法本身不是自研
- **离线副作用**：⑤⑥ 引用了 Google Fonts，Streamlit 默认开启遥测，断网时这些请求会静默失败，不影响功能
- **Spark**：由 pip 安装（4.0.4），不是完整 Hadoop 发行版，只支持 local 模式
- **Spark 4.0 的 ANSI 模式**：`cast` 遇到 `N/A` 会直接抛 `CAST_INVALID_INPUT`，课件里已显式关闭该选项

---

## 文档

| 文档 | 内容 |
|---|---|
| [`docs/项目交接.md`](docs/项目交接.md) | 架构、启动链路、16 条踩坑记录，接手先读这份 |
| [`docs/需求4567-原理讲解与名词手册.md`](docs/需求4567-原理讲解与名词手册.md) | 神经网络、Transformer、强化学习的名词与原理 |
| [`docs/验收演示教程.md`](docs/验收演示教程.md) | 现场演示流程与每步的预期结果 |
| [`docs/需求4-端到端实训-使用说明.md`](docs/需求4-端到端实训-使用说明.md) | 三个专项实训的完整操作说明 |
| [`docs/部署到新电脑.md`](docs/部署到新电脑.md) | 换机器部署的两条路径（离线打包 / 在线构建） |

---

## 致谢

本项目站在这些开源工作上：

- [code-server](https://github.com/coder/code-server) — 浏览器内的 VS Code
- [ConvNetJS](https://github.com/karpathy/convnetjs) — Andrej Karpathy，MIT
- [TensorFlow Playground](https://github.com/tensorflow/playground) — Apache-2.0
- [Transformer Explainer](https://github.com/poloclub/transformer-explainer) — Polo Club of Data Science，MIT
- [MLflow](https://github.com/mlflow/mlflow) · [Streamlit](https://github.com/streamlit/streamlit) · [FastAPI](https://github.com/fastapi/fastapi) · [PySpark](https://github.com/apache/spark) · [Ollama](https://github.com/ollama/ollama)

其中 ConvNetJS 与 TensorFlow Playground 的代码经汉化后置于 `apps/` 与 `nn-playground/`，遵循其原始许可。
