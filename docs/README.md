# 展示網頁

《臺灣公民科技生態系與需求調查報告》的互動網頁版。純靜態 HTML／CSS／JS，
沒有任何建置步驟、沒有任何外部 CDN 或第三方請求——把這個資料夾整包複製到
任何地方都能直接開啟。

**正式上線網址：[report.claire-cheng.com](https://report.claire-cheng.com/)**
（GitHub Pages 讀 `main` 分支的 `/docs` 資料夾，`docs/CNAME` 綁定這個自訂網域）

## 這裡有什麼

```
docs/
├── index.html          全部內容都在這一頁（單頁應用）
├── css/style.css        版面、深色模式
├── js/charts.js          圖表渲染器（純 JS，沒有依賴任何函式庫）
├── js/app.js             章節導覽、閱讀進度、身分推薦
├── data/figures.json     圖表資料（給人看、給程式核對用）
├── data/figures.js       同一份資料，包成 window.FIGDATA（網頁實際載入這個）
└── .nojekyll             告訴 GitHub Pages 不要用 Jekyll 處理這個資料夾
```

## 資料從哪裡來、怎麼更新

網頁上每一張圖的數字，都是 `04_問卷分析報告/分析程式/13_web_data.py`
從 `分析結果/*.csv`（彙總層級、已公開的資料）算出來的，不是手key在網頁裡。

問卷樣本增加、報告數字更新之後，重新產生網頁資料：

```bash
cd 04_問卷分析報告/分析程式
python3 13_web_data.py          # 重新產生 docs/data/figures.json 與 figures.js
python3 14_web_number_check.py  # 核對網頁上每個百分比，對不上就會失敗
```

如果報告正文（`index.html` 裡手寫的段落）也跟著改了數字，一定要重跑
`14_web_number_check.py`——它會抓出「文字裡的百分比」與「分析結果 CSV」對不上的地方。

## 本機預覽

不需要任何安裝，直接用瀏覽器開 `docs/index.html` 就能看（雙擊開檔也可以，
因為圖表資料是用 `<script src="data/figures.js">` 載入，不是 `fetch()`，
不會被瀏覽器的本機檔案安全限制擋下）。

想要更接近正式環境，也可以起一個本機伺服器：

```bash
cd docs
python3 -m http.server 8000
# 瀏覽器開 http://localhost:8000
```

## 部署到 GitHub Pages

> ✅ 這幾步已經做過、網站已上線，下面留著當作之後要重弄（例如換一個 repo）時的參考。

這個 repo 是公開的（`github.com/Legendream/Taiwan-civic-tech-research`），
GitHub Pages 可以直接讀這個 `docs/` 資料夾當網站根目錄：

1. 到 repo 的 **Settings → Pages**
2. **Build and deployment → Source** 選 **Deploy from a branch**
3. **Branch** 選 `main`，資料夾選 **`/docs`**，按 **Save**
4. 等一兩分鐘，頁面會給你一個 `https://legendream.github.io/Taiwan-civic-tech-research/` 網址

這幾步要在 GitHub 網站上手動按，Claude 不會代按。

## 換成你自己的網域

> ✅ 已經設定完成：`report.claire-cheng.com` → `legendream.github.io`（Cloudflare DNS only）。
> 下面留著當參考，之後想換別的子網域可以照抄。

等 GitHub Pages 的網址確認可以正常開啟之後，再做這幾步換成你自己的網域：

1. 在你的網域 DNS 服務商那邊，加一筆 **CNAME** 紀錄：
   - 主機名稱：你想用的子網域（例如 `civictech` 或 `report`）
   - 值指向：`legendream.github.io`
   （如果要用裸網域、不要子網域，GitHub 的官方文件會要你改加 A 紀錄指到 GitHub 的幾個固定 IP，
   做法和子網域不同，需要另外查 GitHub Pages 官方文件當時的最新 IP 清單。）
2. 到 repo 的 **Settings → Pages → Custom domain**，填入你的網域，按 **Save**
   （GitHub 會自動在 `docs/` 底下建立一個 `CNAME` 檔案，內容就是你填的網域——
   這個檔案之後會留在 repo 裡，不要手動刪除，否則下次部署網域設定會被清空）
3. 等 DNS 生效（通常幾分鐘到數小時），並在同一頁勾選 **Enforce HTTPS**

這幾步都需要你自己的網域管理權限與 GitHub 的操作權限，Claude 無法代為執行，
只能陪你核對設定是否正確。

## 個資與授權

- 網頁只使用彙總層級的數字，不含任何逐人資料、開放題原文、組織或專案名稱。
- 授權與 `04_問卷分析報告/公民科技生態系分析報告_定稿.md` 相同：CC BY 4.0，
  署名 g0v.tw jothon 與 Claire Cheng。
