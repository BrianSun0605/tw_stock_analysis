#!/usr/bin/env python3
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR
from stock.normalizer import normalize, search_stock
from stock.data import (
    get_price_data,
    get_revenue_data,
    get_eps_data,
    get_basic_stock_info,
)
from stock.dividend import get_dividend_data
from stock.peers import get_peers_comparison
from news.aggregator import NewsAggregator
from valuation.analyzer import ValuationAnalyzer
from report.generator import PDFReport
from utils.logger import get_logger

logger = get_logger(__name__)


def analyze_stock(stock_id_or_name):
    stock_info = normalize(stock_id_or_name)
    stock_id = stock_info.get("stock_id", "")
    name = stock_info.get("name", "")
    if not stock_id:
        results = search_stock(stock_id_or_name)
        if not results:
            logger.info(f"查不到「{stock_id_or_name}」相關的股票，請重新輸入。")
            return None
        if len(results) == 1:
            stock_info = results[0]
        else:
            logger.info(f"找到多檔相關股票，請選擇：")
            for i, r in enumerate(results, 1):
                logger.info(f"  {i}. {r['name']} ({r['stock_id']}) - {r.get('industry', '')}")
            choice = input("請輸入編號：").strip()
            try:
                idx = int(choice) - 1
                stock_info = results[idx]
            except (ValueError, IndexError):
                logger.info("輸入無效。")
                return None
        stock_id = stock_info["stock_id"]
        name = stock_info["name"]
    if not stock_id:
        logger.info(f"無法識別股票代號。")
        return None
    logger.info(f"\n分析股票：{name} ({stock_id})")
    logger.info(f"產業：{stock_info.get('industry', '未知')}")
    logger.info(f"市場：{stock_info.get('market', '未知')}")
    logger.info("\n開始蒐集資料...\n")

    logger.info("[1/5] 取得基本資訊與股價資料...")
    market = stock_info.get("market", "")
    basic_info = get_basic_stock_info(stock_id, stock_info)
    is_etf = basic_info.get("is_etf", False)
    stock_info["is_etf"] = is_etf
    price_data, price_info = get_price_data(stock_id, market=market)
    has_price = any(p.get("df", None) is not None and not p["df"].empty for p in price_data.values())
    if has_price:
        logger.info("  ✓ 股價資料取得完成")
    else:
        logger.info("  ⚠ 股價資料取得不完全")

    logger.info("[2/5] 取得營收資料...")
    if is_etf:
        revenue_data, revenue_chart = [], None
        logger.info("  ⚠ ETF 無營收資料")
    else:
        revenue_data, revenue_chart = get_revenue_data(stock_id, market=market)
        logger.info(f"  {'✓' if revenue_data else '⚠'} 營收資料{'取得 ' + str(len(revenue_data)) + ' 筆' if revenue_data else '取得不完全'}")

    logger.info("[3/5] 取得 EPS 資料...")
    if is_etf:
        eps_data, eps_chart = [], None
        logger.info("  ⚠ ETF 無 EPS 資料")
    else:
        eps_data, eps_chart = get_eps_data(stock_id, market=market)
        logger.info(f"  {'✓' if eps_data else '⚠'} EPS 資料{'取得 ' + str(len(eps_data)) + ' 筆' if eps_data else '取得不完全'}")

    logger.info("[4/5] 蒐集新聞資訊...")
    aggregator = NewsAggregator()
    news_data = aggregator.collect(stock_info)
    news_count = len(news_data.get("items", []))
    logger.info(f"  {'✓' if news_count else '⚠'} 新聞{'取得 ' + str(news_count) + ' 則' if news_count else '取得不完全'}")

    if not eps_data and not is_etf:
        logger.error("查無此股票的 EPS 資料，無法進行分析。請確認股票代號是否正確（例如台積電請輸入 2330）。")
        return None
    if not has_price:
        logger.error("無法取得股價資料，請稍後再試或確認網路連線。")
        return None

    logger.info("\n進行估值分析...")
    try:
        va = ValuationAnalyzer(
            stock_id, eps_data, price_data, revenue_data, stock_info, price_info
        )
        valuation_analysis = va.full_analysis()
        if not is_etf:
            logger.info(f"  ✓ 健康評分：{valuation_analysis.get('health_score', {}).get('total_score', 'N/A')} 分")
    except Exception as e:
        logger.warning(f"  ⚠ 估值分析失敗：{e}")
        valuation_analysis = None

    logger.info("  取得股利資料...")
    dividend_data = get_dividend_data(stock_id, market=market)
    logger.info("  取得同業比較資料...")
    peers_data = get_peers_comparison(stock_id, basic_info.get("industry", ""), market=market)

    logger.info("\n產生 PDF 報告中...")
    try:
        generator = PDFReport(
            stock_info=basic_info,
            price_data=price_data,
            price_info=price_info,
            revenue_data=revenue_data,
            revenue_chart=revenue_chart,
            eps_data=eps_data,
            eps_chart=eps_chart,
            news_data=news_data,
            valuation_analysis=valuation_analysis,
            dividend_data=dividend_data,
            peers_data=peers_data,
        )
        output_path = generator.generate()
        logger.info(f"\n✓ PDF 報告已產生：{output_path}")
        logger.info(f"  請開啟目錄查看：{OUTPUT_DIR}")
        return output_path
    except Exception as e:
        logger.error(f"\n✗ 報告產生失敗：{e}")
        import traceback
        traceback.print_exc()
        return None


def batch_mode(stock_id_or_name):
    stock_info = normalize(stock_id_or_name)
    stock_id = stock_info.get("stock_id", "")
    if not stock_id:
        results = search_stock(stock_id_or_name)
        if not results:
            logger.warning(f"查不到「{stock_id_or_name}」相關的股票。")
            return
        stock_info = results[0]
        stock_id = stock_info["stock_id"]
    if not stock_id:
        logger.warning(f"無法識別：{stock_id_or_name}")
        return
    name = stock_info.get("name", stock_id)
    market = stock_info.get("market", "")
    logger.info(f"分析：{name} ({stock_id})")
    basic_info = get_basic_stock_info(stock_id, stock_info)
    price_data, price_info = get_price_data(stock_id, market=market)
    revenue_data, revenue_chart = get_revenue_data(stock_id, market=market)
    eps_data, eps_chart = get_eps_data(stock_id, market=market)
    aggregator = NewsAggregator()
    news_data = aggregator.collect(stock_info)
    try:
        va = ValuationAnalyzer(
            stock_id, eps_data, price_data, revenue_data, stock_info, price_info
        )
        valuation_analysis = va.full_analysis()
    except Exception as e:
        logger.warning("valuation analysis failed in batch mode: %s", e)
        valuation_analysis = None
    dividend_data = get_dividend_data(stock_id, market=market)
    peers_data = get_peers_comparison(stock_id, stock_info.get("industry", ""), market=market)
    generator = PDFReport(
        stock_info=basic_info, price_data=price_data, price_info=price_info,
        revenue_data=revenue_data, revenue_chart=revenue_chart,
        eps_data=eps_data, eps_chart=eps_chart,
        news_data=news_data,
        valuation_analysis=valuation_analysis,
        dividend_data=dividend_data,
        peers_data=peers_data,
    )
    path = generator.generate()
    logger.info(f"報告產生：{path}")
    return path


def interactive_menu():
    while True:
        logger.info("\n" + "=" * 50)
        logger.info("  台股投資分析 PDF 報告產生器")
        logger.info("=" * 50)
        logger.info("  1. 查詢單一股票並產出報告")
        logger.info("  2. 批次產出多檔股票報告")
        logger.info("  3. 查詢股票代號")
        logger.info("  0. 離開")
        logger.info("=" * 50)
        choice = input("請選擇操作項目：").strip()
        if choice == "1":
            query = input("\n請輸入股票代號或名稱：").strip()
            if query:
                analyze_stock(query)
            else:
                logger.info("未輸入查詢內容。")
        elif choice == "2":
            queries = input("\n請輸入多檔股票代號或名稱（以逗號或空格分隔）：").strip()
            if queries:
                for q in queries.replace(",", " ").split():
                    q = q.strip()
                    if q:
                        logger.info(f"\n{'─' * 40}")
                        logger.info(f"處理：{q}")
                        logger.info(f"{'─' * 40}")
                        batch_mode(q)
            else:
                logger.info("未輸入查詢內容。")
        elif choice == "3":
            query = input("\n請輸入股票代號或名稱：").strip()
            if query:
                results = search_stock(query)
                if not results:
                    stock_info = normalize(query)
                    if stock_info.get("stock_id"):
                        results = [stock_info]
                if results:
                    logger.info("\n查詢結果：")
                    for r in results:
                        logger.info(f"  {r['name']} ({r['stock_id']}) - {r.get('industry', '')}")
                else:
                    logger.info("查無此股票。")
            else:
                logger.info("未輸入查詢內容。")
        elif choice == "0":
            logger.info("感謝使用，再見！")
            break
        else:
            logger.info("無效的選擇，請重新輸入。")


def main():
    interactive_menu()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        batch_mode(sys.argv[1])
    else:
        main()
