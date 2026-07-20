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
    assert (
        client.post("/shutdown", headers={"X-Shutdown-Token": "wrong"}).status_code
        == 403
    )
    assert (
        client.post(
            "/shutdown",
            headers={"X-Shutdown-Token": token, "Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/shutdown",
            headers={"X-Shutdown-Token": token, "Origin": "http://localhost"},
        ).status_code
        == 200
    )


def test_download_only_serves_existing_pdf_files():
    client = create_app(testing=True).test_client()
    assert client.get("/download/../README.md").status_code == 404
    assert client.get("/download/not-a-report.txt").status_code == 404


def test_security_headers_are_present():
    response = create_app(testing=True).test_client().get("/manifest.json")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_tokenized_homepage_is_never_cached():
    response = create_app(testing=True).test_client().get("/")
    assert response.headers["Cache-Control"] == "no-store"


def test_public_mode_removes_shutdown_surface_and_has_health_check():
    app = create_app(testing=True, public_mode=True)
    client = app.test_client()

    homepage = client.get("/")
    assert app.config["PUBLIC_MODE"] is True
    assert app.config["LOCAL_SHUTDOWN_ENABLED"] is False
    assert b"shutdownApp" not in homepage.data
    assert b"shutdown-token" not in homepage.data
    assert client.post("/shutdown").status_code == 404
    assert client.get("/healthz").get_json()["status"] == "ok"


def test_public_mode_rate_limits_searches_per_client():
    app = create_app(
        testing=True,
        public_mode=True,
        enforce_rate_limits=True,
    )
    app.config["RATE_LIMITS"]["search"] = (1, 60)
    client = app.test_client()

    assert client.get("/search?q=0050").status_code == 200
    limited = client.get("/search?q=2330")
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"


def test_search_rejects_unknown_numeric_security_code():
    response = create_app(testing=True).test_client().get("/search?q=99999999")
    assert response.status_code == 200
    assert response.get_json() == []


def test_search_exposes_official_product_type():
    response = create_app(testing=True).test_client().get("/search?q=020029")
    assert response.status_code == 200
    result = response.get_json()[0]
    assert result["stock_id"] == "020029"
    assert result["asset_type"] == "etn"
