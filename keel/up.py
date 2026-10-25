"""`keel up` and `keel down`: keep the UI served without anyone having to remember to.

`keel up` answers one question - is Keel's UI being served for this catalog - and makes
the answer yes. If it already is, it says where and changes nothing, so it is safe to run
at the start of every session. If nothing is listening it starts the server detached, so
it outlives the terminal or the hook that launched it. If the port belongs to something
else, or to a Keel serving a different catalog, it says so and leaves that alone.

The address is 127.0.0.1 and is not an option. The API writes files and has no login.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
STARTUP_TIMEOUT = 30.0

# Loopback is never reached through a proxy, whatever the environment says.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def url(port: int) -> str:
    return f"http://{HOST}:{port}/"


def log_path(port: int) -> Path:
    return Path(tempfile.gettempdir()) / f"keel-ui-{port}.log"


def probe(port: int) -> dict | None | bool:
    """What is on the port: Keel's health payload, None if nothing is listening, or
    False if something answers that is not Keel."""
    try:
        with _opener.open(f"{url(port)}health", timeout=2) as r:
            body = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError:
        return False                      # something is there and it is not ours
    except (urllib.error.URLError, OSError):
        return None                       # refused or timed out: nobody home
    except ValueError:
        return False                      # answered, but not with JSON
    if isinstance(body, dict) and body.get("service") == "keel":
        return body
    return False


def _spawn(port: int) -> None:
    cmd = [sys.executable, "-m", "uvicorn", "keel.main:app", "--host", HOST, "--port", str(port)]
    log = open(log_path(port), "ab")  # noqa: SIM115 - handed to the child, which outlives us
    common = dict(stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, close_fds=True)
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        try:
            # A launcher that runs its children inside a job object takes them down
            # with it. Leaving the job is refused where the job forbids it, and then
            # the plain flags are the best available.
            subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB,
                             **common)
        except OSError:
            subprocess.Popen(cmd, creationflags=flags, **common)
    else:
        subprocess.Popen(cmd, start_new_session=True, **common)
    log.close()


def _same_catalog(served: str) -> bool:
    from keel.store import resolve_catalog_dir

    try:
        return Path(served).resolve() == resolve_catalog_dir().resolve()
    except OSError:
        return False


def up(port: int) -> int:
    found = probe(port)
    if found is False:
        print(f"Keel UI not started: port {port} is in use by something else. "
              f"Set UI_PORT to a free port.", file=sys.stderr)
        return 1
    if found:
        if not _same_catalog(found.get("catalog", "")):
            print(f"Keel UI not started: port {port} is serving another catalog "
                  f"({found.get('catalog')}). Run `keel down` there, or set UI_PORT.",
                  file=sys.stderr)
            return 1
        print(f"Keel UI is running at {url(port)}")
        return 0

    _spawn(port)
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(0.25)
        if probe(port):
            print(f"Keel UI started at {url(port)}")
            return 0
    print(f"Keel UI did not come up within {STARTUP_TIMEOUT:.0f}s. Log: {log_path(port)}",
          file=sys.stderr)
    return 1


def down(port: int) -> int:
    found = probe(port)
    if not found:
        print(f"Nothing of Keel's is listening on port {port}.")
        return 0
    pid = int(found["pid"])
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
    else:
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if probe(port) is None:
            print(f"Keel UI on port {port} stopped.")
            return 0
        time.sleep(0.2)
    print(f"Keel UI on port {port} (pid {pid}) did not stop.", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> None:
    from keel.config import settings

    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "up"
    port = settings.ui_port
    if command == "up":
        raise SystemExit(up(port))
    if command == "down":
        raise SystemExit(down(port))
    print("usage: keel up | keel down", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
