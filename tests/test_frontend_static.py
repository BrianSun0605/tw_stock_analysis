from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_template_has_no_inline_script_or_event_handlers():
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "onclick=" not in template
    assert "<style" not in template
    assert '<script type="module" src="/static/js/app.js?v=7"></script>' in template


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


def test_results_use_focus_without_announcing_the_whole_page():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    result_tag = html.split('id="resultView"', 1)[1].split(">", 1)[0]
    assert 'tabindex="-1"' in result_tag
    assert 'aria-labelledby="stockName"' in result_tag
    assert "aria-live" not in result_tag


def test_interactive_controls_follow_minimum_touch_target():
    css = (ROOT / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert ".button { min-height: 44px;" in css
    assert ".icon-button { width: 44px; height: 44px;" in css
    assert ".quick-picks button { min-height: 44px;" in css


def test_page_does_not_force_horizontal_scroll_below_320px():
    css = (ROOT / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "body { margin: 0; min-width: 0;" in css
    assert "body { margin: 0; min-width: 320px;" not in css
    assert ".source-list { grid-template-columns: minmax(0, 1fr);" in css
    assert ".source-list dd { min-width: 0;" in css
