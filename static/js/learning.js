import { byId, node, replace } from "./dom.js";
import { isEnglish } from "./i18n.js";
import {
  COURSE_TRACKS,
  CURRICULUM_SOURCES,
  QUESTIONS,
  TERM_ALIASES,
  TOPIC_LIBRARY,
  localized,
} from "./learning-curriculum.js";

const STORAGE_KEY = "twstock.learning.progress.v3";
const RETIRED_PROGRESS_KEYS = ["twstock.learning.progress.v1", "twstock.learning.progress.v2"];
const SESSION_LIMIT = 10;
const QUESTION_IDS = new Set(QUESTIONS.map(question => question.id));
const TOPICS = new Map(TOPIC_LIBRARY.map(topic => [topic.id, topic]));
const TRACKS = new Map(COURSE_TRACKS.map(track => [track.id, track]));

function L(zh, en) { return isEnglish() ? en : zh; }
function currentLanguage() { return isEnglish() ? "en" : "zh-TW"; }
function text(value) { return localized(value, currentLanguage()); }
function dialog() { return byId("learningDialog"); }
function topicFor(question) { return TOPICS.get(question.topicId); }
function trackFor(question) { return TRACKS.get(question.track); }

function readState() {
  let parsed = {};
  try {
    parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") || {};
  } catch {
    parsed = {};
  }
  const completed = new Set((Array.isArray(parsed.completed) ? parsed.completed : []).filter(id => QUESTION_IDS.has(id)));
  const mistakes = {};
  if (parsed.mistakes && typeof parsed.mistakes === "object") {
    for (const [id, count] of Object.entries(parsed.mistakes)) {
      if (QUESTION_IDS.has(id) && Number.isInteger(count) && count > 0) mistakes[id] = Math.min(count, 99);
    }
  }
  const favorites = new Set((Array.isArray(parsed.favorites) ? parsed.favorites : []).filter(id => QUESTION_IDS.has(id)));
  return { completed, mistakes, favorites };
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    completed: [...state.completed],
    mistakes: state.mistakes,
    favorites: [...state.favorites],
  }));
  refreshLearningProgress();
}

function statsFor(questions, state) {
  const completed = questions.filter(question => state.completed.has(question.id)).length;
  const review = questions.filter(question => state.mistakes[question.id]).length;
  return { total: questions.length, completed, review };
}

function favoriteButton(question, onChange) {
  const state = readState();
  const favorite = state.favorites.has(question.id);
  const control = button(
    favorite ? L("★ 已加入重點題目", "★ Added to key questions") : L("☆ 加入重點題目", "☆ Add to key questions"),
    "button secondary lesson-star",
    { "aria-pressed": String(favorite), dataset: { favorite: String(favorite) } },
  );
  control.addEventListener("click", () => {
    if (favorite) state.favorites.delete(question.id);
    else state.favorites.add(question.id);
    saveState(state);
    onChange();
  });
  return control;
}

function clearAnswerRecords() {
  const confirmed = window.confirm(L(
    "要清除所有已完成與錯題紀錄嗎？已標記的重點題目會保留。",
    "Clear all completed and missed-question records? Your starred key questions will be kept.",
  ));
  if (!confirmed) return;
  const state = readState();
  state.completed.clear();
  state.mistakes = {};
  saveState(state);
  courseHome();
}

function retirePreviousAnswerRecords() {
  RETIRED_PROGRESS_KEYS.forEach(key => localStorage.removeItem(key));
}

export function refreshLearningProgress() {
  const label = document.getElementById("learningProgressLabel");
  if (!label) return;
  const state = readState();
  label.textContent = `${state.completed.size} / ${QUESTIONS.length}`;
}

function button(label, className = "button secondary", attributes = {}) {
  return node("button", { type: "button", className, text: label, ...attributes });
}

function show(content, title = L("投資小教室", "Investment Learning Lab")) {
  byId("learningDialogTitle").textContent = title;
  replace("learningDialogContent", content);
  if (!dialog().open) dialog().showModal();
}

function progressLine(stats, label) {
  return node("div", { className: "lesson-progress" }, [
    node("span", { text: label }),
    node("progress", { value: stats.completed, max: Math.max(stats.total, 1), "aria-label": L("學習完成進度", "Learning completion progress") }),
  ]);
}

function sourcePanel(sourceIds, compact = false) {
  const sources = sourceIds.map(id => CURRICULUM_SOURCES[id]).filter(Boolean);
  if (!sources.length) return node("div");
  const list = node("ul", { className: compact ? "curriculum-source-list compact" : "curriculum-source-list" }, sources.map(source => {
    const link = node("a", {
      href: source.url,
      target: "_blank",
      rel: "noreferrer",
      text: text(source.title),
    });
    return node("li", {}, [
      link,
      node("small", { text: text(source.authority) }),
    ]);
  }));
  const details = node("details", { className: "curriculum-sources" }, [
    node("summary", { text: L("來源與查證依據", "Sources and verification basis") }),
    node("p", { text: L("題目以官方投資人教育與監理機構資料編寫；連結只供查閱，學習時不會向外部網站傳送資料。", "Questions are authored from official investor-education and regulator materials. Links are for review only; the app does not send learner data to outside sites.") }),
    list,
  ]);
  return details;
}

function sourceLink(question) {
  const source = CURRICULUM_SOURCES[question.sourceIds[0]];
  if (!source) return node("div");
  return node("p", { className: "question-source" }, [
    node("span", { text: `${L("依據：", "Based on: ")} ` }),
    node("a", { href: source.url, target: "_blank", rel: "noreferrer", text: text(source.title) }),
  ]);
}

function createSvg(tag, attributes = {}, content = "") {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  if (content) element.textContent = content;
  return element;
}

function chartAid(visual) {
  if (!visual) return null;
  const labels = {
    line_chart: L("折線圖：連接各期間價格，先標示觀察期間再談方向。", "Line chart: connects prices across periods; state the period before discussing direction."),
    candlestick_ohlc: L("K 線：實體連接開盤與收盤；上下影線顯示期間高低點。", "Candlestick: the body connects open and close; wicks show period high and low."),
    candlestick_wick: L("影線：記錄期間曾到達、但不一定收在那裡的價格。", "Wick: records prices reached during the period, not necessarily the closing price."),
    volume: L("成交量：描述交易活動；不單獨代表買進或賣出訊號。", "Volume: describes trading activity; it is not a stand-alone buy or sell signal."),
    trend: L("趨勢：短期與長期可能不同，請連同時間區間解讀。", "Trend: short and long horizons can differ; interpret it with the time window."),
    volatility: L("波動：描述價格變化幅度與頻率，不等於必然獲利或損失。", "Volatility: describes the size and frequency of price changes, not guaranteed profit or loss."),
  };
  const svg = createSvg("svg", { viewBox: "0 0 360 116", role: "img", "aria-label": labels[visual] || "Chart learning aid" });
  svg.append(createSvg("line", { x1: 16, y1: 94, x2: 344, y2: 94, stroke: "#9caab5", "stroke-width": 1 }));
  if (["candlestick_ohlc", "candlestick_wick"].includes(visual)) {
    const candles = [[75, 52, 20, 72], [145, 34, 46, 84], [215, 47, 28, 67], [285, 25, 44, 78]];
    candles.forEach(([x, y, top, bottom], index) => {
      const rising = index % 2 === 0;
      svg.append(createSvg("line", { x1: x, y1: top, x2: x, y2: bottom, stroke: rising ? "#08766c" : "#b4232c", "stroke-width": 3 }));
      svg.append(createSvg("rect", { x: x - 11, y, width: 22, height: index % 2 ? 25 : 20, fill: rising ? "#39a982" : "#df6b73", rx: 2 }));
    });
    svg.append(createSvg("text", { x: 17, y: 18, fill: "#44515e", "font-size": 11 }, L("示意 K 線，非交易訊號", "Illustrative candles, not a trade signal")));
  } else if (visual === "volume") {
    [42, 68, 32, 80, 53, 88, 45, 70].forEach((height, index) => {
      svg.append(createSvg("rect", { x: 28 + index * 39, y: 94 - height, width: 22, height, fill: "#77b8d9", rx: 2 }));
    });
    svg.append(createSvg("text", { x: 17, y: 18, fill: "#44515e", "font-size": 11 }, L("期間成交量示意", "Illustrative period volume")));
  } else {
    const path = visual === "volatility"
      ? "M18 68 L55 35 L90 78 L130 30 L165 84 L205 38 L242 70 L283 24 L338 55"
      : visual === "trend"
        ? "M18 80 L64 75 L108 68 L151 71 L196 50 L239 46 L285 31 L338 25"
        : "M18 76 L58 68 L101 72 L145 45 L188 57 L232 38 L280 49 L338 25";
    svg.append(createSvg("path", { d: path, fill: "none", stroke: "#2476a5", "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    svg.append(createSvg("text", { x: 17, y: 18, fill: "#44515e", "font-size": 11 }, L("示意價格路徑，非預測", "Illustrative price path, not a forecast")));
  }
  return node("figure", { className: "chart-aid" }, [svg, node("figcaption", { text: labels[visual] })]);
}

function optionOrder(question, position) {
  const seed = [...question.id].reduce((total, character) => total + character.charCodeAt(0), 0);
  const offset = (seed + position) % question.options.length;
  return question.options.map((option, index) => ({ option, index, order: (index + offset) % question.options.length }))
    .sort((left, right) => left.order - right.order);
}

function trackButton(track, stats) {
  const card = node("article", { className: "track-card", dataset: { track: track.id } }, [
    node("span", { className: "track-icon", text: track.icon }),
    node("div", { className: "track-copy" }, [
      node("p", { className: "eyebrow", text: `${L("主題", "Track")} ${track.order}` }),
      node("h3", { text: text(track.title) }),
      node("p", { text: text(track.summary) }),
      node("small", { text: `${L("完成", "Completed")} ${stats.completed} / ${stats.total} · ${L("難度", "Levels")} 1–5` }),
    ]),
  ]);
  const start = button(
    stats.completed === stats.total ? L("複習這個主題", "Review this track") : L("開始這個主題", "Start this track"),
    "button secondary",
  );
  start.addEventListener("click", () => startTrack(track.id));
  card.append(start);
  return card;
}

function courseHome() {
  const state = readState();
  const stats = statsFor(QUESTIONS, state);
  const reviewQuestions = QUESTIONS.filter(question => state.mistakes[question.id]);
  const favoriteQuestions = QUESTIONS.filter(question => state.favorites.has(question.id));
  const tracks = node("div", { className: "track-grid", "aria-label": L("課程主題", "Course tracks") }, COURSE_TRACKS.map(track => {
    const questions = QUESTIONS.filter(question => question.track === track.id);
    return trackButton(track, statsFor(questions, state));
  }));
  const start = button(
    stats.completed === stats.total ? L("開始整體複習", "Start full review") : L("繼續下一題", "Continue with next question"),
    "button primary",
  );
  start.addEventListener("click", () => startCourse());
  const review = button(
    reviewQuestions.length ? L(`複習錯題 (${reviewQuestions.length})`, `Review missed (${reviewQuestions.length})`) : L("目前沒有待複習錯題", "No missed questions to review"),
    "button secondary",
    { disabled: reviewQuestions.length ? null : "disabled" },
  );
  review.addEventListener("click", () => {
    if (reviewQuestions.length) startQueue(orderForReview(reviewQuestions, state).slice(0, SESSION_LIMIT), L("錯題複習", "Missed-question review"));
  });
  const favorites = button(
    favoriteQuestions.length ? L(`重點題目 (${favoriteQuestions.length})`, `Key questions (${favoriteQuestions.length})`) : L("尚未標記重點題目", "No key questions yet"),
    "button secondary",
    { disabled: favoriteQuestions.length ? null : "disabled" },
  );
  favorites.addEventListener("click", () => {
    if (favoriteQuestions.length) startQueue(orderForReview(favoriteQuestions, state).slice(0, SESSION_LIMIT), L("重點題目", "Key questions"));
  });
  const clear = button(L("清除答題記錄", "Clear answer records"), "button quiet clear-learning-records");
  clear.addEventListener("click", clearAnswerRecords);
  const overview = node("div", { className: "course-stats", "aria-label": L("學習統計", "Learning statistics") }, [
    node("div", {}, [node("strong", { text: String(QUESTIONS.length) }), node("span", { text: L("本機雙語題目", "local bilingual questions") })]),
    node("div", {}, [node("strong", { text: `${stats.completed} / ${stats.total}` }), node("span", { text: L("已完成", "completed") })]),
    node("div", {}, [node("strong", { text: String(reviewQuestions.length) }), node("span", { text: L("待複習錯題", "missed to review") })]),
    node("div", {}, [node("strong", { text: String(favoriteQuestions.length) }), node("span", { text: L("重點題目", "key questions") })]),
  ]);
  show(node("div", { className: "learning-content curriculum-home" }, [
    node("p", { className: "eyebrow", text: L("投資知識學程", "Investment learning path") }),
    node("h3", { text: L("從看懂數字，到辨識資訊與管理風險", "From reading numbers to assessing information and managing risk") }),
    node("p", { text: L("七個主題依概念由淺入深安排。請以理解、查證與風險意識為目標；題目不是投資建議，也不會預測價格。", "Seven tracks progress from foundations to application. The goal is understanding, verification, and risk awareness—not investing advice or price prediction.") }),
    node("p", { className: "learning-disclaimer", text: L("課程內容儲存在本機。每題都附有可追溯的公開教育來源；資料連結僅供查閱，不會在學習時連線抓取或傳送你的學習資料。", "Course content is stored locally. Every question cites a reviewable public educational source; links are optional and the app neither fetches them during study nor sends your learning data." ) }),
    overview,
    progressLine(stats, L(`總進度：${stats.completed} / ${stats.total}`, `Overall progress: ${stats.completed} / ${stats.total}`)),
    node("div", { className: "lesson-actions course-actions" }, [start, review, favorites, clear]),
    node("h3", { className: "track-heading", text: L("選擇學習主題", "Choose a learning track") }),
    tracks,
    sourcePanel(Object.keys(CURRICULUM_SOURCES)),
  ]));
}

function orderForReview(questions, state) {
  return [...questions].sort((left, right) => {
    const priority = (state.mistakes[right.id] || 0) - (state.mistakes[left.id] || 0);
    return priority || left.level - right.level || left.id.localeCompare(right.id);
  });
}

function startCourse() {
  const state = readState();
  const unseen = QUESTIONS.filter(question => !state.completed.has(question.id));
  const queue = unseen.length ? unseen : orderForReview(QUESTIONS, state);
  startQueue(queue.slice(0, SESSION_LIMIT), L("投資小教室", "Investment Learning Lab"));
}

function startTrack(trackId) {
  const state = readState();
  const questions = QUESTIONS.filter(question => question.track === trackId);
  const unseen = questions.filter(question => !state.completed.has(question.id));
  const queue = unseen.length ? unseen : orderForReview(questions, state);
  const track = TRACKS.get(trackId);
  startQueue(queue.slice(0, SESSION_LIMIT), text(track?.title) || L("投資小教室", "Investment Learning Lab"));
}

function startQueue(queue, title) {
  if (!queue.length) return courseHome();
  questionView(queue, 0, title);
}

function questionView(queue, position, title) {
  const question = queue[position] || queue[0];
  const topic = topicFor(question);
  const track = trackFor(question);
  const options = node("div", { className: "lesson-options" }, optionOrder(question, position).map(({ option, index }, order) => {
    const choice = button(`${String.fromCharCode(65 + order)}. ${text(option)}`, "lesson-option");
    choice.addEventListener("click", () => answerView(queue, position, title, index));
    return choice;
  }));
  const back = button(L("回到課程地圖", "Back to course map"));
  back.addEventListener("click", courseHome);
  const favorite = favoriteButton(question, () => questionView(queue, position, title));
  const stats = { completed: position, total: queue.length };
  const visual = chartAid(question.visual);
  const content = [
    progressLine(stats, `${L("本次練習", "This session")} ${position + 1} / ${queue.length}`),
    node("div", { className: "question-meta" }, [
      node("span", { text: `${L("主題", "Track")} ${track?.order || ""} · ${text(track?.title) || ""}` }),
      node("span", { text: `${L("難度", "Level")} ${question.level} / 5` }),
    ]),
    node("p", { className: "eyebrow", text: text(topic?.title) || L("投資概念", "Investment concept") }),
    node("h3", { text: text(question.prompt) }),
    visual,
    options,
    sourceLink(question),
    node("div", { className: "lesson-actions" }, [favorite, back]),
  ];
  show(node("div", { className: "learning-content" }, content), title);
}

function answerView(queue, position, title, selected) {
  const question = queue[position];
  const correct = selected === question.answer;
  const state = readState();
  if (correct) {
    state.completed.add(question.id);
    delete state.mistakes[question.id];
  } else {
    state.mistakes[question.id] = (state.mistakes[question.id] || 0) + 1;
  }
  saveState(state);
  const next = queue[position + 1];
  const continueButton = button(
    correct ? (next ? L("下一題", "Next question") : L("查看學習進度", "View learning progress")) : L("再試一次", "Try again"),
    "button primary",
  );
  continueButton.addEventListener("click", () => {
    if (!correct) questionView(queue, position, title);
    else if (next) questionView(queue, position + 1, title);
    else courseHome();
  });
  const map = button(L("課程地圖", "Course map"));
  map.addEventListener("click", courseHome);
  const explanation = text(question.explanation);
  const misconception = text(question.misconception);
  show(node("div", { className: "learning-content" }, [
    node("p", { className: "eyebrow", text: correct ? L("答對了", "Correct") : L("還差一點", "Not yet") }),
    node("h3", { text: correct ? L("重點是這個判斷範圍", "Here is the key boundary") : L("先釐清這個觀念", "Clarify this concept first") }),
    node("p", { className: `lesson-feedback${correct ? "" : " incorrect"}`, text: explanation }),
    node("p", { className: "learning-disclaimer", text: `${L("常見誤解：", "Common misconception: ")}${misconception}` }),
    sourceLink(question),
    node("div", { className: "lesson-actions" }, [continueButton, map]),
  ]), title);
}

function quickTerm(term) {
  const topicId = TERM_ALIASES[term];
  const topic = TOPICS.get(topicId) || TOPIC_LIBRARY[0];
  const questions = QUESTIONS.filter(question => question.topicId === topic.id);
  const start = button(L("用 5 題快速練習", "Practice with 5 questions"), "button primary");
  start.addEventListener("click", () => startQueue(questions, text(topic.title)));
  const map = button(L("查看完整課程", "View full course"));
  map.addEventListener("click", courseHome);
  show(node("div", { className: "learning-content" }, [
    node("p", { className: "eyebrow", text: L("指標旁快速教學", "Metric quick lesson") }),
    node("h3", { text: text(topic.title) }),
    node("p", { className: "quick-term-definition", text: text(topic.definition) }),
    node("p", { className: "learning-disclaimer", text: `${L("解讀界線：", "Interpretation boundary: ")}${text(topic.interpretation)}` }),
    chartAid(topic.visual),
    sourcePanel(topic.sourceIds, true),
    node("div", { className: "lesson-actions" }, [start, map]),
  ]), `${L("快速教學：", "Quick lesson: ")}${text(topic.title)}`);
}

export function initLearning() {
  retirePreviousAnswerRecords();
  refreshLearningProgress();
  byId("openLearning")?.addEventListener("click", courseHome);
  byId("openLearningFromEmpty")?.addEventListener("click", courseHome);
  byId("closeLearning")?.addEventListener("click", () => dialog().close());
  document.addEventListener("click", event => {
    const trigger = event.target.closest("[data-learning-term]");
    if (trigger) quickTerm(trigger.dataset.learningTerm);
  });
}
