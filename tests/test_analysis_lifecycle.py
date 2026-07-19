import json
import threading
from pathlib import Path
from types import SimpleNamespace

import webui
from services.analysis import AnalysisCancelled


def _sse_messages(response):
    messages = []
    for line in response.get_data(as_text=True).splitlines():
        if line.startswith("data: "):
            messages.append(json.loads(line[6:]))
    return [message for message in messages if message.get("type") != "ping"]


def _clear_tasks():
    with webui.tasks_lock:
        webui.tasks.clear()


def _result(preview):
    return SimpleNamespace(
        preview=preview,
        output_path=None,
        report_context={"stock_info": preview["stock"]},
    )


def test_release_analysis_finishes_without_automatic_pdf(monkeypatch):
    preview = {"stock": {"stock_id": "0050", "name": "元大台灣50"}}

    def fake_analyze(
        query,
        *,
        generate_report,
        artifact_id,
        progress,
        preview_callback,
        report_progress,
        cancel_event,
        deadline,
    ):
        assert generate_report is False
        assert len(artifact_id) == 32
        progress("[5/5] 組裝分析結果")
        preview_callback(preview)
        return _result(preview)

    _clear_tasks()
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "0050"}).get_json()["task_id"]
    messages = _sse_messages(client.get(f"/stream/{task_id}"))

    assert [message["type"] for message in messages] == ["log", "result", "done"]
    assert messages[-1]["filename"] is None
    snapshot = client.get(f"/task/{task_id}").get_json()
    assert snapshot["status"] == "ready"
    assert snapshot["filename"] is None
    assert snapshot["can_generate_report"] is True


def test_pdf_is_generated_only_after_explicit_request(monkeypatch):
    preview = {"stock": {"stock_id": "2330", "name": "台積電"}}

    def fake_analyze(query, **kwargs):
        kwargs["preview_callback"](preview)
        return _result(preview)

    def fake_generate(result, *, progress_callback, cancel_event, deadline):
        assert result.report_context["stock_info"]["stock_id"] == "2330"
        progress_callback(1, 1, "寫入 PDF 檔案")
        return str(Path("output") / "2330_report_unique.pdf")

    _clear_tasks()
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    monkeypatch.setattr(webui, "generate_report_service", fake_generate)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "2330"}).get_json()["task_id"]
    analysis_messages = _sse_messages(client.get(f"/stream/{task_id}"))
    cursor = analysis_messages[-1]["id"]

    response = client.post(f"/task/{task_id}/report")
    assert response.status_code == 202
    report_messages = _sse_messages(client.get(f"/stream/{task_id}?after={cursor}"))

    assert [message["type"] for message in report_messages] == ["report", "done"]
    assert report_messages[-1]["filename"] == "2330_report_unique.pdf"
    snapshot = client.get(f"/task/{task_id}").get_json()
    assert snapshot["status"] == "completed"
    assert snapshot["can_generate_report"] is False


def test_only_one_analysis_or_pdf_job_can_run(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    preview = {"stock": {"stock_id": "2330", "name": "台積電"}}

    def blocking_analyze(query, **kwargs):
        started.set()
        assert release.wait(timeout=2)
        kwargs["preview_callback"](preview)
        return _result(preview)

    _clear_tasks()
    monkeypatch.setattr(webui, "analyze_service", blocking_analyze)
    client = webui.create_app(testing=True).test_client()
    first = client.post("/analyze", json={"query": "2330"})
    assert first.status_code == 202
    assert started.wait(timeout=1)
    try:
        second = client.post("/analyze", json={"query": "1101"})
        assert second.status_code == 429
    finally:
        release.set()
    _sse_messages(client.get(f"/stream/{first.get_json()['task_id']}"))


def test_active_analysis_can_be_cancelled(monkeypatch):
    started = threading.Event()

    def fake_analyze(query, **kwargs):
        started.set()
        assert kwargs["cancel_event"].wait(timeout=2)
        raise AnalysisCancelled("工作已由使用者取消。")

    _clear_tasks()
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "2330"}).get_json()["task_id"]
    assert started.wait(timeout=1)
    response = client.post(f"/task/{task_id}/cancel")
    assert response.status_code == 202
    messages = _sse_messages(client.get(f"/stream/{task_id}"))
    assert messages[-1]["type"] == "cancelled"
    assert client.get(f"/task/{task_id}").get_json()["status"] == "cancelled"


def test_preview_memory_limit_stops_oversized_result(monkeypatch):
    def fake_analyze(query, **kwargs):
        kwargs["preview_callback"]({"payload": "x" * 100})
        return _result({})

    _clear_tasks()
    monkeypatch.setattr(webui, "MAX_TASK_RESULT_BYTES", 32)
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "2330"}).get_json()["task_id"]
    messages = _sse_messages(client.get(f"/stream/{task_id}"))
    assert messages[-1]["type"] == "error"
    assert "64 MiB" in messages[-1]["msg"]
