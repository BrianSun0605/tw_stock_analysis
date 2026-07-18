import json
import threading
from pathlib import Path
from types import SimpleNamespace

import webui


def _sse_messages(response):
    messages = []
    for line in response.get_data(as_text=True).splitlines():
        if line.startswith("data: "):
            messages.append(json.loads(line[6:]))
    return [message for message in messages if message.get("type") != "ping"]


def _clear_tasks():
    with webui.tasks_lock:
        webui.tasks.clear()


def test_preview_is_queryable_before_pdf_finishes(monkeypatch):
    preview_ready = threading.Event()
    finish_report = threading.Event()
    preview = {"stock": {"stock_id": "0050", "name": "元大台灣50"}}

    def fake_analyze(query, *, progress, preview_callback, report_progress):
        progress("[5/5] 組裝分析結果")
        preview_callback(preview)
        preview_ready.set()
        assert finish_report.wait(timeout=2)
        report_progress(1, 1, "完成報告")
        return SimpleNamespace(
            preview=preview,
            output_path=str(Path("output") / "0050_report_test.pdf"),
        )

    _clear_tasks()
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "0050"}).get_json()["task_id"]

    try:
        assert preview_ready.wait(timeout=1)
        snapshot = client.get(f"/task/{task_id}")
        assert snapshot.status_code == 200
        payload = snapshot.get_json()
        assert payload["status"] == "reporting"
        assert payload["preview"] == preview
        assert payload["filename"] is None
    finally:
        finish_report.set()

    messages = _sse_messages(client.get(f"/stream/{task_id}"))
    assert [message["type"] for message in messages][-3:] == ["result", "report", "done"]


def test_completed_task_and_events_survive_stream_disconnect(monkeypatch):
    preview = {"stock": {"stock_id": "2330", "name": "台積電"}}

    def fake_analyze(query, *, progress, preview_callback, report_progress):
        progress("[1/5] 取得基本資訊與股價資料")
        preview_callback(preview)
        report_progress(1, 2, "標題頁")
        report_progress(2, 2, "免責聲明")
        return SimpleNamespace(
            preview=preview,
            output_path=str(Path("output") / "2330_report_test.pdf"),
        )

    _clear_tasks()
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "2330"}).get_json()["task_id"]
    first_stream = _sse_messages(client.get(f"/stream/{task_id}"))

    assert [message["type"] for message in first_stream] == [
        "log", "result", "report", "report", "done",
    ]
    snapshot = client.get(f"/task/{task_id}")
    assert snapshot.status_code == 200
    assert snapshot.get_json()["status"] == "completed"
    assert snapshot.get_json()["filename"] == "2330_report_test.pdf"

    result_event_id = next(
        message["id"] for message in first_stream if message["type"] == "result"
    )
    replay = _sse_messages(client.get(
        f"/stream/{task_id}",
        headers={"Last-Event-ID": str(result_event_id)},
    ))
    assert [message["type"] for message in replay] == ["report", "report", "done"]
