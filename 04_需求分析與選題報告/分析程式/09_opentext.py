# -*- coding: utf-8 -*-
"""
09_opentext.py — 開放題（簡答題）的主題歸納。

與其他分析不同，**主題編碼是人工判讀**，不是程式算出來的。
判讀結果逐筆記錄在 `開放題編碼.csv`（題目／列索引／主題），
這支腳本只做兩件事：核對編碼涵蓋率、彙總次數。

這樣任何人都能回頭check「第 53 列為什麼被歸到這個主題」，
而不是只能相信報告裡的一句話。

⚠️ 引述原文時一律去識別化，且不引述可指認到特定個人的敘述。

輸出：分析結果/09_開放題_*.csv

執行：python3 09_opentext.py
"""

import pandas as pd

import common as C

CODING = C.OUT_DIR / "分析程式" / "開放題編碼.csv"

# 題目代號 → 問卷欄位、分母說明
QUESTIONS = {
    "面對困難採取的行動": (C.C_ACTION_TEXT, "曾參與者中有填答者"),
    "專案在解決什麼問題": (C.C_PROJ_DESC, "曾參與者全數填答"),
    "所屬組織或團體": (C.C_ORG_TEXT, "全體中有填答者"),
}


def main():
    df = C.load_clean()
    coding = pd.read_csv(CODING)

    summary_rows = []
    for label, (col, denom_note) in QUESTIONS.items():
        answered = df.index[df[col].astype(str).str.strip() != ""].tolist()
        sub = coding[coding["題目"] == label]
        coded = set(sub["列索引"])

        # 涵蓋率檢查：每一筆有填答的回覆都必須被編碼，否則就是漏編
        missing = set(answered) - coded
        extra = coded - set(answered)
        assert not extra, f"{label}：編碼了不存在的列 {sorted(extra)}"
        if missing:
            print(f"  ⚠ {label}：{len(missing)} 筆未編碼 → {sorted(missing)}")
        else:
            print(f"  ✓ {label}：{len(answered)} 筆全數編碼")

        counts = sub["主題"].value_counts()
        t = pd.DataFrame({"主題": counts.index, "筆數": counts.values})
        t["分母"] = len(answered)
        t["比例"] = (t["筆數"] / len(answered)).round(4)
        t["分母說明"] = denom_note
        t["信賴度"] = C.subgroup_confidence(len(answered))
        C.save_table(t, f"09_開放題_{label}",
                     f"人工主題編碼，來源 開放題編碼.csv；一筆可對應多主題")
        for _, r in t.iterrows():
            summary_rows.append({"題目": label, **r.to_dict()})

    C.save_table(pd.DataFrame(summary_rows), "09_開放題_總表")

    # 編碼對照檔：把「原文」與「我歸的主題」並排，讓人能直接檢查判讀是否合理。
    # 只有列索引與主題的編碼檔不夠——要查「這筆為什麼歸這類」還得自己去比對原始 CSV。
    review = []
    for label, (col, _) in QUESTIONS.items():
        sub = coding[coding["題目"] == label]
        for idx in sorted(set(sub["列索引"])):
            themes = sorted(sub.loc[sub["列索引"] == idx, "主題"])
            review.append({
                "題目": label,
                "列索引": idx,
                "原文": str(df.at[idx, col]).replace("\n", " ").strip(),
                "歸入主題": "；".join(themes),
                "主題數": len(themes),
            })
    C.save_table(pd.DataFrame(review), "09_開放題_編碼對照",
                 "原文 × 我歸的主題並排，供逐筆檢查判讀是否合理")

    pd.set_option("display.width", 200, "display.max_colwidth", 34)
    for label in QUESTIONS:
        d = pd.read_csv(C.TABLE_DIR / f"09_開放題_{label}.csv")
        print(f"\n=== {label}（{d['分母'].iloc[0]} 筆）===")
        print(d[["主題", "筆數", "比例"]].to_string(index=False))


if __name__ == "__main__":
    main()
