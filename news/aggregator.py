from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from news.providers.google_news import BingNewsProvider, GoogleNewsProvider
from news.providers.industry_fallback import IndustryFallbackProvider

POSITIVE_KW = {
    "成長",
    "創高",
    "利多",
    "突破",
    "賺",
    "大漲",
    "上漲",
    "新高",
    "獲利",
    "增加",
    "擴張",
    "買進",
    "看旺",
    "回升",
    "強勁",
    "受惠",
    "谷底翻",
}
NEGATIVE_KW = {
    "衰退",
    "下滑",
    "利空",
    "大跌",
    "下跌",
    "新低",
    "虧損",
    "減少",
    "裁員",
    "降評",
    "賣出",
    "看衰",
    "危機",
    "違約",
    "破產",
    "緊縮",
}


def classify_sentiment(text: str) -> str:
    if not text:
        return "neutral"
    positive = sum(keyword in text for keyword in POSITIVE_KW)
    negative = sum(keyword in text for keyword in NEGATIVE_KW)
    return (
        "positive"
        if positive > negative
        else "negative"
        if negative > positive
        else "neutral"
    )


def generate_keywords(stock_info):
    name = stock_info.get("name", "")
    stock_id = stock_info.get("stock_id", "")
    aliases = [alias for alias in stock_info.get("aliases", []) if alias]
    primary = " ".join(part for part in (name, stock_id) if part)
    return [primary or name or stock_id, *aliases]


class NewsAggregator:
    def __init__(self):
        self.providers = [GoogleNewsProvider(), BingNewsProvider()]

    def collect(self, stock_info) -> Dict:
        keywords = list(
            dict.fromkeys(
                keyword.strip()
                for keyword in generate_keywords(stock_info)
                if keyword.strip()
            )
        )[:3]
        all_items = []
        provider_status = {}
        if keywords:
            for provider in self.providers:
                provider_status[provider.name] = {
                    "status": "ok",
                    "count": 0,
                    "queries": len(keywords),
                    "errors": [],
                }
            with ThreadPoolExecutor(
                max_workers=min(4, len(self.providers) * len(keywords))
            ) as executor:
                futures = {
                    executor.submit(provider.search, query, stock_info): (
                        provider,
                        query,
                    )
                    for provider in self.providers
                    for query in keywords
                }
                for future in as_completed(futures):
                    provider, query = futures[future]
                    status = provider_status[provider.name]
                    try:
                        items = future.result()
                        all_items.extend(items)
                        status["count"] += len(items)
                    except Exception as exc:
                        status["errors"].append(f"{query}: {str(exc)[:120]}")
            for status in provider_status.values():
                if status["errors"]:
                    status["status"] = "partial" if status["count"] else "error"
                    status["error"] = "; ".join(status.pop("errors"))[:320]
                else:
                    status.pop("errors")

        fallback_used = False
        if not all_items:
            fallback = IndustryFallbackProvider()
            try:
                items = fallback.search("", stock_info)
                all_items.extend(items)
                fallback_used = bool(items)
                provider_status[fallback.name] = {"status": "ok", "count": len(items)}
            except Exception as exc:
                provider_status[fallback.name] = {
                    "status": "error",
                    "count": 0,
                    "error": str(exc)[:160],
                }

        items = self._deduplicate(all_items)
        for item in items:
            item.sentiment = classify_sentiment(f"{item.title} {item.summary}")
        items.sort(key=lambda item: item.publish_date or "", reverse=True)
        counts = {
            label: sum(item.sentiment == label for item in items)
            for label in ("positive", "negative", "neutral")
        }
        return {
            "items": items[:30],
            "total": len(items),
            "industry_fallback_used": fallback_used,
            "analysis_summary": self._generate_analysis(items, stock_info, counts),
            "provider_status": provider_status,
            "provider_errors": {
                name: status["error"]
                for name, status in provider_status.items()
                if status["status"] in {"error", "partial"}
            },
            "sentiment": counts,
            "sentiment_method": "keyword_heuristic",
        }

    @staticmethod
    def _deduplicate(items):
        seen = set()
        result = []
        for item in items:
            normalized_title = " ".join(item.title.lower().split())
            key = (normalized_title, item.url.split("?")[0])
            if normalized_title and key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def _generate_analysis(items, stock_info, counts):
        name = stock_info.get("name", "")
        if not items:
            return (
                f"近期未取得關於{name}的可驗證公開新聞；可另查公開資訊觀測站重大訊息。"
            )
        total = len(items)
        if total < 3:
            tendency = "樣本不足，不判定傾向"
        elif counts["positive"] > counts["negative"] * 1.5:
            tendency = "關鍵字正向項目較多"
        elif counts["negative"] > counts["positive"] * 1.5:
            tendency = "關鍵字負向項目較多"
        else:
            tendency = "關鍵字正負向分布接近"
        return f"共整理 {total} 則關於{name}的公開新聞；{tendency}。此結果僅為關鍵字分類，不是投資訊號。"
