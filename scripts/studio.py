#!/usr/bin/env python3
"""Serve a verified synthetic preview; never start Remotion Studio or an agent."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import signal
from socketserver import TCPServer

import common
from synthetic import status

MAX_PREVIEW_BYTES = 128 * 1024 * 1024


class PreviewServer(ThreadingHTTPServer):
    def server_bind(self):
        # The numeric loopback address needs no reverse DNS or network lookup.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def load_preview(run_id):
    """Take a verified, bounded snapshot. HTTP requests never access the filesystem."""
    common.require_setup_scope()
    run = common.run_path(run_id)
    if common.safe_path(run, ".lock").exists():
        raise ValueError("Run is locked; preserve it and inspect the active operation")
    state = status(run_id)
    if state["status"] != "succeeded":
        raise ValueError(f"Preview requires a verified succeeded run, got {state['status']}; render a fresh synthetic run in Claude Code")
    path = common.safe_path(run, "preview.mp4", exists=True)
    with path.open("rb") as source:
        video = source.read(MAX_PREVIEW_BYTES + 1)
    if not video or len(video) > MAX_PREVIEW_BYTES:
        raise ValueError("Synthetic preview snapshot must be non-empty and at most 128 MiB")
    if hashlib.sha256(video).hexdigest() != state["outputs"]["preview.mp4"]:
        raise ValueError("Preview changed while loading; preserve and inspect")
    common.require_setup_scope()
    return video


def page(run_id):
    # run_id is validated before this function is called; no user HTML or scripts.
    return f'''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>vlog-me · 미리보기</title>
<style>
body{{margin:0;background:#161819;color:#f2f2ef;font:16px system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:32px 24px}}h1{{font-size:24px;margin:0 0 8px}}
p{{color:#b7bdbd;line-height:1.6}}video{{display:block;width:100%;max-height:75vh;background:#000;margin:24px 0}}
code{{font-size:13px;overflow-wrap:anywhere}}
</style><main><h1>vlog-me · 미리보기</h1>
<p>검증된 합성 영상의 저장본입니다. 수정은 Claude Code에서 진행한 뒤 새 렌더로 확인합니다.</p>
<video controls preload="metadata" playsinline controlslist="nodownload noremoteplayback" disableremoteplayback src="/preview.mp4"></video>
<p><code>{run_id}</code> · 실제 촬영본 미사용</p>
</main></html>'''.encode("utf-8")


def handler_for(run_id, video):
    html = page(run_id)

    class PreviewHandler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; media-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            super().end_headers()

        def read_only(self):
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = read_only

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            host = f"127.0.0.1:{self.server.server_port}"
            if (self.headers.get("Host") != host or
                    self.headers.get("Origin", "http://" + host) != "http://" + host):
                self.send_error(403, "Local preview origin required")
                return
            if self.headers.get("Upgrade"):
                self.send_error(400, "No protocol upgrades")
                return
            if self.path not in {"/", "/preview.mp4"}:
                self.send_error(404)
                return
            is_video = self.path == "/preview.mp4"
            data = video if is_video else html
            start, end, code = 0, len(data) - 1, 200
            requested = self.headers.get("Range") if is_video else None
            if requested:
                match = re.fullmatch(r"bytes=(\d{0,16})-(\d{0,16})", requested)
                if match and any(match.groups()):
                    left, right = match.groups()
                    if left:
                        start, end = int(left), min(int(right), end) if right else end
                    else:
                        start = max(0, len(data) - int(right))
                else:
                    start = len(data)
                if not 0 <= start <= end < len(data):
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{len(data)}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                code = 206
            self.send_response(code)
            self.send_header("Content-Type", "video/mp4" if is_video else "text/html; charset=utf-8")
            self.send_header("Content-Length", str(end - start + 1))
            if is_video:
                self.send_header("Accept-Ranges", "bytes")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(memoryview(data)[start:end + 1])
                except (BrokenPipeError, ConnectionResetError):
                    pass  # A seek or closed browser can cancel an in-flight read.

    return PreviewHandler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--port", type=int, default=0, help="Loopback port; 0 selects an available port")
    parser.add_argument("--refresh", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.refresh:
        parser.error("Live Studio refresh was removed; edit/render in Claude Code, then open the new succeeded run")
    if not 0 <= args.port <= 65535:
        parser.error("Port must be 0..65535")
    try:
        video = load_preview(args.run_id)
        with PreviewServer(("127.0.0.1", args.port), handler_for(args.run_id, video)) as server:
            print(json.dumps({"status": "preview_ready", "run_id": args.run_id,
                              "url": f"http://127.0.0.1:{server.server_port}/", "read_only": True}), flush=True)
            try:
                server.serve_forever()
            except (KeyboardInterrupt, InterruptedError):
                print(json.dumps({"status": "preview_stopped"}), flush=True)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    return 0


def interrupted(_signum, _frame):
    # selectors can consume InterruptedError; KeyboardInterrupt reaches main.
    raise KeyboardInterrupt("Preview server stopped")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
