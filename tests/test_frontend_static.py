from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_template_has_no_inline_script_or_event_handlers():
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "onclick=" not in template
    assert "<style" not in template
    assert '<script type="module" src="/static/js/app.js?v=20"></script>' in template


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


def test_etf_layout_has_its_own_structure_and_does_not_show_company_scores():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "static" / "js" / "render.js").read_text(encoding="utf-8")
    for element_id in (
        "growthModelCard",
        "healthPanel",
        "financialPanel",
        "peerPanel",
        "qualityPanel",
        "valuationPanel",
    ):
        assert f'id="{element_id}"' in html
    assert "function applyAssetLayout(data)" in javascript
    assert 'setHidden("growthModelCard", isEtf)' in javascript
    assert 'setKpi("Pe", "NAV 淨值"' in javascript
    assert 'metric("折溢價"' in javascript


def test_kpis_are_grouped_by_beginner_facing_decision_question():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "static" / "js" / "render.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "app.css").read_text(encoding="utf-8")
    for title in ("價格與估值", "公司體質與成長", "收益"):
        assert title in html
    assert "市價與淨值" in javascript
    assert "基金結構" in javascript
    assert ".kpi-summary" in css


def test_learning_curriculum_has_local_bilingual_progress_tracks_and_quick_terms():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    learning = (ROOT / "static" / "js" / "learning.js").read_text(encoding="utf-8")
    curriculum = (ROOT / "static" / "js" / "learning-curriculum.js").read_text(
        encoding="utf-8"
    )
    renderer = (ROOT / "static" / "js" / "render.js").read_text(encoding="utf-8")
    service_worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")
    assert 'id="learningDialog"' in html
    assert 'id="openLearning"' in html
    assert html.count('class="learn-term"') == 6
    assert "twstock.learning.progress.v3" in learning
    assert "twstock.learning.progress.v1" in learning
    assert "localStorage" in learning
    assert "COURSE_TRACKS" in curriculum
    assert "TOPIC_LIBRARY.flatMap" in curriculum
    assert "220 local questions" in curriculum
    assert "localized(value" in curriculum
    assert "chartAid" in learning
    assert "orderForReview" in learning
    assert "favoriteButton" in learning
    assert "clearAnswerRecords" in learning
    assert 'setLearningTerm("kpiPeCard", "nav")' in renderer
    assert '"/static/js/learning.js"' in service_worker
    assert '"/static/js/learning-curriculum.js"' in service_worker


def test_beginner_mode_is_local_rule_based_and_preserves_advanced_content():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    beginner = (ROOT / "static" / "js" / "beginner.js").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")
    for element_id in (
        "beginnerModeButton",
        "advancedModeButton",
        "beginnerGuide",
        "predictionPanel",
        "kpiSummary",
        "advancedDashboard",
    ):
        assert f'id="{element_id}"' in html
    assert "twstock.view-mode.v1" in beginner
    assert "localStorage" in beginner
    assert "data.model_assessments" in beginner
    assert "updateBeginnerGuide(data)" in app
    assert '"/static/js/beginner.js"' in worker


def test_news_and_source_details_are_collapsed_until_requested():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "app.css").read_text(encoding="utf-8")
    for detail_id in ("newsDetails", "sourceDetails", "companyDetails"):
        assert f'<details id="{detail_id}"' in html
    assert "collapsible-panel" in css


def test_model_formula_disclosure_is_available_without_forcing_a_rating():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    renderer = (ROOT / "static" / "js" / "render.js").read_text(encoding="utf-8")
    for element_id in (
        "growthFormulaDetails",
        "safetyFormulaDetails",
        "modelDisclaimer",
    ):
        assert f'id="{element_id}"' in html
    assert "growthFormulaContent" in renderer
    assert "safetyFormulaContent" in renderer
    assert "reference_formula_not_locally_validated" in renderer
    assert "reference_estimate" in renderer
    assert "reference_rating_rule" in renderer


def test_english_rendering_has_explicit_dynamic_localization_paths():
    renderer = (ROOT / "static" / "js" / "render.js").read_text(encoding="utf-8")
    translations = (ROOT / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    assert "function localizedRiskMessage" in renderer
    assert "Health-data coverage is" in renderer
    assert "Growth reference tier (formal validation pending)" in translations
    assert (
        "Financial-structure reference tier (formal validation pending)" in translations
    )
    assert '"例如：2330、台積電": "Example: 2330, TSMC"' in translations
