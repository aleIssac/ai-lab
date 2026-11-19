/**
 * AI Lab Tab 补全 —— 直接调用本地 Ollama 的 FIM 接口，返回内联幽灵文本。
 *
 * 为什么不用 Continue 的补全：Continue 2.1.0 在这个 code-server（VS Code 1.141）
 * 里能收到模型返回的 token，但最终 completion 恒为空，幽灵文本永不渲染。
 * 本扩展自己做 FIM 拼装和请求，链路短、可控、离线。
 */

const vscode = require("vscode");

const PREFIX_MAX_CHARS = 2000; // 往前取多少字符做前缀
const SUFFIX_MAX_CHARS = 500; // 往后取多少字符做后缀

let currentAbort = null; // 上一次请求的 AbortController
let lastRequestAt = 0;

function cfg() {
  const c = vscode.workspace.getConfiguration("ailabAutocomplete");
  return {
    enabled: c.get("enabled", true),
    endpoint: c.get("endpoint", "http://localhost:11435/api/generate"),
    model: c.get("model", "qwen-coder-fim"),
    maxTokens: c.get("maxTokens", 32),
    debounceMs: c.get("debounceMs", 250),
    timeoutMs: c.get("timeoutMs", 8000),
    // 注释生成走 chat 模板，必须直连 ollama（11435 代理会强制 raw:true，套不上模板）
    commentEndpoint: c.get("commentEndpoint", "http://ollama:11434/api/generate"),
    commentModel: c.get("commentModel", "qwen2.5-coder:1.5b"),
    commentMaxTokens: c.get("commentMaxTokens", 512),
    commentTimeoutMs: c.get("commentTimeoutMs", 120000),
  };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** 用 Qwen2.5-Coder 的 FIM 格式拼提示词 */
function buildPrompt(document, position) {
  const offset = document.offsetAt(position);
  const text = document.getText();
  const prefix = text.slice(Math.max(0, offset - PREFIX_MAX_CHARS), offset);
  const suffix = text.slice(offset, offset + SUFFIX_MAX_CHARS);
  return `<|fim_prefix|>${prefix}<|fim_suffix|>${suffix}<|fim_middle|>`;
}

/** 调 Ollama 拿补全（非流式，一次性返回） */
async function requestCompletion(prompt, signal, options) {
  const body = JSON.stringify({
    model: options.model,
    prompt,
    raw: true, // 关键：不让 Ollama 套 chat 模板，否则 FIM 标记失效
    stream: false,
    options: {
      temperature: 0.2,
      num_predict: options.maxTokens,
      stop: ["<|fim_pad|>", "<|fim_suffix|>", "<|fim_middle|>", "<|endoftext|>", "<|file_sep|>"],
    },
  });

  const resp = await fetch(options.endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    signal,
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  const data = await resp.json();
  return data.response || "";
}

/** 过滤明显没用的补全 */
function sanitize(text, document, position) {
  if (!text) return "";
  // 去掉模型偶尔吐出的 FIM 残留标记
  let out = text
    .replace(/<\|?fim_[a-z]+\|?>/g, "")
    .replace(/^```[a-zA-Z]*\n?/, "");

  // 纯空白不要
  if (!out.trim()) return "";

  // 补全内容如果就是光标后已有的文本，说明是复读，丢掉
  const line = document.lineAt(position.line).text;
  const restOfLine = line.slice(position.character);
  if (restOfLine && out.startsWith(restOfLine)) return "";

  // 单行内重复整行也要丢
  const above = position.line > 0 ? document.lineAt(position.line - 1).text.trim() : "";
  if (above && out.trim() === above) return "";

  // 关键：模型补完函数体后常会继续往下编新的顶层语句。
  // 遇到「空行 + 下一行顶格」就截断，只保留当前这个代码块的补全。
  const lines = out.split("\n");
  const kept = [];
  for (let i = 0; i < lines.length; i += 1) {
    const cur = lines[i];
    const next = lines[i + 1];
    if (kept.length > 0 && cur.trim() === "" && next !== undefined && next.trim() !== "" && !/^\s/.test(next)) {
      break;
    }
    kept.push(cur);
    if (kept.length >= 10) break;
  }
  out = kept.join("\n");

  // 收尾的空行去掉
  return out.replace(/\s+$/, "");
}

/**
 * 计算补全替换的范围。
 *
 * 坑：输入 `def avg(` 时 VS Code 会自动补一个 `)`，而模型给的补全里已经带了 `)`
 * （`x, y):\n    return (x + y) / 2`）。直接插会留下一个多余的右括号。
 * 这里如果光标后面正好是一个闭合括号，并且补全里也包含它，就把它一起替换掉。
 *
 * 注意：不能用 InlineCompletionItem.completeBracketPairs = true ——
 * 在本机 VS Code 1.141 上加了它补全就完全不渲染了（实测 ghost 节点数 8 → 0）。
 */
function completionRange(position, text, document) {
  const rest = document.lineAt(position.line).text.slice(position.character);
  const closers = [")", "]", "}"];
  if (rest.length > 0 && closers.includes(rest[0]) && text.includes(rest[0])) {
    return new vscode.Range(position, position.translate(0, 1));
  }
  return new vscode.Range(position, position);
}

// ============================================================
//  注释自动添加：选中代码（或光标所在函数）-> 一条命令 -> 写回文件
//  与补全的区别：这里必须用 chat 模板（不给 raw），所以直连 ollama 11434
// ============================================================

async function requestChat(prompt, options) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.commentTimeoutMs);
  try {
    const resp = await fetch(options.commentEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: options.commentModel,
        prompt,
        stream: false,
        options: { temperature: 0.2, num_predict: options.commentMaxTokens },
      }),
      signal: controller.signal,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return data.response || "";
  } finally {
    clearTimeout(timer);
  }
}

function buildCommentPrompt(code, langId) {
  const isPy = langId === "python";
  const hash = isPy ? "#" : "//";
  const docRule = isPy
    ? "3. 函数/类上方用三引号写文档字符串：一句话说明作用，再写 Args 和 Returns。"
    : "3. 函数上方用块注释写作用、参数和返回值。";
  return [
    `你是代码注释助手。请给下面这段 ${langId} 代码添加简体中文注释。`,
    "",
    "要求：",
    "1. 只输出加了注释后的完整代码，不要任何解释，不要用 markdown 代码块包裹。",
    "2. 代码逻辑、缩进、空行都不要改，只增加注释行。",
    docRule,
    `4. 关键语句上方加一行 ${hash} 注释说明意图。`,
    "5. 已有注释保留，不要删除。",
    "",
    "代码：",
    code,
  ].join("\n");
}

/** 去掉 markdown 围栏和开头可能出现的客套话 */
function extractCode(text, original) {
  if (!text) return "";
  let out = text.replace(/\r\n/g, "\n").trim();
  const fence = out.match(/```[a-zA-Z0-9_+-]*\n([\s\S]*?)```/);
  if (fence) {
    out = fence[1];
  } else {
    out = out.replace(/^```[a-zA-Z0-9_+-]*\n?/, "").replace(/\n?```$/, "");
  }
  // 丢掉开头 3 行以内的说明性文字（既不在原文里，也不是注释/装饰器）
  const lines = out.split("\n");
  let i = 0;
  while (i < lines.length && i < 3) {
    const t = lines[i].trim();
    if (!t) { i += 1; continue; }
    if (original.includes(t) || /^(#|\/\/|"""|'''|@)/.test(t)) break;
    i += 1;
  }
  return lines.slice(i).join("\n").replace(/\s+$/, "");
}

/** 校验模型输出没有把代码改坏 */
function validate(original, candidate) {
  if (!candidate.trim()) return "模型返回空内容";
  const codeLines = original
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"));
  if (codeLines.length === 0) return null;
  let hit = 0;
  for (const l of codeLines) if (candidate.includes(l)) hit += 1;
  const ratio = hit / codeLines.length;
  if (ratio < 0.6) return `代码内容和原文对不上（保留率 ${Math.round(ratio * 100)}%），已放弃`;
  if (candidate.split("\n").length < original.split("\n").length) {
    return "输出行数比原文少，可能丢了代码，已放弃";
  }
  return null;
}

/** 没选中时：把光标所在的 def/class 整块找出来（Python 缩进规则） */
function enclosingBlock(doc, lineIdx) {
  const indentOf = (i) => (doc.lineAt(i).text.match(/^[ \t]*/) || [""])[0].length;
  let start = 0;
  for (let i = lineIdx; i >= 0; i -= 1) {
    if (/^\s*(async\s+)?(def|class)\s/.test(doc.lineAt(i).text)) {
      start = i;
      break;
    }
  }
  while (start > 0 && /^\s*@/.test(doc.lineAt(start - 1).text)) start -= 1;
  const base = indentOf(start);
  let end = start;
  for (let i = start + 1; i < doc.lineCount; i += 1) {
    const t = doc.lineAt(i).text;
    if (t.trim() === "") { end = i; continue; }
    if (indentOf(i) <= base) break;
    end = i;
  }
  while (end > start && doc.lineAt(end).text.trim() === "") end -= 1;
  return [start, end];
}

/** 整个文件里的顶层函数/类，从下往上返回，便于逆序改写 */
function topLevelBlocks(doc) {
  const indentOf = (i) => (doc.lineAt(i).text.match(/^[ \t]*/) || [""])[0].length;
  const blocks = [];
  for (let i = 0; i < doc.lineCount; i += 1) {
    if (!/^(async\s+)?(def|class)\s/.test(doc.lineAt(i).text)) continue;
    let start = i;
    while (start > 0 && /^\s*@/.test(doc.lineAt(start - 1).text)) start -= 1;
    let end = i;
    for (let j = i + 1; j < doc.lineCount; j += 1) {
      const t = doc.lineAt(j).text;
      if (t.trim() === "") { end = j; continue; }
      if (indentOf(j) === 0) break;
      end = j;
    }
    while (end > start && doc.lineAt(end).text.trim() === "") end -= 1;
    blocks.push({ start, end });
    i = end;
  }
  return blocks;
}

/** 给 [startLine, endLine] 这段代码加注释并写回文件 */
async function commentBlock(editor, startLine, endLine) {
  const doc = editor.document;
  const eol = doc.eol === vscode.EndOfLine.CRLF ? "\r\n" : "\n";
  const startPos = new vscode.Position(startLine, 0);
  const endPos = new vscode.Position(endLine, doc.lineAt(endLine).text.length);
  const range = new vscode.Range(startPos, endPos);
  const original = doc.getText(range);

  const options = cfg();
  const prompt = buildCommentPrompt(original, doc.languageId);
  const raw = await requestChat(prompt, options);
  const code = extractCode(raw, original);
  console.log(`[AI Lab 注释] rawLen=${raw.length} codeLen=${code.length}`);

  const bad = validate(original, code);
  if (bad) throw new Error(bad);

  const text = code.split("\n").join(eol);
  const edit = new vscode.WorkspaceEdit();
  edit.replace(doc.uri, range, text);
  const ok = await vscode.workspace.applyEdit(edit);
  if (!ok) throw new Error("写回文件失败");
  return text.length;
}

// ============================================================
//  报错诊断：选区 / 剪贴板 / 编辑器诊断 -> 四段式定位 + 修复代码
// ============================================================

function buildDiagnosePrompt(traceback, code, fileName) {
  return [
    "你是 PyTorch 助教，帮学生诊断报错。严格按下面四段输出，不要寒暄、不要反问。",
    "",
    "输出格式：",
    "【类型】维度不匹配 / 设备不一致 / 梯度爆炸 / 其他（选一个，可加半句说明）",
    "【定位】第几行、哪个变量、具体形状或数值，为什么错",
    "【修复】给出可运行的修复代码（代码块），不要长篇解释",
    "【优化】一句话，怎么从写法上避免这类错误",
    "",
    "判据（先按报错关键词归类）：",
    "- 出现 shapes cannot be multiplied / size mismatch / mat1 和 mat2 → 维度不匹配",
    "- 出现 same device / cuda / cpu → 设备不一致",
    "- 出现 nan / inf / overflow，或 loss 变成 nan、梯度越来越大 → 梯度爆炸",
    "",
    "各类型典型修复方向：",
    "- 维度不匹配：调整 reshape/permute 或构造数据的形状参数，让矩阵乘两侧对齐",
    "- 设备不一致：把模型、输入、标签、损失函数统一 .to(device)",
    "- 梯度爆炸：降低学习率、输入标准化、加 clip_grad_norm_、检查 zero_grad",
    "",
    "重要：",
    "- 修复代码要保持模型输出与标签形状一致（标签常是 (N,) 或 (N,1)），不要为了消除报错去改标签形状",
    "",
    "要求：",
    "- 行号、形状必须取自下面的报错原文和代码，不要编造",
    "- 修复代码必须真的能跑通，不能只是把原代码重复一遍",
    "- 信息不足就在【定位】里说明缺什么，不要猜",
    "",
    "示例：",
    "报错：RuntimeError: mat1 and mat2 shapes cannot be multiplied (3x4 and 3x5)，位置 z = x @ y",
    "【类型】维度不匹配",
    "【定位】z = x @ y，x 是 (3,4)，y 是 (3,5)，左矩阵列数 4 与右矩阵行数 3 不一致",
    "【修复】",
    "```python",
    "y = torch.randn(4, 5)",
    "z = x @ y",
    "```",
    "【优化】矩阵相乘前用 assert x.shape[1] == y.shape[0] 拦住这类错误",
    "",
    "--- 下面是学生的实际情况 ---",
    "报错原文：",
    traceback,
    "",
    `相关代码（${fileName}）：`,
    code,
  ].join("\n");
}

/** 取当前文件的一段代码：文件不长就整份，长就取光标附近 */
function codeContext(doc, lineIdx) {
  const total = doc.lineCount;
  if (total <= 150) return { text: doc.getText(), note: `共 ${total} 行` };
  const from = Math.max(0, lineIdx - 60);
  const to = Math.min(total - 1, lineIdx + 60);
  return {
    text: doc.getText(new vscode.Range(new vscode.Position(from, 0), new vscode.Position(to, doc.lineAt(to).text.length))),
    note: `第 ${from + 1}-${to + 1} 行，共 ${total} 行`,
  };
}

/** 报错来源：选区 > 剪贴板 > 编辑器诊断 */
async function getErrorMaterial(editor) {
  if (editor && !editor.selection.isEmpty) {
    return { text: editor.document.getText(editor.selection), from: "编辑器中选中的内容" };
  }
  // 浏览器里读剪贴板需要权限，失败就跳过（否则整个命令会静默挂掉）
  let clip = "";
  try {
    clip = await vscode.env.clipboard.readText();
  } catch (err) {
    console.log(`[AI Lab 诊断] 读剪贴板失败（多半是浏览器权限），跳过: ${err && err.message}`);
  }
  if (clip && /Traceback|Error|Exception|error:|Error:/.test(clip)) {
    return { text: clip.trim().slice(0, 4000), from: "剪贴板" };
  }
  if (editor) {
    const diags = vscode.languages.getDiagnostics(editor.document.uri);
    const errs = diags.filter((d) => d.severity === vscode.DiagnosticSeverity.Error);
    if (errs.length) {
      const text = errs
        .map((d) => `${editor.document.uri.fsPath}:${d.range.start.line + 1}: ${d.message}`)
        .join("\n");
      return { text, from: "编辑器错误诊断" };
    }
  }
  return null;
}

/** 把诊断结果开在一个新的 Markdown 标签页里，不动正在编辑的文件 */
async function showDiagnosisReport(userText, from, elapsed, modelName) {
  const content = [
    "# 报错诊断",
    "",
    `> 模型 ${modelName} · 耗时 ${(elapsed / 1000).toFixed(1)}s · 来源：${from}`,
    "",
    userText.trim(),
    "",
    "---",
    "",
    "> 本地 1.5B 模型生成，结论仅供参考：修复代码建议先跑一次验证，形状类问题可对照报错原文核对行号。",
    "",
  ].join("\n");
  const doc = await vscode.workspace.openTextDocument({ content, language: "markdown" });
  await vscode.window.showTextDocument(doc, {
    viewColumn: vscode.ViewColumn.Beside,
    preview: false,
    preserveFocus: true,
  });
}

function activate(context) {
  console.log("[AI Lab 补全] 已激活");

  // 预热：容器刚起来时模型是冷的（首次请求 6 秒以上，会错过补全窗口）。
  // 代理可能比扩展晚启动，所以失败就重试，直到成功一次为止。
  let warmTries = 0;
  const warm = () => {
    const o = cfg();
    requestCompletion("<|fim_prefix|>x = 1<|fim_suffix|><|fim_middle|>", undefined, {
      ...o,
      maxTokens: 1,
      timeoutMs: 60000,
    })
      .then((t) => console.log(`[AI Lab 补全] 模型预热完成（第 ${warmTries + 1} 次尝试）`))
      .catch((e) => {
        warmTries += 1;
        if (warmTries < 20) {
          setTimeout(warm, 5000);
        } else {
          console.log(`[AI Lab 补全] 预热放弃（不影响手动使用）: ${e}`);
        }
      });
  };
  warm();

  const provider = {
    async provideInlineCompletionItems(document, position, ctx, token) {
      const options = cfg();
      if (!options.enabled) return undefined;

      // 只在真实输入时触发，Ctrl+Space 手动触发也放行
      const manually = ctx.triggerKind === vscode.InlineCompletionTriggerKind.Invoke;

      // 防抖：新输入到来时先等一会儿，让用户的连击合并成一次请求
      if (!manually && options.debounceMs > 0) {
        await sleep(options.debounceMs);
        if (token.isCancellationRequested) return undefined;
      }

      // 取消上一次还在飞的请求
      if (currentAbort) currentAbort.abort();
      const controller = new AbortController();
      currentAbort = controller;
      const cancelSub = token.onCancellationRequested(() => controller.abort());

      const timeout = setTimeout(() => controller.abort(), options.timeoutMs);
      lastRequestAt = Date.now();

      try {
        const prompt = buildPrompt(document, position);
        const raw = await requestCompletion(prompt, controller.signal, options);
        const text = sanitize(raw, document, position);
        console.log(`[AI Lab 补全] raw=${JSON.stringify(raw.slice(0, 60))} clean=${JSON.stringify(text.slice(0, 60))} canceled=${token.isCancellationRequested}`);
        if (!text) return undefined;
        const item = new vscode.InlineCompletionItem(text, completionRange(position, text, document));
        console.log("[AI Lab 补全] 返回 1 条补全");
        return [item];
      } catch (err) {
        if (String(err && err.name) !== "AbortError") {
          console.log(`[AI Lab 补全] 请求失败: ${err}`);
        }
        return undefined;
      } finally {
        clearTimeout(timeout);
        cancelSub.dispose();
      }
    },
  };

  context.subscriptions.push(
    vscode.languages.registerInlineCompletionItemProvider({ pattern: "**" }, provider)
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ailabAutocomplete.test", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("先打开一个文件");
        return;
      }
      const options = cfg();
      const prompt = buildPrompt(editor.document, editor.selection.active);
      const t0 = Date.now();
      try {
        const text = await requestCompletion(prompt, undefined, options);
        vscode.window.showInformationMessage(
          `补全耗时 ${Date.now() - t0}ms：${JSON.stringify(text.slice(0, 80))}`
        );
      } catch (err) {
        vscode.window.showErrorMessage(`补全失败：${err}`);
      }
    })
  );

  // ---- 给选中代码（或光标所在函数）加注释 ----
  context.subscriptions.push(
    vscode.commands.registerCommand("ailab.addComment", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("先打开一个文件");
        return;
      }
      let startLine;
      let endLine;
      if (!editor.selection.isEmpty) {
        startLine = editor.selection.start.line;
        endLine = editor.selection.end.line;
        if (editor.selection.end.character === 0 && endLine > startLine) endLine -= 1;
      } else {
        [startLine, endLine] = enclosingBlock(editor.document, editor.selection.active.line);
      }
      const label = `第 ${startLine + 1}-${endLine + 1} 行`;
      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: `AI 正在给${label}加注释…` },
        async () => {
          const t0 = Date.now();
          try {
            await commentBlock(editor, startLine, endLine);
            vscode.window.showInformationMessage(`已加注释（${label}，${Date.now() - t0}ms）`);
          } catch (err) {
            vscode.window.showErrorMessage(`加注释失败：${err.message}`);
          }
        }
      );
    })
  );

  // ---- 整个文件的所有顶层函数逐个加注释 ----
  context.subscriptions.push(
    vscode.commands.registerCommand("ailab.addCommentFile", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("先打开一个文件");
        return;
      }
      const blocks = topLevelBlocks(editor.document);
      if (blocks.length === 0) {
        vscode.window.showWarningMessage("没找到顶层函数或类（只支持 def / class）");
        return;
      }
      let done = 0;
      let failed = 0;
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "AI 正在给整个文件加注释…",
          cancellable: false,
        },
        async (progress) => {
          // 从下往上处理，避免行号漂移
          for (let i = blocks.length - 1; i >= 0; i -= 1) {
            const b = blocks[i];
            progress.report({
              message: `${done + failed + 1}/${blocks.length}`,
              increment: 100 / blocks.length,
            });
            try {
              await commentBlock(editor, b.start, b.end);
              done += 1;
            } catch (err) {
              failed += 1;
              console.log(`[AI Lab 注释] 第 ${b.start + 1} 行失败: ${err.message}`);
            }
          }
        }
      );
      const msg = `加注释完成：成功 ${done} 个${failed ? `，失败 ${failed} 个` : ""}`;
      if (failed) vscode.window.showWarningMessage(msg);
      else vscode.window.showInformationMessage(msg);
    })
  );

  // ---- 报错诊断：选区 / 剪贴板 / 编辑器诊断 -> 四段式报告 ----
  context.subscriptions.push(
    vscode.commands.registerCommand("ailab.diagnose", async () => {
      const editor = vscode.window.activeTextEditor;
      const options = cfg();
      const material = await getErrorMaterial(editor);
      if (!material) {
        vscode.window.showWarningMessage(
          "没找到报错信息：先在编辑器里选中 traceback，或把报错复制到剪贴板"
        );
        return;
      }
      const fileName = editor ? editor.document.fileName.split(/[\\/]/).pop() : "(无文件)";
      const ctx = editor
        ? codeContext(editor.document, editor.selection.active.line)
        : { text: "", note: "" };
      const prompt = buildDiagnosePrompt(
        material.text,
        ctx.text || "(没有可用的代码上下文)",
        `${fileName}，${ctx.note}`
      );

      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: `AI 正在诊断（来源：${material.from}）…` },
        async () => {
          const t0 = Date.now();
          try {
            const raw = await requestChat(prompt, options);
            // 直接把模型原话整理后展示（不需要剥 markdown 围栏，报告本身就是 md）
            const body = raw.replace(/^```[a-zA-Z0-9_+-]*\n?/, "").trim();
            if (!body) throw new Error("模型返回空内容");
            await showDiagnosisReport(body, material.from, Date.now() - t0, options.commentModel);
            console.log(`[AI Lab 诊断] ${Date.now() - t0}ms from=${material.from} len=${body.length}`);
          } catch (err) {
            vscode.window.showErrorMessage(`诊断失败：${err.message}`);
          }
        }
      );
    })
  );

  // 状态栏：一眼看出补全是否开着
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 99);
  item.command = "ailabAutocomplete.test";
  const refresh = () => {
    const on = cfg().enabled;
    item.text = on ? "$(sparkle) AI 补全" : "$(circle-slash) AI 补全已关";
    item.tooltip = on ? "本地 Ollama FIM 补全已启用（点我测试）" : "补全已关闭";
    item.show();
  };
  refresh();
  context.subscriptions.push(item);
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("ailabAutocomplete")) refresh();
    })
  );
}

function deactivate() {
  if (currentAbort) currentAbort.abort();
}

module.exports = { activate, deactivate };
