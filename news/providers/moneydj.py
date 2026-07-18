import re
import requests
from bs4 import BeautifulSoup
from config import HEADERS, TIMEOUT
from news.base_provider import BaseNewsProvider, NewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


class MoneyDJProvider(BaseNewsProvider):
    name = "MoneyDJ"
    priority = 30

    def search(self, query, stock_info=None) -> list:
        items = []
        stock_id = (stock_info or {}).get("stock_id", "")
        if stock_id:
            items.extend(self._fetch_stock_news(stock_id, query))
        if not items:
            items.extend(self._search_moneydj(query))
        return items[:15]

    def _fetch_stock_news(self, stock_id, query):
        items = []
        urls = [
            f"https://www.moneydj.com/kmdj/news/newslist.aspx?a={stock_id}",
            f"https://www.moneydj.com/kmdj/news/newslist.aspx?a={stock_id}&b=1",
        ]
        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                for link in soup.select("a[href*='newsview.aspx']"):
                    title = link.get_text().strip()
                    href = link.get("href", "")
                    if title and len(title) > 5:
                        full_url = href if href.startswith("http") else f"https://www.moneydj.com{href}"
                        items.append(NewsItem(
                            title=title,
                            source="MoneyDJ",
                            url=full_url,
                            matched_keyword=query,
                        ))
            except (requests.RequestException, AttributeError) as e:
                logger.warning("MoneyDJ _fetch_stock_news error: %s", e)
                continue
        return items

    def _search_moneydj(self, query):
        items = []
        try:
            url = f"https://www.moneydj.com/Search/Index?q={requests.utils.quote(query)}"
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            for link in soup.select("a[href*='newsview']"):
                title = link.get_text().strip()
                href = link.get("href", "")
                if title and len(title) > 5:
                    full_url = href if href.startswith("http") else f"https://www.moneydj.com{href}"
                    items.append(NewsItem(
                        title=title,
                        source="MoneyDJ",
                        url=full_url,
                        matched_keyword=query,
                    ))
        except (requests.RequestException, AttributeError) as e:
            logger.warning("MoneyDJ search error: %s", e)
        return items
