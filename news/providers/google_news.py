from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from config import HEADERS, TIMEOUT
from news.base_provider import BaseNewsProvider, NewsItem

NEWS_TIMEOUT = min(TIMEOUT, 12)


def _plain_text(value: str) -> str:
    return BeautifulSoup(value or "", "lxml").get_text(" ", strip=True)


def _rss_items(
    content: bytes, provider: BaseNewsProvider, query: str, default_source: str
) -> list[NewsItem]:
    root = ElementTree.fromstring(content)
    items = []
    for entry in root.iter("item"):
        title = _plain_text(entry.findtext("title", "")).strip()
        if not title:
            continue
        link = (entry.findtext("link", "") or "").strip()
        date = provider._normalize_date(entry.findtext("pubDate", "") or "")
        summary = _plain_text(entry.findtext("description", ""))[:300]
        source = _plain_text(entry.findtext("source", "")) or default_source
        items.append(
            NewsItem(
                title=title,
                publish_date=date,
                source=source,
                url=link,
                summary=summary,
                matched_keyword=query,
            )
        )
    return items


class GoogleNewsProvider(BaseNewsProvider):
    name = "Google 新聞"
    priority = 10

    def search(self, query, stock_info=None) -> list:
        url = (
            "https://news.google.com/rss/search"
            f"?q={requests.utils.quote(query)}"
            "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        )
        response = requests.get(url, headers=HEADERS, timeout=NEWS_TIMEOUT)
        response.raise_for_status()
        return _rss_items(response.content, self, query, self.name)[:20]


class BingNewsProvider(BaseNewsProvider):
    name = "Bing 新聞"
    priority = 20

    def search(self, query, stock_info=None) -> list:
        url = f"https://www.bing.com/news/search?q={requests.utils.quote(query)}&format=rss"
        response = requests.get(url, headers=HEADERS, timeout=NEWS_TIMEOUT)
        response.raise_for_status()
        return _rss_items(response.content, self, query, self.name)[:20]
