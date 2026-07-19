function spreadsheetSafe(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /^[\t\r ]*[=+\-@]/.test(text) ? `'${text}` : text;
}

export function csvCell(value) {
  const text = spreadsheetSafe(value).replaceAll('"', '""');
  return `"${text}"`;
}

export function buildSummaryCsv(data) {
  const stock = data.stock || {};
  const growth = data.model_assessments?.growth || {};
  const safety = data.model_assessments?.safety || {};
  const health = data.health_score || {};
  const fair = data.fair_price || {};
  const rows = [
    ["欄位", "數值"],
    ["股票代號", stock.stock_id],
    ["股票名稱", stock.name],
    ["市場", stock.market],
    ["產業", stock.industry],
    ["參考價", stock.current_price],
    ["價格日期", stock.price_date],
    ["正式成長評級", growth.rating],
    ["實驗成長分級", growth.experimental_rating],
    ["12 個月營收成長估計百分點", growth.prediction_pct],
    ["成長模型狀態", growth.status],
    ["正式財務安全評級", safety.rating],
    ["實驗財務安全分級", safety.experimental_rating],
    ["財務安全分數", safety.score],
    ["財務安全模型狀態", safety.status],
    ["健康度", health.score],
    ["健康度資料覆蓋率", health.coverage],
    ["目前本益比", fair.current_pe],
    ["便宜價", fair.cheap],
    ["合理價", fair.fair],
    ["昂貴價", fair.expensive],
    ["股利殖利率百分點", data.dividend?.yield],
    ["新聞分類方法", data.sentiment_method],
  ];
  return `\uFEFF${rows.map(row => row.map(csvCell).join(",")).join("\r\n")}\r\n`;
}

export function downloadSummaryCsv(data) {
  const csv = buildSummaryCsv(data);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const id = String(data.stock?.stock_id || "stock").replace(/[^0-9A-Za-z_-]/g, "_");
  anchor.href = url;
  anchor.download = `${id}_analysis_summary.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
