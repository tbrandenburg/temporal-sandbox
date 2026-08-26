"""Session-scoped Docker Compose lifecycle for the e2e suite.

Brings the real stack (temporal dev server + workers) up once for the whole e2e session,
polls until healthy, yields to the tests, then tears it down. Never touches ports that are
already bound by something else (assumed to be an already-running stack we shouldn't kill).
"""

import socket
import subprocess
import time
import urllib.request
from collections.abc import Iterator

import pytest

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
TEMPORAL_ADDRESS = "127.0.0.1:7233"
TEMPORAL_UI_URL = "http://127.0.0.1:8233"
TEMPORAL_BIN = "/home/linuxbrew/.linuxbrew/opt/temporal/bin/temporal"
READINESS_TIMEOUT_SECONDS = 60
READINESS_POLL_INTERVAL_SECONDS = 2


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def _wait_until_ready(timeout: int = READINESS_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(TEMPORAL_UI_URL, timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError(f"UI returned status {response.status}")
            subprocess.run(
                [
                    TEMPORAL_BIN,
                    "--address",
                    TEMPORAL_ADDRESS,
                    "operator",
                    "namespace",
                    "describe",
                    "default",
                ],
                check=True,
                capture_output=True,
                timeout=10,
            )
            return
        except Exception as error:  # noqa: BLE001 - broad by design, we retry regardless
            last_error = error
            time.sleep(READINESS_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Stack did not become ready within {timeout}s") from last_error


@pytest.fixture(scope="session")
def docker_stack() -> Iterator[dict[str, str]]:
    ports_already_bound = _port_in_use("127.0.0.1", 7233) or _port_in_use("127.0.0.1", 8233)
    we_started_it = False

    if ports_already_bound:
        # Something is already listening on our ports. Given this is a fresh sandbox project
        # this is unexpected — fail loudly instead of silently reusing or colliding with it.
        raise RuntimeError(
            "Ports 7233/8233 are already in use before the e2e stack was started. "
            "Refusing to start a second stack or kill the existing process. "
            "Stop whatever owns those ports (or run `docker compose down`) and retry."
        )

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            timeout=300,
        )
        we_started_it = True
        _wait_until_ready()
        yield {"address": TEMPORAL_ADDRESS, "ui_url": TEMPORAL_UI_URL}
    finally:
        if we_started_it:
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                timeout=60,
            )
