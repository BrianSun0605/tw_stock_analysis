# 台股研究室

這是一套在自己電腦上執行的台股研究工具。它會整理官方公開資料、Yahoo 備援資料、估值情境、財務風險訊號與新聞索引，也能讓使用者自行下載 PDF。

它不是交易系統，也不保證股票會上漲。成長、財務安全與股價是否便宜是三件不同的事，畫面不會把它們平均成一個看似精準的總分。

## 現在能做什麼

- 搜尋隨專案保存的 2,773 筆官方證券快照，涵蓋上市、上櫃、興櫃，以及股票、TDR、ETF、ETN、特別股與 REIT；權證與債券不納入。
- 優先讀取 TWSE、TPEx 與公開資訊觀測站資料；缺資料時才使用 Yahoo，並在畫面標出來源、日期、備援與 stale 狀態。
- 把「已確認資料」和「模型推估」分開顯示。
- 顯示估值區間、財務健康度、Piotroski／Altman 適用性、股利、同業、行事曆與新聞索引。
- 分析完成後先顯示網頁結果；只有按下按鈕時才產生 PDF。
- Windows release 只監聽本機 `127.0.0.1`，同一時間只允許一個執行個體。

## 兩種評級目前代表什麼

### 成長評級

目標是估計公司未來連續 12 個月營收成長，不是預測股價。模型會顯示實驗分級、成長百分比、80% 估計區間與正成長可能性。

目前模型沒有比事先指定的最佳 MAE 基準好 5%，歷史封存資料也不是真正逐日保留的 point-in-time 版本。因此正式 A～F 維持空白，只顯示「實驗分級」。EPS 次要目標尚未完成歷史驗證，不產生預測數字。

### 財務安全評級

一般公司目前使用負債、流動性、保留盈餘與獲利能力做實驗篩檢。這不是破產機率，也還沒有台灣公司財務危機標籤的樣本外驗證，因此正式 A～F 同樣維持空白，只顯示實驗分級與篩檢分數。

- 金融、金控、銀行、保險：不套一般公司公式，顯示「專用模型待建立」。
- ETF：不套公司營收／EPS 模型；只顯示 ETF 結構安全的實驗篩檢。
- ETN、REIT、特別股：已納入官方搜尋主檔，但專用分析模型尚未完成；目前不套普通股公式，也不產生評級或 PDF。
- 成長與安全永遠分開，`combined_rating` 固定為空。

模型與限制位置：

- `models/growth_model.py`
- `models/safety_model.py`
- `research/model_cards/`
- `research/backtest/`

## 安裝與執行原始碼

需求：Python 3.12。專案目前以 Python 3.12 驗證。

```powershell
python -m pip install -r requirements.txt
python webui.py
```

預設網址是 `http://127.0.0.1:5000`。也可指定其他連接埠：

```powershell
python webui.py 5050
```

命令列模式：

```powershell
python main.py 2330
```

## 網頁使用流程

1. 搜尋股票代號或名稱並開始分析。
2. 五個分析階段完成後，網頁立即顯示結果。
3. 需要 PDF 時再按「產生 PDF」；完成後可下載。
4. 分析中可以取消。重新整理頁面後，尚未過期的任務狀態可以恢復。
5. 同一時間只執行一個分析或 PDF 工作，單次工作上限 180 秒。

## 資料來源與限制

| 資料 | 優先來源 | 備援或限制 |
|---|---|---|
| 證券清單 | TWSE OpenAPI、TPEx OpenAPI、TWSE ETN 官方商品清單 | 使用版本化官方快照；更新失敗不會覆蓋最後有效版本 |
| 月營收、財報 | 公開資訊觀測站 | 官方資料缺漏時才使用可用備援，並逐欄標示 |
| 行情、部分財務、ETF | Yahoo Finance／yfinance | Yahoo 為備援；上游偏向個人研究使用，商業化前要重新確認條款 |
| 新聞 | Google／Bing RSS 索引 | 只整理標題、摘要、來源與連結，不保存全文 |

更新證券快照：

```powershell
python scripts\update_stock_snapshot.py
```

主要來源程式位置：

- `stock/official_stock_snapshot.json`
- `stock/official_financials.py`
- `stock/mops_history.py`
- `services/market_snapshot.py`

## PDF、cache 與本機資料

release App 將可寫資料放在：

```text
%LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\
├─ cache\
├─ logs\
└─ output\
```

- PDF：保留 3 天；output 超過 250 MiB 時先刪最舊檔。
- 一次性工作圖表：保留 24 小時。
- cache：超過 200 MiB 時清到 160 MiB；官方最後有效資料可以離線使用，但會標示 stale。
- log：保留 14 天且總量上限 20 MiB。
- 清理每 6 小時最多執行一次。

這比固定「每幾天全部清空」更合適：常用資料可以保留，不常用與過期檔案會依時間和容量逐筆清除。規則位置是 `config.py` 與 `storage/cleanup.py`。

## 開發檢查與 Windows 打包

開發與打包需 Python 3.12、Node.js 20 以上；產生 Setup EXE 另需 Inno Setup。

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pip_audit -r requirements.txt --progress-spinner off
python -m ruff check .
python -m ruff format --check .
python -m pytest -q -p no:cacheprovider
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Installer
```

打包結果：

- 可攜版：`release/TWStockAnalysis-portable-<版本>.zip`
- 安裝版：`release/TWStockAnalysis-Setup-<版本>.exe`
- 校驗碼：`release/SHA256SUMS.txt`
- installer 設定：`packaging/installer.iss`；使用 `-Installer` 時會從 PATH 或常見安裝位置尋找 Inno Setup。
- 目前開發版 EXE 尚未做 Windows 數位簽章，公開下載時可能出現 SmartScreen 警告。

## 重要檔案位置

```text
webui.py                    本機 Web 服務與工作生命週期
services/analysis.py        CLI／Web 共用分析流程
models/                     成長與安全模型
stock/                      官方資料、行情、股利、同業、行事曆
valuation/analyzer.py       估值與既有研究型指標
templates/index.html        頁面結構
static/css/app.css          UI 視覺規範實作
static/js/                  API、呈現、取消與 CSV 匯出
report/                     PDF 產生器
storage/                    SQLite 與自動清理
tests/                      自動測試
docs/UI_DESIGN_SYSTEM.md    字型、色彩、間距、狀態與元件規範
docs/PRIVACY.md             本機資料與外部連線說明
THIRD_PARTY_NOTICES.md      套件、字型、圖示與資料來源
LICENSE                     MIT 開源授權與著作權人
PROJECT_AUDIT_REPORT.md     問題證據、修正狀態與剩餘 checklist
```

## 安全與公開散布狀態

- 服務只綁 `127.0.0.1`，不是可直接公開到 Internet 的網站。
- 關閉端點需要隨機 token、loopback、Host 與同源檢查。
- CSP 禁止 inline script／style；動態 API 不進入 Service Worker 快取。
- 外部文字使用安全 DOM API；CSV 會中和試算表公式前綴。
- Noto Sans TC 的 OFL 授權副本位於 `assets/licenses/`；第三方資訊見 `THIRD_PARTY_NOTICES.md`。
- 專案採 MIT License，著作權人為「胖貓貓工作室」；完整條款見 `LICENSE`。

完整驗證結果與未完成原因請見 [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md)。
