#!/usr/bin/env python3
import sys
import os
import queue
import random
import subprocess
import time
import threading
import uuid
import json
import base64
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, Response, render_template, send_from_directory

from config import OUTPUT_DIR
from utils.logger import get_logger
import shutil

# 每次啟動清空 output 目錄
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE = os.path.dirname(os.path.abspath(__file__))
PICTURE_DIR = os.path.join(BASE, "picture")
SIDE_DIR = os.path.join(PICTURE_DIR, "side")
BORDER_DIR = os.path.join(PICTURE_DIR, "border")
ICON_DIR = os.path.join(PICTURE_DIR, "icon")
CACHE_PREVIEW = {}
CACHE_PREVIEW_TTL = 300

def _img_b64(path):
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return None

def _get_cached_preview(stock_id):
    entry = CACHE_PREVIEW.get(stock_id)
    if entry and (time.time() - entry["ts"]) < CACHE_PREVIEW_TTL:
        return entry["data"]
    return None

def _set_cached_preview(stock_id, data):
    CACHE_PREVIEW[stock_id] = {"ts": time.time(), "data": data}

logger = get_logger(__name__)
from stock.normalizer import normalize, search_stock
from stock.data import (
    get_price_data,
    get_revenue_data,
    get_eps_data,
    get_basic_stock_info,
)
from stock.dividend import get_dividend_data
from stock.calendar import get_calendar_events
from stock.peers import get_peers_comparison
from news.aggregator import NewsAggregator, classify_sentiment
from valuation.analyzer import ValuationAnalyzer
from report.generator import PDFReport

app = Flask(__name__)
tasks = {}


def run_analysis(stock_id_or_name, log_queue):
    def emit(msg):
        log_queue.put(msg)

    try:
        stock_info = normalize(stock_id_or_name)
        stock_id = stock_info.get("stock_id", "")
        name = stock_info.get("name", "")
        if not stock_id:
            results = search_stock(stock_id_or_name)
            if not results:
                emit("error:查不到「{}」相關的股票，請重新輸入。".format(stock_id_or_name))
                return
            stock_info = results[0]
            stock_id = stock_info["stock_id"]
            name = stock_info["name"]

        cached_preview = _get_cached_preview(stock_id)
        if cached_preview:
            emit("result:" + json.dumps(cached_preview, ensure_ascii=False))
            emit("done:cache")
            return

        emit(f"開始分析：{name} ({stock_id})")
        emit(f"產業：{stock_info.get('industry', '未知')}")

        market = stock_info.get("market", "")

        emit("[1/5] 取得基本資訊與股價資料...")
        basic_info = get_basic_stock_info(stock_id, stock_info)
        is_etf = basic_info.get("is_etf", False)
        stock_info["is_etf"] = is_etf  # propagate for downstream (ValuationAnalyzer, NewsAggregator)
        price_data, price_info = get_price_data(stock_id, market=market)
        has_price = any(
            p.get("df") is not None and not p["df"].empty for p in price_data.values()
        )
        emit("  ✓ 股價資料" + ("完成" if has_price else "取得不完全"))

        emit("[2/5] 取得營收資料...")
        if is_etf:
            revenue_data, revenue_chart = [], None
            emit("  ⚠ ETF 無營收資料")
        else:
            revenue_data, revenue_chart = get_revenue_data(stock_id, market=market)
            emit(f"  {'✓' if revenue_data else '⚠'} 營收資料{'共 ' + str(len(revenue_data)) + ' 筆' if revenue_data else '取得不完全'}")

        emit("[3/5] 取得 EPS 資料...")
        if is_etf:
            eps_data, eps_chart = [], None
            emit("  ⚠ ETF 無 EPS 資料")
        else:
            eps_data, eps_chart = get_eps_data(stock_id, market=market)
            emit(f"  {'✓' if eps_data else '⚠'} EPS 資料{'共 ' + str(len(eps_data)) + ' 筆' if eps_data else '取得不完全'}")

        emit("[4/5] 蒐集新聞資訊...")
        aggregator = NewsAggregator()
        news_data = aggregator.collect(stock_info)
        news_count = len(news_data.get("items", []))
        emit(f"  {'✓' if news_count else '⚠'} 新聞{'共 ' + str(news_count) + ' 則' if news_count else '取得不完全'}")
        news_sentiment = news_data.get("sentiment", {})

        if not eps_data and not is_etf:
            emit("error:查無此股票的 EPS 資料，無法進行分析。請確認股票代號是否正確（例如台積電請輸入 2330）。")
            return
        if not has_price:
            emit("error:無法取得股價資料，請稍後再試或確認網路連線。")
            return

        emit("取得資產負債表資料...")
        bs_data, fin_data = None, None
        if not is_etf:
            try:
                import yfinance as yf
                ticker = yf.Ticker(stock_id + (".TW" if "TW" not in stock_id else ""))
                bs_data = ticker.balance_sheet
                fin_data = ticker.financials
                emit("  ✓ 資產負債表資料取得完成")
            except Exception:
                emit("  ⚠ 資產負債表資料取得不完全，部分指標可能無法計算")
                bs_data, fin_data = None, None

        emit("進行估值分析...")
        try:
            va = ValuationAnalyzer(
                stock_id, eps_data, price_data, revenue_data, stock_info, price_info,
                balance_sheet=bs_data, financials=fin_data
            )
            valuation_analysis = va.full_analysis()
            if not is_etf:
                hs = valuation_analysis.get("health_score", {}).get("total_score", "N/A")
                emit(f"  ✓ 健康評分：{hs} 分")
        except Exception as e:
            emit(f"  ⚠ 估值分析失敗：{e}")
            valuation_analysis = None

        emit("取得股利資料...")
        dividend_data = get_dividend_data(stock_id, market=market)
        calendar_events = get_calendar_events(
            stock_id, market=market,
            dividend_history=dividend_data.get("history") if dividend_data else None
        )
        if calendar_events.get("ex_dividend") or calendar_events.get("earnings") or calendar_events.get("dividend_months"):
            emit("  ✓ 行事曆資料取得完成")
        emit("取得同業比較資料...")
        peers_data = get_peers_comparison(stock_id, basic_info.get("industry", ""), market=market)
        emit(f"  ✓ 同業資料{'共 ' + str(len(peers_data)) + ' 筆' if peers_data else '無同業資料'}")
        emit("產生 PDF 報告中...")
        def _pdf_progress(current, total, section_name):
            emit(f"  [{current}/{total}] {section_name}")
        generator = PDFReport(
            stock_info=basic_info,
            price_data=price_data,
            price_info=price_info,
            revenue_data=revenue_data,
            revenue_chart=revenue_chart,
            eps_data=eps_data,
            eps_chart=eps_chart,
            news_data=news_data,
            valuation_analysis=valuation_analysis,
            dividend_data=dividend_data,
            peers_data=peers_data,
            progress_callback=_pdf_progress,
        )
        output_path = generator.generate()
        filename = os.path.basename(output_path)

        # build preview data
        preview = {"stock": {}, "fair_price": None, "health_score": None,
                    "peg": None, "risk_warnings": {}, "dividend": None,
                    "revenue": None, "eps": None, "is_etf": False, "peers": peers_data,
                    "news_sentiment": news_sentiment,
                    "calendar": calendar_events}
        price_date = None
        for pname in ["1y", "6m", "3m"]:
            d = price_data.get(pname, {}).get("df")
            if d is not None and not d.empty:
                price_date = str(d.index[-1].date())
                break
        preview["stock"] = {
            "name": basic_info.get("name", name),
            "stock_id": stock_id,
            "industry": basic_info.get("industry", ""),
            "sector": basic_info.get("sector", ""),
            "market": basic_info.get("market", ""),
            "current_price": basic_info.get("current_price"),
            "day_change_pct": basic_info.get("day_change_pct"),
            "market_cap": basic_info.get("marketCap"),
            "pe": price_info.get("trailingPE"),
            "price_date": price_date,
            "description": basic_info.get("description", ""),
            "country": basic_info.get("country", ""),
            "website": basic_info.get("website", ""),
            "employees": basic_info.get("employees"),
        }
        # financial metrics for preview
        fin_fields = ["grossMargins", "operatingMargins", "profitMargins",
                       "returnOnEquity", "returnOnAssets",
                       "debtToEquity", "freeCashflow", "totalCash", "totalDebt",
                       "revenueGrowth", "earningsGrowth",
                       "revenuePerShare", "bookValue", "forwardPE",
                       "dividendYield", "payoutRatio",
                       "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
                       "fiftyDayAverage", "twoHundredDayAverage"]
        preview["financials"] = {}
        for f in fin_fields:
            if f in basic_info and basic_info[f] is not None:
                preview["financials"][f] = basic_info[f]
        if is_etf:
            preview["etf_data"] = {
                "nav_price": basic_info.get("nav_price"),
                "expense_ratio": basic_info.get("expense_ratio"),
                "total_assets": basic_info.get("total_assets"),
                "etf_category": basic_info.get("etf_category"),
                "fund_family": basic_info.get("fund_family"),
                "avg_volume": basic_info.get("avg_volume"),
                "etf_yield": basic_info.get("etf_yield"),
            }
            if preview["dividend"]:
                preview["etf_data"]["div_yield"] = preview["dividend"]["yield"]
            # compute premium/discount
            nav = basic_info.get("nav_price")
            price = basic_info.get("current_price")
            if nav and price and nav > 0:
                preview["etf_data"]["premium_pct"] = round((price - nav) / nav * 100, 2)
            else:
                preview["etf_data"]["premium_pct"] = None
        if valuation_analysis:
            preview["is_etf"] = valuation_analysis.get("is_etf", False)
            fp = valuation_analysis.get("fair_price_range")
            if fp:
                preview["fair_price"] = {
                    "cheap": fp.get("cheap"), "fair": fp.get("fair"),
                    "expensive": fp.get("expensive"), "current": fp.get("current_price"),
                    "current_pe": fp.get("current_pe"),
                    "eps_growth_rate": fp.get("eps_growth_rate"),
                }
            hs = valuation_analysis.get("health_score")
            if hs:
                preview["health_score"] = {"score": hs.get("total_score"), "level": hs.get("level"),
                                            "components": hs.get("components")}
            pg = valuation_analysis.get("peg")
            if pg:
                preview["peg"] = {"peg": pg.get("peg"), "verdict": pg.get("verdict"), "eps_growth_rate": pg.get("eps_growth_rate")}
            preview["risk_warnings"] = valuation_analysis.get("risk_warnings", [])

            orating = valuation_analysis.get("overall_rating")
            if orating:
                preview["overall_rating"] = {
                    "score": orating.get("score"),
                    "rating": orating.get("rating"),
                    "color": orating.get("color"),
                    "components": orating.get("components"),
                }
            qs = valuation_analysis.get("quality_score")
            if qs:
                preview["quality_score"] = {
                    "piotroski_f_score": qs.get("piotroski_f_score"),
                    "altman_z_score": qs.get("altman_z_score"),
                    "graham_number": qs.get("graham_number"),
                }
        if dividend_data and dividend_data.get("has_dividend"):
            preview["dividend"] = {
                "yield": dividend_data.get("latest_yield"),
                "consecutive_years": dividend_data.get("consecutive_years"),
            }
        if revenue_data:
            last = revenue_data[-1]
            preview["revenue"] = {"latest_yoy": last.get("yoy"), "month": last.get("month"), "year": last.get("year")}
        if eps_data:
            last_eps = eps_data[-1]
            preview["eps"] = {"eps": last_eps.get("eps"), "year": last_eps.get("year"), "quarter": last_eps.get("quarter")}

        # embed news items for frontend display
        news_items = news_data.get("items", [])[:10]
        preview["news"] = []
        for item in news_items:
            title = item.get("title", "") if isinstance(item, dict) else getattr(item, "title", "")
            source = item.get("source", "") if isinstance(item, dict) else getattr(item, "source", "")
            pdate = item.get("publish_date", "") if isinstance(item, dict) else getattr(item, "publish_date", "")
            summary = item.get("summary", "") if isinstance(item, dict) else getattr(item, "summary", "")
            sentiment = item.get("sentiment") if isinstance(item, dict) else getattr(item, "sentiment", None)
            sentiment = sentiment or classify_sentiment(title + " " + summary)
            preview["news"].append({
                "title": title, "source": source, "date": pdate,
                "summary": summary, "sentiment": sentiment,
            })
        # embed charts as base64 for preview
        preview["chart_revenue"] = _img_b64(revenue_chart)
        preview["chart_eps"] = _img_b64(eps_chart)
        preview["charts_price"] = {}
        for pname in ["3m", "6m", "1y"]:
            cp = price_data.get(pname, {}).get("chart")
            if cp and not preview["charts_price"]:
                preview["chart_price"] = _img_b64(cp)
            variants = price_data.get(pname, {}).get("charts", {})
            if variants:
                preview["charts_price"] = {k: _img_b64(v) for k, v in variants.items()}
                break

        emit("result:" + json.dumps(preview, ensure_ascii=False))
        _set_cached_preview(stock_id, preview)
        emit(f"done:{filename}")

    except Exception as e:
        err_str = str(e)
        if "yfinance" in err_str.lower() or "connection" in err_str.lower() or "timeout" in err_str.lower():
            emit("error:無法連線到股價資料源，請檢查網路連線稍後再試。")
        elif "no data" in err_str.lower() or "404" in err_str or "not found" in err_str.lower():
            emit("error:查無此股票資料，請確認股票代號是否正確。")
        else:
            emit(f"error:分析過程發生異常，請稍後再試。（{err_str[:80]}）")
        emit(f"detail:{traceback.format_exc()}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    results = search_stock(q)
    if not results:
        info = normalize(q)
        if info.get("stock_id"):
            results = [info]
    return jsonify([
        {"stock_id": r["stock_id"], "name": r["name"], "industry": r.get("industry", "")}
        for r in results
    ])


@app.route("/picture/<folder>/<filename>")
def picture_file(folder, filename):
    dirs = {"side": SIDE_DIR, "border": BORDER_DIR, "icon": ICON_DIR}
    d = dirs.get(folder)
    if d:
        return send_from_directory(d, filename)
    return "Not Found", 404


def _list_images(directory):
    try:
        files = [f for f in os.listdir(directory) if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))]
        return sorted(files)
    except Exception:
        return []


@app.route("/api/cats")
def list_cats():
    return jsonify(_list_images(SIDE_DIR))


@app.route("/api/cat-random")
def random_cat():
    files = _list_images(SIDE_DIR)
    if files:
        return jsonify({"file": random.choice(files)})
    return jsonify({"file": None})


@app.route("/api/cats-border")
def list_cats_border():
    return jsonify(_list_images(BORDER_DIR))


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "請輸入股票代號或名稱"}), 400

    task_id = uuid.uuid4().hex
    log_queue = queue.Queue()
    tasks[task_id] = {"queue": log_queue, "done": False, "thread": None}

    t = threading.Thread(target=run_analysis, args=(query, log_queue), daemon=True)
    tasks[task_id]["thread"] = t
    t.start()

    return jsonify({"task_id": task_id})


@app.route("/stream/<task_id>")
def stream(task_id):
    task = tasks.get(task_id)
    if not task:
        return Response("data: " + json.dumps({"type": "error", "msg": "任務不存在"}) + "\n\n", mimetype="text/event-stream")

    def generate():
        q = task["queue"]
        thread = task.get("thread")
        while True:
            try:
                msg = q.get(timeout=30)
                if msg.startswith("result:"):
                    payload = json.loads(msg[7:])
                    yield "data: " + json.dumps({"type": "result", "data": payload}) + "\n\n"
                elif msg.startswith("done:"):
                    filename = msg[5:]
                    yield "data: " + json.dumps({"type": "done", "filename": filename}) + "\n\n"
                    tasks.pop(task_id, None)
                    return
                elif msg.startswith("error:"):
                    yield "data: " + json.dumps({"type": "error", "msg": msg[6:]}) + "\n\n"
                    tasks.pop(task_id, None)
                    return
                elif msg.startswith("detail:"):
                    yield "data: " + json.dumps({"type": "detail", "msg": msg[7:]}) + "\n\n"
                else:
                    yield "data: " + json.dumps({"type": "log", "msg": msg}) + "\n\n"
            except queue.Empty:
                # 檢查分析執行緒是否還活著
                if thread and not thread.is_alive():
                    yield "data: " + json.dumps({"type": "error", "msg": "分析執行緒意外終止，請重試"}) + "\n\n"
                    tasks.pop(task_id, None)
                    return
                yield "data: " + json.dumps({"type": "ping"}) + "\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


def _open_browser(port):
    def _open():
        time.sleep(1.5)
        url = f"http://127.0.0.1:{port}"
        if shutil.which("powershell.exe"):
            subprocess.Popen(["powershell.exe", "start", url])
        elif shutil.which("cmd.exe"):
            subprocess.Popen(["cmd.exe", "/c", "start", url])
        else:
            import webbrowser
            webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


@app.route("/shutdown", methods=["POST"])
def shutdown():
    logger.info("收到關閉請求，程式即將終止")
    os._exit(0)


_last_ping = time.time()
_ping_lock = threading.Lock()


@app.route("/ping")
def ping():
    with _ping_lock:
        global _last_ping
        _last_ping = time.time()
    return ""


def _start_ping_checker():
    while True:
        time.sleep(5)
        with _ping_lock:
            if time.time() - _last_ping > 30:
                logger.info("瀏覽器已關閉（ping timeout），程式即將終止")
                os._exit(0)


@app.route("/manifest.json")
def manifest():
    return app.response_class(
        json.dumps({
            "name": "台股投資分析報告",
            "short_name": "台股分析",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#7c3aed",
            "icons": [
                {"src": "/picture/icon/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/picture/icon/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }, ensure_ascii=False),
        mimetype="application/json"
    )


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    logger.info(f"啟動 Web UI：http://127.0.0.1:{port}")
    threading.Thread(target=_start_ping_checker, daemon=True).start()
    _open_browser(port)
    from waitress import serve
    serve(app, host="127.0.0.1", port=port)
