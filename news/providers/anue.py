from news.base_provider import BaseNewsProvider, NewsItem


class AnueProvider(BaseNewsProvider):
    """Disabled legacy adapter; selectors were not reliable enough for production."""

    name = "鉅亨網（停用）"
    priority = 90

    def search(self, query: str, stock_info: dict | None = None) -> list[NewsItem]:
        raise RuntimeError("Anue provider is disabled pending a stable licensed source")
