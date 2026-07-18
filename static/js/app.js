import { searchStocks, shutdown, startAnalysis, streamAnalysis } from "./api.js";
import { byId, node, replace } from "./dom.js";
import { downloadSummaryCsv } from "./export.js";
import { renderResult } from "./render.js";

let suggestions = [];
let activeSuggestion = -1;
let searchController = null;
let activeStream = null;
let currentResult = null;
let searchTimer = null;

function toast(message) {
  const element = byId("toast");
  element.textContent = message;
  element.hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => { element.hidden = true; }, 4200);
}

function setBusy(busy) {
  byId("analyzeButton").disabled = busy;
  byId("stockQuery").disabled = busy;
  byId("analyzeButton").textContent = busy ? "分析中…" : "開始分析";
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
  }, [node("strong", { text: item.stock_id }), node("span", { text: item.name }), node("small", { text: [item.market, item.industry].filter(Boolean).join(" · ") })])));
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
  const match = String(message).match(/\[(\d)\/5\]/);
  const step = match ? Number(match[1]) : 0;
  if (step) {
    byId("progressCounter").textContent = `${step} / 5`;
    byId("progressBar").value = step;
  }
  byId("progressText").textContent = String(message).replace(/^\[\d\/5\]\s*/, "");
  const item = node("li", { text: message });
  byId("progressLog").append(item);
}

async function analyze(query) {
  const value = String(query || "").trim();
  if (!value) return toast("請先輸入股票代號或名稱。");
  activeStream?.close();
  currentResult = null;
  hideSuggestions();
  setBusy(true);
  byId("emptyState").hidden = true;
  byId("resultView").hidden = true;
  byId("analysisProgress").hidden = false;
  replace("progressLog", []);
  byId("progressCounter").textContent = "0 / 5";
  byId("progressBar").value = 0;
  byId("progressText").textContent = "正在建立分析";
  byId("downloadPdf").hidden = true;
  byId("exportCsv").disabled = true;
  try {
    const { task_id: taskId } = await startAnalysis(value);
    activeStream = streamAnalysis(taskId, {
      log: updateProgress,
      result: (data) => {
        currentResult = data;
        renderResult(data);
        byId("analysisProgress").hidden = true;
        byId("resultView").hidden = false;
        byId("exportCsv").disabled = false;
        window.scrollTo({ top: byId("resultView").offsetTop - 76, behavior: "smooth" });
      },
      done: (filename) => {
        setBusy(false);
        if (filename) {
          const link = byId("downloadPdf");
          link.href = `/download/${encodeURIComponent(filename)}`;
          link.hidden = false;
        }
      },
      error: (message) => {
        setBusy(false);
        byId("analysisProgress").hidden = true;
        if (!currentResult) byId("emptyState").hidden = false;
        toast(message || "分析失敗，請稍後再試。");
      },
    });
  } catch (error) {
    setBusy(false);
    byId("analysisProgress").hidden = true;
    byId("emptyState").hidden = false;
    toast(error.message || "無法啟動分析。");
  }
}

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
byId("exportCsv").addEventListener("click", () => { if (currentResult) downloadSummaryCsv(currentResult); });
byId("shutdownApp").addEventListener("click", async () => {
  const token = document.querySelector('meta[name="shutdown-token"]')?.content || "";
  try { await shutdown(token); document.body.replaceChildren(node("main", { className: "empty-state" }, [node("h1", { text: "服務已關閉" }), node("p", { text: "現在可以關閉這個瀏覽器分頁。" })])); }
  catch (error) { toast(error.message || "無法關閉服務。"); }
});

if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("/static/service-worker.js").catch(() => {}));
