"""LAN helper for the second Mac (no GitHub login): serves the self-play kit and the current seat model,
and receives finished self-play batches straight into env4/data as g3h.part3NN.npz (inside the driver's
'data/g3h.part*.npz' training glob). Read-only on the driver's files except for adding new data files.
usage: python3 server.py   (port 8765; URLs need the token from token.txt)"""
import io, os, re, tarfile, time, glob
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
L4 = HERE.parents[1]
ENV = L4 / "env4"
TOKEN = (HERE / "token.txt").read_text().strip()
IP = os.popen("ipconfig getifaddr en0").read().strip() or "127.0.0.1"
TR = Path.home() / ".claude/projects/-Users-iustinepanu-ccc-ccc-ai-engineer-data-ai/b14c4474-1bc1-48f4-a6e4-ffd3bb6867da.jsonl"
LOG = HERE / "server.log"
SKIP_DIRS = {".venv", "data", "__pycache__"}


def log(msg):
    with LOG.open("a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def seat():
    try:
        m = re.findall(r"upload4\.py \.\./level4/env4/(\w+\.onnx)", TR.read_text()[-600000:])
        if m and (ENV / m[-1]).exists():
            return m[-1]
    except Exception:
        pass
    return "n5.onnx"


def kit():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for p in ENV.rglob("*"):
            rel = p.relative_to(ENV)
            if p.is_dir() or SKIP_DIRS & set(rel.parts) or p.suffix in (".onnx", ".pt", ".npz", ".log"):
                continue
            t.add(p, arcname=f"env4/{rel}")
        t.add(HERE.parent / "selfplay_n.py", arcname="env4/selfplay_n.py")
    return buf.getvalue()


SETUP = r'''#!/bin/bash
# Second Mac: self-play worker for the driver Mac (no GitHub needed). Re-run any time; it resumes.
set -u
B="http://__IP__:8765/__TOKEN__"; D="$HOME/ccc-mac2-lan"; mkdir -p "$D" && cd "$D" || exit 1
echo "== downloading the kit from the driver Mac"
curl -fsS "$B/kit.tar.gz" | tar xz || { echo "ERROR: cannot reach $B (same Wi-Fi/hotspot as the driver Mac?)"; exit 1; }
cd env4 && mkdir -p data
if [ ! -x .venv/bin/python ]; then
  echo "== installing the engine (once, 1-2 min)"
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt || { echo "ERROR: install failed (Python 3.11+ on Apple Silicon needed)"; exit 1; }
fi
NP=$(( $(sysctl -n hw.ncpu) - 1 )); i=0; R=$(date +%H%M)
echo "== self-play with $NP processes, ${GAMES:-400} games per batch at ${SIMS:-150} sims"
while true; do
  M=$(curl -fsS "$B/models.txt") || { echo "WARN: driver Mac unreachable, retry in 20 s"; sleep 20; continue; }
  for f in $(echo $M | tr ' ' '\n' | sort -u); do [ -f "$f" ] || curl -fsS -o "$f" "$B/model/$f"; done
  i=$((i + 1)); b="m2_${R}_$i"; t0=$(date +%s)
  if ! NPROC=$NP SIMS=${SIMS:-150} .venv/bin/python selfplay_n.py "data/$b" "${GAMES:-400}" $M > "data/$b.log" 2>&1; then
    echo "WARN: batch $b failed, see $D/env4/data/$b.log"; sleep 10; continue
  fi
  for f in data/$b.part*.npz; do curl -fsS -T "$f" "$B/data/$(basename "$f")" > /dev/null || echo "WARN: upload of $f failed"; done
  echo "$(date +%H:%M:%S) batch $b sent ($(( $(date +%s) - t0 )) s, models: $M)"
done
'''


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _ok(self, body, ctype="application/octet-stream"):
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        parts = self.path.strip("/").split("/")
        if not parts or parts[0] != TOKEN:
            return self.send_error(404)
        what = "/".join(parts[1:])
        if what == "setup.sh":
            return self._ok(SETUP.replace("__IP__", IP).replace("__TOKEN__", TOKEN).encode(), "text/plain")
        if what == "kit.tar.gz":
            log(f"kit -> {self.client_address[0]}"); return self._ok(kit())
        if what == "models.txt":
            s = seat(); return self._ok(f"{s} {s} n2b.onnx".encode(), "text/plain")
        if what.startswith("model/"):
            name = os.path.basename(what)
            p = ENV / name
            if p.suffix == ".onnx" and p.exists():
                log(f"model {name} -> {self.client_address[0]}"); return self._ok(p.read_bytes())
        self.send_error(404)

    def do_PUT(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == TOKEN and parts[1] == "test":
            n = int(self.headers.get("Content-Length", "0")); (HERE / "test_upload.bin").write_bytes(self.rfile.read(n))
            log(f"test upload {n} bytes from {self.client_address[0]}"); return self._ok(b"test ok\n", "text/plain")
        if len(parts) != 3 or parts[0] != TOKEN or parts[1] != "data" or not parts[2].endswith(".npz"):
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", "0"))
        if n <= 0 or n > 60_000_000:
            return self.send_error(400)
        body = self.rfile.read(n)
        k = 300 + len(glob.glob(str(ENV / "data" / "g3h.part3*.npz")))
        tmp = ENV / "data" / f".lan{k}.tmp"
        tmp.write_bytes(body); os.replace(tmp, ENV / "data" / f"g3h.part{k}.npz")
        log(f"batch file {parts[2]} ({n} bytes) from {self.client_address[0]} -> data/g3h.part{k}.npz")
        self._ok(b"ok\n", "text/plain")


if __name__ == "__main__":
    log(f"start on {IP}:8765")
    ThreadingHTTPServer(("0.0.0.0", 8765), H).serve_forever()
