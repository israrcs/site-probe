"""Debug: scan the fixture once and dump performance metrics."""
import asyncio
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.models import Run, RunOptions  # noqa: E402
from app.services.runner import Runner  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixture_site"

big = FIXTURES / "big.bin"
big.write_bytes(b"0" * (4 * 1024 * 1024))

s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
proc = subprocess.Popen(
    [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
     "--directory", str(FIXTURES)],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
for _ in range(50):
    try:
        urllib.request.urlopen(base + "/index.html", timeout=1)
        break
    except Exception:
        time.sleep(0.2)

run = Run(options=RunOptions(url=base + "/index.html", max_pages=1,
                             viewports=["desktop"]))
asyncio.run(Runner(run).execute())
proc.terminate()

home = run.pages[0]
print("STATUS:", run.status.value, run.error)
print("METRICS:", home.metrics)
perf = [i for i in run.issues if i.category.value == "performance"]
print("PERF ISSUES:", [(i.title, i.metadata) for i in perf])
big.unlink(missing_ok=True)
