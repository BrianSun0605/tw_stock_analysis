import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import peewee
import yfinance.cache as yf_cache
from waitress import create_server

import config
import main
import webui
from stock.yf_errors import YFINANCE_EXCEPTIONS
from webui import _close_waitress_server


def test_yfinance_cache_is_project_local_and_writable():
    cache_dir = Path(config.YFINANCE_CACHE_DIR)

    assert cache_dir.parent == Path(config.CACHE_DIR)
    assert cache_dir.is_dir()
    assert Path(yf_cache._CookieDBManager._cache_dir) == cache_dir

    probe = cache_dir / ".write-test"
    probe.write_text("ok", encoding="utf-8")
    try:
        assert probe.read_text(encoding="utf-8") == "ok"
    finally:
        probe.unlink(missing_ok=True)


def test_release_mode_uses_local_app_data_not_bundle():
    root = Path(__file__).resolve().parents[1]
    data_root = root / "output" / f".release-data-test-{uuid.uuid4().hex}"
    env = {
        **os.environ,
        "TWSTOCK_APP_MODE": "release",
        "TWSTOCK_DATA_ROOT": str(data_root),
    }
    code = (
        "import json,config;"
        "print(json.dumps({'mode':config.APP_MODE,'data':config.DATA_ROOT,"
        "'cache':config.CACHE_DIR,'output':config.OUTPUT_DIR}))"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout.strip())
        assert payload["mode"] == "release"
        assert Path(payload["data"]) == data_root
        assert Path(payload["cache"]).is_relative_to(data_root)
        assert Path(payload["output"]).is_relative_to(data_root)
    finally:
        if data_root.is_dir() and data_root.parent == root / "output":
            shutil.rmtree(data_root)


def test_web_mode_uses_supplied_temporary_data_root():
    root = Path(__file__).resolve().parents[1]
    data_root = root / "output" / f".web-data-test-{uuid.uuid4().hex}"
    env = {
        **os.environ,
        "TWSTOCK_APP_MODE": "web",
        "TWSTOCK_DATA_ROOT": str(data_root),
    }
    code = (
        "import json,config;"
        "print(json.dumps({'mode':config.APP_MODE,'web':config.IS_WEB_MODE,"
        "'data':config.DATA_ROOT,'output_max':config.OUTPUT_MAX_BYTES}))"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout.strip())
        assert payload["mode"] == "web"
        assert payload["web"] is True
        assert Path(payload["data"]) == data_root
        assert payload["output_max"] == 48 * 1024 * 1024
    finally:
        if data_root.is_dir() and data_root.parent == root / "output":
            shutil.rmtree(data_root)


def test_web_main_uses_platform_port_and_public_binding(monkeypatch):
    captured = {}
    monkeypatch.setenv("PORT", "5188")
    monkeypatch.setattr(
        webui,
        "run_server",
        lambda port, host: captured.update({"port": port, "host": host}),
    )

    assert webui.web_main() == 0
    assert captured == {"port": 5188, "host": "0.0.0.0"}


def test_yfinance_cache_database_errors_are_recoverable():
    assert peewee.OperationalError in YFINANCE_EXCEPTIONS


def test_cli_returns_failure_exit_code_when_analysis_fails(monkeypatch):
    monkeypatch.setattr(main, "batch_mode", lambda _query: None)

    assert main.cli(["0050"]) == 1


def test_cli_returns_success_exit_code_when_report_exists(monkeypatch):
    monkeypatch.setattr(main, "batch_mode", lambda _query: "output/0050_report.pdf")

    assert main.cli(["0050"]) == 0


def test_waitress_shutdown_closes_keep_alive_channels():
    def test_app(_environ, start_response):
        start_response("204 No Content", [])
        return [b""]

    server = create_server(test_app, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.run, daemon=True)
    client = None
    try:
        thread.start()
        client = socket.create_connection(
            ("127.0.0.1", server.effective_port), timeout=2
        )
        client.sendall(
            b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
        )
        assert b"204 No Content" in client.recv(4096)

        _close_waitress_server(server)
        thread.join(timeout=3)

        assert not thread.is_alive()
        assert not server._map
    finally:
        if client is not None:
            client.close()
        if thread.is_alive():
            _close_waitress_server(server)
