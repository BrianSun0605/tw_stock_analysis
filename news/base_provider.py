from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    is_fallback: bool = False


class BaseNewsProvider:
    name = "base"
    priority = 100

    def search(self, query: str, stock_info: Optional[dict] = None) -> List[NewsItem]:
        raise NotImplementedError

    def _safe(self, func, *args, **kwargs) -> List[NewsItem]:
        try:
            result = func(*args, **kwargs)
            return result or []
        except Exception as exc:
            logger.warning("news %s._safe error: %s", self.name, exc)
            return []

    def _normalize_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        value = date_str.strip()
        try:
            parsed = parsedate_to_datetime(value)
            if parsed:
                return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OverflowError):
            pass

        iso_value = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(iso_value).strftime("%Y-%m-%d")
        except ValueError:
            pass

        for fmt in ("%Y/%m/%d", "%Y年%m月%d日", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return ""
