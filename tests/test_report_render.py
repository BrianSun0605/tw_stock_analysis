from pathlib import Path
import uuid

from news.base_provider import NewsItem
from report.generator import PDFReport


def test_pdf_renders_multiple_risk_and_news_multicells(monkeypatch):
    import report.generator as generator_module

    output_dir = Path(__file__).resolve().parents[1] / "output"
    output_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(generator_module, "OUTPUT_DIR", str(output_dir))
    filename = f"render-regression-{uuid.uuid4().hex}.pdf"
    health = {
        "total_score": 70,
        "level": "良好",
        "coverage": 0.5,
        "components": {
            "growth": {"score": 70, "weight": "22%", "status": "available"},
        },
    }
    report = PDFReport(
        stock_info={"stock_id": "2330", "name": "繁體中文長名稱壓力測試股份有限公司", "industry": "半導體", "market": "上市"},
        price_data={},
        price_info={},
        revenue_data=[],
        revenue_chart=None,
        eps_data=[],
        eps_chart=None,
        news_data={
            "analysis_summary": "兩則新聞用於連續換行測試。",
            "items": [
                NewsItem(title="第一則測試新聞", summary="第一則摘要"),
                NewsItem(title="第二則測試新聞", summary="第二則摘要"),
            ],
        },
        valuation_analysis={
            "health_score": health,
            "overall_rating": {"rating": "B", "score": 70},
            "risk_warnings": [
                {"level": "yellow", "msg": "第一項風險提示"},
                {"level": "green", "msg": "第二項風險提示"},
            ],
            "analysis_text": "這是換行安全性的回歸測試。",
        },
    )
    output = Path(report.generate(filename))
    try:
        assert output.read_bytes().startswith(b"%PDF")
        assert output.stat().st_size > 10_000
    finally:
        output.unlink(missing_ok=True)
