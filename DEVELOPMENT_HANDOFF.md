# 台股研究室：開發交接文件

更新日期：2026-07-19
交接基準版本：`0.2.0-dev`
交接基準 commit：`4b1c8bece5c90f9f7fa959a0260510de03b68e02`（`feat: complete audited desktop release`）
目前分支：`main`

> 這份文件是換手開發的入口。它記錄目前真的完成了什麼、哪些地方刻意停用、測試證據、建置方式與下一步優先順序。問題的逐項證據與歷史修正紀錄仍以 [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md) 為準。

## 1. 先用 30 秒理解這個專案

這是一套免費、MIT 開源、在 Windows 本機執行的台股研究工具，著作權人為「胖貓貓工作室」。使用者透過瀏覽器介面搜尋台灣掛牌證券，程式會整理官方資料、Yahoo 備援資料、估值、財務風險訊號、新聞索引與模型推估，並可自行下載 PDF。

目前產品定位是「公開測試版的本機研究工具」，不是交易系統，也不是已完成學術或金融實證的預測產品。

最重要的產品規則：

1. 「成長」和「財務安全」是兩個獨立評級，不能平均成總分。
2. 成長模型預估的是未來連續 12 個月營收成長，不是股價。
3. 已確認資料與預估資料必須分區顯示。
4. 正式 A～F 沒通過驗證門檻前保持空白；目前只能顯示「實驗分級」。
5. 官方資料優先，Yahoo 只做備援，而且每個欄位都要標示來源、日期、備援與過期狀態。
6. 不同證券不能硬套普通公司公式；不適用時寧可停止並說明。
7. Release App 只監聽 `127.0.0.1`，同時只允許一個使用者、一個工作與一個程式執行個體。
8. PDF 只在使用者按下按鈕後產生，不在每次分析時自動建立。

## 2. 目前 Git 與交付狀態

| 項目 | 現況 |
|---|---|
| 分支 | `main` |
| 已提交基準 | `4b1c8be` |
| 遠端 repository | 尚未設定 |
| Git tag / GitHub Release | 尚未建立 |
| 開源授權 | MIT，Copyright (c) 2026 胖貓貓工作室 |
| Windows 數位簽章 | 尚未簽署，公開下載可能出現 SmartScreen 警告 |
| 交接文件本身 | 建立後會是未提交變更，需由接手者確認後另行 commit |

`release/`、`dist/`、`build/` 等產物受 `.gitignore` 管理，不應把大型打包產物直接提交到 Git。未來應建立遠端 repository，再用正式 Release 附件發佈 ZIP、Setup EXE 與 SHA-256。

## 3. 已完成並有證據的狀態

### 3.1 功能與資料

- 內建官方證券快照 schema 4，共 2,773 筆：
  - 普通股票：2,326
  - ETF：381
  - ETN：21
  - 特別股：29
  - REIT：6
  - TDR：10
- 涵蓋上市、上櫃與興櫃；權證與債券目前排除。
- 可使用代號、中文名稱或別名搜尋，英數混合證券代號可直接輸入。
- 分析流程、取消、重新整理後恢復任務、按需 PDF、CSV 匯出、來源標示與過期資料提示均已實作。
- Release 模式的可寫資料放在 `%LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\`，不寫入唯讀的程式 bundle。
- 單一執行個體、loopback 綁定、正常關閉與 installer 安裝／解除安裝流程已實測。

### 3.2 最後一次完整自動檢查

- `pytest`：106 項通過。
- Ruff lint：通過。
- Ruff format：66 個 Python 檔通過。
- `pip check`：通過。
- `pip-audit 2.10.1`：runtime 相依套件未查到已知漏洞。
- JavaScript：6 個檔案通過 `node --check`。
- Browser 真實流程：鍵盤搜尋 2330、方向鍵與 Enter、五階段分析、結果焦點、來源標示、PDF 13/13 步驟均通過；實際 PDF 為 15 頁。
- 300px、627px、1187px 三種寬度未出現整頁水平溢位。
- Browser console 無 error 或 warning；基本 DOM 無障礙檢查通過。

### 3.3 最後打包產物

| 產物 | 大小 | SHA-256 |
|---|---:|---|
| `release/TWStockAnalysis-portable-0.2.0-dev.zip` | 80,753,404 bytes | `d94d878be678d4bc9773647576ddd8eddc29d7dd8d8cd506a5edb38561d97715` |
| `release/TWStockAnalysis-Setup-0.2.0-dev.exe` | 62,066,691 bytes | `4521c2c3bdd26fff7f77642b40b5fea714c861949aeca1a99db40a7ef09664b1` |

這些是本機打包結果，不在 Git 追蹤內。重新建置後檔案與 hash 一定會改，應以新的 `release/SHA256SUMS.txt` 為準。

### 3.4 與最初版本相比，完成度到底差多少

比較基準是最初 Git commit `ff558d7`（`chore: establish project baseline`）與目前 commit `4b1c8be`。這裡必須把「畫面體感」、「工程完成度」與「正式預測能力」分開看，否則容易誤判。

| 觀察角度 | 最初版本 | 目前版本 | 結論 |
|---|---:|---:|---|
| 畫面與操作體感 | 約 8/10 | 約 8.5/10 | 原本功能已很多，所以肉眼差異不大 |
| 軟體工程與公開測試準備 | 約 2/10 | 約 7.5/10 | 資料、測試、安全、儲存與打包提升明顯 |
| 通過正式驗證的投資模型 | 0/2 | 0/2 | 核心預測能力仍未完成，不能宣稱已變準 |

可直接驗證的數字：

| 項目 | 最初版本 | 目前版本 | 差別 |
|---|---:|---:|---:|
| 可搜尋證券 | 371 筆 | 2,773 筆 | 增加 2,402 筆，約 7.47 倍 |
| repository 內自動測試 | 0 項 | 106 項通過 | 從無回歸保護到主要流程有測試 |
| 正式評級模型通過數 | 0 | 0 | 尚未完成 |
| 實驗評級 | 混合 A～D 總分 | 成長、安全兩套且分開 | 降低誤導，但不代表預測已驗證 |
| 主要資料來源 | Yahoo、HiStock 與硬編清單 | 官方優先、Yahoo 備援、逐欄來源 | 可信度與可追溯性提升 |
| Windows 交付 | 無正式流程 | Portable ZIP、Setup EXE、SHA-256 | 已能交給測試者安裝 |
| CI | 無 | Windows CI 與完整 gate | 每次 push／PR 可自動攔截回歸 |
| 開源與第三方授權 | 不完整 | MIT、字型授權、第三方聲明 | 符合公開原始碼的基本交付需求 |

從最初基準到目前共涉及 111 個檔案，約新增 58,263 行、刪除 4,438 行；但大量新增內容是官方證券快照、測試和文件，行數只能表示修改規模，不能直接當成品質。

以下是為換手排序而建立的內部量表，不是金融業認證：

| 面向 | 權重 | 最初版本 | 目前版本 |
|---|---:|---:|---:|
| UI 與可見功能 | 15 | 12 | 13 |
| 資料覆蓋與來源可信度 | 20 | 5 | 17 |
| 模型合理性與防誤導 | 20 | 3 | 8 |
| 測試與穩定性 | 20 | 1 | 17 |
| 安全與本機資料管理 | 15 | 3 | 12 |
| 安裝、授權與發布 | 10 | 0 | 7 |
| **合計** | **100** | **24** | **74** |

最誠實的解讀是：目前已從「功能很多但缺少證據的展示程式」提升為「可公開測試的本機 App」，但還不是「已證明能預測未來成長與財務危機的正式投資工具」。下一階段不應繼續堆畫面功能，而應優先補齊正式模型所需的資料與驗證證據。

## 4. 架構與資料流

~~~mermaid
flowchart LR
    U["使用者 / 本機瀏覽器"] --> W["webui.py / Flask + Waitress"]
    W --> A["services/analysis.py"]
    A --> R["stock/ 官方資料與證券主檔"]
    A --> Y["services/market_snapshot.py / Yahoo 備援"]
    A --> M["models/ 成長與安全實驗模型"]
    A --> V["valuation/ 估值與研究指標"]
    A --> N["news/ 新聞索引"]
    A --> S["storage/ SQLite cache 與清理"]
    A --> UI["templates + static/js + static/css"]
    UI --> U
    W --> P["report/ 按需 PDF"]
    P --> U
~~~

### 4.1 主要檔案地圖

| 路徑 | 責任 | 換手時注意 |
|---|---|---|
| `webui.py` | Flask 路由、任務狀態、SSE、下載、關閉與 Waitress 啟動 | `_close_waitress_server()` 不可隨意簡化，否則關閉後 EXE 可能殘留 |
| `services/analysis.py` | CLI 與 Web 共用的分析流程 | 新分析步驟應同時維持取消、進度與期限處理 |
| `main.py` | CLI 入口 | 可用 `python main.py 2330` 快速確認分析資料 |
| `config.py` | dev/release 路徑、cache、output、log 與字型 | 不要讓 release 寫回 bundle |
| `stock/normalizer.py` | 證券主檔、搜尋與標準化 | 新資產類別需先定義適用模型，不可只加入搜尋後硬套公式 |
| `stock/official_stock_snapshot.json` | 版本化官方證券主檔 | 更新失敗不得覆蓋最後有效版本 |
| `stock/official_financials.py` | 官方財務資料 | 保留逐欄來源與資料日期 |
| `stock/mops_history.py` | 公開資訊觀測站歷史資料 | 未來 point-in-time 工作的核心位置 |
| `services/market_snapshot.py` | 共享行情快照與 Yahoo 備援 | Yahoo 不是主要可信來源，必須顯示 fallback |
| `models/growth_model.py` | 12 個月營收成長實驗模型 | 不是股價模型，正式評級 gate 不能拿掉 |
| `models/safety_model.py` | 財務安全實驗篩檢 | 不是破產機率；金融業不得套一般公司公式 |
| `research/model_cards/` | 模型目標、限制與適用範圍 | 模型改版要同步更新 |
| `research/backtest/` | 回測與模型驗證產物 | 必須保存基準、切分與失敗結果，不只留下最好數字 |
| `valuation/analyzer.py` | 估值與既有研究型指標 | 估值、成長與安全不可混成單一結論 |
| `templates/index.html` | 頁面結構與無障礙語意 | 修改後需重跑鍵盤與窄螢幕驗收 |
| `static/css/app.css` | UI 規範的實作 | 手機溢位曾在這裡修正，需測 300px |
| `static/js/api.js` | API 呼叫 | 動態 API 不應被 Service Worker 快取 |
| `static/js/app.js` | 互動與任務流程 | 保持單工、取消與焦點管理 |
| `static/js/dom.js` | 安全 DOM 建構 | 外部文字不可改回 `innerHTML` 拼接 |
| `static/js/render.js` | 結果畫面與來源標示 | 可信資料與預估資料必須分區 |
| `static/js/export.js` | CSV 匯出 | 必須保留試算表公式注入中和 |
| `static/service-worker.js` | 靜態資源離線快取 | 不得快取分析結果、task、download 等動態回應 |
| `report/` | PDF 產生器 | 只允許使用者按需產生；未支援資產不得產 PDF |
| `storage/` | SQLite cache、工作檔與自動清理 | 調整 TTL 或容量時同步文件與測試 |
| `packaging/` | PyInstaller 與 Inno Setup 設定 | 安裝版仍未簽章 |
| `scripts/build_windows.ps1` | Windows 檢查與打包 | 腳本目前未執行 `ruff format --check` 與 `pip-audit`，打包前要手動跑完整 gate |
| `tests/` | 自動回歸測試 | 修 bug 時應先增加或更新針對性測試 |
| `docs/UI_DESIGN_SYSTEM.md` | 字型、色彩、間距、狀態、元件規範 | UI 變更必須依此規範 |
| `docs/PRIVACY.md` | 本機資料與外部連線說明 | 新增外部來源或遙測前必須更新 |
| `THIRD_PARTY_NOTICES.md` | 套件、字型、圖示與資料來源 | 更新依賴或資產時同步更新 |
| `PROJECT_AUDIT_REPORT.md` | 完整稽核證據、真實問題與 checklist | 這是 debug 歷史與證據主檔，不要用新摘要取代 |

## 5. Web API、任務生命週期與資源上限

目前端點：

| 方法 | 路徑 | 用途 |
|---|---|---|
| GET | `/` | 主畫面 |
| GET | `/search` | 證券搜尋 |
| POST | `/analyze` | 建立分析工作 |
| GET | `/task/<task_id>` | 取得工作狀態 |
| GET | `/stream/<task_id>` | SSE 進度事件 |
| POST | `/task/<task_id>/report` | 建立 PDF 工作 |
| POST | `/task/<task_id>/cancel` | 取消工作 |
| GET | `/download/<filename>` | 下載輸出檔 |
| POST | `/shutdown` | 安全關閉本機 App |
| GET | `/ping` | 健康檢查 |
| GET | `/manifest.json` | PWA manifest |

硬性限制位於 `webui.py`：

- 同時工作數：1。
- 分析期限：180 秒。
- PDF 期限：180 秒。
- 單一結果上限：64 MiB。
- 事件上限：200 筆或 4 MiB。
- 工作總 TTL：1 小時。
- 結束狀態 TTL：10 分鐘。

這些限制是公開給一般使用者時的防呆與資源保護，不應只為了讓大型輸出成功就任意放寬。若真的需要調整，要同時評估記憶體、磁碟、取消、錯誤訊息與惡意輸入。

## 6. 資料來源與可信度契約

### 6.1 優先順序

1. TWSE、TPEx、公開資訊觀測站等官方來源。
2. 已保存的最後有效官方版本；離線時可以用，但畫面必須標示 stale。
3. Yahoo Finance／yfinance 備援，畫面必須標示 Yahoo 或 fallback。

新聞只保存索引用的標題、摘要、來源與連結，不保存全文。

### 6.2 每個資料欄位應保留

- 值。
- 資料來源。
- 資料日期或取得時間。
- 是否為備援。
- 是否過期。
- 缺值或不適用原因。

不要只在頁尾寫一行「資料來源」，因為同一頁可能混合官方、Yahoo 與模型資料。來源需要跟著欄位或區塊走。

### 6.3 資產類別適用邊界

| 類別 | 搜尋 | 一般公司成長模型 | 一般公司安全模型 | PDF |
|---|---:|---:|---:|---:|
| 一般股票／TDR | 是 | 實驗性，可受 gate 限制 | 實驗性，可受 gate 限制 | 是 |
| 金融、金控、銀行、保險 | 是 | 需依資料判斷 | 否，待監理專用模型 | 可顯示適用限制 |
| ETF | 是 | 否，待成分股加權模型 | 否，只做 ETF 結構實驗篩檢 | 僅限已支援內容 |
| ETN | 是 | 否 | 否 | 否 |
| REIT | 是 | 否 | 否 | 否 |
| 特別股 | 是 | 否 | 否 | 否 |
| 權證／債券 | 否 | 否 | 否 | 否 |

## 7. 模型現況：最容易被誤解的部分

### 7.1 成長模型

- 目標：未來連續 12 個月營收成長。
- 不等於股價預測、投資報酬率或買賣建議。
- 目前可以顯示預估成長百分比、80% 估計區間、正成長可能性與實驗分級。
- 正式 A～F 必須保持空白，因為模型沒有比事先指定的最佳 MAE 基準好 5%。
- 現有歷史資料是「最新修訂版」，不是真正按每個公告日封存的 point-in-time 資料，可能產生回看偏誤。
- EPS 次要目標尚未完成歷史驗證，不應產生看似精準的 EPS 預測數字。

### 7.2 財務安全模型

- 目前是一般公司的財務風險實驗篩檢，使用負債、流動性、保留盈餘與獲利能力等訊號。
- 沒有完整的台灣公司「未來發生財務危機／下市／違約」結果標籤，因此不是破產機率。
- 正式 A～F 保持空白，只能顯示實驗分級、分數與限制。
- 金融與保險業的資產負債結構不同，不得套一般公司公式。

### 7.3 正確的下一階段研究順序

1. 建立按公告日封存、可重現的 point-in-time 資料集。
2. 先凍結目標、基準、時間切分與驗收門檻，再訓練模型。
3. 成長模型使用 rolling／walk-forward 時間驗證，避免隨機切分造成未來資料洩漏。
4. 安全模型先定義可稽核的危機標籤與觀察窗，再處理類別不平衡、校準與樣本外驗證。
5. 報告 MAE、方向正確率、區間涵蓋率、校準、不同產業與不同市值分組結果，不只報一個總分。
6. 通過既定門檻後才能開啟正式 A～F；失敗結果也要保存在 `research/`。

## 8. 本機儲存、cache 與清理規則

Release 資料根目錄：

~~~text
%LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\
├─ cache\
├─ logs\
└─ output\
~~~

| 類型 | 現行規則 | 原因 |
|---|---|---|
| PDF/output | 保留 3 天；總量超過 250 MiB 時先刪最舊檔 | 滿足短期重新下載，不讓報告無限累積 |
| 工作圖表 | 保留 24 小時 | 工作結束後不需要長期占空間 |
| cache | 硬上限 256 MiB；超過 200 MiB 清到 160 MiB | 用高低水位避免每次只刪一點又立即重清 |
| log | 保留 14 天；總量上限 20 MiB | 足夠診斷近期問題，避免長期洩漏或膨脹 |
| 清理頻率 | 每 6 小時最多一次 | 不必每個 request 都完整掃描磁碟 |

這比固定每幾天整批刪除好：常用官方資料可以繼續使用，不常用檔案依時間和容量逐筆淘汰。規則位置為 `config.py` 與 `storage/cleanup.py`。

目前解除安裝會保留 `%LOCALAPPDATA%` 的使用者資料，避免誤刪 PDF、cache 與 log。程式內容會移除，但實測可能留下空的安裝資料夾，屬低優先問題。

## 9. UI、UX 與無障礙規則

- 視覺規範以 `docs/UI_DESIGN_SYSTEM.md` 為準，包含 Noto Sans TC、色彩、間距、狀態與元件。
- 不可只用顏色表達成功、警告、來源或風險，必須同時有文字或圖示。
- 觸控目標至少 44px。
- 搜尋 combobox、方向鍵、Enter、焦點移動與分析完成後的結果焦點已實作。
- 可信資料、預估資料、新聞與限制要有清楚區塊，不要把所有卡片混在一起。
- 窄螢幕至少重測 300px；手機整頁水平溢位曾經是實際 bug。
- 已完成 Browser 的基本 DOM 檢查，但尚未完成 Axe 自動掃描與實體 NVDA／Windows Narrator 驗收。這兩項不能標成已完成。

## 10. 安全邊界與不可破壞的防護

- Waitress 只綁 `127.0.0.1`，不要改成 `0.0.0.0` 對 Internet 開放。
- `/shutdown` 需要隨機 token、loopback、Host 與同源檢查。
- CSP 禁止 inline script 與 inline style。
- 外部文字使用安全 DOM API，不要把新聞、名稱或錯誤文字直接插入 `innerHTML`。
- CSV 匯出必須中和以 `=`, `+`, `-`, `@` 開頭的試算表公式。
- Service Worker 只快取固定靜態資源，不得快取 task、分析、下載或其他動態 API。
- 檔名、task ID 與下載路徑需要持續防止 path traversal。
- 不記錄 `.env`、token、完整個資或不必要的外部回應內容。
- 新增外部資料來源前，先確認官方性、穩定性、授權與公開散布條款，再更新 `docs/PRIVACY.md` 與 `THIRD_PARTY_NOTICES.md`。

## 11. 開發環境與常用命令

需求：Windows、Python 3.12。完整打包另需 Node.js 20+、PyInstaller 與 Inno Setup。

### 11.1 安裝與啟動

~~~powershell
python -m pip install -r requirements-dev.txt
python webui.py
~~~

指定連接埠：

~~~powershell
python webui.py 5050
~~~

CLI 快速測試：

~~~powershell
python main.py 2330
~~~

更新官方證券快照：

~~~powershell
python scripts\update_stock_snapshot.py
~~~

更新快照後至少確認：schema、筆數、各資產類別、重複代號、空名稱、來源 URL、更新失敗不覆蓋最後有效版本，以及一組代表性搜尋。

### 11.2 每次 commit 前的完整 gate

~~~powershell
python -m pip check
python -m pip_audit -r requirements.txt --progress-spinner off
python -m ruff check .
python -m ruff format --check .
python -m pytest -q -p no:cacheprovider
node --check static\js\api.js
node --check static\js\app.js
node --check static\js\dom.js
node --check static\js\export.js
node --check static\js\render.js
node --check static\service-worker.js
git diff --check
~~~

CI 位於 `.github/workflows/ci.yml`，使用 Windows latest 與 Python 3.12，會執行上面的相依性、安全、格式、測試與 JavaScript 語法 gate。

### 11.3 Windows 打包

Portable：

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
~~~

Portable + Setup EXE：

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Installer
~~~

注意：目前 `scripts/build_windows.ps1` 會跑 `pip check`、Ruff lint、pytest 與 JS syntax，但不會跑 `pip-audit` 和 `ruff format --check`。建立公開版本前要先手動執行完整 gate。

打包完成後要實際驗收，不可只看 build exit code：

1. 從全新目錄解壓 portable 並啟動。
2. 確認只監聽 loopback、內建 2,773 筆主檔可用。
3. 搜尋一般股票、ETF、ETN 與至少一個英數代號。
4. 完成 2330 分析、取消一個工作、產生並下載 PDF。
5. 重複啟動確認單一執行個體。
6. 按正常關閉後確認背景 EXE 消失。
7. 安裝 Setup、啟動、重複啟動、關閉、解除安裝。
8. 重新計算 hash，確認 `SHA256SUMS.txt` 與實際檔案相同。

## 12. 已知環境問題與踩雷紀錄

1. 關閉 App 時只呼叫 `server.close()` 會留下 Waitress keep-alive channel，造成 EXE 殘留。`webui.py` 的 `_close_waitress_server()` 會先關閉 channel 再關 server；不要未經回歸測試就刪除。
2. 300px 手機版曾因 `body` 最小寬度與來源清單欄位造成整頁水平捲軸。修改全域 layout、grid 或來源欄位後必須重測。
3. 在受限 sandbox 安裝／解除安裝時，建立捷徑與寫入 HKCU 可能回傳 code 4；一般 Windows 權限下已實測安裝、啟動與解除安裝成功。判讀 installer 問題時需分清楚權限限制與產品 bug。
4. `yfinance` 預設會把 SQLite cookie／timezone cache 寫到使用者 profile，現在已強制放入專案或 LocalAppData 的 cache。不要移除此設定。
5. 正式打包是本機桌面 App，不是公開 Web server。若未來要改為多人 Web 服務，需要重新設計驗證、授權、CSRF、工作佇列、資料隔離、監控與部署，不是把 host 改成 `0.0.0.0` 就完成。

## 13. 下一手開發優先順序

建議主線是先完成「可信資料 → 可重現驗證 → 正式模型」，再補不同資產與正式發佈。現階段不建議優先大改 UI，因為使用者真正缺少的不是更多卡片，而是能證明評級可信的資料與驗證結果。

範圍界線：

- 納入：point-in-time 官方資料、成長與安全模型驗證、ETF／金融專用方法、無障礙、數位簽章與正式開源發佈。
- 暫不納入：股價目標預測、把成長與安全合成單一總分、多人公開 Web server，以及在模型證據完成前進行大幅 UI 裝飾或架構重寫。

### P0：換手後先確認基準沒有漂移

- 先跑完整 gate，確認仍是 106 tests 通過。
- 啟動原始碼版，跑一次 2330 完整流程與 PDF。
- 確認 `git status`，不要把 `build/`、`dist/`、`release/`、cache、log 或 PDF 誤提交。
- 對照 `PROJECT_AUDIT_REPORT.md` 的 checklist，不要只相信本交接摘要。

### P1：建立真正可驗證的正式模型

- 建置 point-in-time 財報與月營收資料集。
- 保存來源、公告時間、版本與修訂關係，避免模型偷看到預測當時尚未公開的資訊。
- 固定時間切分、基準與驗收門檻。
- 建立財務危機標籤與樣本外測試。
- 保存成功與失敗實驗，更新 `research/backtest/` 與 `research/model_cards/`。
- 通過門檻前維持正式 A～F 空白。

完成條件：資料集可從乾淨環境重現、沒有未來資料洩漏，而且成長與安全模型各自得到明確的「通過」或「不通過」結論。這是最優先、也最能實際提高產品價值的工作。

### P2：補齊不同資產的專用方法

- 第一順位 ETF：成分股、權重、追蹤指數、集中度、流動性、折溢價與加權成長。
- 第二順位金融／保險：資本適足、資產品質、準備金、監理與產業專用風險。
- 第三順位 REIT、ETN、特別股：先定義使用者問題與資料契約，再決定是否提供評級和 PDF。

完成條件：每種資產都有自己的適用欄位、停止條件、測試與模型卡，不得回退成套用普通股公式。

### P3：完成公開測試版品質工作

- 執行 Axe 並保存報告。
- 使用 Windows Narrator 或 NVDA 完成主要流程，記錄實體輔具結果。
- 購買或配置 Windows code-signing certificate，簽署主程式與 installer，再測 SmartScreen／簽章資訊。
- 修正解除安裝後空資料夾的低優先問題。

完成條件：主要流程沒有 Axe critical／serious 問題、實體閱讀器能完成核心任務，而且公開安裝檔能顯示可驗證的發行者。

### P4：正式開源發佈

- 設定 Git remote。
- 決定版本號與 release notes。
- 建立 tag 與 GitHub Release。
- 上傳 portable、installer、SHA-256、授權與已知限制。
- 公開頁面要明確寫出：本機工具、非投資建議、模型尚為實驗性、資料來源與 Yahoo 備援限制。

完成條件：新使用者能從公開頁面驗證來源與 hash、完成安裝和主要流程，而且不會把實驗評級誤認為保證或正式投資建議。

### 建議版本路線

| 建議里程碑 | 開發主題 | 驗收成果 |
|---|---|---|
| `0.2.x` | 穩定目前公開測試基準 | 修回歸、補 Axe／閱讀器證據，不增加大功能 |
| `0.3.0` | Point-in-time 資料底座 | 可重現官方歷史資料集、版本記錄與資料品質報告 |
| `0.4.0` | 正式模型驗證 | 成長／安全各自通過門檻，或誠實維持實驗狀態 |
| `0.5.0` | 資產專用分析 | ETF 優先、金融次之，其他資產依資料可行性決定 |
| `1.0.0` | 可公開正式發佈 | 無障礙驗收、數位簽章、遠端 repository 與正式 Release |

## 14. 變更時的回歸規則

| 修改區域 | 最少要重跑 |
|---|---|
| 資料來源／parser | 對應單元測試、失敗備援、來源與日期顯示、stale 行為 |
| 模型／評級 | 時間切分回測、gate、模型卡、正式與實驗標籤、資產適用邊界 |
| `webui.py` | task lifecycle、取消、期限、SSE、單工、shutdown、loopback |
| UI／CSS | 300/627/1187px、鍵盤、焦點、console、來源區塊、44px 目標 |
| PDF | 按需產生、頁面與中文字型、下載、3 天 TTL、不支援資產限制 |
| storage／config | dev/release 路徑、容量與 TTL、清理不誤刪、唯讀 bundle |
| packaging | portable 新目錄、installer、單例、正常關閉、解除安裝、hash |
| 相依套件 | `pip check`、`pip-audit`、完整 pytest、license notices |

## 15. 文件的真實性順序

遇到文件互相矛盾時，依序確認：

1. 現在實際程式碼、測試與真正打包產物。
2. `PROJECT_AUDIT_REPORT.md` 的逐項證據與最後狀態。
3. `PROGRESS.md` 的高階進度。
4. `README.md` 的使用者說明。
5. 本交接文件的整理摘要。

不要因為文件寫「完成」就跳過實測；也不要因為最初 audit 寫「有問題」就忽略後面已記錄的修正與回歸證據。

## 16. 接手者第一個小時建議

1. 閱讀本檔、`README.md`、`PROGRESS.md`，再讀 `PROJECT_AUDIT_REPORT.md` 的結論與未完成項目。
2. 執行 `git status` 與 `git log -1`，確認基準 commit。
3. 建立 Python 3.12 環境並安裝 `requirements-dev.txt`。
4. 執行完整 gate，記錄任何與本文件不同的結果。
5. 執行 `python webui.py`，用 2330 跑搜尋、分析、取消、PDF 與正常關閉。
6. 選定一個 P1 工作，先補測試或研究證據，再做最小變更。
7. 每次交付同步更新 `PROJECT_AUDIT_REPORT.md`、`PROGRESS.md`、必要的模型卡與本交接文件。

## 17. 最後提醒

這個版本最有價值的不是「看起來什麼都能評分」，而是已經把不可信、不適用和未通過驗證的內容明確擋住。後續開發應優先提升資料與模型證據，不能用拿掉 gate、合併兩個評級或補上漂亮數字的方式假裝完成。
