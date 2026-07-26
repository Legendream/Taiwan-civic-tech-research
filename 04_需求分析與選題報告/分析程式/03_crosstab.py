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

    自由填答的收斂**不在這裡做**，而是在 main() 開頭對整個 df 一次做完（見 normalize_freetext）。
    原因：03_全體_* 那批表走的是 C.pct_table 而不是本函式，只在本函式裡收斂會漏掉一半的輸出。

    lift 一律經 common.lift_or_blank：分子少於 common.LIFT_MIN_NUMERATOR 就留空。
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
                "lift": C.lift_or_blank(p, base[opt], n),
                "lift留空原因": C.lift_blank_reason(n),
                "信賴度": C.subgroup_confidence(denom),
            })
    return pd.DataFrame(rows)


def normalize_freetext(df):
    """
    對所有「有正式選項清單」的複選題，一次收斂自由填答並去重（見 common.VALID_OPTS）。

    在 main() 開頭做，而不是在各分析函式裡做——因為 03_全體_* 走 C.pct_table、
    03_三層×* 走 multi_by_group，分頭處理必然會漏掉一邊。

    兩道守門：
      · 清單裡的每個選項都必須真的出現在資料中 → 擋打錯字（打錯會讓正式選項被誤併成「其他」）
      · 列出資料中不在清單裡的值 → 讓人確認那些真的是自由填答，不是漏列的正式選項
    """
    df = df.copy()
    for col, opts in C.VALID_OPTS.items():
        seen = set()
        for v in df[col]:
            seen.update(o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip())
        missing = [o for o in opts if o not in seen]
        if missing:
            raise ValueError(
                f"守門檢查失敗：VALID_OPTS 中這些選項在資料裡找不到（可能打錯字，"
                f"也可能真的 0 人選）：{missing}｜題目：{col[:24]}…")
        extra = sorted(seen - set(opts))
        if extra:
            print(f"  · {col[:20]}… 收斂 {len(extra)} 種自由填答 → 其他（自由填答）：{extra}")
        df[col] = df[col].apply(lambda v, o=opts: C.bucket_and_dedupe(v, o))
    return df


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

    # 自由填答一次收斂完，之後所有輸出（pct_table 與 multi_by_group 兩條路）都一致
    print("自由填答收斂：")
    df = normalize_freetext(df)

    # ---------- 0. 資源與專長：全體曾參與者 ----------
    # 這兩張表原本不存在，報告第 5 章與 5.1 節卻各引用了一整組數字（人脈 31/47、
    # 議題研究 24/47 等）。缺表等於缺追溯：稽核只能重算算術，無法確認分子分母
    # 取自正確的題目與群體，而那正是 61/126 那類錯誤的存活空間。
    # 分母＝該題有作答的人數（＝曾參與的 47 人，只有他們被問到這兩題）。
    done_only_df = df[df[C.LAYER] == C.L_DONE]
    for col, name, extra in [
            (C.C_RESOURCES, "資源", "複選，票數即人數，不同選項的票數不可相加"),
            (C.C_SKILLS, "專長", "問的是「在這個專案裡負責什麼」，不是「你會什麼」")]:
        tbl = C.pct_table(done_only_df, col)
        # 分母由程式推導（該題實際有作答的人數），不寫死 47：問卷持續開放填答，
        # 日後若有曾參與者跳過這一題，寫死的說明就會與 CSV 的分母欄打架。
        n = int(tbl["分母"].iloc[0]) if len(tbl) else 0
        C.save_table(tbl, f"03_全體_{name}", f"分母={n} 位曾參與者；{extra}")

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

    # g0v 參加經驗：報告第 1 章「公民科技不等於 g0v」整段都靠這一題。
    # ⚠️ 這一題就是 61/126 那個錯誤的現場。當時報告寫「48%（61/126）從來沒參加過任何
    #    g0v 活動」，數字取自**分支題**「承上，你參加過哪些 g0v 活動？」的選項列
    #    （只有 126 人作答）；該講的是這一題「最近一次參加是什麼時候」，127 人全數作答、
    #    60 人選「我沒參加過」。算術自洽讓稽核放行，錯的是取自哪一題。
    #    數字已於 PR #7 修正為 47%（60/127），但一直沒有對應的輸出表，
    #    追溯鏈仍是斷的——這裡補上，讓它以後查得到來源。
    G0V_NEVER_VALUE = "我沒參加過 g0v 的活動"
    _g0v_vals = set(df[C.C_G0V_LAST].str.strip())
    assert G0V_NEVER_VALUE in _g0v_vals, (
        f"守門檢查失敗：g0v 最近一次參加題找不到選項「{G0V_NEVER_VALUE}」。"
        f"實際出現的值：{sorted(_g0v_vals)}。"
        "表單選項文字若改過，這裡會靜默算成 0 人，必須先確認再改常數。")
    g0v_never = df[C.C_G0V_LAST].str.strip() == G0V_NEVER_VALUE
    g0v_rows = []
    for gname, mask in [("全體", pd.Series(True, index=df.index)),
                        (C.L_DONE, df[C.LAYER] == C.L_DONE)]:
        denom = int(mask.sum())
        n = int((g0v_never & mask).sum())
        g0v_rows.append({"分群": gname, "類別": "從未參加過任何 g0v 活動",
                         "分子": n, "分母": denom, "比例": round(n / denom, 4),
                         "信賴度": C.confidence(denom) if denom >= 120
                                 else C.subgroup_confidence(denom)})
    # 跳過「我沒參加過」：它已經是上面「從未參加過任何 g0v 活動」那一列，
    # 重複輸出會讓索引出現兩列同分子同分母、名稱卻不同的候選，替後續的來源比對製造歧義。
    dist = df[C.C_G0V_LAST].str.strip().value_counts()
    for k, v in dist.items():
        if k == G0V_NEVER_VALUE:
            continue
        g0v_rows.append({"分群": "全體", "類別": f"最近一次參加：{k}",
                         "分子": int(v), "分母": len(df), "比例": round(v / len(df), 4),
                         "信賴度": C.confidence(len(df))})
    C.save_table(pd.DataFrame(g0v_rows), "03_全體_g0v參加經驗",
                 "來源是「最近一次參加 g0v 活動是什麼時候」（127 人全數作答），"
                 "不是分支題「你參加過哪些 g0v 活動」（僅 126 人作答）")

    # 管道：官方 vs 親友的互斥四分組。
    # 報告第 7 章整整兩張表都建立在這組數字上，先前卻沒有任何表可以追溯，
    # 只存在於報告正文。這是複選題最容易出錯的地方：把「至少勾了官方任一項的人數」
    # 寫成各官方選項票數相加（會把同時勾多項的人重複計）。
    # 這裡一律以「人」為單位去重計算，並讓四組相加必須等於分母。
    OFFICIAL_CHANNELS = [
        "g0v 社群管道（FB_Threads_Instgram)",
        "g0v Slack",
        "揪松團每月電子報",
        "揪松團 LINE 群組",
        "社群活動資訊彙整網頁（https://g0v.hackmd.io/@jothon/event）",
    ]
    FRIEND_CHANNEL = "親友推薦"
    NO_CHANNEL = "都沒有，我之前不太清楚這些管道"
    # 守門：OFFICIAL_CHANNELS 是這裡寫死的，而正式選項的權威來源是 common.VALID_OPTS。
    # 兩者一旦失去同步（例如日後新增一個官方管道），只用該新管道的人會被歸進
    # 「兩者都沒有」，官方觸及率靜默低估，而下面的分割檢查完全看不出來。
    _known = set(OFFICIAL_CHANNELS) | {FRIEND_CHANNEL, NO_CHANNEL, C.FREETEXT_BUCKET}
    _missing = set(C.VALID_OPTS[C.C_G0V_CHANNEL]) - _known
    assert not _missing, (
        f"守門檢查失敗：g0v 消息管道有正式選項沒被歸類成官方／親友／都沒有：{sorted(_missing)}。"
        "請更新 OFFICIAL_CHANNELS，否則官方管道觸及率會被低估。")
    ch_rows = []
    for gname, sub in [("全體", df), (C.L_DONE, df[df[C.LAYER] == C.L_DONE])]:
        picked = [{o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()}
                  for v in sub[C.C_G0V_CHANNEL]]
        denom = len(picked)
        has_off = [bool(p & set(OFFICIAL_CHANNELS)) for p in picked]
        has_fri = [FRIEND_CHANNEL in p for p in picked]
        cats = [
            ("至少用到一個官方管道", sum(has_off)),
            ("有靠親友推薦", sum(has_fri)),
            ("只有官方管道", sum(o and not f for o, f in zip(has_off, has_fri))),
            ("官方與親友都有", sum(o and f for o, f in zip(has_off, has_fri))),
            ("只靠親友推薦，沒有任何官方管道", sum(f and not o for o, f in zip(has_off, has_fri))),
            ("兩者都沒有", sum((not o) and (not f) for o, f in zip(has_off, has_fri))),
        ]
        for label, n in cats:
            ch_rows.append({
                "分群": gname, "類別": label, "分子": n, "分母": denom,
                "比例": round(n / denom, 4),
                "互斥四分組": label in ("只有官方管道", "官方與親友都有",
                                    "只靠親友推薦，沒有任何官方管道", "兩者都沒有"),
                "信賴度": C.confidence(denom) if denom >= 120 else C.subgroup_confidence(denom),
            })
        # 註：四組由 (has_off, has_fri) 的 2×2 組合定義，相加必然等於分母，
        # 檢查它是恆真的、給不出任何保證。真正會出錯的是「官方管道有沒有列全」，
        # 那道守門寫在上面的 _missing 檢查。這裡只保留交叉驗算。
        by = dict(cats)
        assert by["至少用到一個官方管道"] == by["只有官方管道"] + by["官方與親友都有"], gname
        assert by["有靠親友推薦"] == by["只靠親友推薦，沒有任何官方管道"] + by["官方與親友都有"], gname
    C.save_table(pd.DataFrame(ch_rows), "03_管道_官方vs親友",
                 "以人去重計算；互斥四分組的四列相加＝分母。"
                 "官方管道清單是否列全，由 03_crosstab.py 的 _missing 守門檢查")

    # 居住地：雙北合計。報告寫 62%（79/127），但台北 41 票＋新北 39 票＝80，
    # 差的那 1 人同時勾了台北／新北／桃園（common.pct_table 的警語就是記這件事）。
    # 這正是「票數不可相加當人數」的實例，故單獨出表，用 people_count 去重。
    n_tp, d_tp = C.people_count(df, C.C_REGION, ["台北市", "新北市"])
    C.save_table(pd.DataFrame([{
        "類別": "雙北（台北市或新北市）", "分子": n_tp, "分母": d_tp,
        "比例": round(n_tp / d_tp, 4),
        "算法": "people_count 去重；不可用台北票數＋新北票數（會重複計同時勾兩地的人）",
        "信賴度": C.confidence(d_tp),
    }]), "03_全體_居住地_雙北合計", "報告第 1 章 62%（79/127）的來源")

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

    # 「動手做的人，不一定用過別人的公民科技產品」（報告第 2 章）。
    # 分母是「勾了開發維護**或**發起專案」的人數，必須去重——同時勾兩個的人只算一次，
    # 不能把兩個選項的票數相加（33＋28＝61，實際是 38 人）。
    dev, init, user = C.ROLE_LADDER[2], C.ROLE_LADDER[3], C.ROLE_LADDER[0]
    maker = [st for st in role_sets if dev in st or init in st]
    no_user = sum(1 for st in maker if user not in st)
    C.save_table(pd.DataFrame([
        {"類別": "勾了「開發維護」或「發起專案」（去重）", "分子": len(maker), "分母": len(role_sets),
         "比例": round(len(maker) / len(role_sets), 4)},
        {"類別": "上列的人當中，沒有勾「使用過某個工具或參與過討論」", "分子": no_user,
         "分母": len(maker), "比例": round(no_user / len(maker), 4)},
    ]), "03_角色_動手做但沒用過",
        "分母 101 位曾接觸者；第二列的分母是第一列的分子（38），不是 101")

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
