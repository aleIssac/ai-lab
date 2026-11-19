"""Ollama 请求修正代理（流式版）。

问题背景：
    Continue 的 autocomplete 用流式请求（streamEnabled: true）调用 Ollama 的
    /api/generate，但 Ollama 收到 FIM 格式的 prompt 后，如果不带 "raw": true，
    会走 chat template 包装，<|fim_prefix|> 等标记变成普通文本，模型识别不出
    补全意图。

本代理只做一件事：
    给 /api/generate 的请求体补上 "raw": true，其余（含 stream）原样透传。

注意：
    绝不能把 stream 改成 false —— Continue 按 SSE 流式解析，收到单个 JSON
    会报 "The operation was aborted"。

用法：
    python src/ollama_proxy.py
    Continue 配置 apiBase 指向 http://127.0.0.1:11435
"""

import json
import os
import time

import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

UPSTREAM = os.environ.get("OLLAMA_UPSTREAM", "http://ollama:11434")
PORT = int(os.environ.get("PROXY_PORT", "11435"))

app = FastAPI(title="Ollama FIM proxy")


@app.get("/")
def health():
    try:
        r = requests.get(f"{UPSTREAM}/", timeout=5)
        return {"proxy": "ok", "upstream": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"proxy": "ok", "upstream": "unreachable", "error": str(exc)})


@app.post("/api/generate")
async def generate(request: Request):
    body = await request.json()
    forced = body.get("raw") is not True
    body["raw"] = True
    want_stream = body.get("stream", True)

    prompt = body.get("prompt", "")
    head = prompt[:60].replace("\n", "\\n")
    tail = prompt[-40:].replace("\n", "\\n")
    print(f"[REQ] len={len(prompt)} stream={want_stream} forced_raw={forced} "
          f"model={body.get('model')} head={head!r} tail={tail!r}", flush=True)

    if want_stream:
        def relay():
            buf = []
            t0 = time.time()
            print("[STREAM-START]", flush=True)
            try:
                with requests.post(f"{UPSTREAM}/api/generate", json=body,
                                   stream=True, timeout=300) as r:
                    for chunk in r.iter_content(chunk_size=None):
                        if chunk:
                            buf.append(chunk)
                            n = len(buf)
                            if n <= 3:
                                print(f"[CHUNK {n}] {(time.time() - t0) * 1000:.0f}ms "
                                      f"{chunk[:120]!r}", flush=True)
                            yield chunk
            except GeneratorExit:
                print(f"[STREAM-CANCEL] 客户端提前断开 "
                      f"{(time.time() - t0) * 1000:.0f}ms 收到 {len(buf)} 块", flush=True)
                raise
            except Exception as exc:  # noqa: BLE001
                print(f"[STREAM-ERROR] {exc}", flush=True)
            try:
                text = "".join(x.decode("utf-8", "ignore") for x in buf)
                parts = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parts.append(json.loads(line).get("response", ""))
                    except Exception:  # noqa: BLE001
                        pass
                print(f"[RES-stream] {(time.time() - t0) * 1000:.0f}ms "
                      f"{''.join(parts)[:300]!r}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[RES-stream] log failed: {exc}", flush=True)

        return StreamingResponse(relay(), media_type="application/x-ndjson")

    r = requests.post(f"{UPSTREAM}/api/generate", json=body, timeout=300)
    data = r.json()
    print(f"[RES] {data.get('response', '')!r}", flush=True)
    return data


@app.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "PUT"])
async def passthrough(path: str, request: Request):
    url = f"{UPSTREAM}/{path}"
    body = await request.body()
    r = requests.request(
        request.method, url, data=body,
        headers={"Content-Type": request.headers.get("content-type", "application/json")},
        timeout=300,
    )
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type", "application/json"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
