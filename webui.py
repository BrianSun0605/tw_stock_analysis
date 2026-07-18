#!/usr/bin/env python3
import hmac
import json
import os
import queue
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

tasks = {}
tasks_lock = threading.RLock()


def _valid_query(value) -> str:
    if not isinstance(value, str):
        return ""
    value = " ".join(value.strip().split())
    return value if 0 < len(value) <= 64 else ""


def _prune_tasks() -> None:
    cutoff = time.time() - TASK_TTL_SECONDS
    with tasks_lock:
        stale = [
            task_id for task_id, task in tasks.items()
            if task["created_at"] < cutoff
            or (task.get("thread") and not task["thread"].is_alive() and task["queue"].empty())
        ]
        for task_id in stale:
            tasks.pop(task_id, None)


def _run_analysis(query: str, log_queue: queue.Queue) -> None:
    try:
        result = analyze_service(
            query,
            progress=lambda message: log_queue.put(("log", message)),
        )
        log_queue.put(("result", result.preview))
        filename = os.path.basename(result.output_path) if result.output_path else None
        log_queue.put(("done", filename))
    except AnalysisError as exc:
        log_queue.put(("error", str(exc)))
    except Exception:
        logger.exception("web analysis failed for %s", query)
        log_queue.put(("error", "分析過程發生異常，請稍後再試。"))


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
            if len(tasks) >= MAX_TASKS:
                return jsonify({"error": "目前分析任務已滿，請稍後再試"}), 429
            task_id = uuid.uuid4().hex
            task_queue = queue.Queue()
            thread = threading.Thread(
                target=_run_analysis,
                args=(query, task_queue),
                daemon=True,
                name=f"analysis-{task_id[:8]}",
            )
            tasks[task_id] = {
                "queue": task_queue,
                "thread": thread,
                "created_at": time.time(),
            }
            thread.start()
        return jsonify({"task_id": task_id}), 202

    @app.get("/stream/<task_id>")
    def stream(task_id):
        with tasks_lock:
            task = tasks.get(task_id)
        if not task:
            return jsonify({"error": "任務不存在或已過期"}), 404

        def events():
            task_queue = task["queue"]
            thread = task["thread"]
            try:
                while True:
                    try:
                        event_type, value = task_queue.get(timeout=20)
                    except queue.Empty:
                        if not thread.is_alive():
                            yield f"data: {json.dumps({'type': 'error', 'msg': '分析執行緒意外終止'}, ensure_ascii=False)}\n\n"
                            return
                        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                        continue
                    payload = {"type": event_type}
                    if event_type == "result":
                        payload["data"] = value
                    elif event_type == "done":
                        payload["filename"] = value
                    else:
                        payload["msg"] = value
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    if event_type in ("done", "error"):
                        return
            finally:
                with tasks_lock:
                    tasks.pop(task_id, None)

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
