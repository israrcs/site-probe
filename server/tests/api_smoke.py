"""Smoke test: run a scan through the live API (like the dashboard does)."""
import json
import sys
import time
import urllib.request

API = "http://127.0.0.1:8000"
TARGET = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"
MAX_PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 3

body = json.dumps({
    "url": TARGET,
    "max_pages": MAX_PAGES,
    "viewports": ["desktop"],
    "timeout_ms": 25000,
}).encode()

req = urllib.request.Request(API + "/api/runs", data=body,
                             headers={"Content-Type": "application/json"})
run_id = json.loads(urllib.request.urlopen(req, timeout=15).read())["id"]
print("RUN_ID:", run_id)

status = "queued"
for _ in range(60):
    time.sleep(5)
    run = json.loads(urllib.request.urlopen(
        f"{API}/api/runs/{run_id}", timeout=15).read())
    status = run["status"]
    print("  poll:", status, run["phase"], f"{run['pages_done']}/{run['pages_total']}")
    if status in ("completed", "failed", "cancelled"):
        break

print("FINAL STATUS:", status)
print("SCORES:", json.dumps(run["scores"]))
print(f"ISSUES ({len(run['issues'])}):")
for i in run["issues"]:
    print(f"  [{i['severity']:<8}] {i['category']:<11} {i['title'][:110]}")

hashbang = [i for i in run["issues"]
            if 'anchor "#!' in i["title"] or 'anchor "#/' in i["title"]]
print("HASHBANG_NOISE:", len(hashbang), "(must be 0)")
print("SMOKE:", "PASS" if status == "completed" and not hashbang else "FAIL")
