import os
import re
import tempfile
import threading
import uuid
from functools import wraps
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests
import yfinance as yf

from config import (
    HEADERS,
    TIMEOUT,
    CHART_DIR,
    MPL_FONT_PATH,
)
from utils.cache import cache_get, cache_set
from stock.yf_errors import YFINANCE_EXCEPTIONS
from stock.official_financials import (
    OfficialDataMissing,
    OfficialNetworkError,
    get_official_revenue,
)
from stock.mops_history import get_monthly_revenue_history
from utils.logger import get_logger

plt.rcParams["axes.unicode_minus"] = False

logger = get_logger(__name__)
_PLOT_LOCK = threading.RLock()


def _plot_locked(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with _PLOT_LOCK:
            return function(*args, **kwargs)

    return wrapper


def _chart_path(stock_id: str, kind: str, artifact_dir: Optional[str] = None) -> str:
    directory = artifact_dir or CHART_DIR
    os.makedirs(directory, exist_ok=True)
    safe_stock_id = re.sub(r"[^0-9A-Za-z_-]", "_", str(stock_id)) or "unknown"
    return os.path.join(directory, f"{safe_stock_id}_{kind}_{uuid.uuid4().hex}.png")


def _save_chart_atomic(path: str) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=os.path.dirname(path), prefix=".chart-", suffix=".tmp", delete=False
        ) as handle:
            temp_path = handle.name
        plt.savefig(temp_path, format="png", dpi=150, bbox_inches="tight")
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


ALLOW_HISTOCK_SCRAPING = os.environ.get(
    "TWSTOCK_ALLOW_HISTOCK", ""
).strip().lower() in {"1", "true", "yes"}

_MPL_FP = None
try:
    from matplotlib.font_manager import fontManager, FontProperties

    if os.path.exists(MPL_FONT_PATH):
        fontManager.addfont(MPL_FONT_PATH)
        _MPL_FP = FontProperties(fname=MPL_FONT_PATH)
        _fname = _MPL_FP.get_name()
        plt.rcParams["font.family"] = _fname
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
except (ImportError, AttributeError) as e:
    logger.warning("matplotlib font init: %s", e)
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def _suffix(market: Optional[str] = None) -> str:
    return ".TWO" if market in {"上櫃", "興櫃"} else ".TW"


def _yield_as_decimal(
    value: Any, dividend_rate: Any = None, price: Any = None
) -> Optional[float]:
    """Normalize yfinance's version-dependent yield field to a decimal ratio."""
    try:
        if dividend_rate is not None and price is not None and float(price) > 0:
            return float(dividend_rate) / float(price)
        if value is None:
            return None
        numeric = float(value)
        return numeric / 100 if abs(numeric) > 0.20 else numeric
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def get_price_data(
    stock_id: str,
    periods: Optional[Dict[str, int]] = None,
    market: Optional[str] = None,
    artifact_dir: Optional[str] = None,
    snapshot: Optional[Any] = None,
    language: str = "zh-TW",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if periods is None:
        periods = {"3m": 90, "6m": 180, "1y": 365}
    results: Dict[str, Any] = {}
    ticker_symbol = f"{stock_id}{_suffix(market)}"
    try:
        if snapshot is None:
            from services.market_snapshot import MarketDataSnapshot

            snapshot = MarketDataSnapshot(stock_id, market or "")
        info: Dict[str, Any] = {}
        try:
            info = snapshot.info()
        except YFINANCE_EXCEPTIONS as e:
            logger.warning("price info fetch warning for %s: %s", ticker_symbol, e)
        full_history = snapshot.history(period="1y")
        if full_history is None or full_history.empty:
            logger.warning(
                "Yahoo Finance returned no price history for %s", ticker_symbol
            )
            return {
                label: {
                    "df": pd.DataFrame(),
                    "chart": None,
                    "charts": {},
                    "high": None,
                    "low": None,
                }
                for label in periods
            }, info
        full_history = full_history.sort_index().rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        latest = pd.Timestamp(full_history.index[-1])
        for label, days in periods.items():
            cutoff = latest - pd.Timedelta(days=days)
            df = full_history[full_history.index >= cutoff].copy()
            if df.empty:
                results[label] = {
                    "df": df,
                    "chart": None,
                    "charts": {},
                    "high": None,
                    "low": None,
                }
                continue
            chart_path = _plot_price_chart(
                df, stock_id, label, artifact_dir=artifact_dir, language=language
            )
            chart_variants = {}
            if label == "1y":
                for m in ("price", "ma", "full"):
                    chart_variants[m] = _plot_price_chart(
                        df,
                        stock_id,
                        label,
                        mode=m,
                        artifact_dir=artifact_dir,
                        language=language,
                    )
            high_idx = df["high"].idxmax()
            low_idx = df["low"].idxmin()
            results[label] = {
                "df": df,
                "chart": chart_path,
                "charts": chart_variants,
                "high": {
                    "date": str(high_idx.date()),
                    "price": round(float(df.loc[high_idx, "high"]), 2),
                },
                "low": {
                    "date": str(low_idx.date()),
                    "price": round(float(df.loc[low_idx, "low"]), 2),
                },
            }
        return results, info
    except YFINANCE_EXCEPTIONS as e:
        logger.error(
            "price data fetch failed for %s: %s", ticker_symbol, e, exc_info=True
        )
        return {
            "3m": {
                "df": pd.DataFrame(),
                "chart": None,
                "charts": {},
                "high": None,
                "low": None,
            },
            "6m": {
                "df": pd.DataFrame(),
                "chart": None,
                "charts": {},
                "high": None,
                "low": None,
            },
            "1y": {
                "df": pd.DataFrame(),
                "chart": None,
                "charts": {},
                "high": None,
                "low": None,
            },
        }, {}


@_plot_locked
def _plot_price_chart(
    df: pd.DataFrame,
    stock_id: str,
    label: str,
    mode: str = "full",
    artifact_dir: Optional[str] = None,
    language: str = "zh-TW",
) -> str:
    path = _chart_path(stock_id, f"price_{label}_{mode}", artifact_dir)
    fig, ax1 = plt.subplots(figsize=(10, 4))
    english = language == "en"
    ax1.plot(
        df.index,
        df["close"],
        "b-",
        linewidth=1.5,
        label="Close" if english else "收盤價",
    )
    ax1.fill_between(df.index, df["close"], alpha=0.1, color="blue")
    if mode in ("ma", "full"):
        for period, color, lw, name in [
            (20, "#FF9800", 1, "20-day MA" if english else "月線(20)"),
            (60, "#9C27B0", 1, "60-day MA" if english else "季線(60)"),
            (200, "#F44336", 1, "200-day MA" if english else "年線(200)"),
        ]:
            if len(df) >= period:
                sma = df["close"].rolling(window=period).mean()
                ax1.plot(
                    df.index, sma, color=color, linewidth=lw, alpha=0.7, label=name
                )
    ax1.set_ylabel("Price (TWD)" if english else "價格 (元)", fontsize=11)
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    high_idx = df["high"].idxmax()
    low_idx = df["low"].idxmin()
    ax1.annotate(
        f"H: {df.loc[high_idx, 'high']:.1f}",
        xy=(high_idx, df.loc[high_idx, "high"]),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=9,
        color="red",
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="red"),
    )
    ax1.annotate(
        f"L: {df.loc[low_idx, 'low']:.1f}",
        xy=(low_idx, df.loc[low_idx, "low"]),
        xytext=(10, -15),
        textcoords="offset points",
        fontsize=9,
        color="green",
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="green"),
    )
    if mode == "full" and "volume" in df.columns and df["volume"].sum() > 0:
        ax2 = ax1.twinx()
        ax2.bar(df.index, df["volume"] / 1e6, alpha=0.2, color="gray", width=0.8)
        ax2.set_ylabel("Volume (millions)" if english else "成交量 (百萬)", fontsize=10)
    labels_map = (
        {"3m": "3 months", "6m": "6 months", "1y": "1 year"}
        if english
        else {"3m": "近3個月", "6m": "近6個月", "1y": "近1年"}
    )
    plt.title(
        f"{stock_id} Price Trend ({labels_map.get(label, label)})"
        if english
        else f"{stock_id} 股價走勢 ({labels_map.get(label, label)})",
        fontsize=13,
    )
    plt.tight_layout()
    _save_chart_atomic(path)
    plt.close()
    return path


def get_revenue_data(
    stock_id: str,
    market: Optional[str] = None,
    artifact_dir: Optional[str] = None,
    language: str = "zh-TW",
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    records = []
    try:
        records = get_official_revenue(stock_id, market or "")
    except (OfficialNetworkError, OfficialDataMissing) as exc:
        logger.warning("official revenue unavailable for %s: %s", stock_id, exc)
    # TWSE/TPEx OpenAPI publishes the latest month only.  Use the official MOPS
    # archive to supply the preceding months so charts and revenue comparisons
    # do not misleadingly look like missing data just because the current API
    # is a single-period dataset.
    if records:
        latest_record = records[-1]
        try:
            records = get_monthly_revenue_history(
                stock_id,
                end_year=int(latest_record["year"]),
                end_month=int(latest_record["month"]),
                market=market or "",
                months=24,
                latest_record=latest_record,
            )
        except (OfficialNetworkError, OfficialDataMissing) as exc:
            logger.warning(
                "official revenue history unavailable for %s; keeping latest month: %s",
                stock_id,
                exc,
            )
    if not records and ALLOW_HISTOCK_SCRAPING:
        try:
            records = _fetch_revenue_histock(stock_id)
        except (requests.RequestException, ValueError, IndexError) as e:
            logger.warning(
                "opt-in HiStock revenue fetch failed for %s: %s", stock_id, e
            )
    if not records:
        records = _fetch_revenue_yfinance(stock_id, market)
    records.sort(key=lambda x: (x.get("year", 0), x.get("month", 0)))
    chart_path = _plot_revenue_chart(
        records, stock_id, artifact_dir=artifact_dir, language=language
    )
    return records, chart_path


def _fetch_revenue_histock(stock_id: str) -> List[Dict[str, Any]]:
    url = f"https://histock.tw/stock/{stock_id}/%E6%AF%8F%E6%9C%88%E7%87%9F%E6%94%B6"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table")
    records = []
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        for row in rows[2:]:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            date_text = cells[0].get_text(strip=True)
            if not date_text or "/" not in date_text:
                continue
            parts = date_text.split("/")
            if len(parts) != 2:
                continue
            year = int(parts[0])
            month = int(parts[1])
            try:
                revenue = float(cells[1].get_text(strip=True).replace(",", ""))
            except (ValueError, IndexError):
                continue
            try:
                last_year_rev = float(cells[2].get_text(strip=True).replace(",", ""))
            except (ValueError, IndexError):
                last_year_rev = 0
            mom_str = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            yoy_str = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            mom = None
            yoy = None
            try:
                if mom_str:
                    mom = float(mom_str.replace("%", ""))
            except ValueError:
                pass
            try:
                if yoy_str:
                    yoy = float(yoy_str.replace("%", ""))
            except ValueError:
                pass
            records.append(
                {
                    "year": year,
                    "month": month,
                    "source": "HiStock HTML (explicit opt-in)",
                    "revenue": revenue,
                    "prev_month_revenue": None,
                    "last_year_revenue": last_year_rev if last_year_rev > 0 else None,
                    "mom": mom,
                    "yoy": yoy,
                }
            )
    return records


def _fetch_revenue_yfinance(
    stock_id: str, market: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Do not convert annual/TTM revenue into fabricated monthly observations."""
    logger.info("monthly revenue unavailable from yfinance for %s", stock_id)
    return []


@_plot_locked
def _plot_revenue_chart(
    records: List[Dict[str, Any]],
    stock_id: str,
    artifact_dir: Optional[str] = None,
    language: str = "zh-TW",
) -> Optional[str]:
    if not records:
        return None
    path = _chart_path(stock_id, "revenue", artifact_dir)
    labels = [f"{r.get('year', 0)}/{r['month']:02d}" for r in records]
    revenues = [r["revenue"] / 1e5 for r in records]
    moms = [r["mom"] if r["mom"] is not None else 0 for r in records]
    yoys = [r["yoy"] if r["yoy"] is not None else 0 for r in records]
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 2]}
    )
    colors = ["#2196F3" if i % 2 == 0 else "#1976D2" for i in range(len(revenues))]
    ax1.bar(range(len(revenues)), revenues, color=colors, alpha=0.8, width=0.6)
    english = language == "en"
    ax1.set_ylabel("Revenue (TWD 100m)" if english else "營收 (億元)", fontsize=11)
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, fontsize=8)
    for i, v in enumerate(revenues):
        ax1.text(i, v + max(revenues) * 0.01, f"{v:.1f}", ha="center", fontsize=7)
    ax1.grid(True, alpha=0.3, axis="y")
    ax2.plot(
        range(len(moms)),
        moms,
        "g-o",
        linewidth=1.5,
        markersize=4,
        label="MoM (%)" if english else "月增率 (MoM %)",
    )
    ax2.plot(
        range(len(yoys)),
        yoys,
        "r-s",
        linewidth=1.5,
        markersize=4,
        label="YoY (%)" if english else "年增率 (YoY %)",
    )
    ax2.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax2.set_ylabel("Change (%)" if english else "增減率 (%)", fontsize=11)
    ax2.set_xlabel("Period" if english else "年月", fontsize=11)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, rotation=45, fontsize=8)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    plt.suptitle(
        f"{stock_id} Monthly Revenue Analysis"
        if english
        else f"{stock_id} 每月營收分析",
        fontsize=14,
        y=1.01,
    )
    plt.tight_layout()
    _save_chart_atomic(path)
    plt.close()
    return path


def get_eps_data(
    stock_id: str,
    market: Optional[str] = None,
    artifact_dir: Optional[str] = None,
    snapshot: Optional[Any] = None,
    official_financials: Optional[Dict[str, Any]] = None,
    language: str = "zh-TW",
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    cached = cache_get(stock_id, "eps_yahoo_v4", max_age_sec=86400)
    if cached is not None:
        records = cached
    else:
        records = []
        if ALLOW_HISTOCK_SCRAPING:
            try:
                records = _fetch_eps_histock(stock_id)
            except (requests.RequestException, ValueError, IndexError) as e:
                logger.warning(
                    "opt-in HiStock EPS fetch failed for %s: %s", stock_id, e
                )
        if not records:
            try:
                records = _fetch_eps_yfinance(stock_id, market, snapshot=snapshot)
            except YFINANCE_EXCEPTIONS as e:
                logger.warning(
                    "yfinance quarterly EPS fetch failed for %s: %s", stock_id, e
                )
        if records:
            cache_set(stock_id, "eps_yahoo_v4", records)
    official_eps = (official_financials or {}).get("official_cumulative_eps")
    if official_eps and official_financials.get("quarter") == 1:
        year = int(official_financials["year"])
        records = [
            record
            for record in records
            if (record.get("year"), record.get("quarter")) != (year, 1)
        ]
        records.append(
            {
                "year": year,
                "quarter": 1,
                "eps": official_eps["value"],
                "label": f"Q1 {year}",
                "source": official_eps["source"],
                "source_url": (official_financials.get("source_urls") or {}).get(
                    "income"
                ),
                "observed_at": official_eps["observed_at"],
                "fetched_at": official_eps["fetched_at"],
                "unit": official_eps["unit"],
                "status": official_eps["status"],
                "note": official_eps.get("note", ""),
                "data_value": official_eps,
            }
        )
    records.sort(key=lambda x: (x["year"], x["quarter"]))
    chart_path = _plot_eps_chart(
        records, stock_id, artifact_dir=artifact_dir, language=language
    )
    return records, chart_path


def _fetch_eps_histock(stock_id: str) -> List[Dict[str, Any]]:
    url = f"https://histock.tw/stock/{stock_id}/%E6%AF%8F%E8%82%A1%E7%9B%88%E9%A4%98"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table")
    records = []
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 6:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        years = []
        for cell in header_cells[1:]:
            year_text = cell.get_text(strip=True)
            if year_text.isdigit():
                years.append(int(year_text))
        if not years:
            continue
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            label = cells[0].get_text(strip=True)
            if label in ("Q1", "Q2", "Q3", "Q4"):
                q_num = int(label[1])
                for i, year in enumerate(years):
                    if i + 1 < len(cells):
                        try:
                            eps_val = float(cells[i + 1].get_text(strip=True))
                            records.append(
                                {
                                    "year": year,
                                    "quarter": q_num,
                                    "source": "HiStock HTML (explicit opt-in)",
                                    "eps": eps_val,
                                    "label": f"Q{q_num} {year}",
                                }
                            )
                        except (ValueError, IndexError):
                            pass
    return records


def _fetch_eps_yfinance(
    stock_id: str, market: Optional[str] = None, snapshot: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """Read genuine quarterly EPS, deriving it only from matching quarter NI/shares."""
    if snapshot is None:
        frame = yf.Ticker(f"{stock_id}{_suffix(market)}").quarterly_income_stmt
    else:
        frame = snapshot.quarterly_income_stmt()
    if frame is None or frame.empty:
        return []

    eps_rows = [row for row in ("Diluted EPS", "Basic EPS") if row in frame.index]
    income_rows = [
        row
        for row in (
            "Diluted NI Availto Com Stockholders",
            "Net Income Common Stockholders",
        )
        if row in frame.index
    ]
    share_rows = [
        row
        for row in ("Diluted Average Shares", "Basic Average Shares")
        if row in frame.index
    ]
    records: Dict[tuple[int, int], Dict[str, Any]] = {}
    for column in frame.columns:
        timestamp = pd.Timestamp(column)
        year = int(timestamp.year)
        quarter = (int(timestamp.month) - 1) // 3 + 1
        value = None
        for row in eps_rows:
            candidate = frame.loc[row, column]
            if pd.notna(candidate):
                value = float(candidate)
                break
        if value is None:
            net_income = next(
                (
                    float(frame.loc[row, column])
                    for row in income_rows
                    if pd.notna(frame.loc[row, column])
                ),
                None,
            )
            shares = next(
                (
                    float(frame.loc[row, column])
                    for row in share_rows
                    if pd.notna(frame.loc[row, column])
                ),
                None,
            )
            if net_income is not None and shares is not None and shares > 0:
                value = net_income / shares
        if value is None or not pd.notna(value):
            continue
        records[(year, quarter)] = {
            "year": year,
            "quarter": quarter,
            "eps": round(float(value), 4),
            "label": f"Q{quarter} {year}",
            "source": "Yahoo Finance quarterly_income_stmt",
            "source_url": "https://finance.yahoo.com/",
            "observed_at": timestamp.date().isoformat(),
            "fetched_at": getattr(
                snapshot, "created_at", datetime.now().astimezone().isoformat()
            ),
            "unit": "TWD_per_share",
            "status": "fallback",
            "note": "官方 OpenAPI 僅提供當期累計值時，以 Yahoo 單季資料補足歷史序列。",
        }
        records[(year, quarter)]["data_value"] = {
            "value": records[(year, quarter)]["eps"],
            "source": records[(year, quarter)]["source"],
            "observed_at": records[(year, quarter)]["observed_at"],
            "fetched_at": records[(year, quarter)]["fetched_at"],
            "unit": records[(year, quarter)]["unit"],
            "currency": "TWD",
            "status": records[(year, quarter)]["status"],
            "note": records[(year, quarter)]["note"],
        }
    return sorted(records.values(), key=lambda item: (item["year"], item["quarter"]))


@_plot_locked
def _plot_eps_chart(
    records: List[Dict[str, Any]],
    stock_id: str,
    artifact_dir: Optional[str] = None,
    language: str = "zh-TW",
) -> Optional[str]:
    if not records:
        return None
    path = _chart_path(stock_id, "eps", artifact_dir)
    labels = [r["label"] for r in records]
    eps_values = [r["eps"] for r in records]
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#4CAF50" if v >= 0 else "#F44336" for v in eps_values]
    ax.bar(range(len(eps_values)), eps_values, color=colors, alpha=0.8, width=0.5)
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
    english = language == "en"
    ax.set_ylabel("EPS (TWD)" if english else "EPS (元)", fontsize=12)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, fontsize=9)
    for i, v in enumerate(eps_values):
        offset = 0.1 if v >= 0 else -0.4
        ax.text(i, v + offset, f"{v:.2f}", ha="center", fontsize=9, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    plt.title(
        f"{stock_id} Quarterly EPS" if english else f"{stock_id} 各季 EPS", fontsize=14
    )
    plt.tight_layout()
    _save_chart_atomic(path)
    plt.close()
    return path


def get_basic_stock_info(
    stock_id: str, stock_info: Dict[str, Any], snapshot: Optional[Any] = None
) -> Dict[str, Any]:
    # The official security registry is authoritative for the product type.
    # Do not make ETF handling depend on Yahoo responding successfully: without
    # this early flag a transient Yahoo failure sends an ETF down the company
    # revenue/EPS and financial-statement pipeline.
    is_official_etf = stock_info.get("asset_type") == "etf"
    result: Dict[str, Any] = {
        "stock_id": stock_id,
        "name": stock_info.get("name", ""),
        "industry": stock_info.get("industry", ""),
        "market": stock_info.get("market", ""),
        "is_etf": is_official_etf,
        "report_date": datetime.now().strftime("%Y年%m月%d日"),
    }
    if is_official_etf:
        # These registry fields come from TWSE/TPEx official ETF sources.  They
        # remain useful when Yahoo omits ETF metadata, especially TPEx's AUM.
        for field in (
            "fund_type",
            "tracking_index",
            "official_source",
            "source_updated_at",
        ):
            if stock_info.get(field) not in (None, ""):
                result[field] = stock_info[field]
        if stock_info.get("aum") is not None:
            result["total_assets"] = stock_info["aum"]
    try:
        mkt = stock_info.get("market", "")
        if snapshot is None:
            from services.market_snapshot import MarketDataSnapshot

            snapshot = MarketDataSnapshot(stock_id, mkt)
        info = snapshot.info()
        if "longName" in info and info["longName"]:
            result["name_en"] = info["longName"]
            if not result["name"]:
                result["name"] = info["longName"]
        if "sector" in info and info["sector"]:
            result["sector"] = info["sector"]
            if not result["industry"]:
                result["industry"] = info["sector"]
        if not result.get("market") and info.get("market"):
            result["market"] = info["market"]
        qt = info.get("quoteType", "")
        result["is_etf"] = is_official_etf or qt == "ETF"
        if "currentPrice" in info and info["currentPrice"] is not None:
            result["current_price"] = info["currentPrice"]
        elif "regularMarketPrice" in info and info["regularMarketPrice"] is not None:
            result["current_price"] = info["regularMarketPrice"]
        elif (
            result.get("is_etf") and "navPrice" in info and info["navPrice"] is not None
        ):
            result["current_price"] = info["navPrice"]
        if "previousClose" in info:
            result["prev_close"] = info["previousClose"]
        if "marketCap" in info:
            result["market_cap"] = info["marketCap"]
        if "fiftyTwoWeekHigh" in info:
            result["52w_high"] = info["fiftyTwoWeekHigh"]
        if "fiftyTwoWeekLow" in info:
            result["52w_low"] = info["fiftyTwoWeekLow"]
        if "longBusinessSummary" in info and info["longBusinessSummary"]:
            result["description"] = info["longBusinessSummary"]
        if "sector" in info and info["sector"]:
            result["sector"] = info["sector"]
        if "website" in info and info["website"]:
            result["website"] = info["website"]
        if "country" in info and info["country"]:
            result["country"] = info["country"]
        if "city" in info and info["city"]:
            result["city"] = info["city"]
        if "phone" in info and info["phone"]:
            result["phone"] = info["phone"]
        if "fullTimeEmployees" in info and info["fullTimeEmployees"]:
            result["employees"] = info["fullTimeEmployees"]

        market_change = info.get("regularMarketChange")
        previous_close = info.get("previousClose")
        if market_change is not None and previous_close and previous_close > 0:
            result["day_change_pct"] = round(
                float(market_change) / float(previous_close) * 100, 2
            )

        for field in [
            "grossMargins",
            "operatingMargins",
            "profitMargins",
            "returnOnEquity",
            "returnOnAssets",
            "debtToEquity",
            "totalDebt",
            "totalCash",
            "freeCashflow",
            "operatingCashflow",
            "revenueGrowth",
            "earningsGrowth",
            "revenuePerShare",
            "bookValue",
            "priceToBook",
            "forwardPE",
            "forwardEps",
            "dividendYield",
            "payoutRatio",
            "beta",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "fiftyDayAverage",
            "twoHundredDayAverage",
            "shortRatio",
            "shortPercentOfFloat",
            "heldPercentInstitutions",
        ]:
            if field in info and info[field] is not None:
                if field == "dividendYield":
                    normalized_yield = _yield_as_decimal(
                        info[field],
                        info.get("dividendRate"),
                        info.get("currentPrice") or info.get("regularMarketPrice"),
                    )
                    if normalized_yield is not None:
                        result[field] = normalized_yield
                else:
                    result[field] = info[field]

        # ETF-specific fields
        if result["is_etf"]:
            if "navPrice" in info:
                result["nav_price"] = info["navPrice"]
            if "annualReportExpenseRatio" in info:
                result["expense_ratio"] = info["annualReportExpenseRatio"]
            if "totalAssets" in info:
                result["total_assets"] = info["totalAssets"]
            if "category" in info:
                result["etf_category"] = info["category"]
            if "fundFamily" in info:
                result["fund_family"] = info["fundFamily"]
            if "averageVolume" in info:
                result["avg_volume"] = info["averageVolume"]
            if "yield" in info:
                result["etf_yield"] = _yield_as_decimal(
                    info["yield"],
                    info.get("dividendRate"),
                    info.get("currentPrice") or info.get("regularMarketPrice"),
                )
    except YFINANCE_EXCEPTIONS as e:
        logger.warning("basic stock info fetch error for %s: %s", stock_id, e)
    if not result["name"]:
        result["name"] = stock_info.get("name", stock_id)
    return result
