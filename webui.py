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

from flask import (
    Flask,
    Response,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)

from config import OUTPUT_DIR
from services.analysis import (
    AnalysisCancelled,
    AnalysisError,
    analyze as analyze_service,
    generate_report as generate_report_service,
)
from stock.normalizer import refresh_security_registry_if_due, search_stock
from utils.logger import get_logger
from storage.cleanup import cleanup_runtime_storage, remove_task_artifacts
from version import __version__

logger = get_logger(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
PICTURE_DIR = os.path.join(BASE, "picture")
ICON_DIR = os.path.join(PICTURE_DIR, "icon")
MAX_TASKS = 1
TASK_DEADLINE_SECONDS = 180
REPORT_DEADLINE_SECONDS = 180
MAX_TASK_RESULT_BYTES = 64 * 1024 * 1024
MAX_TASK_EVENT_BYTES = 4 * 1024 * 1024
MAX_TASK_EVENTS = 200
TASK_TTL_SECONDS = 3600
COMPLETED_TASK_TTL_SECONDS = 600
ACTIVE_TASK_STATES = {"queued", "analyzing", "reporting", "cancelling"}
TERMINAL_TASK_STATES = {"ready", "completed", "failed", "cancelled"}
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


def _serialized_size(value) -> int:
    return len(
        json.dumps(
            _json_safe(value),
            ensure_ascii=False,
            default=_json_default,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _estimated_size(value, seen=None) -> int:
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)
    if hasattr(value, "memory_usage"):
        try:
            usage = value.memory_usage(index=True, deep=True)
            return int(usage.sum() if hasattr(usage, "sum") else usage)
        except (TypeError, ValueError, AttributeError):
            pass
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(
            _estimated_size(key, seen) + _estimated_size(item, seen)
            for key, item in value.items()
        )
    elif isinstance(value, (list, tuple, set)):
        size += sum(_estimated_size(item, seen) for item in value)
    elif hasattr(value, "__dict__"):
        size += _estimated_size(vars(value), seen)
    return size


def _prune_tasks() -> None:
    now = time.time()
    with tasks_lock:
        stale = []
        for task_id, task in tasks.items():
            age = now - task["updated_at"]
            if task["status"] in {"completed", "failed"}:
                expired = age > COMPLETED_TASK_TTL_SECONDS
            elif task["status"] == "ready":
                expired = age > TASK_TTL_SECONDS
            else:
                expired = now - task["created_at"] > TASK_TTL_SECONDS
            if expired:
                stale.append(task_id)
        for task_id in stale:
            tasks.pop(task_id, None)
    for task_id in stale:
        remove_task_artifacts(task_id)


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
        "can_generate_report": (
            task["status"] == "ready" and task.get("analysis_result") is not None
        ),
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
            preview_bytes = _serialized_size(preview)
            if preview_bytes > MAX_TASK_RESULT_BYTES:
                raise AnalysisError("分析結果超過 64 MiB 記憶體上限，已停止工作。")
            event["data"] = preview
            task["preview"] = preview
            task["status"] = "analyzing"
            task["message"] = "分析結果已可查看"
        elif event_type == "report":
            report = _json_safe(value or {})
            event.update(report)
            task["report"] = report
            task["status"] = "reporting"
        elif event_type == "done":
            filename = os.path.basename(value) if value else None
            event["filename"] = filename
            task["filename"] = filename
            task["status"] = "completed" if filename else "ready"
            task["message"] = (
                "分析與 PDF 報告已完成" if filename else "分析已完成，可按需產生 PDF"
            )
        elif event_type == "report_error":
            message = str(value or "PDF 報告產生失敗，請稍後再試。")
            event["msg"] = message
            task["error"] = message
            task["status"] = "ready"
            task["message"] = message
        elif event_type == "error":
            message = str(value or "分析失敗，請稍後再試。")
            event["msg"] = message
            task["error"] = message
            task["status"] = "failed"
            task["message"] = message
        elif event_type == "cancelled":
            message = str(value or "工作已取消。")
            event["msg"] = message
            task["error"] = None
            task["status"] = "cancelled"
            task["message"] = message
        else:
            raise ValueError(f"unsupported task event: {event_type}")

        task["updated_at"] = now
        event_bytes = _serialized_size(event)
        task["events"].append(event)
        task["event_bytes"] += event_bytes
        while (
            len(task["events"]) > MAX_TASK_EVENTS
            or task["event_bytes"] > MAX_TASK_EVENT_BYTES
        ):
            removed = task["events"].pop(0)
            task["event_bytes"] -= _serialized_size(removed)
        task["condition"].notify_all()


def _run_analysis(query: str, task_id: str) -> None:
    preview_published = False

    def publish_preview(preview):
        nonlocal preview_published
        preview_published = True
        _publish(task_id, "result", preview)

    def publish_report_progress(current, total, section):
        _publish(
            task_id,
            "report",
            {
                "current": int(current),
                "total": int(total),
                "section": str(section),
            },
        )

    try:
        result = analyze_service(
            query,
            generate_report=False,
            artifact_id=task_id,
            progress=lambda message: _publish(task_id, "log", message),
            preview_callback=publish_preview,
            report_progress=publish_report_progress,
            cancel_event=tasks[task_id]["cancel_event"],
            deadline=tasks[task_id]["deadline"],
        )
        if not preview_published:
            publish_preview(result.preview)
        with tasks_lock:
            task = tasks.get(task_id)
            if task:
                if _estimated_size(result) > MAX_TASK_RESULT_BYTES:
                    raise AnalysisError(
                        "分析工作資料超過 64 MiB 記憶體上限，已停止工作。"
                    )
                task["analysis_result"] = result
        _publish(task_id, "done", None)
    except AnalysisCancelled as exc:
        _publish(task_id, "cancelled", str(exc))
        remove_task_artifacts(task_id)
    except AnalysisError as exc:
        message = str(exc)
        _publish(task_id, "error", message)
    except Exception:
        logger.exception("web analysis failed for %s", query)
        _publish(task_id, "error", "分析過程發生異常，請稍後再試。")


def _run_report(task_id: str) -> None:
    def publish_report_progress(current, total, section):
        _publish(
            task_id,
            "report",
            {
                "current": int(current),
                "total": int(total),
                "section": str(section),
            },
        )

    with tasks_lock:
        task = tasks.get(task_id)
        result = task.get("analysis_result") if task else None
        cancel_event = task.get("cancel_event") if task else None
        deadline = task.get("deadline") if task else None
    if result is None:
        _publish(task_id, "report_error", "分析資料已過期，請重新分析後再產生 PDF。")
        return
    try:
        output_path = generate_report_service(
            result,
            progress_callback=publish_report_progress,
            cancel_event=cancel_event,
            deadline=deadline,
        )
        _publish(task_id, "done", os.path.basename(output_path))
        with tasks_lock:
            task = tasks.get(task_id)
            if task:
                task["analysis_result"] = None
        remove_task_artifacts(task_id)
    except AnalysisCancelled as exc:
        _publish(task_id, "cancelled", str(exc))
        with tasks_lock:
            task = tasks.get(task_id)
            if task:
                task["analysis_result"] = None
        remove_task_artifacts(task_id)
    except AnalysisError as exc:
        _publish(task_id, "report_error", str(exc))
    except Exception:
        logger.exception("PDF report failed for task %s", task_id)
        _publish(task_id, "report_error", "PDF 報告產生失敗，分析結果仍保留。")


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
    if not testing:
        cleanup_runtime_storage(force=True)

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
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
        response = make_response(
            render_template(
                "index.html",
                shutdown_token=app.config["SHUTDOWN_TOKEN"],
            )
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/search")
    def search():
        query = _valid_query(request.args.get("q", ""))
        if not query:
            return jsonify([])
        results = search_stock(query)
        return jsonify(
            [
                {
                    "stock_id": item["stock_id"],
                    "name": item["name"],
                    "industry": item.get("industry", ""),
                    "market": item.get("market", ""),
                    "asset_type": item.get("asset_type", ""),
                }
                for item in results[:20]
            ]
        )

    @app.get("/picture/<folder>/<filename>")
    def picture_file(folder, filename):
        directory = ICON_DIR if folder == "icon" else None
        if not directory:
            return "Not Found", 404
        return send_from_directory(directory, filename)

    @app.post("/analyze")
    def start_analysis():
        payload = request.get_json(silent=True)
        query = _valid_query(
            payload.get("query") if isinstance(payload, dict) else None
        )
        if not query:
            return jsonify({"error": "請輸入 1–64 字的股票代號或名稱"}), 400
        _prune_tasks()
        with tasks_lock:
            active_count = sum(
                task["status"] in ACTIVE_TASK_STATES for task in tasks.values()
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
                "event_bytes": 0,
                "next_event_id": 1,
                "created_at": now,
                "updated_at": now,
                "thread": None,
                "analysis_result": None,
                "cancel_event": threading.Event(),
                "deadline": now + TASK_DEADLINE_SECONDS,
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

    @app.post("/task/<task_id>/report")
    def start_report(task_id):
        _prune_tasks()
        with tasks_lock:
            task = tasks.get(task_id)
            if not task:
                return jsonify({"error": "任務不存在或已過期"}), 404
            if task["status"] == "completed" and task.get("filename"):
                return jsonify({"error": "PDF 報告已經完成"}), 409
            if task["status"] != "ready" or task.get("analysis_result") is None:
                return jsonify({"error": "目前無法產生 PDF，請等待分析完成"}), 409
            active_count = sum(
                other["status"] in ACTIVE_TASK_STATES
                for other_id, other in tasks.items()
                if other_id != task_id
            )
            if active_count >= MAX_TASKS:
                return jsonify({"error": "目前有其他工作執行中，請稍後再試"}), 429
            task["status"] = "reporting"
            task["message"] = "正在產生 PDF 報告"
            task["error"] = None
            task["report"] = {"current": 0, "total": 0, "section": ""}
            task["updated_at"] = time.time()
            task["cancel_event"] = threading.Event()
            task["deadline"] = time.time() + REPORT_DEADLINE_SECONDS
            thread = threading.Thread(
                target=_run_report,
                args=(task_id,),
                daemon=True,
                name=f"report-{task_id[:8]}",
            )
            task["thread"] = thread
            thread.start()
        return jsonify({"task_id": task_id, "status": "reporting"}), 202

    @app.post("/task/<task_id>/cancel")
    def cancel_task(task_id):
        with tasks_lock:
            task = tasks.get(task_id)
            if not task:
                return jsonify({"error": "任務不存在或已過期"}), 404
            if task["status"] not in ACTIVE_TASK_STATES:
                return jsonify({"error": "工作已結束，無法取消"}), 409
            task["cancel_event"].set()
            task["status"] = "cancelling"
            task["message"] = "正在取消工作"
            task["updated_at"] = time.time()
            task["condition"].notify_all()
        return jsonify({"task_id": task_id, "status": "cancelling"}), 202

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
                    pending = [
                        event for event in task["events"] if event["id"] > cursor
                    ]
                    terminal = task["status"] in TERMINAL_TASK_STATES
                    if not pending and not terminal:
                        task["condition"].wait(timeout=15)
                        pending = [
                            event for event in task["events"] if event["id"] > cursor
                        ]
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
        if filename != os.path.basename(filename) or not filename.lower().endswith(
            ".pdf"
        ):
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
        return jsonify(
            {
                "name": "台股投資分析工具",
                "short_name": "台股分析",
                "version": __version__,
                "start_url": "/",
                "display": "standalone",
                "background_color": "#f5f7fa",
                "theme_color": "#123047",
                "icons": [
                    {
                        "src": "/picture/icon/app-icon.svg",
                        "sizes": "any",
                        "type": "image/svg+xml",
                    },
                ],
            }
        )

    return app


app = create_app()


def _open_browser(port: int) -> None:
    if os.getenv("TWSTOCK_NO_BROWSER") == "1":
        return

    def open_later():
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=open_later, daemon=True).start()


def _close_waitress_server(server) -> None:
    """Stop accepting requests, drain workers, and close keep-alive channels."""
    from waitress import wasyncore

    server.close()
    server.task_dispatcher.shutdown()
    channel_map = getattr(server, "_map", getattr(server, "map", None))
    if channel_map is not None:
        wasyncore.close_all(channel_map, ignore_all=True)


def run_server(port: int = 5000) -> None:
    from waitress import create_server

    threading.Thread(
        target=refresh_security_registry_if_due,
        daemon=True,
        name="security-registry-refresh",
    ).start()
    server = create_server(app, host="127.0.0.1", port=port)
    app.config["SHUTDOWN_CALLBACK"] = lambda: _close_waitress_server(server)
    logger.info("啟動 Web UI：http://127.0.0.1:%s", port)
    _open_browser(port)
    server.run()


def desktop_main(argv=None) -> int:
    from app_runtime.single_instance import SingleInstance
    from config import DATA_ROOT

    args = list(sys.argv[1:] if argv is None else argv)
    try:
        port = int(args[0]) if args else 5000
    except ValueError:
        logger.error("連接埠必須是 1～65535 的整數")
        return 2
    if not 1 <= port <= 65535:
        logger.error("連接埠必須是 1～65535 的整數")
        return 2
    instance = SingleInstance(DATA_ROOT)
    if not instance.acquire():
        state = instance.read_state()
        existing_port = int(state.get("port") or port)
        if os.getenv("TWSTOCK_NO_BROWSER") != "1":
            webbrowser.open(f"http://127.0.0.1:{existing_port}")
        logger.info("App 已在執行，已開啟現有服務。")
        return 0
    try:
        instance.write_state(port=port, version=__version__)
        run_server(port)
        return 0
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(desktop_main())
