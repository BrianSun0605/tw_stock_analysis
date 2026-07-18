#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR
from services.analysis import AnalysisError, analyze
from stock.normalizer import normalize, search_stock
from utils.logger import get_logger

logger = get_logger(__name__)


def _log_progress(message: str) -> None:
    logger.info(message)


def analyze_stock(stock_id_or_name):
    try:
        result = analyze(stock_id_or_name, progress=_log_progress)
    except AnalysisError as exc:
        logger.error("%s", exc)
        return None
    except Exception:
        logger.exception("分析失敗")
        return None
    logger.info("PDF 報告已產生：%s", result.output_path)
    logger.info("輸出目錄：%s", OUTPUT_DIR)
    return result.output_path


def batch_mode(stock_id_or_name):
    """Batch and single-stock modes deliberately share the same pipeline."""
    return analyze_stock(stock_id_or_name)


def interactive_menu():
    while True:
        logger.info("\n%s", "=" * 50)
        logger.info("  台股投資分析 PDF 報告產生器")
        logger.info("%s", "=" * 50)
        logger.info("  1. 查詢單一股票並產出報告")
        logger.info("  2. 批次產出多檔股票報告")
        logger.info("  3. 查詢股票代號")
        logger.info("  0. 離開")
        choice = input("請選擇操作項目：").strip()
        if choice == "1":
            query = input("請輸入股票代號或名稱：").strip()
            if query:
                analyze_stock(query)
        elif choice == "2":
            queries = input("請輸入多檔股票代號或名稱（以逗號或空格分隔）：").strip()
            for query in queries.replace(",", " ").split():
                batch_mode(query)
        elif choice == "3":
            query = input("請輸入股票代號或名稱：").strip()
            results = search_stock(query) if query else []
            if not results and query:
                stock = normalize(query)
                results = [stock] if stock.get("stock_id") else []
            if not results:
                logger.info("查無此股票。")
            for stock in results:
                logger.info(
                    "%s (%s) - %s / %s",
                    stock["name"],
                    stock["stock_id"],
                    stock.get("industry", ""),
                    stock.get("market", ""),
                )
        elif choice == "0":
            break
        else:
            logger.info("無效的選擇，請重新輸入。")


def main():
    interactive_menu()


def cli(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        main()
        return 0
    return 0 if batch_mode(args[0]) else 1


if __name__ == "__main__":
    raise SystemExit(cli())
