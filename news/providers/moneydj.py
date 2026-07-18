from news.base_provider import BaseNewsProvider, NewsItem


class MoneyDJProvider(BaseNewsProvider):
    """Disabled legacy adapter; no stable, licensed feed is configured."""

    name = "MoneyDJ（停用）"
    priority = 90

    def search(self, query: str, stock_info: dict | None = None) -> list[NewsItem]:
        raise RuntimeError("MoneyDJ provider is disabled pending a stable licensed source")
