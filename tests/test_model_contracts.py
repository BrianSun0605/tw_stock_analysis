import json
import uuid
from pathlib import Path

from models import growth_model
from models.safety_model import assess_company_safety, assess_etf_structure
from services.analysis import AnalysisError, _ensure_supported_analysis_type
from stock.mops_history import _parse_archive, parse_month_html


def test_mops_individual_month_parser_reads_official_table():
    html = """
    <table class="hasBorder">
      <tr><th>項目</th><th>營業收入淨額</th></tr>
      <tr><td>本月</td><td>442,679,969</td></tr>
      <tr><td>去年同期</td><td>263,708,978</td></tr>
      <tr><td>增減百分比</td><td>67.87</td></tr>
    </table>
    """
    result = parse_month_html(html, year=2026, month=6)
    assert result["revenue"] == 442_679_969
    assert result["yoy"] == 67.87
    assert result["source"] == "MOPS official company query"
    assert result["unit"] == "TWD_thousand"


def test_mops_history_months_are_zero_padded_for_official_form(monkeypatch):
    posted = []

    class Response:
        text = "<table><tr><td>本月</td><td>100</td></tr></table>"

        def raise_for_status(self):
            return None

    class Session:
        def get(self, *args, **kwargs):
            return Response()

        def post(self, *args, **kwargs):
            posted.append(kwargs["data"]["month"])
            return Response()

    monkeypatch.setattr("stock.mops_history.requests.Session", Session)
    from stock.mops_history import _fetch_chunk

    _fetch_chunk("2330", [(2025, 0), (2025, 9)])
    assert posted == ["01", "10"]


def test_mops_archive_parser_supports_official_big5_rows():
    rows = "".join(
        f"<tr><td>{1000 + index:04d}</td><td>測試</td><td>{index + 1:,}</td></tr>"
        for index in range(500)
    )
    parsed = _parse_archive(
        f"<table>{rows}</table>".encode("cp950"),
        "https://official.example/archive",
    )
    assert parsed["1000"] == 1
    assert parsed["1499"] == 500


def test_etf_growth_model_is_not_applicable():
    result = growth_model.assess_revenue_growth([], {"asset_type": "etf"})
    assert result["status"] == "not_applicable"
    assert result["rating"] is None


def test_failed_deployment_gate_hides_formal_grade_but_keeps_experimental(monkeypatch):
    artifact = {
        "model_version": "test",
        "target": "future growth",
        "feature_mean": [0.0] * 9,
        "feature_std": [1.0] * 9,
        "coefficients": [0.0] * 9,
        "intercept": 0.1,
        "residual_quantiles": [-0.2 + index * 0.004 for index in range(101)],
        "test_metrics": {"mae": 0.2},
        "deployment_gate": {"passed": False},
    }
    path = (
        Path(__file__).resolve().parents[1]
        / "output"
        / f".growth-model-test-{uuid.uuid4().hex}.json"
    )
    try:
        path.write_text(json.dumps(artifact), encoding="utf-8")
        monkeypatch.setattr(growth_model, "ARTIFACT_PATH", path)
        records = [
            {
                "year": 2024 + (month - 1) // 12,
                "month": (month - 1) % 12 + 1,
                "revenue": 100.0,
            }
            for month in range(1, 25)
        ]
        result = growth_model.assess_revenue_growth(records, {"asset_type": "stock"})
        assert result["status"] == "experimental_not_deployable"
        assert result["rating"] is None
        assert result["experimental_rating"] in "ABCDEF"
        assert (
            result["prediction_interval_80"]["low"]
            < result["prediction_interval_80"]["high"]
        )
    finally:
        path.unlink(missing_ok=True)


def test_growth_and_safety_grades_are_not_averaged_together():
    safe = assess_company_safety(
        {"name": "一般公司", "industry": "半導體", "asset_type": "stock"},
        {
            "totalAssets": 1000,
            "totalLiabilities": 200,
            "currentAssets": 500,
            "currentLiabilities": 200,
            "retainedEarnings": 500,
            "totalRevenue": 1000,
            "operatingIncome": 300,
            "netIncomeToCommon": 250,
        },
    )
    risky = assess_company_safety(
        {"name": "一般公司", "industry": "半導體", "asset_type": "stock"},
        {
            "totalAssets": 1000,
            "totalLiabilities": 950,
            "currentAssets": 100,
            "currentLiabilities": 400,
            "retainedEarnings": -300,
            "totalRevenue": 1000,
            "operatingIncome": -200,
            "netIncomeToCommon": -300,
        },
    )
    assert safe["rating"] is None
    assert risky["rating"] is None
    assert safe["experimental_rating"] in ("A", "B")
    assert risky["experimental_rating"] in ("E", "F")
    assert safe["status"] == "experimental_not_validated"
    assert "growth" not in safe


def test_financial_company_waits_for_specialized_safety_model():
    result = assess_company_safety(
        {"name": "富邦金", "industry": "金融", "asset_type": "stock"},
        {"totalAssets": 1000},
    )
    assert result["status"] == "specialized_model_pending"
    assert result["rating"] is None


def test_etf_uses_structure_screen_not_company_formula():
    result = assess_etf_structure(
        {
            "total_assets": 100_000_000_000,
            "avg_volume": 10_000_000,
            "expense_ratio": 0.004,
            "premium_pct": 0.1,
            "tracking_index": "臺灣50指數",
        }
    )
    assert result["rating"] is None
    assert result["experimental_rating"] in "ABCDEF"
    assert result["target"].startswith("ETF")
    assert result["model_version"] == "etf_structure_screen_v1"


def test_special_products_never_use_company_growth_or_safety_formula():
    for asset_type in ("etn", "reit", "preferred_stock"):
        growth = growth_model.assess_revenue_growth([], {"asset_type": asset_type})
        safety = assess_company_safety({"asset_type": asset_type}, {})
        assert growth["status"] == "specialized_product_model_pending"
        assert safety["status"] == "specialized_product_model_pending"
        assert growth["rating"] is None
        assert safety["rating"] is None


def test_analysis_explains_unsupported_special_product_instead_of_misrating():
    try:
        _ensure_supported_analysis_type({"asset_type": "etn"})
    except AnalysisError as exc:
        assert "已納入官方搜尋主檔" in str(exc)
        assert "不產生評級或 PDF" in str(exc)
    else:
        raise AssertionError("ETN should not enter the company analysis flow")
