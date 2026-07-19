import math
from types import SimpleNamespace

import webui


def test_sse_preview_replaces_non_finite_numbers_with_null(monkeypatch):
    preview = {
        "stock": {"stock_id": "0050", "name": "元大台灣50"},
        "metrics": {
            "nan": float("nan"),
            "positive_infinity": float("inf"),
            "negative_infinity": float("-inf"),
        },
    }

    def fake_analyze(query, **kwargs):
        kwargs["preview_callback"](preview)
        return SimpleNamespace(
            preview=preview,
            output_path=None,
            report_context={"stock_info": preview["stock"]},
        )

    with webui.tasks_lock:
        webui.tasks.clear()
    monkeypatch.setattr(webui, "analyze_service", fake_analyze)
    client = webui.create_app(testing=True).test_client()
    task_id = client.post("/analyze", json={"query": "0050"}).get_json()["task_id"]
    response_text = client.get(f"/stream/{task_id}").get_data(as_text=True)
    snapshot = client.get(f"/task/{task_id}").get_json()

    assert "NaN" not in response_text
    assert "Infinity" not in response_text
    assert snapshot["preview"]["metrics"] == {
        "nan": None,
        "positive_infinity": None,
        "negative_infinity": None,
    }
    assert all(
        value is None or math.isfinite(value)
        for value in snapshot["preview"]["metrics"].values()
    )
