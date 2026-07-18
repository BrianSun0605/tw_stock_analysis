from news.base_provider import BaseNewsProvider, NewsItem


class UDNProvider(BaseNewsProvider):
    """Disabled legacy adapter; the old endpoint did not provide dependable stock news."""

    name = "經濟日報／UDN（停用）"
    priority = 90

    def search(self, query: str, stock_info: dict | None = None) -> list[NewsItem]:
        raise RuntimeError("UDN provider is disabled pending a stable licensed source")
