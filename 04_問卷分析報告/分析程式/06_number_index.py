# -*- coding: utf-8 -*-
"""
06_number_index.py — 產出數字索引，並「回頭驗證報告本文」。

這支腳本做三件事：

A. **自動稽核報告本文**：掃描報告裡每一個「NN%（分子/分母）」寫法，
   重算 分子÷分母 是否等於所寫的百分比。任何一處對不上就報錯。
   → 這是無法蒙混的檢查：報告中所有比例都必須自洽。
   稽核對象是 REPORTS 列出的每一份報告（目前只有對外發布的整合版）。
   列在 REPORTS 裡的檔案若不存在就直接報錯，避免改名後這道關卡默默失效。

B. **產出 99_數字索引.csv**：報告位置／數字／來源欄位／篩選條件／分子／分母／驗算式，
   讓 Claire 隨機抽查，不必碰程式。

C. **每個數字都要對得回一張來源表**：報告裡每一處「分子/分母」都必須在 B 的索引裡
   找得到對應列，找不到就報錯；裸寫的「N 人（P%）」也在索引的分母集合裡回推。

   ⚠️ C 擋得住的與擋不住的，要分清楚：
     · 擋得住：憑空出現的數字、改分析後已經過期的數字、複製到別章卻忘了改分母的數字。
     · **擋不住**：分子分母確實存在於某張表，但那張表回答的不是這句話要講的事。
       實例：報告曾寫「48%（61/126）從來沒參加過任何 g0v 活動」，61/126 算術正確、
       也真的存在於 03_全體_g0v活動類型.csv，但那是分支題「你參加過哪些 g0v 活動」
       的選項列（僅 126 人作答）；該講的是「最近一次參加是什麼時候」（127 人全答、
       60 人選沒參加過），正解 47%（60/127）。
       這一類只能靠人看，紀錄在 04_問卷分析報告/取數來源清查.md。

執行：python3 06_number_index.py
"""

import re
import sys

import pandas as pd

import common as C

# 要稽核的報告。整合版是唯一對外發布的定稿。
# 2026-08-01：好讀版分支已停用（改為只發布整合版），連同已被整合版取代的
# 舊版 公民科技生態系分析報告_v1.md 一併移出稽核清單，兩份檔案也已從 repo 刪除。
REPORTS = [
    C.OUT_DIR / "公民科技生態系分析報告_定稿.md",
]

# 索引裡的 § 編號是 v1 舊報告的章節。整合版重排成 1–11 章，讀者拿索引回頭
# 對照時要能對得上，所以把每個舊章節映到整合版的位置。沒有落在整合版正文的，
# 標「未引用於整合版正文」而不是硬塞一個章節。新增索引段落時要一併補這張表，
# 漏補會讓 build_index() 直接失敗。
_INTEGRATED_SECTION = {
    "§1.2 年齡": "第 1 章",
    "§1.2 性別": "第 1 章",
    "§1.2 身分": "第 1 章",
    "§1.2 居住地": "第 1 章",
    "§1.3 g0v 活動": "第 1 章",
    "§3 參與深度": "第 2 章",
    "§3 最深角色": "第 2 章",
    "§3 角色廣度（勾選數）": "第 2 章",
    "§3 專案階段（合併）": "第 2 章",
    "§3 決策位置": "第 3.2 節",
    "§3 同時進行專案數": "開頭四個發現之一",
    "§3 投入強度（過去30天）": "第 5.2 節",
    "§3 年齡": "第 4 章",
    "§4.1 困擾 %≥3": "第 3 章",
    "§4.1 困擾 %≥4": "第 3 章",
    "§4.2 困擾×決策位置": "第 3.2 節",
    "§5.1 初次動機": "第 4 章",
    "§5.1 持續動機": "第 4 章",
    "§5.1 留存／流失／新增": "第 4 章",
    "§5.2 年齡×持續動機 lift": "第 4 章",
    "§6.2 資源×階段": "未引用於整合版正文",
    "§6.3 資源×決策位置": "未引用於整合版正文",
    "§7 出資評估準則": "第 6 章",
    "§7 資源沙漠階段": "第 6.1 節",
    "§8.1 狩野（全體）": "第 8.1 節",
    "§8.2 議題領域": "第 8.2 節",
    "§8.2 跨領域工具": "第 8.2 節",
    "§9.1 g0v 消息管道": "第 7 章",
    "§9.1 資訊管道": "第 1 章",
    "§9.2 未參與原因": "第 7 章",
    "§9.4 活動意願": "第 7 章",
    "§9.4 活動意願×三層": "第 7 章",
    "§10 新舊對照": "未引用於整合版正文",
    # 以下為「取數來源清查」這一批補上的。這些數字報告一直有寫，但索引查不到，
    # 稽核只能重算算術、無法確認取自正確的題目與群體——61/126 那類錯誤就活在這個空隙裡。
    "§1.2 所屬組織": "第 1 章",
    "§1.2 地區連結": "第 1 章",
    "§1.3 g0v 參加經驗": "第 1 章",
    "§1.2 居住地（雙北合計）": "第 1 章",
    "§3 角色勾選": "第 2 章",
    "§3 動手做但沒用過": "第 2 章",
    "§4.2 困擾×參與深度5級": "第 3 章",
    "§5.1 動機組合是否改變": "第 4 章",
    "§6.1 資源（全體曾參與者）": "第 5 章",
    "§6.1 專長（全體曾參與者）": "第 5.1 節",
    "§9.1 管道：官方 vs 親友": "第 7 章",
}

# 「NN%（a/b）」：全形或半形括號、全形或半形斜線
PCT_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*%\*{0,2}\s*[（(]\s*(\d+)\s*[/／]\s*(\d+)\s*[)）]")
# 「lift 值（a/b）」：例如 2.09（4/10）
# 數值與括號之間可能夾 markdown 粗體記號（例如 **2.09**（4/10）），必須容許
LIFT_PAT = re.compile(r"(?<![\d%.])(\d+\.\d{2})\*{0,2}\s*[（(]\s*(\d+)\s*[/／]\s*(\d+)\s*[)）]")
# 「N 人中有 M 人（P%）」：小樣本改用這種讀得懂的寫法，一樣要被稽核，
# 否則換句話說就等於繞過這道關卡。分母在前、分子在後，與上面兩個 pattern 相反。
PEOPLE_PAT = re.compile(
    r"(\d+)\s*人中(?:有)?\s*(\d+)\s*人\s*[（(]\s*(\d+(?:\.\d+)?)\s*%\s*[)）]")
# 「N 人（P%）」：裸寫法，分母沒寫在句子裡（例如「有 7 人（15%）」）。
# 上面三個 pattern 完全掃不到這種寫法，改寫成這樣就等於繞過稽核，所以要單獨回推分母。
# 比對時先扣掉已被上面 pattern 涵蓋的位置，避免把「8 人中有 1 人（12%）」的後半段重複算。
BARE_PEOPLE_PAT = re.compile(r"(\d+)\s*人\s*[（(]\s*(\d+(?:\.\d+)?)\s*%\s*[)）]")


def audit_one(path):
    """掃描單一份報告，回傳（百分比稽核列, lift 列, 對不上的列）。"""
    text = path.read_text(encoding="utf-8")

    rows, bad = [], []
    for m in PCT_PAT.finditer(text):
        pct, num, den = float(m.group(1)), int(m.group(2)), int(m.group(3))
        calc = num / den * 100
        # 報告一律取整數百分比，容許 ±1 個百分點的四捨五入誤差
        ok = abs(calc - pct) <= 1.0
        line_no = text[:m.start()].count("\n") + 1
        rows.append({"報告": path.name, "行號": line_no, "原文": m.group(0), "宣稱%": pct,
                     "分子": num, "分母": den, "重算%": round(calc, 1),
                     "誤差": round(calc - pct, 2), "通過": ok})
        if not ok:
            bad.append(rows[-1])

    for m in PEOPLE_PAT.finditer(text):
        den, num, pct = int(m.group(1)), int(m.group(2)), float(m.group(3))
        calc = num / den * 100
        ok = abs(calc - pct) <= 1.0
        line_no = text[:m.start()].count("\n") + 1
        rows.append({"報告": path.name, "行號": line_no, "原文": m.group(0), "宣稱%": pct,
                     "分子": num, "分母": den, "重算%": round(calc, 1),
                     "誤差": round(calc - pct, 2), "通過": ok})
        if not ok:
            bad.append(rows[-1])

    lift_rows = []
    for m in LIFT_PAT.finditer(text):
        lift, num, den = float(m.group(1)), int(m.group(2)), int(m.group(3))
        line_no = text[:m.start()].count("\n") + 1
        lift_rows.append({"報告": path.name, "行號": line_no, "原文": m.group(0),
                          "宣稱lift": lift, "分子": num, "分母": den,
                          "群內比例": round(num / den, 3)})

    return rows, lift_rows, bad


def audit_report():
    """A. 逐份掃描 REPORTS 裡的報告，重算每一個「百分比（分子/分母）」。"""
    missing = [p for p in REPORTS if not p.exists()]
    if missing:
        sys.exit("找不到報告：" + "、".join(str(p) for p in missing)
                 + "\n（若報告已改名或移除，請同步更新 06_number_index.py 的 REPORTS）")

    all_rows, all_lifts, all_bad = [], [], []
    print("A. 報告本文稽核")
    for path in REPORTS:
        rows, lift_rows, bad = audit_one(path)
        all_rows += rows
        all_lifts += lift_rows
        all_bad += bad

        print(f"   {path.name}：掃到 {len(rows)} 個「百分比（分子/分母）」寫法、"
              f"{len(lift_rows)} 個 lift 標示")
        if bad:
            print(f"      ✗ 有 {len(bad)} 處對不上：")
            for b in bad:
                print(f"         第 {b['行號']} 行 {b['原文']} → "
                      f"重算 {b['重算%']}%（誤差 {b['誤差']}）")
        else:
            print("      ✓ 全部相符（容許 ±1pt 四捨五入）")

    audit = pd.DataFrame(all_rows)
    C.save_table(audit, "99_報告數字自我稽核", "每個「%（分子/分母）」的重算結果（含報告欄）")
    lift_df = pd.DataFrame(all_lifts)
    C.save_table(lift_df, "99_報告lift稽核", "每個 lift 標示的分子/分母（含報告欄）")
    return audit, lift_df, len(all_bad)


def build_index():
    """B. 從分析結果表組出數字索引。每一列都指得回一個可重跑的來源。"""
    T = C.TABLE_DIR
    rows = []

    def tier(den):
        """
        分母 ≥120 視為全體題，用整體信賴度標準（N≥80 為 L2）；
        其餘是分群，用分群標準（N≥30 為 L2、≥50 為 L3）。
        兩套標準混用會讓「全體 N=127」被標成 L3、與報告開頭的 L2 打架。
        """
        return C.confidence(den) if den >= 120 else C.subgroup_confidence(den)

    def add(section, item, num, den, source, filt):
        rows.append({
            "報告位置": section, "項目": item,
            "數字": f"{num / den:.1%}" if den else "",
            "分子": int(num), "分母": int(den),
            "驗算式": f"{int(num)}/{int(den)}",
            "來源欄位／表": source, "篩選條件": filt,
            "信賴度": tier(int(den)),
        })

    def from_table(fname, section, source, filt, label_col="選項",
                   num_col="票數", den_col="分母", top=None):
        d = pd.read_csv(T / fname)
        if top:
            d = d.head(top)
        for _, r in d.iterrows():
            add(section, str(r[label_col]), r[num_col], r[den_col], source, filt)

    # §1 樣本輪廓
    for f, sec, src in [("03_全體_年齡分布.csv", "§1.2 年齡", "你的年齡？"),
                        ("03_全體_性別分布.csv", "§1.2 性別", "你的性別？"),
                        ("03_全體_身分分布.csv", "§1.2 身分", "你目前主要的身分或工作場域是？")]:
        d = pd.read_csv(T / f)
        for _, r in d.iterrows():
            add(sec, str(r.iloc[0]), r["人數"], r["分母"], src, "全體 N=127")
    from_table("03_全體_居住地.csv", "§1.2 居住地", "你目前居住在哪個區域？", "全體 N=127")
    from_table("03_全體_g0v活動類型.csv", "§1.3 g0v 活動", "承上，你參加過哪些 g0v 活動？", "有作答者")

    # §3 分布位置
    # 分母對應到哪一群人。衍生變項的摘要表不帶這個資訊，但「分母是誰」正是這一批
    # 要擋的錯誤（分子分母取自錯的群體），所以在這裡補齊，不能留白。
    _WHO = {
        127: "全體 N=127",
        101: "曾接觸者 N=101（從未接觸層未被問到這些題）",
        95: "曾接觸者中參與深度落在五級軸上的 95 人（不含「以上都不太像我」6 人）",
        47: "曾參與者 N=47（只有做過專案的人被問到這些題）",
    }
    # 衍生變項不是問卷上的一題，但每一個都由某一題（或某兩題）算出來。
    # 索引的「來源欄位／表」欄若只寫 01_衍生變項.csv，讀者查不到那到底問的是什麼，
    # 也就無法判斷「這一題是不是這句話要講的事」——那正是這一批要擋的錯誤。
    _DERIVED_FROM = {
        "參與深度": C.C_DEPTH,
        "決策位置": f"{C.C_DEPTH}（五級收合為兩類）",
        "最深角色": f"{C.C_ROLES}（取此人勾過的最深一階）",
        "角色廣度（勾選數）": f"{C.C_ROLES}（取此人勾了幾種角色）",
        "專案階段（合併）": f"{C.C_STAGE}（五類收合為四類）",
        "同時進行專案數": C.C_N_PROJECTS,
        "投入強度（過去30天）": C.C_HOURS,
        "年齡": C.C_AGE,
    }
    d = pd.read_csv(T / "01_衍生變項摘要.csv")
    for _, r in d.iterrows():
        note = "" if pd.isna(r["備註"]) else str(r["備註"]).strip()
        who = _WHO.get(int(r["分母"]))
        if who is None:
            sys.exit(f"✗ 衍生變項「{r['變項']}」的分母 {int(r['分母'])} 沒有登記是哪一群人，"
                     "請補 06_number_index.py 的 _WHO。"
                     "（留白會讓取數來源清查表的「分母是誰」欄名不副實）")
        src = _DERIVED_FROM.get(str(r["變項"]))
        if src is None:
            sys.exit(f"✗ 衍生變項「{r['變項']}」沒有登記它算自哪一題，"
                     "請補 06_number_index.py 的 _DERIVED_FROM")
        add(f"§3 {r['變項']}", str(r["類別"]), r["人數"], r["分母"],
            src, f"{who}｜{note}" if note else who)

    # §4 困擾
    d = pd.read_csv(T / "03_困擾_全體.csv")
    for _, r in d.iterrows():
        add("§4.1 困擾 %≥3", r["困難"], r["達3以上_分子"], r["分母"],
            f"{C.TROUBLE_PREFIX}[…]", "曾參與 N=47；主指標 %≥3")
        add("§4.1 困擾 %≥4", r["困難"], r["達4以上_分子"], r["分母"],
            f"{C.TROUBLE_PREFIX}[…]", "曾參與 N=47；主指標 %≥4")
    d = pd.read_csv(T / "03_困擾×決策位置.csv")
    for _, r in d.iterrows():
        add("§4.2 困擾×決策位置", f"{r['分群']}／{r['困難']}", r["達3以上_分子"], r["分母"],
            f"{C.TROUBLE_PREFIX}[…]", f"曾參與且決策位置={r['分群']}")

    # §5 動機
    d = pd.read_csv(T / "04_動機_流向.csv")
    for _, r in d.iterrows():
        add("§5.1 初次動機", r["動機"], r["初次_人數"], r["分母"], C.C_MOTIVE_FIRST, "曾參與 N=47")
        add("§5.1 持續動機", r["動機"], r["持續_人數"], r["分母"], C.C_MOTIVE_NOW, "曾參與 N=47")
        rows.append({"報告位置": "§5.1 留存／流失／新增", "項目": r["動機"],
                     "數字": f"留存 {int(r['留存'])}／流失 {int(r['流失'])}／新增 {int(r['新增'])}",
                     "分子": int(r["留存"]), "分母": int(r["初次_人數"]),
                     "驗算式": f"留存{int(r['留存'])}+流失{int(r['流失'])}={int(r['初次_人數'])}（初次）",
                     "來源欄位／表": f"{C.C_MOTIVE_FIRST} × {C.C_MOTIVE_NOW}", "篩選條件": "同一批曾參與者 N=47 配對比較",
                     "信賴度": C.subgroup_confidence(47)})
    d = pd.read_csv(T / "03_年齡×持續動機_lift.csv")
    for _, r in d[d["選項"].isin(C.MOTIVES)].iterrows():
        # lift 在分子少於 common.LIFT_MIN_NUMERATOR 時是**刻意留空**的，不是算壞。
        # 直接把留空值格式化成字串會印出字面上的「lift nan」，讓拿索引抽查的人
        # 以為程式壞了；改成寫出留空的理由。
        blank = pd.isna(r["lift"])
        reason = str(r["lift留空原因"]).strip() if not pd.isna(r["lift留空原因"]) else ""
        shown = f"lift 未計算（{reason}）" if blank else f"lift {r['lift']}"
        calc = (f"({int(r['分子'])}/{int(r['分母'])}) ÷ {r['全體比例']}"
                + ("＝未計算" if blank else f" = {r['lift']}"))
        rows.append({"報告位置": "§5.2 年齡×持續動機 lift", "項目": f"{r['分群']}／{r['選項']}",
                     "數字": shown, "分子": int(r["分子"]), "分母": int(r["分母"]),
                     "驗算式": calc,
                     "來源欄位／表": f"{C.C_MOTIVE_NOW} × {C.C_AGE}",
                     "篩選條件": f"曾參與且年齡={r['分群']}（年齡收合 3 層）",
                     "信賴度": "L1（僅供產生假設）"})

    # §6 資源
    d = pd.read_csv(T / "03_資源×專案階段.csv")
    for _, r in d.iterrows():
        add("§6.2 資源×階段", f"{r['分群']}／{r['選項']}", r["分子"], r["分母"],
            C.C_RESOURCES, f"曾參與且階段={r['分群']}")
    d = pd.read_csv(T / "03_資源×決策位置.csv")
    for _, r in d.iterrows():
        add("§6.3 資源×決策位置", f"{r['分群']}／{r['選項']}", r["分子"], r["分母"],
            C.C_RESOURCES, f"曾參與且決策位置={r['分群']}")

    # §7–§9
    from_table("03_出資者_評估準則.csv", "§7 出資評估準則", C.C_FUND_CRITERIA, "曾出資者 N=27")
    from_table("03_出資者_資源沙漠階段.csv", "§7 資源沙漠階段", C.C_FUND_HARDEST, "曾出資者 N=27")
    from_table("03_全體_跨領域工具.csv", "§8.2 跨領域工具", C.C_TOOLS, "全體，最多選 3")
    from_table("03_全體_議題領域.csv", "§8.2 議題領域", C.C_DOMAINS, "全體，最多選 5")
    from_table("03_全體_g0v消息管道.csv", "§9.1 g0v 消息管道", C.C_G0V_CHANNEL, "全體，複選")
    from_table("03_全體_公民科技資訊管道.csv", "§9.1 資訊管道", C.C_INFO_CHANNEL, "全體，複選")
    from_table("03_未參與原因.csv", "§9.2 未參與原因", C.C_NOT_JOIN_WHY,
               "從未接觸層 N=26，最多選 3（此題未問「接觸未參與」層）")
    from_table("03_全體_活動意願.csv", "§9.4 活動意願", C.C_EVENTS, "全體，最多選 2")
    d = pd.read_csv(T / "03_三層×活動意願.csv")
    for _, r in d.iterrows():
        add("§9.4 活動意願×三層", f"{r['分群']}／{r['選項']}", r["分子"], r["分母"],
            C.C_EVENTS, f"入坑分層={r['分群']}")

    # ---- 取數來源清查補上的來源 ----
    # 每一組都標明「那一題問的是誰」，因為這一批要擋的錯誤不是算錯，
    # 而是分子分母取自錯的題目或錯的群體。

    # 所屬組織：開放題人工歸類，分母是 55 位願意填答的人，不是全體 127
    d = pd.read_csv(T / "09_開放題_所屬組織或團體.csv")
    for _, r in d.iterrows():
        add("§1.2 所屬組織", str(r["主題"]), r["筆數"], r["分母"], C.C_ORG_TEXT,
            "全體中有填答此開放題者（人工歸類）")

    # g0v 參加經驗：61/126 那個錯誤的現場。來源必須是「最近一次參加是什麼時候」
    # （127 人全數作答），不是分支題「你參加過哪些 g0v 活動」（僅 126 人作答）。
    d = pd.read_csv(T / "03_全體_g0v參加經驗.csv")
    for _, r in d.iterrows():
        add("§1.3 g0v 參加經驗", f"{r['分群']}／{r['類別']}", r["分子"], r["分母"],
            C.C_G0V_LAST, f"{r['分群']}；全數作答，無分支")

    # 地區連結：人工編碼，分母是 63 位填答此開放題的人。
    # 交叉那兩列的分母改成「住雙北的 79 人」——同一句話裡出現兩個分母，
    # 正是最容易被誤植的地方，所以兩者分開列。
    d = pd.read_csv(T / "09_開放題_地區連結.csv")
    for _, r in d.iterrows():
        add("§1.2 地區連結", str(r["主題"]), r["筆數"], r["分母"], C.C_REGION_LINK,
            "全體中有填答此開放題者（人工編碼，見 分析程式/開放題編碼.csv）")
    d = pd.read_csv(T / "09_開放題_地區連結×雙北.csv")
    for _, r in d.iterrows():
        add("§1.2 地區連結", f"住雙北且有「{r['主題']}」連結", r["住雙北且有此連結"],
            r["住雙北人數"], f"{C.C_REGION_LINK} × {C.C_REGION}",
            "分母是住雙北的 79 人，不是填答此題的 63 人")

    # 雙北合計：不可用台北票數＋新北票數，見 03_全體_居住地_雙北合計.csv 的「算法」欄
    d = pd.read_csv(T / "03_全體_居住地_雙北合計.csv")
    for _, r in d.iterrows():
        add("§1.2 居住地（雙北合計）", str(r["類別"]), r["分子"], r["分母"], C.C_REGION,
            "全體 N=127；people_count 去重，非票數相加")

    # 角色勾選：分母 101 位曾接觸者，**不是** 47 位曾參與者。
    # 角色與參與深度是兩條不同的軸（見報告附錄 A1），分母也不同。
    from_table("03_全體_角色勾選.csv", "§3 角色勾選", C.C_ROLES, "曾接觸者 N=101，複選")

    # 「動手做但沒用過」：第二列的分母是第一列的分子（38），不是 101。
    # 這種「分母是另一個數字的分子」的寫法最容易在報告裡被誤植成 101。
    d = pd.read_csv(T / "03_角色_動手做但沒用過.csv")
    for _, r in d.iterrows():
        add("§3 動手做但沒用過", str(r["類別"]), r["分子"], r["分母"], C.C_ROLES,
            "曾接觸者 N=101，複選；勾兩個角色的人只算一次")

    # 困擾 × 參與深度 5 級：各格 5–18 人。報告第 3.1、3.2、3.3 節的數字都取自這張表，
    # 而不是二分版的 03_困擾×決策位置.csv——兩張表的分母不同，不可互換。
    d = pd.read_csv(T / "03_困擾×參與深度5級.csv")
    for _, r in d.iterrows():
        add("§4.2 困擾×參與深度5級", f"{r['分群']}／{r['困難']}（%≥3）",
            r["達3以上_分子"], r["分母"], f"{C.TROUBLE_PREFIX}[…]",
            f"曾參與且參與深度={r['分群']}")

    # 動機組合是否改變：同一批 47 人前後兩題的配對比較，不是兩次獨立調查
    d = pd.read_csv(T / "04_動機_個人變化.csv")
    for _, r in d.iterrows():
        add("§5.1 動機組合是否改變", str(r["類別"]), r["人數"], r["分母"],
            f"{C.C_MOTIVE_FIRST} × {C.C_MOTIVE_NOW}", "曾參與 N=47 逐人配對比較")

    # 資源與專長：這兩題只有曾參與的 47 人被問到
    from_table("03_全體_資源.csv", "§6.1 資源（全體曾參與者）", C.C_RESOURCES,
               "曾參與 N=47，複選")
    from_table("03_全體_專長.csv", "§6.1 專長（全體曾參與者）", C.C_SKILLS,
               "曾參與 N=47，複選；問的是在該專案負責什麼，不是會什麼")

    # 管道官方 vs 親友：互斥四分組是以人去重算的，不是各選項票數相加
    d = pd.read_csv(T / "03_管道_官方vs親友.csv")
    for _, r in d.iterrows():
        add("§9.1 管道：官方 vs 親友", f"{r['分群']}／{r['類別']}", r["分子"], r["分母"],
            C.C_G0V_CHANNEL,
            f"{r['分群']}；以人去重" + ("；互斥四分組相加＝分母" if r["互斥四分組"] else ""))

    # §8.1 / §10 狩野
    d = pd.read_csv(T / "02_狩野_全體.csv")
    for _, r in d.iterrows():
        rows.append({"報告位置": "§8.1 狩野（全體）", "項目": r["主題"],
                     "數字": f"SI {r['SI']}／DSI {r['DSI']}（{r['落點']}）",
                     "分子": int(r["A"] + r["O"]), "分母": int(r["有效樣本"]),
                     "驗算式": f"SI=(A{int(r['A'])}+O{int(r['O'])})/{int(r['有效樣本'])}；"
                               f"DSI=-(O{int(r['O'])}+M{int(r['M'])})/{int(r['有效樣本'])}",
                     "來源欄位／表": f"{C.KANO_FUNC_PREFIX} × {C.KANO_DYSF_PREFIX}（成對問法查表）",
                     "篩選條件": "全體有作答者；分母排除 R 與 Q",
                     "信賴度": r["信賴度"]})
    d = pd.read_csv(T / "02_狩野_新舊對照.csv")
    for _, r in d.iterrows():
        rows.append({"報告位置": "§10 新舊對照", "項目": r["主題"],
                     "數字": f"SI {r['SI_舊']}→{r['SI_新']}",
                     "分子": int(r["有作答差"]), "分母": int(r["有作答_新"]),
                     "驗算式": f"{int(r['有作答_舊'])}→{int(r['有作答_新'])}，差 {int(r['有作答差'])}（應=6）",
                     "來源欄位／表": f"{C.KANO_FUNC_PREFIX} × {C.KANO_DYSF_PREFIX}（新舊回收檔比較）",
                     "篩選條件": "新檔 vs 舊去識別化檔",
                     "信賴度": "黃金對照"})

    idx = pd.DataFrame(rows)

    # 上面的 § 編號是《生態系分析報告 v1》的章節。整合版重排成 1–11 章後，
    # 讀者拿索引回頭對照會對不上，所以另外標一欄整合版的章節位置。
    # 舊欄保留，兩份報告都還在版控裡，抽查任一份都要查得到。
    idx = idx.rename(columns={"報告位置": "報告位置（v1 舊報告）"})
    idx.insert(0, "報告位置（整合版）",
               idx["報告位置（v1 舊報告）"].map(_INTEGRATED_SECTION).fillna("未對應"))

    unmapped = sorted(set(idx.loc[idx["報告位置（整合版）"] == "未對應",
                                  "報告位置（v1 舊報告）"]))
    if unmapped:
        sys.exit("✗ 數字索引有章節對不到整合版，請補 _INTEGRATED_SECTION："
                 + "、".join(unmapped))

    C.save_table(idx, "99_數字索引", "報告每個數字的來源、分子分母與驗算式")
    return idx


def audit_traceable(idx):
    """
    C. 每個數字都要對得回一張來源表。

    兩道檢查：
      1. 報告裡每一處「分子/分母」，索引裡必須有分子分母都相同的列。
      2. 裸寫的「N 人（P%）」沒有把分母寫進句子，改用索引裡出現過的分母回推：
         只要有某個分母 d 同時滿足「N/d 約等於 P%」與「(N, d) 在索引裡」，就算對得回去。

    回傳 (未通過的清單, 裸寫回推結果)。
    """
    pairs = {(int(r["分子"]), int(r["分母"])) for _, r in idx.iterrows()}
    denoms = sorted({int(r["分母"]) for _, r in idx.iterrows() if int(r["分母"]) > 0})

    bad, bare_rows = [], []
    print("C. 每個數字對得回來源表")
    for path in REPORTS:
        text = path.read_text(encoding="utf-8")

        covered = []          # 已被 A 的三個 pattern 涵蓋的字元範圍
        explicit = []         # (位置, 分子, 分母, 原文)
        for m in PCT_PAT.finditer(text):
            covered.append((m.start(), m.end()))
            explicit.append((m.start(), int(m.group(2)), int(m.group(3)), m.group(0)))
        for m in PEOPLE_PAT.finditer(text):
            covered.append((m.start(), m.end()))
            explicit.append((m.start(), int(m.group(2)), int(m.group(1)), m.group(0)))
        for m in LIFT_PAT.finditer(text):
            covered.append((m.start(), m.end()))

        n_bad_here = 0
        for pos, num, den, raw in explicit:
            if (num, den) not in pairs:
                n_bad_here += 1
                bad.append({"報告": path.name, "行號": text[:pos].count("\n") + 1,
                            "原文": raw, "分子": num, "分母": den,
                            "問題": "索引裡找不到這組分子/分母"})

        n_bare, n_bare_bad = 0, 0
        for m in BARE_PEOPLE_PAT.finditer(text):
            if any(s <= m.start() < e for s, e in covered):
                continue
            n_bare += 1
            num, pct = int(m.group(1)), float(m.group(2))
            fits = [d for d in denoms
                    if abs(num / d * 100 - pct) <= 1.0 and (num, d) in pairs]
            line_no = text[:m.start()].count("\n") + 1
            bare_rows.append({"報告": path.name, "行號": line_no, "原文": m.group(0),
                              "分子": num, "宣稱%": pct,
                              "可回推的分母": "、".join(str(d) for d in fits) or "（回推不到）",
                              "通過": bool(fits)})
            if not fits:
                n_bare_bad += 1
                bad.append({"報告": path.name, "行號": line_no, "原文": m.group(0),
                            "分子": num, "分母": None,
                            "問題": "裸寫「N 人（P%）」，索引裡回推不到相符的分母"})

        print(f"   {path.name}：{len(explicit)} 處寫明分母"
              f"（{n_bad_here} 處查無來源）、{n_bare} 處裸寫（{n_bare_bad} 處回推不到）")

    if bad:
        print(f"      ✗ 共 {len(bad)} 處對不回來源：")
        for b in bad:
            print(f"         {b['報告']} 第 {b['行號']} 行 {b['原文']} → {b['問題']}")
    else:
        print("      ✓ 全部對得回 99_數字索引.csv 的某一列")

    return bad, bare_rows


def main():
    _audit, _lifts, n_bad = audit_report()
    print()
    idx = build_index()
    print(f"\nB. 數字索引：{len(idx)} 列，"
          f"涵蓋整合版 {idx['報告位置（整合版）'].nunique()} 個位置")

    print()
    untraceable, bare_rows = audit_traceable(idx)
    C.save_table(pd.DataFrame(bare_rows), "99_報告裸數字回推",
                 "裸寫「N 人（P%）」各自回推到哪個分母")

    print("\n=== 抽樣 8 列（Claire 可比照此法隨機抽查）===")
    pd.set_option("display.width", 220, "display.max_colwidth", 24)
    print(idx.sample(8, random_state=1)[
        ["報告位置（整合版）", "項目", "數字", "分子", "分母", "驗算式", "信賴度"]
    ].to_string(index=False))

    if n_bad:
        sys.exit(f"\n✗ 報告本文共有 {n_bad} 處數字對不上（詳見上方逐份清單），"
                 "請先修正報告再交付。")
    if untraceable:
        sys.exit(f"\n✗ 報告本文有 {len(untraceable)} 處數字在 99_數字索引.csv 裡對不回來源"
                 "（詳見上方 C 段清單）。"
                 "\n  這代表數字憑空出現、已經過期，或分析改了而報告沒跟著改。"
                 "\n  修法：補上對應的分析輸出表並接進 build_index()，或修正報告的數字。")
    print(f"\n✓ {len(REPORTS)} 份報告的所有比例都自洽，且每個數字都對得回來源表；"
          "數字索引已產出。")


if __name__ == "__main__":
    main()
