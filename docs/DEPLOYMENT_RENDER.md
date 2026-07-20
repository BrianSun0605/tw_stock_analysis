# GitHub + Render 公開部署

本文件說明如何將本專案部署成一個可直接開啟網址使用的公開網站。部署架構是單一 Flask／Waitress Web Service；前端頁面、分析 API、SSE 進度、CSV 與 PDF 下載都由同一個 Render 服務提供，不需要另建 GitHub Pages 或額外 AI API。

## 已經完成的專案設定

- 根目錄的 `render.yaml` 已定義免費 Render Web Service、Singapore 區域、Python 3.12、健康檢查與自動部署。
- `TWSTOCK_APP_MODE=web` 時，服務讀取 Render 的 `PORT`，綁定 `0.0.0.0`，不開啟本機瀏覽器、不使用桌面版單一執行個體鎖。
- 公開模式不渲染關閉服務按鈕，也沒有 `/shutdown` 路由；桌面版原有的本機關閉流程不受影響。
- 快取、工作圖表、日誌與 PDF 會寫入 `/tmp/twstock-analysis`。這是暫存空間，不會寫入 GitHub 原始碼，也不會承諾永久保存。
- 公開展示版預設限制為每個來源每小時 6 次分析、每分鐘 60 次搜尋，同一時間全服務只執行一個分析或 PDF 工作。可在 Render 環境變數調整，但免費方案不建議提高。
- `/healthz` 回傳服務狀態與版本，供 Render 健康檢查使用。

## 部署前的必要決定

1. 在 `render.yaml` 將 `name: tw-stock-research-demo` 改成尚未被使用的英數小寫與連字號名稱，例如 `yourname-tw-stock-research`。這會影響預設的 `https://<名稱>.onrender.com` 網址。
2. 決定 GitHub repository 是否公開。競賽展示通常選公開；若題庫或程式碼尚未要公開，可先建 private repository，但 Render GitHub App 必須能讀取它。
3. 免費方案適合展示與評審，不適合承諾長時間、高併發或永久保存。免費服務閒置後可能休眠，首次開啟會有冷啟動等待；PDF 請在產生後立即下載。

## 第一次上傳到 GitHub

此工作區已經有 `.git`，但目前未設定 remote，且本機沒有可用的 Git 指令。因此以下兩個做法任選其一。

### 做法 A：GitHub Desktop（較適合圖形介面）

1. 安裝並登入 [GitHub Desktop](https://desktop.github.com/)。
2. 選擇 **File → Add local repository**，選取本專案根目錄。
3. 建立第一個 commit，訊息可填 `Prepare Render web deployment`。
4. 按 **Publish repository**，指定 repository 名稱與公開／私人可見性。
5. 確認 `render.yaml`、`.python-version`、`docs/DEPLOYMENT_RENDER.md` 和原始碼都有被提交；`cache/`、`output/`、`.venv/`、`dist/`、`release/` 不應上傳。

### 做法 B：安裝 Git 後使用 PowerShell

先在 GitHub 網站建立空白 repository；不要勾選自動新增 README、`.gitignore` 或 License。接著在專案根目錄執行：

```powershell
winget install --id Git.Git -e
git config --global user.name "你的 GitHub 名稱"
git config --global user.email "你的 GitHub 信箱"
git add .
git commit -m "Prepare Render web deployment"
git branch -M main
git remote add origin https://github.com/<帳號>/<repository>.git
git push -u origin main
```

第一次 `git push` 會要求你在瀏覽器登入 GitHub 或設定 Personal Access Token。不要把 token 放進程式碼、`render.yaml`、README 或 commit。

## 在 Render 建立服務

1. 到 [Render Dashboard](https://dashboard.render.com/) 以 GitHub 帳號登入，授權 Render 存取剛建立的 repository。
2. 選擇 **New → Blueprint**，選取 repository 與 `main` 分支。Render 會讀取根目錄 `render.yaml`。
3. 確認服務類型為 **Web Service**、方案為 **Free**、區域為 **Singapore**，並確認服務名稱是你在 `render.yaml` 設定的唯一名稱。
4. 建立 Blueprint。Render 會執行 `python -m pip install -r requirements.txt`，再以 `python webui.py` 啟動。
5. 等待部署日誌出現服務已啟動，且健康檢查 `/healthz` 成功。Render 隨後會提供 `https://<服務名稱>.onrender.com`。
6. 開啟網址，依序測試搜尋、一次分析、繁中／英文切換、PDF 產生與下載。部署後也可直接開啟 `https://<服務名稱>.onrender.com/healthz`，應看到 `status: ok`。

`autoDeployTrigger: checksPass` 已啟用：之後推送到 `main` 時，GitHub Actions 的檢查通過後 Render 才自動更新。若你不想等待 CI，可在 Render 控制台改為 commit 觸發；不建議在未驗證時使用。

## 使用上的限制與維運

- Render 免費 Web Service 為展示用途。服務可能因閒置而休眠，檔案系統也是暫時的；重新部署、重新啟動或空間清理後，舊任務、快取與 PDF 都可能消失。
- 學習小教室的答題紀錄與星號題目存於使用者自己的瀏覽器 `localStorage`，不是伺服器資料庫；清除瀏覽器網站資料會一併清除。
- 公開網站沒有帳號系統。工作 ID 是高熵亂數、服務限制一次只跑一項重工作且有來源頻率限制，但這不是多使用者企業級隔離。若要長期公開，下一階段應加入登入、共享速率限制／WAF、監控與持久化物件儲存。
- 資料仍依賴 TWSE、TPEx、MOPS、Yahoo 備援與 RSS 的可用性及條款。公開展示前應保留研究／教育用途與投資免責聲明。
- Render 不需要任何 AI API 金鑰；本專案所有分析、題庫和報表仍在服務端獨立執行。

## 調整公開展示額度

在 Render 的 **Environment** 設定可調整下列非機密環境變數，修改後重新部署：

| 變數 | 預設 | 用途 |
|---|---:|---|
| `TWSTOCK_ANALYSES_PER_HOUR` | 6 | 每個來源一小時可啟動的分析數，範圍 1–60 |
| `TWSTOCK_SEARCHES_PER_MINUTE` | 60 | 每個來源每分鐘的搜尋數，範圍 10–600 |
| `TWSTOCK_DATA_ROOT` | `/tmp/twstock-analysis` | 暫存資料根目錄；免費服務請維持暫存路徑 |

不要在免費服務把多個 Waitress worker 或多項重分析同時打開。現在的單一重工作策略是為了讓圖表、PDF、網路資料抓取和記憶體使用量維持可預期。

## 更新、回退與移除

- 更新：commit 並推送到 `main`；等 GitHub Actions 成功後，Render 會自動部署。
- 回退：在 Render 的 Deploys 頁面選擇先前成功版本並 Rollback，或在 GitHub 將已知良好的 commit 還原後推送。
- 暫停／移除：從 Render Dashboard 停用或刪除服務；這不會刪除 GitHub repository。若刪除 repository，Render 將無法進行後續自動部署。

官方參考文件：[Render Blueprint](https://render.com/docs/blueprint-spec)、[Render Web Services](https://render.com/docs/web-services)、[Render 免費方案](https://render.com/docs/free)、[GitHub 連接](https://render.com/docs/github)。
