# VS Code 与 Jupyter 的差异说明及安装清单

> 面向「AI 教学实训平台」服务器验收场景。本文只回答两个问题：**两者到底差在哪**、**分别要装什么**。

---

## 一、一句话结论

**VS Code 是「以文件为单位」的编辑器，Jupyter 是「以文档为单位」的计算环境。**

这个差异不是界面风格，而是**代码如何执行、变量活多久、成果如何留存**的根本区别。所有其他差异（补全、调试、图表、报告）都是它的下游结果。

---

## 二、本质差异：两种执行模型

### VS Code 的模型：一次性进程

```
按 F5 运行 main.py
   ↓
启动一个全新的 python 进程
   ↓
从头到尾执行完
   ↓
进程退出，内存里所有变量消失
   ↓
再运行一次 = 又一次从零开始
```

**特点**：干净、可复现、可交付。每次运行都是确定的一次。  
**代价**：想"先看看数据长什么样，再决定怎么处理"，就得反复改代码、反复重跑，或者另开一个交互窗口。

### Jupyter 的模型：常驻内核

```
启动 notebook
   ↓
启动一个 python 内核（kernel），一直活着
   ↓
Cell 1 执行：df = pd.read_csv(...)   → df 留在内存
Cell 2 执行：df.head()               → 直接能用 df
Cell 3 执行：model.fit(...)          → 接着用上面训练好的对象
   ↓
内核不关，变量一直留着
```

**特点**：探索式、增量式，适合"跑一步看一步"。  
**代价**：执行顺序会错乱——跳过 Cell 2 直接跑 Cell 3 也能出结果，但结果可能是错的。这是 Jupyter 最著名的坑（"notebook 不可复现"问题的根源）。

**对 AI 实训的影响**：
- 数据清洗、特征工程、调参、看 loss 曲线——这类**探索性工作**天然契合 Jupyter 的模型。
- 需要交付给他人的脚本、需要 CI 的工程代码——天然契合 VS Code。

---

## 三、第二个关键差异：成果如何留存

| | VS Code | Jupyter |
|---|---|---|
| 代码文件 | `.py` 纯代码 | `.ipynb` 代码 + 输出 + 文字混排 |
| 运行结果 | 在终端里滚过去，关掉就没了 | **永久嵌在文档里**，图和表格都在 |
| 实验记录 | 要自己截图、另存日志 | 文档本身就是记录 |
| 导出交付 | 导出代码文件 | **可直接导出 HTML / PDF 实验报告** |

这一点对验收特别重要：**Jupyter 的 `.ipynb` 导出 HTML 后，就是一份带运行结果的实验报告**，可以直接交给验收人员看"学生做了什么、结果如何"。VS Code 做不到这一点。

---

## 四、能力逐项对比（对照七项验收需求）

| 能力 | VS Code | JupyterLab | 说明 |
|---|---|---|---|
| ① 浏览器内编码 | 需 code-server | **原生支持** | JupyterLab 启动即是 Web 服务 |
| ① Python / PyTorch 运行 | ✅ | ✅ | 两者都只是外壳，真正跑的是同一个 Python 解释器 |
| ① **断点调试** | ✅ 强（图形断点、单步、变量监视、条件断点） | ⚠️ 弱（有 Debugger 扩展，体验一般，通常用 `%debug`/pdb） | **VS Code 明显更强** |
| ② 逐字智能补全 | ✅ 强（Continue 插件，Tab 接受，像 Copilot） | ⚠️ 中（Jupyter AI 有 inline completer，需手动触发，不顺滑） | **VS Code 明显更强** |
| ② 整段函数生成 | ✅ | ✅ | 都是调同一个本地模型，效果相同 |
| ② 自动加注释 | ✅（选中代码 `Ctrl+Alt+C`，自动写回） | ✅（`/doc` 命令或 chat） | 效果相当，交互不同 |
| ③ 报错解析 / 修复建议 | ✅（选中报错 `/fix`，或贴 traceback） | ✅（`/fix` + chat 面板） | 效果相当 |
| ④ 全流程实训演示 | ✅ 但要自己搭脚本 | ✅ **原生契合**（逐 cell 走完流程，图留在页面上） | **Jupyter 更合适** |
| ④ 导出实验报告 | ❌ 需截图 | ✅ 导出 HTML | **Jupyter 独有** |
| ⑤ 图表展示（loss 曲线等） | ✅（需交互窗口 / notebook） | ✅ 内联显示 | Jupyter 更自然 |
| 多文件工程管理 | ✅ 强 | ⚠️ 弱（文件树简单） | VS Code 更强 |
| Git 集成 | ✅ 内置图形界面 | ⚠️ 需装扩展，很弱 | VS Code 更强 |
| 内置终端 | ✅ 完整终端 | ✅ 有 Terminal | 都可用 |
| 资源占用（空载） | 约 500 MB–1 GB | 约 200–300 MB | Jupyter 更轻 |

---

## 五、一个容易被忽略的事实：它们不是二选一

**VS Code 装了 Jupyter 扩展后，可以直接打开并运行 `.ipynb`**，支持 cell 执行、变量查看器、内联图表。也就是说：

```
VS Code + Jupyter 扩展  ≈  两者的并集（但只能桌面运行）
```

反过来，**JupyterLab 不能变成 VS Code**——它没有图形调试器、没有完整 Git 界面、没有强补全。

所以真正的选择不是"VS Code 还是 Jupyter"，而是：

| 你的目标 | 应选 |
|---|---|
| 桌面运行，要最强能力 | VS Code + Jupyter 扩展 + Continue（一个窗口覆盖全部） |
| 必须在浏览器里，且机器干净 | JupyterLab + Jupyter AI |
| 必须在浏览器里，且要专业 IDE 观感 | code-server（VS Code 的浏览器版，同样能装 Jupyter 扩展和 Continue） |

> **code-server 的价值就在这**：它让你在浏览器里同时拿到 VS Code 的调试器和 Continue 的补全。代价是它只支持 Linux / Docker / macOS，Windows 原生装不了。

---

## 六、分别要装什么（含安装位置与体积）

### 方案 A：VS Code 桌面版（能力最全）

| # | 组件 | 安装方式 | 安装位置（Windows） | 体积（约） |
|---|---|---|---|---|
| 1 | VS Code 本体 | 官方 `.exe`（用户级安装）或 `winget install Microsoft.VisualStudioCode` | `C:\Users\<用户>\AppData\Local\Programs\Microsoft VS Code` | 400 MB |
| 2 | Python 扩展 | VS Code 扩展市场搜索 `Python`（ms-python.python） | `C:\Users\<用户>\.vscode\extensions` | 30 MB |
| 3 | Jupyter 扩展 | 扩展市场搜索 `Jupyter`（ms-toolsai.jupyter） | 同上 | 100 MB |
| 4 | Pylance | 扩展市场（通常随 Python 扩展自动装） | 同上 | 50 MB |
| 5 | Continue | 扩展市场搜索 `Continue`（continue.continue） | 同上 | 60 MB |
| 6 | Ollama | 官方 `OllamaSetup.exe` | `C:\Users\<用户>\AppData\Local\Programs\Ollama` | 安装后约 1.5 GB |
| 7 | 代码模型 | `ollama pull qwen2.5-coder:7b` | 默认 `C:\Users\<用户>\.ollama\models` | 4.7 GB |
| 8 | Python 环境 | `python -m venv .venv` | 建议 `D:\...\服务器验收\.venv` | — |
| 9 | 依赖包 | `pip install torch torchvision jupyter pandas scikit-learn matplotlib` | 同上 `.venv` | 约 3 GB |

**合计新增磁盘占用：约 10 GB**（其中 PyTorch 和模型占 7 GB 以上）

**额外配置文件**（需手工写）：
- `C:\Users\<用户>\.continue\config.yaml` —— 把 Continue 指向本地 Ollama

---

### 方案 B：JupyterLab（部署最简单）

| # | 组件 | 安装方式 | 安装位置（Windows） | 体积（约） |
|---|---|---|---|---|
| 1 | Python 3.10+ | 系统已有 Python 3.13 | 系统 | — |
| 2 | 虚拟环境 | `python -m venv .venv` | `D:\...\服务器验收\.venv` | — |
| 3 | JupyterLab | `pip install jupyterlab` | 同上 | 120 MB |
| 4 | Jupyter AI | `pip install jupyter-ai` | 同上 | 200 MB（含 langchain 等依赖） |
| 5 | PyTorch (CUDA 12.8) | `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128` | 同上 | 2.5 GB |
| 6 | 数据/绘图库 | `pip install pandas scikit-learn matplotlib` | 同上 | 300 MB |
| 7 | Ollama | 官方 `OllamaSetup.exe` | `C:\Users\<用户>\AppData\Local\Programs\Ollama` | 1.5 GB |
| 8 | 代码模型 | `ollama pull qwen2.5-coder:7b` | `C:\Users\<用户>\.ollama\models` | 4.7 GB |

**合计新增磁盘占用：约 9 GB**

**优势**：第 1–6 步全部是 `pip`，**不需要任何编译工具链、不需要 Docker、不需要管理员权限**（装 Ollama 需要一次 UAC 确认）。

---

### 方案 C：code-server（浏览器里的 VS Code，仅在有 Docker 时）

| # | 组件 | 安装方式 | 安装位置 | 体积（约） |
|---|---|---|---|---|
| 1 | Docker Desktop | 官方安装包（需开启 WSL2 或 Hyper-V） | `C:\Program Files\Docker\Docker` | 1.5 GB |
| 2 | code-server 镜像 | `docker pull codercom/code-server:latest` | WSL2 虚拟磁盘 | 500 MB |
| 3 | 运行容器 | `docker run` | 容器 + 挂载目录 | — |
| 4 | Continue 扩展 | 容器内从 Open VSX 安装 | 容器内 `/home/coder/.local/share/code-server/extensions` | 60 MB |
| 5 | Ollama + 模型 | 同方案 A | 同方案 A | 6.2 GB |

**注意**：code-server 用的是 **Open VSX** 插件市场，不是微软官方市场。Continue、Python、Jupyter 扩展在 Open VSX 上都有，但**部分微软独占扩展（如 Pylance 完整版）不可用**。

---

## 七、针对本次验收的建议

### 如果那台 Win11 服务器有 Docker
**code-server + Continue + Ollama**。理由：浏览器里同时拿到 IDE 观感、逐字补全、图形调试器，需求①②③全部最强状态，且与需求④的 `.ipynb` 也能共存（装 Jupyter 扩展即可）。

### 如果那台 Win11 服务器没有 Docker
**JupyterLab + Jupyter AI + Ollama**。理由：零编译、零依赖冲突、部署风险最低。需求②的补全观感弱一些，可以在演示话术上补：Jupyter AI 的 `/generate` 整段生成效果和 Continue 是同一个模型。

### 折中方案（推荐给两种情况的保底）
桌面用 **VS Code + Jupyter 扩展 + Continue** 做主力开发演示，浏览器用 **JupyterLab** 做"学生端"演示。两者共用同一个 `.venv` 和同一个 Ollama，互不冲突，装的东西不重复。

---

## 八、三个常见误区

**误区 1：Jupyter 只是"能跑代码的网页"**  
不对。Jupyter 的内核是常驻的，这让它具备"增量式建模"能力——训练好的模型对象可以在下一个 cell 直接复用，不需要重新加载。这是 VS Code 跑脚本做不到的。

**误区 2：VS Code 装了 Jupyter 扩展就等于 JupyterLab**  
不等同。VS Code 的 notebook 体验是"模拟"的，不支持 Jupyter AI 的 `%%ai` magic，也不支持 JupyterLab 的部分服务扩展（如 nbgrader 自动判分）。但日常 cell 执行、出图、变量查看完全够用。

**误区 3：Notebook 适合交付生产代码**  
不适合。`.ipynb` 的执行顺序依赖人工操作，无法保证可复现。行业惯例是：**用 notebook 做探索，把结论固化成 `.py` 脚本交付**。验收演示时也要注意，演示前务必 "Restart Kernel & Run All"，确保结果可复现。

---

## 九、附：一句话记住区别

- **VS Code** = 写代码的地方，跑完就忘，适合交付。
- **Jupyter** = 做实验的地方，跑完记着，适合探索。
- **验收演示**：需求①②③靠 VS Code 更出彩，需求④⑤靠 Jupyter 更自然。
