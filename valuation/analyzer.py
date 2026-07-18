import numpy as np
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════
# 輔助函數
# ═══════════════════════════════════════════════════

def _calc_ttm_eps(eps_data: List[Dict[str, Any]]) -> Tuple[Dict[Tuple[int, int], float], List[Dict[str, Any]]]:
    eps_sorted = sorted(eps_data, key=lambda x: (x["year"], x["quarter"]))
    ttm_map: Dict[Tuple[int, int], float] = {}
    for i in range(len(eps_sorted)):
        if i >= 3:
            ttm = sum(eps_sorted[j]["eps"] for j in range(i - 3, i + 1))
            q = eps_sorted[i]
            ttm_map[(q["year"], q["quarter"])] = round(ttm, 4)
    return ttm_map, eps_sorted


def _quarter_for_date(dt: datetime) -> Tuple[int, int]:
    return (dt.year, (dt.month - 1) // 3 + 1)


def _get_ttm_for_date(dt: datetime, ttm_map: Dict[Tuple[int, int], float], eps_sorted: List[Dict[str, Any]]) -> Optional[float]:
    y, q = _quarter_for_date(dt)
    candidates = [(ky, kv) for ky, kv in ttm_map.items()
                  if ky[0] < y or (ky[0] == y and ky[1] <= q)]
    if candidates:
        candidates.sort(key=lambda x: (x[0][0], x[0][1]))
        return candidates[-1][1]
    if eps_sorted:
        window = eps_sorted[-4:]
        if len(window) == 4:
            return round(sum(e["eps"] for e in window), 4)
    return None


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _safe_get(info: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全取值，若 key 不在或值為 None 則回傳 default。"""
    val = info.get(key)
    return val if val is not None else default


# ═══════════════════════════════════════════════════
# 主分析類別
# ═══════════════════════════════════════════════════

class ValuationAnalyzer:
    """台股估值分析引擎 — 整合傳統估值 + 多因子評分 + 風險預警。

    提供七大分析模組：
      1. 合理價區間 (PE 歷史百分位 + 成長調整)
      2. 安全邊際 (波動率折扣)
      3. PEG 與 EPS 成長
      4. 營收成長評估
      5. 健康度評分 (7 維度)
      6. 多因子品質評分 (Piotroski / Altman / Graham)
      7. 風險預警 (12+ 信號)
    """

    BS_MAP = {
        "totalAssets": "Total Assets",
        "currentAssets": "Current Assets",
        "currentLiabilities": "Current Liabilities",
        "retainedEarnings": "Retained Earnings",
        "totalLiabilities": "Total Liabilities Net Minority Interest",
        "stockholdersEquity": "Stockholders Equity",
        "totalDebt": "Total Debt",
        "sharesOutstanding": "Ordinary Shares Number",
        "workingCapital": "Working Capital",
        "netReceivables": "Accounts Receivable",
        "inventory": "Inventory",
        "currentDebt": "Current Debt",
    }
    FIN_MAP = {
        "totalRevenue": "Total Revenue",
        "operatingIncome": "Operating Income",
        "grossProfit": "Gross Profit",
        "netIncomeToCommon": "Net Income Common Stockholders",
        "ebit": "EBIT",
    }

    def __init__(self, stock_id: str, eps_data: List[Dict[str, Any]], price_data: Dict[str, Any],
                 revenue_data: List[Dict[str, Any]], stock_info: Dict[str, Any], price_info: Dict[str, Any],
                 balance_sheet: Optional["pd.DataFrame"] = None,
                 financials: Optional["pd.DataFrame"] = None):
        self.stock_id = stock_id
        self.eps_data = eps_data or []
        self.price_data = price_data or {}
        self.revenue_data = revenue_data or []
        self.stock_info = stock_info or {}
        self.price_info = price_info or {}
        self.is_etf = stock_info.get("is_etf", False) if isinstance(stock_info, dict) else False
        self._pe_percentiles: Dict[str, float] = {}
        self._populate_from_financials(balance_sheet, financials)
        self._compute()

    def _populate_from_financials(self, bs: Optional["pd.DataFrame"],
                                  fin: Optional["pd.DataFrame"]) -> None:
        """用 yfinance 財報填補 price_info 缺失的欄位。

        yfinance 的 info dict 對台股不提供大部分資產負債表欄位，
        但 balance_sheet / financials DataFrame 有完整資料。
        """
        if bs is not None and not bs.empty:
            col = bs.columns[0]
            for key, bs_key in self.BS_MAP.items():
                if key not in self.price_info or self.price_info[key] is None:
                    if bs_key in bs.index:
                        val = bs.loc[bs_key, col]
                        if pd.notna(val):
                            self.price_info[key] = float(val)

        if fin is not None and not fin.empty:
            col = fin.columns[0]
            for key, fin_key in self.FIN_MAP.items():
                if key not in self.price_info or self.price_info[key] is None:
                    if fin_key in fin.index:
                        val = fin.loc[fin_key, col]
                        if pd.notna(val):
                            self.price_info[key] = float(val)

    # ───────────────────────────
    # 內部初始化
    # ───────────────────────────

    def _compute(self) -> None:
        self.ttm_map, self.eps_sorted = _calc_ttm_eps(self.eps_data)

        df_1y = None
        if "1y" in self.price_data:
            df_1y = self.price_data["1y"].get("df")
        elif "6m" in self.price_data:
            df_1y = self.price_data["6m"].get("df")

        self._daily_prices = []
        self._daily_pe = []
        if df_1y is not None and not df_1y.empty:
            for idx, row in df_1y.iterrows():
                dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                price = float(row.get("close", row.get("Close", 0)))
                if price <= 0:
                    continue
                self._daily_prices.append(price)
                ttm = _get_ttm_for_date(dt, self.ttm_map, self.eps_sorted)
                if ttm and ttm > 0:
                    pe = price / ttm
                    self._daily_pe.append(pe)

        self._pe_arr = np.array(self._daily_pe) if self._daily_pe else np.array([])
        self._price_arr = np.array(self._daily_prices) if self._daily_prices else np.array([])

        if len(self._pe_arr) >= 5:
            self._pe_percentiles = {
                "p5": float(np.percentile(self._pe_arr, 5)),
                "p10": float(np.percentile(self._pe_arr, 10)),
                "p25": float(np.percentile(self._pe_arr, 25)),
                "p50": float(np.percentile(self._pe_arr, 50)),
                "p75": float(np.percentile(self._pe_arr, 75)),
                "p90": float(np.percentile(self._pe_arr, 90)),
                "p95": float(np.percentile(self._pe_arr, 95)),
                "mean": float(np.mean(self._pe_arr)),
                "std": float(np.std(self._pe_arr)),
            }
        current_price = self.price_info.get("currentPrice") or 0
        if not current_price and len(self._price_arr) > 0:
            current_price = float(self._price_arr[-1])

        self.current_price = current_price
        self._eps_growth_rate = self._calc_eps_growth_rate()

    # ═══════════════════════════════════════════
    # 模組 1：合理價區間（PE 歷史百分位法）
    # ═══════════════════════════════════════════

    def get_fair_price_range(self) -> Optional[Dict[str, Any]]:
        """以歷史 PE 百分位數 × TTM EPS 計算合理價區間，並以 EPS 成長率調整。

        成長調整因子截斷在 -20% ~ +50%，分別以 50%/80%/100% 權重套用。
        """
        ttm = _safe_get(self.price_info, "trailingEps")
        if not ttm and self.eps_sorted:
            last4 = self.eps_sorted[-4:]
            if len(last4) == 4:
                ttm = round(sum(e["eps"] for e in last4), 2)
        if not ttm or ttm <= 0:
            return None

        p = self._pe_percentiles
        if not p:
            return {
                "ttm_eps": ttm,
                "current_price": self.current_price,
                "current_pe": round(self.current_price / ttm, 2) if self.current_price and ttm else None,
                "cheap": None,
                "fair": None,
                "expensive": None,
                "note": "歷史 PE 數據不足，無法計算合理價區間",
            }

        cheap = round(ttm * p["p25"], 2)
        fair = round(ttm * p["p50"], 2)
        expensive = round(ttm * p["p75"], 2)

        pe_p25 = round(p["p25"], 2)
        pe_p50 = round(p["p50"], 2)
        pe_p75 = round(p["p75"], 2)
        eps_growth = self._eps_growth_rate
        if eps_growth is not None:
            adj = max(-0.2, min(0.5, eps_growth))
            cheap = round(ttm * p["p25"] * (1 + adj * 0.5), 2)
            fair = round(ttm * p["p50"] * (1 + adj * 0.8), 2)
            expensive = round(ttm * p["p75"] * (1 + adj * 1.0), 2)
            pe_p25 = round(p["p25"] * (1 + adj * 0.5), 2)
            pe_p50 = round(p["p50"] * (1 + adj * 0.8), 2)
            pe_p75 = round(p["p75"] * (1 + adj * 1.0), 2)

        return {
            "ttm_eps": ttm,
            "current_price": self.current_price,
            "current_pe": round(self.current_price / ttm, 2) if self.current_price and ttm else None,
            "pe_p25": pe_p25,
            "pe_p50": pe_p50,
            "pe_p75": pe_p75,
            "pe_mean": round(p["mean"], 2),
            "pe_std": round(p["std"], 2),
            "cheap": cheap,
            "fair": fair,
            "expensive": expensive,
            "margin_safety_8": round(fair * 0.8, 2),
            "margin_safety_7": round(fair * 0.7, 2),
            "eps_growth_rate": round(eps_growth, 3) if eps_growth is not None else None,
        }

    # ═══════════════════════════════════════════
    # 模組 2：安全邊際（波動率折扣）
    # ═══════════════════════════════════════════

    def get_margin_of_safety(self, fair_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if fair_price is None:
            r = self.get_fair_price_range()
            if r and r.get("fair"):
                fair_price = r["fair"]
            else:
                return None
        if not self.current_price or self.current_price <= 0:
            return None
        discount = self._suggest_discount()
        safe_buy = round(fair_price * discount, 2)
        mos_pct = round((fair_price - self.current_price) / fair_price * 100, 1) if fair_price else None
        return {
            "fair_price": fair_price,
            "current_price": self.current_price,
            "suggested_discount": discount,
            "safe_buy_price": safe_buy,
            "margin_of_safety_pct": mos_pct,
            "has_safety": self.current_price <= safe_buy,
        }

    def _suggest_discount(self) -> float:
        vol = self._estimate_volatility()
        if vol > 0.4:
            return 0.65
        elif vol > 0.3:
            return 0.70
        elif vol > 0.2:
            return 0.75
        else:
            return 0.80

    def _estimate_volatility(self) -> float:
        prices = self._price_arr
        if len(prices) < 10:
            return 0.25
        log_rets = np.diff(np.log(prices[prices > 0]))
        if len(log_rets) < 5:
            return 0.25
        return float(np.std(log_rets) * np.sqrt(252))

    # ═══════════════════════════════════════════
    # 模組 3：PEG 與 EPS 成長
    # ═══════════════════════════════════════════

    def get_peg(self) -> Dict[str, Any]:
        ttm_eps = self.price_info.get("trailingEps")
        current_pe = self.price_info.get("trailingPE")
        if not current_pe and self.current_price and ttm_eps and ttm_eps > 0:
            current_pe = self.current_price / ttm_eps

        eps_growth = self._calc_eps_growth_rate()
        if not current_pe or current_pe <= 0:
            return {"peg": None, "pe": None, "eps_growth_rate": eps_growth,
                     "verdict": "本益比數據不足，無法計算 PEG"}
        if eps_growth is None:
            return {"peg": None, "pe": round(current_pe, 2), "eps_growth_rate": None,
                     "verdict": "EPS 歷史資料不足，無法計算成長率"}
        if eps_growth <= 0:
            return {"peg": None, "pe": round(current_pe, 2),
                     "eps_growth_rate": round(eps_growth, 3),
                     "verdict": "EPS 成長率為負或零，PEG 不具參考意義"}
        peg = round(current_pe / (eps_growth * 100), 2)
        if peg < 1:
            verdict = "偏低（可能被低估）"
        elif peg <= 2:
            verdict = "合理"
        else:
            verdict = "偏高（注意估值風險）"
        return {"peg": peg, "pe": round(current_pe, 2),
                "eps_growth_rate": round(eps_growth, 2), "verdict": verdict}

    def _calc_eps_growth_rate(self) -> Optional[float]:
        if len(self.eps_sorted) < 4:
            return None
        total_eps_last4 = sum(e["eps"] for e in self.eps_sorted[-4:])
        if len(self.eps_sorted) >= 8:
            total_eps_prev4 = sum(e["eps"] for e in self.eps_sorted[-8:-4])
            if total_eps_prev4 > 0:
                return (total_eps_last4 / total_eps_prev4) - 1
        if len(self.eps_sorted) >= 4:
            older4 = self.eps_sorted[-8:-4] if len(self.eps_sorted) >= 8 else self.eps_sorted[:4]
            total_older = sum(e["eps"] for e in older4)
            if total_older > 0:
                return (total_eps_last4 / total_older) - 1
        return None

    # ═══════════════════════════════════════════
    # 模組 4：營收成長評估
    # ═══════════════════════════════════════════

    def assess_revenue_growth(self) -> Optional[Dict[str, Any]]:
        if not self.revenue_data or len(self.revenue_data) < 3:
            return None

        yoy_vals = [r.get("yoy") for r in self.revenue_data if r.get("yoy") is not None]
        if not yoy_vals:
            return None
        yoy_arr = np.array(yoy_vals)
        yoy_sma3 = self._sma(yoy_arr, 3)
        yoy_sma6 = self._sma(yoy_arr, min(6, len(yoy_arr)))

        recent_yoy = yoy_arr[-3:] if len(yoy_arr) >= 3 else yoy_arr
        avg_yoy = float(np.mean(yoy_arr))
        avg_recent_yoy = float(np.mean(recent_yoy))
        consecutive_positive = self._count_consecutive_positive(yoy_arr)
        consecutive_negative = self._count_consecutive_negative(yoy_arr)

        slope = None
        if len(yoy_arr) >= 6:
            x = np.arange(len(yoy_arr))
            slope = float(np.polyfit(x, yoy_arr, 1)[0])

        accelerating = False
        decelerating = False
        if len(yoy_sma3) >= 2:
            if yoy_sma3[-1] > yoy_sma3[-2] * 1.05:
                accelerating = True
            elif yoy_sma3[-1] < yoy_sma3[-2] * 0.95:
                decelerating = True

        return {
            "avg_yoy_pct": round(avg_yoy, 1),
            "avg_recent_yoy_pct": round(avg_recent_yoy, 1),
            "sma3": [round(v, 1) for v in yoy_sma3],
            "sma6": [round(v, 1) for v in yoy_sma6] if yoy_sma6 else [],
            "consecutive_positive_months": consecutive_positive,
            "consecutive_negative_months": consecutive_negative,
            "trend_slope": round(slope, 3) if slope is not None else None,
            "accelerating": accelerating,
            "decelerating": decelerating,
            "stable": not accelerating and not decelerating,
        }

    def _sma(self, arr, window):
        if len(arr) < window:
            return list(arr)
        return [float(np.mean(arr[i - window:i])) for i in range(window, len(arr) + 1)]

    def _count_consecutive_positive(self, arr):
        count = 0
        for v in reversed(arr):
            if v > 0:
                count += 1
            else:
                break
        return count

    def _count_consecutive_negative(self, arr):
        count = 0
        for v in reversed(arr):
            if v < 0:
                count += 1
            else:
                break
        return count

    # ═════════════════════════════════════════════════════════
    # 模組 5：健康度評分（7 維度，0–100）
    # ═════════════════════════════════════════════════════════
    #
    # 原有 5 維度 + 新增「品質力」(Quality) + 「現金流」(Cash Flow)
    #
    #  維度         權重   核心指標
    # ──────────────────────────────────────
    #  成長性        22%   營收 YoY、EPS 成長、盈餘成長
    #  估值          20%   PE vs 中位數、股價位階、PEG
    #  獲利能力      18%   ROE、利潤率、ROA
    #  品質力        15%   Piotroski F-Score 轉換、盈餘品質
    #  動能          12%   3m/6m 價格動能
    #  穩定性        8%    波動率、負債比
    #  現金流        5%    FCF 收益率、營運現金流 vs 淨利
    # ═════════════════════════════════════════════════════════

    def calculate_health_score(self) -> Dict[str, Any]:
        """7 維度健康度評分（0–100）。"""
        fair = self.get_fair_price_range()
        peg = self.get_peg()
        rev = self.assess_revenue_growth()

        growth_score = self._score_growth(rev, peg)
        valuation_score = self._score_valuation(fair)
        profitability_score = self._score_profitability()
        quality_score = self._score_quality()
        momentum_score = self._score_momentum()
        stability_score = self._score_stability()
        cashflow_score = self._score_cashflow()

        total = (
            growth_score * 0.22
            + valuation_score * 0.20
            + profitability_score * 0.18
            + quality_score * 0.15
            + momentum_score * 0.12
            + stability_score * 0.08
            + cashflow_score * 0.05
        )
        total = round(total, 1)

        if total >= 70:
            level = "良好"
        elif total >= 45:
            level = "普通"
        else:
            level = "需謹慎"

        return {
            "total_score": total,
            "level": level,
            "components": {
                "growth": {"score": round(growth_score, 1), "weight": "22%"},
                "valuation": {"score": round(valuation_score, 1), "weight": "20%"},
                "profitability": {"score": round(profitability_score, 1), "weight": "18%"},
                "quality": {"score": round(quality_score, 1), "weight": "15%"},
                "momentum": {"score": round(momentum_score, 1), "weight": "12%"},
                "stability": {"score": round(stability_score, 1), "weight": "8%"},
                "cashflow": {"score": round(cashflow_score, 1), "weight": "5%"},
            },
        }

    def _score_growth(self, rev, peg) -> float:
        """成長性評分：營收 YoY + EPS 成長 + 營收動能 + PEG 輔助。"""
        score = 50.0

        if rev:
            yoy = rev.get("avg_recent_yoy_pct", 0)
            score += _clamp(yoy * 1.2, -30, 35)

            if rev.get("accelerating"):
                score += 12
            elif rev.get("decelerating"):
                score -= 12

            pos = rev.get("consecutive_positive_months", 0)
            neg = rev.get("consecutive_negative_months", 0)
            if pos >= 6:
                score += 10
            elif pos >= 3:
                score += 5
            if neg >= 2:
                score -= 15

        # 盈餘成長（earningsGrowth 來自 yfinance）
        eg = _safe_get(self.price_info, "earningsGrowth")
        if eg is not None:
            score += _clamp(eg * 100 * 0.3, -10, 15)

        if peg:
            p = peg.get("peg")
            if p is not None:
                if p < 1:
                    score += 8
                elif p > 3:
                    score -= 10

        return _clamp(score, 0, 100)

    def _score_valuation(self, fair) -> float:
        """估值評分：PE 區間 + 股價位階。"""
        score = 50.0

        if fair and fair.get("current_pe") and fair.get("pe_p50"):
            cur_pe = fair["current_pe"]
            med_pe = fair["pe_p50"]
            ratio = cur_pe / med_pe if med_pe else 1.0

            if ratio <= 1:
                score += 45 * (1 - ratio)
            else:
                score -= 25 * (ratio - 1)
                if ratio > 2:
                    score -= 5 * (ratio - 2)

        # PB 輔助估值
        pb = _safe_get(self.price_info, "priceToBook")
        if pb is not None and pb > 0:
            if pb < 1.5:
                score += 8
            elif pb > 5:
                score -= 8

        if fair and fair.get("current_price") and fair.get("cheap") and fair.get("expensive"):
            cp = fair["current_price"]
            cheap = fair["cheap"]
            expensive = fair["expensive"]
            if cp <= cheap:
                score += 10
            elif cp >= expensive:
                score -= 10

        return _clamp(score, 10, 100)

    def _score_profitability(self) -> float:
        """獲利能力評分：ROE、利潤率、ROA。"""
        score = 50.0

        roe = _safe_get(self.price_info, "returnOnEquity")
        if roe:
            score += _clamp(roe * 100 * 1.5, 0, 30)

        pm = _safe_get(self.price_info, "profitMargins")
        if pm:
            score += _clamp(pm * 100 * 0.8, 0, 15)

        roa = _safe_get(self.price_info, "returnOnAssets")
        if roa:
            score += _clamp(roa * 100 * 1.0, 0, 10)

        eps = _safe_get(self.price_info, "trailingEps")
        if eps and eps > 0:
            score += _clamp(eps * 1.5, 0, 10)

        return _clamp(score, 0, 100)

    def _score_quality(self) -> float:
        """品質力評分：Piotroski F-Score 轉 0–100 + 盈餘品質。"""
        f_score = self._calc_piotroski_f_score()
        score = 30.0 + f_score * 7.0  # F=0→30, F=5→65, F=9→93

        # 盈餘品質：營運現金流 / 淨利（越高越好）
        ocf = _safe_get(self.price_info, "operatingCashflow")
        ni = _safe_get(self.price_info, "netIncome")
        if ocf is not None and ni is not None and ni > 0:
            ratio = abs(ocf) / abs(ni)
            if ratio > 1.5:
                score += 8
            elif ratio > 1.0:
                score += 4
            elif ratio < 0.5:
                score -= 8

        return _clamp(score, 0, 100)

    def _score_momentum(self) -> float:
        score = 50.0
        df_3m = self.price_data.get("3m", {}).get("df")
        df_6m = self.price_data.get("6m", {}).get("df")
        _c = lambda s: s["close"] if "close" in s else s["Close"]
        if df_3m is not None and not df_3m.empty:
            p0 = float(_c(df_3m).iloc[0])
            p1 = float(_c(df_3m).iloc[-1])
            ret_3m = (p1 - p0) / p0 * 100 if p0 > 0 else 0
            score += _clamp(ret_3m * 1.0, -20, 20)
        if df_6m is not None and not df_6m.empty:
            p0 = float(_c(df_6m).iloc[0])
            p1 = float(_c(df_6m).iloc[-1])
            ret_6m = (p1 - p0) / p0 * 100 if p0 > 0 else 0
            score += _clamp(ret_6m * 0.6, -15, 15)
        return _clamp(score, 0, 100)

    def _score_stability(self) -> float:
        """穩定性評分：波動率 + 負債比。"""
        score = 70.0
        vol = self._estimate_volatility()
        if vol > 0.5:
            score -= 25
        elif vol > 0.35:
            score -= 12
        elif vol > 0.25:
            score -= 5
        elif vol < 0.15:
            score += 10
        else:
            score += 3

        dte = _safe_get(self.price_info, "debtToEquity")
        if dte is not None:
            if dte > 100:
                score -= 18
            elif dte > 50:
                score -= 8
            elif dte < 10:
                score += 10

        return _clamp(score, 0, 100)

    def _score_cashflow(self) -> float:
        """現金流評分：FCF 收益率、營運現金流品質。"""
        score = 50.0

        fcf = _safe_get(self.price_info, "freeCashflow")
        if fcf is not None:
            # FCF > 0 是基本門檻
            if fcf > 0:
                score += 20
                # FCF 收益率（FCF / 市值）
                mcap = _safe_get(self.price_info, "marketCap")
                if mcap and mcap > 0:
                    fcf_yield = fcf / mcap
                    score += _clamp(fcf_yield * 1000, 0, 15)
            else:
                score -= 15

        ocf = _safe_get(self.price_info, "operatingCashflow")
        if ocf is not None and ocf > 0:
            score += 5

        # 現金 vs 負債
        cash = _safe_get(self.price_info, "totalCash")
        debt = _safe_get(self.price_info, "totalDebt")
        if cash is not None and debt is not None and debt > 0:
            ratio = cash / debt
            if ratio > 1.5:
                score += 10
            elif ratio > 0.5:
                score += 5
            elif ratio < 0.2:
                score -= 10

        return _clamp(score, 0, 100)

    # ═════════════════════════════════════════════════════════
    # 模組 5b：Piotroski F-Score（9 因子評分）
    # ═════════════════════════════════════════════════════════
    #
    # Piotroski F-Score (2002) — 9 個二元條件，用於區分價值股優劣。
    #
    #  獲利能力 (Profitability):
    #    1. ROA > 0
    #    2. 營運現金流 > 0
    #    3. ROA 變化 > 0 (較去年改善)
    #    4. 營運現金流 > 淨利 (盈餘品質)
    #
    #  財務結構 (Leverage / Liquidity):
    #    5. 長期負債比變化 < 0 (槓桿降低)
    #    6. 流動比率變化 > 0
    #    7. 股票發行數 = 0 (無增發)
    #
    #  營運效率 (Operating Efficiency):
    #    8. 毛利率變化 > 0
    #    9. 資產周轉率變化 > 0
    #
    #  由於 yfinance 資料限制，部分條件以近似替代：
    #    - 流動比率 → 現金/負債變化
    #    - 股票發行數 → sharesOutstanding 變化
    #    - 資產周轉率 → revenue / totalAssets 變化
    # ─────────────────────────────────────────────────────────

    def _calc_piotroski_f_score(self) -> int:
        """計算 Piotroski F-Score (0–9)。因資料限制，部分條件以替代指標近似。"""
        score = 0
        pi = self.price_info

        # ── 獲利能力 (4 項) ──
        # 1. ROA > 0
        roa = _safe_get(pi, "returnOnAssets")
        if roa is not None and roa > 0:
            score += 1

        # 2. 營運現金流 > 0
        ocf = _safe_get(pi, "operatingCashflow")
        if ocf is not None and ocf > 0:
            score += 1

        # 3. ROA 變化 > 0 (較去年改善)
        roa_change = _safe_get(pi, "returnOnAssets", 0) - _safe_get(pi, "lastYearReturnOnAssets", 0)
        if roa_change > 0:
            score += 1

        # 4. 營運現金流 > 淨利 (盈餘品質)
        ni = _safe_get(pi, "netIncomeToCommon")
        if ocf is not None and ni is not None and ni > 0:
            if ocf > ni:
                score += 1

        # ── 財務結構 (3 項) ──
        # 5. 長期負債比變化 < 0 (槓桿降低)
        dte = _safe_get(pi, "debtToEquity", 0)
        dte_prev = _safe_get(pi, "lastYearDebtToEquity", dte)
        if dte < dte_prev:
            score += 1

        # 6. 現金/負債比改善 (流動性替代)
        cash = _safe_get(pi, "totalCash", 0)
        debt = _safe_get(pi, "totalDebt", 1) or 1
        cash_ratio = cash / debt
        # 無歷史資料時假設有改善
        if cash > 0:
            score += 1

        # 7. 無增發 (shares 無增加)
        shares = _safe_get(pi, "sharesOutstanding")
        shares_prev = _safe_get(pi, "lastYearSharesOutstanding", shares)
        if shares is not None and shares_prev is not None:
            if shares <= shares_prev * 1.02:  # 容許 2% 誤差
                score += 1
        else:
            # 無資料時中性處理 (不扣分也不加分)
            pass

        # ── 營運效率 (2 項) ──
        # 8. 毛利率改善
        gm = _safe_get(pi, "grossMargins", 0)
        gm_prev = _safe_get(pi, "lastYearGrossMargins", gm)
        if gm > gm_prev:
            score += 1

        # 9. 資產周轉率改善 (營收/總資產)
        rev = _safe_get(pi, "totalRevenue")
        assets = _safe_get(pi, "totalAssets")
        if rev is not None and assets is not None and assets > 0:
            turnover = rev / assets
            turnover_prev = _safe_get(pi, "lastYearTotalRevenue", 0) / _safe_get(pi, "lastYearTotalAssets", 1)
            if turnover > turnover_prev or turnover_prev <= 0:
                score += 1

        return min(score, 9)

    # ═════════════════════════════════════════════════════════
    # 模組 5c：Altman Z-Score（破產風險預測）
    # ═════════════════════════════════════════════════════════
    #
    # Altman Z-Score (1968) 公式：
    #   Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    #   A = 營運資金 / 總資產
    #   B = 保留盈餘 / 總資產
    #   C = 息前稅前淨利 / 總資產
    #   D = 市值 / 總負債
    #   E = 營收 / 總資產
    #
    #   Z > 2.99  → 安全
    #   1.81 < Z < 2.99 → 灰色地帶
    #   Z < 1.81  → 高度破產風險
    #
    #  Taiwan 市場可考慮使用 Emerging Market Z-Score 調整：
    #   Z > 2.5 → 安全, Z < 1.1 → 危險
    # ─────────────────────────────────────────────────────────

    @property
    def _is_financial(self) -> bool:
        # price_info（yfinance info dict）通常有較完整的 sector/industry
        sector = (_safe_get(self.stock_info, "sector", "")
                  or _safe_get(self.price_info, "sector", ""))
        industry = (_safe_get(self.stock_info, "industry", "")
                    or _safe_get(self.price_info, "industry", ""))
        fin_keywords = ["financial", "bank", "insurance", "asset management", "investment"]
        for kw in fin_keywords:
            if kw in sector.lower() or kw in industry.lower():
                return True
        return False

    def _calc_altman_z_score(self) -> Optional[float]:
        if self._is_financial:
            return None
        pi = self.price_info
        assets = _safe_get(pi, "totalAssets")
        if not assets or assets <= 0:
            return None

        # A: 營運資金 / 總資產
        current_assets = _safe_get(pi, "currentAssets", 0)
        current_liab = _safe_get(pi, "currentLiabilities", 0)
        working_capital = current_assets - current_liab
        A = working_capital / assets

        # B: 保留盈餘 / 總資產 (無直接資料，用淨利潤替代部分)
        retained = _safe_get(pi, "retainedEarnings", 0)
        B = retained / assets

        # C: EBIT / 總資產 (用 operatingIncome 近似)
        ebit = _safe_get(pi, "operatingIncome", 0)
        C = ebit / assets

        # D: 市值 / 總負債 (使用 totalLiabilities 而非 totalDebt，更符合 Altman 原始定義)
        mcap = _safe_get(pi, "marketCap")
        total_liab = _safe_get(pi, "totalLiabilities")
        if total_liab and total_liab > 0:
            D = (mcap / total_liab) if mcap else 0
        else:
            debt = _safe_get(pi, "totalDebt", 1) or 1
            D = (mcap / debt) if mcap else 0

        # E: 營收 / 總資產
        rev = _safe_get(pi, "totalRevenue", 0)
        E = rev / assets

        Z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E
        return round(Z, 3)

    # ═════════════════════════════════════════════════════════
    # 模組 5d：Graham Number（葛拉漢數字）
    # ═════════════════════════════════════════════════════════
    #
    # Graham Number = √(22.5 × EPS × BVPS)
    #   22.5 = 15(PE上限) × 1.5(PB上限)
    #   代表價值投資者可接受的最高價格
    # ─────────────────────────────────────────────────────────

    def _calc_graham_number(self) -> Optional[float]:
        """計算 Graham Number（價值投資合理價上限）。"""
        eps = _safe_get(self.price_info, "trailingEps")
        bvps = _safe_get(self.price_info, "bookValue")
        if eps and bvps and eps > 0 and bvps > 0:
            return round((22.5 * eps * bvps) ** 0.5, 2)
        return None

    # ═════════════════════════════════════════════════════════
    # 模組 5e：綜合整體評級（A/B/C/D）
    # ═════════════════════════════════════════════════════════
    #
    # 此評級移到後端計算，消除前端與後端的雙重計分問題。
    # 公式：加權 [健康度 60% + 品質 25% + 安全邊際 15%]
    # ─────────────────────────────────────────────────────────

    def _quality_z_score(self, z: Optional[float]) -> float:
        """將 Altman Z 轉為 0–100 分數，並在 Z > 10 時飽和。"""
        if z is None:
            return 50.0
        z_capped = min(z, 10.0)
        return _clamp(z_capped * 10.0, 0, 100)

    def calculate_overall_rating(self) -> Dict[str, Any]:
        health = self.calculate_health_score()
        f_score = self._calc_piotroski_f_score()
        z_score = self._calc_altman_z_score()
        graham = self._calc_graham_number()
        mos = self.get_margin_of_safety()

        quality_raw = 30.0 + f_score * 7.0
        if z_score is not None:
            quality_z = self._quality_z_score(z_score) * 0.15
            quality_raw = _clamp(quality_raw + quality_z, 0, 100)

        safety_score = 50.0
        if mos:
            mos_pct = mos.get("margin_of_safety_pct")
            if mos_pct is not None:
                if mos_pct > 30:
                    safety_score = 95
                elif mos_pct > 15:
                    safety_score = 80
                elif mos_pct > 0:
                    safety_score = 65
                elif mos_pct > -20:
                    safety_score = max(30, 50 + mos_pct * 1.0)
                else:
                    safety_score = max(10, 50 + mos_pct * 0.5)

        graham_score = 50.0
        if graham and self.current_price > 0:
            discount = (graham - self.current_price) / graham * 100
            if discount > 30:
                graham_score = 90
            elif discount > 10:
                graham_score = 75
            elif discount > -10:
                graham_score = 55
            elif discount > -30:
                graham_score = 35
            else:
                graham_score = max(10, 50 + discount * 0.5)

        total = (
            health["total_score"] * 0.40
            + quality_raw * 0.20
            + safety_score * 0.25
            + graham_score * 0.15
        )

        if total >= 80:
            rating = "A"
            color = "#10b981"
        elif total >= 60:
            rating = "B"
            color = "#6366f1"
        elif total >= 40:
            rating = "C"
            color = "#f59e0b"
        else:
            rating = "D"
            color = "#ef4444"

        return {
            "score": round(total, 1),
            "rating": rating,
            "color": color,
            "components": {
                "health_score": {"score": health["total_score"], "weight": "40%"},
                "quality": {"score": round(quality_raw, 1), "weight": "20%",
                            "piotroski_f_score": f_score},
                "safety": {"score": round(safety_score, 1), "weight": "25%"},
                "graham": {"score": round(graham_score, 1), "weight": "15%",
                           "graham_number": graham},
            },
        }

    # ═══════════════════════════════════════════
    # 模組 6：風險預警（12+ 信號）
    # ═══════════════════════════════════════════

    def get_risk_warnings(self) -> List[Dict[str, Any]]:
        """產生風險預警信號。

        回傳列表，每項含 type / level (red/yellow/green) / msg / horizon (short/mid/long)。
        """
        fair = self.get_fair_price_range()
        rev = self.assess_revenue_growth()
        peg = self.get_peg()
        health = self.calculate_health_score()
        f_score = self._calc_piotroski_f_score()
        z_score = self._calc_altman_z_score()
        graham = self._calc_graham_number()
        warnings = []

        # ── 營收衰退 ──
        if rev:
            if rev.get("consecutive_negative_months", 0) >= 3:
                warnings.append({"type": "營收衰退", "level": "red", "horizon": "mid",
                                 "msg": f"連續 {rev['consecutive_negative_months']} 個月營收年增率為負"})
            elif rev.get("consecutive_negative_months", 0) >= 1:
                warnings.append({"type": "營收衰退", "level": "yellow", "horizon": "mid",
                                 "msg": "近月營收年增率出現負值"})
            if rev.get("decelerating"):
                warnings.append({"type": "成長放緩", "level": "yellow", "horizon": "mid",
                                 "msg": "營收年增率動能減弱"})

        # ── 估值風險 ──
        if fair and fair.get("current_pe") and fair.get("pe_p75"):
            if fair["current_pe"] > fair["pe_p75"] * 1.2:
                warnings.append({"type": "高估值", "level": "red", "horizon": "mid",
                                 "msg": f"本益比 {fair['current_pe']} 顯著高於歷史 75% 分位 {fair['pe_p75']}"})
            elif fair["current_pe"] > fair["pe_p75"]:
                warnings.append({"type": "高估值", "level": "yellow", "horizon": "mid",
                                 "msg": f"本益比 {fair['current_pe']} 高於歷史 75% 分位 {fair['pe_p75']}"})

        if fair and fair.get("current_pe") and fair.get("pe_p25"):
            if fair["current_pe"] < fair["pe_p25"] * 0.8:
                warnings.append({"type": "估值偏低", "level": "green", "horizon": "mid",
                                 "msg": "本益比顯著低於歷史區間，注意是否有基本面疑慮"})

        # ── PEG 過高 ──
        if peg and peg.get("peg") is not None and peg["peg"] > 3:
            warnings.append({"type": "PEG 過高", "level": "yellow", "horizon": "mid",
                             "msg": f"PEG {peg['peg']} > 3，成長無法支撐當前估值"})

        # ── 波動風險 ──
        vol = self._estimate_volatility()
        if vol > 0.5:
            warnings.append({"type": "波動過大", "level": "red", "horizon": "short",
                             "msg": f"年化波動率 {vol*100:.0f}%，短線風險偏高"})
        elif vol > 0.35:
            warnings.append({"type": "波動較大", "level": "yellow", "horizon": "short",
                             "msg": f"年化波動率 {vol*100:.0f}%"})

        # ── EPS 衰退 ──
        eps_growth = self._calc_eps_growth_rate()
        if eps_growth is not None and eps_growth < -0.1:
            warnings.append({"type": "EPS 下滑", "level": "red", "horizon": "mid",
                             "msg": f"近四季 EPS 較前四季衰退 {abs(eps_growth)*100:.0f}%"})

        # ── Piotroski 低分（品質風險）──
        if f_score <= 3:
            warnings.append({"type": "財務品質", "level": "yellow", "horizon": "long",
                             "msg": f"Piotroski F-Score 僅 {f_score}/9，財務基本面偏弱"})
        elif f_score <= 2:
            warnings.append({"type": "財務品質", "level": "red", "horizon": "long",
                             "msg": f"Piotroski F-Score 僅 {f_score}/9，財務體質需警惕"})

        # ── Altman Z-Score（破產風險）──
        if z_score is not None:
            if z_score < 1.1:
                warnings.append({"type": "財務壓力", "level": "red", "horizon": "long",
                                 "msg": f"Altman Z-Score {z_score}，財務結構需警惕"})
            elif z_score < 2.5:
                warnings.append({"type": "財務壓力", "level": "yellow", "horizon": "long",
                                 "msg": f"Altman Z-Score {z_score}，財務結構處於灰色地帶"})
            else:
                warnings.append({"type": "財務穩健", "level": "green", "horizon": "long",
                                 "msg": f"Altman Z-Score {z_score}，財務結構穩健"})

        # ── Graham Number 警示 ──
        if graham is not None and self.current_price > 0:
            if self.current_price > graham * 1.5:
                warnings.append({"type": "葛拉漢警訊", "level": "yellow", "horizon": "mid",
                                 "msg": f"股價 {self.current_price} 顯著高於 Graham Number {graham}，價值投資角度偏貴"})

        # ── 流動性風險 ──
        cash = _safe_get(self.price_info, "totalCash")
        debt = _safe_get(self.price_info, "totalDebt")
        if cash is not None and debt is not None and debt > 0:
            if cash / debt < 0.2:
                warnings.append({"type": "流動性", "level": "yellow", "horizon": "long",
                                 "msg": "現金/負債比率偏低，留意流動性風險"})

        # ── 獲利能力衰退 ──
        roa = _safe_get(self.price_info, "returnOnAssets")
        roa_prev = _safe_get(self.price_info, "lastYearReturnOnAssets")
        if roa is not None and roa_prev is not None:
            if roa < roa_prev * 0.7 and roa_prev > 0:
                warnings.append({"type": "獲利衰退", "level": "yellow", "horizon": "mid",
                                 "msg": "ROA 較去年同期顯著下滑"})

        # ── 健康度總評警示 ──
        if health["total_score"] < 45:
            warnings.append({"type": "綜合健康度", "level": "red", "horizon": "mid",
                             "msg": f"綜合健康度僅 {health['total_score']} 分，整體表現偏弱"})

        return warnings

    # ═══════════════════════════════════════════
    # 模組 7：白話分析文字
    # ═══════════════════════════════════════════

    def generate_analysis_text(self) -> str:
        fair = self.get_fair_price_range()
        score = self.calculate_health_score()
        rating = self.calculate_overall_rating()
        warnings = self.get_risk_warnings()
        peg = self.get_peg()
        rev = self.assess_revenue_growth()
        graham = self._calc_graham_number()
        f_score = self._calc_piotroski_f_score()

        lines = []
        name = self.stock_info.get("name", self.stock_id)

        # 整體評級
        lines.append(f"【{name} 估值分析】")
        lines.append(f"綜合評級：{rating['rating']}（{rating['score']} 分）")
        lines.append(f"健康評分：{score['total_score']} 分（{score['level']}）")

        # 新指標摘要
        lines.append(f"Piotroski F-Score：{f_score}/9")
        if graham:
            if self.current_price < graham:
                lines.append(f"Graham Number：{graham} 元（目前股價低於葛拉漢數字，價值投資角度具安全邊際）")
            else:
                lines.append(f"Graham Number：{graham} 元（目前股價高於葛拉漢數字）")

        # 價格區間
        if fair and fair.get("cheap"):
            cp = fair.get("current_price", 0)
            cheap = fair["cheap"]
            fair_p = fair["fair"]
            exp = fair["expensive"]
            if cp <= cheap:
                zone = "低於便宜價"
            elif cp <= fair_p:
                zone = "介於便宜價與合理價之間"
            elif cp <= exp:
                zone = "介於合理價與昂貴價之間"
            else:
                zone = "高於昂貴價"
            lines.append(f"合理價區間：{cheap:.0f} ~ {fair_p:.0f} ~ {exp:.0f}（便宜/合理/昂貴）")
            lines.append(f"目前股價 {cp:.0f} 元，{zone}。")

        # PE 分析
        if fair and fair.get("current_pe") and fair.get("pe_p50"):
            cur_pe = fair["current_pe"]
            med_pe = fair["pe_p50"]
            if cur_pe < med_pe * 0.9:
                lines.append(f"本益比 {cur_pe} 低於歷史中位數 {med_pe}，估值相對便宜。")
            elif cur_pe > med_pe * 1.1:
                lines.append(f"本益比 {cur_pe} 高於歷史中位數 {med_pe}，估值相對較高。")
            else:
                lines.append(f"本益比 {cur_pe} 與歷史中位數 {med_pe} 相當，估值合理。")

        # PEG
        if peg and peg.get("peg") is not None:
            p = peg["peg"]
            if p < 1:
                lines.append(f"PEG {p} < 1，成長足以支撐本益比。")
            elif p <= 2:
                lines.append(f"PEG {p}，成長與估值大致匹配。")
            else:
                lines.append(f"PEG {p} > 2，注意成長是否可持續支撐估值。")

        # 營收趨勢
        if rev:
            yoy = rev.get("avg_recent_yoy_pct", 0)
            if yoy > 20:
                lines.append(f"近期營收年增率平均 {yoy}%，成長動能強勁。")
            elif yoy > 5:
                lines.append(f"近期營收年增率平均 {yoy}%，穩定成長。")
            elif yoy > -5:
                lines.append(f"近期營收年增率約 {yoy}%，營收大致持平。")
            else:
                lines.append(f"近期營收年增率 {yoy}%，營收衰退需注意。")
            if rev.get("accelerating"):
                lines.append("營收動能正在增強，趨勢正向。")
            elif rev.get("decelerating"):
                lines.append("營收動能放緩，需關注是否為短期現象。")
            if rev.get("consecutive_positive_months", 0) >= 6:
                lines.append(f"連續 {rev['consecutive_positive_months']} 個月營收正成長，表現穩定。")

        # 安全邊際
        mos = self.get_margin_of_safety()
        if mos:
            pct = mos.get("margin_of_safety_pct")
            if pct is not None and pct > 0:
                lines.append(f"當前價格距離合理價尚有 {pct}% 空間。")
            elif pct is not None:
                lines.append(f"當前價格已高於合理價 {abs(pct)}%。")

        # 風險摘要
        red = [w for w in warnings if w["level"] == "red"]
        yellow = [w for w in warnings if w["level"] == "yellow"]
        green = [w for w in warnings if w["level"] == "green"]
        if red:
            lines.append(f"風險提醒：發現 {len(red)} 項紅燈警訊（{', '.join(w['type'] for w in red)}），請審慎評估。")
        if yellow:
            lines.append(f"注意：{len(yellow)} 項黃燈觀察（{', '.join(w['type'] for w in yellow)}）。")

        return "\n".join(lines)

    # ── ETF 評分 ──

    def _calculate_etf_health_score(self) -> Dict[str, Any]:
        pi = self.price_info
        scores = {}

        er = _safe_get(pi, "annualReportExpenseRatio")
        if er is not None:
            if er <= 0.003:
                scores["expense_ratio"] = {"score": 90, "weight": "30%"}
            elif er <= 0.005:
                scores["expense_ratio"] = {"score": 75, "weight": "30%"}
            elif er <= 0.010:
                scores["expense_ratio"] = {"score": 55, "weight": "30%"}
            else:
                scores["expense_ratio"] = {"score": 25, "weight": "30%"}

        nav = _safe_get(pi, "navPrice")
        price = _safe_get(pi, "currentPrice")
        premium = None
        if nav and price and nav > 0:
            premium = abs((price - nav) / nav * 100)
        if premium is not None:
            if premium <= 0.3:
                scores["premium"] = {"score": 90, "weight": "25%"}
            elif premium <= 0.5:
                scores["premium"] = {"score": 80, "weight": "25%"}
            elif premium <= 1.0:
                scores["premium"] = {"score": 60, "weight": "25%"}
            elif premium <= 2.0:
                scores["premium"] = {"score": 40, "weight": "25%"}
            else:
                scores["premium"] = {"score": 20, "weight": "25%"}

        aum = _safe_get(pi, "totalAssets")
        if aum is not None:
            if aum >= 500e9:
                scores["size"] = {"score": 90, "weight": "15%"}
            elif aum >= 100e9:
                scores["size"] = {"score": 80, "weight": "15%"}
            elif aum >= 50e9:
                scores["size"] = {"score": 65, "weight": "15%"}
            elif aum >= 10e9:
                scores["size"] = {"score": 50, "weight": "15%"}
            else:
                scores["size"] = {"score": 30, "weight": "15%"}

        avg_vol = _safe_get(pi, "averageVolume")
        if avg_vol is not None:
            if avg_vol >= 5e6:
                scores["liquidity"] = {"score": 90, "weight": "15%"}
            elif avg_vol >= 1e6:
                scores["liquidity"] = {"score": 75, "weight": "15%"}
            elif avg_vol >= 200e3:
                scores["liquidity"] = {"score": 55, "weight": "15%"}
            else:
                scores["liquidity"] = {"score": 30, "weight": "15%"}

        div_yield = _safe_get(pi, "yield")
        if div_yield is not None:
            dy = div_yield * 100
            if dy >= 5:
                scores["yield"] = {"score": 90, "weight": "15%"}
            elif dy >= 3:
                scores["yield"] = {"score": 75, "weight": "15%"}
            elif dy >= 1.5:
                scores["yield"] = {"score": 55, "weight": "15%"}
            else:
                scores["yield"] = {"score": 30, "weight": "15%"}

        total = 0.0
        total_w = 0.0
        for k, v in scores.items():
            w = float(v["weight"].rstrip("%")) / 100
            total += v["score"] * w
            total_w += w

        avg = round(total / total_w, 1) if total_w > 0 else 50.0

        if avg >= 70:
            level = "良好"
        elif avg >= 45:
            level = "普通"
        else:
            level = "需謹慎"

        return {"total_score": avg, "level": level, "components": scores}

    def _calculate_etf_rating(self) -> Dict[str, Any]:
        """ETF 綜合評級 (A/B/C/D)。"""
        hs = self._calculate_etf_health_score()
        total = hs["total_score"]

        if total >= 80:
            rating = "A"
            color = "#10b981"
        elif total >= 60:
            rating = "B"
            color = "#6366f1"
        elif total >= 40:
            rating = "C"
            color = "#f59e0b"
        else:
            rating = "D"
            color = "#ef4444"

        return {"score": total, "rating": rating, "color": color, "components": hs.get("components")}

    def _calculate_etf_risk_warnings(self) -> List[Dict[str, Any]]:
        """ETF 專屬風險預警。"""
        pi = self.price_info
        warnings = []

        er = _safe_get(pi, "annualReportExpenseRatio")
        if er is not None and er > 0.01:
            warnings.append({"type": "費用率偏高", "level": "yellow", "horizon": "long",
                             "msg": f"費用率 {(er*100):.2f}% > 1%，長期持有成本偏高"})

        nav = _safe_get(pi, "navPrice")
        price = _safe_get(pi, "currentPrice")
        if nav and price and nav > 0:
            premium = (price - nav) / nav * 100
            if premium > 2:
                warnings.append({"type": "溢價過大", "level": "yellow", "horizon": "short",
                                 "msg": f"溢價 {premium:.2f}% > 2%，買進成本偏高"})
            elif premium < -2:
                warnings.append({"type": "折價過大", "level": "green", "horizon": "short",
                                 "msg": f"折價 {abs(premium):.2f}%，可留意買點"})

        aum = _safe_get(pi, "totalAssets")
        if aum is not None and aum < 5e9:
            warnings.append({"type": "規模偏小", "level": "yellow", "horizon": "long",
                             "msg": "基金規模偏小，留意清算風險"})

        avg_vol = _safe_get(pi, "averageVolume")
        if avg_vol is not None and avg_vol < 100e3:
            warnings.append({"type": "流動性低", "level": "yellow", "horizon": "short",
                             "msg": "日均成交量偏低，買賣價差可能較大"})

        return warnings

    def _generate_etf_analysis_text(self) -> str:
        """ETF 白話分析文字。"""
        pi = self.price_info
        name = self.stock_info.get("name", self.stock_id)
        rating = self._calculate_etf_rating()
        parts = [f"【{name} ETF 分析】"]
        parts.append(f"綜合評級：{rating['rating']}（{rating['score']} 分）")

        er = _safe_get(pi, "annualReportExpenseRatio")
        if er is not None:
            parts.append(f"費用率 {(er*100):.2f}% — {'偏低' if er <= 0.005 else '合理' if er <= 0.01 else '偏高'}")

        nav = _safe_get(pi, "navPrice")
        price = _safe_get(pi, "currentPrice")
        if nav and price and nav > 0:
            premium = (price - nav) / nav * 100
            parts.append(f"目前 {'溢價' if premium > 0 else '折價'} {abs(premium):.2f}%")

        aum = _safe_get(pi, "totalAssets")
        if aum is not None:
            aum_str = f"{aum/1e8:.0f} 億" if aum < 1e11 else f"{aum/1e11:.1f} 百億"
            parts.append(f"基金規模 {aum_str}")

        div_yield = _safe_get(pi, "yield")
        if div_yield is not None:
            parts.append(f"殖利率 {(div_yield*100):.2f}%")

        parts.append("ETF 不適用個股 PE 估值，請以折溢價與費用率為主要評估依據。")
        return "。".join(parts)

    # ═══════════════════════════════════════════
    # 彙總輸出
    # ═══════════════════════════════════════════

    def full_analysis(self) -> Dict[str, Any]:
        """完整分析輸出，保持與舊版相容並加入新欄位。"""
        if self.is_etf:
            etf_rating = self._calculate_etf_rating()
            return {
                "is_etf": True,
                "fair_price_range": {"current_price": self.current_price} if self.current_price else None,
                "margin_of_safety": None,
                "peg": None,
                "revenue_growth": self.assess_revenue_growth(),
                "health_score": self._calculate_etf_health_score(),
                "overall_rating": etf_rating,
                "quality_score": None,
                "altman_z_score": None,
                "graham_number": None,
                "piotroski_f_score": None,
                "risk_warnings": self._calculate_etf_risk_warnings(),
                "analysis_text": self._generate_etf_analysis_text(),
            }
        return {
            "fair_price_range": self.get_fair_price_range(),
            "margin_of_safety": self.get_margin_of_safety(),
            "peg": self.get_peg(),
            "revenue_growth": self.assess_revenue_growth(),
            "health_score": self.calculate_health_score(),
            "overall_rating": self.calculate_overall_rating(),
            "quality_score": {
                "piotroski_f_score": self._calc_piotroski_f_score(),
                "altman_z_score": self._calc_altman_z_score(),
                "graham_number": self._calc_graham_number(),
            },
            "risk_warnings": self.get_risk_warnings(),
            "analysis_text": self.generate_analysis_text(),
        }
