import { cancelTask as cancelTaskRequest, getTask, requestReport, searchStocks, shutdown, startAnalysis, streamAnalysis } from "./api.js";
import { byId, node, replace } from "./dom.js";
import { downloadSummaryCsv } from "./export.js";
import { getLocale, initI18n, t } from "./i18n.js";
import { initBeginnerMode, updateBeginnerGuide } from "./beginner.js";
import { initLearning } from "./learning.js";
import { renderResult } from "./render.js";

const ACTIVE_TASK_KEY = "twstock.activeTask.v1";
const stepLabels = {
  1: "行情與基本資料",
  2: "營收與季度 EPS",
  3: "財報與估值指標",
  4: "新聞、股利與同業",
  5: "組裝分析結果",
};
const assetTypeNames = {
  stock: "股票", tdr: "TDR", etf: "ETF", etn: "ETN",
  reit: "REIT", preferred_stock: "特別股",
};

let suggestions = [];
let activeSuggestion = -1;
let searchController = null;
let activeStream = null;
let activeTaskId = null;
let currentResult = null;
let resultRendered = false;
let lastQuery = "";
let searchTimer = null;
let recoveryTimer = null;
let terminalHandled = false;
let lastEventId = 0;

function toast(message) {
  const element = byId("toast");
  element.textContent = t(message);
  element.hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => { element.hidden = true; }, 5200);
}

function setBusy(busy, label = "分析中…") {
  byId("analyzeButton").disabled = busy;
  byId("stockQuery").disabled = busy;
  byId("analyzeButton").textContent = t(busy ? label : "開始分析");
}

function setWorkflow(state, { title, detail, badge, tone = "running" }) {
  const panel = byId("analysisProgress");
  panel.hidden = false;
  panel.dataset.state = state;
  byId("progressText").textContent = t(title);
  byId("progressDetail").textContent = t(detail);
  byId("progressState").textContent = t(badge);
  byId("progressState").dataset.tone = tone;
}

function updateStepStates(activeStep, detail = "處理中") {
  for (const item of byId("analysisSteps").children) {
    const step = Number(item.dataset.step);
    const state = step < activeStep ? "complete" : step === activeStep ? "active" : "waiting";
    item.dataset.state = state;
    const status = item.querySelector("small");
    if (status) status.textContent = t(state === "complete" ? "完成" : state === "active" ? detail : "等待中");
  }
}

function completeAnalysisSteps() {
  for (const item of byId("analysisSteps").children) {
    item.dataset.state = "complete";
    const status = item.querySelector("small");
    if (status) status.textContent = t("完成");
  }
  byId("progressBar").max = 5;
  byId("progressBar").value = 5;
  byId("progressCounter").textContent = t("分析完成");
}

function resetWorkflow() {
  terminalHandled = false;
  resultRendered = false;
  byId("analysisProgress").hidden = false;
  byId("analysisProgress").dataset.state = "running";
  byId("progressBar").max = 5;
  byId("progressBar").value = 0;
  byId("progressCounter").textContent = "0 / 5";
  byId("progressLog").replaceChildren();
  byId("reportProgress").hidden = true;
  byId("reportProgressTitle").textContent = "PDF 報告產生中";
  byId("reportProgressBar").max = 1;
  byId("reportProgressBar").value = 0;
  byId("reportProgressCounter").textContent = "0 / 0";
  byId("connectionNotice").hidden = true;
  byId("progressDownloadPdf").hidden = true;
  byId("generatePdf").hidden = true;
  byId("generatePdf").disabled = false;
  byId("viewResults").hidden = true;
  byId("retryAnalysis").hidden = true;
  byId("analyzeAnother").hidden = true;
  byId("cancelTask").hidden = true;
  byId("cancelTask").disabled = false;
  updateStepStates(0);
}

function hideSuggestions() {
  suggestions = [];
  activeSuggestion = -1;
  byId("searchResults").hidden = true;
  byId("stockQuery").setAttribute("aria-expanded", "false");
  byId("stockQuery").removeAttribute("aria-activedescendant");
}

function chooseSuggestion(index) {
  const item = suggestions[index];
  if (!item) return;
  byId("stockQuery").value = `${item.stock_id} ${item.name}`;
  hideSuggestions();
}

function drawSuggestions(items) {
  suggestions = items;
  activeSuggestion = -1;
  const list = byId("searchResults");
  replace("searchResults", items.map((item, index) => node("li", {
    id: `suggestion-${index}`, role: "option", "aria-selected": "false", tabindex: "-1",
  }, [node("strong", { text: item.stock_id }), node("span", { text: item.name }), node("small", { text: [item.market, assetTypeNames[item.asset_type], item.industry].filter(Boolean).join(" · ") })])));
  for (const [index, element] of [...list.children].entries()) {
    element.addEventListener("pointerdown", (event) => { event.preventDefault(); chooseSuggestion(index); });
  }
  list.hidden = items.length === 0;
  byId("stockQuery").setAttribute("aria-expanded", items.length ? "true" : "false");
}

async function updateSuggestions() {
  const query = byId("stockQuery").value.trim();
  if (query.length < 1) return hideSuggestions();
  searchController?.abort();
  searchController = new AbortController();
  try {
    drawSuggestions(await searchStocks(query, searchController.signal));
  } catch (error) {
    if (error.name !== "AbortError") hideSuggestions();
  }
}

function moveSuggestion(direction) {
  if (!suggestions.length) return;
  activeSuggestion = (activeSuggestion + direction + suggestions.length) % suggestions.length;
  for (const [index, element] of [...byId("searchResults").children].entries()) {
    element.setAttribute("aria-selected", index === activeSuggestion ? "true" : "false");
  }
  const id = `suggestion-${activeSuggestion}`;
  byId("stockQuery").setAttribute("aria-activedescendant", id);
  document.getElementById(id)?.scrollIntoView({ block: "nearest" });
}

function updateProgress(message) {
  const text = String(message || "");
  const match = text.match(/^\[(\d+)\/(\d+)\]\s*(.*)$/);
  if (!match) {
    byId("progressLog").append(node("li", { text }));
    return;
  }
  const step = Number(match[1]);
  const total = Number(match[2]);
  const detail = match[3] || stepLabels[step] || "處理中";
  byId("progressBar").max = total;
  byId("progressBar").value = step;
  byId("progressCounter").textContent = `${step} / ${total}`;
  updateStepStates(step, detail);
  setBusy(true, `分析中 ${step}/${total}`);
  if (!currentResult) {
    setWorkflow("running", {
      title: stepLabels[step] || "正在建立分析",
      detail,
      badge: `${step} / ${total}`,
    });
  } else {
    completeAnalysisSteps();
    setBusy(true, "報告產生中…");
  }
  byId("progressLog").append(node("li", { text }));
}

function setResultStatus(state, title, detail) {
  byId("resultStatus").dataset.state = state;
  byId("resultStatusTitle").textContent = t(title);
  byId("resultStatusText").textContent = t(detail);
}

function handlePreview(data, { scroll = true } = {}) {
  currentResult = data;
  try {
    renderResult(data);
    updateBeginnerGuide(data);
    resultRendered = true;
  } catch (error) {
    console.error("Result rendering failed", error);
    resultRendered = false;
    setWorkflow("error", {
      title: "分析完成，但畫面顯示失敗",
      detail: "請重新執行分析；PDF 尚未產生。",
      badge: "顯示異常",
      tone: "error",
    });
  }
  byId("emptyState").hidden = true;
  byId("resultView").hidden = !resultRendered;
  byId("exportCsv").disabled = !resultRendered;
  completeAnalysisSteps();
  byId("reportProgress").hidden = true;
  byId("viewResults").hidden = !resultRendered;
  setBusy(true, "分析收尾中…");
  if (resultRendered) {
    setWorkflow("running", {
      title: "分析結果已可查看",
      detail: "正在完成最後整理；PDF 會在你按下按鈕後才產生。",
      badge: "分析收尾中",
    });
    setResultStatus("running", "分析結果已可查看", "PDF 尚未產生");
    if (scroll) {
      window.scrollTo({ top: byId("resultView").offsetTop - 76, behavior: "smooth" });
      byId("resultView").focus({ preventScroll: true });
    }
  }
}

function handleReportProgress(report) {
  byId("cancelTask").hidden = false;
  const current = Math.max(0, Number(report.current) || 0);
  const total = Math.max(1, Number(report.total) || 1);
  const section = String(report.section || "產生報告內容");
  byId("reportProgress").hidden = false;
  byId("reportProgressTitle").textContent = "PDF 報告產生中";
  byId("reportProgressBar").max = total;
  byId("reportProgressBar").value = current;
  byId("reportProgressCounter").textContent = `${current} / ${total}`;
  byId("reportProgressText").textContent = `正在處理：${section}`;
  setWorkflow("reporting", {
    title: currentResult ? "分析結果已可查看" : "PDF 報告產生中",
    detail: currentResult ? `PDF 正在處理「${section}」，分析內容已可先行閱讀。` : `正在處理「${section}」。`,
    badge: `PDF ${current}/${total}`,
  });
}

function setDownload(filename) {
  byId("generatePdf").hidden = true;
  byId("downloadPdf").hidden = true;
  for (const id of ["progressDownloadPdf"]) {
    const link = byId(id);
    link.href = `/download/${encodeURIComponent(filename)}`;
    link.hidden = false;
  }
}

function clearActiveTask() {
  sessionStorage.removeItem(ACTIVE_TASK_KEY);
  window.clearTimeout(recoveryTimer);
  recoveryTimer = null;
  activeTaskId = null;
}

function handleDone(filename) {
  if (terminalHandled) return;
  terminalHandled = true;
  activeStream?.close();
  activeStream = null;
  setBusy(false);
  byId("cancelTask").hidden = true;
  byId("cancelTask").disabled = false;
  completeAnalysisSteps();
  byId("reportProgress").hidden = !filename;
  if (filename) {
    byId("reportProgressTitle").textContent = "PDF 報告已完成";
    byId("reportProgressBar").value = byId("reportProgressBar").max;
    byId("reportProgressText").textContent = `已完成：${filename}`;
  }
  byId("retryAnalysis").hidden = true;
  byId("analyzeAnother").hidden = false;
  byId("viewResults").hidden = !resultRendered;
  byId("generatePdf").hidden = Boolean(filename) || !resultRendered;
  byId("generatePdf").disabled = false;
  if (filename) setDownload(filename);
  setWorkflow("complete", {
    title: filename ? "分析與 PDF 報告已完成" : "分析已完成",
    detail: filename ? `PDF 已寫入本機 output 目錄：${filename}` : "需要報告時，請按「產生並下載 PDF」。",
    badge: "已完成",
    tone: "success",
  });
  if (resultRendered) {
    setResultStatus(
      "complete",
      filename ? "PDF 報告已完成" : "分析結果已完成",
      filename ? `已儲存 ${filename}，可立即下載` : "PDF 尚未產生，可按需建立",
    );
  }
  if (filename) clearActiveTask();
  document.title = filename ? "報告已完成｜台股研究室" : "分析已完成｜台股研究室";
  toast(filename ? "PDF 報告已完成，可立即下載。" : "分析已完成；需要時可產生 PDF。" );
}

function handleReportFailure(message) {
  terminalHandled = true;
  activeStream?.close();
  activeStream = null;
  setBusy(false);
  byId("cancelTask").hidden = true;
  byId("cancelTask").disabled = false;
  byId("generatePdf").hidden = !resultRendered;
  byId("generatePdf").disabled = false;
  byId("reportProgress").hidden = false;
  byId("reportProgressTitle").textContent = "PDF 報告產生失敗";
  byId("reportProgressText").textContent = message || "請稍後重試。";
  setResultStatus("error", "分析結果已保留", "PDF 產生失敗，可再次嘗試");
  setWorkflow("error", {
    title: "分析結果已保留，但 PDF 產生失敗",
    detail: message || "請稍後再次按下產生 PDF。",
    badge: "PDF 失敗",
    tone: "error",
  });
  toast(message || "PDF 報告產生失敗。" );
}

function handleFailure(message) {
  if (terminalHandled) return;
  terminalHandled = true;
  activeStream?.close();
  activeStream = null;
  setBusy(false);
  byId("cancelTask").hidden = true;
  byId("cancelTask").disabled = false;
  byId("retryAnalysis").hidden = false;
  byId("analyzeAnother").hidden = false;
  if (currentResult) byId("reportProgressTitle").textContent = "PDF 報告產生失敗";
  byId("viewResults").hidden = !resultRendered;
  if (!currentResult) {
    byId("emptyState").hidden = false;
    byId("resultView").hidden = true;
  } else {
    byId("resultView").hidden = !resultRendered;
    setResultStatus("error", "分析結果已保留", "PDF 報告產生失敗，可重新執行");
  }
  setWorkflow("error", {
    title: currentResult ? "分析結果已保留，但 PDF 產生失敗" : "分析未完成",
    detail: message || "請重新執行；若持續失敗，請查看執行紀錄。",
    badge: "需要處理",
    tone: "error",
  });
  clearActiveTask();
  toast(message || "分析失敗，請稍後再試。" );
}

function handleCancelled(message) {
  if (terminalHandled) return;
  terminalHandled = true;
  activeStream?.close();
  activeStream = null;
  setBusy(false);
  byId("cancelTask").hidden = true;
  byId("cancelTask").disabled = false;
  byId("retryAnalysis").hidden = false;
  byId("analyzeAnother").hidden = false;
  setWorkflow("error", {
    title: "工作已取消",
    detail: message || "目前工作已安全停止，可重新執行。",
    badge: "已取消",
    tone: "error",
  });
  if (!currentResult) byId("emptyState").hidden = false;
  clearActiveTask();
  toast(message || "工作已取消。");
}

function handleConnection(state) {
  const notice = byId("connectionNotice");
  if (state === "connected") {
    notice.hidden = true;
    window.clearTimeout(recoveryTimer);
    recoveryTimer = null;
    return;
  }
  notice.hidden = false;
  window.clearTimeout(recoveryTimer);
  recoveryTimer = window.setTimeout(() => {
    if (activeTaskId && !terminalHandled) recoverTask(activeTaskId).catch(() => {});
  }, 1200);
}

function connectToTask(taskId, after = 0) {
  activeStream?.close();
  activeStream = streamAnalysis(taskId, {
    log: updateProgress,
    result: (data) => handlePreview(data),
    report: handleReportProgress,
    done: handleDone,
    error: handleFailure,
    reportError: handleReportFailure,
    cancelled: handleCancelled,
    cursor: (cursor) => { lastEventId = Math.max(lastEventId, cursor); },
    connection: handleConnection,
    clientError: (error) => {
      console.error("Task event handling failed", error);
      byId("connectionNotice").hidden = false;
      recoverTask(taskId).catch(() => {});
    },
  }, after);
}

async function recoverTask(taskId) {
  const snapshot = await getTask(taskId);
  if (snapshot.preview && !resultRendered) handlePreview(snapshot.preview, { scroll: false });
  if (snapshot.stage) updateProgress(snapshot.message || `[${snapshot.stage}/${snapshot.stage_total || 5}] 正在恢復分析`);
  if (snapshot.report?.total) handleReportProgress(snapshot.report);
  if (snapshot.status === "ready") return handleDone(null);
  if (snapshot.status === "completed") return handleDone(snapshot.filename);
  if (snapshot.status === "failed") return handleFailure(snapshot.error);
  if (snapshot.status === "cancelled") return handleCancelled(snapshot.message);
  if (!activeStream) connectToTask(taskId);
}

async function analyze(query) {
  const value = String(query || "").trim();
  if (!value) return toast("請先輸入股票代號或名稱。");
  activeStream?.close();
  activeStream = null;
  window.clearTimeout(recoveryTimer);
  currentResult = null;
  activeTaskId = null;
  lastEventId = 0;
  lastQuery = value;
  hideSuggestions();
  resetWorkflow();
  setBusy(true, "正在建立任務…");
  byId("emptyState").hidden = true;
  byId("resultView").hidden = true;
  byId("downloadPdf").hidden = true;
  byId("exportCsv").disabled = true;
  document.title = "分析進行中｜台股研究室";
  setWorkflow("running", {
    title: "正在建立分析任務",
    detail: "接下來會完成五個分析步驟，結果會在 PDF 之前顯示。",
    badge: "準備中",
  });
  try {
    const { task_id: taskId } = await startAnalysis(value, getLocale());
    activeTaskId = taskId;
    byId("cancelTask").hidden = false;
    sessionStorage.setItem(ACTIVE_TASK_KEY, JSON.stringify({ taskId, query: value }));
    connectToTask(taskId);
  } catch (error) {
    handleFailure(error.message || "無法啟動分析。");
  }
}

async function generatePdf() {
  if (!activeTaskId || !currentResult) return toast("請先完成一份分析。" );
  const button = byId("generatePdf");
  button.disabled = true;
  byId("cancelTask").hidden = false;
  byId("cancelTask").disabled = false;
  terminalHandled = false;
  setBusy(true, "PDF 產生中…");
  byId("reportProgress").hidden = false;
  byId("reportProgressTitle").textContent = t("PDF 報告產生中");
  byId("reportProgressText").textContent = "正在準備報告內容";
  byId("reportProgressBar").max = 1;
  byId("reportProgressBar").value = 0;
  setResultStatus("reporting", "分析結果已完成", "正在產生 PDF 報告");
  try {
    await requestReport(activeTaskId);
    connectToTask(activeTaskId, lastEventId);
  } catch (error) {
    handleReportFailure(error.message || "無法啟動 PDF 工作。" );
  }
}

async function cancelCurrentTask() {
  if (!activeTaskId || terminalHandled) return;
  const button = byId("cancelTask");
  button.disabled = true;
  setWorkflow("cancelling", {
    title: "正在取消工作",
    detail: "目前網路請求結束後會立即停止，不會產生半份 PDF。",
    badge: "取消中",
  });
  try {
    await cancelTaskRequest(activeTaskId);
  } catch (error) {
    button.disabled = false;
    toast(error.message || "目前無法取消工作。");
  }
}

function focusForAnotherAnalysis() {
  setBusy(false);
  byId("stockQuery").focus();
  byId("stockQuery").select();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

initI18n();
initLearning();
initBeginnerMode();

byId("searchForm").addEventListener("submit", (event) => { event.preventDefault(); analyze(byId("stockQuery").value); });
byId("stockQuery").addEventListener("input", () => { window.clearTimeout(searchTimer); searchTimer = window.setTimeout(updateSuggestions, 180); });
byId("stockQuery").addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown") { event.preventDefault(); moveSuggestion(1); }
  else if (event.key === "ArrowUp") { event.preventDefault(); moveSuggestion(-1); }
  else if (event.key === "Enter" && activeSuggestion >= 0) { event.preventDefault(); chooseSuggestion(activeSuggestion); }
  else if (event.key === "Escape") hideSuggestions();
});
byId("stockQuery").addEventListener("blur", () => window.setTimeout(hideSuggestions, 120));
for (const button of document.querySelectorAll("[data-query]")) button.addEventListener("click", () => { byId("stockQuery").value = button.dataset.query; analyze(button.dataset.query); });
byId("exportCsv").addEventListener("click", () => { if (currentResult) downloadSummaryCsv(currentResult, getLocale()); });
byId("generatePdf").addEventListener("click", generatePdf);
byId("cancelTask").addEventListener("click", cancelCurrentTask);
byId("viewResults").addEventListener("click", () => { if (resultRendered) window.scrollTo({ top: byId("resultView").offsetTop - 76, behavior: "smooth" }); });
byId("retryAnalysis").addEventListener("click", () => analyze(lastQuery || byId("stockQuery").value));
byId("analyzeAnother").addEventListener("click", focusForAnotherAnalysis);
const shutdownButton = byId("shutdownApp");
if (shutdownButton) {
  shutdownButton.addEventListener("click", async () => {
    const token = document.querySelector('meta[name="shutdown-token"]')?.content || "";
    try { await shutdown(token); document.body.replaceChildren(node("main", { className: "empty-state" }, [node("h1", { text: "服務已關閉" }), node("p", { text: "現在可以關閉這個瀏覽器分頁。" })])); }
    catch (error) { toast(error.message || "無法關閉服務。"); }
  });
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && activeTaskId && !terminalHandled) recoverTask(activeTaskId).catch(() => {});
});

try {
  const saved = JSON.parse(sessionStorage.getItem(ACTIVE_TASK_KEY) || "null");
  if (saved && typeof saved.taskId === "string" && /^[a-f0-9]{32}$/.test(saved.taskId)) {
    activeTaskId = saved.taskId;
    lastQuery = typeof saved.query === "string" ? saved.query : "";
    if (lastQuery) byId("stockQuery").value = lastQuery;
    resetWorkflow();
    setBusy(true, "正在恢復任務…");
    setWorkflow("running", {
      title: "正在恢復分析進度",
      detail: "頁面已重新載入，正在讀取後端保留的任務狀態。",
      badge: "重新連線",
    });
    recoverTask(activeTaskId).catch(() => handleFailure("先前的分析任務不存在或已過期，請重新執行。"));
  }
} catch {
  sessionStorage.removeItem(ACTIVE_TASK_KEY);
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    try {
      const registration = await navigator.serviceWorker.register("/static/service-worker.js", { updateViaCache: "none" });
      await registration.update();
    } catch {
      // Offline support is optional; analysis remains available without it.
    }
  });
}
