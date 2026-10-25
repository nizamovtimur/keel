"""Keel answers to the machine it runs on and to nothing else.

The API writes files and has no login, so "local only" is the whole of its access
control. Listening on loopback is half of it. The other half is the user's own browser,
which can reach loopback on behalf of any page it has open, so the app also checks the
name it was asked for and where a write came from.
"""
import socket
import subprocess

import pytest
from fastapi.testclient import TestClient

from keel import up
from keel.config import settings
from keel.main import app
from keel.store import Store, set_store


@pytest.fixture
def client(catalog_dir):
    set_store(Store(catalog_dir(threats=[{"id": "T-A"}])))
    yield TestClient(app)
    set_store(None)


def test_a_request_under_a_name_keel_does_not_answer_to_is_refused(client):
    r = client.get("/api/threats", headers={"host": "attacker.example"})
    assert r.status_code == 400


def test_no_origin_is_told_it_may_read_the_answer(client):
    r = client.get("/api/threats", headers={"origin": "https://attacker.example"})
    assert "access-control-allow-origin" not in r.headers


def test_a_preflight_from_another_site_is_not_granted(client):
    r = client.options("/api/threats", headers={
        "origin": "https://attacker.example",
        "access-control-request-method": "POST",
        "access-control-request-headers": "content-type",
    })
    assert "access-control-allow-origin" not in r.headers


@pytest.mark.parametrize("method,path", [
    ("POST", "/api/threats"),
    ("DELETE", "/api/threats/T-A"),
    ("PATCH", "/api/threats/T-A"),
    ("PUT", "/api/catalog/file"),
])
def test_a_write_from_another_site_is_refused(client, method, path):
    r = client.request(method, path, json={}, headers={"origin": "https://attacker.example"})
    assert r.status_code == 403


def test_a_refused_delete_deletes_nothing(client):
    client.delete("/api/threats/T-A", headers={"origin": "https://attacker.example"})
    assert client.get("/api/threats/T-A").status_code == 200


def test_the_apps_own_page_may_write(client):
    r = client.delete("/api/threats/T-A", headers={"origin": "http://localhost:8420"})
    assert r.status_code == 200


def test_a_write_with_no_origin_is_a_script_and_is_let_through(client):
    assert client.delete("/api/threats/T-A").status_code == 200


# --------------------------------------------------------------------------- #
# what gets listened on
# --------------------------------------------------------------------------- #

def test_keel_up_starts_the_server_on_loopback(monkeypatch, tmp_path):
    started = []
    monkeypatch.setattr(up, "log_path", lambda port: tmp_path / "ui.log")
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: started.append(cmd))
    up._spawn(8420)
    cmd = started[0]
    assert cmd[cmd.index("--host") + 1] == "127.0.0.1"


def test_mcp_over_http_refuses_a_non_loopback_address_by_default(monkeypatch):
    from keel.mcp import server

    monkeypatch.setattr(settings, "mcp_http_host", "0.0.0.0")
    monkeypatch.setattr(settings, "mcp_http_allow_remote", False)
    with pytest.raises(SystemExit) as stopped:
        server.run_http()
    assert stopped.value.code == 2


# --------------------------------------------------------------------------- #
# what `keel up` makes of the port
# --------------------------------------------------------------------------- #

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_a_port_nobody_listens_on_reads_as_free():
    assert up.probe(_free_port()) is None


def test_a_port_held_by_something_else_is_not_mistaken_for_keel(monkeypatch):
    """`keel up` must not report a stranger's server as Keel's UI, and `keel down` must
    not stop it."""
    import http.server
    import threading

    class Stranger(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Stranger)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        assert up.probe(port) is False
        assert up.up(port) == 1
        killed = []
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: killed.append(a))
        monkeypatch.setattr(up.os, "kill", lambda *a: killed.append(a))
        up.down(port)
        assert killed == []
    finally:
        server.shutdown()
