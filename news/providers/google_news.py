import requests
from xml.etree import ElementTree
from config import HEADERS, TIMEOUT
from news.base_provider import BaseNewsProvider, NewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


class GoogleNewsProvider(BaseNewsProvider):
    name = "Google 新聞"
    priority = 10

    def search(self, query, stock_info=None) -> list:
        url = (
            "https://news.google.com/rss/search"
            f"?q={requests.utils.quote(query)}"
            "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        )
        try:
            resp = requests.get(url, headers={
                **HEADERS,
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            }, timeout=TIMEOUT)
            resp.raise_for_status()
            root = ElementTree.fromstring(resp.content)
            items = []
            for entry in root.iter("item"):
                title = ""
                link = ""
                pub_date = ""
                summary = ""
                title_el = entry.find("title")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                link_el = entry.find("link")
                if link_el is not None and link_el.text:
                    link = link_el.text.strip()
                date_el = entry.find("pubDate")
                if date_el is not None and date_el.text:
                    pub_date = self._normalize_date(date_el.text.strip())
                desc_el = entry.find("description")
                if desc_el is not None and desc_el.text:
                    summary = desc_el.text.strip()
                    summary = summary.replace("<![CDATA[", "").replace("]]>", "").strip()
                source = "Google 新聞"
                source_el = entry.find("source")
                if source_el is not None and source_el.text:
                    source = source_el.text.strip()
                if title:
                    items.append(NewsItem(
                        title=title,
                        publish_date=pub_date,
                        source=source,
                        url=link,
                        summary=summary[:200],
                        matched_keyword=query,
                    ))
            return items[:15]
        except (requests.RequestException, ElementTree.ParseError) as e:
            logger.warning("GoogleNews search failed: %s", e)
            return []


class BingNewsProvider(BaseNewsProvider):
    name = "Bing 新聞"
    priority = 20

    def search(self, query, stock_info=None) -> list:
        url = f"https://www.bing.com/news/search?q={requests.utils.quote(query)}&format=rss"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            root = ElementTree.fromstring(resp.content)
            items = []
            ns = {"": "http://www.w3.org/2005/Atom"}
            for entry in root.iter("entry"):
                title = ""
                link = ""
                pub_date = ""
                summary = ""
                title_el = entry.find("title")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                link_el = entry.find("link")
                if link_el is not None:
                    link = link_el.get("href", "")
                date_el = entry.find("updated")
                if date_el is not None and date_el.text:
                    pub_date = self._normalize_date(date_el.text.strip())
                summary_el = entry.find("summary")
                if summary_el is not None and summary_el.text:
                    summary = summary_el.text.strip()[:200]
                if title:
                    items.append(NewsItem(
                        title=title, publish_date=pub_date,
                        source="Bing 新聞", url=link,
                        summary=summary, matched_keyword=query,
                    ))
            return items[:15]
        except (requests.RequestException, ElementTree.ParseError) as e:
            logger.warning("BingNews search failed: %s", e)
            return []
