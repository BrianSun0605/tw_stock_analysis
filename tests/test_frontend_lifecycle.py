from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_template_exposes_analysis_and_report_lifecycle():
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for element_id in (
        "progressState",
        "progressDetail",
        "analysisSteps",
        "reportProgress",
        "reportProgressBar",
        "connectionNotice",
        "progressDownloadPdf",
        "retryAnalysis",
        "analyzeAnother",
        "resultStatus",
        "generatePdf",
        "cancelTask",
    ):
        assert f'id="{element_id}"' in template
    assert "PDF 報告" in template
    assert "分析結果" in template


def test_frontend_can_recover_task_and_preserve_preview():
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    api = (ROOT / "static" / "js" / "api.js").read_text(encoding="utf-8")
    assert "getTask" in api
    assert "Last-Event-ID" not in api  # EventSource manages this header itself.
    assert "sessionStorage" in app
    assert "recoverTask" in app
    assert "handlePreview" in app
    assert "handleReportProgress" in app
    assert "requestReport" in api
    assert "cancelTask" in api
    assert "generatePdf" in app
    assert "分析結果已可查看" in app
    assert "PDF 報告已完成" in app
    # A completed report is downloadable from the workflow panel only; the
    # result-card duplicate is deliberately hidden.
    assert 'for (const id of ["progressDownloadPdf"])' in app
    assert 'byId("downloadPdf").hidden = true;' in app


def test_service_worker_refreshes_changed_static_assets():
    worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert 'CACHE_NAME = "tw-stock-v24"' in worker
    assert '"/static/js/learning.js"' in worker
    assert '"/static/js/learning-curriculum.js"' in worker
    assert "networkFirst" in worker
    assert 'url.pathname === "/"' in worker
    assert '  "/",' not in worker
    assert 'updateViaCache: "none"' in app
