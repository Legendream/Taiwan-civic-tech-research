# -*- coding: utf-8 -*-
"""
04_motivation.py — 初次動機 → 持續動機的配對流向（同一批 47 位曾參與者）。

為什麼做配對而不是比較兩組比例：
  Q12 與 Q13 是同一批人、同一套選項，逐人比對「留下／新增／流失」比
  兩個獨立的百分比更有力——後者只能說「總量差不多」，前者能說出人在動機之間怎麼移動。
  依 Rotman 動態模型，初次投入與持續投入本來就該分開問、成對看。

⚠ 選項外的自由填答（例如「我現在已淡出」「累了」）單獨歸類，不塞進既有選項。

輸出：分析結果/04_動機_流向.csv、04_動機_個人變化.csv、04_動機_自由填答.csv

執行：python3 04_motivation.py
"""

import pandas as pd

import common as C


def parse(v):
    return {o.strip() for o in str(v).split(C.MULTI_SELECT_SEP) if o.strip()}


def main():
    df = C.load_clean()
    done = df[df[C.LAYER] == C.L_DONE]
    n = len(done)
    print(f"曾參與者 N={n}（配對比較的分母）")

    first = done[C.C_MOTIVE_FIRST].apply(parse)
    now = done[C.C_MOTIVE_NOW].apply(parse)

    canon = set(C.MOTIVES)
    first_c = first.apply(lambda s: s & canon)
    now_c = now.apply(lambda s: s & canon)

    # ---------- 逐動機的流向 ----------
    rows = []
    for m in C.MOTIVES:
        in_first = first_c.apply(lambda s, m=m: m in s)
        in_now = now_c.apply(lambda s, m=m: m in s)
        keep = int((in_first & in_now).sum())
        lost = int((in_first & ~in_now).sum())
        gained = int((~in_first & in_now).sum())
        rows.append({
            "動機": m, "動機類型": C.MOTIVE_TYPE[m],
            "初次_人數": int(in_first.sum()), "持續_人數": int(in_now.sum()),
            "分母": n,
            "初次_比例": round(in_first.mean(), 4), "持續_比例": round(in_now.mean(), 4),
            "留存": keep, "流失": lost, "新增": gained,
            "淨變化": int(in_now.sum()) - int(in_first.sum()),
            "留存率": round(keep / in_first.sum(), 3) if in_first.sum() else None,
            "信賴度": C.subgroup_confidence(n),
        })
    flow = pd.DataFrame(rows).sort_values("初次_人數", ascending=False)
    C.save_table(flow, "04_動機_流向", f"同一批 N={n} 的配對比較")

    # ---------- 個人層級：動機是否改變 ----------
    same = [f == nw for f, nw in zip(first_c, now_c)]
    changed = sum(1 for s in same if not s)
    person = pd.DataFrame({
        "類別": ["動機組合完全相同", "動機組合有變動"],
        "人數": [n - changed, changed],
        "分母": [n, n],
        "比例": [round((n - changed) / n, 4), round(changed / n, 4)],
    })
    C.save_table(person, "04_動機_個人變化")

    # ---------- 選項外的自由填答 ----------
    extra = []
    for label, series in [("初次動機", first), ("持續動機", now)]:
        for i, s in series.items():
            for o in s - canon:
                extra.append({"題目": label, "列索引": i, "自由填答": o})
    extra_df = pd.DataFrame(extra)
    C.save_table(extra_df, "04_動機_自由填答", "單獨歸類，未計入正式選項")

    # ---------- 輸出 ----------
    pd.set_option("display.width", 200, "display.max_colwidth", 30)
    print("\n=== 動機流向（同一批 47 人）===")
    print(flow[["動機", "初次_人數", "持續_人數", "淨變化", "留存", "流失", "新增", "留存率"]]
          .to_string(index=False))
    print(f"\n動機組合有變動者：{changed}/{n} = {changed / n:.1%}")
    print("\n=== 選項外自由填答 ===")
    print(extra_df.to_string(index=False) if len(extra_df) else "（無）")

    # 檢查：留存＋流失 = 初次人數；留存＋新增 = 持續人數
    assert ((flow["留存"] + flow["流失"]) == flow["初次_人數"]).all(), "留存＋流失 ≠ 初次人數"
    assert ((flow["留存"] + flow["新增"]) == flow["持續_人數"]).all(), "留存＋新增 ≠ 持續人數"
    print("\n✓ 流向檢查通過（留存＋流失＝初次；留存＋新增＝持續）")


if __name__ == "__main__":
    main()
