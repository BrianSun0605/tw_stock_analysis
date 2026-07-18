import requests

from config import HEADERS
from news.base_provider import BaseNewsProvider
from news.providers.google_news import NEWS_TIMEOUT, _rss_items


class IndustryFallbackProvider(BaseNewsProvider):
    name = "Google 產業新聞"
    priority = 99

    def search(self, query, stock_info=None) -> list:
        industry = (stock_info or {}).get("industry", "")
        if not industry:
            return []
        keyword = f"{industry} 產業"
        url = (
            "https://news.google.com/rss/search"
            f"?q={requests.utils.quote(keyword)}"
            "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        )
        response = requests.get(url, headers=HEADERS, timeout=NEWS_TIMEOUT)
        response.raise_for_status()
        items = _rss_items(response.content, self, keyword, self.name)[:10]
        for item in items:
            item.is_fallback = True
        return items
