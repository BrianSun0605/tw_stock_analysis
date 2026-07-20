import { byId, compactMoney, money, node, number, percentDecimal, percentPoint, present, replace, safeUrl } from "./dom.js";
import { isEnglish, t } from "./i18n.js";

const componentNames = {
  growth: "成長性", valuation: "估值", profitability: "獲利能力",
  quality: "品質力", momentum: "價格動能", stability: "穩定性", cashflow: "現金流",
};
const signalNames = { positive: "正向", negative: "負向", neutral: "中性" };
const assetTypeNames = {
  stock: "公司財務安全", tdr: "公司財務安全", etf: "ETF 結構安全",
  etn: "ETN 結構安全", reit: "REIT 結構安全", preferred_stock: "特別股財務安全",
};

function setText(id, value) { byId(id).textContent = t(String(value)); }
function L(zh, en) { return isEnglish() ? en : zh; }
function unit(value, zh, en) { return present(value) ? `${value} ${L(zh, en)}` : value; }
function metric(label, value, note) {
  const children = [node("dt", { text: t(String(label)) }), node("dd", { text: t(String(value)) })];
  if (note) children.push(node("small", { text: t(String(note)) }));
  return node("dl", { className: "metric" }, children);
}
function empty(text = "目前沒有可呈現的資料") { return node("p", { className: "empty-copy", text: t(text) }); }
function localizedRiskMessage(message) {
  if (!isEnglish()) return message;
  const value = String(message || "");
  let match = value.match(/^Altman Z-Score ([\d.]+)，財務結構(穩健|需警惕|處於灰色地帶)$/);
  if (match) {
    const meanings = { "穩健": "financial structure appears resilient", "需警惕": "financial structure needs caution", "處於灰色地帶": "financial structure is in the gray zone" };
    return `Altman Z-Score ${match[1]}; ${meanings[match[2]]}.`;
  }
  match = value.match(/^股價 ([\d.]+) 顯著高於 Graham Number ([\d.]+)，價值投資角度偏貴$/);
  if (match) return `Market price ${match[1]} is materially above the Graham Number ${match[2]}; it appears expensive under this value-investing reference.`;
  return t(value);
}

function renderHeader(data) {
  const stock = data.stock || {};
  const growth = data.model_assessments?.growth || {};
  const safety = data.model_assessments?.safety || {};
  setText("stockName", stock.name || "名稱資料不足");
  setText("stockEnglish", stock.name_en || "");
  setText("stockMeta", [stock.stock_id, t(stock.market || ""), t(stock.industry || "")].filter(Boolean).join(" · ") || "資料不足");
  setText("stockPrice", money(stock.current_price));
  const change = stock.day_change_pct;
  setText("stockChange", present(change) ? L(`單日 ${Number(change) >= 0 ? "+" : ""}${percentPoint(change)}`, `Daily ${Number(change) >= 0 ? "+" : ""}${percentPoint(change)}`) : "漲跌資料不足");
  byId("stockChange").className = present(change) ? (Number(change) >= 0 ? "positive" : "negative") : "";
  setText("priceDate", stock.price_date ? L(`價格日期 ${stock.price_date}`, `Price date ${stock.price_date}`) : "價格日期未提供");
  const setGrade = (prefix, assessment, fallbackText) => {
    const candidate = assessment.rating || assessment.reference_rating || assessment.experimental_rating;
    const grade = ["A", "B", "C", "D", "E", "F"].includes(candidate) ? candidate : "N/A";
    const isReference = !assessment.rating && grade !== "N/A";
    setText(`${prefix}RatingBadge`, grade);
    byId(`${prefix}RatingBadge`).className = `rating ${grade === "N/A" ? "n-a" : grade.toLowerCase()}`;
    setText(`${prefix}RatingText`, grade === "N/A" || isReference ? fallbackText : `${number(assessment.score, 1)} / 100`);
  };
  const growthReference = growth.reference_rating || growth.experimental_rating;
  const safetyReference = safety.reference_rating;
  setGrade("growth", growth, growthReference ? L(`參考 ${growthReference}`, `Reference ${growthReference}`) : "暫不評級");
  setText("growthRatingMeta", growth.rating ? L(`信心 ${growth.confidence || "未標示"}`, `Confidence ${growth.confidence || "not stated"}`) : growthReference ? L("參考分級；未完成正式歷史驗證", "Reference tier; formal historical validation pending") : "正式評級未通過驗證");
  setGrade("safety", safety, safety.status === "specialized_model_pending" ? "專用模型待建" : safetyReference ? L(`參考 ${safetyReference}`, `Reference ${safetyReference}`) : safety.reference_band ? L("公式參考", "Formula reference") : safety.experimental_rating ? L(`實驗 ${safety.experimental_rating}`, `Experimental ${safety.experimental_rating}`) : "暫不評級");
  setText("safetyRatingMeta", safety.rating ? L(`信心 ${safety.confidence || "未標示"}`, `Confidence ${safety.confidence || "not stated"}`) : safetyReference ? L("參考分級；非破產機率或信用評等", "Reference tier; not a bankruptcy probability or credit rating") : safety.reference_band ? L("尚未完成台灣歷史驗證", "Taiwan historical validation pending") : "正式評級尚未完成歷史驗證");
}

function renderQualityBanner(data) {
  const coverage = data.health_score?.coverage;
  const mapping = data.data_quality?.stock_mapping_source || "unknown";
  const banner = byId("qualityBanner");
  if (!present(coverage) || Number(coverage) < .7) {
    banner.className = "quality-banner warning";
    banner.textContent = L(`可用資料不足 70%，綜合分數不應作為判斷依據。股票清單：${mapping}。`, `Available data is below 70%; do not use the composite score as a conclusion. Security master: ${mapping}.`);
  } else {
    banner.className = "quality-banner";
    banner.textContent = L(`本次健康度資料覆蓋率 ${percentDecimal(coverage, 0)}；缺漏維度已標示為「資料不足」，未以零分代替。股票清單：${mapping}。`, `Health-data coverage is ${percentDecimal(coverage, 0)}; missing dimensions are marked as insufficient data, not treated as zero. Security master: ${mapping}.`);
  }
}

function renderFactsSummary(data) {
  const provenance = data.data_provenance || {};
  const quality = data.data_quality || {};
  const price = provenance.current_price || {};
  const latestRevenue = provenance.latest_revenue || {};
  const sourceText = [price.source, latestRevenue.source].filter(Boolean).join("／") || "來源未標示";
  const statusText = price.status === "fallback" ? "行情使用 Yahoo 備援" : price.status === "stale" ? "資料為舊快照" : "官方／可信資料";
  replace("factsSummary", [
    metric("標的與價格日期", `${data.stock?.stock_id || "—"} · ${data.stock?.price_date || "日期不足"}`),
    metric("主要資料來源", sourceText),
    metric("備援狀態", statusText),
    metric("缺漏狀態", present(quality.health_coverage) ? L(`健康資料覆蓋 ${percentDecimal(quality.health_coverage, 0)}`, `Health-data coverage ${percentDecimal(quality.health_coverage, 0)}`) : "核心資料不足"),
  ]);
}

function renderKpis(data) {
  const fair = data.fair_price || {};
  const health = data.health_score || {};
  const dividend = data.dividend || {};
  setText("kpiPe", present(fair.current_pe) ? unit(number(fair.current_pe), "倍", "x") : "資料不足");
  setText("kpiFair", money(fair.fair));
  setText("kpiHealth", present(health.score) ? `${number(health.score, 1)} / 100` : "資料不足");
  setText("kpiHealthLevel", health.level || "資料覆蓋門檻 70%");
  setText("kpiYield", percentPoint(dividend.yield));
  setText("kpiYieldBasis", dividend.last_completed_year ? L(`${dividend.last_completed_year} 完整年度`, `${dividend.last_completed_year} full year`) : "最近完整年度");
  setText("kpiRevenue", percentPoint(data.revenue?.latest_yoy));
  setText("kpiRevenuePeriod", data.revenue ? `${data.revenue.year}/${String(data.revenue.month).padStart(2, "0")}` : "—");
  setText("kpiEps", present(data.eps?.eps) ? unit(number(data.eps.eps), "元", "TWD") : "資料不足");
  setText("kpiEpsPeriod", data.eps ? `${data.eps.year} Q${data.eps.quarter}` : "—");
}

function setKpi(id, label, value, note) {
  setText(`kpi${id}Label`, label);
  setText(`kpi${id}`, value);
  setText(`kpi${id}${id === "Health" ? "Level" : id === "Yield" ? "Basis" : id === "Revenue" || id === "Eps" ? "Period" : "Basis"}`, note);
}

function setLearningTerm(cardId, term) {
  byId(cardId).querySelector("[data-learning-term]").dataset.learningTerm = term;
}

function applyAssetLayout(data) {
  const isEtf = Boolean(data.is_etf || data.stock?.asset_type === "etf");
  const setHidden = (id, hidden) => { byId(id).hidden = hidden; };
  setHidden("growthModelCard", isEtf);
  setHidden("healthPanel", isEtf);
  setHidden("financialPanel", isEtf);
  setHidden("peerPanel", isEtf);
  setHidden("qualityPanel", isEtf);
  setText("modelTitle", isEtf ? "ETF 結構與交易風險" : "預估與風險篩檢");
  setText("valuationEyebrow", isEtf ? "ETF STRUCTURE" : "VALUATION");
  setText("valuationTitle", isEtf ? "ETF 結構與交易指標" : "估值檢視");
  setText("valuationMethod", isEtf ? "不套用公司估值" : "歷史資料法");
  if (!isEtf) {
    setText("kpiValuationEyebrow", "PRICE & VALUE");
    setText("kpiValuationTitle", "價格與估值");
    setText("kpiValuationNote", "市場價格是否已反映公司獲利");
    setText("kpiFundamentalEyebrow", "BUSINESS HEALTH");
    setText("kpiFundamentalTitle", "公司體質與成長");
    setText("kpiFundamentalNote", "公司是否穩健，且營運是否正在成長");
    setText("kpiIncomeEyebrow", "INCOME");
    setText("kpiIncomeTitle", "收益");
    setText("kpiIncomeNote", "過去配息，不保證未來金額");
    setText("kpiPeLabel", "歷史本益比");
    setText("kpiPeBasis", "目前估計值");
    setText("kpiFairLabel", "合理價");
    setText("kpiFairBasis", "歷史 PE 分位法");
    setText("kpiHealthLabel", "健康度");
    setText("kpiYieldLabel", "股利殖利率");
    setText("kpiRevenueLabel", "近月營收 YoY");
    setText("kpiEpsLabel", "最新季 EPS");
    setLearningTerm("kpiPeCard", "pe");
    setLearningTerm("kpiFairCard", "fair_value");
    setLearningTerm("kpiHealthCard", "financial_health");
    setLearningTerm("kpiYieldCard", "yield");
    setLearningTerm("kpiRevenueCard", "revenue_yoy");
    setLearningTerm("kpiEpsCard", "eps");
    return false;
  }

  const etf = data.etf_data || {};
  setText("kpiValuationEyebrow", "MARKET & NAV");
  setText("kpiValuationTitle", "市價與淨值");
  setText("kpiValuationNote", "市價相對基金淨值的位置");
  setText("kpiFundamentalEyebrow", "FUND STRUCTURE");
  setText("kpiFundamentalTitle", "基金結構");
  setText("kpiFundamentalNote", "成本、規模與交易便利性");
  setText("kpiIncomeEyebrow", "INCOME");
  setText("kpiIncomeTitle", "交易與收益");
  setText("kpiIncomeNote", "配息紀錄與流動性，不保證未來報酬");
  setKpi("Pe", "NAV 淨值", money(etf.nav_price), "與市價比較");
  setKpi("Fair", "折溢價", percentPoint(etf.premium_pct), "市價相對 NAV");
  setKpi("Health", "費用率", percentDecimal(etf.expense_ratio, 3), "長期持有成本");
  setKpi("Yield", "完整年度殖利率", percentPoint(data.dividend?.yield ?? etf.etf_yield), data.dividend?.last_completed_year ? L(`${data.dividend.last_completed_year} 完整年度`, `${data.dividend.last_completed_year} full year`) : "資料不足不代表 0%");
  setKpi("Revenue", "管理資產 AUM", compactMoney(etf.total_assets), "基金規模，不是公司市值");
  setKpi("Eps", "日均成交量", present(etf.avg_volume) ? unit(number(etf.avg_volume, 0), "股", "shares") : "資料不足", "交易便利性，不代表報酬");
  setLearningTerm("kpiPeCard", "nav");
  setLearningTerm("kpiFairCard", "premium");
  setLearningTerm("kpiHealthCard", "expense");
  setLearningTerm("kpiYieldCard", "yield");
  setLearningTerm("kpiRevenueCard", "aum");
  setLearningTerm("kpiEpsCard", "volume");
  return true;
}

function renderValuation(data) {
  const fair = data.fair_price;
  if (data.is_etf || data.stock?.asset_type === "etf") {
    const etf = data.etf_data || {};
    return replace("fairMetrics", [
      metric("市價", money(data.stock?.current_price)),
      metric("NAV 淨值", money(etf.nav_price)),
      metric("折溢價", percentPoint(etf.premium_pct), "市價與 NAV 必須是同一時間點才可比較"),
      metric("費用率", percentDecimal(etf.expense_ratio, 3)),
      metric("管理資產 AUM", compactMoney(etf.total_assets), "基金規模，不是公司市值"),
      metric("日均成交量", present(etf.avg_volume) ? unit(number(etf.avg_volume, 0), "股", "shares") : "資料不足"),
      metric("追蹤指數", data.stock?.tracking_index || "官方主檔未提供", "追蹤標的可辨識，不代表成分股安全"),
    ]);
  }
  if (!fair) return replace("fairMetrics", empty("資料不足，未建立個股歷史本益比區間。"));
  replace("fairMetrics", [
    metric("便宜價", money(fair.cheap)), metric("合理價", money(fair.fair)), metric("昂貴價", money(fair.expensive)),
    metric("目前本益比", present(fair.current_pe) ? unit(number(fair.current_pe), "倍", "x") : "資料不足"),
    metric("EPS 成長", percentPoint(fair.eps_growth_pct), "需 8 季連續資料"),
    metric("歷史樣本數", present(fair.sample_size) ? unit(number(fair.sample_size, 0), "日", "days") : "資料不足", "至少 60 個交易日"),
  ]);
}

function renderHealth(data) {
  const health = data.health_score || {};
  setText("healthCoverage", present(health.coverage) ? L(`覆蓋率 ${percentDecimal(health.coverage, 0)}`, `Coverage ${percentDecimal(health.coverage, 0)}`) : L("覆蓋率 —", "Coverage —"));
  const rows = Object.entries(health.components || {}).map(([key, item]) => {
    const available = item?.status === "available" && present(item.score);
    return node("div", { className: `score-row${available ? "" : " unavailable"}` }, [
      node("div", { className: "score-label" }, [t(componentNames[key] || key), node("small", { text: L(`權重 ${item?.weight || "—"}`, `Weight ${item?.weight || "—"}`) })]),
      node("progress", { className: "score-track", max: "100", value: available ? Math.max(0, Math.min(100, Number(item.score))) : 0, "aria-label": L(`${componentNames[key] || key}分數`, `${t(componentNames[key] || key)} score`) }),
      node("div", { className: "score-value", text: available ? number(item.score, 1) : t("資料不足") }),
    ]);
  });
  replace("healthComponents", rows.length ? rows : empty());
}

function renderFinancials(data) {
  const f = data.financials || {};
  const definitions = [
    ["毛利率", percentDecimal(f.grossMargins)], ["營業利益率", percentDecimal(f.operatingMargins)],
    ["淨利率", percentDecimal(f.profitMargins)], ["ROE", percentDecimal(f.returnOnEquity)],
    ["ROA", percentDecimal(f.returnOnAssets)], ["負債權益比", present(f.debtToEquity) ? `${number(f.debtToEquity)}%` : "資料不足"],
    ["營收成長", percentDecimal(f.revenueGrowth)], ["盈餘成長", percentDecimal(f.earningsGrowth)],
    ["自由現金流", compactMoney(f.freeCashflow)], ["總現金", compactMoney(f.totalCash)],
    ["總負債", compactMoney(f.totalDebt)], ["每股淨值", money(f.bookValue)],
    ["預估本益比", present(f.forwardPE) ? unit(number(f.forwardPE), "倍", "x") : "資料不足"], ["Beta", number(f.beta)],
    ["52 週高點", money(f.fiftyTwoWeekHigh)], ["52 週低點", money(f.fiftyTwoWeekLow)],
  ];
  replace("financialMetrics", definitions.map(([label, value]) => metric(label, value)));
}

const growthFeatureLabels = {
  growth_3m_yoy: ["近 3 個月年增率", "3-month year-over-year growth"],
  growth_6m_yoy: ["近 6 個月年增率", "6-month year-over-year growth"],
  growth_12m_yoy: ["近 12 個月年增率", "12-month year-over-year growth"],
  growth_acceleration: ["近期相對年度的成長加速度", "Recent growth acceleration versus annual growth"],
  recent_momentum: ["近 3 個月相對前 3 個月動能", "Recent 3-month momentum versus the prior 3 months"],
  monthly_yoy_volatility: ["月年增率波動度", "Volatility of monthly year-over-year growth"],
  log_revenue_trend_annualized: ["近 12 個月營收趨勢年化", "Annualized trend across the latest 12 months"],
  seasonality_variation: ["近 12 個月季節性變異", "Seasonality variation across the latest 12 months"],
  log_trailing_revenue: ["近 12 個月營收規模（log10）", "Trailing-12-month revenue scale (log10)"],
};

function formulaList(rows) {
  return node("dl", { className: "formula-list" }, rows.flatMap(([label, value]) => [
    node("dt", { text: label }), node("dd", { text: value }),
  ]));
}

function growthFormulaContent(formula) {
  if (!formula?.type) return empty(L("完整公式需要可用的模型 artifact。", "A usable model artifact is required to show the full formula."));
  const featureRows = (formula.features || []).map(item => {
    const names = growthFeatureLabels[item.name] || [item.name, item.name];
    const label = L(names[0], names[1]);
    const value = `x=${number(item.value, 4)} · β=${number(item.coefficient, 4)} · μ=${number(item.mean, 4)} · σ=${number(item.std, 4)}`;
    return [label, value];
  });
  const gradeRows = Object.entries(formula.grade_rule || {}).map(([grade, rule]) => [grade, rule]);
  return node("div", {}, [
    node("p", { text: L(`使用最近 ${formula.history_months || 24} 個月官方月營收。先標準化各特徵，再代入下列公開參數；所有候選僅以 2023 驗證期選擇，未用保留測試期調整。`, `Uses the most recent ${formula.history_months || 24} months of official monthly revenue. Features are standardized before applying the public parameters; candidates were selected only on the 2023 validation period, not tuned on the held-out test period.`) }),
    node("p", { className: "formula-equation", text: `${formula.raw_equation || ""}\n${formula.prediction_equation || ""}` }),
    node("p", { text: L("特徵與本次代入值：", "Features and this analysis' inputs:") }),
    formulaList(featureRows),
    node("p", { text: L("若未來完整部署門檻通過，字母級距的規則如下；目前只顯示實驗參考，不發出正式評級：", "If all deployment gates pass in a future release, grades use the following rules. This release shows a reference estimate only and issues no formal rating:") }),
    formulaList(gradeRows),
  ]);
}

function safetyBandText(value) {
  const labels = {
    safe_reference: ["高於原始安全參考線", "Above the original safe reference"],
    gray_zone_reference: ["原始灰色區間", "Original gray zone"],
    distress_reference: ["低於原始壓力參考線", "Below the original distress reference"],
  };
  const label = labels[value] || ["資料不足", "Insufficient data"];
  return L(label[0], label[1]);
}

function safetyFormulaContent(formula) {
  if (!formula?.type) return empty(L("完整公式需要期間一致的年度財報。", "Period-aligned annual statements are required to show the full formula."));
  const officialQuarterlyReference = formula.profitability_input === "annualized_operating_income";
  const formulaIntro = officialQuarterlyReference
    ? L("這是使用最新官方季度財報的財務結構參考：年初至今營業利益與營收會依已公布季度以 4／季度年化；它不是原始 Altman Z、台灣破產機率、信用評等或投資建議。", "This is a financial-structure reference built from the latest official quarterly statement. Year-to-date operating income and revenue are annualized by 4 / reported quarter; it is not the original Altman Z, a Taiwan bankruptcy probability, a credit rating, or investment advice.")
    : L("這使用公開公司 Altman Z 公式作為財務結構參考；不是台灣未來 12 個月破產機率。", "This uses the public-company Altman Z formula as a financial-structure reference; it is not a Taiwan 12-month bankruptcy probability.");
  const safetyInputLabels = {
    working_capital_to_assets: ["營運資金／總資產", "Working capital / total assets"],
    retained_earnings_to_assets: ["保留盈餘／總資產", "Retained earnings / total assets"],
    ebit_to_assets: ["EBIT／總資產", "EBIT / total assets"],
    market_value_equity_to_total_liabilities: ["市值／總負債", "Market value of equity / total liabilities"],
    sales_to_assets: ["年度營收／總資產", "Annual sales / total assets"],
  };
  if (officialQuarterlyReference) {
    safetyInputLabels.ebit_to_assets = ["年化營業利益／總資產", "Annualized operating income / total assets"];
    safetyInputLabels.sales_to_assets = ["年化年初至今營收／總資產", "Annualized year-to-date revenue / total assets"];
  }
  const rows = Object.entries(formula.inputs || {}).map(([name, item]) => [
    L(...(safetyInputLabels[name] || [name.replaceAll("_", " "), name.replaceAll("_", " ")])),
    item.value === null || item.value === undefined
      ? L("資料不足", "Insufficient data")
      : `${L("比率", "ratio")}=${number(item.value, 4)} · ${L("係數", "coefficient")}=${number(item.coefficient, 2)} · ${L("貢獻", "contribution")}=${number(item.contribution, 4)}`,
  ]);
  const bands = Object.entries(formula.band_rule || {}).map(([name, rule]) => [safetyBandText(name), rule]);
  const referenceTiers = Object.entries(formula.reference_rating_rule || {}).map(([tier, rule]) => [L(`參考 ${tier}`, `Reference ${tier}`), rule]);
  return node("div", {}, [
    node("p", { text: formulaIntro }),
    node("p", { className: "formula-equation", text: formula.equation || "" }),
    node("p", { text: L("本次代入比率：", "Ratios used in this analysis:") }),
    formulaList(rows),
    node("p", { text: L("原始參考區間：", "Original reference bands:") }),
    formulaList(bands),
    node("p", { text: L("本次顯示的參考分級規則：", "Reference-tier rules displayed by this app:") }),
    formulaList(referenceTiers),
    node("p", { text: L("正式台灣評級仍需要：可回溯的當時財報、客觀定義的財務危機結果，以及按時間順序的樣本外驗證。", "A formal Taiwan rating still requires point-in-time statements, objectively defined financial-distress outcomes, and chronological out-of-sample validation.") }),
  ]);
}

function renderModels(data) {
  const models = data.model_assessments || {};
  const growth = models.growth || {};
  const safety = models.safety || {};
  const statusNames = {
    validated: "已通過驗證",
    reference_estimate: "參考成長分級（未完成正式驗證）",
    reference_rating: "參考財務結構分級（未完成正式驗證）",
    experimental_not_deployable: "實驗估計／未通過驗證",
    experimental_not_validated: "實驗性篩檢／尚未歷史驗證",
    reference_formula_not_locally_validated: "公式參考／尚未本地歷史驗證",
    annual_statement_unavailable: "年度財報無法核對",
    specialized_model_pending: "專用模型待建立",
    specialized_product_model_pending: "特殊商品專用模型待建立",
    insufficient_data: "資料不足",
    official_history_unavailable: "官方歷史資料暫不可用",
    model_incompatible: "模型設定不相容",
    not_applicable: "不適用",
  };
  setText("modelSeparationNote", models.separation_note || "成長性與財務安全不合併成單一分數。");
  setText("modelDisclaimer", L("模型與公式只供研究與教學參考，不構成投資建議、報酬保證、信用評等或破產機率。請先查看資料期間、適用範圍與未通過的驗證條件。", "Models and formulas are for research and education only—not investment advice, a return guarantee, a credit rating, or a bankruptcy probability. Review the data period, applicability, and any validation gates that remain unmet."));
  setText("growthModelStatus", statusNames[growth.status] || growth.status || "資料不足");
  const interval = growth.prediction_interval_80 || {};
  replace("growthModelDetails", [
    metric(L("成長參考分級", "Growth reference tier"), growth.reference_rating || growth.experimental_rating || L("資料不足", "Insufficient data"), L("依營收成長估計與正成長可能性分級；非投資建議", "Based on the revenue-growth estimate and positive-growth likelihood; not investment advice")),
    metric(L("12 個月營收估計", "12-month revenue estimate"), percentPoint(growth.prediction_pct), t(growth.target || "未來連續 12 個月")),
    metric(L("80% 估計區間", "80% estimate interval"), present(interval.low_pct) && present(interval.high_pct) ? `${percentPoint(interval.low_pct)} ～ ${percentPoint(interval.high_pct)}` : L("資料不足", "Insufficient data")),
    metric(L("正成長可能性", "Positive-growth likelihood"), percentDecimal(growth.positive_growth_probability), L("不是保證或勝率", "Not a guarantee or win rate")),
    metric(L("資料觀測至", "Data observed through"), growth.observed_through || L("資料不足", "Insufficient data"), growth.input_source || L("官方資料", "Official data")),
    metric(L("EPS 次要目標", "Secondary EPS target"), L("尚未驗證", "Not validated"), growth.secondary_eps_target?.note ? t(growth.secondary_eps_target.note) : L("不產生預測數字", "Does not create a forecast number")),
  ]);
  setText("growthModelNote", ["experimental_not_deployable", "reference_estimate"].includes(growth.status)
    ? L("此成長參考分級在正式驗證門檻尚未完成時仍可閱讀；它是可追溯的營收成長估計，不是股價預測、投資報酬預測或投資建議。", "This reference tier remains available despite incomplete formal-validation gates. It is a traceable revenue-growth estimate, not a stock-price forecast, investment-return forecast, or recommendation.")
    : growth.note || L("模型估計具有不確定性，請搭配原始資料判讀。", "Model estimates are uncertain; interpret them together with the underlying data."));
  replace("growthFormulaDetails", growthFormulaContent(growth.formula));

  setText("safetyModelTitle", assetTypeNames[data.stock?.asset_type] || (data.is_etf ? "ETF 結構安全" : "公司財務安全"));
  setText("safetyModelStatus", statusNames[safety.status] || safety.status || "資料不足");
  replace("safetyModelDetails", [
    metric(L("財務結構參考分級", "Financial-structure reference tier"), safety.reference_rating || safety.experimental_rating || L("資料不足", "Insufficient data"), safety.reference_band ? safetyBandText(safety.reference_band) : L("不套用不適合的公式", "Does not apply unsuitable formulas")),
    metric(safety.score_label || L("篩檢分數", "Screening score"), present(safety.score) ? number(safety.score, 3) : L("資料不足", "Insufficient data"), safety.score_label === "Altman Z-Score" ? L("非 0–100 分數", "Not a 0–100 score") : null),
    metric(L("資料覆蓋率", "Data coverage"), percentDecimal(safety.coverage, 0)),
    metric(L("信心標示", "Confidence label"), safety.confidence || "none"),
    metric(L("評估目標", "Assessment target"), t(safety.target || "資料不足")),
  ]);
  setText("safetyModelNote", ["reference_formula_not_locally_validated", "reference_rating"].includes(safety.status)
    ? L("這是透明的財務結構參考分級，不是台灣破產機率、信用評等或投資建議。", "This is a transparent financial-structure reference tier. It is not a Taiwan bankruptcy probability, credit rating, or investment recommendation.")
    : t(safety.note || L("安全評級不代表股價不會下跌。", "A safety screen does not mean the share price cannot fall.")));
  replace("safetyFormulaDetails", safetyFormulaContent(safety.formula));
}

function renderRisks(data) {
  const risks = data.risk_warnings || [];
  if (!risks.length) return replace("riskList", node("li", {}, empty("目前無可用風險訊號；不代表沒有風險。")));
  replace("riskList", risks.map(item => node("li", { className: `risk-item ${["red", "yellow", "green"].includes(item.level) ? item.level : ""}` }, [
    node("strong", { text: `${t(item.type || "風險訊號")} · ${t(item.horizon === "short" ? "短期" : item.horizon === "long" ? "長期" : "中期")}` }),
    node("p", { text: localizedRiskMessage(item.msg || "說明資料不足") }),
  ])));
}

function renderQuality(data) {
  const quality = data.quality_score || {};
  const pi = quality.piotroski_details || {};
  const score = pi.score ?? quality.piotroski_f_score;
  const items = [
    metric("Piotroski F-Score", present(score) ? `${number(score, 0)} / 9` : "資料不足", present(pi.coverage) ? L(`訊號覆蓋率 ${percentDecimal(pi.coverage, 0)}`, `Signal coverage ${percentDecimal(pi.coverage, 0)}`) : "需完整 9 項訊號"),
    metric("Altman Z-Score", present(quality.altman_z_score) ? number(quality.altman_z_score, 3) : "資料不足", quality.altman_status ? L(`原始上市製造業模型：${quality.altman_status}`, `Original listed-manufacturer model: ${quality.altman_status}`) : "金融業與 ETF 不適用"),
    metric("Graham Number", money(quality.graham_number), "僅為經典價值投資參考"),
  ];
  replace("qualityMetrics", items);
}

function renderIncome(data) {
  const d = data.dividend;
  replace("dividendMetrics", d ? [
    metric("完整年度殖利率", percentPoint(d.yield), d.last_completed_year ? L(`${d.last_completed_year} 年`, `${d.last_completed_year}`) : "基準年度不足"),
    metric("本年度迄今殖利率", percentPoint(d.ytd_yield), "未完成年度，不與完整年度混用"),
    metric("連續配息", present(d.consecutive_years) ? L(`${number(d.consecutive_years, 0)} 年`, `${number(d.consecutive_years, 0)} years`) : "資料不足", "以可取得歷史覆蓋期間計"),
  ] : empty("無可用配息資料。"));
  const calendar = data.calendar || {};
  const events = [];
  if (calendar.ex_dividend) events.push(node("li", {}, [node("span", { text: "除息參考日" }), node("strong", { text: calendar.ex_dividend })]));
  for (const event of calendar.earnings || []) events.push(node("li", {}, [node("span", { text: t(event.label || "財報事件") }), node("strong", { text: event.date || "日期不足" })]));
  if (calendar.dividend_months?.length) {
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const months = calendar.dividend_months.map(month => {
      if (!isEnglish()) return month;
      const match = String(month).match(/(\d{1,2})/);
      return match && Number(match[1]) >= 1 && Number(match[1]) <= 12 ? monthNames[Number(match[1]) - 1] : String(month).replace("月", "");
    });
    events.push(node("li", {}, [node("span", { text: t("歷史配息月份") }), node("strong", { text: months.join(isEnglish() ? ", " : "、") })]));
  }
  replace("calendarList", events.length ? events : node("li", { text: "近期行事曆資料不足" }));
}

function renderPeers(data) {
  const peers = data.peers || [];
  if (!peers.length) return replace("peerTable", node("tr", {}, node("td", { colspan: "6", className: "empty-copy", text: "同產業資料不足" })));
  replace("peerTable", peers.map(peer => node("tr", {}, [
    node("td", { text: peer.stock_id || "—" }), node("td", { text: peer.name || "—" }),
    node("td", { text: money(peer.price, false) }), node("td", { text: present(peer.pe) ? `${number(peer.pe)}x` : "—" }),
    node("td", { text: percentPoint(peer.dividend_yield) }), node("td", { text: compactMoney(peer.market_cap) }),
  ])));
}

function renderNews(data) {
  const counts = data.news_sentiment || {};
  const providers = data.provider_status || {};
  const providerText = Object.entries(providers).map(([name, status]) => `${name}: ${status.status === "ok" ? L(`${status.count || 0} 則`, `${status.count || 0} items`) : t("失敗")}`).join(" · ");
  setText("newsStatus", L(`${providerText || "來源狀態不足"}。分類為關鍵字規則，不是投資訊號。`, `${providerText || t("來源狀態不足")}. Classification uses keyword rules and is not an investment signal.`));
  const items = data.news || [];
  const renderItems = (target, selected, emptyText) => replace(target, selected.length ? selected.map(item => {
    const url = safeUrl(item.url);
    const title = url ? node("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: item.title || "未命名新聞" }) : node("strong", { text: item.title || "未命名新聞" });
    return node("li", {}, [
      title,
      node("p", { text: item.summary || "無摘要" }),
      node("small", {}, [item.source || "來源未標示", item.date ? ` · ${item.date}` : "", node("span", { className: "sentiment", text: signalNames[item.sentiment] || "未分類" })]),
    ]);
  }) : node("li", {}, empty(emptyText)));
  renderItems("companyNewsList", items.filter(item => !item.is_fallback), "未取得可驗證的公司相關新聞。");
  renderItems("industryNewsList", items.filter(item => item.is_fallback), "未使用產業新聞備援。");
  byId("newsStatus").title = L(`正向 ${counts.positive || 0}／負向 ${counts.negative || 0}／中性 ${counts.neutral || 0}`, `Positive ${counts.positive || 0} / Negative ${counts.negative || 0} / Neutral ${counts.neutral || 0}`);
}

function renderCharts(data) {
  const charts = [
    ["股價趨勢", data.chart_price], ["月營收趨勢", data.chart_revenue], ["季度 EPS 趨勢", data.chart_eps],
  ].filter(([, url]) => typeof url === "string" && url.startsWith("data:image/"));
  replace("chartGrid", charts.length ? charts.map(([label, src]) => node("figure", { className: "chart-card" }, [
    node("img", { src, alt: `${data.stock?.name || "股票"}${label}`, loading: "lazy" }), node("figcaption", { text: label }),
  ])) : empty("圖表資料不足。"));
}

function renderSources(data) {
  const quality = data.data_quality || {};
  const provenance = data.data_provenance || {};
  const statusName = { official: "官方", stale: "官方舊資料", fallback: "備援", derived: "推算" };
  const sourceDetail = (item) => {
    if (!item) return node("span", { text: "未取得" });
    const details = [
      item.observed_at ? L(`資料期間：${item.observed_at}`, `Period: ${item.observed_at}`) : "資料期間：未提供",
      item.unit ? L(`單位：${item.unit}`, `Unit: ${item.unit}`) : "單位：未提供",
      item.fetched_at ? L(`抓取時間：${item.fetched_at}`, `Retrieved: ${item.fetched_at}`) : "抓取時間：未提供",
      item.note || "",
    ].filter(Boolean).join("｜");
    return node("details", { className: "source-detail" }, [
    node("summary", { text: `${item.source || t("來源未標示")} · ${t(statusName[item.status] || item.status || "狀態未標示")}` }),
      node("small", { text: details }),
    ]);
  };
  const entries = [
    ["股票清單", `${quality.stock_mapping_source || "unknown"} · ${quality.stock_mapping_status || "unknown"}`],
    ["主檔更新", quality.stock_mapping_updated_at || "未提供"],
    ["健康度覆蓋", percentDecimal(quality.health_coverage, 0)],
    ["Piotroski 覆蓋", percentDecimal(quality.piotroski_coverage, 0)],
    ["新聞分類", data.sentiment_method || "未執行"],
    ["參考價", sourceDetail(provenance.current_price)],
    ["月營收", sourceDetail(provenance.latest_revenue)],
    ["季度 EPS", sourceDetail(provenance.latest_eps)],
    ["官方累計 EPS", sourceDetail(provenance.official_cumulative_eps)],
  ];
  for (const [field, item] of Object.entries(provenance.financial_fields || {})) {
    entries.push([`財務欄位：${field}`, sourceDetail(item)]);
  }
  replace("dataSourceList", entries.flatMap(([label, value]) => [
    node("dt", { text: t(label) }),
    value instanceof Node ? node("dd", {}, value) : node("dd", { text: t(value) }),
  ]));
}

function renderCompany(data) {
  const stock = data.stock || {};
  const website = safeUrl(stock.website);
  const details = node("dl", {}, [
    node("dt", { text: t("產業／領域") }), node("dd", { text: [stock.industry, stock.sector].filter(Boolean).map(value => t(value)).join(isEnglish() ? " / " : "／") || t("資料不足") }),
    node("dt", { text: "國家" }), node("dd", { text: stock.country || "資料不足" }),
    node("dt", { text: "員工數" }), node("dd", { text: present(stock.employees) ? number(stock.employees, 0) : "資料不足" }),
    node("dt", { text: "官方網站" }), website ? node("dd", {}, node("a", { href: website, target: "_blank", rel: "noopener noreferrer", text: website })) : node("dd", { text: "資料不足" }),
  ]);
  const children = [details];
  if (stock.description) children.push(node("p", { text: stock.description }));
  replace("companyBody", children);
}

export function renderResult(data) {
  const isEtf = applyAssetLayout(data);
  renderHeader(data); renderFactsSummary(data); renderQualityBanner(data); renderModels(data); if (!isEtf) renderKpis(data); renderValuation(data); if (!isEtf) renderHealth(data);
  if (!isEtf) { renderFinancials(data); renderQuality(data); renderPeers(data); } renderRisks(data); renderIncome(data);
  renderNews(data); renderCharts(data); renderSources(data); renderCompany(data);
}
