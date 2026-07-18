#!/usr/bin/env python3
import hmac
import json
import math
import os
import re
import secrets
import sys
import threading
import time
import uuid
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from config import OUTPUT_DIR
from services.analysis import AnalysisError, analyze as analyze_service
from stock.normalizer import normalize, search_stock
from utils.logger import get_logger

logger = get_logger(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
PICTURE_DIR = os.path.join(BASE, "picture")
ICON_DIR = os.path.join(PICTURE_DIR, "icon")
MAX_TASKS = 20
TASK_TTL_SECONDS = 3600
COMPLETED_TASK_TTL_SECONDS = 600
TERMINAL_TASK_STATES = {"completed", "failed"}
STEP_PATTERN = re.compile(r"^\[(\d+)/(\d+)\]\s*(.*)$")

tasks = {}
tasks_lock = threading.RLock()


def _valid_query(value) -> str:
    if not isinstance(value, str):
        return ""
    value = " ".join(value.strip().split())
    return value if 0 < len(value) <= 64 else ""


def _json_safe(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_default(value):
    return _json_safe(value)


def _prune_tasks() -> None:
    now = time.time()
    with tasks_lock:
        stale = []
        for task_id, task in tasks.items():
            age = now - task["updated_at"]
            if task["status"] in TERMINAL_TASK_STATES:
                expired = age > COMPLETED_TASK_TTL_SECONDS
            else:
                expired = now - task["created_at"] > TASK_TTL_SECONDS
            if expired:
                stale.append(task_id)
        for task_id in stale:
            tasks.pop(task_id, None)


def _task_snapshot(task_id, task):
    return {
        "task_id": task_id,
        "query": task["query"],
        "status": task["status"],
        "stage": task["stage"],
        "stage_total": task["stage_total"],
        "message": task["message"],
        "report": task["report"],
        "preview": task["preview"],
        "filename": task["filename"],
        "error": task["error"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
    }


def _publish(task_id: str, event_type: str, value=None) -> None:
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return
        event = {"id": task["next_event_id"], "type": event_type}
        task["next_event_id"] += 1
        now = time.time()

        if event_type == "log":
            message = str(value or "")
            event["msg"] = message
            task["message"] = message
            match = STEP_PATTERN.match(message)
            if match:
                task["stage"] = int(match.group(1))
                task["stage_total"] = int(match.group(2))
            if task["status"] == "queued":
                task["status"] = "analyzing"
        elif event_type == "result":
            preview = _json_safe(value or {})
            event["data"] = preview
            task["preview"] = preview
            task["status"] = "reporting"
            task["message"] = "分析結果已可查看，正在產生 PDF 報告"
        elif event_type == "report":
            report = _json_safe(value or {})
            event.update(report)
            task["report"] = report
            task["status"] = "reporting"
        elif event_type == "done":
            filename = os.path.basename(value) if value else None
            event["filename"] = filename
            task["filename"] = filename
            task["status"] = "completed"
            task["message"] = "分析與 PDF 報告已完成"
        elif event_type == "error":
            message = str(value or "分析失敗，請稍後再試。")
            event["msg"] = message
            task["error"] = message
            task["status"] = "failed"
            task["message"] = message
        else:
            raise ValueError(f"unsupported task event: {event_type}")

        task["updated_at"] = now
        task["events"].append(event)
        task["condition"].notify_all()


def _run_analysis(query: str, task_id: str) -> None:
    preview_published = False

    def publish_preview(preview):
        nonlocal preview_published
        preview_published = True
        _publish(task_id, "result", preview)

    def publish_report_progress(current, total, section):
        _publish(task_id, "report", {
            "current": int(current),
            "total": int(total),
            "section": str(section),
        })

    try:
        result = analyze_service(
            query,
            progress=lambda message: _publish(task_id, "log", message),
            preview_callback=publish_preview,
            report_progress=publish_report_progress,
        )
        if not preview_published:
            publish_preview(result.preview)
        filename = os.path.basename(result.output_path) if result.output_path else None
        _publish(task_id, "done", filename)
    except AnalysisError as exc:
        message = str(exc)
        if preview_published:
            message = f"分析結果已完成，但 PDF 報告產生失敗：{message}"
        _publish(task_id, "error", message)
    except Exception:
        logger.exception("web analysis failed for %s", query)
        message = (
            "分析結果已完成，但 PDF 報告產生失敗，請重新執行。"
            if preview_published else "分析過程發生異常，請稍後再試。"
        )
        _publish(task_id, "error", message)


def _last_event_id() -> int:
    raw = request.headers.get("Last-Event-ID") or request.args.get("after", "0")
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def create_app(*, testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(
        TESTING=testing,
        SHUTDOWN_TOKEN=secrets.token_urlsafe(32),
        SHUTDOWN_CALLBACK=None,
    )
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "style-src 'self'; "
            "connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            shutdown_token=app.config["SHUTDOWN_TOKEN"],
        )

    @app.get("/search")
    def search():
        query = _valid_query(request.args.get("q", ""))
        if not query:
            return jsonify([])
        results = search_stock(query)
        if not results:
            stock = normalize(query)
            results = [stock] if stock.get("stock_id") else []
        return jsonify([
            {
                "stock_id": item["stock_id"],
                "name": item["name"],
                "industry": item.get("industry", ""),
                "market": item.get("market", ""),
            }
            for item in results[:20]
        ])

    @app.get("/picture/<folder>/<filename>")
    def picture_file(folder, filename):
        directory = ICON_DIR if folder == "icon" else None
        if not directory:
            return "Not Found", 404
        return send_from_directory(directory, filename)

    @app.post("/analyze")
    def start_analysis():
        payload = request.get_json(silent=True)
        query = _valid_query(payload.get("query") if isinstance(payload, dict) else None)
        if not query:
            return jsonify({"error": "請輸入 1–64 字的股票代號或名稱"}), 400
        _prune_tasks()
        with tasks_lock:
            active_count = sum(
                task["status"] not in TERMINAL_TASK_STATES
                for task in tasks.values()
            )
            if active_count >= MAX_TASKS:
                return jsonify({"error": "目前分析任務已滿，請稍後再試"}), 429
            task_id = uuid.uuid4().hex
            now = time.time()
            task = {
                "query": query,
                "status": "queued",
                "stage": 0,
                "stage_total": 5,
                "message": "分析任務已建立",
                "report": {"current": 0, "total": 0, "section": ""},
                "preview": None,
                "filename": None,
                "error": None,
                "events": [],
                "next_event_id": 1,
                "created_at": now,
                "updated_at": now,
                "thread": None,
                "condition": threading.Condition(tasks_lock),
            }
            thread = threading.Thread(
                target=_run_analysis,
                args=(query, task_id),
                daemon=True,
                name=f"analysis-{task_id[:8]}",
            )
            task["thread"] = thread
            tasks[task_id] = task
            thread.start()
        return jsonify({"task_id": task_id, "status": "queued"}), 202

    @app.get("/task/<task_id>")
    def task_status(task_id):
        _prune_tasks()
        with tasks_lock:
            task = tasks.get(task_id)
            if not task:
                return jsonify({"error": "任務不存在或已過期"}), 404
            snapshot = _task_snapshot(task_id, task)
        response = jsonify(snapshot)
        response.headers["Cache-Control"] = "no-cache, no-store"
        return response

    @app.get("/stream/<task_id>")
    def stream(task_id):
        cursor = _last_event_id()
        with tasks_lock:
            if task_id not in tasks:
                return jsonify({"error": "任務不存在或已過期"}), 404

        def events():
            nonlocal cursor
            while True:
                with tasks_lock:
                    task = tasks.get(task_id)
                    if not task:
                        return
                    pending = [event for event in task["events"] if event["id"] > cursor]
                    terminal = task["status"] in TERMINAL_TASK_STATES
                    if not pending and not terminal:
                        task["condition"].wait(timeout=15)
                        pending = [event for event in task["events"] if event["id"] > cursor]
                        terminal = task["status"] in TERMINAL_TASK_STATES

                if pending:
                    for event in pending:
                        cursor = event["id"]
                        payload = json.dumps(
                            event,
                            ensure_ascii=False,
                            default=_json_default,
                            allow_nan=False,
                        )
                        yield f"id: {cursor}\ndata: {payload}\n\n"
                    continue
                if terminal:
                    return
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        response = Response(events(), mimetype="text/event-stream")
        response.headers["Cache-Control"] = "no-cache, no-store"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    @app.get("/download/<filename>")
    def download(filename):
        if filename != os.path.basename(filename) or not filename.lower().endswith(".pdf"):
            return "Not Found", 404
        path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.isfile(path):
            return "Not Found", 404
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

    @app.post("/shutdown")
    def shutdown():
        remote = request.remote_addr or ""
        token = request.headers.get("X-Shutdown-Token", "")
        origin = request.headers.get("Origin", "")
        host = request.host.split(":", 1)[0].lower()
        loopback = remote in ("127.0.0.1", "::1")
        allowed_host = host in ("127.0.0.1", "localhost", "::1")
        allowed_origin = not origin or origin == f"http://{request.host}"
        if not (
            loopback
            and allowed_host
            and allowed_origin
            and hmac.compare_digest(token, app.config["SHUTDOWN_TOKEN"])
        ):
            return jsonify({"error": "forbidden"}), 403
        callback = app.config.get("SHUTDOWN_CALLBACK")
        if callback:
            threading.Thread(target=callback, daemon=True).start()
        return jsonify({"status": "shutting_down"})

    @app.get("/ping")
    def ping():
        return "", 204

    @app.get("/manifest.json")
    def manifest():
        return jsonify({
            "name": "台股投資分析工具",
            "short_name": "台股分析",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f5f7fa",
            "theme_color": "#123047",
            "icons": [
                {"src": "/picture/icon/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/picture/icon/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        })

    return app


app = create_app()


def _open_browser(port: int) -> None:
    def open_later():
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=open_later, daemon=True).start()


if __name__ == "__main__":
    from waitress import create_server

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    server = create_server(app, host="127.0.0.1", port=port)
    app.config["SHUTDOWN_CALLBACK"] = server.close
    logger.info("啟動 Web UI：http://127.0.0.1:%s", port)
    _open_browser(port)
    server.run()
