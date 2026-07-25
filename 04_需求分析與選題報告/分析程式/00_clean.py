# -*- coding: utf-8 -*-
"""
00_clean.py — 去識別化、清理、分層，並產出欄位辨識表。

這是唯一允許讀取原始 CSV（含 email／電話）的腳本。

輸出：
  03_問卷回收資料/去識別化_至20260724.csv    之後所有分析的唯一資料來源
  04_需求分析與選題報告/分析結果/00_欄位辨識表.csv
  04_需求分析與選題報告/分析結果/00_清理紀錄.csv

執行：python3 00_clean.py
"""

import sys
import pandas as pd

import common as C

# ---------------------------------------------------------------- 欄位題型宣告
# 先宣告、再用資料特徵自動核對，兩者不一致就標「低信心」請人確認。
# 這是 satisfaction-survey-analyzer 步驟 1「先辨識、後分析」的落實。

SPEC = {
    C.C_TS: ("時間戳記", "全體"),
    C.C_LAST_CONTACT: ("單選（分層依據）", "全體"),
    C.C_ROLES: ("複選（角色，建階梯與廣度）", "曾接觸"),
    C.C_DEPTH: ("單選序位（參與深度 1–5＋逃生選項）", "曾接觸"),
    C.C_EVER: ("單選（分層依據）", "曾接觸"),
    C.C_PROJ_DESC: ("開放題", "曾參與"),
    C.C_STAGE: ("單選序位（專案階段）", "曾參與"),
    C.C_SKILLS: ("複選（專長）", "曾參與"),
    C.C_RESOURCES: ("複選（資源）", "曾參與"),
    C.C_HOURS: ("單選序位（投入強度）", "曾參與"),
    C.C_ACTION_TEXT: ("開放題", "曾參與"),
    C.C_MOTIVE_FIRST: ("複選（初次動機，最多 2）", "曾參與"),
    C.C_MOTIVE_NOW: ("複選（持續動機，最多 2）", "曾參與"),
    C.C_N_PROJECTS: ("單選（同時進行專案數）", "曾參與"),
    # ⚠ 分支到「從未接觸」層（26 人），不是「接觸未參與」層。
    #    → 被選為主要服務對象的「接觸未參與」54 人，問卷從未問過他們為何沒投入。
    C.C_NOT_JOIN_WHY: ("複選（未參與原因，最多 3）", "從未接觸"),
    C.C_DOMAINS: ("複選（議題領域，最多 5）", "全體"),
    C.C_TOOLS: ("複選（跨領域工具，最多 3）", "全體"),
    C.C_EVENTS: ("複選（活動意願，最多 2）", "全體"),
    C.C_FUNDED: ("單選（出資者篩選）", "全體"),
    C.C_FUND_DESC: ("開放題", "出資者"),
    C.C_FUND_CRITERIA: ("複選（出資評估準則，最多 3）", "出資者"),
    # 設計上為複選，但 27 位出資者全部只勾一項，實務上等同單選
    C.C_FUND_HARDEST: ("複選（資源沙漠階段；實際皆單選）", "出資者"),
    C.C_G0V_LAST: ("單選（g0v 活動近因）", "全體"),
    C.C_G0V_EVENTS: ("複選（g0v 活動類型）", "全體"),
    C.C_G0V_CHANNEL: ("複選（g0v 消息管道）", "全體"),
    C.C_INFO_CHANNEL: ("複選（公民科技資訊管道）", "全體"),
    C.C_AGE: ("單選（年齡層）", "全體"),
    C.C_IDENTITY: ("單選（身分／工作場域）", "全體"),
    C.C_ORG_TEXT: ("開放題（組織）", "全體"),
    C.C_GENDER: ("單選（性別）", "全體"),
    # 表單實為複選：126 人勾 1 項、1 人勾 3 項（台北／新北／桃園）
    C.C_REGION: ("複選（居住地；126/127 只勾一項）", "全體"),
    C.C_REGION_LINK: ("開放題（需人工編碼為地區）", "全體"),
    "想持續收到社群活動消息嗎？勾選你想加入的管道，我們將把相關資訊寄送給你": ("複選（訂閱意願）", "全體"),
}


def detect(series: pd.Series) -> str:
    """
    由資料特徵自動判斷題型，用來核對 SPEC。

    先判開放題再判複選：開放題的文字常含「, 」，若先看分隔字串會把
    專案描述、組織名稱等自由填答誤判為複選。
    """
    from collections import Counter
    vals = [v for v in series.astype(str).str.strip() if v]
    if not vals:
        return "全空"
    uniq = set(vals)

    # 複選題：拆開後的「單一選項」會重複出現且種類有限。
    # 用選項層級判斷，才不會因為「每人勾的組合都不同」而誤判為開放題。
    if any(C.MULTI_SELECT_SEP in v for v in vals):
        opts = Counter(o.strip() for v in vals for o in v.split(C.MULTI_SELECT_SEP) if o.strip())
        repeated = sum(n for o, n in opts.items() if n >= 3)
        if len(opts) <= 40 and repeated / sum(opts.values()) > 0.5:
            return "複選"

    if len(uniq) / len(vals) > 0.8 and len(vals) > 5:   # 幾乎人人不同 → 自由填答
        return "開放題"
    if len(uniq) <= 12 and max(len(v) for v in uniq) < 80:
        return "單選"
    return "開放題"


def main():
    if not C.RAW_CSV.exists():
        sys.exit(f"找不到原始檔：{C.RAW_CSV}")

    df = pd.read_csv(C.RAW_CSV, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    n_raw = len(df)
    log = []
    print(f"原始檔：{n_raw} 列 × {len(df.columns)} 欄")

    # ---------- 1. 移除個資欄 ----------
    dropped = [c for c in C.PII_COLS if c in df.columns]
    for c in dropped:
        nonblank = (df[c].str.strip() != "").sum()
        log.append({"步驟": "移除個資欄", "對象": c, "影響筆數": nonblank})
        print(f"  移除個資欄「{c[:30]}…」（原有 {nonblank} 筆非空值）")
    df = df.drop(columns=dropped)

    # ---------- 2. 開放題與複選題中的人名去識別化 ----------
    redacted = 0
    for col in df.columns:
        for name, placeholder in C.NAME_REDACTIONS.items():
            hit = df[col].str.contains(name, regex=False, na=False)
            if hit.any():
                redacted += int(hit.sum())
                log.append({"步驟": "人名去識別化", "對象": f"{col} / {name}", "影響筆數": int(hit.sum())})
                df.loc[hit, col] = df.loc[hit, col].str.replace(name, placeholder, regex=False)
    print(f"  人名去識別化：{redacted} 處")

    # ---------- 3. 選項歸併（大小寫／錯字造成的重複選項）----------
    for col, mapping in C.OPTION_MERGE.items():
        if col not in df.columns:
            continue
        for wrong, right in mapping.items():
            # 以完整選項為單位取代，避免誤傷子字串
            def fix(v, w=wrong, r=right):
                opts = [o.strip() for o in str(v).split(C.MULTI_SELECT_SEP)]
                return C.MULTI_SELECT_SEP.join(r if o == w else o for o in opts if o)
            before = df[col].str.split(C.MULTI_SELECT_SEP).apply(
                lambda xs: sum(1 for x in xs if x.strip() == wrong)).sum()
            if before:
                df[col] = df[col].apply(fix)
                log.append({"步驟": "選項歸併", "對象": f"{col[:20]}… / {wrong} → {right}", "影響筆數": int(before)})
                print(f"  歸併：{wrong!r} → {right!r}（{before} 票）")

    # ---------- 3.5 複選題欄位正規化 ----------
    # 有些儲存格結尾帶多餘的分隔符（例如「我沒參加過 g0v 的活動, 」），
    # 以 ", " 切分時剛好不影響計數，但換一種切法就會拆出空選項。
    # 一律重組成乾淨的「選項, 選項」形式，讓下游怎麼切都安全。
    # ⚠ 只處理 SPEC 宣告為「複選」的欄位。先前用「欄位是否含 ', '」判斷，
    #   會把含逗號的開放題（例如「da0, 範圍很廣，包括數位身分等」）一併重寫，
    #   等於靜默竄改受訪者的逐字回答。
    multi_cols = [c for c, (kind, _) in SPEC.items() if kind.startswith("複選") and c in df.columns]
    normalized = 0
    for col in multi_cols:
        cleaned = df[col].apply(
            lambda v: C.MULTI_SELECT_SEP.join(
                o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()))
        diff = int((cleaned != df[col]).sum())
        if diff:
            normalized += diff
            log.append({"步驟": "複選題正規化（去除多餘分隔符）", "對象": col[:30], "影響筆數": diff})
        df[col] = cleaned
    print(f"  複選題正規化：{normalized} 個儲存格（僅限 {len(multi_cols)} 個複選欄位，開放題不動）")

    # ---------- 4. 角色題垃圾值標記 ----------
    def clean_roles(v):
        opts = [o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()]
        return C.MULTI_SELECT_SEP.join("其他（自由填答）" if o in C.ROLE_JUNK else o for o in opts)

    junk_hits = df[C.C_ROLES].apply(
        lambda v: sum(1 for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip() in C.ROLE_JUNK)).sum()
    df[C.C_ROLES] = df[C.C_ROLES].apply(clean_roles)
    log.append({"步驟": "角色題垃圾值歸為其他", "對象": C.C_ROLES, "影響筆數": int(junk_hits)})
    print(f"  角色題自由填答歸為「其他」：{junk_hits} 筆")

    # ---------- 5. 分層 ----------
    def layer(row):
        if row[C.C_LAST_CONTACT].strip() == C.NEVER_CONTACT_VALUE:
            return C.L_NEVER
        return C.L_DONE if row[C.C_EVER].strip() == "有" else C.L_AWARE

    df[C.LAYER] = df.apply(layer, axis=1)
    counts = df[C.LAYER].value_counts().to_dict()
    print(f"  分層：{ {k: counts.get(k, 0) for k in C.LAYER_ORDER} }")

    # 硬檢查：分層數必須符合預期，且加總 = 總列數
    for k, expected in C.LAYER_EXPECTED_N.items():
        got = counts.get(k, 0)
        assert got == expected, f"分層 {k} 應為 {expected}，實得 {got}——分層規則或資料有變，請先確認"
    assert sum(counts.values()) == n_raw, "分層加總不等於總列數"

    # 交叉核對：「從未接觸」的人應該全部沒答「曾參與過嗎」
    never = df[df[C.LAYER] == C.L_NEVER]
    assert (never[C.C_EVER].str.strip() == "").all(), "「從未接觸」層有人答了曾參與題，分層邏輯需重檢"
    # 「曾參與」層應與深度分支作答數一致
    done_answered = (df[df[C.LAYER] == C.L_DONE][C.C_STAGE].str.strip() != "").sum()
    assert done_answered == C.LAYER_EXPECTED_N[C.L_DONE], \
        f"曾參與層 {C.LAYER_EXPECTED_N[C.L_DONE]} 人，但答專案階段者 {done_answered} 人"
    print("  ✓ 分層檢查通過（含與深度分支的一致性核對）")

    # ---------- 6. 輸出去識別化檔 ----------
    for c in C.PII_COLS:
        assert c not in df.columns, f"個資欄 {c} 仍在輸出中"
    df.to_csv(C.CLEAN_CSV, index=False, encoding="utf-8-sig")
    print(f"\n去識別化檔已輸出：{C.CLEAN_CSV.name}（{len(df)} 列 × {len(df.columns)} 欄）")

    # ---------- 7. 欄位辨識表 ----------
    rows = []
    for col in df.columns:
        if col == C.LAYER:
            continue
        answered = int((df[col].astype(str).str.strip() != "").sum())
        auto = detect(df[col])
        declared, scope = SPEC.get(col, ("（未宣告）", "？"))
        if col.startswith(C.TROUBLE_PREFIX):
            declared, scope = "量表 1–5（困擾程度）", "曾參與"
        elif col.startswith(C.KANO_FUNC_PREFIX):
            declared, scope = "狩野功能型（五點）", "全體"
        elif col.startswith(C.KANO_DYSF_PREFIX):
            declared, scope = "狩野反功能型（五點）", "全體"
        agree = declared.startswith(auto[:2]) or auto[:2] in declared or (
            auto == "單選" and ("單選" in declared or "量表" in declared or "狩野" in declared))
        rows.append({
            "欄位": col,
            "宣告題型": declared,
            "自動判定": auto,
            "信心": "高" if agree else "低（請確認）",
            "分層歸屬": scope,
            "作答數": answered,
            "作答率": f"{answered / n_raw:.0%}",
        })
    spec_df = pd.DataFrame(rows)
    C.save_table(spec_df, "00_欄位辨識表")
    low = spec_df[spec_df["信心"] != "高"]
    if len(low):
        print(f"\n⚠ 有 {len(low)} 欄自動判定與宣告不符，需人工確認：")
        for _, r in low.iterrows():
            print(f"    {r['欄位'][:40]}… 宣告={r['宣告題型']} 自動={r['自動判定']}")
    else:
        print("\n✓ 全部欄位的宣告題型與自動判定一致")

    C.save_table(pd.DataFrame(log), "00_清理紀錄")


if __name__ == "__main__":
    main()
