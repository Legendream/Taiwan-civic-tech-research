# -*- coding: utf-8 -*-
"""
10_role_crosstab.py — 角色（Q3 複選）與角色廣度的交叉分析。

為什麼要單獨一支：03_crosstab.py 已經做了「參與深度（Q4 單選）」的交叉，
但**角色（Q3 複選）**只做到勾選率、廣度分布與重疊矩陣，沒有交叉到困擾、資源、動機。
報告要談「不同角色的處境差異」就缺這一塊。

同時輸出「依參與深度 5 級」的同一組指標，因為本檔的核心用途就是**比較這兩條軸**：
角色（Q3 複選，「你做什麼事」）與參與深度（Q4 單選序位，「你有多少決定權」），
哪一條比較能區辨處境。兩軸放在同一支腳本才對得起來。

⚠️ 這支腳本最重要的方法論限制，每張輸出表都會**寫成 CSV 欄位**（不是只印在終端機，
   因為這些表常被單獨打開，看不到 stdout）：

  1. **角色是複選，群體互相重疊，而且沒有深淺順序。**
     common.ROLE_LADDER 把角色排成使用者→出資者，那只是**輸出時的固定順序**，
     不是深淺量尺——出資者完全可以沒使用過、沒推廣過任何專案。
     因此五個角色群的數字**不可讀成遞增梯度**，只能讀成「五個重疊群體各自的水準」。
     又因為各群的平均角色廣度不同（3.49–4.56），連群間的小差異都可能只是
     「身兼多職的人被更多事情卡住」。每張表都附「該群平均角色廣度」欄揭露此混淆。
     真正有序的軸是參與深度（DEPTH_ORDER 1–5，主動權由低到高）與角色廣度（1–5）。

  2. **複選表的各列分子不可相加**。分子是「勾了該選項的人數」，跨選項相加會把
     同時勾多項的人重複計（例：出資者組 8 個資源分子相加＝47 > 分母 16）。

  3. 角色題分母是 101 位曾接觸者，但困擾／資源／動機只有 47 位曾參與者作答。
     所有交叉的分母都落在那 47 人之內。**信賴度不是一律 L1**：
     使用者(39)／落地推廣(36)／開發維護(33) 為 L2，發起者(27)／出資者(16) 為 L1。
     另加「決策可用性」欄，n<10 一律標「不可作為決策依據」——L1 從 5 人到 29 人
     用同一個標籤，區辨力不足。

  4. **小樣本的平均數以中位數為主指標**。例：參與深度「接收資訊」組平均 3.00 題
     但中位數僅 1.0，是被單一個案（某人 13 題中有 10 題達 3 分以上）拉起來的。
     故三張負荷表一律同時輸出 平均／中位數／最大值／一題都沒達標的人數。

  5. **自由填答收斂**：資源與動機題的選項外填答（n 皆為 1，且有「累了」「我現在已淡出」
     這類個人狀態）一律收斂成「其他（自由填答）」，依 common.py 的既有規範。
     未收斂時會出現 n=1 卻 lift 2.94 的假訊號，且在 16 人的小群中有回推到特定填答者的風險。
     另：分子 <5 的列一律不給 lift（分母小到 lift 只是雜訊）。

可驗證性（不必讀程式就能核對）：
  · 每張表都有 分子／分母_作答人數／群人數／比例／信賴度／決策可用性／讀法說明
  · 10_逐人核對表.csv 是去識別化的逐人明細，**含 13 題困擾原始分數與資源／動機勾選旗標**，
    可在 Excel 拉樞紐重算本檔每一張表（不只彙總表）
  · 開頭的守門檢查會讀 03_全體_角色勾選.csv 與 01_衍生變項.csv 實際比對，
    不是跟寫死的常數比；且用 raise 而非 assert，`python -O` 下依然生效

前置檔案（需先跑過對應腳本）：
  · 03_問卷回收資料/去識別化_至20260724.csv   ← 00_clean.py
  · 分析結果/01_衍生變項.csv                  ← 01_indices.py
  · 分析結果/03_全體_角色勾選.csv、03_角色重疊矩陣.csv  ← 03_crosstab.py

執行：python3 10_role_crosstab.py
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common as C

# 角色廣度的合併分組：在曾參與 47 人子集裡，1–5 逐級各只有 5–11 人
#（分布見本檔輸出 10_角色負荷_依廣度.csv 的逐級列；03_角色廣度分布.csv 是 101 人的分布，
#  數字為 46/20/12/11/10，不可拿來當這裡的依據）。逐級比較會被單一個案左右，
#  故主指標用二分組，逐級版一併輸出供追溯。
BREADTH_GROUPS = [("1–2 種角色", (1, 2)), ("3–5 種角色", (3, 5))]

ROLE_NOTE = ("角色為複選、各群互相重疊，且五個角色之間沒有深淺順序（輸出順序僅沿用 "
             "ROLE_LADDER 的固定排列），不可跨群當互斥類別比較、更不可讀成遞增梯度；"
             "「該群平均角色廣度」欄用於揭露身兼多職這個混淆。"
             "分母池＝曾參與專案的 47 人（角色題本身的 101 人不是這裡的分母）。")

BREADTH_NOTE = ("角色廣度為互斥且有序的分組（勾選角色數 1–5），可讀成順序。"
                "「切法」欄區分二分組與逐級：**兩套切法不可混在一起加總**"
                "（同一批 47 人被切了兩次，全部相加會得到 94）。"
                "逐級各僅 5–11 人，僅供追溯。分母池＝曾參與專案的 47 人。")

DEPTH_NOTE = ("參與深度為單選、各級互斥，且為有序序位（主動權由低到高），可讀成順序；"
              "但各級僅 5–18 人。**請以中位數為主指標**——平均易被單一個案拉動，"
              "例如「接收資訊」組平均 3.00 但中位數僅 1.0，係某一人 13 題中有 10 題達標所致。"
              "分母池＝曾參與專案的 47 人。")

MULTI_NOTE = ("各列分子＝勾了該選項的人數，**跨選項不可相加**（會把複選多項的人重複計）。"
              "選項外的自由填答已收斂成「其他（自由填答）」。分子 <5 的列不給 lift。")

TROUBLE_DEF = "「達3」＝該題評 3、4、5 分者合計（共 13 題，每題強制作答 1–5 分，無「沒遇到」選項）"

# lift 的分子下限。低於此值時 lift 由 1–4 個人決定，只是雜訊，一律留空。
# ⚠️ 這條政策必須套用到**每一個**輸出 lift 的地方，不能只實作一半——
#    先前只加在 multi_by_masks，trouble_by_group 漏掉，結果 21/65 列違反本檔規則。
LIFT_MIN_NUMERATOR = 5


def lift_blank_reason(n: int) -> str:
    return f"分子<{LIFT_MIN_NUMERATOR}，lift 為雜訊" if n < LIFT_MIN_NUMERATOR else ""


def usability(n: int) -> str:
    """決策可用性：補 subgroup_confidence 的不足（L1 從 5 人到 29 人共用一個標籤）。"""
    if n < 10:
        return "不可作為決策依據（n<10）"
    if n < 30:
        return "僅供參考"
    return "可用於比較"


def role_masks(df):
    """回傳 [(角色短名, 布林 Series)]，依 ROLE_LADDER 順序。複選，群體重疊、無深淺。"""
    picked = df[C.C_ROLES].apply(
        lambda v: {o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()})
    return [(C.ROLE_SHORT[r], picked.apply(lambda s, r=r: r in s)) for r in C.ROLE_LADDER]


def trouble_scores(df):
    """13 題困擾 → 分數 DataFrame（欄名為去前綴後的題目）。未作答為 NaN。"""
    tcols = [c for c in df.columns if c.startswith(C.TROUBLE_PREFIX)]
    scores = df[tcols].apply(lambda s: s.str.strip().map(C.TROUBLE_SCALE))
    scores.columns = [c[len(C.TROUBLE_PREFIX):].strip(" []") for c in tcols]
    return scores


def n_over3(scores):
    """每人在 13 題中「達 3 分以上」的題數。全題未作答者為 NaN。"""
    return (scores >= 3).sum(axis=1).where(scores.notna().any(axis=1))


def trouble_by_group(scores, groups, breadth, base_mask, note=ROLE_NOTE):
    """困擾 %≥3／%≥4 × 任意分群。分母＝該群該題實際作答人數；另附全體基準供對照。"""
    rows = []
    base = scores[base_mask]
    for gname, mask in groups:
        sub = scores[mask]
        for item in scores.columns:
            s = sub[item].dropna()
            if len(s) == 0:
                continue
            b = base[item].dropna()
            n3 = int((s >= 3).sum())
            p = (s >= 3).mean()
            base_p = (b >= 3).mean()
            rows.append({
                "分群": gname, "困難": item,
                "分子_達3以上": n3,
                "分母_作答人數": len(s), "群人數": int(mask.sum()),
                "達3以上比例": round(p, 4),
                "全體曾參與者比例": round(base_p, 4),
                # 分子 <5 時 lift 由 1–4 個人決定，只是雜訊，一律留空。
                # 這條政策必須與 multi_by_masks 一致——先前只在那裡實作，
                # 這裡漏掉，結果 21/65 列違反了本檔 docstring 自己寫的規則
                # （最糟：出資者「不知道怎麼管帳」以 2 人算出 lift 1.96，
                #  看起來像「出資者受財務行政困擾將近兩倍」）。
                "lift": (round(p / base_p, 2) if (base_p and n3 >= LIFT_MIN_NUMERATOR) else None),
                "lift留空原因": lift_blank_reason(n3),
                "分子_達4以上": int((s >= 4).sum()),
                "達4以上比例": round((s >= 4).mean(), 4),
                "平均分_次要": round(s.mean(), 2),
                "該群平均角色廣度": round(breadth[mask].mean(), 2),
                "信賴度": C.subgroup_confidence(len(s)),
                "決策可用性": usability(len(s)),
                "達3定義": TROUBLE_DEF,
                "讀法說明": note,
                "平均分警語": C.TROUBLE_CAVEAT,
            })
    return pd.DataFrame(rows)


def load_by_group(scores, groups, breadth, note=ROLE_NOTE, split_col=None):
    """
    困擾「負荷」：13 題中達 3 分以上的題數，用平均與中位數描述。

    note：寫進 CSV 的讀法說明。角色群用 ROLE_NOTE（重疊、無序），
    角色廣度用 BREADTH_NOTE，參與深度用 DEPTH_NOTE——同一張表被單獨取用時
    警語不能張冠李戴（曾發生過：廣度表誤掛角色的「重疊、不可讀順序」警語）。

    split_col：若分群來自兩套不同切法，傳入 {分群名: 切法標籤} 以產生「切法」欄，
    避免不同切法的人數被相加（同一批人被切兩次，相加會超過總人數）。
    """
    v_all = n_over3(scores)
    rows = []
    for gname, mask in groups:
        v = v_all[mask].dropna()
        if len(v) == 0:
            continue
        row = {"分群": gname}
        if split_col:
            row["切法"] = split_col.get(gname, "")
        row.update({
            "人數": len(v),
            "達3分以上題數_平均": round(v.mean(), 2),
            "達3分以上題數_中位數": float(v.median()),
            "達3分以上題數_最大": int(v.max()),
            "一題都沒達3分以上的人數": int((v == 0).sum()),
            "該群平均角色廣度": round(breadth[mask].mean(), 2),
            "信賴度": C.subgroup_confidence(len(v)),
            "決策可用性": usability(len(v)),
            "達3定義": TROUBLE_DEF,
            "讀法說明": note,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def multi_by_masks(df, col, groups, breadth, valid_opts):
    """
    複選題 × 可重疊分群 → 分子／分母／群內比例／全體比例／lift。

    valid_opts：正式選項清單。清單外的自由填答一律收斂成「其他（自由填答）」——
    未收斂時 n=1 的個人語句（例如「累了」）會與正式選項並排，還會算出誇張的 lift。

    ⚠️ 收斂後必須去重。bucket_freetext 把所有非正式選項映到同一個字串，若某人的
       自由填答本身含分隔字串「, 」（例如「自己的存款, 朋友借的場地」），
       explode_multi 會把它切成多個 token 而全部收斂成同一選項，該人就對同一選項
       貢獻多票——pct_table 的「單一選項票數＝人數」不變式因此失效，
       群內比例可能 >1（實測：票數 2／分母 1／比例 2.0）。
    """
    valid = set(valid_opts)

    def normalize(v):
        opts = [o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()]
        # dict.fromkeys 去重且保留原順序
        return C.MULTI_SELECT_SEP.join(dict.fromkeys(C.bucket_freetext(opts, valid)))

    d = df.copy()
    d[col] = d[col].apply(normalize)
    base = C.pct_table(d, col).set_index("選項")["比例"].to_dict()
    rows = []
    for gname, mask in groups:
        sub = d[mask]
        denom = int((sub[col].astype(str).str.strip() != "").sum())
        if denom == 0:
            continue
        long = C.explode_multi(sub, col)
        vc = long["選項"].value_counts() if not long.empty else pd.Series(dtype=int)
        for opt in base:
            n = int(vc.get(opt, 0))
            p = n / denom
            rows.append({
                "分群": gname, "選項": opt,
                "分子": n, "分母_作答人數": denom, "群人數": int(mask.sum()),
                "群內比例": round(p, 4), "全體比例": round(base[opt], 4),
                "lift": (round(p / base[opt], 2)
                         if (base[opt] and n >= LIFT_MIN_NUMERATOR) else None),
                "lift留空原因": lift_blank_reason(n),
                "該群平均角色廣度": round(breadth[mask].mean(), 2),
                "信賴度": C.subgroup_confidence(denom),
                "決策可用性": usability(denom),
                "讀法說明": ROLE_NOTE + " " + MULTI_NOTE,
            })
    return pd.DataFrame(rows)


def guard(condition, message):
    """守門檢查。用 raise 而非 assert——`python -O` 會停用 assert，守門就失效了。"""
    if not condition:
        raise ValueError(f"守門檢查失敗：{message}")


def main():
    df = C.load_clean()
    idx = pd.read_csv(C.TABLE_DIR / "01_衍生變項.csv", index_col=0,
                      keep_default_na=False, dtype=str)
    breadth = pd.to_numeric(idx["角色廣度"], errors="coerce")

    contacted = df[C.LAYER].isin([C.L_AWARE, C.L_DONE])       # 101 人，角色題作答範圍
    done = df[C.LAYER] == C.L_DONE                            # 47 人，專案層級題作答範圍
    scores = trouble_scores(df)
    all_masks = role_masks(df)

    # ---------- 守門 1：01_衍生變項.csv 必須與現在的原始資料是同一批人 ----------
    # 01_衍生變項.csv 是快取產物，且它的索引是「當時的列序」而非穩定的填答者 ID。
    # 問卷持續收案，一旦原始資料更新而這份沒重跑，索引就會指到不同的人。
    # pandas 按 index label 對齊，單純重排列序不會出錯，但陳舊的檔案會——所以要對帳。
    guard(len(idx) == len(df), f"01_衍生變項.csv 有 {len(idx)} 列，原始資料有 {len(df)} 列，請重跑 01_indices.py")
    guard(set(idx.index) == set(df.index), "01_衍生變項.csv 的索引與原始資料不一致，請重跑 01_indices.py")
    guard((idx["入坑分層"] == df[C.LAYER]).all(), "入坑分層對不上，01_衍生變項.csv 已過期，請重跑 01_indices.py")
    # ⚠️ 以下兩處刻意避開會拋 pandas 原生例外的寫法。守門的目的是給出「該重跑 01_indices.py」
    #    這個可執行的補救指示；若比較本身先炸掉（dropna 後索引不同 → ValueError:
    #    Can only compare identically-labeled Series objects；to_numeric 遇空字串 →
    #    ValueError: Unable to parse string），使用者就只看到 pandas 訊息，看不到補救指示。
    for short, mask in all_masks:
        flag = pd.to_numeric(idx[f"角色_{short}"], errors="coerce").fillna(0).astype(bool)
        guard(flag.reindex(df.index).equals(mask.reindex(df.index)),
              f"角色_{short} 旗標與原始資料對不上，請重跑 01_indices.py")
    # Series.equals 視 NaN==NaN 為相等，故未作答者（兩邊皆 NaN）不會誤判為不符
    cached = pd.to_numeric(idx["困擾_達3項數"], errors="coerce").astype(float)
    guard(cached.reindex(df.index).equals(n_over3(scores).astype(float).reindex(df.index)),
          "困擾_達3項數對不上，請重跑 01_indices.py")
    print("✓ 01_衍生變項.csv 與原始資料逐列對帳通過（分層、5 個角色旗標、困擾達標題數）")

    # ---------- 守門 2：角色人數要與既有輸出相符（讀檔比對，不是跟寫死的常數比）----------
    ref = pd.read_csv(C.TABLE_DIR / "03_全體_角色勾選.csv")
    ref_n = {C.ROLE_SHORT[r]: int(ref.loc[ref["選項"] == r, "票數"].iloc[0])
             for r in C.ROLE_LADDER}
    for short, mask in all_masks:
        got = int((mask & contacted).sum())
        guard(got == ref_n[short],
              f"角色「{short}」人數 {got} ≠ 03_全體_角色勾選.csv 的 {ref_n[short]}")
    print(f"✓ 角色人數與 03_全體_角色勾選.csv 讀檔比對相符：{ref_n}")

    # ---------- 樣本規模的絆線（與下面的切法檢查是兩件不同的事）----------
    # 問卷持續收案。這條不是在驗程式對錯，而是提醒「報告基準已變動」。
    # 切法檢查一律拿 n_done 比，不拿 47——否則資料一成長，切法檢查會全部失敗，
    # 而錯誤訊息會把原因誤指成「切法漏人」，實際上切法完全正確。
    n_done = int(done.sum())
    REPORT_BASELINE_N = 47
    guard(n_done == REPORT_BASELINE_N,
          f"曾參與層人數已從報告基準 {REPORT_BASELINE_N} 變成 {n_done}——"
          f"程式本身沒問題，但報告內所有以 {REPORT_BASELINE_N} 為分母的數字都需重新確認。"
          f"確認完請更新本檔的 REPORT_BASELINE_N，並重跑 06_number_index.py")

    # 交叉分析的分群：角色（限縮在曾參與層）＋ 角色廣度 ＋ 參與深度
    role_groups = [(s, m & done) for s, m in all_masks]
    breadth_two = [(name, done & breadth.between(lo, hi)) for name, (lo, hi) in BREADTH_GROUPS]
    breadth_each = [(f"{int(b)} 種角色", done & (breadth == b))
                    for b in sorted(breadth.dropna().unique())]
    depth_groups = [(lbl, done & (idx["參與深度"] == lbl)) for lbl in C.DEPTH_LABEL.values()]

    # ---------- 守門 3：互斥切法必須剛好切完曾參與者，一個都不漏 ----------
    # 比較對象是 n_done 而不是寫死的數字：這道檢查要驗的是「切法有沒有漏人」，
    # 與「樣本規模有沒有變」是兩個不同的問題，分開檢查訊息才不會誤導。
    for label, groups_ in [("角色廣度二分組", breadth_two),
                           ("角色廣度逐級", breadth_each),
                           ("參與深度 5 級", depth_groups)]:
        total = sum(int(m.sum()) for _, m in groups_)
        hint = (f"（可能有人選「{C.DEPTH_ESCAPE}」，這些人不在 5 級量尺上）"
                if label == "參與深度 5 級" else "（可能有人的角色廣度為 0 或空值）")
        guard(total == n_done,
              f"{label} 合計 {total} ≠ 曾參與者 {n_done} 人，有人被漏掉{hint}")
    print(f"✓ 三套互斥切法各自剛好切完 {n_done} 位曾參與者（廣度二分、廣度逐級、參與深度 5 級）")

    # ---------- 1. 角色 × 困擾 ----------
    C.save_table(trouble_by_group(scores, role_groups, breadth, done), "10_角色×困擾",
                 "重疊、無序；信賴度 L2/L1 混合，逐列見「信賴度」與「決策可用性」欄")

    # ---------- 2. 困擾負荷：依角色、依廣度、依參與深度 ----------
    # 加一列全體曾參與者當基準，否則讀者沒有對照點
    baseline = [("（基準）全體曾參與者", done)]
    C.save_table(load_by_group(scores, baseline + role_groups, breadth),
                 "10_角色負荷_依角色", "13 題中達 3 分以上的題數；群體重疊、無深淺順序")

    split = {name: "二分組" for name, _ in BREADTH_GROUPS}
    split.update({name: "逐級" for name, _ in breadth_each})
    split["（基準）全體曾參與者"] = "基準"
    C.save_table(load_by_group(scores, baseline + breadth_two + breadth_each, breadth,
                               note=BREADTH_NOTE, split_col=split),
                 "10_角色負荷_依廣度", "「切法」欄區分二分組與逐級，兩套不可相加")

    depth_load = load_by_group(scores, baseline + depth_groups, breadth, note=DEPTH_NOTE)
    C.save_table(depth_load, "10_負荷_依參與深度5級", "互斥且有序；以中位數為主指標")

    # ---------- 3. 角色 × 資源、角色 × 動機 ----------
    role_done = [(s, m[done]) for s, m in role_groups]
    C.save_table(multi_by_masks(df[done], C.C_RESOURCES, role_done, breadth[done],
                                C.RESOURCE_OPTS), "10_角色×資源", "自由填答已收斂")
    for col, name in [(C.C_MOTIVE_FIRST, "初次動機"), (C.C_MOTIVE_NOW, "持續動機")]:
        C.save_table(multi_by_masks(df[done], col, role_done, breadth[done], C.MOTIVES),
                     f"10_角色×{name}", "自由填答已收斂")

    # ---------- 4. 重疊矩陣的人數版 ----------
    # 既有 03_角色重疊矩陣.csv 只有比例，無法直接核對分子。這裡補人數版並回頭比對比例。
    con = df[contacted]
    role_sets = [{o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()}
                 for v in con[C.C_ROLES]]
    OVERLAP_NOTE = ("讀法：分母＝勾了 A 的人數，比例＝這些人當中也勾了 B 的比例——方向不可反讀"
                    "（使用者→出資者 0.1889 是「勾使用者的人有 19% 也勾出資者」，"
                    "不是「19% 的出資者是使用者」，後者為 100%）。"
                    "五個角色**不是巢狀階梯**：勾發起者的人只有 82% 也勾使用者，"
                    "分母 90→17 遞減不可讀成漏斗。分母池＝101 位曾接觸者。")
    ov_rows = []
    for a in C.ROLE_LADDER:
        has_a = [s for s in role_sets if a in s]
        for b in C.ROLE_LADDER:
            n = sum(1 for s in has_a if b in s)
            ov_rows.append({
                "勾了A": C.ROLE_SHORT[a], "也勾了B": C.ROLE_SHORT[b],
                "分子": n, "分母_勾了A的人數": len(has_a),
                "在勾A的人當中也勾B的比例": round(n / len(has_a), 4) if has_a else None,
                "信賴度": C.subgroup_confidence(len(has_a)),
                "決策可用性": usability(len(has_a)),
                "讀法說明": OVERLAP_NOTE,
            })
    overlap = pd.DataFrame(ov_rows)
    C.save_table(overlap, "10_角色重疊_人數版", "03_角色重疊矩陣.csv 的分子/分母版，供逐格核對")

    # ---------- 守門 4：比例要與既有矩陣對得上 ----------
    old = pd.read_csv(C.TABLE_DIR / "03_角色重疊矩陣.csv")
    for _, r in overlap.iterrows():
        old_v = old.loc[old["勾了（列）"] == r["勾了A"], f"也勾{r['也勾了B']}"].iloc[0]
        guard(abs(float(old_v) - r["在勾A的人當中也勾B的比例"]) < 1e-4,
              f"重疊比例不符：{r['勾了A']}→{r['也勾了B']} 本檔 "
              f"{r['在勾A的人當中也勾B的比例']} vs 既有 {old_v}")
    print("✓ 重疊矩陣人數版與既有 03_角色重疊矩陣.csv 逐格相符")

    # ---------- 5. 角色廣度 × 困擾負荷的序位相關 ----------
    # 03_序位相關_Spearman.csv 有「參與深度×困擾」與「投入強度×困擾」，獨缺「角色廣度×困擾」。
    pair = pd.concat([breadth, n_over3(scores).rename("困擾_達3項數")], axis=1).loc[done].dropna()
    rho, p = spearmanr(pair["角色廣度"], pair["困擾_達3項數"])
    sp = pd.DataFrame([{
        "變項A": "角色廣度（勾選角色數 1–5）", "變項B": "困擾_達3分以上題數（13 題中）",
        "N": len(pair), "N是誰": "曾參與專案的 47 人",
        "Spearman rho": round(rho, 3), "p值_未用於任何判讀": round(p, 4),
        "方向": "正向" if rho > 0 else "負向",
        "強度_教材四級": ("缺乏" if abs(rho) < 0.25 else "不強" if abs(rho) < 0.5
                     else "良好" if abs(rho) < 0.75 else "非常強"),
        "信賴度": C.subgroup_confidence(len(pair)),
        "決策可用性": usability(len(pair)),
        "讀法說明": ("相關不等於因果，本列不得用於任何因果宣稱；"
                 "p 值僅為計算副產物，報告未引用、不作顯著性宣稱。"
                 "強度四級門檻為 0.25／0.5／0.75，與 03_序位相關_Spearman.csv 一致。"),
    }])
    C.save_table(sp, "10_角色廣度×困擾_Spearman", "補 03_序位相關_Spearman.csv 缺的這一對")

    # ---------- 6. 逐人核對表 ----------
    # 讓 Claire 用 Excel 樞紐重算本檔**所有**表，不只彙總表——因此必須含
    # 13 題困擾原始分數與資源／動機的逐項旗標，否則 10_角色×困擾／資源／動機 無法覆核。
    CHECK_NOTE = ("用途：核對 10_*.csv 的每一個數字。分母池分兩種——角色欄涵蓋 101 位曾接觸者，"
                  "困擾／資源／動機欄只有 47 位曾參與者有值，**空白表示未被詢問，不是 0**"
                  "（若當 0 計入，使用者組的達3題數平均會從 2.41 掉到 1.04）。"
                  "「填答序號」是去識別化 CSV 的列序（0 起算、有跳號），不是 Excel 列號。")
    check = pd.DataFrame({
        "入坑分層": df[C.LAYER],
        "角色廣度": breadth,
        "參與深度": idx["參與深度"],
        "決策位置": idx["決策位置"],
        "專案階段_合併": idx["專案階段_合併"],
        "達3分以上題數": n_over3(scores),
    })
    for short, mask in all_masks:
        check[f"角色_{short}"] = mask.astype(int)
    for item in scores.columns:                       # 13 題原始分數
        check[f"困擾分數_{item}"] = scores[item]
    for opt in C.RESOURCE_OPTS:                       # 資源逐項旗標
        check[f"資源_{opt.split('（')[0]}"] = df[C.C_RESOURCES].apply(
            lambda v, o=opt: int(o in str(v).split(C.MULTI_SELECT_SEP)))
    for col, tag in [(C.C_MOTIVE_FIRST, "初次動機"), (C.C_MOTIVE_NOW, "持續動機")]:
        for m in C.MOTIVES:
            check[f"{tag}_{m}"] = df[col].apply(
                lambda v, m=m: int(m in str(v).split(C.MULTI_SELECT_SEP)))
    check = check[contacted].copy()
    # 專案層級的欄位只有曾參與者被問過，其餘留空（不是 0）——說明已寫進「讀法說明」欄。
    # 先轉 object 再填空字串，否則往 float 欄位塞字串會有 dtype 警告（未來版本會直接報錯）。
    proj_cols = [c for c in check.columns
                 if c.startswith(("困擾分數_", "資源_", "初次動機_", "持續動機_"))]
    is_done = done.reindex(check.index, fill_value=False)
    check[proj_cols] = check[proj_cols].astype(object).where(is_done, "")
    check["讀法說明"] = CHECK_NOTE
    check.index.name = "填答序號"
    C.save_table(check.reset_index(), "10_逐人核對表",
                 "含 13 題困擾原始分數與資源／動機旗標，可重算本檔所有表")

    # ---------- 摘要 ----------
    pd.set_option("display.width", 220, "display.max_colwidth", 30)
    cols = ["分群", "人數", "達3分以上題數_平均", "達3分以上題數_中位數",
            "達3分以上題數_最大", "該群平均角色廣度", "決策可用性"]
    print("\n=== 困擾負荷（13 題中達 3 分以上的題數）｜角色：重疊、無序 ===")
    print(load_by_group(scores, baseline + role_groups, breadth)[cols].to_string(index=False))
    print("※ 五個角色群互相重疊、且無深淺順序，不可讀成梯度。")

    print("\n=== 同一指標｜角色廣度二分組：互斥、有序 ===")
    print(load_by_group(scores, breadth_two, breadth)[cols].to_string(index=False))

    print("\n=== 同一指標｜參與深度 5 級：互斥、有序（主動權由低到高）===")
    print(depth_load[cols].to_string(index=False))
    print("※ 以中位數為主指標：「接收資訊」平均 3.00 但中位數 1.0、最大 10，係單一個案拉動。")

    print(f"\n=== 角色廣度 × 困擾負荷 Spearman：rho={rho:.3f}"
          f"（N={len(pair)}，{sp['強度_教材四級'].iloc[0]}）；相關≠因果 ===")

    print("\n=== 出資者的重疊結構（分母＝勾「出錢或調度資源」的 17 人）===")
    fund = overlap[overlap["勾了A"] == "出資者"]
    print(fund[["也勾了B", "分子", "分母_勾了A的人數",
                "在勾A的人當中也勾B的比例"]].to_string(index=False))


if __name__ == "__main__":
    main()
