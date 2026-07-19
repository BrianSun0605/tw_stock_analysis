import { byId, compactMoney, money, node, number, percentDecimal, percentPoint, present, replace, safeUrl } from "./dom.js";

const componentNames = {
  growth: "成長性", valuation: "估值", profitability: "獲利能力",
  quality: "品質力", momentum: "價格動能", stability: "穩定性", cashflow: "現金流",
};
const signalNames = { positive: "正向", negative: "負向", neutral: "中性" };
const assetTypeNames = {
  stock: "公司財務安全", tdr: "公司財務安全", etf: "ETF 結構安全",
  etn: "ETN 結構安全", reit: "REIT 結構安全", preferred_stock: "特別股財務安全",
};

function setText(id, value) { byId(id).textContent = value; }
function metric(label, value, note) {
  const children = [node("dt", { text: label }), node("dd", { text: value })];
  if (note) children.push(node("small", { text: note }));
  return node("dl", { className: "metric" }, children);
}
function empty(text = "目前沒有可呈現的資料") { return node("p", { className: "empty-copy", text }); }

function renderHeader(data) {
  const stock = data.stock || {};
  const growth = data.model_assessments?.growth || {};
  const safety = data.model_assessments?.safety || {};
  setText("stockName", stock.name || "名稱資料不足");
  setText("stockEnglish", stock.name_en || "");
  setText("stockMeta", [stock.stock_id, stock.market, stock.industry].filter(Boolean).join(" · ") || "資料不足");
  setText("stockPrice", money(stock.current_price));
  const change = stock.day_change_pct;
  setText("stockChange", present(change) ? `單日 ${Number(change) >= 0 ? "+" : ""}${percentPoint(change)}` : "漲跌資料不足");
  byId("stockChange").className = present(change) ? (Number(change) >= 0 ? "positive" : "negative") : "";
  setText("priceDate", stock.price_date ? `價格日期 ${stock.price_date}` : "價格日期未提供");
  const setGrade = (prefix, assessment, fallbackText) => {
    const grade = ["A", "B", "C", "D", "E", "F"].includes(assessment.rating) ? assessment.rating : "N/A";
    setText(`${prefix}RatingBadge`, grade);
    byId(`${prefix}RatingBadge`).className = `rating ${grade === "N/A" ? "n-a" : grade.toLowerCase()}`;
    setText(`${prefix}RatingText`, grade === "N/A" ? fallbackText : `${number(assessment.score, 1)} / 100`);
  };
  setGrade("growth", growth, growth.experimental_rating ? `實驗 ${growth.experimental_rating}` : "暫不評級");
  setText("growthRatingMeta", growth.rating ? `信心 ${growth.confidence || "未標示"}` : "正式評級未通過驗證");
  setGrade("safety", safety, safety.status === "specialized_model_pending" ? "專用模型待建" : safety.experimental_rating ? `實驗 ${safety.experimental_rating}` : "暫不評級");
  setText("safetyRatingMeta", safety.rating ? `信心 ${safety.confidence || "未標示"}` : "正式評級尚未完成歷史驗證");
}

function renderQualityBanner(data) {
  const coverage = data.health_score?.coverage;
  const mapping = data.data_quality?.stock_mapping_source || "unknown";
  const banner = byId("qualityBanner");
  if (!present(coverage) || Number(coverage) < .7) {
    banner.className = "quality-banner warning";
    banner.textContent = `可用資料不足 70%，綜合分數不應作為判斷依據。股票清單：${mapping}。`;
  } else {
    banner.className = "quality-banner";
    banner.textContent = `本次健康度資料覆蓋率 ${percentDecimal(coverage, 0)}；缺漏維度已標示為「資料不足」，未以零分代替。股票清單：${mapping}。`;
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
    metric("缺漏狀態", present(quality.health_coverage) ? `健康資料覆蓋 ${percentDecimal(quality.health_coverage, 0)}` : "核心資料不足"),
  ]);
}

function renderKpis(data) {
  const fair = data.fair_price || {};
  const health = data.health_score || {};
  const dividend = data.dividend || {};
  setText("kpiPe", present(fair.current_pe) ? `${number(fair.current_pe)} 倍` : "資料不足");
  setText("kpiFair", money(fair.fair));
  setText("kpiHealth", present(health.score) ? `${number(health.score, 1)} / 100` : "資料不足");
  setText("kpiHealthLevel", health.level || "資料覆蓋門檻 70%");
  setText("kpiYield", percentPoint(dividend.yield));
  setText("kpiYieldBasis", dividend.last_completed_year ? `${dividend.last_completed_year} 完整年度` : "最近完整年度");
  setText("kpiRevenue", percentPoint(data.revenue?.latest_yoy));
  setText("kpiRevenuePeriod", data.revenue ? `${data.revenue.year}/${String(data.revenue.month).padStart(2, "0")}` : "—");
  setText("kpiEps", present(data.eps?.eps) ? `${number(data.eps.eps)} 元` : "資料不足");
  setText("kpiEpsPeriod", data.eps ? `${data.eps.year} Q${data.eps.quarter}` : "—");
}

function renderValuation(data) {
  const fair = data.fair_price;
  if (!fair) return replace("fairMetrics", empty("ETF 或資料不足，未建立個股歷史本益比區間。"));
  replace("fairMetrics", [
    metric("便宜價", money(fair.cheap)), metric("合理價", money(fair.fair)), metric("昂貴價", money(fair.expensive)),
    metric("目前本益比", present(fair.current_pe) ? `${number(fair.current_pe)} 倍` : "資料不足"),
    metric("EPS 成長", percentPoint(fair.eps_growth_pct), "需 8 季連續資料"),
    metric("歷史樣本數", present(fair.sample_size) ? `${number(fair.sample_size, 0)} 日` : "資料不足", "至少 60 個交易日"),
  ]);
}

function renderHealth(data) {
  const health = data.health_score || {};
  setText("healthCoverage", present(health.coverage) ? `覆蓋率 ${percentDecimal(health.coverage, 0)}` : "覆蓋率 —");
  const rows = Object.entries(health.components || {}).map(([key, item]) => {
    const available = item?.status === "available" && present(item.score);
    return node("div", { className: `score-row${available ? "" : " unavailable"}` }, [
      node("div", { className: "score-label" }, [componentNames[key] || key, node("small", { text: `權重 ${item?.weight || "—"}` })]),
      node("progress", { className: "score-track", max: "100", value: available ? Math.max(0, Math.min(100, Number(item.score))) : 0, "aria-label": `${componentNames[key] || key}分數` }),
      node("div", { className: "score-value", text: available ? number(item.score, 1) : "資料不足" }),
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
    ["預估本益比", present(f.forwardPE) ? `${number(f.forwardPE)} 倍` : "資料不足"], ["Beta", number(f.beta)],
    ["52 週高點", money(f.fiftyTwoWeekHigh)], ["52 週低點", money(f.fiftyTwoWeekLow)],
  ];
  replace("financialMetrics", definitions.map(([label, value]) => metric(label, value)));
}

function renderModels(data) {
  const models = data.model_assessments || {};
  const growth = models.growth || {};
  const safety = models.safety || {};
  const statusNames = {
    validated: "已通過驗證",
    experimental_not_deployable: "實驗估計／未通過驗證",
    experimental_not_validated: "實驗性篩檢／尚未歷史驗證",
    specialized_model_pending: "專用模型待建立",
    specialized_product_model_pending: "特殊商品專用模型待建立",
    insufficient_data: "資料不足",
    official_history_unavailable: "官方歷史資料暫不可用",
    not_applicable: "不適用",
  };
  setText("modelSeparationNote", models.separation_note || "成長性與財務安全不合併成單一分數。");
  setText("growthModelStatus", statusNames[growth.status] || growth.status || "資料不足");
  const interval = growth.prediction_interval_80 || {};
  replace("growthModelDetails", [
    metric("正式成長評級", growth.rating || "未通過驗證", growth.experimental_rating ? `實驗分級 ${growth.experimental_rating}` : "不強行產生分數"),
    metric("12 個月營收估計", percentPoint(growth.prediction_pct), growth.target || "未來連續 12 個月"),
    metric("80% 估計區間", present(interval.low_pct) && present(interval.high_pct) ? `${percentPoint(interval.low_pct)} ～ ${percentPoint(interval.high_pct)}` : "資料不足"),
    metric("正成長可能性", percentDecimal(growth.positive_growth_probability), "不是保證或勝率"),
    metric("資料觀測至", growth.observed_through || "資料不足", growth.input_source || "官方資料"),
    metric("EPS 次要目標", "尚未驗證", growth.secondary_eps_target?.note || "不產生預測數字"),
  ]);
  setText("growthModelNote", growth.note || "模型估計具有不確定性，請搭配原始資料判讀。");

  setText("safetyModelTitle", assetTypeNames[data.stock?.asset_type] || (data.is_etf ? "ETF 結構安全" : "公司財務安全"));
  setText("safetyModelStatus", statusNames[safety.status] || safety.status || "資料不足");
  replace("safetyModelDetails", [
    metric("正式安全評級", safety.rating || "未通過驗證", safety.experimental_rating ? `實驗分級 ${safety.experimental_rating}；不是破產機率` : "不套用不適合的公式"),
    metric("篩檢分數", present(safety.score) ? `${number(safety.score, 1)} / 100` : "資料不足"),
    metric("資料覆蓋率", percentDecimal(safety.coverage, 0)),
    metric("信心標示", safety.confidence || "none"),
    metric("評估目標", safety.target || "資料不足"),
  ]);
  setText("safetyModelNote", safety.note || "安全評級不代表股價不會下跌。");
}

function renderRisks(data) {
  const risks = data.risk_warnings || [];
  if (!risks.length) return replace("riskList", node("li", {}, empty("目前無可用風險訊號；不代表沒有風險。")));
  replace("riskList", risks.map(item => node("li", { className: `risk-item ${["red", "yellow", "green"].includes(item.level) ? item.level : ""}` }, [
    node("strong", { text: `${item.type || "風險訊號"} · ${item.horizon === "short" ? "短期" : item.horizon === "long" ? "長期" : "中期"}` }),
    node("p", { text: item.msg || "說明資料不足" }),
  ])));
}

function renderQuality(data) {
  const quality = data.quality_score || {};
  const pi = quality.piotroski_details || {};
  const score = pi.score ?? quality.piotroski_f_score;
  const items = [
    metric("Piotroski F-Score", present(score) ? `${number(score, 0)} / 9` : "資料不足", present(pi.coverage) ? `訊號覆蓋率 ${percentDecimal(pi.coverage, 0)}` : "需完整 9 項訊號"),
    metric("Altman Z-Score", present(quality.altman_z_score) ? number(quality.altman_z_score, 3) : "資料不足", quality.altman_status ? `原始上市製造業模型：${quality.altman_status}` : "金融業與 ETF 不適用"),
    metric("Graham Number", money(quality.graham_number), "僅為經典價值投資參考"),
  ];
  replace("qualityMetrics", items);
}

function renderIncome(data) {
  const d = data.dividend;
  replace("dividendMetrics", d ? [
    metric("完整年度殖利率", percentPoint(d.yield), d.last_completed_year ? `${d.last_completed_year} 年` : "基準年度不足"),
    metric("本年度迄今殖利率", percentPoint(d.ytd_yield), "未完成年度，不與完整年度混用"),
    metric("連續配息", present(d.consecutive_years) ? `${number(d.consecutive_years, 0)} 年` : "資料不足", "以可取得歷史覆蓋期間計"),
  ] : empty("無可用配息資料。"));
  const calendar = data.calendar || {};
  const events = [];
  if (calendar.ex_dividend) events.push(node("li", {}, [node("span", { text: "除息參考日" }), node("strong", { text: calendar.ex_dividend })]));
  for (const event of calendar.earnings || []) events.push(node("li", {}, [node("span", { text: event.label || "財報事件" }), node("strong", { text: event.date || "日期不足" })]));
  if (calendar.dividend_months?.length) events.push(node("li", {}, [node("span", { text: "歷史配息月份" }), node("strong", { text: calendar.dividend_months.join("、") })]));
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
  const providerText = Object.entries(providers).map(([name, status]) => `${name}: ${status.status === "ok" ? `${status.count || 0} 則` : "失敗"}`).join(" · ");
  setText("newsStatus", `${providerText || "來源狀態不足"}。分類為關鍵字規則，不是投資訊號。`);
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
  byId("newsStatus").title = `正向 ${counts.positive || 0}／負向 ${counts.negative || 0}／中性 ${counts.neutral || 0}`;
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
      item.observed_at ? `資料期間：${item.observed_at}` : "資料期間：未提供",
      item.unit ? `單位：${item.unit}` : "單位：未提供",
      item.fetched_at ? `抓取時間：${item.fetched_at}` : "抓取時間：未提供",
      item.note || "",
    ].filter(Boolean).join("｜");
    return node("details", { className: "source-detail" }, [
      node("summary", { text: `${item.source || "來源未標示"} · ${statusName[item.status] || item.status || "狀態未標示"}` }),
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
    node("dt", { text: label }),
    value instanceof Node ? node("dd", {}, value) : node("dd", { text: value }),
  ]));
}

function renderCompany(data) {
  const stock = data.stock || {};
  const website = safeUrl(stock.website);
  const details = node("dl", {}, [
    node("dt", { text: "產業／領域" }), node("dd", { text: [stock.industry, stock.sector].filter(Boolean).join("／") || "資料不足" }),
    node("dt", { text: "國家" }), node("dd", { text: stock.country || "資料不足" }),
    node("dt", { text: "員工數" }), node("dd", { text: present(stock.employees) ? number(stock.employees, 0) : "資料不足" }),
    node("dt", { text: "官方網站" }), website ? node("dd", {}, node("a", { href: website, target: "_blank", rel: "noopener noreferrer", text: website })) : node("dd", { text: "資料不足" }),
  ]);
  const children = [details];
  if (stock.description) children.push(node("p", { text: stock.description }));
  replace("companyBody", children);
}

export function renderResult(data) {
  renderHeader(data); renderFactsSummary(data); renderQualityBanner(data); renderModels(data); renderKpis(data); renderValuation(data); renderHealth(data);
  renderFinancials(data); renderRisks(data); renderQuality(data); renderIncome(data); renderPeers(data);
  renderNews(data); renderCharts(data); renderSources(data); renderCompany(data);
}
