# -*- coding: utf-8 -*-
"""
06_number_index.py — 產出數字索引，並「回頭驗證報告本文」。

這支腳本做兩件事：

A. **自動稽核報告本文**：掃描報告裡每一個「NN%（分子/分母）」寫法，
   重算 分子÷分母 是否等於所寫的百分比。任何一處對不上就報錯。
   → 這是無法蒙混的檢查：報告中所有比例都必須自洽。
   稽核對象是 REPORTS 列出的每一份報告（生態系分析 v1 ＋ 對外整合版）。
   列在 REPORTS 裡的檔案若不存在就直接報錯，避免改名後這道關卡默默失效。

B. **產出 99_數字索引.csv**：報告位置／數字／來源欄位／篩選條件／分子／分母／驗算式，
   讓 Claire 隨機抽查，不必碰程式。

執行：python3 06_number_index.py
"""

import re
import sys

import pandas as pd

import common as C

# 要稽核的報告。整合版是要對外發布的那一份，必須跟 v1 一樣受這道關卡保護。
REPORTS = [
    C.OUT_DIR / "公民科技生態系分析報告_v1.md",
    C.OUT_DIR / "公民科技生態系分析報告_整合版_v1.md",
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
    "§3 投入強度（過去30天）": "未引用於整合版正文",
    "§3 年齡": "第 4 章",
    "§4.1 困擾 %≥3": "第 3 章",
    "§4.1 困擾 %≥4": "第 3 章",
    "§4.2 困擾×決策位置": "第 3.2 節",
    "§5.1 初次動機": "第 4 章",
    "§5.1 持續動機": "第 4 章",
    "§5.1 留存／流失／新增": "第 4 章",
    "§5.2 年齡×持續動機 lift": "第 4 章",
    "§6.2 資源×階段": "第 5.1 節",
    "§6.3 資源×決策位置": "第 5.2 節",
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
    d = pd.read_csv(T / "01_衍生變項摘要.csv")
    for _, r in d.iterrows():
        add(f"§3 {r['變項']}", str(r["類別"]), r["人數"], r["分母"],
            "01_衍生變項.csv（衍生）", str(r["備註"]) or "見 §2.2 變項定義")

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
                     "來源欄位／表": "04_動機_流向.csv", "篩選條件": "同一批曾參與者 N=47 配對比較",
                     "信賴度": C.subgroup_confidence(47)})
    d = pd.read_csv(T / "03_年齡×持續動機_lift.csv")
    for _, r in d[d["選項"].isin(C.MOTIVES)].iterrows():
        rows.append({"報告位置": "§5.2 年齡×持續動機 lift", "項目": f"{r['分群']}／{r['選項']}",
                     "數字": f"lift {r['lift']}", "分子": int(r["分子"]), "分母": int(r["分母"]),
                     "驗算式": f"({int(r['分子'])}/{int(r['分母'])}) ÷ {r['全體比例']} = {r['lift']}",
                     "來源欄位／表": "03_年齡×持續動機_lift.csv",
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

    # §8.1 / §10 狩野
    d = pd.read_csv(T / "02_狩野_全體.csv")
    for _, r in d.iterrows():
        rows.append({"報告位置": "§8.1 狩野（全體）", "項目": r["主題"],
                     "數字": f"SI {r['SI']}／DSI {r['DSI']}（{r['落點']}）",
                     "分子": int(r["A"] + r["O"]), "分母": int(r["有效樣本"]),
                     "驗算式": f"SI=(A{int(r['A'])}+O{int(r['O'])})/{int(r['有效樣本'])}；"
                               f"DSI=-(O{int(r['O'])}+M{int(r['M'])})/{int(r['有效樣本'])}",
                     "來源欄位／表": "02_狩野_全體.csv（功能型×反功能型查表）",
                     "篩選條件": "全體有作答者；分母排除 R 與 Q",
                     "信賴度": r["信賴度"]})
    d = pd.read_csv(T / "02_狩野_新舊對照.csv")
    for _, r in d.iterrows():
        rows.append({"報告位置": "§10 新舊對照", "項目": r["主題"],
                     "數字": f"SI {r['SI_舊']}→{r['SI_新']}",
                     "分子": int(r["有作答差"]), "分母": int(r["有作答_新"]),
                     "驗算式": f"{int(r['有作答_舊'])}→{int(r['有作答_新'])}，差 {int(r['有作答差'])}（應=6）",
                     "來源欄位／表": "02_狩野_新舊對照.csv",
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


def main():
    _audit, _lifts, n_bad = audit_report()
    print()
    idx = build_index()
    print(f"\nB. 數字索引：{len(idx)} 列，"
          f"涵蓋整合版 {idx['報告位置（整合版）'].nunique()} 個位置")

    print("\n=== 抽樣 8 列（Claire 可比照此法隨機抽查）===")
    pd.set_option("display.width", 220, "display.max_colwidth", 24)
    print(idx.sample(8, random_state=1)[
        ["報告位置（整合版）", "項目", "數字", "分子", "分母", "驗算式", "信賴度"]
    ].to_string(index=False))

    if n_bad:
        sys.exit(f"\n✗ 報告本文共有 {n_bad} 處數字對不上（詳見上方逐份清單），"
                 "請先修正報告再交付。")
    print(f"\n✓ {len(REPORTS)} 份報告的所有比例都自洽；數字索引已產出。")


if __name__ == "__main__":
    main()
