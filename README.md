# ai-lab

离线 AI 开发教学环境。两个 Docker 容器承载编辑器、模型服务、实验跟踪与演示页面，宿主机只需 Docker Desktop，不安装 Python。

| 项 | 值 |
|---|---|
| 环境 | Windows 11 · Docker Desktop (WSL2) · 20 核 CPU / 8 GB 内存 · 无 GPU · 无外网 |
| 启动 | `start.bat`，拉起容器、五个后台服务与门户 |
| 组成 | 7 个模块 · 9 个 Notebook · 6 个 Web 服务 |
| 镜像 | `ai-lab:1.0`（自建）· `ollama/ollama` |
| 模型 | `qwen2.5-coder:1.5b` · `qwen-coder-fim` · `gpt2` |

---

## 功能

| # | 模块 | 入口 | 实现 |
|---|---|---|---|
| ① | 编码与调试 | `:8080` | code-server 4.141（VS Code 1.141），Python / Jupyter 扩展，支持断点调试 |
| ② | 代码补全 | `:8080` | 自研扩展调用 `qwen-coder-fim`，请求经 `:11435` 代理转为 FIM 格式，Tab 接受；`Ctrl+Alt+C` 生成注释，`Ctrl+Alt+Shift+C` 批量处理 |
| ③ | 报错诊断 | `:8080` · `Ctrl+Alt+K` | 选中报错文本，由本地模型返回排查路径 |
| ④ | 端到端实训 | `:8080` `:5001` `:8000` `:8501` `:8502` | 数据清洗 → 特征工程 → 训练 → MLflow 跟踪 → FastAPI 服务 → Streamlit 界面 → RAG 问答 |
| ⑤ | 超参实验 | `:3000` | TensorFlow Playground，前向传播、反向传播与梯度更新在前端实时执行 |
| ⑥ | Transformer 可视化 | `:3000` | GPT-2 转 ONNX，ONNX Runtime Web 在浏览器内完成推理，逐层展示注意力与输出概率 |
| ⑦ | 算法可视化 | `:3000` | ConvNetJS 系列 demo，含 DQN 与 CIFAR-10 |

模块 ④ 的三个专项各自配有 Notebook：

```
courses/01-ai-app/     数据清洗 · 特征工程 · 训练与 MLflow · 部署发布   （4 个）
courses/02-bigdata/    Spark 数据清洗 · Spark ML 训练                  （2 个）
courses/03-llm-app/    文档切块与向量化 · RAG 问答链路 · Streamlit 发布 （3 个）
```

---

## 架构

```
Windows 宿主机（仅需 Docker Desktop）
│
├── 容器 ai-lab
│     :8080  code-server        编辑器
│     :3000  门户               模块入口（Python 运行在容器内）
│     :5001  MLflow             实验跟踪
│     :8501  Streamlit          流失预测界面
│     :8502  Streamlit          RAG 问答界面
│     :8000  FastAPI            预测服务（/predict /health /docs）
│     :4040  Spark UI           执行 Spark Notebook 后出现
│     :11435 Ollama 代理        补全请求改写为 raw:true（未映射到宿主机）
│
└── 容器 ollama
      :11434 Ollama             模型服务
```

数据与模型全部挂载在项目目录，容器可删除重建。

---

## 部署

**有离线包**（约 7.4 GB，C 盘需 15 GB 空闲）：

1. 安装 Docker Desktop，后端选 WSL2
2. 双击 `install.bat`：加载两个镜像、校验模型仓库、启动 `ollama`、调用 `start.bat`
3. 打开 `http://localhost:3000`

`code-server` 密码取自根目录 `.env` 的 `CODE_SERVER_PASSWORD`；未设置时 compose 直接报错，不使用兜底密码。日常重启执行 `start.bat`。

**仅有本仓库**：镜像与模型不在仓库中，无法直接运行。可读取 `src/` 与 `courses/`；`apps/convnetjs`、`nn-playground` 为静态页面，可用任意静态服务器打开。

---

## 端口

| 端口 | 服务 | 可用时机 |
|---|---|---|
| 3000 | 门户 | `start.bat` 完成后 |
| 8080 | code-server | 容器启动后 |
| 5001 | MLflow | `start.bat` 完成后 |
| 8501 | 流失预测 | `start.bat` 完成后 |
| 8502 | RAG 问答 | `start.bat` 完成后 |
| 8000 | 预测 API | `start.bat` 完成后 |
| 4040 | Spark UI | 执行 Spark Notebook 首格后 |
| 11434 | Ollama | `ollama` 容器启动后 |

Swagger 需直接访问 `localhost:8000/docs`；经 `localhost:8080/proxy/8000/docs` 会返回 404，原因是 `/openapi.json` 使用绝对路径。

---

## 目录

```
apps/            Streamlit 页面与三个前端可视化项目
courses/         9 个 Notebook
data/            raw 原始数据、processed 清洗结果、kb 知识库
docker/          Dockerfile、补全扩展、MLflow 汉化脚本
models/          预处理器、模型 pkl、Spark Pipeline
portal/          门户首页
src/             数据管道、训练、FastAPI 服务、RAG、Ollama 代理
tools/           部署与验收脚本
docker-compose.yml
start.bat        启动容器与后台服务
stop.bat
```

---

## 资源边界

仓库保留源码、课件与文档，二进制资源需从离线包获取：

| 内容 | 体积 | 缺失影响 |
|---|---|---|
| `部署包/images/*.tar` | 5.2 GB | 无法加载镜像，环境不可启动 |
| `部署包/.../ollama-models` | 940 MB | 模型缺失，补全与 RAG 不可用 |
| `apps/transformer-explainer/build/model-v2/` | 627 MB | 模块 ⑥ 无法加载 GPT-2 权重 |
| `docker/extensions/` | 379 MB | 编辑器缺少 Continue / Python / Jupyter 扩展 |
| `config/index/` | 268 MB | VS Code 索引缓存，可重建 |
| `data/_mnist_src/` | 152 MB | CIFAR-10 演示缺少样本图 |
| `apps/transformer-explainer/build/ort/` | 70 MB | ONNX Runtime wasm，前端另有副本 |

---

## 限制

- 对话与补全使用 1.5B 模型，代码补全与注释可用，复杂推理能力有限
- 单机 CPU 推理，3～5 人并发后响应明显下降
- 所有用户共用同一个 code-server 实例与工作目录，无身份隔离
- 模块 ⑤⑥⑦ 基于开源项目，本仓库提供离线部署、汉化与缺陷修复
- 断网环境下 Google Fonts 与 Streamlit 遥测请求会静默失败，不影响功能
- Spark 由 pip 安装（4.0.4），local 模式，非完整 Hadoop 发行版
- Spark 4.0 默认开启 ANSI 模式，`cast` 遇非法值抛 `CAST_INVALID_INPUT`，课件中已关闭该项

---

## 致谢

- [code-server](https://github.com/coder/code-server) — MIT
- [ConvNetJS](https://github.com/karpathy/convnetjs) — Andrej Karpathy，MIT
- [TensorFlow Playground](https://github.com/tensorflow/playground) — Apache-2.0
- [Transformer Explainer](https://github.com/poloclub/transformer-explainer) — Polo Club of Data Science，MIT
- [MLflow](https://github.com/mlflow/mlflow) · [Streamlit](https://github.com/streamlit/streamlit) · [FastAPI](https://github.com/fastapi/fastapi) · [PySpark](https://github.com/apache/spark) · [Ollama](https://github.com/ollama/ollama)
