# 英文版

把網頁報告翻成英文，給國際讀者（第一個用途：2026 Freedom Film Festival 的 Civic Tech Showcase 延伸閱讀）。

| 網址 | 內容 |
|---|---|
| `report.claire-cheng.com/en/` | **精華版**：約 900 字、3 張圖，5 分鐘讀完；結尾一個按鈕前往完整版 |
| `report.claire-cheng.com/en/full/` | **完整版**：中文網頁全文的忠實翻譯，結構與中文版一模一樣 |

中文版右上角有「English」按鈕，連到精華版；英文兩頁都有「中文」按鈕連回中文版。

## 這裡有什麼

| 檔案 | 內容 |
|---|---|
| `精華版_初稿.md` | 精華版正文，每段附〔根據〕（出處：報告段落編號、g0v.tw 與揪松團官網） |
| `精華版.md` | 上線用：初稿拿掉〔根據〕、標好圖表位置與連結 |
| `完整版譯稿.md` | 完整版全部正文，段落編號與中文改稿包一一對應 |
| `術語表.md` | 中英術語（全部經 Claire 確認） |
| `圖表與介面譯名.csv` | 圖表標題、說明、選項的中英對照，由程式套用 |
| `完整版_第三章樣稿.md`、`精華版_樣稿.md` | 給 Claire 校準譯法用的樣稿（紀錄） |

## 怎麼重新產生

```bash
cd 04_問卷分析報告/分析程式
python3 13_web_data.py           # 同時產生 figures.json 與 figures_en.json（數字共用）
python3 20_build_english.py      # 產生 docs/en/、docs/en/full/、docs/js/i18n_en.js
python3 19_translation_check.py  # 逐段核對英文數字和中文版一致
python3 14_web_number_check.py   # 網頁數字稽核（含英文頁）
```

**中文網頁改了，英文版要跟著改**：先改 `完整版譯稿.md` 對應的段落，再重跑上面四步。
`19_translation_check.py` 會擋下數字對不上的段落。

## 寫法原則

- **完整版**：忠實翻譯中文定稿。意思不變；句子可以拆開或合併、刪掉贅字。不加新內容，下面列的脈絡說明除外
- **精華版**：同一批事實，為國際讀者重新寫。照 Claire 的四個原則：精簡、具體化、分類、由簡入繁
- 一律寫「g0v.tw」（Claire 指定，和中文版一致）
- 問卷是中文的，英文版的選項是翻譯，精華版的方法說明有註明

## 為國際讀者補充的脈絡（中文版沒有）

| 段落 | 補充 | 出處 |
|---|---|---|
| `intro-02`、精華版開頭 | g0v.tw 是「Taiwan's grassroots civic tech community」 | g0v.tw 英文介紹頁（g0v.tw/intl/en）：「a grassroots social movement community」「Founded in Taiwan」 |
| 精華版開頭 | 黑客松約 100 人、三分鐘提案找夥伴、每兩個月一次 | 揪松團官網 jothon.g0v.tw；g0v.tw 英文介紹頁 |
| `intro-04` | 中文「疫情期間」寫明 COVID-19；口罩地圖補「in Taiwan」 | 一般常識，未新增數字 |
| `intro-05`、`rec-1-3-05`、精華版 | 台灣公民科技資料庫用官方英文名稱「Civic Tech Taiwan」，並註明網站只有中文 | civictech.tw 頁首 |
| `top-06`、`about-03` | 註明 PDF、原始資料表是中文 | — |
| `ch1-1-09` | 雙北補「capital region」 | — |
| 全文 | 三群人用 Curious／Users／Builders 稱呼；第二群「most have used a civic tech tool or joined a discussion」 | 54 人中 51 人勾了「使用過某個公民科技工具、服務，或參與討論的人」（逐人明細重算） |

## 驗證

- `19_translation_check.py`：170 段數字逐段和中文版一致；31 處寫法差異（中文國字章節號、日期格式等）逐條登記說明
- 英文圖表資料 881 個數字和中文版完全相同（兩份共用同一次計算）
- `14_web_number_check.py`：英文完整版與精華版的百分比一併稽核
- `20_build_english.py`：英文頁畫面上不能殘留中文（人名、資料授權署名、零時政府除外）
