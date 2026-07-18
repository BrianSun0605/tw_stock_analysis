# 台股研究室

本專案是一套在本機執行的台股研究輔助工具，可從命令列或 Web UI 產生估值、財務健康度、風險提示與 PDF 報告。它不是交易系統，也不提供買賣建議。

目前定位：**個人研究／教學用途的本機工具**。尚未完成商業資料授權、模型績效回測與公開網路部署安全設計。

## 功能

- 上市、上櫃股票代號與名稱搜尋
- 股價、財務與季度 EPS 整理
- 歷史本益比分位估值、PEG、Graham Number
- 七維度健康度與資料覆蓋率
- Piotroski、Altman 模型的可用性檢查
- 股利、同業、行事曆與公開新聞索引
- 專業桌機／平板／手機 Web UI
- 繁體中文 PDF 報告

## 安裝與執行

需求：Python 3.10 以上。專案目前以 Python 3.12 驗證。

```powershell
python -m pip install -r requirements.txt
python webui.py
```

Web UI 預設只監聽 `127.0.0.1:5000`，啟動後會開啟本機瀏覽器。也可指定連接埠：

```powershell
python webui.py 5050
```

命令列模式：

```powershell
python main.py 2330
python main.py
```

開發檢查：

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q -p no:cacheprovider
python -m pip check
```

## 資料來源與限制

| 資料 | 目前來源 | 重要限制 |
|---|---|---|
| 上市公司清單 | [TWSE OpenAPI](https://openapi.twse.com.tw/) | 以版本化快照隨專案提供，不會在一般搜尋時阻塞式更新 |
| 上櫃公司清單 | [TPEx OpenAPI](https://www.tpex.org.tw/openapi/) | 同上 |
| 行情、財務、ETF、股利 | [yfinance](https://ranaroussi.github.io/yfinance/) | yfinance 說明其資料供研究／教育且 Yahoo Finance API 為個人使用；商業用途需另行確認 |
| 季度 EPS | `Ticker.quarterly_income_stmt` | 欄位可能缺漏；只從同季度 EPS 或淨利／股數計算，不把 TTM EPS 當單季 EPS |
| 月營收 | 預設不提供 | 不會把年度營收拆成月份；HiStock HTML 爬取因條款與穩定性風險預設停用 |
| 新聞 | Google／Bing RSS 索引 | 僅整理標題、摘要、來源與連結；關鍵字情緒不是模型預測 |

若已自行取得 HiStock 使用授權，可明確設定 `TWSTOCK_ALLOW_HISTOCK=1` 啟用既有轉接器。設定環境變數不代表已取得授權，使用者仍須自行確認條款。

更新官方股票快照：

```powershell
python scripts\update_stock_snapshot.py
```

更新器會同時取得 TWSE 與 TPEx，筆數未達完整性門檻時拒絕覆寫。

## 評分口徑

### 個股健康度

| 維度 | 權重 |
|---|---:|
| 成長性 | 22% |
| 估值 | 20% |
| 獲利能力 | 18% |
| 品質力 | 15% |
| 動能 | 12% |
| 穩定性 | 8% |
| 現金流 | 5% |

- 可用權重低於 50% 時，不顯示健康度總分。
- 缺漏維度標示為「資料不足」，不會補零。
- 綜合評級另使用健康度 40%、完整 Piotroski 品質 20%、安全邊際 25%、Graham 15%；缺漏模型會排除並重新正規化，總覆蓋率低於 50% 時回傳 `N/A`。
- 所有權重與門檻目前都是研究型啟發式規則，**尚未經投資績效回測校準**。

### 模型適用性

- 歷史 PE 需要至少 60 個可用交易日，TTM EPS 必須由四個連續季度組成。
- 歷史估值依保守財報可得日期避免前視偏誤，但日期仍是統一假設，不是逐公司實際公告時間。
- Piotroski 只有九項訊號完整時才給總分。
- Altman 使用原始上市製造業模型與 1.81／2.99 門檻；金融業與 ETF 不計算，其他產業是否適用仍需使用者決定。

## 專案結構

```text
main.py                     CLI 入口
webui.py                    Flask／Waitress 本機服務
services/analysis.py        CLI 與 Web 共用分析流程
stock/                      行情、代碼、股利、同業、行事曆
valuation/analyzer.py       估值、評分與風險規則
news/                       RSS 新聞聚合與停用轉接器
report/                     PDF 產生器與字型選擇
templates/index.html        語意化頁面骨架
static/css/                 視覺系統
static/js/                  API、DOM、安全呈現與 CSV 匯出
tests/                      回歸、安全、資料與 PDF 測試
scripts/                    官方快照維護工具
PROJECT_AUDIT_REPORT.md     完整稽核、修正紀錄與決策清單
```

`cache/`、`output/`、`tmp/`、Python bytecode 與測試暫存皆由 Git 忽略。既有 `output/*.pdf` 可能是舊版產物，需重新產生才會套用目前修正。

## 安全邊界

- Web 服務只綁定 loopback，關閉端點要求隨機 token、loopback、Host 與同源檢查。
- 外部新聞與本機儲存文字一律用 `textContent` 類型的安全 DOM API 呈現。
- CSP 禁止 inline script/style；動態 API 不進入 Service Worker 快取。
- CSV 依 RFC 4180 加引號，並中和 `= + - @` 公式前綴。
- **不可直接把目前 Flask app 對外公開。** 公開部署需要認證、CSRF、速率限制、代理與正式威脅模型。

## 稽核狀態

完整內容、已修復問題、剩餘風險與待確認事項請見 [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md)。
