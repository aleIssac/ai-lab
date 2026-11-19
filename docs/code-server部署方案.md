# code-server 部署方案（Windows 11 目标机）

> 适用场景：AI 教学实训平台验收，需求①②③ 通过浏览器内的 VS Code 实现。

---

## 零、必须先接受的事实

**code-server 官方不支持 Windows 原生安装。** 官方支持的平台只有 Linux、macOS、FreeBSD，Windows 需通过 Docker 或源码编译。

本机已实测：`npm install code-server` 在 Windows 上失败两次（v4.23.1 / latest），报错为 `argon2` 的 `node-gyp` 找不到 Visual Studio 编译环境。补齐需安装 VS Build Tools，约 3–5 GB 且极易出问题，**不建议走这条路**。

所以真正可行的是下面三条。

---

## 一、先跑三条命令判断该走哪条

在目标 Win11 服务器上打开 PowerShell：

```powershell
wsl --status          # 是否已装 WSL2
docker --version      # 是否已装 Docker
systeminfo | findstr /C:"OS 名称" /C:"OS Name"
```

| 结果 | 走哪条 |
|---|---|
| 有 Docker | **路线 A**（最省事，镜像预构建好） |
| 有 WSL2 但没 Docker | **路线 B**（直接装 Linux 版 code-server） |
| 都没有，但能上外网 | **路线 C**（VS Code 官方 tunnel，零容器） |
| 都没有，且是内网 | 先装 WSL2，再走 A 或 B |

---

## 二、路线 A：Docker Desktop + code-server（推荐）

### 为什么推荐
- 官方镜像 `codercom/code-server` 已预构建，**零编译风险**
- 环境完全隔离，弄坏了删容器重来
- 可自定义 Dockerfile 预装 PyTorch，验收时不用现场等 pip

### 步骤

**1. 装 WSL2（Docker Desktop 的前置）**

```powershell
wsl --install
```

装完必须**重启电脑**。验证：`wsl --status` 显示默认版本 2。

> Win11 家庭版也支持 WSL2，不需要 Hyper-V。

**2. 装 Docker Desktop**

官方安装包约 1.5 GB，安装位置 `C:\Program Files\Docker\Docker`。安装时勾选 "Use WSL 2 based engine"。

**3. 写 Dockerfile（预装 Python 环境）**

在项目目录建 `docker/Dockerfile`：

```dockerfile
FROM codercom/code-server:latest
USER root

# 系统依赖：Python 3 + venv
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv curl \
 && rm -rf /var/lib/apt/lists/*

# 独立虚拟环境，避免污染系统 Python
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# PyTorch 用 CPU 版：约 200 MB，演示够用，比 CUDA 版小 10 倍
RUN pip install --no-cache-dir torch torchvision \
      --index-url https://download.pytorch.org/whl/cpu

# 实训所需依赖
RUN pip install --no-cache-dir \
      pandas numpy scikit-learn matplotlib \
      jupyter mlflow fastapi uvicorn streamlit

USER coder
```

**4. 构建镜像**

```bash
cd D:\...\服务器验收
docker build -t ai-lab:1.0 -f docker/Dockerfile .
```

首次构建约 5–8 分钟，产物约 3.5 GB。

**5. 启动容器**

```bash
docker run -d --name ai-lab ^
  -p 8080:8080 ^
  -p 5001:5001 ^
  -p 8501:8501 ^
  -e PASSWORD=your-password ^
  -v "D:\Zeko\Documents\WorkBuddy\服务器验收:/home/coder/project" ^
  -v ai-lab-ext:/home/coder/.local \
  ai-lab:1.0 --bind-addr 0.0.0.0:8080 /home/coder/project
```

**6. 浏览器打开 `http://localhost:8080`**，输入密码。

---

## 三、路线 B：WSL2 + Linux 版 code-server（不装 Docker）

### 适用
不想装 Docker，或 Docker Desktop 授权/性能有问题。

### 步骤

```powershell
wsl --install -d Ubuntu        # 装完重启
```

进入 Ubuntu 后：

```bash
# 官方一键安装脚本
curl -fsSL https://code-server.dev/install.sh | sudo sh

# 设置密码与端口
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml <<'EOF'
bind-addr: 0.0.0.0:8080
auth: password
password: your-password
cert: false
EOF

# 启动（后台常驻）
sudo systemctl enable --now code-server@$USER
```

Windows 浏览器访问 `http://localhost:8080`（WSL2 会自动转发 localhost）。

### 优势
- 比 Docker 轻（省约 1.5 GB）
- **可以直接用 GPU**：WSL2 里装 CUDA 版 PyTorch，能调用 RTX 5060 Ti

### 注意
- WSL2 的 Python 是 Linux 版，装包用 `pip`，与 Windows Python 互不影响
- 项目文件放在 `/mnt/d/...` 下，跨文件系统 IO 较慢，建议把项目复制到 WSL 内部 `~/project`，演示更流畅

---

## 四、路线 C：VS Code 官方 Tunnel（零容器，但必须联网）

### 适用
目标机能上外网，且不想装 Docker/WSL2。

### 步骤

```powershell
# 1. 装 VS Code 桌面版（约 400 MB）
# 2. 在终端执行：
code tunnel
# 3. 按提示用 Microsoft 或 GitHub 账号登录
# 4. 得到形如 https://vscode.dev/tunnel/xxxx 的地址
```

浏览器打开那个地址，就是**微软官方的 VS Code Web**。

### 优势
- 官方支持，**扩展最全**（Pylance、Jupyter 完整版都能装，Open VSX 上没有的也能用）
- 零容器、零编译

### 致命限制
- **必须联网 + 微软账号**。内网验收环境直接不可用
- 流量走微软服务器中转，代码会经过外部

> 如果验收是内网环境，这条路不能作为主方案，最多作为备用。

---

## 五、code-server 内部配置

### 5.1 装扩展（关键）

code-server 用的是 **Open VSX** 市场，不是微软市场。打开侧边栏扩展面板，搜索安装：

| 扩展 | 用途 | Open VSX 可用 |
|---|---|---|
| `Python`（ms-python.python） | 语言支持、调试器 | ✅ |
| `Jupyter`（ms-toolsai.jupyter） | 打开 .ipynb | ✅ |
| `Continue`（continue.continue） | AI 补全 + 对话 | ✅ |
| `Pylance` | 类型检查 | ⚠️ 功能受限（微软独占协议） |

> 如果 Pylance 装不上，用 `Python` 扩展自带的 jedi 补全，功能够演示。

### 5.2 配置 Continue 连接模型

在 code-server 里按 `Ctrl+Shift+P` → 输入 `Continue: Open Config`，或点 Continue 面板右下角的齿轮，会打开配置文件（通常 `~/.continue/config.yaml`）。

**方案一：纯云端 API（
最省事）**

```yaml
name: api-backend
version: 1.0.0
schema: v1
models:
  - name: DeepSeek Chat
    provider: deepseek
    model: deepseek-chat
    apiKey: sk-xxxxxxxx
    roles: [chat, edit, apply]
  - name: 补全模型
    provider: openai
    model: qwen2.5-coder-32b-instruct
    apiBase: https://dashscope.aliyuncs.com/compatible-mode/v1
    apiKey: sk-xxxxxxxx
    roles: [autocomplete]
```

**方案二：纯本地 Ollama**

```yaml
name: local-ollama
version: 1.0.0
schema: v1
models:
  - name: Qwen2.5 Coder 7B
    provider: ollama
    model: qwen2.5-coder:7b
    apiBase: http://host.docker.internal:11434   # Docker 内访问宿主
    roles: [chat, edit, apply, autocomplete]
    defaultCompletionOptions:
      contextLength: 8192
```

> **Docker 内的地址必须写 `host.docker.internal`，写 `localhost` 会连不上**——这是最常见的坑。

**方案三：混合（推荐）**

```yaml
models:
  - name: Claude（对话/诊断）
    provider: anthropic
    model: claude-sonnet-4-5
    apiKey: sk-ant-xxxxx
    roles: [chat, edit, apply]
  - name: 本地补全
    provider: ollama
    model: qwen2.5-coder:1.5b
    apiBase: http://host.docker.internal:11434
    roles: [autocomplete]
```

补全走本地小模型（快、免费），对话走云端（强）。断网时至少补全还能用。

### 5.3 选 Python 解释器

`Ctrl+Shift+P` → `Python: Select Interpreter` → 选 `/opt/venv/bin/python`。

---

## 六、端口规划（容易漏）

| 服务 | 端口 | 是否需映射出容器 |
|---|---|---|
| code-server | 8080 | ✅ 必须 |
| MLflow UI | 5001 | ✅ 需求④演示用 |
| Streamlit | 8501 | ✅ 需求④演示用 |
| Ollama | 11434 | ❌ 容器内走 `host.docker.internal` |

> Windows 上 **5000 端口常被 Hyper-V 保留**，MLflow 用 5001 更稳。

---

## 七、验收演示：在 code-server 里走完七条需求

| 需求 | 演示动作 | 时长 |
|---|---|---|
| ① 编码调试 | 打开 `mnist_train.py`，下断点，F5 调试，看变量面板 | 1 min |
| ① 数据预处理 | 打开 `.ipynb`，逐 cell 跑 pandas 清洗 | 1 min |
| ② 智能补全 | 输入 `def train_` 停住 → Tab 接受补全 | 30 s |
| ② 函数生成 | 注释写"写一个加载 MNIST 的 DataLoader" → 触发补全 | 30 s |
| ② 加注释 | 选中整个函数 → `Ctrl+Alt+C`（自研扩展，自动写回文件） | 10 s |
| ③ 报错诊断 | 故意制造维度不匹配，把 traceback 贴进 Continue → `/fix` | 1.5 min |
| ④ 全流程 | 终端跑 `python src/train.py` → 打开 MLflow UI 看实验 | 2 min |
| ④ 部署发布 | 打开 Streamlit 页面交互预测 | 1 min |
| ⑤~⑦ | 切到 playground / transformer-explainer / 可视化实验（另开标签页） | 3 min |

**演示前必做**：`Restart Kernel & Run All` 跑一遍，确认所有输出都是真的。

---

## 八、常见坑（按踩到概率排序）

| 坑 | 现象 | 解法 |
|---|---|---|
| Ollama 地址写成 localhost | Continue 报连接失败 | 容器内必须用 `host.docker.internal:11434` |
| 端口没映射 | 浏览器打不开 MLflow | `docker run` 时补 `-p 5001:5001` |
| Windows 5000 端口被占 | MLflow 启动失败 | 改用 5001 |
| 扩展装不上 | Open VSX 搜不到 Pylance | 用 Python 扩展自带补全，不影响演示 |
| 容器重启后扩展丢失 | 扩展没了 | 挂载 `-v ai-lab-ext:/home/coder/.local` 持久化 |
| CUDA 版 PyTorch 太大 | 镜像 8 GB+，构建慢 | **用 CPU 版**，演示场景完全够 |
| 项目挂载在 `D:\` 下 IO 慢 | 文件操作卡顿 | 常规可接受；WSL2 方案建议放 `~/project` |

---

## 九、体积汇总

| 项目 | 体积 |
|---|---|
| Docker Desktop | 1.5 GB |
| WSL2 Ubuntu | 1.5 GB |
| code-server 镜像（含 Python + CPU 版 PyTorch） | 3.5 GB |
| Ollama + qwen2.5-coder:7b（可选） | 6.2 GB |
| 项目数据与课程文件 | < 1 GB |

**合计约 12.7 GB**（不装本地模型则约 6.5 GB）。

---

## 十、结论

- **内网验收机** → 路线 A（Docker），最稳
- **想省 1.5 GB 且要 GPU** → 路线 B（WSL2 直装）
- **联网环境、追求零部署** → 路线 C（官方 tunnel），但不可用于内网

三条路里，**只有 A 和 B 是 code-server 本体**；C 是微软官方的同类能力，效果等价但不算 code-server。

---

## 十一、当前采用的方案（路线 A + 纯 API）

> 目标机可上外网、大模型走云端 API，因此**不安装 Ollama，不占用显卡，省 6.2 GB**。

### 11.1 已生成的文件

| 文件 | 作用 |
|---|---|
| `docker/Dockerfile` | 自定义镜像：code-server + Python venv + CPU 版 PyTorch + 数据科学栈 + MLflow/FastAPI/Streamlit |
| `docker-compose.yml` | 一键启动配置，含端口映射、卷挂载、密码 |
| `config/config.yaml` | Continue 的模型配置（**需要填 API Key**），同时约定中文回答与报错诊断规则 |
| `.dockerignore` | 避免把大文件传给构建上下文 |
| `start.bat` / `stop.bat` | 一键启停（纯 ASCII，无路径编码风险） |

### 11.2 三步启动

```powershell
# 1. 填 Key（关键，不填则 AI 功能不可用）
notepad config\config.yaml
#    把 sk-REPLACE_WITH_YOUR_DEEPSEEK_KEY 换成真实 Key

# 2. 一键启动（首次构建约 5-8 分钟）
.\start.bat

# 3. 浏览器打开
#    http://localhost:8080    密码 ai-lab-2026
```

### 11.3 首次进入 code-server 后要做的事

1. 扩展面板安装：`Python`、`Jupyter`、`Continue`（Open VSX 市场）
2. `Ctrl+Shift+P` → `Python: Select Interpreter` → 选 `/opt/venv/bin/python`
3. Continue 面板应该已经读到 `config/config.yaml`，发一句话验证连通

### 11.4 可选：打开大数据 / 大模型专项

`docker-compose.yml` 里改 `build.args`：

```yaml
      args:
        WITH_BIGDATA: "true"    # 装 JDK 17 + PySpark（约 +800 MB）
        WITH_LLM_APP: "true"    # 装 LangChain + Chroma（约 +1.2 GB）
```

改完重新 `.\start.bat` 即可（会重建镜像）。

### 11.5 体积（纯 API 版）

| 项目 | 体积 |
|---|---|
| Docker Desktop | 1.5 GB |
| WSL2 Ubuntu（Docker 前置） | 1.5 GB |
| `ai-lab:1.0` 镜像 | 约 3.2 GB |
| 项目文件 | < 1 GB |
| **合计** | **约 6.2 GB** |

对比装本地 Ollama 的 12.7 GB，省了一半。

### 11.6 API 方案的两个风险与应对

| 风险 | 应对 |
|---|---|
| 现场断网 / Key 限额 | 提前测通；准备第二个 Key；演示前把关键结果先跑一遍存图 |
| 验收方追问"模型部署在哪" | 如实说明调用云端 API。若担心这一问，可临时补装 `qwen2.5-coder:1.5b`（仅 1 GB），既做补全兜底，也能答"本地也部署了小模型" |

### 11.7 推荐的模型组合

| 角色 | 推荐 | 说明 |
|---|---|---|
| 对话 / 报错诊断（chat） | `deepseek-chat` | 中文好、代码强、便宜 |
| 代码补全（autocomplete） | `deepseek-chat` 或 SiliconFlow 的 `Qwen2.5-Coder-7B` | 补全请求量大，选便宜的；质量不满意再换 FIM 专用模型 |

> 若补全响应偏慢，可在 Continue 面板把 autocomplete 关掉，只保留对话功能——演示需求②仍可用"整段生成"体现。

### 11.8 离线迁移（可选）

如果之后需要把环境搬到无外网的机器：

```bash
# 在有网的机器上
docker save -o ai-lab.tar ai-lab:1.0

# 拷到目标机后
docker load -i ai-lab.tar
docker compose up -d          # 不再触发 build
```
