import logging
import os
import re
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from config import FONT_PATH, FONT_PATH_BOLD, FONT_NAME, OUTPUT_DIR
from storage.cleanup import enforce_output_policy
from report.font import get_chinese_font
from utils.logger import get_logger

logger = get_logger(__name__)


class _KnownFontSubsetNoiseFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith("MERG NOT subset")


logging.getLogger("fontTools.subset").addFilter(_KnownFontSubsetNoiseFilter())


class PDFReport:
    def __init__(
        self,
        stock_info: Dict[str, Any],
        price_data: Dict[str, Any],
        price_info: Dict[str, Any],
        revenue_data: List[Dict[str, Any]],
        revenue_chart: Optional[str],
        eps_data: List[Dict[str, Any]],
        eps_chart: Optional[str],
        news_data: Dict[str, Any],
        valuation_analysis: Optional[Dict[str, Any]] = None,
        dividend_data: Optional[Dict[str, Any]] = None,
        peers_data: Optional[List[Dict[str, Any]]] = None,
        financial_snapshot: Optional[Dict[str, Any]] = None,
        model_assessments: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
    ):
        self.stock_info = stock_info
        self.price_data = price_data
        self.price_info = price_info
        self.revenue_data = revenue_data
        self.revenue_chart = revenue_chart
        self.eps_data = eps_data
        self.eps_chart = eps_chart
        self.news_data = news_data
        self.valuation_analysis = valuation_analysis
        self.dividend_data = dividend_data
        self.peers_data = peers_data or []
        self.financial_snapshot = financial_snapshot or {}
        self.model_assessments = model_assessments or {}
        self.progress_callback = progress_callback
        self.font_path = get_chinese_font()
        self._init_pdf()

    def _init_pdf(self):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=20)
        self._font_ok = False
        regular_src = None
        bold_src = None
        for candidate in [self.font_path, FONT_PATH]:
            if candidate and os.path.exists(candidate):
                regular_src = candidate
                break
        if FONT_PATH_BOLD and os.path.exists(FONT_PATH_BOLD):
            bold_src = FONT_PATH_BOLD
        if not regular_src:
            raise RuntimeError("找不到可用的繁體中文字型，無法安全產生 PDF")
        if regular_src:
            try:
                self.pdf.add_font(FONT_NAME, "", regular_src)
                if bold_src:
                    self.pdf.add_font(FONT_NAME, "B", bold_src)
                else:
                    self.pdf.add_font(FONT_NAME, "B", regular_src)
                self._font_ok = True
            except (RuntimeError, FileNotFoundError) as e:
                logger.warning("font registration failed: %s", e)

    def _font(self, style="", size=12):
        if self._font_ok:
            self.pdf.set_font(FONT_NAME, style, size)
        else:
            raise RuntimeError("中文字型尚未完成註冊")

    def _multi_cell(self, width, height, text, **kwargs):
        """Render wrapped text and restore the left margin for the next block."""
        self.pdf.set_x(self.pdf.l_margin)
        self.pdf.multi_cell(
            width,
            height,
            text,
            new_x="LMARGIN",
            new_y="NEXT",
            **kwargs,
        )

    def generate(self, filename=None):
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            stock_id = self.stock_info.get("stock_id", "unknown")
            safe_stock_id = re.sub(r"[^0-9A-Za-z_-]", "_", str(stock_id)) or "unknown"
            filename = f"{safe_stock_id}_report_{ts}_{uuid.uuid4().hex[:8]}.pdf"
        filename = os.path.basename(str(filename))
        if not filename.lower().endswith(".pdf"):
            raise ValueError("PDF filename must end with .pdf")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, filename)
        is_etf = self.stock_info.get("is_etf", False)
        sections = [
            ("標題頁", self._add_title_page),
            ("基本資料", self._add_basic_info),
            ("模型估計", self._add_model_assessments),
            ("股價走勢", self._add_price_section),
        ]
        if not is_etf:
            sections.append(("營收分析", self._add_revenue_section))
            sections.append(("EPS 分析", self._add_eps_section))
        sections.append(("估值分析", self._add_valuation_section))
        sections.append(("同業比較", self._add_peers_section))
        sections.append(("股利分析", self._add_dividend_section))
        sections.append(("新聞摘要", self._add_news_section))
        sections.append(("免責聲明", self._add_disclaimer))
        sections.append(("名詞解釋", self._add_glossary))
        total = len(sections) + 1
        for i, (name, func) in enumerate(sections):
            func()
            if self.progress_callback:
                self.progress_callback(i + 1, total, name)
        if self.progress_callback:
            self.progress_callback(total, total, "寫入 PDF 檔案")
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=OUTPUT_DIR,
                prefix=".report-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = handle.name
            self.pdf.output(temp_path)
            with open(temp_path, "rb+") as handle:
                os.fsync(handle.fileno())
            os.replace(temp_path, output_path)
            temp_path = None
            enforce_output_policy()
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        return output_path

    def _data_source_summary(self):
        sources = ["TWSE／TPEx OpenAPI（公司清單）", "Yahoo Finance（行情與財務）"]
        record_sources = {
            record.get("source")
            for record in [*self.revenue_data, *self.eps_data]
            if record.get("source")
        }
        sources.extend(sorted(record_sources))
        if (self.news_data or {}).get("items"):
            sources.append("Google／Bing RSS（新聞索引）")
        return "、".join(dict.fromkeys(sources))

    def _freshness_note(self, text):
        self._font("", 8)
        self.pdf.set_text_color(150, 150, 150)
        self.pdf.cell(0, 5, f"  資料日期：{text}", new_x="LMARGIN", new_y="NEXT")
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(2)

    @staticmethod
    def _format_aum(aum):
        if aum >= 1e8:
            return f"{aum / 1e8:,.1f} 億元"
        return f"{aum:,.0f} 元"

    def _render_table(self, col_widths, items, font_size=9, row_height=7):
        for i, (lab, val) in enumerate(items):
            fill = i % 2 == 0
            self.pdf.set_fill_color(245, 250, 255) if fill else self.pdf.set_fill_color(
                255, 255, 255
            )
            self._font("", font_size)
            self.pdf.cell(col_widths[0], row_height, f"  {lab}", border=1, fill=True)
            self.pdf.cell(
                col_widths[1], row_height, val, border=1, fill=True, align="C"
            )
            self.pdf.ln()

    def _section_title(self, title):
        self.pdf.set_fill_color(18, 48, 71)
        self.pdf.set_text_color(255, 255, 255)
        self._font("B", 16)
        self.pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.pdf.ln(4)
        self.pdf.set_text_color(0, 0, 0)

    def _latest_price_date(self):
        for pname in ["1y", "6m", "3m"]:
            d = self.price_data.get(pname, {}).get("df")
            if d is not None and not d.empty:
                return str(d.index[-1].date())
        return "—"

    def _latest_revenue_date(self):
        if self.revenue_data:
            r = self.revenue_data[-1]
            return f"{r['year']}/{r['month']:02d}"
        return "—"

    def _latest_eps_date(self):
        if self.eps_data:
            r = self.eps_data[-1]
            q = r.get("quarter", "")
            return f"{r['year']} Q{q}" if q else str(r["year"])
        return "—"

    def _add_title_page(self):
        self.pdf.add_page()
        self.pdf.ln(40)
        self.pdf.set_text_color(18, 48, 71)
        self._font("B", 28)
        self.pdf.cell(
            0, 15, "台股投資分析報告", new_x="LMARGIN", new_y="NEXT", align="C"
        )
        self.pdf.ln(8)
        name = self.stock_info.get("name", "")
        stock_id = self.stock_info.get("stock_id", "")
        self.pdf.set_text_color(60, 60, 60)
        display_name = f"{name} ({stock_id})"
        self._font("B", 18 if len(display_name) <= 28 else 13)
        self._multi_cell(0, 10, display_name, align="C")
        self.pdf.ln(15)
        self.pdf.set_text_color(100, 100, 100)
        self._font("", 14)
        report_date = datetime.now().strftime("%Y 年 %m 月 %d 日")
        self.pdf.cell(
            0,
            10,
            f"報告產出日期：{report_date}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.pdf.ln(8)
        self.pdf.cell(
            0,
            10,
            "本報告由系統自動產生，僅供參考",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.pdf.ln(40)
        self.pdf.set_text_color(150, 150, 150)
        self._font("", 10)
        self._multi_cell(
            0,
            6,
            f"來源：{self._data_source_summary()}",
            align="C",
        )
        self.pdf.set_text_color(0, 0, 0)

    def _add_basic_info(self):
        self.pdf.add_page()
        is_etf = self.stock_info.get("is_etf", False)
        self._section_title("ETF 基本資訊" if is_etf else "個股基本資訊")
        info = self.stock_info
        pi = self.price_info if isinstance(self.price_info, dict) else {}
        fields = [
            ("名稱", info.get("name", "-")),
            ("代號", info.get("stock_id", "-")),
            ("產業分類", info.get("industry", "-")),
            ("市場別", info.get("market", "-")),
            ("報告產出日期", datetime.now().strftime("%Y年%m月%d日")),
        ]
        if info.get("current_price"):
            fields.append(("最新收盤價", f"{info['current_price']:.2f} 元"))
        if info.get("prev_close"):
            fields.append(("前日收盤價", f"{info['prev_close']:.2f} 元"))
        if is_etf:
            if info.get("nav_price"):
                fields.append(("NAV 淨值", f"{info['nav_price']:.2f} 元"))
            if info.get("fund_family"):
                fields.append(("發行商", info["fund_family"]))
            if info.get("etf_category"):
                fields.append(("類型", info["etf_category"]))
            if info.get("expense_ratio"):
                fields.append(("費用率", f"{info['expense_ratio'] * 100:.3f}%"))
            if info.get("total_assets"):
                fields.append(("管理資產 AUM", self._format_aum(info["total_assets"])))
            if info.get("avg_volume"):
                fields.append(("日均成交量", f"{info['avg_volume']:,.0f} 股"))
        else:
            if info.get("52w_high"):
                fields.append(("52週高點", f"{info['52w_high']:.2f} 元"))
            if info.get("52w_low"):
                fields.append(("52週低點", f"{info['52w_low']:.2f} 元"))
            if info.get("market_cap"):
                cap = info["market_cap"]
                if cap > 1e9:
                    cap_str = f"{cap / 1e9:.2f} 十億"
                elif cap > 1e6:
                    cap_str = f"{cap / 1e6:.2f} 百萬"
                else:
                    cap_str = f"{cap:.2f}"
                fields.append(("市值", cap_str))
            pe = pi.get("trailingPE") or info.get("trailingPE")
            if pe:
                fields.append(("本益比 (PE)", f"{pe:.2f}"))
            fpe = pi.get("forwardPE") or info.get("forwardPE")
            if fpe:
                fields.append(("預估本益比", f"{fpe:.2f}"))
            pb = pi.get("priceToBook") or info.get("priceToBook")
            if pb:
                fields.append(("股價淨值比 (PB)", f"{pb:.2f}"))
            roe = pi.get("returnOnEquity") or info.get("returnOnEquity")
            if roe:
                fields.append(("股東權益報酬率 (ROE)", f"{roe * 100:.1f}%"))
            pm = pi.get("profitMargins") or info.get("profitMargins")
            if pm:
                fields.append(("淨利率", f"{pm * 100:.1f}%"))
        dy = pi.get("dividendYield") or info.get("dividendYield")
        if dy and not is_etf:
            fields.append(("殖利率", f"{dy * 100:.2f}%"))
        desc = info.get("description", "")
        if desc and not is_etf:
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(0, 7, "公司簡介", new_x="LMARGIN", new_y="NEXT")
            self._font("", 9)
            self.pdf.set_text_color(80, 80, 80)
            desc_short = desc[:500] + "…" if len(desc) > 500 else desc
            self._multi_cell(0, 6, desc_short)
            self.pdf.set_text_color(0, 0, 0)
            emp = info.get("employees")
            if emp:
                self._font("", 8)
                self.pdf.set_text_color(120, 120, 120)
                self.pdf.cell(0, 5, f"員工：{emp:,} 人", new_x="LMARGIN", new_y="NEXT")
                self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_fill_color(240, 248, 255)
        for i, (label, value) in enumerate(fields):
            if i % 2 == 0:
                self.pdf.set_fill_color(245, 250, 255)
            else:
                self.pdf.set_fill_color(255, 255, 255)
            self._font("B", 11)
            self.pdf.cell(40, 10, label, border=0, fill=True)
            self._font("", 11)
            self.pdf.cell(0, 10, f"  {value}", new_x="LMARGIN", new_y="NEXT", fill=True)

    def _add_model_assessments(self):
        self.pdf.add_page()
        self._section_title("模型估計（與已知資料分開）")
        assessments = self.model_assessments or {}
        growth = assessments.get("growth") or {}
        safety = assessments.get("safety") or {}

        self._font("B", 13)
        self.pdf.cell(0, 8, "成長性", new_x="LMARGIN", new_y="NEXT")
        formal_growth = growth.get("rating")
        experimental_growth = growth.get("experimental_rating")
        growth_label = (
            f"正式評級：{formal_growth}"
            if formal_growth
            else (
                f"正式評級：未通過驗證（實驗分級 {experimental_growth}）"
                if experimental_growth
                else "正式評級：暫不提供"
            )
        )
        self._font("", 10)
        self._multi_cell(0, 6, growth_label)
        if growth.get("prediction_pct") is not None:
            interval = growth.get("prediction_interval_80") or {}
            self._multi_cell(
                0,
                6,
                "未來 12 個月營收實驗估計："
                f"{growth['prediction_pct']:+.2f}%；"
                f"80% 區間 {interval.get('low_pct', 0):+.2f}% ～ "
                f"{interval.get('high_pct', 0):+.2f}%。",
            )
        self._multi_cell(
            0,
            6,
            f"狀態：{growth.get('status', 'unavailable')}；"
            f"信心：{growth.get('confidence', 'none')}。",
        )
        if growth.get("note"):
            self._multi_cell(0, 6, f"限制：{growth['note']}")

        self.pdf.ln(4)
        self._font("B", 13)
        safety_title = (
            "ETF 結構安全" if self.stock_info.get("is_etf") else "公司財務安全"
        )
        self.pdf.cell(0, 8, safety_title, new_x="LMARGIN", new_y="NEXT")
        self._font("", 10)
        formal_safety = safety.get("rating")
        experimental_safety = safety.get("experimental_rating")
        safety_label = (
            f"正式評級：{formal_safety}（{safety.get('score', 0):.1f} / 100）"
            if formal_safety
            else (
                f"正式評級：未通過驗證（實驗分級 {experimental_safety}；"
                f"篩檢分數 {safety.get('score', 0):.1f} / 100）"
                if experimental_safety
                else "正式評級：資料不足或專用模型尚未完成"
            )
        )
        self._multi_cell(0, 6, safety_label)
        self._multi_cell(
            0,
            6,
            f"狀態：{safety.get('status', 'unavailable')}；"
            f"資料覆蓋率：{float(safety.get('coverage') or 0) * 100:.0f}%；"
            f"信心：{safety.get('confidence', 'none')}。",
        )
        if safety.get("note"):
            self._multi_cell(0, 6, f"限制：{safety['note']}")

        self.pdf.ln(5)
        self.pdf.set_fill_color(255, 247, 224)
        self._font("B", 10)
        self._multi_cell(
            0,
            7,
            assessments.get("separation_note")
            or "成長性與財務安全是不同問題，不合併成單一總分。",
            fill=True,
        )

    def _add_price_section(self):
        self.pdf.add_page()
        self._section_title("股價走勢分析")
        self._freshness_note(f"{self._latest_price_date()} 收盤")
        for period_name in ["3m", "6m", "1y"]:
            labels = {"3m": "近 3 個月", "6m": "近 6 個月", "1y": "近 1 年"}
            self._font("B", 13)
            self.pdf.cell(
                0,
                8,
                f"{labels.get(period_name, period_name)} 股價走勢",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            data = self.price_data.get(period_name, {})
            chart = data.get("chart")
            high = data.get("high")
            low = data.get("low")
            if chart and os.path.exists(chart):
                try:
                    self.pdf.image(chart, x=10, w=180)
                    self.pdf.ln(2)
                except (RuntimeError, FileNotFoundError) as e:
                    logger.warning("price chart image load failed: %s", e)
                    self.pdf.cell(
                        0, 6, "（圖表載入失敗）", new_x="LMARGIN", new_y="NEXT"
                    )
            if high:
                self._font("", 10)
                self.pdf.set_text_color(200, 0, 0)
                self.pdf.cell(
                    0,
                    6,
                    f"  期間最高：{high['price']} 元 ({high['date']})",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                self.pdf.set_text_color(0, 0, 0)
            if low:
                self._font("", 10)
                self.pdf.set_text_color(0, 128, 0)
                self.pdf.cell(
                    0,
                    6,
                    f"  期間最低：{low['price']} 元 ({low['date']})",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                self.pdf.set_text_color(0, 0, 0)
            self.pdf.ln(4)
        df_1y = self.price_data.get("1y", {}).get("df")
        if df_1y is not None and not df_1y.empty:
            close = df_1y["close"] if "close" in df_1y.columns else df_1y["Close"]
            parts = []
            for period, name in [(20, "月線"), (60, "季線"), (200, "年線")]:
                if len(close) >= period:
                    sma = close.rolling(period).mean().iloc[-1]
                    rel = "高於" if close.iloc[-1] > sma else "低於"
                    parts.append(f"{name}({rel})")
            if parts:
                self.pdf.ln(2)
                self._font("", 9)
                self.pdf.set_text_color(80, 80, 80)
                self.pdf.cell(
                    0,
                    6,
                    "  目前股價 " + " ｜ ".join(parts),
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                self.pdf.set_text_color(0, 0, 0)

    def _add_revenue_section(self):
        self.pdf.add_page()
        self._section_title("近兩年營收分析")
        self._freshness_note(f"最新至 {self._latest_revenue_date()}")
        if self.revenue_chart and os.path.exists(self.revenue_chart):
            try:
                self.pdf.image(self.revenue_chart, x=10, w=180)
                self.pdf.ln(4)
            except (RuntimeError, FileNotFoundError) as e:
                logger.warning("revenue chart image load failed: %s", e)
        if self.revenue_data:
            try:
                recent = (
                    self.revenue_data[-6:]
                    if len(self.revenue_data) > 6
                    else self.revenue_data
                )
                self._font("B", 11)
                self.pdf.cell(0, 7, "近幾期營收概況：", new_x="LMARGIN", new_y="NEXT")
                self.pdf.set_fill_color(240, 245, 250)
                col_w = [20, 25, 28, 22, 22]
                headers = ["年月", "營收(億)", "月增率", "年增率", "年增額"]
                self._font("B", 9)
                self.pdf.set_fill_color(220, 230, 240)
                for h, w in zip(headers, col_w):
                    self.pdf.cell(w, 8, h, border=1, fill=True, align="C")
                self.pdf.ln()
                self._font("", 9)
                for r in reversed(recent):
                    year = r.get("year", 0)
                    month = r["month"]
                    label = f"{year}/{month:02d}"
                    rev_100m = r["revenue"] / 1e5
                    mom = f"{r['mom']:+.1f}%" if r.get("mom") is not None else "N/A"
                    yoy = f"{r['yoy']:+.1f}%" if r.get("yoy") is not None else "N/A"
                    yoy_val = ""
                    if r.get("yoy") is not None:
                        diff = r["revenue"] - (r.get("last_year_revenue") or 0)
                        yoy_val = f"{diff / 1e5:+.1f}億" if abs(diff) > 1e3 else ""
                    self.pdf.cell(col_w[0], 7, label, border=1, align="C")
                    self.pdf.cell(col_w[1], 7, f"{rev_100m:.1f}", border=1, align="C")
                    self.pdf.cell(col_w[2], 7, mom, border=1, align="C")
                    self.pdf.cell(col_w[3], 7, yoy, border=1, align="C")
                    self.pdf.cell(col_w[4], 7, yoy_val, border=1, align="C")
                    self.pdf.ln()
                self.pdf.ln(4)
            except (KeyError, AttributeError) as e:
                logger.warning("revenue table rendering failed: %s", e)
            latest_yoy_values = [
                r["yoy"] for r in self.revenue_data if r.get("yoy") is not None
            ]
            if latest_yoy_values:
                avg_yoy = sum(latest_yoy_values) / len(latest_yoy_values)
                recent_yoy = (
                    latest_yoy_values[-3:]
                    if len(latest_yoy_values) >= 3
                    else latest_yoy_values
                )
                avg_recent_yoy = sum(recent_yoy) / len(recent_yoy)
                self._font("", 10)
                trend_parts = []
                if avg_yoy > 5:
                    trend_parts.append(
                        f"整體營收年增率平均約 {avg_yoy:.1f}%，營收趨勢偏正向。"
                    )
                elif avg_yoy < -5:
                    trend_parts.append(
                        f"整體營收年增率平均約 {avg_yoy:.1f}%，營收呈現衰退。"
                    )
                else:
                    trend_parts.append(
                        f"整體營收年增率平均約 {avg_yoy:.1f}%，營收大致持平。"
                    )
                if abs(avg_recent_yoy - avg_yoy) > 10:
                    if avg_recent_yoy > avg_yoy:
                        trend_parts.append(
                            f"近 3 期年增率上升至 {avg_recent_yoy:.1f}%，動能增強。"
                        )
                    else:
                        trend_parts.append(
                            f"近 3 期年增率降至 {avg_recent_yoy:.1f}%，動能放緩。"
                        )
                pi = self.price_info if isinstance(self.price_info, dict) else {}
                rg = pi.get("revenueGrowth")
                if rg:
                    trend_parts.append(f"年度營收成長率約 {rg * 100:.1f}%。")
                trend = " ".join(trend_parts)
                self._multi_cell(0, 7, trend)
        else:
            self._font("", 11)
            self.pdf.cell(
                0,
                8,
                "暫無營收資料，請至公開資訊觀測站查詢。",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    def _add_eps_section(self):
        self.pdf.add_page()
        self._section_title("EPS (每股盈餘) 分析")
        self._freshness_note(f"最新至 {self._latest_eps_date()}")
        if self.eps_chart and os.path.exists(self.eps_chart):
            try:
                self.pdf.image(self.eps_chart, x=10, w=180)
                self.pdf.ln(4)
            except (RuntimeError, FileNotFoundError) as e:
                logger.warning("EPS chart image load failed: %s", e)
        if self.eps_data:
            col_w = [30, 45, 30]
            self._font("B", 9)
            self.pdf.set_fill_color(220, 230, 240)
            for h, w in zip(["季度", "EPS (元)", "增減"], col_w):
                self.pdf.cell(w, 8, h, border=1, fill=True, align="C")
            self.pdf.ln()
            self._font("", 9)
            eps_values = [r["eps"] for r in self.eps_data]
            for i, r in enumerate(self.eps_data):
                diff = ""
                if i > 0 and len(eps_values) > i:
                    d = r["eps"] - eps_values[i - 1]
                    diff = f"{d:+.2f}"
                self.pdf.cell(col_w[0], 7, r["label"], border=1, align="C")
                self.pdf.cell(col_w[1], 7, f"{r['eps']:.2f}", border=1, align="C")
                self.pdf.cell(col_w[2], 7, diff, border=1, align="C")
                self.pdf.ln()
            self.pdf.ln(4)
            if len(eps_values) >= 2:
                recent_eps = eps_values[-4:] if len(eps_values) >= 4 else eps_values
                if len(recent_eps) >= 2:
                    trend_text = ""
                    if all(
                        recent_eps[i] <= recent_eps[i + 1]
                        for i in range(len(recent_eps) - 1)
                    ):
                        trend_text = "近幾季 EPS 呈現上升趨勢，獲利能力持續改善。"
                    elif all(
                        recent_eps[i] >= recent_eps[i + 1]
                        for i in range(len(recent_eps) - 1)
                    ):
                        trend_text = "近幾季 EPS 呈現下降趨勢，獲利能力有所下滑。"
                    else:
                        trend_text = "近幾季 EPS 呈現波動，獲利能力尚需觀察。"
                    avg_eps = sum(recent_eps) / len(recent_eps)
                    trend_text += (
                        f" 近{len(recent_eps)}季平均 EPS 為 {avg_eps:.2f} 元。"
                    )
                    self._font("", 10)
                    self._multi_cell(0, 7, trend_text)
                annual_eps = {}
                for record in self.eps_data:
                    annual_eps.setdefault(record["year"], []).append(record)
                if annual_eps:
                    self.pdf.ln(2)
                    self._font("B", 10)
                    self.pdf.cell(
                        0, 7, "各年度／年初至今 EPS：", new_x="LMARGIN", new_y="NEXT"
                    )
                    self._font("", 9)
                    for year in sorted(annual_eps.keys(), reverse=True)[:5]:
                        records = annual_eps[year]
                        total = sum(record["eps"] for record in records)
                        quarters = sorted(
                            {
                                record.get("quarter")
                                for record in records
                                if record.get("quarter")
                            }
                        )
                        label = (
                            "完整年度"
                            if quarters == [1, 2, 3, 4]
                            else f"YTD 截至 Q{max(quarters)}"
                            if quarters
                            else "資料不完整"
                        )
                        self.pdf.cell(
                            0,
                            6,
                            f"  {year} 年（{label}）：{total:.2f} 元",
                            new_x="LMARGIN",
                            new_y="NEXT",
                        )
        else:
            self._font("", 11)
            self.pdf.cell(
                0,
                8,
                "暫無 EPS 資料，請至公開資訊觀測站查詢。",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    def _add_valuation_section(self):
        va = self.valuation_analysis
        if not va:
            return
        try:
            self.pdf.add_page()
            self._section_title("估值分析")
            if va.get("is_etf"):
                self._font("B", 12)
                self.pdf.cell(0, 8, "ETF 評估指標", new_x="LMARGIN", new_y="NEXT")
                self.pdf.ln(2)

                # Overall ETF rating from backend
                orating = va.get("overall_rating", {}) or {}
                if orating.get("rating"):
                    or_colors = {
                        "A": (16, 125, 92),
                        "B": (37, 99, 155),
                        "C": (194, 126, 23),
                        "D": (190, 55, 55),
                        "N/A": (100, 116, 139),
                    }
                    ocolor = or_colors.get(orating.get("rating", "B"), (0, 0, 0))
                    self._font("B", 16)
                    self.pdf.set_text_color(*ocolor)
                    self.pdf.cell(
                        0,
                        10,
                        f"  綜合評級：{orating['rating']}（{orating['score']} 分）"
                        if orating.get("score") is not None
                        else "  綜合評級：資料不足，暫不提供字母評級",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    self.pdf.set_text_color(0, 0, 0)
                    self.pdf.ln(2)

                info = self.stock_info
                col_w = [55, 50]
                items = []
                if info.get("current_price"):
                    items.append(("收盤價", f"{info['current_price']:.2f} 元"))
                if info.get("nav_price"):
                    items.append(("NAV 淨值", f"{info['nav_price']:.2f} 元"))
                    price = info.get("current_price")
                    if price:
                        prem = round(
                            (price - info["nav_price"]) / info["nav_price"] * 100, 2
                        )
                        sign = "+" if prem > 0 else ""
                        color = (
                            "溢價" if prem > 1 else ("折價" if prem < -1 else "平價")
                        )
                        items.append(("折溢價", f"{sign}{prem}% ({color})"))
                if info.get("expense_ratio"):
                    er = info["expense_ratio"]
                    er_color = (
                        "偏低" if er < 0.005 else ("合理" if er < 0.01 else "偏高")
                    )
                    items.append(("費用率", f"{er * 100:.3f}% ({er_color})"))
                if info.get("total_assets"):
                    items.append(
                        ("資產規模 AUM", self._format_aum(info["total_assets"]))
                    )
                if info.get("avg_volume"):
                    items.append(("日均成交量", f"{info['avg_volume']:,.0f} 股"))
                dy = info.get("etf_yield") or info.get("dividendYield")
                if dy:
                    items.append(("殖利率", f"{dy * 100:.2f}%"))
                self._render_table(col_w, items)
                self.pdf.set_text_color(0, 0, 0)
                return
            fp = va.get("fair_price_range")
            peg = va.get("peg")
            rev = va.get("revenue_growth")
            score = va.get("health_score")
            warnings = va.get("risk_warnings", [])
            text = va.get("analysis_text", "")

            col_w_2 = [60, 50]
            if fp:
                self._font("B", 11)
                self.pdf.cell(0, 7, "合理價區間", new_x="LMARGIN", new_y="NEXT")
                self.pdf.ln(2)
                self.pdf.set_fill_color(240, 245, 250)
                items = [
                    ("便宜價", f"{fp.get('cheap', 'N/A')} 元"),
                    ("合理價", f"{fp.get('fair', 'N/A')} 元"),
                    ("昂貴價", f"{fp.get('expensive', 'N/A')} 元"),
                    ("安全買入價 (0.8x)", f"{fp.get('margin_safety_8', 'N/A')} 元"),
                    ("目前股價", f"{fp.get('current_price', 'N/A')} 元"),
                    ("目前本益比", f"{fp.get('current_pe', 'N/A')}"),
                ]
                self._font("", 9)
                for i, (lab, val) in enumerate(items):
                    fill = i % 2 == 0
                    if fill:
                        self.pdf.set_fill_color(245, 250, 255)
                    else:
                        self.pdf.set_fill_color(255, 255, 255)
                    self.pdf.cell(col_w_2[0], 7, f"  {lab}", border=1, fill=True)
                    self.pdf.cell(col_w_2[1], 7, val, border=1, fill=True, align="C")
                    self.pdf.ln()

                self.pdf.ln(2)
                self._font("", 8)
                self.pdf.set_text_color(100, 100, 100)
                self.pdf.cell(
                    0,
                    5,
                    f"歷史 PE：P25={fp.get('pe_p25', '')}  P50={fp.get('pe_p50', '')}  "
                    f"P75={fp.get('pe_p75', '')}  樣本={fp.get('sample_size', 0)} 日",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                self.pdf.set_text_color(0, 0, 0)
                self._font("B", 8)
                self.pdf.set_text_color(180, 100, 50)
                self.pdf.cell(
                    0,
                    6,
                    "※ 價格區間為歷史 PE 情境，另含成長率啟發式調整；未經回測校準，不是預測目標價。",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                self.pdf.set_text_color(0, 0, 0)

            # — Overall Rating —
            orating = va.get("overall_rating", {}) or {}
            if orating.get("rating"):
                self.pdf.ln(2)
                or_colors = {
                    "A": (16, 125, 92),
                    "B": (37, 99, 155),
                    "C": (194, 126, 23),
                    "D": (190, 55, 55),
                    "N/A": (100, 116, 139),
                }
                ocolor = or_colors.get(orating.get("rating", "B"), (0, 0, 0))
                self._font("B", 16)
                self.pdf.set_text_color(*ocolor)
                self.pdf.cell(
                    0,
                    10,
                    f"  綜合評級：{orating['rating']}（{orating['score']} 分）"
                    if orating.get("score") is not None
                    else "  綜合評級：資料不足，暫不提供字母評級",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                self.pdf.set_text_color(0, 0, 0)
                comps = orating.get("components", {}) or {}
                if comps:
                    self._font("", 8)
                    self.pdf.set_text_color(100, 100, 100)
                    parts = []
                    for k in ["health_score", "quality", "safety", "graham"]:
                        v = comps.get(k, {})
                        if isinstance(v, dict):
                            parts.append(f"{k}: {v.get('score', '?')}")
                    if parts:
                        self.pdf.cell(
                            0,
                            5,
                            "  " + "  |  ".join(parts),
                            new_x="LMARGIN",
                            new_y="NEXT",
                        )
                    self.pdf.set_text_color(0, 0, 0)

            if peg:
                self.pdf.ln(3)
                self._font("B", 11)
                self.pdf.cell(0, 7, "PEG 分析", new_x="LMARGIN", new_y="NEXT")
                self._font("", 10)
                if peg.get("peg") is not None:
                    color_map = {
                        "偏低": (0, 128, 0),
                        "合理": (0, 0, 0),
                        "偏高": (200, 0, 0),
                    }
                    v_color = next(
                        (
                            c
                            for k, c in color_map.items()
                            if k in str(peg.get("verdict", ""))
                        ),
                        (0, 0, 0),
                    )
                    self.pdf.set_text_color(*v_color)
                    self.pdf.cell(
                        0,
                        7,
                        f"PEG = {peg['peg']}（{peg['verdict']}）",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    self.pdf.set_text_color(0, 0, 0)
                    self._font("", 9)
                    self.pdf.cell(
                        0,
                        6,
                        f"  本益比 {peg['pe']} ／ EPS 成長率 {peg.get('eps_growth_pct')}%",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                else:
                    self._font("", 9)
                    self.pdf.set_text_color(100, 100, 100)
                    self.pdf.cell(
                        0, 6, peg.get("verdict", ""), new_x="LMARGIN", new_y="NEXT"
                    )
                    self.pdf.set_text_color(0, 0, 0)

            if rev:
                self.pdf.ln(3)
                self._font("B", 11)
                self.pdf.cell(0, 7, "營收成長評估", new_x="LMARGIN", new_y="NEXT")
                self._font("", 9)
                cpos = rev.get("consecutive_positive_months", 0)
                cneg = rev.get("consecutive_negative_months", 0)
                parts = []
                if rev.get("avg_recent_yoy_pct") is not None:
                    parts.append(f"近 3 期年增率均值：{rev['avg_recent_yoy_pct']}%")
                if cpos >= 3:
                    parts.append(f"連續 {cpos} 個月正成長")
                if cneg >= 2:
                    parts.append(f"連續 {cneg} 個月負成長")
                if rev.get("accelerating"):
                    parts.append("動能增強 ↑")
                elif rev.get("decelerating"):
                    parts.append("動能放緩 ↓")
                if parts:
                    self._multi_cell(0, 6, "  " + " ／ ".join(parts))
                if rev.get("trend_slope") is not None:
                    self.pdf.set_x(self.pdf.l_margin)
                    self.pdf.cell(
                        0,
                        6,
                        f"  成長趨勢斜率：{rev['trend_slope']:.3f}",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )

            # — Quality Score —
            qs = va.get("quality_score", {}) or {}
            has_qs = bool(qs)
            if has_qs:
                self.pdf.ln(3)
                self._font("B", 11)
                self.pdf.cell(0, 7, "多因子品質評分", new_x="LMARGIN", new_y="NEXT")
                self._font("", 9)
                pf = qs.get("piotroski_f_score")
                if pf is not None:
                    pf_color = (
                        (0, 128, 0)
                        if pf >= 7
                        else ((200, 150, 0) if pf >= 4 else (200, 0, 0))
                    )
                    self.pdf.set_text_color(*pf_color)
                    self.pdf.cell(
                        0,
                        6,
                        f"  Piotroski F-Score：{pf}/9  （完整九項資料）",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    self.pdf.set_text_color(0, 0, 0)
                else:
                    details = qs.get("piotroski_details", {})
                    self.pdf.cell(
                        0,
                        6,
                        f"  Piotroski F-Score：資料不足（可計算 {details.get('available_count', 0)}/9 項）",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                az = qs.get("altman_z_score")
                if az is not None:
                    az_color = (
                        (0, 128, 0)
                        if az >= 2.99
                        else ((200, 150, 0) if az >= 1.81 else (200, 0, 0))
                    )
                    self.pdf.set_text_color(*az_color)
                    self.pdf.cell(
                        0,
                        6,
                        f"  Altman Z-Score：{az:.2f}  （原始上市製造業模型：>=2.99 安全 | 1.81~2.99 灰色）",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    self.pdf.set_text_color(0, 0, 0)
                gn = qs.get("graham_number")
                if gn is not None:
                    cp = fp.get("current_price") if fp else None
                    if cp:
                        ratio = cp / gn
                        gn_color = (
                            (0, 128, 0)
                            if ratio <= 1
                            else ((200, 150, 0) if ratio <= 1.5 else (200, 0, 0))
                        )
                        self.pdf.set_text_color(*gn_color)
                        self.pdf.cell(
                            0,
                            6,
                            f"  Graham Number：{gn:.1f} 元（股價/GN = {ratio:.2f}）",
                            new_x="LMARGIN",
                            new_y="NEXT",
                        )
                        self.pdf.set_text_color(0, 0, 0)

            if score:
                self.pdf.ln(3)
                self._font("B", 11)
                self.pdf.cell(0, 7, "健康度評分", new_x="LMARGIN", new_y="NEXT")
                ts = score["total_score"]
                level = score["level"]
                if ts is None:
                    self._font("", 9)
                    self.pdf.cell(
                        0,
                        7,
                        f"  資料不足（覆蓋權重 {score.get('coverage', 0) * 100:.0f}%）",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                elif ts >= 70:
                    scolor = (0, 128, 0)
                elif ts >= 45:
                    scolor = (200, 150, 0)
                else:
                    scolor = (200, 0, 0)
                if ts is not None:
                    self._font("B", 14)
                    self.pdf.set_text_color(*scolor)
                    self.pdf.cell(
                        0,
                        8,
                        f"  {ts} 分（{level}，資料覆蓋 {score.get('coverage', 0) * 100:.0f}%）",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    self.pdf.set_text_color(0, 0, 0)
                    self._font("", 8)
                    self.pdf.ln(1)
                    self.pdf.set_text_color(130, 130, 130)
                    self.pdf.cell(
                        0,
                        5,
                        "  對照：70+ 良好 ｜ 45~69 普通 ｜ <45 需謹慎",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                    self.pdf.set_text_color(0, 0, 0)
                    self._font("", 8)
                    comps = score.get("components", {})
                    label_w = 25
                    bar_w = 80
                    score_w = 15
                    for cname, cdata in comps.items():
                        cs = cdata["score"]
                        if cs is None:
                            continue
                        label_map = {
                            "growth": "成長性",
                            "valuation": "估值",
                            "profitability": "獲利",
                            "quality": "品質力",
                            "momentum": "動能",
                            "stability": "穩定",
                            "cashflow": "現金流",
                        }
                        cn = label_map.get(cname, cname)
                        cs_color = (
                            (0, 128, 0)
                            if cs >= 70
                            else ((200, 150, 0) if cs >= 45 else (200, 0, 0))
                        )
                        self.pdf.cell(label_w, 5, f"  {cn}", border=0)
                        x0 = self.pdf.get_x()
                        fill_w = max(bar_w * cs / 100, 1.5) if cs > 0 else 0
                        self.pdf.set_fill_color(*cs_color)
                        self.pdf.rect(x0, self.pdf.get_y(), fill_w, 5, "F")
                        self.pdf.set_fill_color(255, 255, 255)
                        self.pdf.set_x(x0 + bar_w)
                        self.pdf.cell(
                            score_w,
                            5,
                            f"{cs:.0f}",
                            new_x="LMARGIN",
                            new_y="NEXT",
                            align="R",
                        )

            if warnings:
                self.pdf.ln(3)
                self._font("B", 11)
                self.pdf.cell(0, 7, "風險提示", new_x="LMARGIN", new_y="NEXT")
                for w in warnings:
                    lvl = w["level"]
                    if lvl == "red":
                        wcolor = (200, 0, 0)
                    elif lvl == "yellow":
                        wcolor = (200, 150, 0)
                    else:
                        wcolor = (0, 128, 0)
                    self._font("", 9)
                    self.pdf.set_text_color(*wcolor)
                    msg = f"  [{lvl.upper()}] {w['msg']}"
                    self._multi_cell(0, 6, msg)
                    self.pdf.set_text_color(0, 0, 0)

            if text:
                self.pdf.ln(3)
                self._font("B", 11)
                self.pdf.cell(0, 7, "綜合分析", new_x="LMARGIN", new_y="NEXT")
                self._font("", 9)
                self.pdf.set_text_color(60, 60, 60)
                self._multi_cell(0, 6, text)
                self.pdf.set_text_color(0, 0, 0)
        except (KeyError, AttributeError) as e:
            logger.exception("valuation section rendering failed: %s", e)
            raise

    def _add_dividend_section(self):
        dd = self.dividend_data
        if not dd or not dd.get("has_dividend"):
            return
        self.pdf.add_page()
        self._section_title("股利分析")
        hist = dd.get("history", [])
        cy = dd.get("consecutive_years", 0)
        ly = dd.get("latest_yield")
        ay = dd.get("avg_yield_3y")

        self._font("B", 11)
        self.pdf.cell(0, 7, "歷年每股現金股利", new_x="LMARGIN", new_y="NEXT")
        self.pdf.ln(2)
        col_w = [25, 30]
        self.pdf.set_fill_color(220, 230, 240)
        self._font("B", 9)
        self.pdf.cell(col_w[0], 8, "年度", border=1, fill=True, align="C")
        self.pdf.cell(col_w[1], 8, "股利 (元)", border=1, fill=True, align="C")
        self.pdf.ln()
        self._font("", 9)
        for r in hist[:6]:
            year_label = (
                f"{r['year']} YTD" if r.get("status") == "ytd" else str(r["year"])
            )
            self.pdf.cell(col_w[0], 7, year_label, border=1, align="C")
            self.pdf.cell(col_w[1], 7, f"{r['dividend']:.2f}", border=1, align="C")
            self.pdf.ln()

        self.pdf.ln(4)
        self._font("", 10)
        lines = []
        if cy >= 5:
            lines.append(f"連續 {cy} 年配息，股利政策穩定。")
        elif cy >= 3:
            lines.append(f"連續 {cy} 年配息。")
        elif cy > 0:
            lines.append("近幾年有配息紀錄。")
        if ly is not None:
            basis_year = dd.get("last_completed_year")
            lines.append(f"{basis_year or '最近完整年度'}殖利率：{ly:.2f}%")
        if ay is not None and ay > 0 and ly is not None:
            direction = "高於" if ly > ay else "低於"
            lines.append(f"近 3 年平均殖利率 {ay:.2f}%，目前 {direction} 平均。")
        if lines:
            self._multi_cell(0, 7, "  " + " ／ ".join(lines))

    def _add_peers_section(self):
        peers = self.peers_data
        if not peers:
            return
        is_etf = self.stock_info.get("is_etf", False)
        self.pdf.add_page()
        self._section_title("同業比較")
        self._font("", 10)
        industry_label = "類型" if is_etf else "產業"
        self.pdf.cell(
            0,
            7,
            f"{industry_label}：{self.stock_info.get('industry', '—')}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.pdf.ln(3)
        if is_etf:
            col_w = [35, 25, 25, 25, 25]
            self.pdf.set_fill_color(220, 230, 240)
            self._font("B", 8)
            headers = ["股票", "股價", "NAV", "折溢價", "費用率"]
            for i, h in enumerate(headers):
                self.pdf.cell(col_w[i], 8, h, border=1, fill=True, align="C")
            self.pdf.ln()
            self._font("", 8)
            for p in peers:
                price = f"{p['price']:.2f}" if p.get("price") is not None else "—"
                nav = f"{p.get('nav_price', 0):.2f}" if p.get("nav_price") else "—"
                prem = p.get("premium_pct")
                prem_str = f"{prem:+.2f}%" if prem is not None else "—"
                er = p.get("expense_ratio")
                er_str = f"{er * 100:.3f}%" if er is not None else "—"
                label = p.get("name", "—")[:8]
                self.pdf.cell(col_w[0], 7, label, border=1, align="C")
                self.pdf.cell(col_w[1], 7, price, border=1, align="C")
                self.pdf.cell(col_w[2], 7, nav, border=1, align="C")
                self.pdf.cell(col_w[3], 7, prem_str, border=1, align="C")
                self.pdf.cell(col_w[4], 7, er_str, border=1, align="C")
                self.pdf.ln()
        else:
            col_w = [35, 30, 30, 30]
            self.pdf.set_fill_color(220, 230, 240)
            self._font("B", 9)
            headers = ["股票", "股價", "本益比", "殖利率"]
            for i, h in enumerate(headers):
                self.pdf.cell(col_w[i], 8, h, border=1, fill=True, align="C")
            self.pdf.ln()
            self._font("", 9)
            for p in peers:
                price = f"{p['price']:.2f} 元" if p.get("price") is not None else "—"
                pe_val = f"{p['pe']:.2f}" if p.get("pe") is not None else "—"
                yield_val = (
                    f"{p['dividend_yield']:.2f}%"
                    if p.get("dividend_yield") is not None
                    else "—"
                )
                label = p.get("name", "—")
                self.pdf.cell(col_w[0], 7, label, border=1, align="C")
                self.pdf.cell(col_w[1], 7, price, border=1, align="C")
                self.pdf.cell(col_w[2], 7, pe_val, border=1, align="C")
                self.pdf.cell(col_w[3], 7, yield_val, border=1, align="C")
                self.pdf.ln()

    def _add_news_section(self):
        self.pdf.add_page()
        self._section_title("新聞與研究摘要")
        news_items = (self.news_data or {}).get("items", [])
        analysis_summary = (self.news_data or {}).get("analysis_summary", "")
        if analysis_summary:
            self._font("B", 11)
            self.pdf.cell(0, 7, "【趨勢摘要】", new_x="LMARGIN", new_y="NEXT")
            self._font("", 10)
            self._multi_cell(0, 7, analysis_summary)
            self.pdf.ln(4)
        if not news_items:
            self._font("", 11)
            self.pdf.cell(0, 8, "暫無近期新聞資料。", new_x="LMARGIN", new_y="NEXT")
            return
        self._font("B", 11)
        self.pdf.cell(
            0,
            7,
            f"【近期相關新聞共 {len(news_items)} 則】",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.pdf.ln(2)
        for i, item in enumerate(news_items[:15], 1):
            try:
                title = item.title[:80] + "..." if len(item.title) > 80 else item.title
                date_str = item.publish_date[:10] if item.publish_date else ""
                src = item.source or ""
                date_part = f"[{date_str}]" if date_str else ""
                src_part = f"({src})" if src else ""
                news_kind = "產業新聞備援" if item.is_fallback else "公司相關新聞"
                line = f"{i}. [{news_kind}] {title}"
                self._font("B", 9)
                self.pdf.set_text_color(18, 48, 71)
                self._multi_cell(0, 6, line)
                self.pdf.set_text_color(100, 100, 100)
                self._font("", 8)
                if date_part or src_part:
                    self.pdf.set_x(self.pdf.l_margin)
                    self.pdf.cell(
                        0,
                        5,
                        f"   {date_part} {src_part}",
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                if item.summary:
                    summary = item.summary[:100]
                    self.pdf.set_text_color(80, 80, 80)
                    self._multi_cell(0, 5, f"   {summary}")
                self.pdf.set_text_color(0, 0, 0)
                self.pdf.ln(2)
            except (AttributeError, KeyError) as e:
                logger.warning("news item rendering skipped: %s", e)
                continue
        provider_errors = (self.news_data or {}).get("provider_errors", {})
        if provider_errors:
            self.pdf.ln(2)
            self._font("", 8)
            self.pdf.set_text_color(150, 150, 150)
            failed = [k for k in provider_errors.keys()]
            self.pdf.cell(
                0,
                5,
                f"（部分新聞來源未取得資料：{', '.join(failed)}）",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            self.pdf.set_text_color(0, 0, 0)

    def _add_disclaimer(self):
        self.pdf.add_page()
        self.pdf.ln(40)
        self.pdf.set_fill_color(240, 240, 240)
        self.pdf.rect(15, self.pdf.get_y(), 180, 50, "F")
        self.pdf.set_text_color(80, 80, 80)
        self._font("B", 14)
        self.pdf.cell(0, 10, "投資免責聲明", new_x="LMARGIN", new_y="NEXT", align="C")
        self.pdf.ln(5)
        self._font("", 10)
        self.pdf.set_text_color(100, 100, 100)
        self._multi_cell(
            0,
            7,
            "所有投資相關內容僅供參考，不構成任何投資建議，"
            "使用者應自行評估風險。\n\n"
            f"本報告本次資料來源：{self._data_source_summary()}。\n\n"
            "第三方資料可能延遲、缺漏或受使用條款限制；資訊正確性以 TWSE、TPEx 與"
            "公開資訊觀測站等官方原始公告為準。\n"
            "投資有風險，入市前請審慎評估。",
            align="C",
        )
        self.pdf.set_text_color(0, 0, 0)

    def _add_glossary(self):
        self.pdf.add_page()
        is_etf = self.stock_info.get("is_etf", False)
        self._section_title("專有名詞解釋")
        entries = [
            (
                "本益比 (PE)",
                "股價 ÷ 每股盈餘，表示市場給予盈餘的倍數；不同產業、景氣階段與會計品質不可直接橫向比較。",
            ),
            (
                "股價淨值比 (PB)",
                "股價 ÷ 每股淨值。低於 1 不等於被低估，仍須檢查資產品質、獲利能力與產業特性。",
            ),
            (
                "PEG",
                "PE ÷ EPS 成長率。本工具僅將其作為啟發式參考；成長率期間、負成長與一次性盈餘會使結果失真。",
            ),
            (
                "ROE (股東權益報酬率)",
                "稅後淨利 ÷ 平均股東權益，用於觀察資本使用效率；高槓桿也可能推升 ROE。",
            ),
            (
                "殖利率",
                "每股現金股利 ÷ 參考股價。高殖利率可能來自股價下跌，且過去配息不保證未來配息。",
            ),
            (
                "安全邊際",
                "(合理價 - 目前股價) / 合理價。預留的下跌緩衝空間，安全邊際越高風險越低。",
            ),
            (
                "健康度評分",
                "資料覆蓋至少 50% 才顯示。權重為成長 22%、估值 20%、獲利 18%、品質 15%、動能 12%、穩定 8%、現金流 5%；未經績效回測校準。",
            ),
        ]
        if is_etf:
            entries = [
                (
                    "NAV (淨資產價值)",
                    "ETF 每股對應的實際資產價值，計算方式為（基金總資產－總負債）÷ 發行股數。市價偏離 NAV 即產生折溢價。",
                ),
                (
                    "折溢價",
                    "市價與 NAV 之間的偏離幅度。溢價（市價 > NAV）代表買貴了，折價（市價 < NAV）代表買便宜了。溢價 > 1% 應謹慎。",
                ),
                (
                    "費用率 (Expense Ratio)",
                    "ETF 每年的管理費、保管費等總和佔基金淨值的比例。費用率越低，長期投資成本越少。一般被動型 ETF 費用率 < 0.5%。",
                ),
                (
                    "AUM (資產管理規模)",
                    "ETF 管理的總資產金額。規模越大通常代表流動性越好、折溢價較穩定。",
                ),
                (
                    "殖利率",
                    "每股現金股利 ÷ 參考股價。高殖利率可能來自股價下跌，且過去配息不保證未來配息。",
                ),
                (
                    "追蹤誤差 (Tracking Error)",
                    "ETF 報酬與其追蹤指數報酬之間的偏離程度。誤差越小，代表 ETF 複製指數效果越好。",
                ),
                (
                    "本益比 (PE)",
                    "股價 ÷ 每股盈餘，表示市場給予盈餘的倍數；不同產業、景氣階段與會計品質不可直接橫向比較。",
                ),
            ]
        self._font("", 10)
        for term, desc in entries:
            self.pdf.set_fill_color(240, 245, 250)
            self._font("B", 11)
            self.pdf.cell(0, 8, f"  {term}", new_x="LMARGIN", new_y="NEXT", fill=True)
            self.pdf.set_fill_color(255, 255, 255)
            self._font("", 10)
            self.pdf.set_text_color(80, 80, 80)
            self._multi_cell(0, 7, f"  {desc}")
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.ln(2)
