import os
import time
import urllib.request
from pathlib import Path


if os.environ.get("APP_PROCESS", "web") == "worker":
    heartbeat = Path(
        os.environ.get(
            "WORKER_HEARTBEAT_PATH", "/home/app/riot-analysis-worker-heartbeat"
        )
    )
    healthy = heartbeat.exists() and time.time() - heartbeat.stat().st_mtime < 120
else:
    host = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")[0]
    request = urllib.request.Request(
        "http://127.0.0.1:8000/healthz",
        headers={"Host": host, "X-Forwarded-Proto": "https"},
    )
    try:
        healthy = urllib.request.urlopen(request, timeout=3).status == 200
    except Exception:
        healthy = False

raise SystemExit(0 if healthy else 1)
