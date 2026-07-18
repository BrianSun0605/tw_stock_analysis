from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_template_has_no_inline_script_or_event_handlers():
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "onclick=" not in template
    assert "<style" not in template
    assert '<script type="module" src="/static/js/app.js?v=4"></script>' in template


def test_frontend_avoids_html_injection_sinks():
    javascript = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "static" / "js").glob("*.js")
    )
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert sink not in javascript
    assert "textContent" in javascript


def test_service_worker_does_not_cache_dynamic_routes():
    service_worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")
    for route in ("/analyze", "/stream/", "/download/", "/shutdown", "/search"):
        assert route in service_worker
    assert 'request.method !== "GET"' in service_worker


def test_csv_export_neutralizes_formula_prefixes():
    exporter = (ROOT / "static" / "js" / "export.js").read_text(encoding="utf-8")
    assert "spreadsheetSafe" in exporter
    assert "[=+\\-@]" in exporter
    assert "replaceAll" in exporter
