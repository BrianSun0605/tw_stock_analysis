# 台股研究室：白話版檢測報告與修正計畫

- 檢測日期：2026-07-18
- 專案版本：main / adcdea5
- 專案根目錄：C:\active\胖貓貓的遊戲工作室\投資神器\tw_stock_analysis
- 初次稽核只修改本報告；後續已依 Phase 0、Phase 1 開始修改產品程式
- 再驗證日期：2026-07-19
- 文件用途：後續 debug 與修正驗收 checklist

## 已確認的產品方向

以下產品方向已由產品負責人確認，不再列為待回答問題：

1. 工具會公開給其他人使用，但會包裝成「每位使用者在自己電腦執行」的本地 App。
2. 專案採免費開源方式散布；每台電腦同時只有一位使用者，正常情況只需要一個分析工作。
3. 使用兩個獨立 A～F 評級：預測未來 12 個月營收／EPS 成長的「成長評級」，以及公司財務出問題風險的「財務安全評級」。
4. 帶有預估或模型判讀的內容放在「模型推估區」；直接抓到、可追溯的資料放在「已確認資料區」。
5. 目標主檔範圍包含上市、上櫃、興櫃、TDR、特別股、ETF、ETN 與 REIT；排除權證與債券。schema 4 官方快照已擴充為 2,773 筆。
6. 資料來源以 TWSE／TPEx／公開資訊觀測站等官方資料為主，Yahoo 只作備援；畫面必須標示來源。
7. 可更換內嵌字型，但 UI 必須先建立一致的設計規範。
8. release 不自動產生 PDF，但分析完成後提供「產生並下載 PDF」選項；dev 可自動產生作 QA。output 每個檔案保存三天，超過三天逐檔清除。
9. 採完整證券主檔、個別詳細資料按需抓取；不預先下載全市場多年行情。
10. TPEx ETF 接受官方下載檔或官方快照；不使用未授權網頁爬蟲。
11. 第一版金融、金控與保險不套用一般公司的財務安全公式；顯示「專用模型尚未完成」，但官方事實資料仍正常呈現。
12. 第一版 ETF 不顯示公司式成長 A～F；先提供 ETF 結構安全資訊，未來取得完整持股資料後再開發「成分股加權成長潛力」。

這些決策帶來三個優先級調整：

- Web 不應再允許 20 個同時分析；本地 App 建議同時只跑 1 個，新的工作要先取消或等前一個完成。
- PDF 仍是使用者可選功能，但不再是每次分析的必經流程；只有按下下載選項時才產生。
- 「公開」指散布本地 App，不代表把 Flask 服務綁到區域網路或網際網路；目前 127.0.0.1 綁定應保留。

## 再驗證狀態總表

狀態定義：

- ✅ 已重現：有可執行案例、HTTP 輸出或直接程式證據。
- ⚠️ 部分成立：問題存在，但原報告的範圍或嚴重度要修正。
- 🧭 產品決策：不是單純 bug，必須先決定規則才可實作。
- ⏳ 尚未驗證：目前環境缺少必要工具或證據。

| Debug ID | 狀態 | 再驗證結果 | 主要檔案位置 |
|---|---|---|---|
| DBG-001 | ✅ 已修正並有測試 | 官方快照已含 0050、006208、00878；代碼與名稱搜尋都會回傳 ETF metadata | stock/normalizer.py、stock/official_stock_snapshot.json、tests/test_data_integrity.py |
| DBG-002 | ✅ 已修正並有測試 | 未知純數字代碼不再用 user_input fallback 偽造標的，HTTP 搜尋回空陣列 | stock/normalizer.py、webui.py、tests/test_web_security.py |
| DBG-003 | ✅ 已修正並有測試 | 評分最低覆蓋率提高至 70%；原 0.53 案例改回「資料不足」 | valuation/analyzer.py、tests/test_valuation.py |
| DBG-004 | ✅ 已修正並有測試 | ETF 缺資料統一顯示「資料不足（N/A）」，不再出現 None 分 | valuation/analyzer.py、tests/test_valuation.py |
| DBG-005 | ✅ 主流程已修正並有測試 | 主畫面不再顯示舊 A～D；成長與安全各自使用 A～F 契約，但未通過驗證時正式評級為空 | models/、services/analysis.py、static/js/render.js、tests/test_model_contracts.py |
| DBG-006 | ✅ 主流程已修正並有測試 | 估值安全邊際保留在估值情境；財務安全另用財報比率篩檢，不再冒充同一概念 | models/safety_model.py、services/analysis.py、tests/test_model_contracts.py |
| DBG-007 | ✅ 已修正並有測試 | model_assessments 明確分成 growth／safety，combined_rating 固定為空，衝突不平均 | services/analysis.py、static/js/render.js、tests/test_model_contracts.py |
| DBG-008 | ⚠️ 部分完成 | 已有時間順序成長回測、模型產物與 model card；仍缺真正 point-in-time 修訂版本與財務危機結果標籤 | research/backtest/、research/model_cards/、models/artifacts/ |
| DBG-009 | ✅ 已修正並有測試 | cache key 已包含目標公司；連查 1101、1102 不會混用 | stock/peers.py、tests/test_sources_and_models.py |
| DBG-010 | ✅ 已修正並有測試 | 先以相同產業篩選，再依官方實收資本額的比例差距排序；目標公司另以 is_target 標示 | stock/peers.py、tests/test_sources_and_models.py |
| DBG-011 | ✅ 已修正並有測試 | 過去日期顯示「已公布財報」，未來日期才顯示「預計公布財報」 | stock/calendar.py、tests/test_sources_and_models.py |
| DBG-012 | ✅ 已修正並有測試 | quality_score 已輸出 altman_status，前後端欄位一致 | valuation/analyzer.py、tests/test_valuation.py |
| DBG-013 | ✅ 已修正並有並行測試 | PDF 使用微秒、UUID 唯一檔名並以暫存檔原子換名 | report/generator.py、tests/test_report_render.py |
| DBG-014 | ✅ 已修正並有並行測試 | 圖表使用 UUID 唯一路徑、暫存檔原子換名與 Matplotlib 全域鎖 | stock/data.py、tests/test_report_render.py |
| DBG-015 | ✅ 已修正並有流程測試 | Web 分析完成後才顯示「產生並下載 PDF」；點擊後另開 PDF 工作 | services/analysis.py、webui.py、static/js/app.js、tests/test_analysis_lifecycle.py |
| DBG-016 | ✅ 已修正並有測試 | 重要數字使用 DataValue 保存來源、期間、抓取時間、單位、幣別與狀態；畫面來源區可逐項展開 | models/data_value.py、services/analysis.py、static/js/render.js、tests/test_official_financials.py |
| DBG-017 | ✅ 已修正並有測試 | 每次分析共用一個 MarketDataSnapshot；1 年價格只抓一次再切 3m／6m／1y，info 與財報同工作快取 | services/market_snapshot.py、services/analysis.py、stock/data.py、tests/test_market_snapshot.py |
| DBG-018 | ✅ 已修正並有測試 | Yahoo 例外邊界不再包含 ValueError、KeyError、TypeError、AttributeError、IndexError | stock/yf_errors.py、tests/test_market_snapshot.py |
| DBG-019 | ✅ 已修正並有測試 | 單工之外已加入 180 秒期限、取消、64 MiB 工作資料與 4 MiB 事件上限 | webui.py、services/analysis.py、tests/test_analysis_lifecycle.py |
| DBG-020 | ✅ 已修正 | Web 分成公司新聞與產業備援；PDF 每則也標示類型 | static/js/render.js、report/generator.py |
| DBG-021 | ✅ 已修正並有測試 | 每個來源搜尋主要名稱與最多兩個別名，結果合併去重且外部請求有固定上限 | news/aggregator.py、tests/test_sources_and_models.py |
| DBG-022 | ✅ 已修正 | 次要文字色改為 #596672，設計規範同步記錄對比要求 | static/css/app.css、docs/UI_DESIGN_SYSTEM.md |
| DBG-023 | ✅ 已修正 | 搜尋框使用 combobox／listbox／aria-expanded 契約 | templates/index.html、static/js/app.js |
| DBG-024 | ✅ 已修正並有測試 | 結果區不再整段 aria-live；完成後移動焦點到有標題的結果區 | templates/index.html、static/js/app.js、tests/test_frontend_static.py |
| DBG-025 | ✅ 已修正 | 替換為 Noto Sans TC 2.004，保存 OFL；圖示改成專案自製 SVG，移除來源不明素材 | fonts/、assets/licenses/、picture/icon/app-icon.svg、THIRD_PARTY_NOTICES.md |
| DBG-026 | ✅ 已修正並有測試 | 結構化 cache 改存 SQLite，200 MiB 觸發、清到 160 MiB；output 上限 250 MiB | storage/app_db.py、utils/cache.py、storage/cleanup.py、tests/test_storage_cleanup.py |
| DBG-027 | ✅ 已修正並有測試 | output 逐檔保存三天，App 啟動與 PDF 寫入後執行容量／期限清理 | storage/cleanup.py、report/generator.py、tests/test_storage_cleanup.py |
| DBG-028 | ✅ 已修正並有測試 | 過期 cache 會刪除；工作圖表完成後清除、失敗殘留最長 24 小時 | utils/cache.py、storage/cleanup.py、webui.py、tests/test_storage_cleanup.py |
| DBG-029 | ✅ 已修正並有測試 | SQLite 明確保存 last_accessed_at，命中時更新並以此作 LRU 清理 | storage/app_db.py、utils/cache.py、tests/test_storage_cleanup.py |
| DBG-030 | ✅ 已修正並有測試 | 首頁不進 Service Worker cache 且回傳 no-store，shutdown token 不會落入離線快取 | static/service-worker.js、webui.py、tests/test_web_security.py |
| DBG-031 | ✅ 已修正並有測試 | 月營收預設改用 TWSE／TPEx 官方 OpenAPI，保留來源、資料年月、出表日與仟元單位 | stock/official_financials.py、stock/data.py、tests/test_official_financials.py |
| DBG-032 | ✅ 已修正並有測試 | 官方季度損益表／資產負債表優先，依 ci／basi／bd／fh／ins／mim 分流；Yahoo 只補官方缺欄位 | stock/official_financials.py、services/analysis.py、valuation/analyzer.py、tests/test_official_financials.py |
| DBG-033 | ✅ 已修正 | 畫面分成已確認資料與模型推估，來源與缺漏摘要放在結果最前面 | templates/index.html、static/js/render.js |
| DBG-034 | ✅ 已修正並有測試 | release 可寫資料移到 LocalAppData，bundle 只留唯讀資源；dev 仍使用專案目錄 | config.py、tests/test_packaging_contract.py |
| DBG-035 | ✅ 符合方向 | Waitress 目前只綁 127.0.0.1，符合每台電腦單人本地 App | webui.py 第 416～424 行 |
| DBG-036 | ✅ 真實瀏覽器已通過 | Browser 插件重新附加後，實際打包 App 已完成桌面、平板、手機、鍵盤搜尋、完整分析、PDF 與關閉流程；Axe 與實體螢幕閱讀器仍列為人工驗收 | dist/TWStockAnalysis/TWStockAnalysis.exe、static/css/app.css、templates/index.html |
| DBG-037 | ✅ 已修正並有測試 | 主檔擴充為 2,773 筆，含興櫃、ETN、特別股、REIT；英數代碼可直接輸入，搜尋會標示商品類型，權證不納入 | stock/normalizer.py、stock/official_stock_snapshot.json、webui.py、static/js/app.js、tests/test_data_integrity.py |
| DBG-038 | ✅ 已修正並有測試 | ETN、REIT、特別股不再進入普通股成長／安全公式；在專用模型完成前顯示明確訊息且不產生評級或 PDF | models/growth_model.py、models/safety_model.py、services/analysis.py、tests/test_model_contracts.py |
| DBG-039 | ✅ 已修正並有測試 | 真實手機結果頁曾因 body 最小寬度與資料來源雙欄清單產生整頁水平捲軸；移除強制 320px，窄畫面來源清單改單欄後，300px 視窗的 clientWidth 與 scrollWidth 均為 300 | static/css/app.css、tests/test_frontend_static.py |
| DBG-040 | ✅ 已修正並有測試 | 關閉畫面出現後，Waitress 曾因 keep-alive 通道未清空而留下背景 EXE；現在會關閉監聽、工作執行緒與全部通道，最終打包 EXE 在 8 秒內退出 | webui.py、tests/test_runtime_resilience.py |

本輪一次性 harness 前兩次因測試類別名稱與圖表欄位大小寫寫錯而中止；修正 harness 後第三次完整執行。這兩次是檢查程式錯誤，不是產品 bug，沒有寫進上表。

## 官方資料來源再確認

2026-07-18 已直接連線官方 OpenAPI：

| 官方來源 | Live 結果 | 可否作主來源 | 目前限制 |
|---|---|---|---|
| TWSE 上市公司基本資料 | 1,090 筆，欄位含代碼、名稱、產業、上市日等 | 可以 | 官方條款仍保留修改或停止服務權利 |
| TPEx 上櫃公司基本資料 | 891 筆，欄位含代碼、名稱、產業、上市日等 | 可以 | 官方條款仍不保證永不中斷或完全無誤 |
| TWSE 基金基本資料彙總表 | 264 筆；0050 正確顯示元大台灣50、追蹤臺灣50指數 | 可以，限 TWSE 基金範圍 | 不包含已知 TPEx ETF，例如 006201、00679B、00986B |
| TPEx ETF InfoHub | 官方頁面存在並提供 ETF 資訊 | 是權威展示來源 | 官方 Swagger 目前沒有找到完整 ETF metadata API，不應直接宣稱已有穩定介接方式 |
| TPEx 興櫃公司基本資料 | 355 筆 | 可以 | 以興櫃市場獨立分類；Yahoo 行情備援使用 .TWO |
| TWSE ETN 官方商品清單 | 15 筆；另由 TPEx 每日證券資料補入 6 筆 | 可以 | ETN 只納入搜尋主檔，尚無專用評級模型 |
| TWSE／TPEx 每日證券資料 | 補入 29 檔特別股、6 檔 REIT，以及基金清單尚未出現的新 ETF | 可以作主檔補充 | 僅接受已明確辨識的商品代碼；權證一律排除 |
| Yahoo Finance／yfinance | 可補價格與部分財務欄位 | 只能備援 | 不是台灣掛牌身分的權威來源，且 yfinance 官方定位偏個人研究用途 |

重要結論：

- 「官方」代表權責機關的第一手來源，可以作為權威主來源；不代表官方保證永久不改欄位、永不中斷或百分之百無錯。
- TWSE 與 TPEx 的網站條款都保留服務修改權，並對資料錯誤或中斷免責。因此程式仍必須做 schema 檢查、筆數異常檢查、最後有效快照與來源狀態顯示。
- 全部 TWSE 上市公司、TPEx 上櫃公司與 TWSE 基金已找到可用官方 OpenAPI。
- 目前尚未找到涵蓋全部 TPEx 上櫃 ETF 的穩定官方程式介面；已決定改用 TPEx 官方下載檔或經驗證的官方快照，並保留更新日期、來源與完整性檢查，不使用未授權爬蟲。
- 初次稽核時的 stock/official_stock_snapshot.json 只有 1,981 家公司，沒有 0050 與 asset_type；目前 schema 4 已擴充為 2,773 筆，並通過 ETF、ETN、REIT、特別股與英數代碼搜尋測試。

## 先看結論

原先會算錯或讓人誤會的主要程式問題已依 Phase 0～4 修正，portable ZIP 與 Windows Setup EXE 也已建置並實跑。現在可以公開提供「免費開源測試版」，但仍要清楚標示這是研究工具，不是買賣建議。

目前最重要的限制有四個：

1. 成長與安全的正式 A～F 尚未通過足夠歷史資料驗證，所以畫面只顯示實驗結果，不假裝是可靠預測。
2. ETF、金融／保險、ETN、REIT 與特別股仍有專用模型缺口；程式會停止不適用的計算，不硬套普通股公式。
3. 實際 App 已通過 Browser 響應式、鍵盤、焦點、PDF 與基本無障礙結構檢查；Axe 與實體螢幕閱讀器仍需另做人工驗收。
4. EXE 尚未做 Windows 數位簽章，公開下載時可能被 SmartScreen 警告。

## 這份報告怎麼看

每個問題都分成五段：

- 白話說明：使用者實際會遇到什麼。
- 我怎麼確認：本次實際看到或重現的證據。
- 為什麼重要：不修會有什麼影響。
- 檔案位置：之後要從哪裡開始修改。
- 修好標準：怎樣才算真的完成，不是只改表面。

優先級：

- P0：下一輪最先修，因為可能給出錯誤結果或破壞檔案。
- P1：P0 修完後處理，會影響可信度、速度或使用體驗。
- P2：整理與長期維護問題，可以最後處理。

常見名詞：

| 名詞 | 白話意思 |
|---|---|
| cache／暫存 | 先把結果存起來，下次不用重新抓；若辨識方式錯誤，就可能拿到別人的結果 |
| coverage／資料完整度 | 這次計算到底有多少需要的資料 |
| regression test／防復發測試 | 把已發現的 bug 寫成永久測試，避免之後又壞掉 |
| point-in-time data／當時資料 | 回到歷史某天時，只使用當天真的看得到的資料，不能偷看到未來 |
| schema／資料格式規格 | 規定每個欄位叫什麼、是什麼單位、可能有哪些狀態 |
| atomic write／一次完成寫入 | 先寫暫存檔，完整成功後才換成正式檔，避免留下半份 PDF |

## 專案重要檔案地圖

| 功能 | 檔案位置 |
|---|---|
| 程式入口 | main.py |
| Web 伺服器與背景工作 | webui.py |
| 整體分析流程 | services/analysis.py |
| 股票代碼、名稱與搜尋 | stock/normalizer.py |
| 目前公司清單 | stock/official_stock_snapshot.json |
| 更新公司清單的腳本 | scripts/update_stock_snapshot.py |
| 股價、營收、EPS 與圖表 | stock/data.py |
| 同業比較 | stock/peers.py |
| 財報／股利行事曆 | stock/calendar.py |
| Yahoo 例外處理 | stock/yf_errors.py |
| 評分、估值與 ETF 分析 | valuation/analyzer.py |
| 新聞彙整 | news/aggregator.py |
| 新聞來源 | news/providers/ |
| PDF 產生 | report/generator.py |
| PDF 字型設定 | report/font.py |
| 首頁 HTML | templates/index.html |
| 畫面樣式 | static/css/app.css |
| 畫面結果組裝 | static/js/render.js |
| 前端主流程 | static/js/app.js |
| API 與 SSE | static/js/api.js |
| Service Worker | static/service-worker.js |
| 暫存系統 | utils/cache.py |
| 測試 | tests/ |
| 內附字型 | fonts/ |

注意：下面行號是本次檢測時的位置。之後修改程式後，行號可能移動，但函式名稱與檔案位置仍可用來搜尋。

## 本次實際檢查結果

| 檢查 | 結果 | 白話解釋 |
|---|---|---|
| Python 測試 | 106 passed | 完整 build gate 通過 |
| Python 相依檢查 | 通過 | pip check 沒有套件衝突 |
| 已知相依漏洞 | 未查到 | pip-audit 2.10.1 掃描 requirements.txt 通過；這不是原始碼安全稽核 |
| Python／JavaScript 語法 | 通過 | Ruff 與 6 個 JavaScript 語法檢查通過 |
| Ruff 格式檢查 | 通過 | 39 個檔案已統一排版；66 個 Python 檔通過 `ruff format --check` |
| 官方證券主檔 | 2,773 筆 | 股票 2,326、ETF 381、ETN 21、特別股 29、REIT 6、TDR 10 |
| Windows portable | 通過 | ZIP 內含 MIT LICENSE、官方主檔與必要資源，實際 EXE 可啟動與關閉 |
| Windows installer | 通過 | Inno Setup 6.7.3 建置；實際安裝、啟動、單例與解除安裝通過 |

以下問題章節保留「初次稽核時的重現證據」，方便日後 debug。是否已修好，請以上方「再驗證狀態總表」為準。

## ✅ 已重現 P0-1：系統不真正認得 ETF

### 白話說明

輸入 0050 時，系統可能抓得到價格，卻只把名稱顯示成「0050」，也不知道它屬於哪個市場。輸入「元大台灣50」時甚至找不到。

這就像電話號碼打得通，但通訊錄裡沒有名字。

### 我怎麼確認

- 現有 stock/official_stock_snapshot.json 只有上市與上櫃公司，沒有 ETF。
- normalize("0050") 回傳 name="0050"，market 與 industry 是空的。
- 搜尋「元大台灣50」沒有結果。
- README 與畫面卻讓使用者以為可以用 ETF 名稱搜尋。

### 為什麼重要

- ETF 報告標題會錯。
- 無法正確顯示發行人、追蹤指數、幣別和市場。
- 之後的 ETF 比較也沒有可靠的分類基礎。

### 檔案位置

- stock/normalizer.py，第 500～560 行：載入清單、normalize、search_stock。
- stock/official_stock_snapshot.json：目前只有公司主檔。
- scripts/update_stock_snapshot.py：更新主檔的腳本。
- templates/index.html，第 38 行附近：搜尋輸入框。
- README.md：對外說明的支援範圍。

### 建議修法

1. 建立完整的證券清單，明確標示普通股、ETF、ETN、TDR。
2. ETF 至少保存代碼、中文名、英文名、市場、幣別、發行人、追蹤指數與上市日。
3. 優先採官方 TWSE／TPEx 資料。
4. 找不到的代碼要說「未收錄」，不能自己把代碼當成公司名稱。

### 修好標準

- 0050、006208、00878 可以用代碼與中文名找到。
- 畫面與 PDF 正確顯示 ETF 名稱、類型、市場與幣別。
- 99999999 不會被當成真的股票。

## ✅ 已重現 P0-2：資料不夠，系統卻仍給出正常分數

### 白話說明

目前有些評分只要少數欄位存在，就會把整個項目當成「可以評分」。其他缺少的資料可能被當成普通或中性，因此最後仍出現一個看起來很完整的分數。

真正意思應該是「不知道」，現在卻可能顯示成「普通」。

### 我怎麼確認

我用非常少的測試資料：只有零成長、零 ROE、一個現金數字和 12 天平盤價格。系統仍算出：

- 健康分數 54.5。
- 等級「普通」。
- 資料完整度 0.53。

2330 的即時結果中，健康分數完整度顯示 1.0，但 Piotroski 只有 9 項中的 3 項可計算，也說明目前完整度不是逐欄位計算。

### 為什麼重要

- 使用者會把「資料不足」誤認成「表現普通」。
- 不同股票的分數無法公平比較。
- 後續回測也會被假分數污染。

### 檔案位置

- valuation/analyzer.py，第 468～515 行：calculate_health_score。
- valuation/analyzer.py，第 904～1012 行：calculate_overall_rating。
- valuation/analyzer.py，第 1247～1367 行：ETF 健康分數與評級。
- services/analysis.py，第 79～138 行：把評分整理給 Web／PDF。
- services/analysis.py，第 203～204 行：健康分數與 Piotroski 完整度。
- tests/test_valuation.py：現有估值測試。
- tests/test_sources_and_models.py：現有資料與模型測試。

### 建議修法

每個欄位都要保存：

- 有沒有資料。
- 資料來源。
- 資料日期。
- 單位與幣別。
- 是否經過換算。

缺資料時不要補中性分。若核心欄位不足，就直接顯示「資料不足，無法評級」。

### 修好標準

- 全缺、只缺一半、零值與過期資料都有測試。
- 缺資料不會得到假分數。
- 畫面能分清楚「0」、「沒有資料」與「這個模型不適用」。

## ✅ 已確認缺口 P0-3：評級與合理價還沒有被證明有效

### 白話說明

目前的評級是把成長、估值、獲利、動能、品質與安全邊際依預先設定的權重加在一起。它可以當整理資訊的方法，但專案內沒有證據證明 A 級股票未來真的比 B 級好，也沒有證明「合理價」能代表未來可接受的價格。

產品現在要同時表達「成長性」與「公司財務安全」，但現行程式不符合：

- 畫面與程式只有 A、B、C、D、N/A，沒有 E、F。
- overall rating 的 safety 主要來自「股價低於估值多少」，不是負債、現金流、償債能力等財務安全。
- 成長與安全被壓成一個總分，高成長但高財務風險的公司可能被平均成普通分數。

### 我怎麼確認

- 專案內沒有完整歷史回測結果。
- 沒有寫清楚評級到底要預測未來報酬、跌幅、獲利成長還是倒閉風險。
- 沒有交易成本、基準指數、樣本外測試與模型版本紀錄。
- 2330 的歷史本益比估值只有 75 筆交易日樣本，仍產生合理價。
- valuation/analyzer.py 第 915～947 行直接把估值安全邊際命名為 safety。
- valuation/analyzer.py 第 1000～1007 行只定義 A～D。

### 為什麼重要

大字顯示單一 A～D 或單一合理價，會讓人以為這是已經驗證過的投資結論，也會看不出成長與安全互相衝突的情況。

### 檔案位置

- valuation/analyzer.py，第 213～293 行：合理價與安全邊際。
- valuation/analyzer.py，第 462～515 行：健康分數。
- valuation/analyzer.py，第 702～904 行：Piotroski 與 Altman。
- valuation/analyzer.py，第 904～1012 行：總評級。
- valuation/analyzer.py，第 1134～1162 行：文字摘要。
- static/js/render.js：畫面上的分數與評級。
- report/generator.py：PDF 的估值與評級內容。
- tests/test_valuation.py：目前只有計算測試，沒有投資效果回測。

### 建議修法

1. 回測完成前，把「綜合評級」改成「模型摘要」。
2. 把「合理價」改成「估值情境區間」，顯示使用期間、樣本數與假設。
3. 股票、金融股與 ETF 使用不同模型。
4. 先定義模型要解決的問題，再決定指標和權重。
5. 建議改成兩個獨立等級：成長評級 A～F、財務安全評級 A～F；不要先平均成一個總級。

### 修好標準

- 每個評級都有明確目標、適用範圍和模型版本。
- 使用當時真正可取得的資料做歷史測試。
- 有未參與調整的樣本外期間。
- 扣除成本後仍優於事先選定的簡單基準，才恢復強烈評級文案。

## ✅ 已重現 P0-4：同業暫存會混到別家公司

### 白話說明

系統會把同產業的同業結果暫存起來。但暫存名稱只記得「產業和市場」，沒有記得「這次正在分析哪家公司」。

所以先查 1101，再查 1102，1102 可能拿到為 1101 準備的同業清單，甚至把自己列成自己的同業。

### 我怎麼確認

- 先以 1101 取得同業 1102、1103。
- 接著查 1102，命中同一份暫存並包含 1102 自己。
- 暫存 key 是 peers:{industry}:{market}，沒有 stock_id。

### 檔案位置

- stock/peers.py，第 45～82 行：get_peers_comparison、cache key、候選處理。
- utils/cache.py，第 48 行起：cache_get。
- services/analysis.py：呼叫同業比較並組裝結果。
- tests/test_sources_and_models.py：建議加入跨股票連續查詢測試。

### 建議修法

- 方法一：暫存名稱加入 stock_id 與演算法版本。
- 方法二：只暫存整個產業候選，回傳前才排除目前公司。

### 修好標準

- 先查 1101 再查 1102，或反過來查，結果都正確。
- 同業清單永遠不包含自己。
- 清除暫存與命中暫存時結果相同。

## ✅ 已確認 P0-5：現在的「同業」其實接近清單前五名

### 白話說明

目前同業不是找「最像的五家公司」，而是從公司清單順序取得前幾個能抓到資料的候選。

因此結果比較接近代碼順序，不是真正的商業相似度。

### 我怎麼確認

2330 得到的同業是 2302、2303、2329、2337、2338。程式沒有用市值、營收、資產規模或產品相似度排名。

### 檔案位置

- stock/peers.py，第 58～82 行：候選清單與平行抓取。
- stock/official_stock_snapshot.json：候選順序與基本分類。
- static/js/render.js：同業表顯示。
- report/generator.py：PDF 同業表。

### 建議修法

1. 先用證券類型、市場與產業篩選。
2. 再比較市值、營收、總資產、獲利結構、流動性和業務標籤。
3. 把最相似的排前面。
4. 在同一張表第一列放目前公司，使用者才能直接比較。
5. 顯示「為什麼選它當同業」。

### 修好標準

- 變更公司清單順序不會改變同業排名。
- 已知大型公司能得到合理且可說明原因的同業。
- ETF 只跟相同追蹤方向的 ETF 比較。

## ✅ 已重現、release 風險降級 P0-6：圖表與 PDF 會取得相同檔名

### 白話說明

即使只有一位使用者，多開分頁、重複送出或 dev 測試仍可能讓兩個工作在同一秒分析同一檔股票，並寫到同一個檔名。這可能造成：

- A 工作讀到 B 工作的圖。
- PDF 被後完成的工作覆蓋。
- 使用者下載到只寫一半的檔案。

### 我怎麼確認

- PDF 檔名只到秒；固定同一時間產生兩次，得到完全相同的檔名。
- 圖表名稱由股票代碼、期間和模式組成，同股票工作會共用。
- PDF 直接寫正式路徑，沒有先寫暫存檔。
- Web 最多允許 20 個背景執行緒。

### 檔案位置

- report/generator.py，第 90～119 行：PDF 檔名與輸出。
- stock/data.py，第 58～103 行：重複抓價格與建立圖表。
- stock/data.py，第 103～139、230～259、378～398 行：各類圖表輸出。
- webui.py，第 27～34 行：MAX_TASKS 與全域 tasks。
- webui.py，第 150～187 行：背景分析。
- webui.py，第 262～298 行：建立 thread。
- config.py：output、cache 與圖表目錄。
- tests/test_report_render.py：PDF 測試。
- tests/test_analysis_lifecycle.py：工作生命週期測試。

### 建議修法

1. 每個工作建立自己的 UUID 資料夾。
2. 圖表和中間檔只寫在該工作的資料夾。
3. PDF 先完整寫入暫存檔，再一次換成正式檔。
4. 檔名加入短 UUID 或毫秒。
5. Matplotlib 繪圖加全域鎖，或放到獨立 process。
6. release build 只在使用者按下「產生並下載 PDF」後建立報告，且同時只允許一個分析；這是第一層防線，不取代安全寫檔。

### 修好標準

- release build 不會自動啟動 PDF；第二個分析或報告工作會要求先取消或等待。
- dev 模式同時啟動 2 個相同股票分析時，每個 PDF 都有不同檔名。
- 每份 PDF 都能開啟、頁數正常、圖片屬於自己的工作。
- 失敗時不留下半份正式檔。

## ⚠️ 部分成立 P0-7：專案缺少字型散布授權證明

### 白話說明

字型檔能正常使用，不代表可以跟著專案公開散布。現在專案沒有文件證明這三個字型可以重新打包給其他人。

### 檔案位置

- fonts/msjh.ttc
- fonts/msjhbd.ttc
- fonts/STKAITI.TTF
- report/font.py：選擇 PDF 字型。
- report/generator.py：實際產生 PDF。
- picture/icon/：圖示和圖片也應記錄來源。

### 建議修法

- 若沒有明確授權，改用允許再散布的 OFL 字型，例如 Noto Sans TC。
- 新增 THIRD_PARTY_NOTICES.md。
- 在 assets/licenses/ 或相同用途資料夾保存來源、授權、版本和取得日期。
- Yahoo、新聞來源與官方資料的使用範圍也要寫清楚。

### 修好標準

所有跟著專案散布的字型、圖片與資料，都能找到來源和授權依據。

## ✅ 已修正 P1-1：重要數字已有逐欄位來源與日期

### 白話說明

畫面有數字，但使用者通常看不到：

- 是官方資料還是 Yahoo。
- 是今天盤中價、昨天收盤價，還是更舊的 cache。
- 單位是百分比還是小數。
- 金額是哪一種幣別。

### 檔案位置

- stock/data.py：價格、月營收、EPS。
- stock/dividend.py：股利資料。
- stock/calendar.py：日期事件。
- services/analysis.py：把所有資料組裝在一起。
- valuation/analyzer.py：換算並評分。
- static/js/render.js：畫面呈現。
- report/generator.py：PDF 呈現。

### 建議修法

每個重要數字都附上：

- value：數值。
- source：資料來源。
- as_of：這個數字代表哪一天。
- fetched_at：系統何時抓到。
- unit／currency：單位與幣別。
- status：新鮮、過期、缺少、不適用或錯誤。

「最新收盤價」若其實是盤中或延遲資料，應改叫「參考價」並附時間。

## ✅ 已重現 P1-2：已經公布的財報仍被寫成「即將公布」

### 白話說明

2330 的日期是 2026-07-16，本次檢查日是 2026-07-18，但系統仍顯示「近期待公布財報」。

### 檔案位置

- stock/calendar.py，第 22～40 行：get_calendar_events。
- services/analysis.py：把行事曆放入分析結果。
- static/js/render.js：畫面事件區塊。
- report/generator.py：PDF 事件區塊。

### 建議修法

- 日期在今天之後：顯示「預計公布」。
- 日期在今天之前：顯示「最近公布」。
- 全部日期先轉成 Asia/Taipei 再比較。
- 補跨午夜、時區、同一天與週末測試。

## ✅ 已修正 P1-3：同一次分析共用資料快照

### 白話說明

3 個月、6 個月、1 年價格目前分開向 Yahoo 要資料，其他模組也會重複取得 Ticker.info。

這會讓分析變慢、增加被限流的機會，而且同一份報告可能混到不同抓取時間的資料。

### 檔案位置

- stock/data.py，第 58～98 行：get_price_data 與多次 history。
- services/analysis.py：整體抓取順序。
- valuation/analyzer.py：使用多個 Yahoo 欄位。
- stock/dividend.py、stock/calendar.py、stock/peers.py：其他資料呼叫。

### 建議修法

- 每次分析只建立一份 MarketDataSnapshot。
- 一次抓最長期間，再在記憶體切成 3 個月、6 個月、1 年。
- info 與財報資料同次工作只抓一次。
- 所有結果共用同一 fetched_at。

## ✅ 已修正 P1-4：網路、格式、缺資料與程式 bug 分開處理

### 白話說明

現在有些 ValueError、KeyError、TypeError、AttributeError、IndexError 都被當成 Yahoo 資料抓取失敗。

但這些錯誤也可能代表程式寫錯或 Yahoo 改了資料格式。全部吞掉後，只會顯示「資料無法取得」，開發者看不到真正 bug。

### 檔案位置

- stock/yf_errors.py，第 1～43 行：YFINANCE_EXCEPTIONS。
- stock/data.py、stock/dividend.py、stock/calendar.py、stock/peers.py：捕捉例外的位置。
- utils/logger.py：錯誤紀錄。

### 建議修法

- 網路 timeout、連線失敗、HTTP 錯誤單獨處理。
- 欄位格式變更回報為「來源格式改變」。
- 沒預期到的程式錯誤要保留 traceback 和 task id，不要假裝成資料缺失。

## ✅ 已修正、依單人本地 App 調整 P1-5：單工、取消與資源上限

### 白話說明

系統限制最多 20 個正在執行的工作，但完成和失敗的工作會繼續留在記憶體約 10 分鐘。大量快速失敗時，仍可能累積很多 events 和 preview。

使用者關閉頁面後，背景工作也不會停止。

### 檔案位置

- webui.py，第 27～34 行：工作上限與全域暫存。
- webui.py，第 67～80 行：清理舊工作。
- webui.py，第 83～147 行：工作內容與 events。
- webui.py，第 150～187 行：分析執行。
- webui.py，第 262～330 行：建立工作、查詢狀態與 SSE。
- static/js/api.js：前端連線與 SSE。
- static/js/app.js：前端啟動與錯誤處理。

### 建議修法

- active analysis 固定為 1；若已有工作，UI 提供「取消目前工作」或「等待完成」。
- 不需要為單人本地 App 引入外部 queue server。
- 加入 deadline 和取消旗標。
- preview 與 events 設定大小上限。
- 工作完成後只保留必要資訊。
- 分析與 Matplotlib 可放在單一受控 worker process，避免 UI thread 卡住並隔離繪圖狀態。

## ✅ 已確認 P1-6：產業新聞可能被看成公司新聞

### 白話說明

如果找不到公司新聞，系統會放入產業新聞。後端其實知道這是 fallback，但畫面和 PDF 沒有明顯標示，摘要還可能說這是「關於某公司的新聞」。

### 檔案位置

- news/aggregator.py：搜尋、排序、摘要與 fallback。
- news/providers/industry_fallback.py：產業備援新聞。
- news/providers/google_news.py、anue.py、moneydj.py、udn.py：新聞來源。
- static/js/render.js：新聞畫面。
- report/generator.py：PDF 新聞內容。

### 建議修法

- 公司新聞與產業背景新聞分成兩個區塊。
- 每則新聞顯示命中的公司名、代碼或產業詞。
- 產業 fallback 不加入公司正負面統計。
- 關鍵字正負面只能寫「規則分類」，不要叫預測。

## ✅ 已確認 P1-7：Altman 欄位前後端對不起來

### 白話說明

後端提供 altman_z_score 和 altman_model，前端卻讀 altman_status。

因此即使有分數，或只是缺少資料，畫面也可能一律顯示「金融業與 ETF 不適用」。

### 檔案位置

- valuation/analyzer.py，第 806～904 行：Altman 計算。
- services/analysis.py：輸出品質資料。
- static/js/render.js，第 119 行：讀取 altman_status。
- report/generator.py，第 676 行附近：PDF 讀取 altman_z_score。
- tests/test_frontend_static.py：現有靜態前端測試。
- tests/test_sources_and_models.py：模型資料測試。

### 建議修法

後端統一提供：

- status：可計算、不適用、資料不足或錯誤。
- model：用了哪個模型。
- score：分數。
- zone：安全、灰色或危險區。
- reasons：為什麼不能算。

前端和 PDF 只照同一份規格顯示，不要各自猜測。

## ✅ 已重現 P1-8：搜尋會接受不存在的數字代碼

### 白話說明

輸入 99999999 時，系統會建立一個名稱也叫 99999999 的假標的，甚至可能出現在搜尋建議中。

### 檔案位置

- stock/normalizer.py，第 526～546 行：normalize。
- stock/normalizer.py，第 549 行起：search_stock。
- webui.py：search API 與 analyze API。
- static/js/app.js：搜尋選擇與送出。

### 建議修法

- 格式正確不代表股票真的存在。
- 搜尋建議只顯示主檔內存在的代碼。
- 直接輸入未知代碼時，回覆「查無此證券」，不要自動建立。

## UI/UX：畫面怎麼改會比較好懂

## 🧭 已採用方向 UI-1：分開「已確認資料」與「模型推估」

目前畫面容易先看到評級，使用者卻不知道資料是哪一天，而且 KPI 同時混入合理價、健康分數、股利、營收與 EPS。

依已確認的產品方向，建議首頁明確分成兩區：

1. 已確認資料區：股票／ETF 名稱、代碼、類型、市場、價格、官方營收、財報、股利、日期、來源與缺漏。
2. 模型推估區：成長評級、財務安全評級、估值情境、風險訊號、模型版本、資料完整度與不確定性。

兩區都要保留來源資訊，但「模型推估」必須使用不同底色、標籤與說明，不能讓使用者把推估當成官方事實。

檔案位置：

- templates/index.html，第 107 行起：整個結果區。
- static/js/render.js：所有結果卡片。
- static/css/app.css：視覺順序與字級。
- services/analysis.py：前端所需資料。

## 🧭 待確認雙評級 UI-2：不要用單一大分數掩蓋成長與安全衝突

一個等級無法同時忠實表達兩個衝突目標。建議顯示：

- 成長評級 A～F。
- 財務安全評級 A～F。
- 二維狀態，例如「高成長／低安全」、「低成長／高安全」。
- 資料完整度：高／中／低。
- 估值情境：偏低／接近歷史區間／偏高。
- 主要風險：最多列 3 項。
- 不能判斷的項目：清楚列出原因。

若仍要一個「總評級」，必須另行決定成長與安全的權重；本報告不建議先做，因為平均後會失去衝突資訊。

檔案位置：

- static/js/render.js。
- static/css/app.css 的 score 相關樣式。
- valuation/analyzer.py 的 rating 輸出。
- report/generator.py 的摘要頁。

## ✅ 已確認 UI-3：小字顏色太淡

目前 --slate-500 是 #77838e。它用在 10～13px 小字時，對白底與淺灰底的對比都不足。

檔案位置：

- static/css/app.css，第 20 行：--slate-500。
- static/css/app.css，第 99、104、166、180、184、197、206、224、227 行附近：實際使用位置。

修法：

- 把一般小字顏色加深。
- placeholder、disabled、圖表標籤也一起測。
- 加入 axe 自動檢查和人工鍵盤測試。

## ✅ 已確認 UI-4：搜尋框的無障礙標記不完整

搜尋框已有多數 aria 屬性，但缺少 role="combobox"。鍵盤和螢幕閱讀器可能無法得到完整資訊。

檔案位置：

- templates/index.html，第 38 行：stockQuery。
- static/js/app.js：上下鍵、Enter、Escape 與選項狀態。
- static/css/app.css：focus 樣式。

修好標準：

- ArrowUp／Down、Enter、Escape、Tab 都正確。
- 中文輸入法組字期間不誤送出。
- 螢幕閱讀器知道搜尋框已展開、有幾個選項、目前選到哪一個。

## ✅ 已確認 UI-5：結果區不應整塊自動朗讀

resultView 整區使用 aria-live="polite"。分析完成時，螢幕閱讀器可能一次朗讀大量內容。

檔案位置：

- templates/index.html，第 46 行：分析進度。
- templates/index.html，第 107 行：resultView。
- templates/index.html，第 215 行：toast。
- static/js/app.js：完成後的 focus。

修法：

- aria-live 只朗讀一句簡短狀態。
- 完成後把焦點移到結果標題。
- 使用者再自行往下讀各區內容。

## ✅ 已重現 UI-6：N/A 要說明原因

ETF 測試曾出現「N/A（None 分）」。使用者無法知道是：

- 沒資料。
- 模型不適用。
- 資料過期。
- 系統出錯。

檔案位置：

- valuation/analyzer.py，第 1340～1367 行。
- services/analysis.py。
- static/js/render.js。
- report/generator.py。

修法：

Web 與 PDF 共用同一套文字格式，顯示「無法計算：缺少五年現金流」這類具體原因，不顯示 None 或 NaN。

## 已採用的 UI 設計規範草案

這份規範先作為修正 checklist，正式改 UI 時再轉成 CSS design tokens：

### 資訊規範

- 「已確認資料」與「模型推估」必須是兩個清楚分開的區塊。
- 官方原始值不得使用「預測、建議、看多、看空」等語氣。
- 模型結果一律顯示模型版本、資料完整度、計算日期與不適用原因。
- 官方資料、Yahoo 備援、歷史快照使用不同 source badge。
- 官方來源失敗而改用備援時，畫面必須主動提醒，不能靜默切換。
- 數字不可單獨顯示 None、NaN、0 元或 0%，必須先判斷是真零還是缺值。

### 字型規範

- 內嵌字型建議改用具 OFL 授權的 Noto Sans TC；Windows 系統字型只作 fallback，不隨 App 重新散布。
- 一般內文建議 16px、輔助文字 14px，最小文字不得低於 12px。
- 內文行高至少 1.5；表格與密集數字至少 1.4。
- 數字、代碼與日期可使用等寬數字特性，但不可犧牲中文可讀性。

### 色彩與狀態規範

- 一般文字對背景至少 4.5:1。
- 大字至少 3:1，但不要把 12～14px 小字當成大字。
- 成功、警告、危險不可只靠綠、黃、紅；同時使用文字與圖示。
- 「已確認資料」使用中性背景；「模型推估」使用明顯但不刺眼的區分背景。
- focus ring 至少 2px，所有按鈕與連結都必須看得到鍵盤焦點。

### 間距與元件規範

- 使用 8px 間距系統：8、16、24、32、48。
- 同類卡片使用一致的 padding、圓角、標題層級與 source badge 位置。
- 點擊目標至少 44×44px，避免手機與觸控誤按。
- 表格在窄螢幕要改為卡片或提供清楚的橫向捲動提示，不可只縮小字體。
- loading、empty、error、stale、not_applicable 都要有固定元件，不在各畫面臨時拼字。

### 驗收位置

- templates/index.html
- static/css/app.css
- static/js/render.js
- static/js/app.js
- tests/test_frontend_static.py
- 建議新增 tests/e2e/ 與設計 token 文件 docs/UI_DESIGN_SYSTEM.md

## 演算法應該怎麼重新設計

## 第一步：先說清楚分數想回答什麼

產品目標已進一步確認：

- 成長評級 A～F：預測公司未來 12 個月營收與 EPS 是否有持續成長的機會。
- 財務安全評級 A～F：評估公司未來出現償債、現金流或財務結構問題的風險。
- 估值：獨立顯示情境區間，不混進上述兩個等級。

成長評級預測的是公司營運成長，不是預測未來股價一定上漲。即使公司成長，股價仍可能因估值過高、市場下跌或其他風險而下跌。

成長模型的 target 建議定義為：

- 主要 target：未來連續 12 個月營收成長率。
- 次要 target：未來四季累計 EPS 成長率。
- 輸出：成長機率、預估成長區間、A～F 等級、資料完整度與模型信心。
- 不直接輸出「會漲多少」或買賣建議。

主要檔案：

- valuation/analyzer.py。
- services/analysis.py。
- 建議新增 models/ 或 research/ 目錄保存模型與驗證，不要直接塞進 Web 程式。

## 第二步：股票和 ETF 分開

### 股票適合看的項目

- 估值：P/E、P/B、EV/EBITDA 的歷史與同業範圍。
- 品質：ROIC、毛利穩定度、現金轉換與負債。
- 成長：營收與 EPS，但要處理負基期和一次性項目。
- 風險：波動、回撤、流動性、負債與資料過期。

### ETF 適合看的項目

- 追蹤差異與 tracking error。
- 費用率。
- 成交量、買賣價差與市場深度。
- AUM、幣別和下市風險。
- 折溢價，但價格和 NAV 必須是同一時間。
- 追蹤指數、持股集中度、產業與國家曝險。
- 配息來源與含息總報酬。

ETF 不應使用公司的盈餘品質或破產分數。

ETF 本身沒有公司營收與 EPS。已確認第一版 ETF 不顯示公司式成長 A～F，只提供 ETF 結構安全資訊。未來若要加入 ETF 成長評級，必須開發「持有成分的加權未來成長」模型，不能直接套公司模型。

主要檔案：

- valuation/analyzer.py，第 1247 行起：目前 ETF 邏輯。
- stock/normalizer.py 與證券主檔：判斷資產類型。
- services/analysis.py：選擇正確模型。
- static/js/render.js、report/generator.py：使用不同版面。

## 為什麼金融、金控與保險不能直接用一般財務安全模型

### 一般公司

一般製造、科技或服務公司可以觀察：

- 現金與總負債。
- 流動比率、速動比率。
- 利息保障倍數。
- 自由現金流與營運現金流。
- 負債權益比。
- Altman 類型的破產風險模型，但仍要限制適用產業。

### 銀行

銀行收進來的存款在會計上是負債，但存款本來就是銀行經營的核心資金來源。若用一般公司的「負債越高越危險」規則，正常銀行也可能被判成危險。

銀行更應該看：

- 資本適足率。
- 第一類資本比率。
- 逾期放款比率。
- 備抵呆帳覆蓋率。
- 流動性覆蓋比率。
- 放款與存款品質。

### 保險公司

保險公司的保險負債、責任準備金與資產負債久期也不是一般公司負債。更應該看：

- 資本適足／清償能力。
- 淨值與保險負債變化。
- 避險成本與匯率風險。
- 資產負債期限是否匹配。

### 金控

金控要看合併資本與銀行、保險、證券子公司的風險，不能只用母公司表面的流動比率。

### 目前建議

第一版先採安全做法：

- 一般產業可以建立財務安全 A～F，但必須完成缺值處理與回測。
- 金融、金控、保險先顯示「專用模型尚未完成」，不給假 A～F。
- 原始官方財務資料仍照常放在「已確認資料區」。
- 後續取得金管會／銀行局／保險局官方監理指標後，再建立獨立模型。

這不是說金融股不安全，而是目前沒有足夠且適用的模型，不能用錯公式製造假精確感。

## 第三步：建立公平的歷史測試

白話流程：

1. 選一個過去日期。
2. 只讓模型看到當天已經公布的資料。
3. 算出當時的分數。
4. 看後來 3、6、12 個月發生什麼。
5. 計入手續費、稅、滑價與不能成交的情況。
6. 跟大盤、產業或簡單規則比較。
7. 用前段歷史調整，最後一段只驗收一次。

還要保留已下市和表現差的公司，不然只看活到今天的公司，結果會過度樂觀。

建議新增位置：

- research/backtest/：回測程式。
- research/datasets/：資料格式與說明，不一定把大型資料直接提交 Git。
- research/model_cards/：每版模型的目標、欄位、權重、結果和限制。
- tests/test_model_contracts.py：模型輸入輸出規格。

## 第四步：分數不夠可靠時就不要硬給

每個模型要先定義最低資料需求。

例如需要 8 個欄位，只有 3 個時：

- 不應補成普通分數。
- 顯示「資料不足」。
- 列出缺少的 5 個欄位。
- 仍可顯示不需要推論的原始資料。

## 分階段修正計畫

## Phase 0：先阻止錯誤結果與檔案互蓋

這一階段不要重新設計整個 UI，也不要調整評分權重。

### 0-1 證券主檔與搜尋

- [x] 先新增 0050、006208、00878、99999999 測試。
- [x] 建立股票／ETF／TDR 類型欄位。
- [x] 匯入官方 ETF 名稱與 metadata。
- [x] 未知代碼回傳清楚錯誤。

修改位置：

- stock/normalizer.py
- stock/official_stock_snapshot.json
- scripts/update_stock_snapshot.py
- webui.py
- static/js/app.js
- tests/test_data_integrity.py
- tests/test_sources_and_models.py

### 0-2 同業比較

- [x] 先新增 1101、1102 連續查詢的 cache 防復發測試。
- [x] 修正 cache key。
- [x] 同業候選永遠排除自己；目標公司只以 is_target 身分另列於比較表。
- [x] 用相同產業代表業務相似度，再依官方實收資本額比例差距排序。
- [x] 把目標公司放進比較表。

修改位置：

- stock/peers.py
- utils/cache.py
- services/analysis.py
- static/js/render.js
- report/generator.py
- tests/test_sources_and_models.py

### 0-3 日期與前後端欄位

- [x] 修正過去／未來財報文案。
- [x] 統一 Altman status。
- [x] 統一 ETF N/A 格式。

修改位置：

- stock/calendar.py
- valuation/analyzer.py
- services/analysis.py
- static/js/render.js
- report/generator.py
- tests/test_valuation.py
- tests/test_frontend_static.py

### 0-4 圖表、PDF 與背景工作隔離

- [x] release build 不自動產生 PDF；分析完成後才顯示「產生並下載 PDF」按鈕。
- [x] 點擊按鈕後才啟動獨立 PDF 工作，完成後提供下載。
- [x] dev／CLI 保留可選擇自動產生 PDF 作 QA 的服務參數。
- [x] 本地 App 同時只允許 1 個分析／PDF 工作；第二個工作會回傳 429。
- [x] 每個 task 在 cache/tasks/<task_id>/ 建立獨立圖表資料夾。
- [x] PDF 與圖表使用唯一檔名。
- [x] 先寫暫存檔，再以 os.replace 換成正式檔。
- [x] Matplotlib 加全域鎖。
- [x] 新增同股票兩份 PDF 與兩張圖表的並行碰撞測試。

修改位置：

- webui.py
- stock/data.py
- report/generator.py
- config.py
- tests/test_analysis_lifecycle.py
- tests/test_report_render.py
- tests/test_runtime_resilience.py

### Phase 0 完成標準

- Phase 0 處理的 P0-1、P0-2、P0-4、P0-5、P0-6 實際案例都已變成自動測試；P0-3 的雙評級與歷史驗證依計畫留在 Phase 2，不在此階段假裝完成。
- 所有測試通過。
- 0050 名稱正確、99999999 被拒絕。
- 同業不混用、不包含自己。
- release build 不自動產生 PDF，且同時只能有 1 個分析／PDF 工作。
- dev build 即使誤觸兩個分析，也不會互相蓋圖表或 PDF。

### Phase 0 驗收記錄（2026-07-18）

- 全套測試：55 passed。
- 前端 JavaScript：5 個檔案通過 node --check。
- 官方快照 schema 2：共 2,360 筆，包含 1,971 股票、379 ETF、10 TDR。
- 官方 ETF 來源：TWSE OpenAPI 264 筆、TPEx 官方月報下載端點 115 筆。
- Phase 0 無臨時未解 blocker；評級有效性不是漏修，而是明確排入 Phase 2。

## Phase 1：讓每個數字都有來源，並減少重複抓資料

- [x] 建立完整 security registry，至少含 TWSE 股票、TPEx 股票、TWSE ETF 與確認來源後的 TPEx ETF。
- [x] 每筆證券保存 asset_type、market、currency、listing_date、official_source 與 source_updated_at。
- [x] 月營收改接 TWSE／TPEx 官方 OpenAPI，不再讓正常流程固定回空資料。
- [x] 季度 EPS、損益表與資產負債表優先使用官方財務報表端點，並依一般業、金融、金控、保險等報表類型分流。
- [x] Yahoo fallback 只在官方欄位缺少或官方暫時不可用時啟用，且逐欄位標示 fallback。
- [x] 官方更新每日最多一次，使用 required fields、筆數變動、重複代碼與日期檢查。
- [x] 官方更新失敗時保留最後有效快照並標示 stale，不使用空資料覆蓋。
- [x] 建立共用 DataValue 格式。
- [x] 建立每次分析專用的 MarketDataSnapshot。
- [x] 價格抓一次後切成不同期間。
- [x] info、財報與股利同次工作只抓一次。
- [x] 區分網路失敗、來源格式改變、缺資料與程式 bug。
- [x] 工作改為 active=1，加入 deadline、取消與記憶體上限。
- [x] cache 改用下方「建議 cache 與儲存政策」。

主要修改位置：

- services/analysis.py
- stock/data.py
- stock/dividend.py
- stock/calendar.py
- stock/peers.py
- stock/yf_errors.py
- valuation/analyzer.py
- webui.py
- utils/cache.py
- 建議新增 services/market_snapshot.py
- 建議新增 models/data_value.py
- 建議新增 storage/app_db.py
- 建議新增 storage/cleanup.py

### Phase 1 完成標準

- 使用者點每個重要數字都能看到來源、日期、單位與狀態。
- 同一份報告所有資料來自同一分析快照。
- 官方來源改格式時會明確失敗，不會偷偷產出空資料。
- 重複 Yahoo 呼叫明顯減少。
- App 離線時可以使用最後有效主檔，但會清楚顯示資料已過期。

### Phase 1 驗收記錄（2026-07-18）

- 全套測試：72 passed；前端 render.js、app.js 通過 node --check。
- 官方證券主檔 schema 3：2,360 筆，四個來源分別為上市公司 1,090、上櫃公司 891、上市基金 264、上櫃 ETF 115。
- Live 分流驗證：2330 使用 ci、6488 使用 TPEx ci、2881 使用 fh；三者皆取得 2026 Q1 官方資料。
- 官方月營收 Live 驗證：2330、6488、2881 皆取得 2026-06 資料，來源與出表日期可追溯。
- Q2／Q3 官方 EPS 是累計口徑，不偽裝成單季 EPS；單季歷史使用明確標示的 Yahoo fallback。
- cache 使用 SQLite；PDF 三天逐檔清理、工作圖表 24 小時、官方最後有效資料可離線使用並標示 stale。
- 工作固定 active=1，deadline 180 秒；取消為協作式，單次網路呼叫仍可能等到 30 秒 timeout 才停止。
- Phase 1 當日沒有未解 blocker；當時尚未涵蓋的興櫃／特別股／ETN 已在下方 2026-07-19 主檔擴充完成。

### 官方主檔擴充驗收記錄（2026-07-19）

- schema 4 共 2,773 筆：上市 1,403、上櫃 1,015、興櫃 355。
- 商品分類：普通股 2,326、ETF 381、ETN 21、特別股 29、REIT 6、TDR 10。
- 八組官方來源均通過最低筆數、必要欄位、重複代碼、來源網址與日期檢查；更新失敗時仍不覆蓋最後有效快照。
- 020029、020001、2881A、8349A、01001T 與 009825 都有永久測試；英數代碼大小寫皆可直接輸入。
- 每日證券資料只接受 ETF、ETN、REIT 與有已知發行公司的特別股代碼；權證不會進入主檔。
- ETN、REIT、特別股目前只完成「可搜尋、可辨識」。專用分析模型未完成前，App 會清楚停止，不套普通股公式，也不產生錯誤評級或 PDF。

## Phase 2：重新設計評分並做歷史驗證

- [x] 暫時移除現行單一 A～D 總評級的主視覺。
- [x] 建立成長評級 A～F 與財務安全評級 A～F 的獨立資料契約。
- [x] 成長主要 target 定義為未來連續 12 個月營收成長，次要 target 為未來四季累計 EPS 成長；次要 target 尚未驗證，所以不輸出預測數字。
- [x] 成長結果同時輸出預測區間與模型信心，不只輸出 A～F。
- [x] 財務安全不再使用估值安全邊際冒充；估值另列為估值情境。
- [x] 高成長／低安全等衝突必須原樣顯示，不做平均掩蓋。
- [x] 股票與 ETF 使用不同模型。
- [x] 第一版 ETF 不套公司營收／EPS 模型，也不顯示公司式成長 A～F；只提供 ETF 結構安全資訊。
- [ ] 未來取得完整 ETF 持股與成分公司資料後，另行開發並回測「成分股加權成長潛力」模型。
- [x] 第一版金融、金控與保險的財務安全先回「專用模型尚未完成」，不套一般公司公式。
- [ ] 後續使用官方監理指標建立金融、保險專用財務安全模型。
- [x] 為每個模型定義目標、股票範圍、比較基準與更新頻率。
- [ ] 建立真正的「當時可看到內容」歷史資料集。目前 MOPS 歷史封存是事後最新版，不假裝為 point-in-time。
- [x] 成長模型進行時間順序的樣本外測試；財務安全仍缺結果標籤，未宣稱完成。
- [x] 成長模型報告 MAE、方向命中率、正成長 precision／recall 與 Brier 機率校準。
- [x] 保存每版模型的結果與限制。
- [x] 只有通過事先門檻的模型才顯示正式強烈評級；目前成長與安全都只顯示明確標註的實驗分級。

交易成本只有在未來把評級轉成投資組合策略時才需要納入；本階段驗證的是營收／EPS 成長預測，不應用股價報酬反過來偷換 target。

主要修改／新增位置：

- valuation/analyzer.py
- services/analysis.py
- research/backtest/（建議新增）
- research/model_cards/（建議新增）
- tests/test_model_contracts.py（建議新增）

### Phase 2 完成標準

任何評級都能回答：

- 它想預測什麼。
- 適用哪些證券。
- 使用哪些資料。
- 歷史樣本外表現如何。
- 什麼情況不應使用。

### Phase 2 驗收記錄（2026-07-19）

- 正式成長評級沒有通過門檻：測試 MAE 0.1824，最佳零成長基準 0.1788，未達「至少改善 5%」；方向命中率 62.89%、正成長 precision 62.95%、recall 97.74%、Brier 0.2312、80% 區間覆蓋率 82.49%。模型正確保持正式 rating 為空。
- 2330 實跑可輸出實驗 C、預估 +13.12%、80% 區間 -18.58%～+31.00%、正成長可能性 61.39%，但畫面明示未通過驗證。
- 0050 不套公司成長模型，只回 ETF 結構安全實驗篩檢；2882 不套一般公司財務安全公式。
- 財務安全比率公式沒有台灣 point-in-time 危機結果標籤，因此正式 rating 也保持空白；實驗分級不能解讀成破產機率。
- 仍未完成：真正 point-in-time 資料集、一般公司財務危機樣本外驗證、ETF 成分股加權模型、金融監理專用模型。這些是資料研究工作，不以假數字補齊。

### 官方財務危機標籤可行性確認（2026-07-19）

白話結論：官方有「發生了什麼事」的事件資料，但還沒有一份可以直接拿來訓練「未來 12 個月會不會財務出問題」的乾淨答案表。

- TWSE「終止上市公司」官方端點目前回傳 264 筆，涵蓋民國 90～115 年，但欄位只有終止日期、公司名稱與代碼。合併、私有化與真正財務惡化混在一起，不能全部標成財務危機。
- TPEx「歷史暫停／恢復交易」端點目前 232 筆全部是民國 115 年；「變更交易、分盤、管理股票與停止交易」端點是 21 筆目前狀態，不是多年 point-in-time 歷史。
- TWSE 目前的暫停交易與變更交易端點同樣偏向目前狀態。MOPS 可查歷史財報與 XBRL 文件，但本專案沒有保存每次公告當下的原始版本；日後重編或更正會造成偷看到未來資料的風險。
- 因此現階段只保留實驗財務比率篩檢，正式安全 rating 必須是空值。

未來要解鎖正式安全評級，至少要完成：

1. 每日保存官方財報／XBRL 原始檔、公告時間與檔案雜湊，不能只保存事後最新版。
2. 建立事件分類表，分開財務惡化、退票、淨值問題、重整，以及合併、轉上市、主動下市等非危機事件。
3. 對每個歷史評估日只使用當天已公告資料，採時間向前的樣本外測試。
4. 公開 precision、recall、誤報率、漏報率與機率校準；通過預先門檻後才開正式 A～F。

相關程式與未來資料位置：

- models/safety_model.py
- stock/official_financials.py
- research/model_cards/financial_safety_screen_v1.md
- 未來建議新增 research/distress_labels/ 與 point-in-time 原始檔索引；目前尚未建立，避免產生看似完成的空資料夾。

## Phase 3：UI/UX、無障礙與發布準備

- [x] 依已採用方向建立「已確認資料」與「模型推估」兩個主區。
- [x] 結果頁最前面顯示標的、日期、來源、備援狀態和缺資料。
- [x] 同時顯示成長與財務安全，不顯示未定義的單一總評級。
- [x] 公司新聞與產業新聞分開。
- [x] 修正小字對比。
- [x] 修正 combobox、focus 與 aria-live。
- [x] 將前述字型、色彩、間距、狀態與元件規範寫成 docs/UI_DESIGN_SYSTEM.md。
- [x] 使用 Browser Playwright 測 desktop、tablet、mobile。
- [ ] 使用 axe 做基本無障礙檢查。
- [x] 建立固定套件版本與 CI；目前執行 pip check、pip-audit、Ruff、pytest 與 JavaScript 語法檢查。
- [x] 替換沒有授權證據的字型。
- [x] 新增第三方授權清單。

主要修改位置：

- templates/index.html
- static/css/app.css
- static/js/app.js
- static/js/render.js
- static/js/api.js
- static/service-worker.js
- report/generator.py
- report/font.py
- fonts/
- requirements.txt
- requirements-dev.txt
- 建議新增 THIRD_PARTY_NOTICES.md
- 建議新增 docs/UI_DESIGN_SYSTEM.md
- 建議新增 .github/workflows/ci.yml

### Phase 3 完成標準

- 真實瀏覽器完成桌面與手機檢查。
- 純鍵盤可以完成搜尋、分析、閱讀與下載。
- 自動無障礙檢查沒有重大問題。
- 所有散布的字型、圖片與資料都有授權說明。
- CI 會自動執行測試、lint、格式、語法與相依安全檢查。

### Phase 3 驗收記錄（2026-07-19）

- 程式碼、靜態契約與鍵盤焦點流程已有自動測試；結果區不再一次朗讀全部內容。
- Noto Sans TC、OFL 副本、自製 SVG、第三方清單與隱私說明已放入專案及 App bundle。
- Browser 插件重新附加後，已用實際打包 App 完成 `2330` 鍵盤搜尋（ArrowDown／Enter）、五階段分析與結果焦點驗收；正式成長／安全評級保持 N/A，實驗分級與官方／Yahoo 備援來源分開顯示。
- 真實結果頁在手機測出兩層整頁水平溢出：body 強制 320px，以及資料來源雙欄的最小內容寬度。修正後在 300px 手機視窗 `clientWidth=300`、`scrollWidth=300`；平板 627px 與桌面 1187px 也都沒有整頁水平捲軸。
- PDF 按鈕完成 13/13 階段並產生可讀的 15 頁 PDF；最終 App 的瀏覽器 console 無 error／warning。
- 基本無障礙 DOM 檢查通過：無重複 ID、無未命名互動元件、無缺 alt 圖片、無標題層級跳號，且 main／banner／contentinfo 各一個。Axe 與實體螢幕閱讀器仍未執行，不宣稱已通過。
- 關閉流程另重現「連接埠已關閉但 EXE 留在背景」；修正 Waitress keep-alive 通道清理後，真實打包 EXE 在含 PDF 工作的情境下正常退出。
- CI 已加入 pip-audit 2.10.1 與 `ruff format --check`。requirements.txt 目前沒有查到已知漏洞；39 個 Python 檔完成一次性排版，66 個 Python 檔均通過格式 gate。

## Phase 4：本地 App 包裝與公開散布

- [x] 伺服器只綁 127.0.0.1，不開放 LAN／Internet。
- [x] 唯一執行個體：重複啟動時開啟既有服務，不再開第二個服務。
- [x] release build 由使用者按需產生 PDF，不在分析完成後自動產生。
- [x] 可寫資料移到每位 Windows 使用者的 LocalAppData，不寫安裝目錄。
- [x] 唯讀字型、圖示和 template 留在 App bundle。
- [x] 建立 installer、版本號、解除安裝與使用者資料保留／移除選項。
- [x] 公開下載檔提供 SHA-256；正式發行前仍需評估付費 Windows code signing。
- [x] 記錄第三方套件、資料來源、字型、圖片授權與隱私說明。
- [x] 明確說明 Yahoo 備援的限制；商業化前重新確認資料使用授權。

### Phase 4 驗收記錄（2026-07-19）

- Windows portable 與 installer 在 Browser 修正後成功重建，106 項測試、Ruff lint、Ruff format、pip check、pip-audit 與 6 個 JavaScript 語法檢查通過；dist 為 1,712 個檔案、153,647,409 bytes，ZIP 為 80,753,404 bytes。
- portable ZIP SHA-256：d94d878be678d4bc9773647576ddd8eddc29d7dd8d8cd506a5edb38561d97715。
- Setup EXE 為 62,066,691 bytes；SHA-256：4521c2c3bdd26fff7f77642b40b5fea714c861949aeca1a99db40a7ef09664b1。
- EXE 實跑：/ping 204、首頁／manifest／前端 JS 200、首頁 no-store；內建主檔 2,773 筆且 020029 搜尋回 ETN；第二個實例以 0 結束且第一個服務仍存活；受保護 shutdown 後主程式以 0 結束。
- Inno Setup 6.7.3 安裝版實跑：靜默安裝、已安裝 App `/ping` 204、首頁 200、manifest 版本 0.2.0-dev、020029 回傳 ETN、第二實例正常結束、受保護 shutdown 與解除安裝均回傳 0。使用者資料會保留。
- 受限沙箱內安裝曾回傳代碼 4；Inno log 證實是沙箱拒絕開始功能表、桌面捷徑與 HKCU 解除安裝登錄鍵，不是 Setup 損壞。改用已授權的正常 Windows 權限後，同一檔案完整通過上述驗收。
- 解除安裝後程式內容數為 0，但留下空的安裝資料夾；屬低風險清理問題，不影響 App 或使用者資料。
- 原始碼、portable 與 installer 均包含 MIT License，Copyright (c) 2026 胖貓貓工作室。
- Setup EXE 與主程式的 Authenticode 狀態皆為 NotSigned；公開散布時可能觸發 SmartScreen，正式穩定版建議評估程式碼簽章。

建議 Windows 資料位置：

- %LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\data\app.db
- %LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\cache\
- %LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\output\
- %LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\logs\
- %TEMP%\TWStockAnalysis\{task_id}\ 只放工作中間檔

初次檢測時 config.py 把 cache 與 output 建在專案旁邊；目前 release 已改存每位使用者的 LocalAppData，安裝目錄只放唯讀程式資源。

## 建議 cache 與儲存政策

### 目前實際狀況

2026-07-18 唯讀盤點：

| 類型 | 檔案數 | 大小 | 問題 |
|---|---:|---:|---|
| cache 全部 | 211 | 約 11.6 MiB | 162 檔已超過三天 |
| 圖表 | 151 | 約 10.9 MiB | 沒有 TTL，是目前主要占用 |
| JSON cache | 54 | 約 0.63 MiB | 100 筆上限只作用於這一類 |
| yfinance SQLite／log | 6 | 約 0.05 MiB | 由 yfinance 與 runtime 產生 |
| output PDF | 3 | 約 1.8 MiB | 沒有自動清理；目前恰好都未滿三天 |

因此目前不是容量立即失控，而是「沒有真正清理規則」。圖表會一直累積，舊 JSON 失效後仍留在磁碟。

### 建議 TTL

| 資料種類 | 建議有效期限 | 原因 |
|---|---:|---|
| 官方證券主檔 | 每 24 小時檢查更新 | 掛牌、下市與名稱不需每次分析重抓 |
| 最後有效官方快照 | 保留最新與前一版，舊版最多 30 天 | 官方中斷或 schema 異常時可回復 |
| 盤中／近期價格 | 10 分鐘 | 單人研究工具不需每秒更新；畫面仍要顯示價格時間 |
| 收盤後價格 | 到下一個預定更新時段 | 收盤後同一交易日不必反覆抓 |
| 月營收、季度 EPS、財報 | 24 小時 | 官方資料發布頻率低於行情 |
| 股利與財報行事曆 | 12 小時 | 日期偶爾更新，但不需每分鐘查 |
| 同業結果 | 6 小時，底層資料更新時立即失效 | 同業本身變動慢，但不能跨 subject 污染 |
| 新聞 | 15 分鐘 | 保持時效，又避免每次切換畫面重抓 |
| 工作圖表 | 工作完成後刪除；失敗殘留最長 24 小時 | 圖表只是 Web／dev PDF 中間檔 |
| dev PDF output | 每個檔案 3 天 | 符合產品決策 |
| log | 14 天，且總量最多 20 MiB | 保留 debug 證據但避免無限增長 |

三天期限建議採「逐檔刪除超過三天的檔案」，不要因為一個舊檔就清空整個 output。這樣不會誤刪仍在三天內的報告。

### 建議容量上限

- 一般 cache 總上限：256 MiB。
- 觸發清理水位：超過 200 MiB 開始依 last_accessed_at 刪除，清到 160 MiB。
- dev output 總上限：250 MiB；即使全部未滿三天，超過上限仍從最舊檔開始刪。
- log 總上限：20 MiB。
- 工作 temp：每次 task 結束立即清除；App 啟動時再清除超過 24 小時的殘留。

256 MiB 對目前約 11.6 MiB 的使用量有足夠餘裕。若未來要預先下載「全市場多年歷史行情」，那不應放進一般 cache，應另建可管理的 dataset 儲存區與獨立容量設定。

### 什麼時候執行清理

1. App 啟動時先做一次快速清理。
2. App 持續開啟時，每 6 小時最多做一次。
3. 寫入新 cache 或 PDF 後，若超過容量水位再清理。
4. App 非正常關閉後，下次啟動清除過期 temporary files。
5. 清理只能操作預先解析並確認在 App data root 內的路徑。

### 建議儲存方式

不建議繼續讓每個小資料都變成一個 JSON 檔。對本地單人 App，最簡單且可靠的是混合儲存：

#### SQLite：存結構化資料與 cache 索引

建議存：

- securities：股票、ETF、TDR 等證券主檔。
- source_runs：每次官方更新的 URL、時間、狀態、筆數與 hash。
- cached_responses：cache key、來源、抓取時間、到期時間、最後讀取時間與 payload。
- schema_version：資料庫版本。
- app_settings：不含秘密的本機設定。

建議開啟 WAL mode、transaction 與 migration。SQLite 是 Python 內建能力，單人本地 App 不需要額外伺服器。

#### 檔案系統：存大型或暫時產物

- PDF 留在 output，不要塞進 SQLite。
- 圖表放 task temp，完成後刪除。
- 官方最後有效 snapshot 可另外保留一份壓縮 JSON，讓資料庫壞掉時仍可救援。
- 圖片、字型、HTML、CSS、JS 是唯讀 App assets，留在 bundle。

#### 未來真的要保存全市場多年資料

若需求變成保存所有股票多年 OHLC、財報與回測資料，建議使用依市場／年份分區的 Parquet，並以 DuckDB 查詢。這是 dataset，不是 cache；需要新的相依套件與容量規劃，不能在本輪 bug 修正時順便加入。

### 主要修改位置

- config.py：改用 LocalAppData 與 dev／release mode。
- utils/cache.py：改為真正的 expiry、last access 與容量清理。
- stock/data.py：圖表改進 task temp。
- webui.py：啟動清理、單一工作、取消與按需 PDF。
- report/generator.py：三天 output、唯一檔名與 atomic write。
- 建議新增 storage/app_db.py。
- 建議新增 storage/cleanup.py。
- 建議新增 tests/test_storage_policy.py。

## P2：最後再整理

這些問題不應搶在 P0 前面：

- 清除沒有使用的 import、變數與舊註解。
- [x] 統一 Ruff 格式（2026-07-19 完成，66 個 Python 檔通過檢查）。
- 釐清 cache 到底是 LRU 還是只按檔案寫入時間清理。
- 不要讓 Service Worker 長期保存含 shutdown token 的首頁。
- mobile 大表格改成卡片或清楚提示可以左右滑動。
- 為 snapshot、分析結果與 PDF 加版本號。

檔案位置：

- Ruff 顯示的 Python 檔案。
- utils/cache.py，第 39、48 行附近。
- static/service-worker.js，第 1～53 行。
- static/css/app.css。
- templates/index.html。

## 執行時不要混在一起做的事情

為了比較容易確認哪個修改造成問題，建議分開：

1. 不要把功能修正和全專案格式化放在同一批。
2. 不要一邊修 cache，一邊重新設計整個評分模型。
3. 不要先美化 A～F，再處理它沒有回測證據的問題。
4. 不要直接刪除字型，先確認 PDF 替代字型可正常顯示中文。
5. 不要更新官方 snapshot 後只看檔案存在；要檢查筆數、重複、空欄位與 ETF。

## 已確認的模型邊界

已確認：

- 免費開源。
- 成長評級預測未來 12 個月公司營收／EPS 成長，不預測股價。
- 使用成長 A～F、財務安全 A～F 兩個獨立總評級。
- 主檔包含上市、上櫃、興櫃、TDR、特別股、ETF、ETN；排除權證與債券。
- TPEx ETF 接受官方下載檔／官方快照，不做未授權爬蟲。
- release 分析完成後提供按需「產生並下載 PDF」，不自動產生。
- 完整證券主檔、詳細資料按需抓取。
- 金融、金控與保險第一版顯示「專用模型尚未完成」，不使用一般公司公式製造錯誤評級；官方事實資料照常顯示。
- ETF 第一版不顯示公司式成長 A～F，只提供 ETF 結構安全資訊。
- 未來修正：取得完整 ETF 持股與成分公司資料後，開發並以歷史資料驗證「成分股加權成長潛力」模型；通過預定門檻後才顯示 ETF 成長評級。

## 整份專案修好後應該達到的狀態

- 0050 等 ETF 可以用名稱和代碼找到，metadata 正確。
- 已確認範圍內的所有掛牌證券都有 asset_type、market、currency、listing_date 與官方來源。
- 不存在的代碼不會被當成股票。
- 缺資料只顯示資料不足，不會產生看似正常的分數。
- 同業真的相似，不受清單順序或前一次查詢影響。
- 日期、單位、幣別與來源都能查到。
- release App 同時只允許一個分析／PDF 工作；分析完成後可由使用者按需產生並下載 PDF，dev 才可另開自動產生供測試。
- dev PDF 不會混圖、覆蓋或留下超過三天的檔案。
- 成長與財務安全分開顯示；若評級存在，就有清楚目標與樣本外歷史證據。
- 金融、金控、保險在專用模型完成前不顯示財務安全 A～F；ETF 在加權成長模型完成前不顯示成長 A～F。
- 已確認資料與模型推估分區呈現，Yahoo 備援會明確標示。
- cache 有分資料種類 TTL、256 MiB 上限、真正 last-access 清理與啟動清理。
- 使用者資料存入 LocalAppData，不寫入安裝目錄。
- 桌面、手機、鍵盤與螢幕閱讀器使用情境都有驗收。
- 所有套件、字型、圖片和資料的版本與授權可追蹤。

在完成以上條件前，畫面和報告應清楚寫明：這是資料整理與研究輔助工具，不是投資建議；分數不保證未來報酬。

## 參考的官方資料

- TWSE OpenAPI：https://openapi.twse.com.tw/
- TWSE 終止上市公司：https://openapi.twse.com.tw/v1/company/suspendListingCsvAndHtml
- TWSE ETN 商品清單：https://www.twse.com.tw/zh/products/securities/etn/products/domestic.html
- TWSE 網站使用條款：https://www.twse.com.tw/zh/terms/use.html
- TPEx OpenAPI：https://www.tpex.org.tw/openapi/
- TPEx 歷史暫停／恢復交易：https://www.tpex.org.tw/openapi/v1/tpex_spendi_history
- TPEx 目前變更／停止交易：https://www.tpex.org.tw/openapi/v1/tpex_cmode
- TPEx ETF InfoHub：https://info.tpex.org.tw/ETF/en/filter.html
- MOPS XBRL 與歷史文件入口：https://mops.twse.com.tw/mops/
- TPEx 網站使用條款：https://www.tpex.org.tw/zh-tw/gtsm_disclaimer.html
- W3C 一般文字對比說明：https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum
- W3C Combobox 設計方式：https://www.w3.org/WAI/ARIA/apg/patterns/combobox/
- Matplotlib thread safety：https://matplotlib.org/stable/users/faq.html
- yfinance 使用定位：https://ranaroussi.github.io/yfinance/index.html
- Piotroski 原始研究：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455
- 回測過度擬合研究：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659
