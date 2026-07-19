from research.backtest.download_official_revenue import parse_archive
from models.growth_features import FEATURE_NAMES, extract_growth_features


def test_official_archive_parser_uses_code_and_revenue_columns():
    # Production archives contain hundreds of rows; keep parser validation while
    # replacing the minimum only for this unit fixture.
    rows = []
    for index in range(500):
        code = f"{1000 + index:04d}"
        rows.append(f"<tr><td>{code}</td><td>測試</td><td>{index + 1:,}</td></tr>")
    content = (
        "<table class='hasBorder'><tr><th>公司代號</th><th>公司名稱</th>"
        "<th>當月營收</th></tr>" + "".join(rows) + "</table>"
    ).encode("cp950")
    parsed = parse_archive(
        content,
        market="sii",
        year=2025,
        month=12,
        source_url="https://official.example/archive",
    )
    assert len(parsed) == 500
    assert parsed[0]["stock_id"] == "1000"
    assert parsed[0]["revenue_thousand"] == 1
    assert parsed[-1]["market"] == "上市"


def test_growth_features_need_exactly_24_nonnegative_months():
    assert extract_growth_features([100.0] * 23) is None
    assert extract_growth_features([100.0] * 23 + [-1.0]) is None
    features = extract_growth_features([100.0] * 12 + [110.0] * 12)
    assert list(features) == FEATURE_NAMES
    assert round(features["growth_12m_yoy"], 3) == 0.1
    assert features["monthly_yoy_volatility"] == 0.0
