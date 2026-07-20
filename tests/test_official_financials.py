import shutil
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

from stock import data as stock_data
from stock import official_financials as official


ROOT = Path(__file__).resolve().parents[1]


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _dataset(rows, url="https://official.example/data", status="official"):
    return official.OfficialDataset(
        rows=rows,
        source_url=url,
        fetched_at="2026-07-18T00:00:00+00:00",
        status=status,
    )


def test_official_revenue_has_value_source_period_unit_and_status(monkeypatch):
    monkeypatch.setattr(
        official,
        "_load_dataset",
        lambda *_args, **_kwargs: _dataset(
            [
                {
                    "出表日期": "1150717",
                    "資料年月": "11506",
                    "公司代號": "2330",
                    "營業收入-當月營收": "442679969",
                    "營業收入-上月營收": "416975163",
                    "營業收入-去年當月營收": "263708978",
                    "營業收入-上月比較增減(%)": "6.16",
                    "營業收入-去年同月增減(%)": "67.87",
                }
            ]
        ),
    )
    item = official.get_official_revenue("2330", "上市")[0]
    assert item["revenue"] == 442_679_969
    assert item["observed_at"] == "2026-06"
    assert item["source_date"] == "2026-07-17"
    assert item["unit"] == "TWD_thousand"
    assert item["status"] == "official"
    assert item["data_value"]["currency"] == "TWD"


def test_revenue_data_expands_latest_official_month_with_mops_history(monkeypatch):
    latest = {
        "year": 2026,
        "month": 6,
        "revenue": 442_679_969,
        "source": "TWSE OpenAPI",
        "status": "official",
    }
    history = [
        {"year": 2024, "month": 7, "revenue": 1},
        latest,
    ]
    monkeypatch.setattr(stock_data, "get_official_revenue", lambda *_args: [latest])
    monkeypatch.setattr(
        stock_data,
        "get_monthly_revenue_history",
        lambda stock_id, **kwargs: history,
    )
    monkeypatch.setattr(
        stock_data, "_plot_revenue_chart", lambda *_args, **_kwargs: None
    )

    result, chart = stock_data.get_revenue_data("2330", market="上市")

    assert result == history
    assert chart is None


def test_report_type_routing_covers_company_and_financial_variants():
    assert (
        official.report_type_candidates({"name": "台積電", "industry": "半導體"})[0]
        == "ci"
    )
    assert (
        official.report_type_candidates({"name": "富邦金", "industry": "金融"})[0]
        == "fh"
    )
    assert (
        official.report_type_candidates({"name": "彰銀", "industry": "金融"})[0]
        == "basi"
    )
    assert (
        official.report_type_candidates({"name": "元大證券", "industry": "金融"})[0]
        == "bd"
    )
    assert (
        official.report_type_candidates({"name": "某保險", "industry": "金融"})[0]
        == "ins"
    )
    assert set(
        official.report_type_candidates({"name": "未知金融", "industry": "金融"})
    ) == {"ci", "basi", "bd", "fh", "ins", "mim"}


def test_official_financials_convert_thousand_twd_and_keep_cumulative_eps(monkeypatch):
    income = {
        "出表日期": "1150718",
        "年度": "115",
        "季別": "1",
        "公司代號": "2330",
        "營業收入": "100.00",
        "營業利益（損失）": "25.00",
        "本期淨利（淨損）": "20.00",
        "基本每股盈餘（元）": "2.5",
    }
    balance = {
        "出表日期": "1150718",
        "年度": "115",
        "季別": "1",
        "公司代號": "2330",
        "流動資產": "80.00",
        "資產總額": "200.00",
        "流動負債": "30.00",
        "負債總額": "90.00",
        "保留盈餘": "50.00",
        "權益總額": "110.00",
        "每股參考淨值": "12.3",
    }

    def find(_stock_id, _market, _stock_info, statement):
        return (
            income if statement == "income" else balance,
            _dataset([income if statement == "income" else balance]),
            "ci",
        )

    monkeypatch.setattr(official, "_find_financial_row", find)
    result = official.get_official_financials(
        "2330", "上市", {"name": "台積電", "industry": "半導體"}
    )
    assert result["fields"]["totalRevenue"] == 100_000
    assert result["fields"]["totalAssets"] == 200_000
    assert result["fields"]["bookValue"] == 12.3
    assert result["field_values"]["totalAssets"]["unit"] == "TWD"
    assert result["official_cumulative_eps"]["value"] == 2.5
    assert result["official_cumulative_eps"]["unit"] == "TWD_per_share"


def test_official_q2_cumulative_eps_does_not_replace_single_quarter_yahoo(monkeypatch):
    yahoo = [
        {
            "year": 2026,
            "quarter": 2,
            "eps": 3.0,
            "label": "Q2 2026",
            "source": "Yahoo Finance quarterly_income_stmt",
            "status": "fallback",
            "data_value": {"value": 3.0, "status": "fallback"},
        }
    ]
    monkeypatch.setattr(stock_data, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stock_data, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        stock_data, "_fetch_eps_yfinance", lambda *_args, **_kwargs: list(yahoo)
    )
    monkeypatch.setattr(stock_data, "_plot_eps_chart", lambda *_args, **_kwargs: None)
    cumulative = {
        "value": 5.5,
        "source": "TWSE OpenAPI",
        "observed_at": "2026-Q2",
        "fetched_at": "2026-08-14T00:00:00+00:00",
        "unit": "TWD_per_share",
        "currency": "TWD",
        "status": "official",
        "note": "",
    }
    result, _ = stock_data.get_eps_data(
        "2330",
        official_financials={
            "year": 2026,
            "quarter": 2,
            "official_cumulative_eps": cumulative,
        },
    )
    assert result == yahoo


def test_endpoint_fetches_once_daily_and_preserves_last_good_on_schema_change(
    monkeypatch,
):
    test_dir = ROOT / "output" / f".official-test-{uuid.uuid4().hex}"
    calls = []
    good = [{"公司代號": "2330", "資料年月": "11506"}]
    responses = [_Response(good), _Response({"unexpected": True})]
    monkeypatch.setattr(official, "_SOURCE_DIR", str(test_dir))
    monkeypatch.setattr(
        official.requests,
        "get",
        lambda *_args, **_kwargs: calls.append(1) or responses.pop(0),
    )
    requirements = (("公司代號",), ("資料年月",))
    try:
        first = official._load_dataset("https://official.example/revenue", requirements)
        second = official._load_dataset(
            "https://official.example/revenue", requirements
        )
        assert first.status == second.status == "official"
        assert len(calls) == 1

        state = official._read_state("https://official.example/revenue")
        state["last_attempt_at"] = official._iso(official._now() - timedelta(days=2))
        official._write_state("https://official.example/revenue", state)
        stale = official._load_dataset("https://official.example/revenue", requirements)
        assert stale.rows == good
        assert stale.status == "stale"
        assert "格式異常" in stale.note
        assert len(calls) == 2
    finally:
        if test_dir.is_dir():
            shutil.rmtree(test_dir)


def test_schema_change_without_last_good_is_explicit(monkeypatch):
    test_dir = ROOT / "output" / f".official-test-{uuid.uuid4().hex}"
    monkeypatch.setattr(official, "_SOURCE_DIR", str(test_dir))
    monkeypatch.setattr(
        official.requests,
        "get",
        lambda *_args, **_kwargs: _Response({"unexpected": True}),
    )
    try:
        with pytest.raises(official.OfficialSchemaError, match="格式異常"):
            official._load_dataset(
                "https://official.example/bad",
                (("公司代號",),),
            )
    finally:
        if test_dir.is_dir():
            shutil.rmtree(test_dir)
