"""Launch Edge headless and run FrontendStress through Chrome DevTools Protocol.

This intentionally uses only Python's standard library so the browser test does not
depend on Selenium/Playwright or downloaded browser binaries.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


class CDPWebSocket:
    def __init__(self, url: str):
        parsed = urlparse(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port or 80), timeout=20)
        self.socket.settimeout(30)
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        request_target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        request = (
            f"GET {request_target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = self._read_until(b"\r\n\r\n")
        headers, _, remainder = response.partition(b"\r\n\r\n")
        self._buffer = bytearray(remainder)
        if b" 101 " not in headers.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WebSocket handshake failed: {response[:200]!r}")
        self.next_id = 1
        self.events: list[dict] = []

    def _read_until(self, marker: bytes) -> bytes:
        data = bytearray()
        while marker not in data:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket closed during handshake")
            data.extend(chunk)
        return bytes(data)

    def _read_exact(self, length: int) -> bytes:
        data = self._buffer[:length]
        del self._buffer[:len(data)]
        while len(data) < length:
            chunk = self.socket.recv(length - len(data))
            if not chunk:
                raise ConnectionError("WebSocket closed")
            data.extend(chunk)
        return bytes(data)

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        mask = secrets.token_bytes(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(header + masked)

    def _receive_message(self) -> dict:
        fragments = bytearray()
        while True:
            first, second = self._read_exact(2)
            finished = bool(first & 0x80)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            masked = bool(second & 0x80)
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 8:
                raise ConnectionError("WebSocket closed by browser")
            if opcode == 9:
                self._send_frame(payload, opcode=10)
                continue
            if opcode in (1, 2, 0):
                fragments.extend(payload)
                if finished:
                    return json.loads(fragments.decode("utf-8"))

    def call(self, method: str, params: dict | None = None) -> dict:
        message_id = self.next_id
        self.next_id += 1
        self._send_frame(json.dumps({"id": message_id, "method": method, "params": params or {}}).encode())
        while True:
            message = self._receive_message()
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method}: {message['error']}")
                return message.get("result", {})
            self.events.append(message)

    def evaluate(self, expression: str, await_promise: bool = False):
        result = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": await_promise,
        })
        value = result.get("result", {})
        if value.get("subtype") == "error":
            raise RuntimeError(value.get("description", "JavaScript evaluation failed"))
        return value.get("value")

    def close(self) -> None:
        try:
            self._send_frame(b"", opcode=8)
        except OSError:
            pass
        self.socket.close()


def wait_json(url: str, timeout: float = 30) -> object:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                return json.load(response)
        except Exception as error:  # startup races are expected
            last_error = error
            time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for {url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=10_000)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20_260_717)
    parser.add_argument("--port", type=int, default=8089)
    parser.add_argument("--debug-port", type=int, default=9223)
    parser.add_argument("--timeout", type=int, default=10_800)
    parser.add_argument("--output", default="artifacts/frontend_stress_report.json")
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--preview-screen", choices=("battle", "formation"), default="battle")
    args = parser.parse_args()

    edge = next((path for path in EDGE_CANDIDATES if path.exists()), None)
    if not edge:
        raise FileNotFoundError("Microsoft Edge executable not found")

    server = None
    browser = None
    ws = None
    base_url = f"http://127.0.0.1:{args.port}"
    try:
        try:
            wait_json(base_url + "/api/state", timeout=1)
        except TimeoutError:
            env = os.environ.copy()
            env.update({"PYTHONIOENCODING": "utf-8", "PORT": str(args.port)})
            server = subprocess.Popen(
                [sys.executable, "main_web.py"], cwd=ROOT, env=env,
                # 压力测试会产生数十万条 HTTP 访问日志；若使用未消费的 PIPE，
                # 缓冲区填满后服务器会阻塞，看起来像游戏卡死。
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            )
            wait_json(base_url + "/api/state", timeout=30)

        profile = tempfile.mkdtemp(prefix="sanguo-edge-stress-")
        browser = subprocess.Popen([
            str(edge), "--headless=new", f"--remote-debugging-port={args.debug_port}",
            f"--user-data-dir={profile}", "--enable-precise-memory-info",
            "--no-sandbox", "--disable-gpu", "--disable-software-rasterizer",
            "--disable-background-networking", "--disable-extensions", "--no-first-run",
            "--no-default-browser-check", base_url,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        targets = wait_json(f"http://127.0.0.1:{args.debug_port}/json/list", timeout=30)
        deadline = time.time() + 30
        target = None
        while time.time() < deadline:
            targets = wait_json(f"http://127.0.0.1:{args.debug_port}/json/list", timeout=3)
            target = next((item for item in targets if item.get("type") == "page" and base_url in item.get("url", "")), None)
            if target:
                break
            time.sleep(0.2)
        if not target:
            raise RuntimeError("Game page target not found")

        ws = CDPWebSocket(target["webSocketDebuggerUrl"])
        ws.call("Runtime.enable")
        ws.call("Page.enable")
        deadline = time.time() + 30
        while time.time() < deadline and not ws.evaluate("document.readyState === 'complete' && !!window.FrontendStress"):
            time.sleep(0.2)
        if not ws.evaluate("!!window.FrontendStress"):
            raise RuntimeError("FrontendStress did not load")

        if args.preview_only:
            if args.preview_screen == "formation":
                preview = """
                (async function() {
                  async function p(path, body) {
                    const response = await fetch('/api' + path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body || {})});
                    return response.json();
                  }
                  let state = await p('/new');
                  state = await p('/select', {general_ids:state.pool.slice(0, 4).map(g => g.id)});
                  state = await p('/select', {general_ids:state.pool.slice(0, 4).map(g => g.id)});
                  window.G = state; window.__stressMode = false; window.selectedFormGen = state.p1.generals[0]; renderFormation();
                  await new Promise(resolve => setTimeout(resolve, 500));
                  return {phase:state.phase, generals:state.p1.generals.map(g => g.name)};
                })()
                """
            else:
                preview = """
            (async function() {
              async function p(path, body) {
                const response = await fetch('/api' + path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body || {})});
                return response.json();
              }
              let state = await p('/new');
              state = await p('/select', {general_ids:[state.pool[0].id]});
              state = await p('/select', {general_ids:[state.pool[0].id]});
              state = await p('/place', {positions:state.p1.generals.map((g,i) => ({general_id:g.id,row:1,col:i+1}))});
              state = await p('/place', {positions:state.p2.generals.map((g,i) => ({general_id:g.id,row:1,col:i+1}))});
              state = await p('/dice');
              window.G = state; window.__stressMode = false; renderBattle();
              await new Promise(resolve => setTimeout(resolve, 1800));
              return {phase:state.phase, p1:state.p1.generals[0].name, p2:state.p2.generals[0].name};
            })()
            """
            result = ws.evaluate(preview, await_promise=True)
            output = ROOT / args.output
            output.parent.mkdir(parents=True, exist_ok=True)
            screenshot = ws.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            output.with_suffix(".png").write_bytes(base64.b64decode(screenshot["data"]))
            print(f"preview={result} screenshot={output.with_suffix('.png')}")
            return 0

        options = json.dumps({"games": args.games, "batchSize": args.batch_size, "seed": args.seed})
        ws.evaluate(f"FrontendStress.run({options}); 'started'")
        started = time.time()
        last_processed = -1
        report = None
        while time.time() - started < args.timeout:
            raw = ws.evaluate("JSON.stringify(window.__frontendStressReport && ({status:__frontendStressReport.status,finished:__frontendStressReport.finished,processed:__frontendStressReport.processed,completed:__frontendStressReport.completed,crashes:__frontendStressReport.crashes,stalls:__frontendStressReport.stalls,rate:__frontendStressReport.rate,heap:__frontendStressReport.heap,dom:__frontendStressReport.dom}))")
            progress = json.loads(raw) if raw and raw != "null" else {}
            processed = progress.get("processed", 0) or 0
            if processed != last_processed:
                heap = progress.get("heap", {}).get("current")
                heap_text = f"{heap / 1024 / 1024:.1f}MiB" if heap else "n/a"
                print(
                    f"browser {processed}/{args.games} completed={progress.get('completed', 0)} "
                    f"failures={progress.get('crashes', 0) + progress.get('stalls', 0)} "
                    f"heap={heap_text} dom={progress.get('dom', {}).get('current')} "
                    f"rate={progress.get('rate') or 0:.2f}/s",
                    flush=True,
                )
                last_processed = processed
            if progress.get("finished"):
                report = json.loads(ws.evaluate("JSON.stringify(window.__frontendStressReport)"))
                break
            time.sleep(1)
        if report is None:
            ws.evaluate("FrontendStress.cancel()")
            raise TimeoutError(f"Browser stress test exceeded {args.timeout}s")

        output = ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        screenshot = ws.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        output.with_suffix(".png").write_bytes(base64.b64decode(screenshot["data"]))
        print(f"report={output}")
        return 0 if report.get("status") == "passed" else 1
    finally:
        if ws:
            ws.close()
        if browser and browser.poll() is None:
            browser.terminate()
            try:
                browser.wait(timeout=10)
            except subprocess.TimeoutExpired:
                browser.kill()
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
