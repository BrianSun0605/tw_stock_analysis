# 專案進度

更新日期：2026-07-19

## 已完成

- [x] Phase 0：主檔搜尋、同業、日期欄位、按需 PDF、單工與檔案隔離。
- [x] Phase 1：官方月營收／財報、逐欄來源、Yahoo 備援、共享行情快照、SQLite cache、三天 PDF、取消與資源上限。
- [x] Phase 2 可安全上線的部分：成長／安全契約完全分開，不平均；ETF、金融適用邊界已實作；歷史未過門檻時正式 A～F 保持空白。
- [x] Phase 3 可由程式確認的部分：事實／模型分區、新聞分區、對比、combobox、焦點、44px 觸控目標、UI 規範、Noto OFL、第三方與隱私文件、固定版本與 CI。
- [x] Phase 4 portable 與 installer：LocalAppData、唯讀 bundle、單一實例、loopback、按需 PDF、版本、ZIP、Setup EXE 與 SHA-256。
- [x] 官方主檔擴充：schema 4 共 2,773 筆，已納入興櫃、ETF、ETN、特別股與 REIT；權證排除，英數代碼可直接輸入。
- [x] 完整檢查：106 項 pytest、Ruff、pip check、pip-audit、6 個 JavaScript 語法檢查通過；最終 EXE 啟動、2,773 筆內建主檔、ETN 搜尋、資源、單例與正常關閉通過。
- [x] Inno Setup 6.7.3 安裝版完成：實際安裝、啟動、重複啟動、正常關閉與解除安裝均通過；解除安裝保留使用者資料。
- [x] Browser 真實驗收完成：鍵盤搜尋、完整分析、300px 手機、627px 平板、1187px 桌面、PDF 13/13、結果焦點與 console 均通過。
- [x] 修正手機整頁水平捲軸與關閉後背景 EXE 殘留；兩者都有回歸測試，最終打包 App 已重跑確認。

## 尚未完成／不能假裝完成

- [ ] 成長資料仍不是逐公告版本的 point-in-time；正式成長評級未通過預定 MAE 門檻。
- [ ] 一般公司財務安全缺歷史危機結果標籤；目前只顯示實驗篩檢，不是破產機率。
- [ ] ETF 成分股加權成長模型與金融／保險專用監理模型待建立。
- [ ] ETN、REIT、特別股已可搜尋，但專用分析模型尚未完成；目前明確停止，不誤套普通股公式。
- [ ] Axe 與實體螢幕閱讀器仍未執行；Browser 內的基本 DOM 無障礙檢查已通過，但不把它當成 Axe 或真人輔具驗收。
- [ ] Setup EXE 與主程式目前沒有 Windows 數位簽章；公開散布時可能出現 SmartScreen 警告。
- [ ] 解除安裝會刪除全部程式內容，但目前留下空的安裝資料夾；不影響程式或使用者資料，列為低優先清理問題。
- [x] 正式開源授權：MIT License，Copyright (c) 2026 胖貓貓工作室；原始碼、portable 與 installer 均納入 LICENSE。
- [x] CI 已加入 pip-audit；目前 runtime 相依套件沒有查到已知漏洞。
- [x] Ruff 已格式化 39 個既有 Python 檔；66 個 Python 檔通過 `ruff format --check`，CI 已加入格式 gate。

## 主要成果位置

- 使用與架構：[README.md](README.md)
- 完整證據與 checklist：[PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md)
- Windows portable：[release/TWStockAnalysis-portable-0.2.0-dev.zip](release/TWStockAnalysis-portable-0.2.0-dev.zip)
- Windows 安裝版：[release/TWStockAnalysis-Setup-0.2.0-dev.exe](release/TWStockAnalysis-Setup-0.2.0-dev.exe)
- 開源授權：[LICENSE](LICENSE)
- 校驗碼：[release/SHA256SUMS.txt](release/SHA256SUMS.txt)
