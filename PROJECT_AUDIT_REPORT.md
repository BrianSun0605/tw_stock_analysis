# 台股研究室完整檢測報告

- 檢測日期：2026-07-18
- 專案路徑：`tw_stock_analysis`
- 檢測基準：Git baseline `ff558d7`
- 檢測範圍：71 個版本控制候選檔案，另含既有 cache／output 產物、圖片與字型完整性
- 最終定位：本機個人研究／教學原型

## 1. 結論

專案已從「可展示但資料口徑、安全與 UI 風險偏高」修正為可在本機進行研究的穩定原型。核心路徑已有測試、真實 2330 端到端驗證、PDF 轉圖檢查與三種 viewport 瀏覽器 QA。

目前仍**不建議商業化、對外公開部署或直接把評級用於資金決策**。主要阻擋項目不是程式能自行決定的 bug，而是資料授權、評分回測、模型適用範圍、字型／圖片授權與部署威脅模型。這些項目集中在第 10 節供專案負責人回答。

## 2. 審查範圍與方法

### 2.1 已逐類檢查

- Python：CLI、Web、共用服務、行情、代碼、月營收、EPS、股利、行事曆、同業、新聞、估值、PDF、cache、logger、helper、config。
- 前端：HTML 語意、CSS 響應式、JavaScript API／SSE／DOM／CSV、PWA Service Worker、CSP 相容性。
- 資料：TWSE／TPEx 官方公司清單、Yahoo Finance/yfinance、HiStock 條款與頁面結構、Google／Bing RSS。
- 演算法：TTM EPS、歷史 PE、PEG、營收趨勢、健康度、綜合評級、Piotroski、Altman、Graham、ETF 評分、風險提示。
- 產物：PDF 長名稱、連續 `multi_cell`、繁體字型、表格、免責聲明、名詞解釋；所有 11 頁轉 PNG 檢視。
- 資產：14 張 JPG、3 張 PNG/GIF 皆可解碼；3 個字型檔皆可解析，並檢查 OS/2 embedding flag 與 name/license metadata。
- 工程：依賴上限、Git ignore、官方快照更新器、測試、compile、Node syntax、pip dependency consistency。

### 2.2 重要外部依據

- [TWSE OpenAPI](https://openapi.twse.com.tw/) 提供上市公司基本資料與其他公開資料端點。
- [TPEx OpenAPI](https://www.tpex.org.tw/openapi/) 提供上櫃公司基本資料與財務資料端點。
- [yfinance 官方文件](https://ranaroussi.github.io/yfinance/) 明示工具用於研究／教育，並提醒 Yahoo Finance API 為個人使用。
- [HiStock 服務條款](https://histock.tw/term.aspx) 涉及自動化、內容重製／散布與智慧財產限制，因此專案改為預設不爬取。
- HiStock 的[月營收頁](https://histock.tw/stock/2330/%E6%AF%8F%E6%9C%88%E7%87%9F%E6%94%B6)與[季度 EPS 頁](https://histock.tw/stock/2330/%E6%AF%8F%E8%82%A1%E7%9B%88%E9%A4%98)僅用於核對舊解析器欄位，不再是預設來源。

## 3. 驗證摘要

| 檢查 | 結果 |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | 38 passed |
| `python -m pip check` | No broken requirements |
| Python `compileall` | 通過 |
| 5 個前端 module + Service Worker `node --check` | 通過 |
| `git diff --check` | 無 whitespace error |
| 官方股票快照 | TWSE + TPEx 共 1,981 筆；未達 800/700 門檻會拒絕覆寫 |
| 股票抽查 | 2330＝台積電／半導體；9942＝茂順／其他 |
| 真實端到端 smoke | 2330 與 0050 完成；0050 已驗證 preview 先於 PDF、10 段報告進度與實際下載連結 |
| PDF 壓力測試 | 11 頁產生成功、文字可抽取、全頁轉圖檢視 |
| UI viewport | 1440×900、768×1024、390×844，無水平 overflow |
| UI 互動 | 鍵盤搜尋、SSE mock render、CSV formula neutralization、XSS payload 均通過 |

本次真實 smoke 的 2330 資料為測試當下快照，不是報告中的永久行情主張；重要的是來源欄位與管線行為已核對。

## 4. 問題與修正紀錄

狀態定義：`已修復`、`已安全降級`、`待決策`、`後續改善`。

### 4.1 嚴重／高風險

| ID | 問題 | 影響 | 修正／狀態 |
|---|---|---|---|
| SEC-01 | `/shutdown` 無驗證且使用 `os._exit` | 任意網頁或本機程式可終止服務並造成非正常關閉 | 隨機 token、loopback、Host、Origin、自訂 header、Waitress graceful close；`已修復` |
| SEC-02 | 舊 UI 以 `innerHTML` 呈現新聞與 localStorage | 第三方 RSS 或本機資料可形成 DOM XSS | 全部改用 DOM node／`textContent`，URL 限 http/https，CSP 禁 inline；`已修復` |
| DATA-01 | yfinance 年營收曾被拆成假月資料 | 營收趨勢與圖表為虛構 | 完全取消；缺月營收就回傳空資料；`已修復` |
| DATA-02 | trailing EPS 曾被標成單季 EPS | TTM、PEG、成長率錯誤 | 改讀 `quarterly_income_stmt`，只用同季度 EPS 或淨利／股數；`已修復` |
| DATA-03 | HiStock HTML 預設自動爬取 | 條款、穩定性、欄位漂移風險 | 預設停用；僅在明確環境變數與自行取得授權時啟用；`已安全降級` |
| ALG-01 | TTM 接受不連續季度且找不到歷史值時回填最新 TTM | 估值前視偏誤、缺季仍計算 | 四季必須連續；歷史日期只用當時可取得財報；`已修復` |
| ALG-02 | 空資料、缺財務欄位仍可能得到健康度或綜合評級 | 看似精確但實為中性預設 | 健康度與總評都有 50% coverage gate；缺模型排除而非補 50；`已修復` |
| ALG-03 | Piotroski 缺欄位仍補分／使用代理變數 | F-Score 名稱與原模型不符 | 九項完整才給總分；每項回傳 available/passed；`已修復` |
| ALG-04 | Altman 使用錯誤欄位、零值 fallback、錯誤門檻 | 破產風險誤判 | 改為原始上市製造業公式與 1.81／2.99；金融／ETF 排除；適用產業仍 `待決策` |
| ALG-05 | 歷史 PE 對最新 EPS 有 look-ahead，且樣本過少仍估值 | 價格區間失真 | 設定保守可得日、至少 60 日 PE 樣本；`已修復` |
| SRC-01 | 靜態股票表只有約 371 筆且含錯誤名稱／產業 | 搜尋錯誤，例如 9942 | 官方 1,981 筆快照、完整性門檻、版本化 cache；`已修復` |
| SRC-02 | yfinance 殖利率與漲跌幅重複乘 100 | UI、同業與 PDF 百分比放大百倍 | 統一 decimal／percentage-point contract；`已修復` |
| PDF-01 | 連續多段 `multi_cell` 後游標留在右邊界 | 真實 PDF 產生時可拋 `FPDFException` | 共用 `_multi_cell` 每段重設 left margin；新增回歸測試；`已修復` |
| WEB-01 | CLI 與 Web 各自維護分析流程 | 來源、ETF suffix、評分與報告不一致 | 統一至 `services/analysis.py`；`已修復` |

### 4.2 中風險／正確性

| ID | 問題 | 修正／狀態 |
|---|---|---|
| ALG-06 | EPS 成長只有四季資料就計算 | 需 8 個連續季度，否則 `None`；`已修復` |
| ALG-07 | 負成長營收被誤認為加速、缺月不切斷連續期 | 改用 percentage-point 斜率、穩定帶與月份連續性；`已修復` |
| ALG-08 | 負 OCF 可能因 absolute ratio 得到品質加分 | 負 OCF 明確扣分；`已修復` |
| ALG-09 | 獲利能力使用絕對 EPS，偏袒高面額／高 EPS 公司 | 移除，改用 ROE／margin／ROA；`已修復` |
| ALG-10 | 波動率忽略日期缺口 | 依時間跨度正規化；`已修復` |
| ALG-11 | 「調整後 PE」與歷史分位混在一起 | 分離 `growth_adjusted_multiples` 與歷史 PE；`已修復` |
| SRC-03 | 上櫃股票錯用 `.TW` | 市場 suffix 統一由 `_suffix(market)` 決定；`已修復` |
| SRC-04 | 官方中文名稱／產業被 Yahoo 英文覆蓋 | 官方欄位優先，英文另存 `name_en`；`已修復` |
| SRC-05 | 股利把 YTD 與完整年度混用 | 分開 `latest_yield`、`ytd_yield`、年度 status；`已修復` |
| SRC-06 | 配息月份為推估值 | 改從實際 dividend event month；`已修復` |
| SRC-07 | Google 日期 RFC822 解析錯、Bing 被當 HTML | 共用 RSS parser 與 RFC822/ISO 日期正規化；`已修復` |
| SRC-08 | MoneyDJ／Anue／UDN 失效 scraper 仍像可用來源 | 保留明確 disabled adapter，不納入 aggregator；`已修復` |
| SRC-09 | provider exception 被吞掉 | 聚合結果回傳 per-provider status/error；`已修復` |
| CACHE-01 | Windows 不合法 `:`、路徑穿越與非原子寫入 | slug+SHA、lock、temp+fsync+replace；`已修復` |
| CACHE-02 | 語意變更後可能讀到舊假資料 cache | 股票 mapping v4、revenue v3、EPS v3；`已修復` |
| UI-01 | 1,700+ 行 inline HTML/CSS/JS、紫色裝飾與大量貓圖 | 語意 HTML + CSS + 5 個 JS module；專業投資工具視覺；`已修復` |
| UI-02 | 前端另算評級，與 PDF 不同 | 只呈現後端評級；`已修復` |
| UI-03 | CSV 無 RFC 4180 quote 且可公式注入 | 全欄 quote、雙引號 escaping、`=+-@` 前綴中和；`已修復` |
| PWA-01 | Service Worker cache-first 可能保留舊 JS，且動態 API 不應快取 | v4 network-first 靜態資源；task/API/download 完全排除；註冊時略過 HTTP cache；`已修復` |
| WEB-02 | 任務表無 lock／上限／TTL | lock、最多 20、TTL 與 pruning；`已修復`，可再縮小上限 |
| WEB-03 | SSE 可能暴露 traceback | 使用者只收穩定訊息，完整錯誤留本機 logger；`已修復` |
| WEB-04 | 第 5/5 步後才開始同步產生 PDF，預覽與完成通知都被阻塞 | preview callback 先發布分析結果，PDF 另走逐章進度；`已修復` |
| WEB-05 | SSE 中的 `NaN`／Infinity 不是合法瀏覽器 JSON，真實 ETF preview 解析失敗 | 所有非有限數值遞迴轉 `null`，輸出以 `allow_nan=False` fail closed；`已修復` |
| WEB-06 | SSE 斷線即刪除任務，重新整理或短暫斷線後無法恢復 | 任務快照、事件 ID、Last-Event-ID 重播、10 分鐘終態保留與 session 恢復；`已修復` |
| UI-04 | 「5/5」看似全部完成，但沒有結果、PDF 狀態、檔名或下一步 | 分析／PDF 雙進度、成功與部分失敗狀態、明確下載 CTA、再次分析操作；`已修復` |
| PDF-02 | AUM 單位、殖利率倍率、YTD 標籤與來源聲明錯 | 全部校正並動態列出本次來源；`已修復` |
| PDF-03 | 長名稱、警告、摘要用單行 cell | 改用 multi-cell 與長名稱縮字；`已修復` |
| DOC-01 | README 聲稱不存在來源／不一致權重／舊 Python | 全面重寫；`已修復` |
| GIT-01 | cache、PDF、PYC、temp 混入版本候選 | `.gitignore` 與 baseline；`已修復` |

## 5. UI／UX 檢查

### 5.1 已完成

- 資訊層級：搜尋 → 公司／價格／評級 → 六張 KPI → 估值／健康度／財務 → 風險／品質／新聞。
- 視覺：深海軍藍、白色資料卡、藍綠狀態色；B 級固定為藍色，不再使用紫色主視覺。
- 品牌：貓只保留 36px logo 與空狀態，不再作大面積背景。
- 響應式：桌機雙欄、平板轉單欄、手機 2-column KPI；測試未出現水平 overflow。
- 可操作性：input label、skip link、ARIA listbox、上下鍵／Enter／Esc、focus-visible、reduced-motion。
- 資料誠實性：每個空值使用「資料不足」，coverage banner 提醒缺漏，不生成前端假評分。
- 任務可見性：五步分析與 PDF 寫檔分開；分析結果先顯示，PDF 完成後明示實際檔名與儲存位置。
- 恢復能力：SSE 事件可重播，重新整理頁面可從 task snapshot 恢復預覽、報告進度與完成下載。
- 安全：不使用動態 HTML 字串；第三方 URL 僅允許 http/https。

### 5.2 後續改善

- [ ] UI-F01 建立正式設計 token 文件與元件展示頁。
- [ ] UI-F02 對色彩、鍵盤、螢幕閱讀器執行 WCAG 2.2 AA 專項稽核。
- [ ] UI-F03 將目前手動 Playwright QA 固化為 CI 測試。
- [ ] UI-F04 增加「資料來源與日期」可展開明細，逐欄顯示 provenance。
- [ ] UI-F05 在長分析中提供取消任務，不只關閉 SSE。

## 6. 演算法審查

### 6.1 現有模型可解釋範圍

- PE 分位法：適合「同公司、同口徑、盈餘為正」的歷史相對估值，不是絕對目標價。
- PEG：高度依賴成長率期間；負成長、基期低與一次性損益時不可靠。
- 健康度：規則式 dashboard，不是統計預測器。
- Piotroski：完整九項才可稱 F-Score；目前 yfinance 對台股常缺前期欄位，因此多數會 unavailable。
- Altman：現在公式正確，但原始模型以上市製造業為主；台灣非製造業的外部效度未驗證。
- Graham Number：經典保守估值參考，不適合所有成長股或無形資產公司。
- ETF：費用率、折溢價、規模、流動性、殖利率的規則式評分；未含 tracking difference、持股重疊、指數方法與稅務。

### 6.2 尚未解決的模型風險

- [ ] ALG-F01 用至少一個完整多空週期回測各分數與未來 1/3/6/12 月報酬、回撤。
- [ ] ALG-F02 先指定 benchmark、再定義「好評級」；避免用事後挑選門檻。
- [ ] ALG-F03 使用實際公告時間取代統一 Q1/Q2/Q3/Q4 可得日期。
- [ ] ALG-F04 對金融、營建、航運、景氣循環與 ETF 建立不同模型族。
- [ ] ALG-F05 同業比較改為可解釋的 peer selection，而非股票代號順序前五檔。
- [ ] ALG-F06 對 corporate action、負 EPS、極端 PE、KY 公司與資料修訂建立測試資料集。

## 7. 資料與來源審查

### 7.1 目前資料契約

- `dividendYield`、margin、ROE、growth：後端存 decimal ratio；UI 在顯示時乘 100。
- peer `dividend_yield` 與 dividend 模組 `latest_yield`：已是 percentage points。
- revenue `revenue`：原解析器口徑為千元；只有明確 opt-in HiStock 時才存在。
- EPS：單季值；`source` 明確為 `Yahoo Finance quarterly_income_stmt` 或 opt-in HiStock。
- snapshot：含 `schema_version`、`fetched_at`、上市／上櫃官方 endpoint、每檔 source 與 industry code。

### 7.2 仍需改善

- [ ] DATA-F01 設計官方月營收歷史管線，取代 HTML scraper。
- [ ] DATA-F02 每個輸出欄位加入 `source`、`as_of`、`fetched_at`、`unit`、`transform`。
- [ ] DATA-F03 建立 source schema contract；來源欄名變更時 fail closed。
- [ ] DATA-F04 對官方快照做增刪 diff 與人工抽查，而非只看筆數。
- [ ] DATA-F05 對 Yahoo/yfinance 欄位漂移建立錄製 fixture，不依賴 live test。
- [ ] DATA-F06 新聞 RSS 只保留索引與短摘要，避免內容重製；確認 Google/Bing 使用政策。

## 8. 安全與部署審查

### 8.1 已防護的本機威脅

- shutdown CSRF／無授權終止。
- RSS／localStorage DOM XSS。
- CSV formula injection。
- 任意檔案下載與非 PDF download。
- cache path traversal 與半寫 JSON。
- traceback 對前端曝露。
- Service Worker 快取分析結果與控制端點。

### 8.2 明確不在目前安全模型內

- 公網使用者、帳號、權限、租戶隔離、API key。
- 反向代理與 `X-Forwarded-*` 信任。
- CSRF session、登入、速率限制、WAF、TLS、稽核 log。
- 多使用者同時分析與資源配額。

因此目前只應監聽 loopback。若要 LAN／公網部署，需重新做威脅模型，不可只把 host 改成 `0.0.0.0`。

## 9. 工程品質與檔案狀態

### 9.1 Git 應追蹤

- Python／HTML／CSS／JS 原始碼。
- `tests/`、`scripts/`、requirements、README、稽核報告。
- `stock/official_stock_snapshot.json`。
- UI 必要 icon 與 PDF 必要字型（但授權待確認）。

### 9.2 Git 不應追蹤

- `cache/`、`output/`、`tmp/`、`__pycache__/`、`*.pyc`、pytest cache、coverage、`.env`、IDE/OS metadata。

### 9.3 資產風險

- `msjh.ttc`、`msjhbd.ttc` metadata 明示 Microsoft supplied font，fsType=8；嵌入 PDF 與把原始字型檔隨專案散布是不同權利，需確認。
- `STKAITI.TTF` 與貓圖片沒有專案內 license/provenance 文件。
- `picture/side` 與 `picture/border` 已不在新版 UI 使用，因此停止追蹤但保留本機檔案；若未來要再散布，仍須補齊 provenance／license。

## 10. 需要你回答／確認的 checklist

這一節只列不能由程式自行替專案負責人決定的事項。回答時可直接寫 `Q01: ...`。

- [ ] **Q01 部署範圍**：只供單機個人使用，還是未來會在 LAN／公網提供多人使用？
- [ ] **Q02 商業用途**：是否會收費、內嵌商業產品、對客戶展示或散布資料？這會直接影響 Yahoo/yfinance、新聞與其他來源授權。
- [ ] **Q03 月營收來源**：要（A）維持「資料不足」、（B）取得 HiStock 書面授權、或（C）投入官方歷史月營收管線？建議 C。
- [ ] **Q04 評級目的**：A/B/C/D 要預測哪個期間、哪種結果（超額報酬、下檔風險、品質或純研究排序）？沒有 target 就無法正確回測。
- [ ] **Q05 模型權重**：是否保留目前健康度與總評權重，或先停用字母評級直到回測完成？保守建議停用對外字母評級。
- [ ] **Q06 Altman 適用性**：只對製造業顯示原始模型，還是要為非製造業導入 Z'-Score／Z''-Score 與台灣市場校準？
- [ ] **Q07 新聞情緒**：保留明確標示的關鍵字分類、完全移除情緒，或投入有標註資料的中文模型？
- [ ] **Q08 資料更新政策**：官方股票快照要手動、每週或每月更新？誰負責檢查增刪 diff？
- [ ] **Q09 字型授權**：是否有權散布 Microsoft JhengHei／STKaiti 原始檔？若不確定，是否改用 SIL OFL 的 Noto Sans TC？建議改用 Noto。
- [ ] **Q10 圖片授權**：目前仍使用的貓 icon 來源與授權為何？未使用 side/border 已停止追蹤並只留本機。
- [ ] **Q11 專案 license**：程式碼要採私人版權、MIT、Apache-2.0 或其他授權？目前 repository 沒有 LICENSE。
- [ ] **Q12 新聞來源**：是否要恢復 MoneyDJ／Anue／UDN？若要，需使用正式 API／授權，不建議恢復 HTML selector。

## 11. 建議開發順序

### Phase 0：發布阻擋

- [ ] 回答 Q01–Q12。
- [ ] 解決 yfinance／Yahoo、新聞、字型、圖片的授權範圍。
- [ ] 決定是否在回測前隱藏字母評級。
- [ ] 決定月營收正式來源。

### Phase 1：資料可信度

- [ ] 完成 DATA-F01～F06。
- [ ] 建立每欄 provenance 與 UI 詳情。
- [ ] 以實際公告日重算歷史 PE。
- [ ] 建立固定來源 fixture 與 schema drift test。

### Phase 2：模型驗證

- [ ] 定義 target／benchmark／universe／交易成本。
- [ ] Walk-forward 回測，分產業與市值報告 coverage、IC、hit rate、drawdown。
- [ ] 校準門檻後才凍結 A/B/C/D。

### Phase 3：產品與部署

- [ ] Playwright CI、WCAG 稽核、cancel task。
- [ ] 若多人使用，加入 auth、CSRF、rate limit、job queue、持久狀態、監控與 TLS。
- [ ] 建立版本化 release 與資料／模型變更紀錄。

## 12. 完成定義

只有同時符合下列條件，才應把專案稱為「可正式發布」：

- [ ] 所有 Q01–Q12 有書面決定。
- [ ] 所有資料與資產有合法且符合部署情境的授權。
- [ ] 評分已依預先定義 target 做 out-of-sample 驗證，或 UI 不再顯示預測性字母評級。
- [ ] 關鍵來源有 schema drift 與 outage 降級測試。
- [ ] 公開部署（若有）通過新的安全稽核。
- [ ] CI 在乾淨環境通過 Python、前端、PDF 與 E2E 測試。

---

本報告是後續開發的 canonical checklist。`PROGRESS.md` 只記錄目前完成狀態；`improvement_prompt.md` 已封存，不應再當作需求來源。
