import os

import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
CACHE_MAX_ITEMS = 100
FONT_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_DIR = os.path.join(CACHE_DIR, "charts")
YFINANCE_CACHE_DIR = os.path.join(CACHE_DIR, "yfinance")

for d in [CACHE_DIR, FONT_DIR, OUTPUT_DIR, CHART_DIR, YFINANCE_CACHE_DIR]:
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

FONT_PATH = os.path.join(FONT_DIR, "msjh.ttc")
FONT_PATH_BOLD = os.path.join(FONT_DIR, "msjhbd.ttc")
FONT_NAME = "MSJH"

MPL_FONT_PATH = os.path.join(FONT_DIR, "STKAITI.TTF")
MPL_FONT_NAME = "STKaiti"
