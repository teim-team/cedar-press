"""Local real-release proof across Grove, Cedar and the producer HTTP boundary.

Run explicitly with saved catalog/pin/packet paths in a queue, never in ordinary
CI. The listener binds only loopback and exists only for this command. Source
credentials are generated in memory and do not enter arguments or receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import threading
import time
from pathlib import Path

import uvicorn


def run_one(item, args):
    from lumecon_data.api import create_app

    key, rid = item["collection"], item["release"]
    output = args.output / key
    output.mkdir(parents=True, exist_ok=False)
    packet = Path(item["packet"])
    saved = json.loads((packet / "receipt.json").read_bytes())
    if saved["release_id"] != rid or saved["synthetic"] is not False:
        raise ValueError("queue does not name a real pinned packet")
    token = secrets.token_urlsafe(32)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(Path(item["store"]), {token: {key}}),
            log_config=None,
            access_log=False,
            log_level="critical",
        )
    )
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    worker.start()
    started = time.monotonic()
    while not server.started:
        if not worker.is_alive() or time.monotonic() - started > 10:
            raise RuntimeError("local producer listener did not start")
        time.sleep(0.05)
    env = dict(
        os.environ,
        CEDAR_RELEASE_CONSUMER_ROOT=str(args.consumer_root.resolve()),
        CEDAR_RELEASE_CONSUMER_PYTHON=str(args.python.resolve()),
        CEDAR_GROVE_RELEASE_TEMP_ROOT=str((args.output / "temporary").resolve()),
        CEDAR_PRESS_DATA_API=f"http://127.0.0.1:{listener.getsockname()[1]}",
        CEDAR_PRESS_DATA_TOKEN=token,
        CEDAR_PRESS_DATA_TIMEOUT_SECONDS="300",
        CEDAR_PRESS_ENVIRONMENT="development",
        CEDAR_GROVE_ENVIRONMENT="review",
        CEDAR_PRESS_PARTITIONED_REHEARSAL="1",
        PYTHONUTF8="1",
        CEDAR_PRESS_RELEASE_CATALOG=item["catalog"],
        CEDAR_GROVE_RELEASE_CATALOG=item["catalog"],
        CEDAR_PRESS_COMPONENT_RELEASE_CATALOG=item["catalog"],
        CEDAR_PRESS_COMPONENT_RELEASE_PIN=item["pin"],
        CEDAR_GROVE_RELEASE_PIN=item["pin"],
        CEDAR_PRESS_RESEARCH_CATALOG=item["research_catalog"],
    )
    config = output / "checks.json"
    config.write_text(
        json.dumps({"collection": key, "release_id": rid, "checks": item["checks"]}) + "\n",
        encoding="utf-8",
    )
    log = output / "progress.log"
    command = [
        str(args.node),
        str(args.grove_root / "scripts/verify-cedar-release.cjs"),
        str(config),
        str(output / "receipt.json"),
    ]
    child = None
    try:
        with log.open("w", encoding="utf-8") as stream:
            child = subprocess.Popen(
                command,
                cwd=args.grove_root,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            next_progress = 0.0
            while child.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed > 900:
                    raise TimeoutError("real Grove review exceeded 15 minutes")
                if elapsed >= next_progress:
                    print(
                        json.dumps(
                            {
                                "collection": key,
                                "pid": child.pid,
                                "seconds": round(elapsed),
                                "log_bytes": log.stat().st_size,
                            }
                        ),
                        flush=True,
                    )
                    next_progress = elapsed + 15
                time.sleep(1)
        if child.returncode:
            raise RuntimeError("real Grove process review failed; see named checks in log")
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        server.should_exit = True
        worker.join(timeout=10)
        listener.close()
    result = json.loads((output / "receipt.json").read_bytes())
    if result.get("status") != "passed":
        raise ValueError("incomplete Grove receipt")
    result["packet_receipt_sha256"] = hashlib.sha256(
        (packet / "receipt.json").read_bytes()
    ).hexdigest()
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps({"collection": key, "checks": len(result["checks"]), "status": "passed"}),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "queue",
        "output",
        "grove-root",
        "consumer-root",
        "producer-root",
        "python",
        "node",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("LUMECON_ENVIRONMENT") != "review":
        raise ValueError("requires explicit producer review environment")
    contract = json.loads(
        (args.grove_root / "server/contracts/cedarReleaseConsumer.json").read_bytes()
    )
    for root, field in (
        (args.consumer_root, "consumer_commit"),
        (args.producer_root, "producer_commit"),
    ):
        check = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if check.stdout.strip() != contract[field]:
            raise ValueError("review tree differs from exact cross-repository pin")
    for item in json.loads(args.queue.read_bytes()):
        run_one(item, args)


if __name__ == "__main__":
    main()
