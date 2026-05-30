"""Integrated voiceover recorder (PRD §18.2). `explainer record <dir>` launches a local
browser teleprompter that records the mic per segment (MediaRecorder), saves each clip
straight into the project's voiceover/ folder, and supports re-recording — no external app.

Run it in the background; it returns when the operator clicks "Finish" in the browser."""
import json, subprocess, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ASSETS = Path(__file__).parent / "assets"


def run(proj, open_browser=True):
    from .media.common import effective_segments
    script = json.loads(proj.script_json.read_text())
    seg_list = [{"id": s["id"], "slide": s["slide"], "text": s["text"]}
                for s in effective_segments(proj, script)]
    vdir = proj.voiceover_dir
    html = (ASSETS / "recorder.html").read_text().replace("{{TITLE}}", str(proj.data.get("title", "Voiceover")))
    state = {"done": False}

    def wav(sid): return vdir / f"seg_{sid:03d}.wav"
    def recorded(sid): return wav(sid).exists()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, (bytes, bytearray)) else str(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            p = urlparse(self.path)
            if p.path == "/":
                self._send(200, html, "text/html; charset=utf-8")
            elif p.path == "/segments":
                self._send(200, json.dumps([{**s, "recorded": recorded(s["id"])} for s in seg_list]))
            elif p.path == "/clip":
                sid = int(parse_qs(p.query).get("seg", ["-1"])[0])
                f = wav(sid)
                self._send(200, f.read_bytes(), "audio/wav") if f.exists() else self._send(404, b"")
            else:
                self._send(404, b"{}")

        def do_POST(self):
            p = urlparse(self.path)
            if p.path == "/save":
                sid = int(parse_qs(p.query).get("seg", ["-1"])[0])
                blob = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                webm = vdir / f"seg_{sid:03d}.webm"
                webm.write_bytes(blob)
                r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(webm),
                                    "-ar", "48000", "-ac", "1", str(wav(sid))], capture_output=True)
                webm.unlink(missing_ok=True)
                ok = r.returncode == 0 and wav(sid).exists()
                self._send(200 if ok else 500, json.dumps({"ok": ok, "seg": sid}))
            elif p.path == "/done":
                state["done"] = True
                self._send(200, json.dumps({"ok": True}))
            else:
                self._send(404, b"{}")

    srv = HTTPServer(("127.0.0.1", 0), H)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"RECORDER READY → {url}\nRecord each segment in the browser, then click 'Finish & render'.", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        while not state["done"]:
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    srv.shutdown()
    rec = [s["id"] for s in seg_list if recorded(s["id"])]
    miss = [s["id"] for s in seg_list if not recorded(s["id"])]
    result = {"recorded": rec, "missing": miss, "segments": len(seg_list)}
    print("RECORD DONE:", json.dumps(result))
    return result
