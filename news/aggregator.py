from datetime import datetime
from typing import Dict, List

from news.base_provider import NewsItem
from news.providers.google_news import GoogleNewsProvider, BingNewsProvider
from news.providers.moneydj import MoneyDJProvider
from news.providers.anue import AnueProvider
from news.providers.udn import UDNProvider
from news.providers.industry_fallback import IndustryFallbackProvider

POSITIVE_KW = {"成長", "創高", "利多", "突破", "賺", "大漲", "上漲", "新高", "獲利",
               "增加", "擴張", "買進", "看旺", "回升", "強勁", "受惠", "谷底翻"}
NEGATIVE_KW = {"衰退", "下滑", "利空", "大跌", "下跌", "新低", "虧損", "減少",
               "裁員", "降評", "賣出", "看衰", "危機", "違約", "破產", "緊縮"}


def classify_sentiment(text: str) -> str:
    if not text:
        return ""
    pos = sum(1 for k in POSITIVE_KW if k in text)
    neg = sum(1 for k in NEGATIVE_KW if k in text)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def generate_keywords(stock_info):
    keywords = []
    name = stock_info.get("name", "")
    stock_id = stock_info.get("stock_id", "")
    industry = stock_info.get("industry", "")
    aliases = stock_info.get("aliases", [])
    names = [name] + aliases
    for n in names:
        if n:
            keywords.append(n)
    if name and stock_id:
        keywords.append(f"{name} {stock_id}")
        keywords.append(f"{stock_id} {name}")
    if industry and name:
        keywords.append(f"{industry} {name}")
        keywords.append(f"{name} {industry}")
    seen = []
    for kw in keywords:
        if kw not in seen:
            seen.append(kw)
    return seen


class NewsAggregator:
    def __init__(self):
        self.providers = [
            GoogleNewsProvider(),
            BingNewsProvider(),
            MoneyDJProvider(),
            AnueProvider(),
            UDNProvider(),
            IndustryFallbackProvider(),
        ]

    def collect(self, stock_info) -> Dict:
        keywords = generate_keywords(stock_info)
        all_items = []
        provider_errors = {}
        for provider in self.providers:
            provider_items = []
            found_any = False
            for kw in keywords:
                if found_any and provider.priority < 50:
                    break
                try:
                    items = provider.search(kw, stock_info)
                    if items:
                        provider_items.extend(items)
                        found_any = True
                except Exception as e:
                    provider_errors[provider.name] = str(e)
                    continue
            if provider_items:
                deduped = self._deduplicate(provider_items)
                all_items.extend(deduped)
        all_items = self._deduplicate(all_items)
        for item in all_items:
            if not item.sentiment:
                item.sentiment = classify_sentiment(item.title + " " + item.summary)
        all_items.sort(key=lambda x: x.publish_date or "", reverse=True)
        pos = sum(1 for i in all_items if i.sentiment == "positive")
        neg = sum(1 for i in all_items if i.sentiment == "negative")
        neutral = sum(1 for i in all_items if i.sentiment == "neutral")
        industry = stock_info.get("industry", "")
        analysis_summary = self._generate_analysis(all_items, stock_info)
        return {
            "items": all_items[:30],
            "total": len(all_items),
            "industry_fallback_used": not any(
                i for i in all_items
                if i.matched_keyword == stock_info.get("name", "")
            ),
            "analysis_summary": analysis_summary,
            "provider_errors": provider_errors,
            "sentiment": {"positive": pos, "negative": neg, "neutral": neutral},
        }

    def _deduplicate(self, items):
        seen = set()
        result = []
        for item in items:
            key = item.title[:50].strip().lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    def _generate_analysis(self, items, stock_info):
        name = stock_info.get("name", "")
        industry = stock_info.get("industry", "")
        if not items:
            return f"近期未取得關於{name}之公開新聞資訊。可查閱公開資訊觀測站(MOPS)獲取最新公告。"
        titles = [i.title for i in items if i.title]
        news_count = len(items)
        summary = f"近期共有約{news_count}則關於{name}"
        if industry:
            summary += f"及{industry}產業"
        summary += "之公開新聞。"
        trending_down = any("衰退" in t or "下滑" in t or "利空" in t for t in titles)
        trending_up = any("成長" in t or "創高" in t or "利多" in t or "突破" in t for t in titles)
        if trending_up and not trending_down:
            summary += "近期新聞多偏正向。"
        elif trending_down and not trending_up:
            summary += "近期新聞多偏保守。"
        elif trending_up and trending_down:
            summary += "市場看法多空分歧。"
        return summary
