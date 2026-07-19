from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import uuid

from news.base_provider import NewsItem
from report.generator import PDFReport
from stock import data as stock_data


def test_pdf_renders_multiple_risk_and_news_multicells(monkeypatch):
    import report.generator as generator_module

    output_dir = Path(__file__).resolve().parents[1] / "output"
    output_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(generator_module, "OUTPUT_DIR", str(output_dir))
    filename = f"render-regression-{uuid.uuid4().hex}.pdf"
    report_progress = []
    health = {
        "total_score": 70,
        "level": "良好",
        "coverage": 0.5,
        "components": {
            "growth": {"score": 70, "weight": "22%", "status": "available"},
        },
    }
    report = PDFReport(
        stock_info={
            "stock_id": "2330",
            "name": "繁體中文長名稱壓力測試股份有限公司",
            "industry": "半導體",
            "market": "上市",
        },
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
                NewsItem(
                    title="第二則測試新聞", summary="第二則摘要", is_fallback=True
                ),
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
        model_assessments={
            "growth": {
                "rating": None,
                "experimental_rating": "C",
                "prediction_pct": 13.1,
                "prediction_interval_80": {"low_pct": -18.5, "high_pct": 31.0},
                "status": "experimental_not_deployable",
                "confidence": "low",
                "note": "模型尚未通過部署門檻。",
            },
            "safety": {
                "rating": None,
                "experimental_rating": "A",
                "score": 91.2,
                "coverage": 1.0,
                "status": "experimental_not_validated",
                "confidence": "low",
                "note": "不是破產機率。",
            },
            "separation_note": "兩個評級不平均。",
        },
        progress_callback=lambda current, total, section: report_progress.append(
            (current, total, section)
        ),
    )
    output = Path(report.generate(filename))
    try:
        assert output.read_bytes().startswith(b"%PDF")
        assert output.stat().st_size > 10_000
        assert report_progress[-1][0] == report_progress[-1][1]
        assert report_progress[-1][2] == "寫入 PDF 檔案"
    finally:
        output.unlink(missing_ok=True)


def test_same_stock_reports_receive_unique_atomic_paths(monkeypatch):
    import report.generator as generator_module

    tmp_path = (
        Path(__file__).resolve().parents[1]
        / "output"
        / f".report-test-{uuid.uuid4().hex}"
    )
    tmp_path.mkdir(parents=True)
    monkeypatch.setattr(generator_module, "OUTPUT_DIR", str(tmp_path))

    def generate_one():
        report = PDFReport(
            stock_info={
                "stock_id": "2330",
                "name": "台積電",
                "industry": "半導體",
                "market": "上市",
            },
            price_data={},
            price_info={},
            revenue_data=[],
            revenue_chart=None,
            eps_data=[],
            eps_chart=None,
            news_data={},
            valuation_analysis={},
        )
        return Path(report.generate())

    with ThreadPoolExecutor(max_workers=2) as executor:
        paths = list(executor.map(lambda _index: generate_one(), range(2)))
    try:
        assert paths[0] != paths[1]
        assert all(
            path.exists() and path.read_bytes().startswith(b"%PDF") for path in paths
        )
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        for path in paths:
            path.unlink(missing_ok=True)
        tmp_path.rmdir()


def test_same_stock_charts_receive_unique_atomic_paths(monkeypatch):
    tmp_path = (
        Path(__file__).resolve().parents[1]
        / "output"
        / f".chart-test-{uuid.uuid4().hex}"
    )
    tmp_path.mkdir(parents=True)
    monkeypatch.setattr(stock_data, "CHART_DIR", str(tmp_path))
    records = [{"year": 2025, "quarter": 1, "eps": 1.5, "label": "Q1 2025"}]
    with ThreadPoolExecutor(max_workers=2) as executor:
        paths = list(
            executor.map(
                lambda _index: Path(stock_data._plot_eps_chart(records, "2330")),
                range(2),
            )
        )
    try:
        assert paths[0] != paths[1]
        assert all(
            path.exists() and path.read_bytes().startswith(b"\x89PNG") for path in paths
        )
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        for path in paths:
            path.unlink(missing_ok=True)
        tmp_path.rmdir()
