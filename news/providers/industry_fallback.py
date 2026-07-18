import requests
from xml.etree import ElementTree
from config import HEADERS, TIMEOUT
from news.base_provider import BaseNewsProvider, NewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


class IndustryFallbackProvider(BaseNewsProvider):
    name = "產業新聞"
    priority = 99

    def search(self, query, stock_info=None) -> list:
        if not stock_info:
            return []
        industry = stock_info.get("industry", "")
        if not industry:
            return []
        items = []
        try:
            keywords = [industry, f"{industry} 產業"]
            for kw in keywords:
                url = (
                    "https://news.google.com/rss/search"
                    f"?q={requests.utils.quote(kw)}"
                    "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
                )
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                root = ElementTree.fromstring(resp.content)
                for entry in root.iter("item"):
                    title = ""
                    link = ""
                    pub_date = ""
                    title_el = entry.find("title")
                    if title_el is not None and title_el.text:
                        title = title_el.text.strip()
                    link_el = entry.find("link")
                    if link_el is not None and link_el.text:
                        link = link_el.text.strip()
                    date_el = entry.find("pubDate")
                    if date_el is not None and date_el.text:
                        pub_date = self._normalize_date(date_el.text.strip())
                    source = "Google 新聞"
                    source_el = entry.find("source")
                    if source_el is not None and source_el.text:
                        source = source_el.text.strip()
                    if title:
                        items.append(NewsItem(
                            title=title, publish_date=pub_date,
                            source=source, url=link,
                            summary=f"[{industry}產業新聞]",
                            matched_keyword=kw,
                        ))
                if len(items) >= 10:
                    break
        except (requests.RequestException, ElementTree.ParseError) as e:
            logger.warning("IndustryFallback search error: %s", e)
        return items[:15]
