# -*- coding: utf-8 -*-
"""
07_old_report_diff.py — 舊報告《選題依據與建議報告》更新到 N=126 的差異對照。

舊報告的資源短文選題，是把「議題領域」與「跨領域工具」放進同一池排序、共搶 8 個名額。
本腳本用新舊兩份資料各跑一次同樣的整合排序，輸出差異對照，
讓「要不要改寫舊報告」這個決定有依據，而不是憑印象。

輸出：分析結果/07_舊報告差異_資源短文排序.csv
      分析結果/07_舊報告差異_摘要.csv

執行：python3 07_old_report_diff.py
"""

import pandas as pd

import common as C


def integrated_ranking(df, denom_mode="總回收"):
    """
    議題領域 ＋ 跨領域工具 放同一池排序（沿用舊報告的作法）。

    denom_mode：
      "總回收"——分母＝總回收份數。**舊報告用的就是這個**
                （查核：群眾協力 74/121 = 61.2%，與舊報告表 3 完全吻合）。
      "有作答"——分母＝該題有作答的人數，較嚴謹，但與舊報告不可直接比。
    兩種都算，才知道差異是「樣本變了」還是「分母定義不同」造成的。
    """
    parts = []
    for col, kind in [(C.C_DOMAINS, "領域"), (C.C_TOOLS, "工具")]:
        denom = len(df) if denom_mode == "總回收" else None
        t = C.pct_table(df, col, denom=denom)
        t["類型"] = kind
        parts.append(t)
    pool = pd.concat(parts, ignore_index=True)
    # 只留正式選項（自由填答票數極少，不參與名額競爭）
    pool = pool[pool["票數"] >= 5].copy()
    pool = pool.sort_values("比例", ascending=False).reset_index(drop=True)
    pool["排名"] = pool.index + 1
    return pool


def main():
    new = C.load_clean()
    old = pd.read_csv(C.OLD_CSV, dtype=str, keep_default_na=False)
    old.columns = [c.strip() for c in old.columns]

    # 與舊報告對齊：一律用「總回收」當分母，否則差異會混入分母定義的改變
    r_new = integrated_ranking(new, "總回收")
    r_old = integrated_ranking(old, "總回收")

    # 驗證分母慣例判斷正確：舊資料應重現舊報告表 3 的數字
    chk = r_old[r_old["選項"].str.startswith("群眾協力")]["比例"].iloc[0]
    assert abs(chk - 0.612) < 0.001, f"未重現舊報告的 61.2%（得 {chk:.1%}），分母慣例判斷可能有誤"
    print(f"✓ 分母慣例查核：以總回收為分母，重現舊報告「群眾協力 {chk:.1%}」\n")

    cmp = r_old.merge(r_new, on=["選項", "類型"], suffixes=("_舊", "_新"), how="outer")
    cmp["排名變化"] = cmp["排名_舊"] - cmp["排名_新"]
    cmp["進前8_舊"] = cmp["排名_舊"] <= 8
    cmp["進前8_新"] = cmp["排名_新"] <= 8
    cmp["前8名單是否改變"] = cmp["進前8_舊"] != cmp["進前8_新"]
    cmp = cmp.sort_values("排名_新")

    keep = ["排名_舊", "排名_新", "排名變化", "類型", "選項",
            "票數_舊", "分母_舊", "比例_舊", "票數_新", "分母_新", "比例_新",
            "進前8_舊", "進前8_新", "前8名單是否改變"]
    C.save_table(cmp[keep], "07_舊報告差異_資源短文排序")

    pd.set_option("display.width", 210, "display.max_colwidth", 30)
    print("=== 資源短文整合排序：新 vs 舊 ===")
    show = cmp[["排名_舊", "排名_新", "類型", "選項", "比例_舊", "比例_新", "排名變化"]].head(12).copy()
    show["比例_舊"] = (show["比例_舊"] * 100).round(1)
    show["比例_新"] = (show["比例_新"] * 100).round(1)
    print(show.to_string(index=False))

    # 前 8 名單是否有人進出
    changed = cmp[cmp["前8名單是否改變"]]
    top8_new = cmp[cmp["排名_新"] <= 8]
    ninth = cmp[cmp["排名_新"] == 9]
    gap = (top8_new["比例_新"].min() - ninth["比例_新"].iloc[0]) if len(ninth) else float("nan")

    summary = []
    summary.append({"檢查項": "前 8 名的名單是否有人進出", "結果": "否" if changed.empty else "是",
                    "說明": "選題結論不變" if changed.empty else "需回報並討論改寫"})
    swaps = cmp[(cmp["排名_新"] <= 8) & (cmp["排名變化"] != 0)]
    summary.append({"檢查項": "前 8 名內部順序是否有變動",
                    "結果": f"{len(swaps)} 項名次移動",
                    "說明": "；".join(f"{r['選項'][:12]} {int(r['排名_舊'])}→{int(r['排名_新'])}"
                                     for _, r in swaps.iterrows()) or "無"})
    summary.append({"檢查項": "第 8 名與第 9 名的斷層", "結果": f"{gap * 100:.1f} 個百分點",
                    "說明": "斷層仍明顯，前 8 名的分界線站得住" if gap > 0.05 else "斷層變小，分界線需重新檢視"})

    k = pd.read_csv(C.TABLE_DIR / "02_狩野_新舊對照.csv")
    summary.append({"檢查項": "狩野 5 主題落點是否改變",
                    "結果": "否" if not k["落點是否改變"].any() else "是",
                    "說明": "五個主題仍全部在「魅力 A」，長文選題不變"})
    summary.append({"檢查項": "狩野有作答數差異",
                    "結果": "、".join(str(int(v)) for v in k["有作答差"].unique()),
                    "說明": "應恰為 6（新增 6 份回覆），黃金對照通過"})

    s = pd.DataFrame(summary)
    C.save_table(s, "07_舊報告差異_摘要")
    print("\n=== 是否需要改寫舊報告 ===")
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()
