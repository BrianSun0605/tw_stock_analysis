# 專案進度

更新日期：2026-07-18

## 已完成

- [x] 建立 Git baseline 與 `.gitignore`。
- [x] CLI／Web 共用 `services/analysis.py`。
- [x] 官方 TWSE／TPEx 1,981 筆股票快照與更新器。
- [x] 修正 TTM、EPS growth、PE look-ahead、coverage、Piotroski、Altman、Graham 與綜合評級缺值行為。
- [x] 預設停用 HiStock HTML；季度 EPS 改用 yfinance 正式季度損益表。
- [x] 修正股利年度口徑、時區、同業殖利率與 cache 原子性。
- [x] 新聞改為 Google／Bing RSS，停用失效 scraper，回傳來源狀態。
- [x] Web shutdown、task、SSE、download、CSP 與 security headers 強化。
- [x] 修正真實資料 `NaN` 造成瀏覽器無法解析結果；預覽先行、PDF 逐章進度、事件重播與重新整理恢復。
- [x] 專業投資工具 UI；HTML／CSS／JS 模組化與響應式 QA。
- [x] PDF 來源、單位、長文字、游標崩潰與免責聲明修正；11 頁轉圖 QA。
- [x] 38 項測試、compile、Node syntax、pip check、2330／0050 live smoke。
- [x] 完整稽核報告與決策 checklist。

## 待專案負責人決定

請直接處理 [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md) 第 10 節 Q01–Q12。授權、部署範圍、評級 target 與模型適用性未確認前，不進入商業／公開發布階段。

## Canonical 文件

- 使用與架構：`README.md`
- 完整問題、修正、風險與 checklist：`PROJECT_AUDIT_REPORT.md`
- 本檔：只記錄高階進度，不重複技術細節
