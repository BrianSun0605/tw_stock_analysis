import logging
import os
import re
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from config import PDF_FONT_PATH, PDF_FONT_PATH_BOLD, FONT_NAME, OUTPUT_DIR
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
        language: str = "zh-TW",
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
        self.language = "en" if language == "en" else "zh-TW"
        self.font_path = get_chinese_font()
        self._init_pdf()

    def _init_pdf(self):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=20)
        self._font_ok = False
        regular_src = None
        bold_src = None
        for candidate in [self.font_path, PDF_FONT_PATH]:
            if candidate and os.path.exists(candidate):
                regular_src = candidate
                break
        if PDF_FONT_PATH_BOLD and os.path.exists(PDF_FONT_PATH_BOLD):
            bold_src = PDF_FONT_PATH_BOLD
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
        # Noto Sans TC covers the report languages but not all decorative emoji
        # found in raw RSS/news text. Remove only supplementary emoji so a
        # single unsupported glyph cannot produce a PDF font warning or blank
        # placeholder; all words, numbers, CJK text, and punctuation remain.
        text = "".join(
            char
            for char in str(text)
            if not (0x1F300 <= ord(char) <= 0x1FAFF or ord(char) == 0xFE0F)
        )
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
        if self.language == "en":
            return self._generate_english(filename)
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

    def _generate_english(self, filename: str) -> str:
        """Produce an English report with the same report coverage as Chinese output."""
        sections = [
            ("Cover page", self._add_english_title_page),
            ("Security profile", self._add_english_profile),
            ("Model estimates", self._add_english_model_assessments),
            ("Price trend", self._add_english_price_section),
        ]
        if not self.stock_info.get("is_etf"):
            sections.extend(
                [
                    ("Revenue analysis", self._add_english_revenue_section),
                    ("EPS analysis", self._add_english_eps_section),
                ]
            )
        sections.extend(
            [
                ("Valuation or ETF structure", self._add_english_valuation_section),
                (
                    "Fundamental health and quality",
                    self._add_english_health_quality_section,
                ),
                (
                    "Financial metrics and sources",
                    self._add_english_financial_metrics_section,
                ),
                (
                    "Risk signals and analysis notes",
                    self._add_english_risk_analysis_section,
                ),
                ("Peers", self._add_english_peers_section),
                ("Dividends", self._add_english_dividend_section),
                ("News summary", self._add_english_news_section),
                ("Glossary", self._add_english_glossary),
                ("Method and disclaimer", self._add_english_disclaimer),
            ]
        )
        total = len(sections) + 1
        for index, (name, function) in enumerate(sections):
            function()
            if self.progress_callback:
                self.progress_callback(index + 1, total, name)
        if self.progress_callback:
            self.progress_callback(total, total, "Writing PDF file")
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=OUTPUT_DIR, prefix=".report-", suffix=".tmp", delete=False
            ) as handle:
                temp_path = handle.name
            self.pdf.output(temp_path)
            with open(temp_path, "rb+") as handle:
                os.fsync(handle.fileno())
            os.replace(temp_path, os.path.join(OUTPUT_DIR, filename))
            temp_path = None
            enforce_output_policy()
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        return os.path.join(OUTPUT_DIR, filename)

    def _english_name(self) -> str:
        return str(
            self.stock_info.get("name_en")
            or self.stock_info.get("stock_id")
            or "Taiwan security"
        )

    @staticmethod
    def _has_cjk_text(value: Any) -> bool:
        """Return whether a system-generated value contains CJK characters."""
        return bool(re.search(r"[\u3400-\u9fff]", str(value or "")))

    @staticmethod
    def _english_health_level(value: Any) -> str:
        """Localize labels produced by the Chinese-only valuation engine."""
        label = str(value or "Unavailable")
        return {
            "良好": "Good",
            "普通": "Fair",
            "需謹慎": "Needs caution",
            "資料不足": "Insufficient data",
        }.get(label, "Reference level" if PDFReport._has_cjk_text(label) else label)

    @staticmethod
    def _english_risk_category(value: Any) -> str:
        """Translate every current system-generated risk category.

        Security names, industry names, and source text are deliberately not
        passed through this helper.  It is only used for analyser-owned labels.
        """
        label = str(value or "Risk signal")
        translations = {
            "營收衰退": "Revenue contraction",
            "成長放緩": "Growth deceleration",
            "高估值": "High valuation",
            "估值偏低": "Low valuation reference",
            "PEG 過高": "High PEG",
            "波動過大": "High volatility",
            "波動較大": "Elevated volatility",
            "EPS 下滑": "EPS decline",
            "財務品質": "Financial quality",
            "財務壓力": "Financial stress",
            "財務穩健": "Financial resilience",
            "葛拉漢警訊": "Graham-value warning",
            "流動性": "Liquidity",
            "獲利衰退": "Profitability decline",
            "綜合健康度": "Overall fundamental health",
        }
        return translations.get(
            label,
            "System-generated risk signal" if PDFReport._has_cjk_text(label) else label,
        )

    @staticmethod
    def _english_risk_horizon(value: Any) -> str:
        horizon = str(value or "").strip().lower()
        return {
            "short": "Short term",
            "short term": "Short term",
            "mid": "Medium term",
            "mid term": "Medium term",
            "long": "Long term",
            "long term": "Long term",
        }.get(horizon, "")

    def _english_risk_message(self, value: Any) -> str:
        """Translate the analyser's risk-message templates without touching raw data."""
        message = str(value or "No detail provided")
        exact = {
            "本益比數據不足，無法計算 PEG": "P/E data is insufficient; PEG cannot be calculated.",
            "需要兩組完整且連續的四季 EPS 才能計算成長率": "Two complete, consecutive sets of four quarterly EPS observations are required to calculate growth.",
            "EPS 成長率為負或零，PEG 不具參考意義": "EPS growth is zero or negative, so PEG has no reference value.",
            "偏低（可能被低估）": "Low (possibly undervalued under this reference).",
            "合理": "Broadly aligned under this reference.",
            "偏高（注意估值風險）": "High (review valuation risk).",
            "近月營收年增率出現負值": "Recent revenue year-over-year growth was negative.",
            "營收年增率動能減弱": "Revenue year-over-year growth momentum has weakened.",
            "本益比顯著低於歷史區間，注意是否有基本面疑慮": "P/E is materially below its historical range; review whether fundamentals explain the discount.",
            "現金/負債比率偏低，留意流動性風險": "The cash-to-debt ratio is low; monitor liquidity risk.",
            "ROA 較去年同期顯著下滑": "Return on assets has declined materially from the prior-year period.",
        }
        if message in exact:
            return exact[message]

        patterns = (
            (
                r"^連續\s*(\d+)\s*個月營收年增率為負$",
                "Revenue year-over-year growth was negative for \\1 consecutive months.",
            ),
            (
                r"^本益比\s*([^\s]+)\s*顯著高於歷史\s*75%\s*分位\s*([^\s]+)$",
                "P/E \\1 is materially above the historical 75th percentile (\\2).",
            ),
            (
                r"^本益比\s*([^\s]+)\s*高於歷史\s*75%\s*分位\s*([^\s]+)$",
                "P/E \\1 is above the historical 75th percentile (\\2).",
            ),
            (
                r"^PEG\s*([^\s]+)\s*>\s*3，成長無法支撐當前估值$",
                "PEG \\1 is above 3; measured growth does not support the current valuation.",
            ),
            (
                r"^年化波動率\s*([^%]+)%[，,]短線風險偏高$",
                "Annualized volatility is \\1%; short-term risk is elevated.",
            ),
            (r"^年化波動率\s*([^%]+)%$", "Annualized volatility is \\1%."),
            (
                r"^近四季\s*EPS\s*較前四季衰退\s*([^%]+)%$",
                "EPS for the latest four quarters declined \\1% from the previous four quarters.",
            ),
            (
                r"^Piotroski F-Score\s*僅\s*([^，,]+)[，,]財務體質需警惕$",
                "Piotroski F-Score is only \\1; financial quality warrants caution.",
            ),
            (
                r"^Piotroski F-Score\s*僅\s*([^，,]+)[，,]財務基本面偏弱$",
                "Piotroski F-Score is only \\1; financial fundamentals appear weak.",
            ),
            (
                r"^Altman Z-Score\s*([^，,]+)[，,]財務結構需警惕$",
                "Altman Z-Score \\1 indicates the financial structure warrants caution.",
            ),
            (
                r"^Altman Z-Score\s*([^，,]+)[，,]財務結構處於灰色地帶$",
                "Altman Z-Score \\1 is in the reference gray zone.",
            ),
            (
                r"^Altman Z-Score\s*([^，,]+)[，,]財務結構穩健$",
                "Altman Z-Score \\1 suggests a resilient financial structure.",
            ),
            (
                r"^股價\s*([^\s]+)\s*顯著高於\s*Graham Number\s*([^，,]+)[，,]價值投資角度偏貴$",
                "Market price \\1 is materially above Graham Number \\2; it appears expensive under this value reference.",
            ),
            (
                r"^綜合健康度僅\s*([^\s]+)\s*分[，,]整體表現偏弱$",
                "Overall fundamental health is only \\1 points; the broad result appears weak.",
            ),
        )
        for pattern, replacement in patterns:
            if re.fullmatch(pattern, message):
                return re.sub(pattern, replacement, message)
        if self._has_cjk_text(message):
            logger.warning("Untranslated system-generated risk message: %s", message)
            return "A system-generated screening signal is present; review the related metrics and disclosures."
        return message

    def _english_analysis_narrative(self, value: Dict[str, Any]) -> str:
        """Build the narrative from structured results instead of printing Chinese text.

        The valuation analyser intentionally remains Chinese-first for the
        Traditional Chinese UI.  Rebuilding this report-only summary from its
        structured output gives English PDFs the same analytical coverage while
        preserving source-provided text elsewhere in the report.
        """
        existing = str(value.get("analysis_text") or "").strip()
        if existing and not self._has_cjk_text(existing):
            return existing

        fair = value.get("fair_price_range") or {}
        health = value.get("health_score") or {}
        overall = value.get("overall_rating") or {}
        quality = value.get("quality_score") or {}
        peg = value.get("peg") or {}
        revenue = value.get("revenue_growth") or {}
        margin = value.get("margin_of_safety") or {}
        warnings = value.get("risk_warnings") or []
        lines = [f"{self._english_name()} valuation analysis"]

        overall_score = overall.get("score")
        if overall_score is None:
            lines.append(
                f"Overall rating: Insufficient data (coverage {float(overall.get('coverage') or 0) * 100:.0f}%)."
            )
        elif overall.get("rating"):
            lines.append(
                f"Overall rating: {overall['rating']} ({overall_score} points)."
            )

        health_score = health.get("total_score")
        if health_score is None:
            lines.append(
                f"Fundamental health score: Insufficient data (coverage {float(health.get('coverage') or 0) * 100:.0f}%)."
            )
        else:
            lines.append(
                f"Fundamental health score: {health_score} points ({self._english_health_level(health.get('level'))})."
            )

        piotroski = quality.get("piotroski_f_score")
        pi_details = quality.get("piotroski_details") or {}
        if piotroski is None:
            lines.append(
                f"Piotroski F-Score: Insufficient data ({pi_details.get('available_count', 0)} of 9 signals available)."
            )
        else:
            lines.append(f"Piotroski F-Score: {piotroski}/9.")

        graham = quality.get("graham_number")
        current_price = fair.get("current_price")
        if isinstance(graham, (int, float)):
            graham_text = f"Graham Number: TWD {graham:,.2f}."
            if isinstance(current_price, (int, float)):
                if current_price < graham:
                    graham_text = f"Graham Number: TWD {graham:,.2f}; the current price is below this value reference."
                else:
                    graham_text = f"Graham Number: TWD {graham:,.2f}; the current price is above this value reference."
            lines.append(graham_text)

        if all(fair.get(key) is not None for key in ("cheap", "fair", "expensive")):
            cheap, fair_value, expensive = (
                fair["cheap"],
                fair["fair"],
                fair["expensive"],
            )
            lines.append(
                f"Valuation references (lower / central / upper): {cheap:.0f} / {fair_value:.0f} / {expensive:.0f}."
            )
            if isinstance(current_price, (int, float)):
                if current_price <= cheap:
                    zone = "at or below the lower reference"
                elif current_price <= fair_value:
                    zone = "between the lower and central references"
                elif current_price <= expensive:
                    zone = "between the central and upper references"
                else:
                    zone = "above the upper reference"
                lines.append(f"Current price {current_price:.0f} is {zone}.")

        current_pe = fair.get("current_pe")
        median_pe = fair.get("pe_p50")
        if isinstance(current_pe, (int, float)) and isinstance(median_pe, (int, float)):
            if current_pe < median_pe * 0.9:
                assessment = "relatively low"
            elif current_pe > median_pe * 1.1:
                assessment = "relatively high"
            else:
                assessment = "close to the historical median"
            lines.append(
                f"P/E {current_pe} versus historical median {median_pe}: {assessment}."
            )

        peg_value = peg.get("peg")
        if isinstance(peg_value, (int, float)):
            if peg_value < 1:
                peg_assessment = (
                    "growth is sufficient to support the P/E under this reference"
                )
            elif peg_value <= 2:
                peg_assessment = (
                    "growth and valuation are broadly aligned under this reference"
                )
            else:
                peg_assessment = (
                    "review whether growth can continue to support valuation"
                )
            lines.append(f"PEG {peg_value}: {peg_assessment}.")

        recent_yoy = revenue.get("avg_recent_yoy_pct")
        if isinstance(recent_yoy, (int, float)):
            if recent_yoy > 20:
                assessment = "strong growth momentum"
            elif recent_yoy > 5:
                assessment = "steady growth"
            elif recent_yoy > -5:
                assessment = "broadly flat revenue"
            else:
                assessment = "revenue contraction that warrants attention"
            lines.append(
                f"Recent average revenue year-over-year growth: {recent_yoy}% ({assessment})."
            )
        if revenue.get("accelerating"):
            lines.append("Revenue momentum is strengthening.")
        elif revenue.get("decelerating"):
            lines.append(
                "Revenue momentum is slowing; assess whether this is temporary."
            )
        positive_months = revenue.get("consecutive_positive_months")
        if isinstance(positive_months, int) and positive_months >= 6:
            lines.append(
                f"Revenue grew year over year for {positive_months} consecutive months."
            )

        margin_pct = margin.get("margin_of_safety_pct")
        if isinstance(margin_pct, (int, float)):
            if margin_pct > 0:
                lines.append(
                    f"The central valuation reference is {margin_pct}% above the current price."
                )
            else:
                lines.append(
                    f"The current price is {abs(margin_pct)}% above the central valuation reference."
                )

        red = [warning for warning in warnings if warning.get("level") == "red"]
        yellow = [warning for warning in warnings if warning.get("level") == "yellow"]
        if red:
            categories = ", ".join(
                self._english_risk_category(warning.get("type")) for warning in red
            )
            lines.append(
                f"Risk alert: {len(red)} red signal(s) ({categories}); review carefully."
            )
        if yellow:
            categories = ", ".join(
                self._english_risk_category(warning.get("type")) for warning in yellow
            )
            lines.append(f"Watch list: {len(yellow)} yellow signal(s) ({categories}).")
        return "\n".join(lines)

    def _add_english_title_page(self):
        self.pdf.add_page()
        self.pdf.ln(48)
        self.pdf.set_text_color(18, 48, 71)
        self._font("B", 26)
        self.pdf.cell(
            0,
            15,
            "Taiwan Security Research Report",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.pdf.ln(12)
        self._font("B", 18)
        self._multi_cell(
            0,
            10,
            f"{self._english_name()} ({self.stock_info.get('stock_id', '-')})",
            align="C",
        )
        self.pdf.ln(18)
        self._font("", 12)
        self.pdf.set_text_color(90, 90, 90)
        self.pdf.cell(
            0,
            8,
            f"Generated on {datetime.now():%Y-%m-%d}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.pdf.ln(8)
        self._multi_cell(
            0,
            6,
            "Automatically generated for research and education. It is not investment advice.",
            align="C",
        )
        self.pdf.set_text_color(0, 0, 0)

    def _add_english_profile(self):
        self.pdf.add_page()
        self._section_title("Security Profile")
        info = self.stock_info
        market_map = {
            "上市": "TWSE listed",
            "上櫃": "TPEx listed",
            "興櫃": "Emerging market",
        }
        fields = [
            ("Ticker", info.get("stock_id", "-")),
            ("Security name", self._english_name()),
            ("Market", market_map.get(info.get("market"), "Taiwan market")),
            ("Asset type", "ETF" if info.get("is_etf") else "Equity"),
            (
                "Industry / category",
                str(info.get("industry") or info.get("category") or "Unavailable"),
            ),
        ]
        if info.get("current_price") is not None:
            fields.append(("Reference price", f"TWD {info['current_price']:.2f}"))
        if info.get("nav_price") is not None:
            fields.append(("NAV", f"TWD {info['nav_price']:.2f}"))
        if info.get("total_assets") is not None:
            fields.append(
                ("Assets under management", f"TWD {info['total_assets']:,.0f}")
            )
        for label, key in (
            ("52-week high", "fiftyTwoWeekHigh"),
            ("52-week low", "fiftyTwoWeekLow"),
            ("Market capitalization", "marketCap"),
            ("Trailing P/E", "trailingPE"),
            ("Price-to-book", "priceToBook"),
        ):
            item = (
                self.price_info.get(key) if isinstance(self.price_info, dict) else None
            )
            if item is not None:
                fields.append(
                    (
                        label,
                        f"TWD {item:,.2f}"
                        if key in {"fiftyTwoWeekHigh", "fiftyTwoWeekLow", "marketCap"}
                        and isinstance(item, (int, float))
                        else str(item),
                    )
                )
        for index, (label, value) in enumerate(fields):
            self.pdf.set_fill_color(245, 250, 255 if index % 2 == 0 else 255)
            self._font("B", 11)
            self.pdf.cell(56, 10, label, fill=True)
            self._font("", 11)
            self.pdf.cell(0, 10, str(value), new_x="LMARGIN", new_y="NEXT", fill=True)
        description = str(info.get("description") or "")
        if description and not info.get("is_etf"):
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(
                0, 7, "Company description (source text)", new_x="LMARGIN", new_y="NEXT"
            )
            self._font("", 9)
            self._multi_cell(
                0, 6, description[:700] + ("..." if len(description) > 700 else "")
            )

    def _add_english_analysis(self):
        self.pdf.add_page()
        self._section_title("Market and Fundamentals")
        self._font("B", 13)
        self.pdf.cell(0, 8, "Price overview", new_x="LMARGIN", new_y="NEXT")
        self._font("", 10)
        price_1y = self.price_data.get("1y", {})
        if price_1y.get("high") or price_1y.get("low"):
            high = price_1y.get("high") or {}
            low = price_1y.get("low") or {}
            self._multi_cell(
                0,
                6,
                f"One-year high: {high.get('price', 'N/A')} ({high.get('date', 'N/A')}). One-year low: {low.get('price', 'N/A')} ({low.get('date', 'N/A')}).",
            )
        else:
            self._multi_cell(0, 6, "Price history was not available for this report.")
        price_chart = price_1y.get("chart")
        if price_chart and os.path.exists(price_chart):
            self.pdf.image(price_chart, x=14, w=175)
        if not self.stock_info.get("is_etf"):
            self.pdf.ln(5)
            self._font("B", 13)
            self.pdf.cell(0, 8, "Revenue and earnings", new_x="LMARGIN", new_y="NEXT")
            self._font("", 10)
            latest_revenue = self.revenue_data[-1] if self.revenue_data else {}
            latest_eps = self.eps_data[-1] if self.eps_data else {}
            revenue_text = "No monthly revenue record was available."
            if latest_revenue:
                revenue_text = f"Latest monthly revenue period: {latest_revenue.get('year')}-{latest_revenue.get('month', 0):02d}. Year-over-year change: {latest_revenue.get('yoy', 'N/A')}%."
            eps_text = "No quarterly EPS record was available."
            if latest_eps:
                eps_text = f"Latest reported EPS: {latest_eps.get('eps', 'N/A')} for {latest_eps.get('label', 'the latest quarter')} ."
            self._multi_cell(0, 6, f"{revenue_text}\n{eps_text}")
            for title, chart in [
                ("Monthly revenue trend", self.revenue_chart),
                ("Quarterly EPS trend", self.eps_chart),
            ]:
                if chart and os.path.exists(chart):
                    self.pdf.ln(3)
                    self._font("B", 11)
                    self.pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
                    self.pdf.image(chart, x=14, w=175)
        self.pdf.ln(5)
        self._font("B", 13)
        self.pdf.cell(0, 8, "Model status", new_x="LMARGIN", new_y="NEXT")
        growth = (self.model_assessments or {}).get("growth") or {}
        safety = (self.model_assessments or {}).get("safety") or {}
        self._font("", 10)
        self._multi_cell(
            0,
            6,
            f"Growth assessment status: {growth.get('status', 'unavailable')}. Financial safety assessment status: {safety.get('status', 'unavailable')}. Experimental results are not formal ratings unless independently validated.",
        )

    def _add_english_model_assessments(self):
        self.pdf.add_page()
        self._section_title("Model Estimates (Separate from Confirmed Data)")
        assessments = self.model_assessments or {}
        growth = assessments.get("growth") or {}
        safety = assessments.get("safety") or {}
        rows = [
            ("Growth target", "Next rolling 12-month revenue growth"),
            ("Formal growth rating", growth.get("rating") or "Not validated"),
            (
                "Growth reference tier",
                growth.get("reference_rating")
                or growth.get("experimental_rating")
                or "Not available",
            ),
            (
                "Experimental growth grade",
                growth.get("experimental_rating") or "Not available",
            ),
            (
                "Growth estimate",
                f"{growth.get('prediction_pct')}%"
                if growth.get("prediction_pct") is not None
                else "Not available",
            ),
            ("Growth status", growth.get("status") or "Unavailable"),
            ("Formal financial-safety rating", safety.get("rating") or "Not validated"),
            (
                "Financial-structure reference tier",
                safety.get("reference_rating") or "Not available",
            ),
            (
                "Experimental safety grade",
                safety.get("experimental_rating") or "Not available",
            ),
            (
                "Financial-safety score",
                str(
                    safety.get("score")
                    if safety.get("score") is not None
                    else "Not available"
                ),
            ),
            ("Financial-safety status", safety.get("status") or "Unavailable"),
        ]
        self._render_table((78, 112), rows, font_size=9)
        self.pdf.ln(4)
        self._font("", 10)
        self._multi_cell(
            0,
            6,
            "Formal ratings remain blank until pre-defined historical validation gates are passed. Displayed reference tiers are transparent research/education outputs, not investment recommendations, credit ratings, or bankruptcy probabilities.",
        )
        growth_formula = growth.get("formula") or {}
        safety_formula = safety.get("formula") or {}
        if growth_formula.get("raw_equation"):
            self.pdf.ln(3)
            self._font("B", 10)
            self.pdf.cell(
                0, 6, "Growth calculation formula", new_x="LMARGIN", new_y="NEXT"
            )
            self._font("", 8)
            self._multi_cell(0, 5, growth_formula["raw_equation"])
            self._multi_cell(0, 5, growth_formula.get("prediction_equation", ""))
        if safety_formula.get("equation"):
            self.pdf.ln(3)
            self._font("B", 10)
            self.pdf.cell(
                0,
                6,
                "Financial-structure reference formula",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            self._font("", 8)
            self._multi_cell(0, 5, safety_formula["equation"])
            self._multi_cell(
                0,
                5,
                "Reference only: this is not a Taiwan bankruptcy probability, credit rating, or investment recommendation.",
            )

    def _add_english_price_section(self):
        self.pdf.add_page()
        self._section_title("Price Trend")
        price_1y = self.price_data.get("1y", {})
        high, low = price_1y.get("high") or {}, price_1y.get("low") or {}
        self._render_table(
            (78, 112),
            [
                (
                    "Reference price",
                    f"TWD {self.stock_info.get('current_price'):.2f}"
                    if self.stock_info.get("current_price") is not None
                    else "Unavailable",
                ),
                (
                    "One-year high",
                    f"{high.get('price', 'N/A')} ({high.get('date', 'N/A')})",
                ),
                (
                    "One-year low",
                    f"{low.get('price', 'N/A')} ({low.get('date', 'N/A')})",
                ),
            ],
        )
        chart = price_1y.get("chart")
        if chart and os.path.exists(chart):
            self.pdf.ln(4)
            self.pdf.image(chart, x=14, w=175)
        else:
            self.pdf.ln(5)
            self._multi_cell(
                0, 6, "Price chart data was not available for this report."
            )

    def _add_english_revenue_section(self):
        self.pdf.add_page()
        self._section_title("Two-Year Revenue Analysis")
        latest = self.revenue_data[-1] if self.revenue_data else {}
        self._render_table(
            (78, 112),
            [
                (
                    "Latest period",
                    f"{latest.get('year', 'N/A')}-{latest.get('month', 'N/A')}",
                ),
                ("Latest revenue", str(latest.get("revenue", "Unavailable"))),
                (
                    "Year-over-year change",
                    f"{latest.get('yoy')}%"
                    if latest.get("yoy") is not None
                    else "Unavailable",
                ),
                (
                    "Month-over-month change",
                    f"{latest.get('mom')}%"
                    if latest.get("mom") is not None
                    else "Unavailable",
                ),
            ],
        )
        if self.revenue_chart and os.path.exists(self.revenue_chart):
            self.pdf.ln(4)
            self.pdf.image(self.revenue_chart, x=14, w=175)
        if self.revenue_data:
            self.pdf.ln(3)
            self._font("B", 10)
            self.pdf.cell(0, 7, "Recent monthly records", new_x="LMARGIN", new_y="NEXT")
            headers = [
                ("Period", 30),
                ("Revenue", 45),
                ("MoM", 30),
                ("YoY", 30),
                ("Source", 45),
            ]
            self._font("B", 8)
            for header, width in headers:
                self.pdf.cell(width, 7, header, border=1, align="C")
            self.pdf.ln()
            self._font("", 8)
            for item in reversed(self.revenue_data[-6:]):
                period = (
                    f"{item.get('year', 'N/A')}-{int(item.get('month', 0) or 0):02d}"
                )
                revenue = item.get("revenue")
                values = [
                    period,
                    f"TWD {float(revenue):,.0f}"
                    if isinstance(revenue, (int, float))
                    else "Unavailable",
                    f"{float(item['mom']):+.1f}%"
                    if isinstance(item.get("mom"), (int, float))
                    else "Unavailable",
                    f"{float(item['yoy']):+.1f}%"
                    if isinstance(item.get("yoy"), (int, float))
                    else "Unavailable",
                    str(item.get("source") or "Unavailable")[:22],
                ]
                for value, (_, width) in zip(values, headers):
                    self.pdf.cell(width, 6, value, border=1)
                self.pdf.ln()
            yoy_values = [
                item.get("yoy")
                for item in self.revenue_data
                if isinstance(item.get("yoy"), (int, float))
            ]
            if yoy_values:
                recent_yoy = yoy_values[-3:]
                self.pdf.ln(2)
                self._multi_cell(
                    0,
                    6,
                    f"Average YoY change across available records: {sum(yoy_values) / len(yoy_values):+.1f}%. "
                    f"Average across the latest {len(recent_yoy)} reported months: {sum(recent_yoy) / len(recent_yoy):+.1f}%.",
                )
        self.pdf.ln(3)
        self._multi_cell(
            0,
            6,
            "Revenue growth is an operating-data observation. It does not by itself predict profit, price return, or a buy/sell outcome.",
        )

    def _add_english_eps_section(self):
        self.pdf.add_page()
        self._section_title("EPS (Earnings per Share) Analysis")
        latest = self.eps_data[-1] if self.eps_data else {}
        self._render_table(
            (78, 112),
            [
                ("Latest period", str(latest.get("label") or "Unavailable")),
                ("Latest EPS", str(latest.get("eps", "Unavailable"))),
                ("Data source", str(latest.get("source") or "Unavailable")),
            ],
        )
        if self.eps_chart and os.path.exists(self.eps_chart):
            self.pdf.ln(4)
            self.pdf.image(self.eps_chart, x=14, w=175)
        if self.eps_data:
            self.pdf.ln(3)
            self._font("B", 10)
            self.pdf.cell(0, 7, "Reported quarterly EPS", new_x="LMARGIN", new_y="NEXT")
            headers = [
                ("Period", 48),
                ("EPS (TWD)", 40),
                ("Change from prior record", 50),
                ("Source", 42),
            ]
            self._font("B", 8)
            for header, width in headers:
                self.pdf.cell(width, 7, header, border=1, align="C")
            self.pdf.ln()
            self._font("", 8)
            records = self.eps_data[-8:]
            for index, item in enumerate(records):
                eps = item.get("eps")
                prior = records[index - 1].get("eps") if index else None
                change = (
                    f"{float(eps) - float(prior):+.2f}"
                    if isinstance(eps, (int, float)) and isinstance(prior, (int, float))
                    else "-"
                )
                values = [
                    str(item.get("label") or "Unavailable"),
                    f"{float(eps):.2f}"
                    if isinstance(eps, (int, float))
                    else "Unavailable",
                    change,
                    str(item.get("source") or "Unavailable")[:20],
                ]
                for value, (_, width) in zip(values, headers):
                    self.pdf.cell(width, 6, value, border=1)
                self.pdf.ln()
            eps_values = [
                item.get("eps")
                for item in records
                if isinstance(item.get("eps"), (int, float))
            ]
            if len(eps_values) >= 2:
                direction = (
                    "increased"
                    if eps_values[-1] > eps_values[0]
                    else "decreased"
                    if eps_values[-1] < eps_values[0]
                    else "was unchanged"
                )
                self.pdf.ln(2)
                self._multi_cell(
                    0,
                    6,
                    f"Across the displayed reported records, EPS {direction} from {eps_values[0]:.2f} to {eps_values[-1]:.2f}.",
                )
        self.pdf.ln(3)
        self._multi_cell(
            0,
            6,
            "EPS is historical reported earnings per share. It is not a forecast of future EPS or market price.",
        )

    def _add_english_valuation_section(self):
        self.pdf.add_page()
        is_etf = self.stock_info.get("is_etf", False)
        self._section_title("ETF Structure" if is_etf else "Valuation Analysis")
        if is_etf:
            info = self.stock_info
            rows = [
                ("NAV", str(info.get("nav_price", "Unavailable"))),
                ("Premium / discount", str(info.get("premium_pct", "Unavailable"))),
                ("Expense ratio", str(info.get("expense_ratio", "Unavailable"))),
                (
                    "Assets under management",
                    str(info.get("total_assets", "Unavailable")),
                ),
                ("Tracking index", str(info.get("tracking_index", "Unavailable"))),
            ]
            self._render_table((78, 112), rows)
            self._multi_cell(
                0,
                6,
                "ETF company-style revenue and EPS metrics are not applicable. NAV, premium/discount, costs, liquidity, and the tracked index answer different questions.",
            )
            return
        value = self.valuation_analysis or {}
        fair = value.get("fair_price_range") or {}
        rows = [
            ("Current P/E", str(fair.get("current_pe", "Unavailable"))),
            ("Lower valuation reference", str(fair.get("cheap", "Unavailable"))),
            ("Fair-value reference", str(fair.get("fair", "Unavailable"))),
            ("Upper valuation reference", str(fair.get("expensive", "Unavailable"))),
            (
                "Margin-of-safety reference (0.8x)",
                str(fair.get("margin_safety_8", "Unavailable")),
            ),
            ("TTM EPS used", str(fair.get("ttm_eps", "Unavailable"))),
        ]
        self._render_table((78, 112), rows)
        percentile_rows = [
            ("Historical P/E 25th percentile", str(fair.get("pe_p25", "Unavailable"))),
            ("Historical P/E median", str(fair.get("pe_p50", "Unavailable"))),
            ("Historical P/E 75th percentile", str(fair.get("pe_p75", "Unavailable"))),
            ("Historical P/E sample size", str(fair.get("sample_size", "Unavailable"))),
        ]
        if any(item[1] != "Unavailable" for item in percentile_rows):
            self.pdf.ln(3)
            self._font("B", 10)
            self.pdf.cell(
                0, 7, "Historical valuation inputs", new_x="LMARGIN", new_y="NEXT"
            )
            self._render_table((78, 112), percentile_rows, font_size=8)
        self._multi_cell(
            0,
            6,
            "Valuation references use available historical assumptions and are not target prices or guaranteed fair values.",
        )

    def _add_english_health_quality_section(self):
        """Render the health and quality detail that Chinese reports already include."""
        value = self.valuation_analysis or {}
        if not value or value.get("is_etf"):
            return
        health = value.get("health_score") or {}
        quality = value.get("quality_score") or {}
        overall = value.get("overall_rating") or {}
        if not (health or quality or overall):
            return

        self.pdf.add_page()
        self._section_title("Fundamental Health and Quality")
        health_rows = []
        if health:
            total = health.get("total_score")
            health_rows.extend(
                [
                    (
                        "Health score",
                        f"{total} / 100" if total is not None else "Insufficient data",
                    ),
                    ("Health level", self._english_health_level(health.get("level"))),
                    (
                        "Input coverage",
                        f"{float(health.get('coverage') or 0) * 100:.0f}%",
                    ),
                ]
            )
        if overall.get("rating"):
            score = overall.get("score")
            health_rows.append(
                (
                    "Existing overall research rating",
                    f"{overall['rating']}"
                    + (f" ({score} / 100)" if score is not None else ""),
                )
            )
        if health_rows:
            self._render_table((82, 108), health_rows)

        components = health.get("components") or {}
        if components:
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(
                0, 7, "Seven-dimension health detail", new_x="LMARGIN", new_y="NEXT"
            )
            labels = {
                "growth": "Growth",
                "valuation": "Valuation",
                "profitability": "Profitability",
                "quality": "Quality",
                "momentum": "Price momentum",
                "stability": "Stability",
                "cashflow": "Cash flow",
            }
            rows = []
            for key, item in components.items():
                score = item.get("score") if isinstance(item, dict) else None
                weight = item.get("weight", "-") if isinstance(item, dict) else "-"
                status = item.get("status", "") if isinstance(item, dict) else ""
                display = (
                    f"{score:.1f} / 100"
                    if isinstance(score, (int, float))
                    else "Insufficient data"
                )
                rows.append(
                    (
                        f"{labels.get(key, key)} (weight {weight})",
                        f"{display}; {status}".strip("; "),
                    )
                )
            self._render_table((105, 85), rows, font_size=8)

        self.pdf.ln(3)
        self._font("B", 11)
        self.pdf.cell(0, 7, "Quality models", new_x="LMARGIN", new_y="NEXT")
        piotroski = quality.get("piotroski_f_score")
        pi_details = quality.get("piotroski_details") or {}
        altman = quality.get("altman_z_score")
        graham = quality.get("graham_number")
        quality_rows = [
            (
                "Piotroski F-Score",
                f"{piotroski} / 9"
                if piotroski is not None
                else f"Insufficient data ({pi_details.get('available_count', 0)} / 9 signals)",
            ),
            (
                "Altman Z-Score",
                str(altman)
                if altman is not None
                else "Insufficient data or not applicable",
            ),
            (
                "Graham Number",
                f"TWD {float(graham):,.2f}"
                if isinstance(graham, (int, float))
                else "Unavailable",
            ),
        ]
        self._render_table((82, 108), quality_rows)
        self.pdf.ln(3)
        self._multi_cell(
            0,
            6,
            "Health, quality, valuation, growth, and financial-structure references answer different questions. They are not combined into a buy/sell conclusion.",
        )

    def _add_english_financial_metrics_section(self):
        """Show the financial fields and provenance omitted by the old English summary."""
        if self.stock_info.get("is_etf"):
            return
        fields = self.price_info if isinstance(self.price_info, dict) else {}
        snapshot = self.financial_snapshot or {}
        official_fields = snapshot.get("fields") or {}
        metric_keys = [
            ("Gross margin", "grossMargins", "percent"),
            ("Operating margin", "operatingMargins", "percent"),
            ("Profit margin", "profitMargins", "percent"),
            ("Return on equity", "returnOnEquity", "percent"),
            ("Return on assets", "returnOnAssets", "percent"),
            ("Debt to equity", "debtToEquity", "number"),
            ("Free cash flow", "freeCashflow", "currency"),
            ("Total cash", "totalCash", "currency"),
            ("Total debt", "totalDebt", "currency"),
            ("Book value per share", "bookValue", "currency"),
            ("Forward P/E", "forwardPE", "number"),
            ("Beta", "beta", "number"),
            ("52-week high", "fiftyTwoWeekHigh", "currency"),
            ("52-week low", "fiftyTwoWeekLow", "currency"),
        ]
        rows = []
        for label, key, kind in metric_keys:
            item = fields.get(key)
            if item is None:
                continue
            if kind == "percent" and isinstance(item, (int, float)):
                display = f"{item * 100:.2f}%"
            elif kind == "currency" and isinstance(item, (int, float)):
                display = f"TWD {item:,.2f}"
            elif isinstance(item, (int, float)):
                display = f"{item:,.2f}"
            else:
                display = str(item)
            rows.append((label, display))
        if not rows and not official_fields:
            return

        self.pdf.add_page()
        self._section_title("Financial Metrics and Data Sources")
        if rows:
            self._render_table((82, 108), rows, font_size=8)
        if official_fields:
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(
                0,
                7,
                "Latest official quarterly statement",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            period = snapshot.get("observed_at") or "Unavailable"
            source = snapshot.get("status") or "Unavailable"
            report_type = snapshot.get("report_type") or "Unavailable"
            self._render_table(
                (82, 108),
                [
                    ("Reported period", str(period)),
                    ("Official-source status", str(source)),
                    ("Statement format", str(report_type)),
                ],
                font_size=8,
            )
            label_map = {
                "totalRevenue": "Revenue",
                "operatingIncome": "Operating income",
                "netIncomeToCommon": "Net income attributable to common shareholders",
                "totalAssets": "Total assets",
                "currentAssets": "Current assets",
                "currentLiabilities": "Current liabilities",
                "retainedEarnings": "Retained earnings",
                "totalLiabilities": "Total liabilities",
                "stockholdersEquity": "Stockholders' equity",
            }
            statement_rows = []
            for key, label in label_map.items():
                item = official_fields.get(key)
                if item is not None:
                    statement_rows.append(
                        (
                            label,
                            f"TWD {float(item):,.0f}"
                            if isinstance(item, (int, float))
                            else str(item),
                        )
                    )
            if statement_rows:
                self.pdf.ln(2)
                self._render_table((112, 78), statement_rows, font_size=8)
        self.pdf.ln(3)
        self._multi_cell(
            0,
            6,
            "Financial values can be delayed, revised, or unavailable. Source and period must be considered before comparing companies or making a decision.",
        )

    def _add_english_risk_analysis_section(self):
        """Render risk warnings, PEG, revenue trend, and narrative analysis in English."""
        value = self.valuation_analysis or {}
        if not value or value.get("is_etf"):
            return
        warnings = value.get("risk_warnings") or []
        peg = value.get("peg") or {}
        revenue = value.get("revenue_growth") or {}
        narrative = value.get("analysis_text")
        if not (warnings or peg or revenue or narrative):
            return

        self.pdf.add_page()
        self._section_title("Risk Signals and Analysis Notes")
        if peg:
            self._font("B", 11)
            self.pdf.cell(0, 7, "PEG context", new_x="LMARGIN", new_y="NEXT")
            rows = [
                (
                    "PEG",
                    str(
                        peg.get("peg") if peg.get("peg") is not None else "Unavailable"
                    ),
                ),
                (
                    "P/E used",
                    str(peg.get("pe") if peg.get("pe") is not None else "Unavailable"),
                ),
                (
                    "EPS growth used",
                    f"{peg.get('eps_growth_pct')}%"
                    if peg.get("eps_growth_pct") is not None
                    else "Unavailable",
                ),
                ("Interpretation", self._english_risk_message(peg.get("verdict"))),
            ]
            self._render_table((82, 108), rows, font_size=8)
        if revenue:
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(0, 7, "Revenue-trend context", new_x="LMARGIN", new_y="NEXT")
            rows = [
                (
                    "Recent average YoY growth",
                    f"{revenue.get('avg_recent_yoy_pct')}%"
                    if revenue.get("avg_recent_yoy_pct") is not None
                    else "Unavailable",
                ),
                (
                    "Positive-growth months",
                    str(revenue.get("consecutive_positive_months", "Unavailable")),
                ),
                (
                    "Negative-growth months",
                    str(revenue.get("consecutive_negative_months", "Unavailable")),
                ),
                (
                    "Acceleration flag",
                    "Yes"
                    if revenue.get("accelerating")
                    else "No"
                    if revenue.get("decelerating")
                    else "Not indicated",
                ),
            ]
            self._render_table((82, 108), rows, font_size=8)
        if warnings:
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(0, 7, "Risk signals", new_x="LMARGIN", new_y="NEXT")
            for warning in warnings:
                level = str(warning.get("level") or "info").upper()
                message = self._english_risk_message(warning.get("msg"))
                horizon = self._english_risk_horizon(warning.get("horizon"))
                category = self._english_risk_category(warning.get("type"))
                self._multi_cell(
                    0, 6, f"[{level}] {category} {horizon}: {message}".strip()
                )
        if narrative or value:
            self.pdf.ln(3)
            self._font("B", 11)
            self.pdf.cell(0, 7, "Analysis narrative", new_x="LMARGIN", new_y="NEXT")
            self._font("", 9)
            self._multi_cell(0, 6, self._english_analysis_narrative(value))
        self.pdf.ln(3)
        self._multi_cell(
            0,
            6,
            "Risk signals and narrative are screening aids based on available data. They do not predict market price or guarantee an outcome.",
        )

    def _add_english_peers_section(self):
        self.pdf.add_page()
        self._section_title("Peer Reference")
        peers = self.peers_data or []
        if not peers:
            self._multi_cell(0, 6, "No comparable peer data was available.")
            return
        self._font("B", 9)
        for header, width in [
            ("Ticker", 28),
            ("Name", 62),
            ("Price", 30),
            ("P/E", 25),
            ("Yield", 25),
        ]:
            self.pdf.cell(width, 7, header, border=1, align="C")
        self.pdf.ln()
        self._font("", 8)
        for peer in peers[:8]:
            values = [
                peer.get("stock_id", "-"),
                peer.get("name", "-"),
                str(peer.get("price", "-")),
                str(peer.get("pe", "-")),
                str(peer.get("dividend_yield", "-")),
            ]
            for value, width in zip(values, [28, 62, 30, 25, 25]):
                self.pdf.cell(width, 7, str(value)[:28], border=1)
            self.pdf.ln()
        self.pdf.ln(3)
        self._multi_cell(
            0,
            6,
            "Peer reference is a comparison aid, not a statement that securities have identical business risk or return potential.",
        )

    def _add_english_dividend_section(self):
        self.pdf.add_page()
        self._section_title("Dividend Analysis")
        dividend = self.dividend_data or {}
        self._render_table(
            (78, 112),
            [
                (
                    "Full-year dividend yield",
                    str(
                        dividend.get(
                            "yield", dividend.get("latest_yield", "Unavailable")
                        )
                    ),
                ),
                (
                    "Consecutive dividend years",
                    str(dividend.get("consecutive_years", "Unavailable")),
                ),
                (
                    "Latest completed year",
                    str(dividend.get("last_completed_year", "Unavailable")),
                ),
                (
                    "Three-year average yield",
                    str(dividend.get("avg_yield_3y", "Unavailable")),
                ),
                (
                    "Ex-dividend reference date",
                    str(dividend.get("ex_dividend_date", "Unavailable")),
                ),
                (
                    "Historical dividend months",
                    ", ".join(
                        str(item) for item in (dividend.get("dividend_months") or [])
                    )
                    or "Unavailable",
                ),
            ],
        )
        history = dividend.get("history") or []
        if history:
            self.pdf.ln(3)
            self._font("B", 10)
            self.pdf.cell(
                0, 7, "Recent dividend history", new_x="LMARGIN", new_y="NEXT"
            )
            self._font("B", 8)
            self.pdf.cell(50, 7, "Year", border=1, align="C")
            self.pdf.cell(50, 7, "Dividend per share (TWD)", border=1, align="C")
            self.pdf.cell(50, 7, "Record status", border=1, align="C")
            self.pdf.ln()
            self._font("", 8)
            for item in history[:8]:
                year = str(item.get("year") or "Unavailable")
                amount = item.get("dividend")
                status = str(item.get("status") or "completed")
                self.pdf.cell(50, 6, year, border=1)
                self.pdf.cell(
                    50,
                    6,
                    f"{float(amount):.2f}"
                    if isinstance(amount, (int, float))
                    else "Unavailable",
                    border=1,
                )
                self.pdf.cell(50, 6, status, border=1)
                self.pdf.ln()
        self._multi_cell(
            0,
            6,
            "Dividend history is historical information. It does not guarantee the amount, timing, or continuation of future distributions.",
        )

    def _add_english_news_section(self):
        self.pdf.add_page()
        self._section_title("Public News Summary")
        items = (self.news_data or {}).get("items", [])
        analysis_summary = (self.news_data or {}).get("analysis_summary")
        if analysis_summary:
            self._font("B", 11)
            self.pdf.cell(0, 7, "Source-backed summary", new_x="LMARGIN", new_y="NEXT")
            self._font("", 10)
            self._multi_cell(0, 6, str(analysis_summary))
            self.pdf.ln(3)
        if not items:
            self._multi_cell(
                0,
                6,
                "No verifiable public-news items were available. News classification is a keyword rule, not an investment signal.",
            )
            return
        self._font("", 9)
        for item in items[:10]:
            # Analysis passes NewsItem dataclasses here, while callers that
            # reconstruct a report from JSON may provide dictionaries.
            # Support both forms so English report generation cannot fail on
            # the normal in-memory pipeline.
            if isinstance(item, dict):
                title = str(item.get("title") or "Untitled public-news item")
                source = str(item.get("source") or "Source unavailable")
                date = str(
                    item.get("date") or item.get("publish_date") or "Date unavailable"
                )
            else:
                title = str(getattr(item, "title", "") or "Untitled public-news item")
                source = str(getattr(item, "source", "") or "Source unavailable")
                date = str(getattr(item, "publish_date", "") or "Date unavailable")
            summary = (
                str(item.get("summary") or "")
                if isinstance(item, dict)
                else str(getattr(item, "summary", "") or "")
            )
            self._font("B", 9)
            self._multi_cell(0, 5, f"• {title}")
            self._font("", 8)
            self._multi_cell(0, 5, f"  {source} · {date}")
            if summary:
                self._multi_cell(0, 5, f"  {summary}")
            self.pdf.ln(2)

    def _add_english_glossary(self):
        self.pdf.add_page()
        self._section_title("Key Terms")
        entries = [
            (
                "P/E",
                "Share price divided by earnings per share; it is not a complete measure of value.",
            ),
            ("EPS", "Reported earnings attributable to each share."),
            ("YoY", "Change compared with the same period one year earlier."),
            ("MoM", "Change compared with the immediately preceding month."),
            (
                "TTM",
                "The trailing twelve months; a rolling historical period rather than a forecast.",
            ),
            (
                "NAV",
                "ETF net asset value per unit, which can differ from market price.",
            ),
            ("Premium / discount", "The difference between ETF market price and NAV."),
            (
                "Data coverage",
                "How much required input data was actually available for a calculation.",
            ),
            (
                "Free cash flow",
                "Cash remaining after operating and capital expenditures; it is not the same as profit.",
            ),
            (
                "ROE",
                "Return on equity: a profitability ratio relative to shareholders' equity.",
            ),
            (
                "ROA",
                "Return on assets: a profitability ratio relative to total assets.",
            ),
            (
                "Piotroski F-Score",
                "A nine-signal historical quality screen; incomplete data must not be treated as a score.",
            ),
            (
                "Altman Z-Score",
                "A classic financial-structure formula with limited applicability; it is not a Taiwan bankruptcy probability.",
            ),
            (
                "Growth reference tier",
                "A research/education tier based on the revenue-growth model estimate and empirical positive-growth likelihood.",
            ),
            (
                "Financial-structure reference tier",
                "A transparent A/C/E reference from available financial data, not a credit rating or investment recommendation.",
            ),
        ]
        for term, definition in entries:
            self._font("B", 11)
            self.pdf.cell(0, 7, term, new_x="LMARGIN", new_y="NEXT")
            self._font("", 10)
            self._multi_cell(0, 6, definition)
            self.pdf.ln(2)

    def _add_english_disclaimer(self):
        self.pdf.add_page()
        self._section_title("Method and Disclaimer")
        self._font("", 10)
        self._multi_cell(
            0,
            6,
            "This report combines official Taiwan market disclosures with clearly identified fallback sources where applicable. Data can be delayed, incomplete, revised, or unavailable. Valuation, growth, financial safety, and ETF structure address different questions and must not be combined into a single investment conclusion.",
        )
        self.pdf.ln(5)
        self._multi_cell(
            0,
            6,
            "This document is for research and education only. It is not an offer, recommendation, or solicitation to buy or sell any security. Verify material information with official disclosures before making an investment decision.",
        )

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
            year = r.get("year")
            month = r.get("month")
            if year is not None and month is not None:
                try:
                    return f"{year}/{int(month):02d}"
                except (TypeError, ValueError):
                    return f"{year}/{month}"
            return str(r.get("label") or "—")
        return "—"

    def _latest_eps_date(self):
        if self.eps_data:
            r = self.eps_data[-1]
            year = r.get("year")
            q = r.get("quarter", "")
            if year is not None:
                return f"{year} Q{q}" if q else str(year)
            return str(r.get("label") or "—")
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
        experimental_safety = safety.get("reference_rating") or safety.get(
            "experimental_rating"
        )
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
        if safety.get("reference_rating"):
            safety_label = (
                f"財務結構參考分級：{safety['reference_rating']}"
                f"（{safety.get('score_label', 'Z-ref')} {safety.get('score', 'N/A')}；"
                "研究／教育用途，非破產機率、信用評等或投資建議）"
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

        growth_formula = growth.get("formula") or {}
        safety_formula = safety.get("formula") or {}
        if growth_formula.get("raw_equation") or safety_formula.get("equation"):
            self.pdf.ln(4)
            self._font("B", 11)
            self.pdf.cell(0, 7, "指標計算公式（可追溯）", new_x="LMARGIN", new_y="NEXT")
            self._font("", 8)
            if growth_formula.get("raw_equation"):
                self._multi_cell(0, 5, f"成長性：{growth_formula['raw_equation']}")
                self._multi_cell(0, 5, growth_formula.get("prediction_equation", ""))
            if safety_formula.get("equation"):
                self._multi_cell(0, 5, f"財務結構參考：{safety_formula['equation']}")
                self._multi_cell(
                    0,
                    5,
                    "僅供研究與教學參考；不是台灣公司破產機率、信用評等或投資建議。",
                )

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
