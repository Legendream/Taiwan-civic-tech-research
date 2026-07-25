# -*- coding: utf-8 -*-
"""
02_kano.py — 狩野（Kano）分析：全體 ＋ 入坑三層，並與舊報告（N≈120）對照。

方法出處：satisfaction-survey-analyzer/references/methodology.md
  · 逐位受訪者查「功能型 × 反功能型」對照表得 A/O/M/I/R/Q
  · SI  = (A+O) / (A+O+M+I)        分母排除 R 與 Q
  · DSI = (O+M) / (A+O+M+I) × (−1)
  · 落點閾值 0.5 / −0.5：右上魅力 A、右下期望 O、左下基本 M、左上無差別 I
  · Q > 5% 先別下結論，提醒題目可能被誤解

⚠ 絕不對狩野答案取平均、加總或跑相關——只能查表分類。

輸出：分析結果/02_狩野_全體.csv、02_狩野_三層.csv、02_狩野_新舊對照.csv

執行：python3 02_kano.py
"""

import pandas as pd

import common as C


def topics(df):
    """回傳 [(主題, 功能型欄, 反功能型欄)]，並確認兩邊主題一一對應。"""
    func = {c[len(C.KANO_FUNC_PREFIX):].strip(" []"): c
            for c in df.columns if c.startswith(C.KANO_FUNC_PREFIX)}
    dysf = {c[len(C.KANO_DYSF_PREFIX):].strip(" []"): c
            for c in df.columns if c.startswith(C.KANO_DYSF_PREFIX)}
    assert set(func) == set(dysf), f"狩野成對題主題不一致：{set(func) ^ set(dysf)}"
    return [(t, func[t], dysf[t]) for t in func]


def classify(df, fcol, dcol):
    """逐列查對照表；任一邊未作答則回傳 None（不計入）。"""
    res = []
    for f, d in zip(df[fcol].str.strip(), df[dcol].str.strip()):
        if f in C.KANO_TABLE and d in C.KANO_TABLE[f]:
            res.append(C.KANO_TABLE[f][d])
        else:
            res.append(None)
    return pd.Series(res, index=df.index)


def score(cats: pd.Series, topic: str, group: str, n_group: int) -> dict:
    c = cats.dropna().value_counts()
    a, o, m, i = (int(c.get(k, 0)) for k in "AOMI")
    r, q = int(c.get("R", 0)), int(c.get("Q", 0))
    valid = a + o + m + i
    total = valid + r + q
    si = (a + o) / valid if valid else float("nan")
    dsi = -(o + m) / valid if valid else float("nan")
    if si >= 0.5:
        cls = "魅力 A" if dsi > -0.5 else "期望 O"
    else:
        cls = "無差別 I" if dsi > -0.5 else "基本 M"
    return {
        "分群": group, "主題": topic, "群體N": n_group,
        "A": a, "O": o, "M": m, "I": i, "R": r, "Q": q,
        "有效樣本": valid, "有作答": total,
        "Q比例": q / total if total else float("nan"),
        "SI": round(si, 3), "DSI": round(dsi, 3), "落點": cls,
        "信賴度": C.subgroup_confidence(valid),
    }


def run(df, group_name, n_group):
    return [score(classify(df, f, d), t, group_name, n_group) for t, f, d in topics(df)]


def main():
    df = C.load_clean()
    ts = topics(df)
    print(f"狩野主題 {len(ts)} 組：" + "、".join(t for t, _, _ in ts))

    # ---------- 全體 ----------
    overall = pd.DataFrame(run(df, "全體", len(df)))
    C.save_table(overall, "02_狩野_全體")

    # ---------- 三層 ----------
    rows = []
    for layer in C.LAYER_ORDER:
        sub = df[df[C.LAYER] == layer]
        rows += run(sub, layer, len(sub))
    layered = pd.DataFrame(rows)
    C.save_table(layered, "02_狩野_三層")

    # ---------- Q 值警示 ----------
    high_q = overall[overall["Q比例"] > 0.05]
    if len(high_q):
        print(f"\n⚠ Q（矛盾答案）>5% 的主題 {len(high_q)} 個——SI 絕對值不宜過度精讀：")
        for _, r in high_q.iterrows():
            print(f"    {r['主題'][:28]}… Q={r['Q']}／{r['有作答']} = {r['Q比例']:.1%}")

    # ---------- 黃金對照：新舊差異必須恰好來自 6 份新回覆 ----------
    old = pd.read_csv(C.OLD_CSV, dtype=str, keep_default_na=False)
    old.columns = [c.strip() for c in old.columns]
    old_res = pd.DataFrame(run(old, "舊檔", len(old)))
    cmp = overall.merge(old_res, on="主題", suffixes=("_新", "_舊"))
    cmp["有作答差"] = cmp["有作答_新"] - cmp["有作答_舊"]
    cmp["SI差"] = (cmp["SI_新"] - cmp["SI_舊"]).round(3)
    cmp["DSI差"] = (cmp["DSI_新"] - cmp["DSI_舊"]).round(3)
    cmp["落點是否改變"] = cmp["落點_新"] != cmp["落點_舊"]
    keep = ["主題", "有作答_舊", "有作答_新", "有作答差", "SI_舊", "SI_新", "SI差",
            "DSI_舊", "DSI_新", "DSI差", "落點_舊", "落點_新", "落點是否改變"]
    C.save_table(cmp[keep], "02_狩野_新舊對照")

    print("\n=== 黃金對照（新 vs 舊報告樣本）===")
    pd.set_option("display.width", 200, "display.max_colwidth", 30)
    print(cmp[["主題", "有作答_舊", "有作答_新", "有作答差", "SI_舊", "SI_新",
               "落點_舊", "落點_新", "落點是否改變"]].to_string(index=False))

    diffs = set(cmp["有作答差"])
    print(f"\n各主題有作答數差異：{sorted(diffs)}（新增 6 份回覆，差異必須恰為 6）")
    # 收緊為「恰等於 6」：報告 §10 明白宣稱「多一票少一票都代表讀錯欄位」，
    # 放寬成 5 或 6 等於讓這道黃金對照失效。
    assert diffs == {6}, f"有作答數差異應恰為 6，實得 {diffs}——可能讀錯欄位或分層"
    if cmp["落點是否改變"].any():
        changed = cmp.loc[cmp["落點是否改變"], "主題"].tolist()
        print(f"\n⚠⚠ 有 {len(changed)} 個主題的狩野落點改變：{changed}")
        print("    → 依計畫，此情況須先回報再決定是否改寫舊報告該節。")
    else:
        print("\n✓ 5 個主題的狩野落點全部未改變，舊報告的選題結論不受新樣本影響。")

    # ---------- 主結果 ----------
    print("\n=== 全體落點（N=126）===")
    print(overall[["主題", "A", "O", "M", "I", "R", "Q", "有效樣本", "SI", "DSI", "落點"]].to_string(index=False))
    print("\n=== 三層落點 ===")
    print(layered[["分群", "主題", "群體N", "有效樣本", "SI", "DSI", "落點", "信賴度"]].to_string(index=False))


if __name__ == "__main__":
    main()
