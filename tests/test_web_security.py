import os

from config import OUTPUT_DIR
from webui import create_app


def test_analyze_rejects_missing_or_invalid_json():
    client = create_app(testing=True).test_client()
    assert client.post("/analyze").status_code == 400
    assert client.post("/analyze", json={"query": ["2330"]}).status_code == 400
    assert client.post("/analyze", json={"query": "x" * 65}).status_code == 400


def test_shutdown_requires_loopback_token_and_same_origin():
    app = create_app(testing=True)
    client = app.test_client()
    token = app.config["SHUTDOWN_TOKEN"]
    assert client.post("/shutdown").status_code == 403
    assert client.post("/shutdown", headers={"X-Shutdown-Token": "wrong"}).status_code == 403
    assert client.post(
        "/shutdown",
        headers={"X-Shutdown-Token": token, "Origin": "https://evil.example"},
    ).status_code == 403
    assert client.post(
        "/shutdown",
        headers={"X-Shutdown-Token": token, "Origin": "http://localhost"},
    ).status_code == 200


def test_download_only_serves_existing_pdf_files():
    client = create_app(testing=True).test_client()
    assert client.get("/download/../README.md").status_code == 404
    assert client.get("/download/not-a-report.txt").status_code == 404


def test_security_headers_are_present():
    response = create_app(testing=True).test_client().get("/manifest.json")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
