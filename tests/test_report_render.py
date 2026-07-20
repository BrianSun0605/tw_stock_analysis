from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import re
import uuid

from news.base_provider import NewsItem
from report.generator import PDFReport
from stock import data as stock_data


def test_pdf_uses_a_truetype_cjk_font_for_portable_unicode_mapping():
    from config import PDF_FONT_PATH

    font_path = Path(PDF_FONT_PATH)
    assert font_path.name == "NotoSansTC-Variable.ttf"
    assert font_path.read_bytes()[:4] == b"\x00\x01\x00\x00"


def test_report_date_helpers_tolerate_partial_source_records():
    report = PDFReport(
        stock_info={"stock_id": "2330"},
        price_data={},
        price_info={},
        revenue_data=[{"label": "latest revenue"}],
        revenue_chart=None,
        eps_data=[{"label": "Q1 2026", "eps": 1.2}],
        eps_chart=None,
        news_data={
            "items": [
                NewsItem(
                    title="原始新聞標題",
                    source="Official source",
                    publish_date="2026-07-20",
                )
            ]
        },
    )
    assert report._latest_revenue_date() == "latest revenue"
    assert report._latest_eps_date() == "Q1 2026"


def test_english_pdf_uses_english_sections_and_preserves_raw_security_data(monkeypatch):
    import report.generator as generator_module

    output_dir = Path(__file__).resolve().parents[1] / "output"
    monkeypatch.setattr(generator_module, "OUTPUT_DIR", str(output_dir))
    progress = []
    report = PDFReport(
        stock_info={"stock_id": "2330", "name": "台積電", "name_en": "TSMC"},
        price_data={},
        price_info={},
        revenue_data=[],
        revenue_chart=None,
        eps_data=[],
        eps_chart=None,
        news_data={
            "items": [
                NewsItem(
                    title="原始新聞標題",
                    source="Official source",
                    publish_date="2026-07-20",
                )
            ]
        },
        model_assessments={
            "growth": {
                "rating": None,
                "reference_rating": "D",
                "experimental_rating": None,
                "status": "experimental_not_deployable",
                "formula": {
                    "raw_equation": "raw = intercept + sum(coefficient × standardized feature)",
                    "prediction_equation": "prediction = calibration_offset + shrinkage × raw",
                },
            },
            "safety": {
                "rating": None,
                "reference_rating": "A",
                "experimental_rating": None,
                "status": "reference_formula_not_locally_validated",
                "formula": {"equation": "Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5"},
            },
        },
        language="en",
        progress_callback=lambda current, total, section: progress.append(section),
    )
    output = Path(report.generate(f"english-regression-{uuid.uuid4().hex}.pdf"))
    try:
        assert output.read_bytes().startswith(b"%PDF")
        assert progress == [
            "Cover page",
            "Security profile",
            "Model estimates",
            "Price trend",
            "Revenue analysis",
            "EPS analysis",
            "Valuation or ETF structure",
            "Fundamental health and quality",
            "Financial metrics and sources",
            "Risk signals and analysis notes",
            "Peers",
            "Dividends",
            "News summary",
            "Glossary",
            "Method and disclaimer",
            "Writing PDF file",
        ]
    finally:
        output.unlink(missing_ok=True)


def test_english_report_keeps_detail_pages_when_rich_analysis_data_exists(monkeypatch):
    import report.generator as generator_module

    output_dir = Path(__file__).resolve().parents[1] / "output"
    output_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(generator_module, "OUTPUT_DIR", str(output_dir))
    filename = f"english-detail-regression-{uuid.uuid4().hex}.pdf"
    report = PDFReport(
        stock_info={
            "stock_id": "2330",
            "name": "Test Company",
            "name_en": "Test Company Ltd.",
            "market": "TWSE",
            "industry": "Semiconductors",
            "current_price": 100.0,
            "description": "A source-text company description for the report regression test.",
        },
        price_data={
            "1y": {
                "high": {"price": 120, "date": "2026-01-01"},
                "low": {"price": 80, "date": "2025-01-01"},
            }
        },
        price_info={
            "grossMargins": 0.5,
            "operatingMargins": 0.4,
            "profitMargins": 0.3,
            "returnOnEquity": 0.2,
            "returnOnAssets": 0.1,
            "debtToEquity": 20,
            "freeCashflow": 1000,
            "totalCash": 2000,
            "totalDebt": 500,
            "bookValue": 40,
            "forwardPE": 15,
            "beta": 1.1,
            "fiftyTwoWeekHigh": 120,
            "fiftyTwoWeekLow": 80,
        },
        revenue_data=[
            {
                "year": 2026,
                "month": month,
                "revenue": 1000 + month,
                "mom": 1.0,
                "yoy": 10.0,
                "source": "Official source",
            }
            for month in range(1, 7)
        ],
        revenue_chart=None,
        eps_data=[
            {
                "label": f"Q{quarter} 2025",
                "eps": float(quarter),
                "source": "Official source",
            }
            for quarter in range(1, 5)
        ],
        eps_chart=None,
        news_data={
            "analysis_summary": "A source-backed summary for the regression test.",
            "items": [
                NewsItem(
                    title="Public disclosure title",
                    summary="Public disclosure summary.",
                    source="Official source",
                    publish_date="2026-07-20",
                )
            ],
        },
        valuation_analysis={
            "fair_price_range": {
                "current_pe": 20,
                "cheap": 80,
                "fair": 100,
                "expensive": 120,
                "margin_safety_8": 80,
                "ttm_eps": 5,
                "pe_p25": 16,
                "pe_p50": 20,
                "pe_p75": 24,
                "sample_size": 60,
            },
            "health_score": {
                "total_score": 72,
                "level": "Good",
                "coverage": 1.0,
                "components": {
                    "growth": {"score": 80, "weight": "22%", "status": "available"},
                    "quality": {"score": 70, "weight": "15%", "status": "available"},
                },
            },
            "quality_score": {
                "piotroski_f_score": 7,
                "piotroski_details": {"available_count": 9},
                "altman_z_score": 3.1,
                "graham_number": 90,
            },
            "overall_rating": {"rating": "B", "score": 72},
            "peg": {
                "peg": 1.2,
                "pe": 20,
                "eps_growth_pct": 16,
                "verdict": "Reference only",
            },
            "revenue_growth": {
                "avg_recent_yoy_pct": 10,
                "consecutive_positive_months": 4,
                "consecutive_negative_months": 0,
                "accelerating": True,
            },
            "risk_warnings": [
                {
                    "level": "yellow",
                    "type": "Valuation",
                    "horizon": "mid term",
                    "msg": "Reference warning.",
                }
            ],
            "analysis_text": "Detailed regression narrative.",
        },
        dividend_data={
            "yield": 1.2,
            "consecutive_years": 5,
            "last_completed_year": 2025,
            "avg_yield_3y": 1.1,
            "ex_dividend_date": "2026-09-01",
            "dividend_months": [3, 6, 9, 12],
            "history": [{"year": 2025, "dividend": 5.0, "status": "completed"}],
        },
        peers_data=[
            {
                "stock_id": "9999",
                "name": "Peer",
                "price": 90,
                "pe": 18,
                "dividend_yield": 1.0,
            }
        ],
        financial_snapshot={
            "observed_at": "2026-Q2",
            "status": "official",
            "report_type": "ci",
            "fields": {
                "totalRevenue": 1000,
                "operatingIncome": 400,
                "totalAssets": 5000,
                "totalLiabilities": 2000,
            },
        },
        language="en",
    )
    output = Path(report.generate(filename))
    try:
        assert output.read_bytes().startswith(b"%PDF")
        assert len(report.pdf.pages) >= 15
    finally:
        output.unlink(missing_ok=True)


def test_english_dynamic_analysis_text_and_risk_signals_do_not_leak_chinese():
    report = PDFReport(
        stock_info={"stock_id": "2330", "name": "台積電", "name_en": "TSMC"},
        price_data={},
        price_info={},
        revenue_data=[],
        revenue_chart=None,
        eps_data=[],
        eps_chart=None,
        news_data={},
        language="en",
    )
    value = {
        "fair_price_range": {"current_price": 600.0},
        "health_score": {"total_score": 45.7, "level": "普通", "coverage": 1.0},
        "overall_rating": {"rating": "C", "score": 53.7, "coverage": 1.0},
        "quality_score": {
            "piotroski_f_score": None,
            "piotroski_details": {"available_count": 3},
            "graham_number": 415.28,
        },
        "peg": {"verdict": "需要兩組完整且連續的四季 EPS 才能計算成長率"},
        "revenue_growth": {
            "avg_recent_yoy_pct": -14.1,
            "consecutive_positive_months": 0,
            "decelerating": True,
        },
        "risk_warnings": [
            {
                "level": "red",
                "type": "營收衰退",
                "horizon": "mid",
                "msg": "連續 3 個月營收年增率為負",
            },
            {
                "level": "yellow",
                "type": "成長放緩",
                "horizon": "mid",
                "msg": "營收年增率動能減弱",
            },
            {
                "level": "yellow",
                "type": "財務壓力",
                "horizon": "long",
                "msg": "Altman Z-Score 2.759，財務結構處於灰色地帶",
            },
        ],
        "analysis_text": "【台積電 估值分析】\n綜合評級：C（53.7 分）",
    }

    narrative = report._english_analysis_narrative(value)
    warning_text = "\n".join(
        " ".join(
            [
                report._english_risk_category(warning["type"]),
                report._english_risk_horizon(warning["horizon"]),
                report._english_risk_message(warning["msg"]),
            ]
        )
        for warning in value["risk_warnings"]
    )
    peg_verdict = report._english_risk_message(value["peg"]["verdict"])

    assert not re.search(
        r"[\u3400-\u9fff]", f"{narrative}\n{warning_text}\n{peg_verdict}"
    )
    assert "TSMC valuation analysis" in narrative
    assert "Revenue contraction Medium term" in warning_text
    assert "Altman Z-Score 2.759 is in the reference gray zone." in warning_text
    assert (
        peg_verdict
        == "Two complete, consecutive sets of four quarterly EPS observations are required to calculate growth."
    )

    # Exercise the report-section path too, so the PEG table, risk rows, and
    # narrative cannot accidentally bypass the localized helpers in future.
    report.valuation_analysis = value
    rendered_blocks = []
    rendered_rows = []
    report._multi_cell = lambda _width, _height, text, **_kwargs: (
        rendered_blocks.append(str(text))
    )
    report._render_table = lambda _widths, rows, **_kwargs: rendered_rows.extend(rows)
    report._add_english_risk_analysis_section()
    rendered_text = "\n".join(
        rendered_blocks + [str(item) for row in rendered_rows for item in row]
    )
    assert not re.search(r"[\u3400-\u9fff]", rendered_text)
    assert (
        "Two complete, consecutive sets of four quarterly EPS observations are required to calculate growth."
        in rendered_text
    )
    assert "Revenue contraction Medium term" in rendered_text


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
                "formula": {
                    "raw_equation": "raw = intercept + sum(coefficient × standardized feature)",
                    "prediction_equation": "prediction = calibration_offset + shrinkage × raw",
                },
                "confidence": "low",
                "note": "模型尚未通過部署門檻。",
            },
            "safety": {
                "rating": None,
                "experimental_rating": "A",
                "score": 91.2,
                "coverage": 1.0,
                "status": "experimental_not_validated",
                "formula": {
                    "equation": "Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5",
                },
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
        pdf_bytes = output.read_bytes()
        assert pdf_bytes.startswith(b"%PDF")
        assert output.stat().st_size > 10_000
        # TrueType fonts are emitted as CIDFontType2.  CIDFontType0 is the
        # CFF/OTF path that produced garbled Traditional Chinese in some PDF
        # viewers despite an apparently valid ToUnicode map.
        assert b"/CIDFontType2" in pdf_bytes
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
