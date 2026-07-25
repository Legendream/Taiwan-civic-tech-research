# -*- coding: utf-8 -*-
"""
03_crosstab.py — 交叉分析。

原則（依計畫第三節）：
  · 一律輸出「群內比例（分子/分母）」，不只有百分比
  · N=47 撐不起 5 分格 → 階段收成 4 類、參與深度收成 2 類
  · 年齡分析用「條件比例＋lift」，去除年齡本身樣本分布的影響
  · 每格人數過小，**不做顯著性檢定**（卡方期望值 <5），只報方向、全標 L1
  · Spearman 只用於序位對序位，且僅報方向

輸出：分析結果/03_*.csv

執行：python3 03_crosstab.py
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common as C


def multi_by_group(df, col, group_col, group_order=None, min_n=1):
    """
    複選題 × 分群 → 長表：分群 / 選項 / 分子 / 分母 / 群內比例 / lift / 信賴度。
    分母＝該分群中「有作答該題」的人數。lift＝群內比例 ÷ 全體比例。
    """
    base = C.pct_table(df, col).set_index("選項")["比例"].to_dict()
    groups = group_order or [g for g in df[group_col].unique() if str(g).strip()]
    rows = []
    for g in groups:
        sub = df[df[group_col] == g]
        denom = int((sub[col].astype(str).str.strip() != "").sum())
        if denom < min_n:
            continue
        counts = C.explode_multi(sub, col)
        vc = counts["選項"].value_counts() if not counts.empty else pd.Series(dtype=int)
        for opt in base:
            n = int(vc.get(opt, 0))
            p = n / denom if denom else np.nan
            rows.append({
                "分群": g, "選項": opt, "分子": n, "分母": denom,
                "群內比例": round(p, 4),
                "全體比例": round(base[opt], 4),
                "lift": round(p / base[opt], 2) if base[opt] else np.nan,
                "信賴度": C.subgroup_confidence(denom),
            })
    return pd.DataFrame(rows)


def trouble_table(df, idx, group_col=None):
    """困擾題：主指標 %≥3、%≥4；平均分為次要並附註低估。"""
    tcols = [c for c in df.columns if c.startswith(C.TROUBLE_PREFIX)]
    scores = df[tcols].apply(lambda s: s.str.strip().map(C.TROUBLE_SCALE))
    scores.columns = [c[len(C.TROUBLE_PREFIX):].strip(" []") for c in tcols]
    done = df[C.LAYER] == C.L_DONE
    rows = []
    if group_col is None:
        groups = [("全體曾參與者", done)]
    else:
        groups = [(g, done & (idx[group_col] == g))
                  for g in idx.loc[done, group_col].dropna().unique() if str(g).strip()]
    for gname, mask in groups:
        sub = scores[mask]
        group_n = len(sub)
        for item in scores.columns:
            s = sub[item].dropna()
            # 分母一律用「實際算比例時的分母」＝該列有作答的人數。
            # 先前寫成群人數，一旦有人漏答，「分子/分母」就算不出所寫的比例，
            # 整份報告的可追溯性就破了。
            denom = len(s)
            rows.append({
                "分群": gname, "困難": item, "分母": denom, "群人數": group_n,
                "達3以上_分子": int((s >= 3).sum()), "達3以上比例": round((s >= 3).mean(), 4),
                "達4以上_分子": int((s >= 4).sum()), "達4以上比例": round((s >= 4).mean(), 4),
                "平均分_次要": round(s.mean(), 2),
                "信賴度": C.subgroup_confidence(denom),
                # 警語直接寫進 CSV：這幾張表常被單獨取用，只 print 到 stdout 看不到
                "平均分警語": C.TROUBLE_CAVEAT,
            })
    return pd.DataFrame(rows)


def main():
    df = C.load_clean()
    idx = pd.read_csv(C.TABLE_DIR / "01_衍生變項.csv", index_col=0, keep_default_na=False,
                      dtype={"參與深度": str, "決策位置": str, "最深角色": str, "年齡": str})
    for c in ["參與深度序位", "投入強度序位", "角色廣度", "最深角色階", "活躍度序位",
              "困擾_平均", "困擾_達3項數", "困擾_達4項數"]:
        idx[c] = pd.to_numeric(idx[c], errors="coerce")
    df = df.join(idx[["參與深度", "決策位置", "最深角色", "專案階段_合併", "投入時數"]])
    # 年齡：全體分布用原始 5 層；交叉分析用收合 3 層，避免 N=2 的格子產生假訊號
    df["年齡_合併"] = df[C.C_AGE].str.strip().map(C.AGE_COARSE)

    # ---------- 1. 資源 × 專案階段 ----------
    res_stage = multi_by_group(df, C.C_RESOURCES, "專案階段_合併", C.STAGE_COARSE_ORDER)
    C.save_table(res_stage, "03_資源×專案階段", "曾參與 N=47，全部 L1 方向觀察")

    # ---------- 2. 資源 × 決策位置 ----------
    res_depth = multi_by_group(df, C.C_RESOURCES, "決策位置", ["方向決策者", "執行協力者"])
    C.save_table(res_depth, "03_資源×決策位置", "僅曾參與者有作答")

    # ---------- 3. 困擾 ----------
    # 五級完整分布：讓任何人都能自己驗證 %≥3 是怎麼加出來的
    # （%≥3 常被誤讀成「只算給 3 分的人」，攤開分布是最直接的澄清）
    tcols = [c for c in df.columns if c.startswith(C.TROUBLE_PREFIX)]
    done_df = df[df[C.LAYER] == C.L_DONE]
    dist_rows = []
    for c in tcols:
        vals = done_df[c].str.strip().map(C.TROUBLE_SCALE)
        row = {"困難": c[len(C.TROUBLE_PREFIX):].strip(" []")}
        for score, label in sorted((v, k) for k, v in C.TROUBLE_SCALE.items()):
            row[f"{score}分_{label.split('：')[1]}"] = int((vals == score).sum())
        row["合計"] = int(vals.notna().sum())
        row["3分以上_合計"] = int((vals >= 3).sum())
        row["3分以上_比例"] = round((vals >= 3).mean(), 4)
        row["4分以上_合計"] = int((vals >= 4).sum())
        row["4分以上_比例"] = round((vals >= 4).mean(), 4)
        dist_rows.append(row)
    dist = pd.DataFrame(dist_rows).sort_values("3分以上_比例", ascending=False)
    C.save_table(dist, "03_困擾_五級分布",
                 "每題 1–5 分各有幾人；3分以上＝3+4+5 三格相加，可自行核對")

    C.save_table(trouble_table(df, idx), "03_困擾_全體")
    C.save_table(trouble_table(df, idx, "專案階段_合併"), "03_困擾×專案階段")
    C.save_table(trouble_table(df, idx, "決策位置"), "03_困擾×決策位置")
    # 參與深度是完整的 5 級序位（問卷為單選、主動權由低到高），
    # 二分成「決策位置」是為了交叉表的格子大小，但不該因此丟掉 5 級的資訊。
    # 5 級版一併輸出：它顯示「發起專案」與「共創解法」之間仍有明顯落差，
    # 這個落差會被二分版抹平。各格 5–18 人，L1。
    C.save_table(trouble_table(df, idx, "參與深度"), "03_困擾×參與深度5級",
                 "曾參與層各深度 n=5/6/8/18/10，全部 L1；二分版見 03_困擾×決策位置")
    C.save_table(multi_by_group(df, C.C_RESOURCES, "參與深度",
                                list(C.DEPTH_LABEL.values())), "03_資源×參與深度5級",
                 "同上，5 級完整版")

    # ---------- 4. 年齡 × 動機（條件比例＋lift）----------
    for col, name in [(C.C_MOTIVE_FIRST, "初次動機"), (C.C_MOTIVE_NOW, "持續動機")]:
        done_only = df[df[C.LAYER] == C.L_DONE]
        t = multi_by_group(done_only, col, "年齡_合併", C.AGE_COARSE_ORDER)
        C.save_table(t, f"03_年齡×{name}_lift",
                     "年齡收合為 3 層（10/19/18 人）；條件比例＋lift；不做顯著性檢定")
        # 原始 5 層版一併保留供追溯，但因含 N=2 的格，不作為結論依據
        C.save_table(multi_by_group(done_only, col, C.C_AGE, C.AGE_ORDER),
                     f"03_年齡×{name}_lift_原始5層",
                     "含 N=2 的年齡層，僅供追溯，不作結論依據")

    # ---------- 5. 年齡 × 投入強度、年齡 × 活動意願 ----------
    done_mask = df[C.LAYER] == C.L_DONE
    hours = pd.crosstab(df.loc[done_mask, C.C_AGE], df.loc[done_mask, "投入時數"])
    hours_pct = hours.div(hours.sum(axis=1), axis=0).round(3)
    out = hours.stack().rename("分子").reset_index().merge(
        hours_pct.stack().rename("群內比例").reset_index(),
        on=[C.C_AGE, "投入時數"])
    out["分母"] = out[C.C_AGE].map(hours.sum(axis=1))
    out["信賴度"] = out["分母"].apply(C.subgroup_confidence)
    C.save_table(out, "03_年齡×投入強度")

    C.save_table(multi_by_group(df, C.C_EVENTS, "年齡_合併", C.AGE_COARSE_ORDER),
                 "03_年齡×活動意願_lift", "全體 N=127，年齡收合為 3 層")

    # ---------- 6. 三層 × 需求題（領域／工具／活動）----------
    for col, name in [(C.C_DOMAINS, "議題領域"), (C.C_TOOLS, "跨領域工具"), (C.C_EVENTS, "活動意願")]:
        C.save_table(multi_by_group(df, col, C.LAYER, C.LAYER_ORDER), f"03_三層×{name}")
        C.save_table(C.pct_table(df, col), f"03_全體_{name}")

    # ---------- 7. 生態系：管道、地區、身分、未參與原因 ----------
    for col, name in [(C.C_G0V_CHANNEL, "g0v消息管道"), (C.C_INFO_CHANNEL, "公民科技資訊管道"),
                      (C.C_REGION, "居住地"), (C.C_G0V_EVENTS, "g0v活動類型")]:
        C.save_table(C.pct_table(df, col), f"03_全體_{name}")
        C.save_table(multi_by_group(df, col, C.LAYER, C.LAYER_ORDER), f"03_三層×{name}")

    # ⚠ 此題分支到「從未接觸」層（26 人全數作答），不是「接觸未參與」層。
    #    被選為主要服務對象的「接觸未參與」54 人，問卷沒問過他們為何沒投入——報告限制章須寫明。
    never = df[df[C.LAYER] == C.L_NEVER]
    # 自由填答收斂成「其他」：原句過長、且有受訪者自述個人狀態，不適合整句上圖
    NOT_JOIN_OPTS = {
        "不知道怎麼加入、找不到入口", "不知道有哪些專案或議題",
        "覺得要會寫程式、技術門檻太高", "身邊沒有人帶，怕自己融不進去、或幫不上忙",
        "沒有時間", "還沒遇到讓我想投入的議題", "覺得參與好像也改變不了什麼",
    }
    never = never.copy()
    never[C.C_NOT_JOIN_WHY] = never[C.C_NOT_JOIN_WHY].apply(
        lambda v: C.MULTI_SELECT_SEP.join(C.bucket_freetext(
            [o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()], NOT_JOIN_OPTS)))
    nj = C.pct_table(never, C.C_NOT_JOIN_WHY)
    assert nj["分母"].iloc[0] == 26, f"未參與原因分母應為 26，實得 {nj['分母'].iloc[0]}"
    assert (df.loc[df[C.LAYER] != C.L_NEVER, C.C_NOT_JOIN_WHY].str.strip() == "").all(), \
        "「從未接觸」以外的層不應有未參與原因作答"
    C.save_table(nj, "03_未參與原因", "分母=26（從未接觸層全數作答），L1；接觸未參與層未被問此題")

    for col, name in [(C.C_IDENTITY, "身分"), (C.C_AGE, "年齡"), (C.C_GENDER, "性別")]:
        t = df[col].value_counts().rename_axis(name).reset_index(name="人數")
        t["分母"] = len(df)
        t["比例"] = (t["人數"] / len(df)).round(4)
        C.save_table(t, f"03_全體_{name}分布")

    # ---------- 7.5 角色：勾選率、廣度、重疊矩陣 ----------
    contacted = df[df[C.LAYER] != C.L_NEVER]
    C.save_table(C.pct_table(contacted, C.C_ROLES), "03_全體_角色勾選",
                 "分母=101 位曾接觸者")

    # 重疊矩陣：勾了「列角色」的人當中，也勾了「欄角色」的比例。
    # 這張表就是用來檢驗「角色階梯是不是巢狀」——若是巢狀，下三角應全為 1.00。
    role_sets = [{o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()}
                 for v in contacted[C.C_ROLES]]
    ov_rows = []
    for a in C.ROLE_LADDER:
        has_a = [st for st in role_sets if a in st]
        row = {"勾了（列）": C.ROLE_SHORT[a], "該角色人數": len(has_a)}
        for b in C.ROLE_LADDER:
            row[f"也勾{C.ROLE_SHORT[b]}"] = (
                round(sum(1 for st in has_a if b in st) / len(has_a), 4) if has_a else None)
        ov_rows.append(row)
    C.save_table(pd.DataFrame(ov_rows), "03_角色重疊矩陣",
                 "列＝勾了該角色的人；值＝其中也勾了欄角色的比例。若為巢狀階梯，下三角應全 1.00")

    # 角色廣度分布
    breadth = idx["角色廣度"].dropna().astype(int).value_counts().sort_index()
    bt = pd.DataFrame({"勾選角色數": breadth.index, "人數": breadth.values})
    bt["分母"] = len(contacted)
    bt["比例"] = (bt["人數"] / len(contacted)).round(4)
    C.save_table(bt, "03_角色廣度分布", "分母=101（其中 99 人有有效角色）")

    # ---------- 8. 出資者 ----------
    funder = df[df[C.C_FUNDED].str.strip() == "有"]
    C.save_table(C.pct_table(funder, C.C_FUND_CRITERIA), "03_出資者_評估準則", "N=27，L1")
    C.save_table(C.pct_table(funder, C.C_FUND_HARDEST), "03_出資者_資源沙漠階段", "N=27，L1")

    # ---------- 9. Spearman（序位對序位，只報方向）----------
    pairs = [("參與深度序位", "投入強度序位"), ("角色廣度", "投入強度序位"),
             ("參與深度序位", "角色廣度"), ("參與深度序位", "困擾_達3項數"),
             ("投入強度序位", "困擾_達3項數"), ("角色廣度", "活躍度序位")]
    rows = []
    for a, b in pairs:
        sub = idx[[a, b]].dropna()
        if len(sub) < 10:
            continue
        rho, p = spearmanr(sub[a], sub[b])
        rows.append({"變項A": a, "變項B": b, "N": len(sub), "Spearman rho": round(rho, 3),
                     "p值_未用於任何判讀": round(p, 4),
                     "方向": "正向" if rho > 0 else "負向",
                     "強度_教材四級": ("缺乏" if abs(rho) < 0.25 else "不強" if abs(rho) < 0.5
                                  else "良好" if abs(rho) < 0.75 else "非常強"),
                     "信賴度": C.subgroup_confidence(len(sub))})
    sp = pd.DataFrame(rows)
    C.save_table(sp, "03_序位相關_Spearman",
                 "相關≠因果；N<50 僅 L1。p 值欄僅為計算副產物，報告未引用、不作顯著性宣稱")

    # ---------- 摘要輸出 ----------
    pd.set_option("display.width", 200, "display.max_colwidth", 34, "display.max_rows", 100)
    print("\n=== 困擾題（全體曾參與者 N=47，依 %≥3 排序）===")
    tr = trouble_table(df, idx).sort_values("達3以上比例", ascending=False)
    print(tr[["困難", "達3以上_分子", "分母", "達3以上比例", "達4以上_分子", "平均分_次要"]].to_string(index=False))
    print(f"※ {C.TROUBLE_CAVEAT}")

    print("\n=== 序位相關（Spearman）===")
    print(sp.to_string(index=False))

    print("\n=== 資源 × 專案階段（群內比例）===")
    piv = res_stage.pivot(index="選項", columns="分群", values="群內比例")
    piv = piv.reindex(columns=[c for c in C.STAGE_COARSE_ORDER if c in piv.columns])
    print((piv * 100).round(0).astype("Int64").to_string())
    print("分母：" + "、".join(
        f"{g}={res_stage.loc[res_stage['分群'] == g, '分母'].iloc[0]}"
        for g in piv.columns))


if __name__ == "__main__":
    main()
