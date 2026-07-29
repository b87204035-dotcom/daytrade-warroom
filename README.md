# Daytrade War Room v1.0

台股與台指期盤後戰報網站。資料更新、提交與 GitHub Pages 部署整合在同一個 Workflow，避免「更新資料後 Pages 不重新部署」的問題。

## 第一次安裝

1. 將本 ZIP **解壓縮**。
2. 進入解壓縮後的資料夾，全選裡面的檔案與資料夾後上傳到 Repository 根目錄。
3. Repository 應直接看到 `index.html`、`app.js`、`styles.css`、`.github`、`scripts`、`data`，外面不可再多包一層資料夾。
4. GitHub → Settings → Pages → Source 選 **GitHub Actions**。
5. GitHub → Actions → **Build and Deploy War Room** → Run workflow。

## 自動時間

週一至週五台灣時間 15:20 自動執行。GitHub Actions 排程可能延遲數分鐘。

## 資料誠信

系統只顯示成功取得的資料。未取得的法人、維持率或均量資料會標示缺漏，不會用假數據補齊。

## 目錄檢查

`.github/workflows/warroom.yml` 必須位於 Repository 根目錄下的 `.github` 內。
