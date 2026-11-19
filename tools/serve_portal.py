"""统一入口静态服务器。

把门户页、playground、transformer-explainer 挂到同一个端口下，
避免为每个静态站点单独开服务。

用法：
    python tools/serve_portal.py            # 默认 3000 端口
    python tools/serve_portal.py 3005

路由：
    /                       门户页
    /nn-playground/         TensorFlow Playground（需求⑤）
    /transformer-explainer/ Transformer Explainer（需求⑥）
"""

import http.server
import os
import socketserver
import sys
import urllib.parse

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 这两个演示站点原来放在 D:\Environment\Server\apps（项目外），换机器就找不到。
# 现在优先用项目里的 apps/ 副本，找不到再回落到老路径，两边都能跑。
LEGACY_APPS = r"D:\Environment\Server\apps"


def _resolve(*parts):
    for base in (os.path.join(PROJECT, "apps"), LEGACY_APPS):
        cand = os.path.join(base, *parts)
        if os.path.isdir(cand):
            return cand
    return os.path.join(PROJECT, "apps", *parts)


MOUNTS = {
    "/nn-playground/": os.path.join(PROJECT, "nn-playground"),
    "/transformer-explainer/": _resolve("transformer-explainer", "build"),
    "/convnetjs/": _resolve("convnetjs"),
}

PORTAL = os.path.join(PROJECT, "portal")


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean = urllib.parse.urlparse(path).path

        for prefix, root in MOUNTS.items():
            if clean.startswith(prefix):
                rel = clean[len(prefix):]
                parts = [p for p in rel.split("/") if p]
                return os.path.join(root, *parts) if parts else root

        rel = clean.lstrip("/")
        parts = [p for p in rel.split("/") if p]
        return os.path.join(PORTAL, *parts) if parts else PORTAL

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

    for prefix, root in MOUNTS.items():
        state = "就绪" if os.path.isdir(root) else "缺失"
        print(f"  {prefix:28s} -> {root}  [{state}]")

    # 必须用多线程：浏览器会并发建立多条 keep-alive 连接，
    # 单线程 TCPServer 会被第一条慢连接堵死，后续请求全部无响应
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler) as httpd:
        print(f"\n演示入口已启动: http://localhost:{port}\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")


if __name__ == "__main__":
    main()
