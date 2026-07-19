# 隱私與網路連線說明

- App 只在本機 127.0.0.1 提供介面，不接受區域網路或 Internet 連入。
- App 不要求帳號，不收集姓名、Email、交易紀錄或投資組合。
- 查詢的股票代號會送到 TWSE、TPEx、公開資訊觀測站、Yahoo Finance 與新聞 RSS 等資料來源；這些來源可能依自己的政策記錄 IP、User-Agent 與請求。
- 分析 cache、SQLite、log 與 PDF 都留在本機。release build 使用每位 Windows 使用者的 LocalAppData；dev mode 使用專案目錄。
- PDF 預設逐檔保留三天，output 超過 250 MiB 時先刪最舊檔；cache 超過 200 MiB 時清到 160 MiB。
- App 不會把分析結果上傳到本專案作者的伺服器。

使用者可從 App 的 output 目錄刪除 PDF；解除安裝程式應提供保留或移除使用者資料的選項。
