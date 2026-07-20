# 專案進度

更新日期：2026-07-20

## 已完成

- [x] Phase 0：主檔搜尋、同業、日期欄位、按需 PDF、單工與檔案隔離。
- [x] Phase 1：官方月營收／財報、逐欄來源、Yahoo 備援、共享行情快照、SQLite cache、三天 PDF、取消與資源上限。
- [x] Phase 2 可安全上線的部分：成長／安全契約完全分開，不平均；ETF、金融適用邊界已實作；歷史未過門檻時正式 A～F 保持空白。
- [x] Phase 3 可由程式確認的部分：事實／模型分區、新聞分區、對比、combobox、焦點、44px 觸控目標、UI 規範、Noto OFL、第三方與隱私文件、固定版本與 CI。
- [x] Phase 4 portable 與 installer：LocalAppData、唯讀 bundle、單一實例、loopback、按需 PDF、版本、ZIP、Setup EXE 與 SHA-256。
- [x] 官方主檔擴充：schema 4 共 2,773 筆，已納入興櫃、ETF、ETN、特別股與 REIT；權證排除，英數代碼可直接輸入。
- [x] 完整檢查：127 項 pytest、Ruff、pip check、pip-audit、10 個 JavaScript 語法檢查通過；2330 官方 24 個月營收與 0050 ETF 真實資料 smoke test 通過。
- [x] Inno Setup 6.7.3 安裝版完成：實際安裝、啟動、重複啟動、正常關閉與解除安裝均通過；解除安裝保留使用者資料。
- [x] Browser 真實驗收完成：鍵盤搜尋、完整分析、300px 手機、627px 平板、1187px 桌面、PDF 13/13、結果焦點與 console 均通過。
- [x] 修正手機整頁水平捲軸與關閉後背景 EXE 殘留；兩者都有回歸測試，最終打包 App 已重跑確認。
- [x] PDF 繁中亂碼修正：PDF 文字改用 Noto Sans TC TrueType 字型，確認輸出為 CIDFontType2；保留 OTF 給 Matplotlib 圖表使用。
- [x] 官方月營收趨勢修正：以 TWSE／TPEx 最新一期搭配 MOPS 官方歷史封存補齊 24 個月，並推導封存資料缺少的 MoM／YoY。
- [x] ETF 結構與新手 UI：官方 ETF 身分、追蹤指數與 TPEx AUM 可穿透 Yahoo 失敗情境；ETF 改用市價與淨值／基金結構／交易與收益，個股改用價格與估值／公司體質與成長／收益分組。
- [x] 投資小教室 MVP：12 個新手互動任務、答題回饋與常見誤解、個股／ETF 指標旁快速教學、本機瀏覽器進度；教育內容不作買賣建議。

## 尚未完成／不能假裝完成

- [ ] 成長資料仍不是逐公告版本的 point-in-time；正式成長評級未通過預定 MAE 門檻。
- [ ] 一般公司財務安全仍缺台灣歷史危機結果標籤與 point-in-time 財報；目前只顯示 Altman Z 財務結構參考區間，不是破產機率或正式台灣評級。
- [ ] ETF 成分股加權成長模型與金融／保險專用監理模型待建立。
- [ ] ETN、REIT、特別股已可搜尋，但專用分析模型尚未完成；目前明確停止，不誤套普通股公式。
- [ ] Axe 與實體螢幕閱讀器仍未執行；Browser 內的基本 DOM 無障礙檢查已通過，但不把它當成 Axe 或真人輔具驗收。
- [ ] Setup EXE 與主程式目前沒有 Windows 數位簽章；公開散布時可能出現 SmartScreen 警告。
- [ ] 解除安裝會刪除全部程式內容，但目前留下空的安裝資料夾；不影響程式或使用者資料，列為低優先清理問題。
- [x] 正式開源授權：MIT License，Copyright (c) 2026 胖貓貓工作室；原始碼、portable 與 installer 均納入 LICENSE。
- [x] CI 已加入 pip-audit；目前 runtime 相依套件沒有查到已知漏洞。
- [x] Ruff 已格式化既有 Python 檔；67 個 Python 檔通過 `ruff format --check`，CI 已加入格式 gate。

## 主要成果位置

- 使用與架構：[README.md](README.md)
- 完整證據與 checklist：[PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md)
- Windows portable：[release/TWStockAnalysis-portable-0.2.0-dev.zip](release/TWStockAnalysis-portable-0.2.0-dev.zip)
- Windows 安裝版：[release/TWStockAnalysis-Setup-0.2.0-dev.exe](release/TWStockAnalysis-Setup-0.2.0-dev.exe)
- 開源授權：[LICENSE](LICENSE)
- 校驗碼：[release/SHA256SUMS.txt](release/SHA256SUMS.txt)

## 2026-07-20：投資小教室擴充

- [x] 投資小教室已由 12 個單一新手任務擴充為 7 個主題軌、44 個概念、220 題本機雙語題目，涵蓋投資基礎、K 線與價格圖、財報與估值、ETF、產業、新聞識讀及策略與風險。
- [x] 加入主題卡、難度 1–5、整體／分主題進度、錯題複習、答案位置輪替、圖表概念示意與每題來源連結；原有 12 題完成紀錄可遷移。
- [x] 題目使用 SEC Investor.gov、SEC、FINRA 與臺灣證券交易所的可查證教育資料重新編寫；正式使用時不連線抓題目或傳送學習資料。
- [x] 新增中英文對等的來源與維護規則：[docs/INVESTMENT_LEARNING_SOURCES.md](docs/INVESTMENT_LEARNING_SOURCES.md)／[docs/INVESTMENT_LEARNING_SOURCES.en.md](docs/INVESTMENT_LEARNING_SOURCES.en.md)。
- [x] 已重設既有答題紀錄，並新增「清除答題記錄」按鈕及星號重點題目功能；清除完成／錯題紀錄不會移除重點題目。

## 2026-07-20：成長與財務安全公式可追溯化

- [x] 成長模型修正營收規模特徵被截斷為固定值的缺陷，採用驗證期選出的 ridge＋收縮＋中位殘差校正 v2 公式；以全市場 1,696 家上市／上櫃公司、6,619 筆最終保留樣本回測，MAE 0.1703，較零成長基準改善約 4.8%。
- [x] 保留原先門檻不放寬：成長 MAE 仍差 5% 目標約 0.04 個百分點，且歷史封存未證明 point-in-time，因此正式 A–F 仍保持空白；畫面與 PDF 顯示「僅供研究與教學參考」及可展開的公式、特徵、參數與分級規則。
- [x] 一般公司財務安全取消任意 0–100 加權與實驗 A–F，改為完整、期間一致年度財報才計算的原始公開公司 Altman Z 財務結構參考；金融與不適用商品仍明確停止。
- [x] 已稽核現行 TWSE／TPEx `ci` 官方財報 API 的 1,927 家可配對一般公司：資產負債表核心欄位齊全，但精確 EBIT 欄位為 0 家，故不假稱能以該 API 建立全市場、已校準的破產預測。
- [x] 新增雙語模型卡、全市場欄位稽核腳本、公式／免責聲明 UI 與 PDF；120 項 pytest、Ruff、前端語法與 `pip check` 均通過。

## 2026-07-20：以現有資料提供可用的參考分級

- [x] 保留正式部署門檻，但把既有成長公式的 A–F 輸出改為明確標示的研究／教育「成長參考分級」。分級依未來連續 12 個月營收估計與正成長樣本占比而定，附非投資建議聲明，不會因為畫面顯示而變成正式評級。
- [x] 新增 `financial_structure_reference_v3`：使用同季官方季度財報的資產、負債、保留盈餘、營業利益與營收；僅將年初至今的損益欄位以 `4／已公告季度` 年化，並輸出透明的 A／C／E 財務結構參考分級。
- [x] 新增中英文 v3 模型卡、公式分級揭露、CSV／PDF 欄位與 2330 端到端 smoke test；實測輸出為成長參考 D、財務結構參考 A，必要欄位覆蓋率 100%。

## 2026-07-20：英文 PDF 報告內容對等

- [x] 將原本縮減版的英文 PDF 路徑補齊為對等詳細內容：基本資料、股價、近期月營收、季度 EPS、估值輸入、健康度與品質、財務指標與官方財報來源、風險訊號、股利歷史、新聞摘要、名詞表與免責聲明。
- [x] 修正英文估值頁誤從分析物件最上層讀取合理價欄位的問題，改為正確讀取 `fair_price_range`。
- [x] 以 2330 實際資料在暫存目錄生成比較：中英文報告皆為 15 頁；英文每一頁均有可擷取文字，所有必要的詳細章節標題皆存在。
- [x] 新增英文詳細報告回歸測試，未來資料完整時必須至少產生 15 頁 PDF。

## 2026-07-20：英文 PDF 動態分析文字本地化

- [x] 修正英文 PDF 的 PEG 解讀、風險訊號與分析敘述仍直接輸出中文的問題；英文報告現在由結構化分析結果重建敘述，不依賴中文 UI 用的分析段落。
- [x] 完整翻譯現有系統產生的風險類型、短／中／長期標籤、PEG 結論、營收、估值、波動、EPS、Piotroski、Altman、Graham、流動性、獲利與健康度訊息；保留公司名稱、新聞與其他原始來源文字。
- [x] 加入回歸測試，確保含中文分析引擎輸入時，英文動態分析與風險訊號不會輸出任何中文字元；PDF 報表測試、Ruff 與編譯檢查通過。

## 2026-07-20：文件同步與開發工作區清理

- [x] 已檢視全部 Markdown 文件；README、開發交接、稽核補充、UI 規範、進度紀錄與中英文模型卡已同步到雙語 UI／PDF、220 題投資小教室、參考分級與 123 項測試的現況。隱私、授權、第三方通知、題庫來源與已封存的歷史需求文件內容仍正確，因此不改寫其事實內容。
- [x] 已將舊成長 v1、財務安全 v1 與財務結構 v2 模型卡標示為歷史版本，連結至現行 v2 成長模型與 v3 財務結構參考，避免後續開發誤用舊公式。
- [x] 在確認沒有 App／Python 工作執行後，已清除 `cache/`、`build/`、`logs/`、`__pycache__/`、`app_runtime/__pycache__/`、`.pytest_cache/` 與 `.ruff_cache/`，共約 67 MiB。`.venv/`、`dist/`、`release/` 與 `output/` 均排除在本次清理目標之外。

## 2026-07-20：GitHub + Render 公開展示部署準備

- [x] 新增 `render.yaml`、`.python-version` 與中英文部署文件；Render 可從 GitHub 的 `main` 分支以 Python 3.12 啟動單一 Web Service，健康檢查為 `/healthz`，CI 通過後才自動部署。
- [x] 新增獨立 `TWSTOCK_APP_MODE=web`：讀取平台 `PORT`、綁定 `0.0.0.0`、不開啟瀏覽器、不使用桌面單一執行個體鎖；桌面版仍只綁定 `127.0.0.1`。
- [x] 公開模式移除 `/shutdown` 路由和關閉按鈕，使用暫存資料根目錄與較小的容量／保留上限，並對每個來源預設限制每小時 6 次分析、每分鐘 60 次搜尋；全服務仍只執行一個重工作。
- [x] 新增公開模式、健康檢查、關機面與頻率限制回歸測試；實際以 `TWSTOCK_APP_MODE=web` 本機 smoke test 驗證 `/healthz` 200、首頁無關機 token／按鈕、`POST /shutdown` 404。最終 `ruff check .`、`ruff format --check .`、127 項 pytest 與 10 個 JavaScript `node --check` 全數通過。
- [x] Git for Windows 已由官方簽章安裝，GitHub remote `https://github.com/BrianSun0605/tw_stock_analysis.git` 已建立，首次提交 `2a3da08` 已推送至 `main`；快取、輸出、虛擬環境與打包產物均由 `.gitignore` 排除。
- [ ] 實際 Render Blueprint 仍需 repository 擁有者登入 Render 並授權 GitHub repository 後完成；步驟見 `docs/DEPLOYMENT_RENDER.md`。
