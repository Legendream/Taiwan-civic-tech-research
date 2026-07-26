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
    # 報告第 1 章「不只看居住地，還要看地緣連結」整段靠這一題，
    # 但這題原本沒有任何輸出表，分類規則也沒被記錄下來，數字無法回溯。
    # 「取數來源清查」這一批補上逐筆編碼。
    # 分類規則（Claire 於 2026-07-26 定案）：
    #   · 中南部或東部＝**縣市層級**的行政區名：台中、台南、高雄、嘉義、屏東、
    #     彰化、南投、雲林、苗栗、宜蘭、花蓮、台東
    #     （宜蘭依本專案居住地選項屬「東部區域（宜蘭、花蓮、台東）」，計入）
    #   · **鄉鎮層級的地名與自然地名一律不計**。鄉鎮名（某縣某鎮）不計，
    #     地理特徵名（濕地、步道、溪口等）也不計，即使它們位於中南部。
    #     實際踩到這兩種邊界的各有一筆，判讀結果見 開放題編碼.csv。
    #   · 海外＝台灣以外的地名
    #   · 一筆可同時屬於兩類；兩類都不屬於的歸「其他」
    # ⚠️ 這個規則以前只存在於編碼者腦中，數字（34、20）無法回溯。現在寫下來，
    #    任何人都能拿 09_開放題_編碼對照.csv 逐筆核對判讀是否符合這條規則。
    "地區連結": (C.C_REGION_LINK, "全體中有填答者"),
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

    # 地區連結 × 是否住雙北：報告第 1 章寫「住雙北的 79 人裡，也有 N 人同時與中南部或
    # 東部有深度連結、M 人與海外有連結」。這是交叉數字，上面的彙總表給不出來，
    # 而它同樣沒有來源表，故單獨輸出。
    link = coding[coding["題目"] == "地區連結"]
    is_tp = df[C.C_REGION].astype(str).apply(
        lambda v: any(k in v for k in ["台北市", "新北市"]))
    rows = []
    for theme in ["中南部或東部", "海外"]:
        who = set(link.loc[link["主題"] == theme, "列索引"])
        rows.append({
            "主題": theme,
            "全體有填答者中的人數": len(who),
            "全體有填答者": int((df[C.C_REGION_LINK].astype(str).str.strip() != "").sum()),
            "住雙北且有此連結": sum(1 for i in who if is_tp.get(i, False)),
            "住雙北人數": int(is_tp.sum()),
        })
    C.save_table(pd.DataFrame(rows), "09_開放題_地區連結×雙北",
                 "分母有兩個：全體有填答者 63、住雙北者 79，兩者不可混用")

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
