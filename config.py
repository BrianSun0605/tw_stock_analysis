import os
import sys

import yfinance as yf

BUNDLE_DIR = os.path.abspath(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
)
BASE_DIR = BUNDLE_DIR
APP_MODE = (
    os.environ.get(
        "TWSTOCK_APP_MODE",
        "release" if getattr(sys, "frozen", False) else "dev",
    )
    .strip()
    .lower()
)
if APP_MODE not in {"dev", "release"}:
    raise RuntimeError("TWSTOCK_APP_MODE must be dev or release")

if APP_MODE == "release":
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        local_appdata = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    DATA_ROOT = os.path.abspath(
        os.environ.get(
            "TWSTOCK_DATA_ROOT",
            os.path.join(local_appdata, "FatCatGameStudio", "TWStockAnalysis"),
        )
    )
else:
    DATA_ROOT = BUNDLE_DIR

CACHE_DIR = os.path.join(DATA_ROOT, "cache")
CACHE_MAX_BYTES = 256 * 1024 * 1024
CACHE_HIGH_WATER_BYTES = 200 * 1024 * 1024
CACHE_EVICT_TARGET_BYTES = 160 * 1024 * 1024
OUTPUT_MAX_BYTES = 250 * 1024 * 1024
OUTPUT_TTL_SECONDS = 3 * 86400
TASK_ARTIFACT_TTL_SECONDS = 86400
CLEANUP_INTERVAL_SECONDS = 6 * 3600
LOG_TTL_SECONDS = 14 * 86400
LOG_MAX_BYTES = 20 * 1024 * 1024
FONT_DIR = os.path.join(BUNDLE_DIR, "fonts")
OUTPUT_DIR = os.path.join(DATA_ROOT, "output")
LOG_DIR = os.path.join(DATA_ROOT, "logs")
CHART_DIR = os.path.join(CACHE_DIR, "charts")
TASK_ARTIFACT_DIR = os.path.join(CACHE_DIR, "tasks")
YFINANCE_CACHE_DIR = os.path.join(CACHE_DIR, "yfinance")

for d in [
    DATA_ROOT,
    CACHE_DIR,
    OUTPUT_DIR,
    LOG_DIR,
    CHART_DIR,
    TASK_ARTIFACT_DIR,
    YFINANCE_CACHE_DIR,
]:
    os.makedirs(d, exist_ok=True)

# yfinance otherwise writes SQLite cookie/timezone caches to the user profile.
# Desktop/sandbox launches may not be allowed to write there, so keep every
# runtime cache inside this project's writable cache directory.
yf.set_tz_cache_location(YFINANCE_CACHE_DIR)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TIMEOUT = 30

FONT_PATH = os.path.join(FONT_DIR, "NotoSansTC-Regular.otf")
FONT_PATH_BOLD = os.path.join(FONT_DIR, "NotoSansTC-Bold.otf")
FONT_NAME = "NotoSansTC"

MPL_FONT_PATH = FONT_PATH
MPL_FONT_NAME = "Noto Sans TC"
