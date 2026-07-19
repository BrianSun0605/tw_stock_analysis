# 第三方套件、字型與資料來源

本檔記錄會隨原始碼或 Windows App 散布的第三方內容。完整授權文字仍以各套件內附檔案與上游專案為準。

## 字型

### Noto Sans TC

- 用途：PDF、圖表與繁體中文顯示。
- 上游：notofonts/noto-cjk，Noto Sans CJK Traditional Chinese。
- 授權：SIL Open Font License 1.1。
- 專案內授權副本：assets/licenses/NotoSansCJK-OFL.txt。
- 字型檔：fonts/NotoSansTC-Regular.otf、fonts/NotoSansTC-Bold.otf。
- 版本：2.004。
- SHA-256（Regular）：5BAB0CB3C1CF89DDE07C4A95A4054B195AFBCFE784D69D75C340780712237537。
- SHA-256（Bold）：55420B259EB119BF5F2A0AADBA10CF9D736C12D64AB93E78546D69EF5F43558B。

字型可與軟體一起散布，但不能把字型單獨販售；若修改字型，仍需遵守 OFL 與保留名稱條款。

## Python 執行期套件

| 套件 | 固定版本 | 主要授權 |
|---|---:|---|
| yfinance | 1.5.1 | Apache |
| NumPy | 2.4.6 | BSD-3-Clause 與內含元件授權 |
| pandas | 3.0.3 | BSD-3-Clause |
| Matplotlib | 3.10.9 | Matplotlib License 與內含元件授權 |
| fpdf2 | 2.8.7 | LGPL-3.0-only |
| Requests | 2.33.1 | Apache-2.0 |
| Beautiful Soup | 4.15.0 | MIT |
| lxml | 6.1.1 | BSD-3-Clause |
| Flask | 3.1.3 | BSD-3-Clause |
| Waitress | 3.0.2 | ZPL-2.1 |

正式 installer 應保留 PyInstaller 收集到的套件 license／metadata。依賴升級時必須同步更新本表。

## 資料來源

- TWSE OpenAPI、TPEx OpenAPI、公開資訊觀測站：官方公開資料來源；App 儲存必要快照與 cache，畫面逐欄標示來源與日期。
- Yahoo Finance／yfinance：只作行情、部分財務與 ETF 資訊備援。上游說明 Yahoo 資料偏向個人研究使用；本專案不重新散布完整 Yahoo 資料集，商業化前必須重新確認條款。
- Google News／Bing RSS：只整理公開索引的標題、摘要、來源與連結，不保存或重新發布全文。

官方資料公開可讀不等於保證正確或不中斷；App 會驗證欄位、保留最後有效資料並標示 stale／fallback。

## 圖示

picture/icon/app-icon.svg 是本專案自行建立的幾何圖示，不含第三方照片或商標素材。

## 專案本身的開源授權

本專案採 MIT License，Copyright (c) 2026 胖貓貓工作室。完整條款見專案根目錄 LICENSE。
