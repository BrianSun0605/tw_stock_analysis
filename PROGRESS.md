# PROGRESS.md — tw_stock_analysis 修正進度

> 交接文件。上個 session 做到哪、下個 session 從哪接手。
> 完整 51 項發現清單與 8 階段計畫見對話壓縮記錄（b2）。

## 專案位置

`C:\active\胖貓貓的遊戲工作室\投資神器\tw_stock_analysis`

## 已變更檔案（本次 session 已完成）

### `stock/data.py`
- **Line 80-84** `get_price_data` 例外：`except Exception` → `except (requests.RequestException, ValueError, KeyError)` + `exc_info=True`。失敗 stub 3 個 results entry 全部補上 `"charts": {}` key。
- **Line 388-389** `get_basic_stock_info` market 覆寫：改為 `if not result.get("market") and info.get("market")` — 不再覆蓋傳入的「上市/上櫃」。

### `stock/dividend.py`（66 → 87 行，核心重寫）
- 加入 `import requests`、`from datetime import datetime, timedelta`、`from utils.cache import cache_get, cache_set`。
- `_DIV_CACHE_TTL = 43200`（12 小時）常數。
- 函式開頭查快取，hit 直接 return；成功路徑結尾 `cache_set`。
- **核心修正**：`consecutive_years` 改用日曆年逐年往回跑（`range(most_recent, most_recent - 11, -1)` + `yearly.get(y, 0)`），缺口年份能正確 break。掃描範圍 11 年。
- `avg_yield_3y` 改用 3 年價格視窗（`timedelta(days=365*3)`），方法論與 3 年股利視窗一致。
- 例外 tuple 精準化：`(KeyError, ValueError, AttributeError, IndexError, requests.RequestException)`。
- `_empty_result` 加上 `-> Dict[str, Any]` 型別註解。

## 階段一剩餘未完成（下個 session 接手起點）

### analyzer.py（valuation/analyzer.py）
- [ ] **:996-1001** Piotroski 紅燈分支修正：`elif f_score < 2`（或重排為 `if f_score < 2: 紅 elif f_score <= 3: 黃 else: 綠`）。
- [ ] **`_score_valuation`** clamp `[10,100]` → `[0,100]`（與其他 6 個 scorer 一致）。
- [ ] **`calculate_overall_rating`** Piotroski 雙重計分：`quality_raw` 改用 OCF/NI ratio 而非 F-score（health 的 `_score_quality` 已用 F-score）。
- [ ] **`_estimate_volatility`** 改用 `prices.pct_change().dropna()` 取代 `np.diff(np.log(prices[prices>0]))`（避免時間缺口 log return）。
- [ ] **ETF health** 最小資料門檻：`total_w < 0.5` → return None（避免小樣本誤判）。

### generator.py（report/generator.py）
- [ ] **:888** Glossary「健康度評分」更新為 7 維權重：成長 22% / 估值 20% / 獲利 18% / 品質 15% / 動能 12% / 穩定 8% / 現金流 5%。
- [ ] **`_add_eps_section`** 加 per-row `try/except (KeyError, ValueError)`，單一壞 row 不中斷整份 PDF。
- [ ] **`_add_valuation_section`** 吞式 try/except 拆細：把 `try/except (KeyError, AttributeError)` 範圍縮小到各子區塊（fair/peg/quality/health/risk 各自 try）。
- [ ] **risk warnings** 超 6 項時加 footer 文字「另有 N 項風險未列出」。
- [ ] **市值/AUM 單位統一**：格式器擇一（建議都用 億/百億）。

### font.py（report/font.py）
- [ ] 加 Windows 原生路徑：`C:\Windows\Fonts\msjh.ttc`、`C:\Windows\Fonts\msyh.ttc`、`%WINDIR%\Fonts\...`。
- [ ] 移除 `import shutil`（dead import）。
- [ ] 字型註冊失敗時 raise 明確錯誤（或至少讓 caller 可偵測），而非靜默 fallback 到 Courier（無法 render CJK）。

### normalizer.py（stock/normalizer.py）
- [ ] **STOCK_DB** 修正 3 筆：
  - `2633 台灣高鐵` industry `"航運"` → `"運輸"` 或 `"軌道運輸"`。
  - `9930 中聯資源`：與 `9928` 重複，確認正確 ID 後刪除其一。
  - `9945 潤泰新`：與 `9942` 重複，確認正確 ID 後刪除其一。

### news/base_provider.py
- [ ] **`_normalize_date`** 加入 RFC-822 格式：`%a, %d %b %Y %H:%M:%S GMT`（RSS `<pubDate>`）+ ISO 8601 `%Y-%m-%dT%H:%M:%S%z`（含時區）。
  - 注意：`%b` 是 locale月份縮寫，中文 locale 下可能抓不到英文月份，需顯式locale或用 `email.utils.parsedate_to_datetime` 作為更穩健的 fallback。

### news/providers/google_news.py
- [ ] **BingNewsProvider** 先用 curl/requests 實測 `https://www.bing.com/news/search?q=...&format=rss`，確認回 RSS `<item>` 还是 Atom `<entry>`，再決定修（改 iter("item") + 移除 ns dict）或刪。
- [ ] **GoogleNewsProvider** 移除 Googlebot UA 覆寫（`Mozilla/5.0 (compatible; Googlebot/2.1; ...)`），改用 config.HEADERS 即可。

### news/providers/{moneydj,anue,udn}.py
- [ ] 各加 `resp.raise_for_status()`（目前 HTTP 錯誤靜默為 []）。
- [ ] 補日期 selector：需先 curl/requests 抓各站 HTML 探查日期元素位置。
  - MoneyDJ：`newslist.aspx` 頁面日期元素待查。
  - Anue：`/news/id/` 列表日期待查。
  - UDN：`/rank/stock/{id}` endpoint 疑似錯誤，先實測確認正確的 per-stock news endpoint。
- [ ] 移除 dead `import re`（三檔都有）。

### 隨行 regression test
- [ ] 建立 pytest 框架（`tests/` 目錄、`pytest.ini` 或 pyproject.toml、requirements.txt 加 pytest + pytest-mock）。
- [ ] `tests/test_dividend.py`：consecutive_years 修正的 regression test（用 mock yfinance Ticker 回歷史股利，驗證缺口年份正確 break）。
- [ ] 其他已修正項目的 regression test。

## 階段二～八（全部未開始）

- **階段二**：反爬蟲/效能 — Session 共用、keywords 上限、sleep+backoff、priority 短路反轉、ThreadPoolExecutor 並發 3-5、各 TTL、`@cached_property`、atomic 寫入、stock_id sanitize、matplotlib use 移入函式。
- **階段三**：安全性 — escHtml 5 處、CSV RFC-4180、/shutdown 限 127.0.0.1+token、SSE Cache-Control、rmtree 白名檢查、isinstance guard、tasks Lock、orphan 掃描、graceful shutdown 替換 os._exit。
- **階段四**：PWA — activate + cache 清理 + skipWaiting + clients.claim、離線 fallback、runtime cache。
- **階段五**：可觀測性 — 裸 except 改 warning + 縮窄、provider_errors list、logger timestamp。
- **階段六**：重構 — _suffix 抽取、BaseScrapingProvider、移除 dead imports/code、Type hint 統一 Optional、ValuationAnalyzer 拆解、PDFReport 拆解、Rating 顏色表抽 colors.py、FONT_NAME 動態設。
- **階段七**：STOCK_DB 活化 — 啟動抓 TWSE/TPEx openapi，失敗 fallback，結果寫 stock_mapping.json。
- **階段八**：補核心模組測試 — dividend/analyzer/generator/normalizer/base_provider/webui 各 5-10 case。

## 使用者已裁決的 6 項決策

1. **BingNewsProvider** — 先實測再決定（修復或刪除）。
2. **HTML 來源日期擷取** — 探查並補上各站 selector。
3. **STOCK_DB** — 活化 openapi + 保留 STOCK_DB 為 fallback。
4. **god-class 拆解** — 本次做（階段六）。
5. **測試** — pytest + 補核心模組測試（各 5-10 個 case）。
6. **Type hint** — 統一 `Optional[...]`（相容 3.8+）。

## 環境與工具備忘

- OS: win32，Shell: pwsh（PowerShell 7+）。
- 編輯工具：`edit` / `write` 均可執行。
- 已驗證：無 pytest / pyproject.toml / setup.cfg / tests/ / .github/。
- cache/ 內已有 20 檔 eps/revenue JSON + 70+ chart PNG（既有產物，勿刪）。
- fonts/ 含 msjh.ttc / msjhbd.ttc / STKAITI.TTF（既有字型，勿刪）。
- picture/ 多張 JPG/GIF/PNG（既有資源，勿刪）。
- `stock/data._suffix` 是 private symbol，dividend.py 已 import 它（既有耦合，階段六統一抽取時再處理）。
