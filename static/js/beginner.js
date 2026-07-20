import { byId, node, replace } from "./dom.js";
import { isEnglish } from "./i18n.js";

const STORAGE_KEY = "twstock.view-mode.v1";
let mode = localStorage.getItem(STORAGE_KEY) === "advanced" ? "advanced" : "beginner";

function has(value) { return value !== null && value !== undefined && value !== ""; }
function pct(value) { return has(value) ? `${Number(value).toFixed(1)}%` : null; }
function label(zh, en) { return isEnglish() ? en : zh; }
function text(value) { return value || label("資料不足", "Insufficient data"); }

function setMode(next) {
  mode = next === "advanced" ? "advanced" : "beginner";
  localStorage.setItem(STORAGE_KEY, mode);
  document.body.dataset.viewMode = mode;
  byId("beginnerModeButton").setAttribute("aria-pressed", String(mode === "beginner"));
  byId("advancedModeButton").setAttribute("aria-pressed", String(mode === "advanced"));
  byId("beginnerGuide").hidden = mode !== "beginner";
  for (const element of document.querySelectorAll(".advanced-content")) element.hidden = mode !== "advanced";
  byId("viewModeTitle").textContent = mode === "beginner" ? label("新手模式", "Beginner mode") : label("進階模式", "Advanced mode");
  byId("viewModeDescription").textContent = mode === "beginner"
    ? label("先看重點、限制與下一個學習任務", "Start with the essentials, limits, and one learning task")
    : label("展開完整指標、圖表、模型與資料來源", "Show all indicators, charts, models, and source details");
}

function guideCard(number, title, body, detail) {
  return node("article", { className: "beginner-card" }, [
    node("span", { className: "beginner-card-number", text: number }),
    node("h3", { text: title }), node("p", { text: body }),
    detail ? node("small", { text: detail }) : null,
  ].filter(Boolean));
}

function sourceStatus(data) {
  const provenance = data.data_provenance || {};
  const price = provenance.current_price || {};
  if (price.status === "fallback") return label("行情使用已標示的備援資料；解讀前請注意來源。", "Price data uses a labeled fallback source; check provenance before interpreting it.");
  if (price.status === "stale") return label("目前使用最後有效的舊資料；請先注意資料日期。", "The last valid older data is in use; check the data date first.");
  return label("主要欄位使用官方或可信來源；仍請留意資料日期與缺漏。", "Key fields use official or trusted sources; still check dates and missing data.");
}

function renderBeginnerGuide(data) {
  const stock = data.stock || {};
  const etf = Boolean(data.is_etf || stock.asset_type === "etf");
  const asset = etf ? "ETF" : (stock.asset_type || label("一般股票", "ordinary share")).toUpperCase();
  const revenue = data.revenue || {};
  const eps = data.eps || {};
  const fair = data.fair_price || {};
  const etfData = data.etf_data || {};
  const coverage = data.health_score?.coverage;
  const recommendation = etf
    ? ["nav", label("用一題理解 NAV 與市價", "Learn NAV and market price")]
    : has(revenue.latest_yoy)
      ? ["revenue_yoy", label("用一題理解營收年增率", "Learn revenue YoY")]
      : has(fair.current_pe) || has(eps.eps)
        ? ["pe", label("用一題理解本益比與 EPS", "Learn P/E and EPS")]
        : ["financial_health", label("用一題理解資料不足與財務健康度", "Learn insufficient data and financial health")];
  const start = node("button", { type: "button", className: "button primary", text: recommendation[1] });
  start.dataset.learningTerm = recommendation[0];
  const caution = [];
  if (etf) caution.push(label("ETF 不適用公司營收與 EPS；請改看 NAV、折溢價、費用率與追蹤指數。", "Company revenue and EPS do not apply to ETFs; use NAV, premium/discount, expense ratio, and tracking index instead."));
  if (!etf && (!has(coverage) || Number(coverage) < .7)) caution.push(label("公司財務資料覆蓋不足 70%，不能把健康度當成完整結論。", "Company financial-data coverage is below 70%; do not treat the health score as a complete conclusion."));
  if (data.model_assessments?.growth?.status !== "validated") caution.push(label("模型估計與已確認資料不同；正式評級尚未通過完整驗證。", "Model estimates differ from confirmed data; formal ratings have not passed full validation."));
  if (!caution.length) caution.push(label("資料看起來較完整，但任何單一指標都不能單獨代表買賣結論。", "Data appears more complete, but no single metric is a buy/sell conclusion."));
  const firstQuestion = etf
    ? label(`這是 ${asset}。市價 ${text(stock.current_price)}；NAV ${text(etfData.nav_price)}，折溢價 ${text(pct(etfData.premium_pct))}。`, `This is an ${asset}. Market price is ${text(stock.current_price)}; NAV is ${text(etfData.nav_price)} and premium/discount is ${text(pct(etfData.premium_pct))}.`)
    : label(`這是 ${asset}。參考價 ${text(stock.current_price)}；歷史本益比 ${text(fair.current_pe)}。`, `This is an ${asset}. Reference price is ${text(stock.current_price)} and historical P/E is ${text(fair.current_pe)}.`);
  const secondQuestion = etf
    ? label(`基金結構：費用率 ${text(pct(etfData.expense_ratio))}；追蹤 ${text(etfData.tracking_index)}。`, `Fund structure: expense ratio ${text(pct(etfData.expense_ratio))}; tracks ${text(etfData.tracking_index)}.`)
    : label(`營運資料：近月營收 YoY ${text(pct(revenue.latest_yoy))}；最新季 EPS ${text(eps.eps)}。`, `Operating data: latest revenue YoY ${text(pct(revenue.latest_yoy))}; latest-quarter EPS ${text(eps.eps)}.`);
  replace("beginnerGuide", [
    node("div", { className: "beginner-heading" }, [node("div", {}, [node("p", { className: "eyebrow", text: "START HERE" }), node("h3", { id: "beginnerGuideTitle", text: label("30 秒看懂這份分析", "Understand this analysis in 30 seconds") })]), node("span", { className: "method-tag", text: label("教育用途，非投資建議", "Education only, not investment advice") })]),
    node("p", { className: "beginner-intro", text: `${label("資料狀態：", "Data status: ")}${sourceStatus(data)}` }),
    node("div", { className: "beginner-card-grid" }, [
      guideCard("1", label("這是什麼？", "What is this?"), firstQuestion, stock.price_date ? `${label("價格日期", "Price date")}: ${stock.price_date}` : null),
      guideCard("2", label("現在能確認什麼？", "What can be confirmed now?"), secondQuestion, label("先把事實資料和模型推估分開看。", "Keep observed facts separate from model estimates.")),
      guideCard("3", label("哪些地方不能直接下結論？", "What should not be concluded yet?"), caution.join(" "), null),
    ]),
    node("div", { className: "beginner-next" }, [node("div", {}, [node("strong", { text: label("下一步學習", "Next learning step") }), node("p", { text: label("完成一題，練習分辨指標回答的問題與它不能回答的問題。", "Complete one question to practice what a metric can—and cannot—answer.") })]), start]),
  ]);
}

export function initBeginnerMode() {
  byId("beginnerModeButton").addEventListener("click", () => setMode("beginner"));
  byId("advancedModeButton").addEventListener("click", () => setMode("advanced"));
  setMode(mode);
}

export function updateBeginnerGuide(data) {
  renderBeginnerGuide(data);
  setMode(mode);
}
