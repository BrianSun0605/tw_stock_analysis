from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NewsItem:
    title: str
    publish_date: str = ""
    source: str = ""
    url: str = ""
    summary: str = ""
    matched_keyword: str = ""
    sentiment: str = ""


class BaseNewsProvider:
    name = "base"
    priority = 100

    def search(self, query: str, stock_info: Optional[dict] = None) -> List[NewsItem]:
        raise NotImplementedError

    def _safe(self, func, *args, **kwargs) -> List[NewsItem]:
        try:
            result = func(*args, **kwargs)
            if result is None:
                return []
            return result
        except Exception as e:
            logger.warning("news %s._safe error: %s", self.name, e)
            return []

    def _normalize_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        date_str = date_str.strip()
        formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日",
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%Y", "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str[:10] if len(date_str) >= 10 else date_str
