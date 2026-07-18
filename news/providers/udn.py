import re
import requests
from bs4 import BeautifulSoup
from config import HEADERS, TIMEOUT
from news.base_provider import BaseNewsProvider, NewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


class UDNProvider(BaseNewsProvider):
    name = "經濟日報/UDN"
    priority = 50

    def search(self, query, stock_info=None) -> list:
        items = []
        stock_id = (stock_info or {}).get("stock_id", "")
        if stock_id:
            items.extend(self._fetch_stock_news(stock_id, query))
        if not items:
            items.extend(self._search_udn(query))
        return items[:15]

    def _fetch_stock_news(self, stock_id, query):
        items = []
        url = f"https://money.udn.com/rank/stock/{stock_id}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select("a[href*='/money/story']"):
                title = a.get_text().strip()
                href = a.get("href", "")
                if title and len(title) > 5:
                    full_url = href if href.startswith("http") else f"https://money.udn.com{href}"
                    items.append(NewsItem(
                        title=title, source="經濟日報",
                        url=full_url, matched_keyword=query,
                    ))
        except (requests.RequestException, AttributeError) as e:
            logger.warning("UDN _fetch_stock_news error: %s", e)
        return items

    def _search_udn(self, query):
        items = []
        try:
            url = f"https://money.udn.com/search/tagging/1001/{requests.utils.quote(query)}"
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select("a[href*='/money/story']"):
                title = a.get_text().strip()
                href = a.get("href", "")
                if title and len(title) > 5:
                    full_url = href if href.startswith("http") else f"https://money.udn.com{href}"
                    items.append(NewsItem(
                        title=title, source="經濟日報",
                        url=full_url, matched_keyword=query,
                    ))
        except (requests.RequestException, AttributeError) as e:
            logger.warning("UDN search error: %s", e)
        return items
