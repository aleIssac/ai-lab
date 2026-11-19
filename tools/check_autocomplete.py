"""Tab 补全自检脚本（在容器内或宿主机上跑都行）。

它做三件事：
  1. 检查 11435 代理是否在跑
  2. 检查 qwen-coder-fim 模型能否正常做 FIM 补全（含首 token 延迟）
  3. 打印补全内容，人工判断质量

用法（容器内）：
    docker exec ai-lab /opt/venv/bin/python tools/check_autocomplete.py

用法（宿主机，需要模型端口映射）：
    python tools/check_autocomplete.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

PROXY = os.environ.get("PROXY_URL", "http://localhost:11435")
MODEL = os.environ.get("FIM_MODEL", "qwen-coder-fim")

CASES = [
    ("普通函数", "<|fim_prefix|>import torch\n\ndef sum_list(nums):\n    <|fim_suffix|>\n\nprint(sum_list([1, 2, 3]))\n<|fim_middle|>"),
    ("读文件", "<|fim_prefix|>import pandas as pd\n\ndef load(path):\n    <|fim_suffix|>\n\nprint(load(\"a.csv\").shape)\n<|fim_middle|>"),
    ("类方法", "<|fim_prefix|>class Model:\n    def __init__(self):\n        self.w = 1.0\n\n    <|fim_suffix|>\n\nm = Model()\n<|fim_middle|>"),
]


def health() -> bool:
    try:
        with urllib.request.urlopen(f"{PROXY}/", timeout=5) as r:
            data = json.load(r)
        print(f"[1] 代理 {PROXY} 正常: {data}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[1] 代理 {PROXY} 不可用: {exc}")
        return False


def complete(prompt: str):
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "raw": True,
        "stream": True,
        "options": {"temperature": 0.2, "num_predict": 64},
    }).encode()
    req = urllib.request.Request(
        f"{PROXY}/api/generate", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    first = None
    chunks = []
    stop_reason = None
    with urllib.request.urlopen(req, timeout=120) as r:
        for line in r:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("response") and first is None:
                first = time.time() - t0
            chunks.append(d.get("response", ""))
            if d.get("done"):
                stop_reason = d.get("done_reason")
                break
    return "".join(chunks), first, time.time() - t0, stop_reason


def main() -> int:
    if not health():
        return 1

    ok = True
    for name, prompt in CASES:
        try:
            text, first, total, reason = complete(prompt)
        except urllib.error.URLError as exc:
            print(f"[ERR] {name}: {exc}")
            ok = False
            continue
        clean = text.replace("\n", "\\n")
        print(f"[2] {name}: 首token {0 if first is None else round(first * 1000)}ms, "
              f"总耗时 {round(total * 1000)}ms, stop={reason}")
        print(f"    补全 => {clean[:160]}")
        if not text.strip():
            print("    !! 空补全，检查模型名与代理")
            ok = False

    print("[3] 结论:", "链路正常" if ok else "有问题，需排查")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
