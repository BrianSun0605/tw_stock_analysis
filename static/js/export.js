function spreadsheetSafe(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /^[\t\r ]*[=+\-@]/.test(text) ? `'${text}` : text;
}

export function csvCell(value) {
  const text = spreadsheetSafe(value).replaceAll('"', '""');
  return `"${text}"`;
}

export function buildSummaryCsv(data, language = "zh-TW") {
  const stock = data.stock || {};
  const growth = data.model_assessments?.growth || {};
  const safety = data.model_assessments?.safety || {};
  const health = data.health_score || {};
  const fair = data.fair_price || {};
  const en = language === "en";
  const L = (zh, english) => en ? english : zh;
  const unavailable = (value, reason = null) => value === null || value === undefined || value === "" ? L(reason || "資料不足", reason ? "Not applicable" : "Insufficient data") : value;
  const isEtf = Boolean(data.is_etf || stock.asset_type === "etf");
  const etf = data.etf_data || {};
  const rows = [
    [L("欄位", "Field"), L("數值", "Value")],
    [L("股票代號", "Ticker"), stock.stock_id], [L("股票名稱", "Security name"), stock.name],
    [L("市場", "Market"), stock.market], [L("產業／類型", "Industry / type"), stock.industry || stock.asset_type],
    [L("資產類別", "Asset type"), stock.asset_type], [L("參考價", "Reference price"), unavailable(stock.current_price)],
    [L("價格日期", "Price date"), unavailable(stock.price_date)],
    [L("正式成長評級", "Formal growth rating"), unavailable(growth.rating, "正式評級未通過驗證")],
    [L("成長參考分級", "Growth reference tier"), unavailable(growth.reference_rating ?? growth.experimental_rating, "不適用")],
    [L("實驗成長分級", "Experimental growth grade"), unavailable(growth.experimental_rating, "不適用")],
    [L("12 個月營收成長估計百分點", "12-month revenue-growth estimate (percentage points)"), unavailable(growth.prediction_pct, "不適用")],
    [L("成長模型狀態", "Growth model status"), unavailable(growth.status)],
    [L("正式財務安全評級", "Formal financial-safety rating"), unavailable(safety.rating, "正式評級未通過驗證")],
    [L("財務結構參考分級", "Financial-structure reference tier"), unavailable(safety.reference_rating, "不適用")],
    [L("實驗財務安全分級", "Experimental financial-safety grade"), unavailable(safety.experimental_rating, "不適用")],
    [L("財務安全分數", "Financial-safety score"), unavailable(safety.score, "不適用")],
    [L("財務安全模型狀態", "Financial-safety model status"), unavailable(safety.status)],
    [L("健康度", "Health score"), unavailable(health.score, isEtf ? "不適用" : null)],
    [L("健康度資料覆蓋率", "Health-data coverage"), unavailable(health.coverage, isEtf ? "不適用" : null)],
  ];
  if (isEtf) {
    rows.push(
      [L("NAV 淨值", "NAV"), unavailable(etf.nav_price)], [L("折溢價百分點", "Premium / discount (percentage points)"), unavailable(etf.premium_pct)],
      [L("費用率", "Expense ratio"), unavailable(etf.expense_ratio)], [L("管理資產 AUM", "Assets under management (AUM)"), unavailable(etf.total_assets)],
      [L("日均成交量", "Average daily volume"), unavailable(etf.avg_volume)], [L("追蹤指數", "Tracking index"), unavailable(etf.tracking_index ?? stock.tracking_index)],
      [L("完整年度殖利率百分點", "Full-year dividend yield (percentage points)"), unavailable(data.dividend?.yield ?? etf.etf_yield)],
    );
  } else {
    rows.push(
      [L("目前本益比", "Current P/E"), unavailable(fair.current_pe)], [L("便宜價", "Lower valuation reference"), unavailable(fair.cheap)],
      [L("合理價", "Fair-value reference"), unavailable(fair.fair)], [L("昂貴價", "Upper valuation reference"), unavailable(fair.expensive)],
      [L("近月營收 YoY 百分點", "Latest revenue YoY (percentage points)"), unavailable(data.revenue?.latest_yoy)],
      [L("最新季 EPS", "Latest quarterly EPS"), unavailable(data.eps?.eps)], [L("股利殖利率百分點", "Dividend yield (percentage points)"), unavailable(data.dividend?.yield)],
    );
  }
  rows.push([L("新聞分類方法", "News classification method"), unavailable(data.sentiment_method)]);
  return `\uFEFF${rows.map(row => row.map(csvCell).join(",")).join("\r\n")}\r\n`;
}

export function downloadSummaryCsv(data, language = "zh-TW") {
  const csv = buildSummaryCsv(data, language);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const id = String(data.stock?.stock_id || "stock").replace(/[^0-9A-Za-z_-]/g, "_");
  anchor.href = url;
  anchor.download = `${id}_analysis_summary.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
