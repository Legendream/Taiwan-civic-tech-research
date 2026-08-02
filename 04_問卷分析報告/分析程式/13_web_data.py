# -*- coding: utf-8 -*-
"""
13_web_data.py — 產生展示網頁用的資料檔。

讀 分析結果/*.csv（皆為已公開、彙總層級的表），轉成 docs/data/figures.json，
供 docs/index.html 用 JS 畫成互動圖表。

⚠️ 個資原則同 common.py：這支腳本只讀 分析結果/ 底下的彙總 CSV，
   不讀 03_問卷回收資料/ 或任何逐人層級的檔案。

執行：python3 13_web_data.py
輸出：../../docs/data/figures.json
"""

import json

import pandas as pd

import common as C

WEB_DATA_DIR = C.PROJ / "docs" / "data"
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)


def rows(df, cols):
    """DataFrame → list[dict]，只留指定欄位，數值欄位轉 float/int。"""
    out = []
    for _, r in df.iterrows():
        d = {}
        for c in cols:
            v = r[c]
            if isinstance(v, (int,)):
                d[c] = int(v)
            elif isinstance(v, float):
                d[c] = round(float(v), 6)
            else:
                d[c] = v
        out.append(d)
    return out


def hbar_dataset(csv_name, label_col, value_col, num_col,
                  title, subtitle, denom_note, min_votes=None):
    """
    ⚠️ 分母一律讀每列自己的「分母」欄，不接受外部傳入的固定數字。
       樣本數以後會變（N=127 之後還會再收），若分母是寫死的常數，
       重跑這支腳本也不會跟著更新，網頁數字就會跟 CSV 對不上。
    """
    df = pd.read_csv(C.TABLE_DIR / csv_name)
    if min_votes is not None:
        df = df[df[num_col] >= min_votes]
    df = df.sort_values(value_col, ascending=False)
    items = []
    for _, r in df.iterrows():
        items.append({
            "label": r[label_col],
            "pct": round(float(r[value_col]), 4),
            "n": int(r[num_col]),
            "d": int(r["分母"]),
        })
    return {
        "type": "hbar",
        "title": title,
        "subtitle": subtitle,
        "denomNote": denom_note,
        "items": items,
    }


def main():
    out = {
        "meta": {
            "n_total": 127,
            "n_never": 26,
            "n_aware": 54,
            "n_done": 47,
            "sample_note": "資料範圍：截至 2026/7/20 的問卷有效樣本，共 127 份",
        },
        "palette": {
            "primary": C.PALETTE["primary"],
            "accent": C.PALETTE["accent"],
            "neutral": C.PALETTE["neutral"],
            "grid": C.PALETTE["grid"],
            "layers": dict(C.PALETTE["layers"]),
        },
        "layerOrder": C.LAYER_ORDER,
        "layerPlain": C.LAYER_PLAIN,
        "figures": {},
        "tables": {},
    }

    # ---------------- fig01：入坑分層（甜甜圈） ----------------
    lay = pd.read_csv(C.TABLE_DIR / "01_入坑分層分布.csv")
    out["figures"]["fig01_layers"] = {
        "type": "donut",
        "title": "127 位填答者，分成三層",
        "subtitle": "分母＝全體 127 人｜色隨身分固定：聽過或看過＝綠、接觸未參與＝橘、做過專案＝藍",
        "items": [
            {"label": C.LAYER_PLAIN[r["分層"]], "key": r["分層"],
             "pct": round(float(r["比例"]), 4), "n": int(r["人數"]), "d": int(r["分母"])}
            for _, r in lay.iterrows()
        ],
    }

    # ---------------- fig02：居住地分布 ----------------
    out["figures"]["fig02_region"] = hbar_dataset(
        "03_全體_居住地.csv", "選項", "比例", "票數",
        "填答者的居住地分布",
        "全體 N=127｜雙北合計逾六成，反映問卷經 g0v 管道發放的取樣偏誤",
        "分母＝全體 127 人")
    twin = pd.read_csv(C.TABLE_DIR / "03_全體_居住地_雙北合計.csv").iloc[0]
    out["tables"]["雙北合計"] = {
        "n": int(twin["分子"]), "d": int(twin["分母"]), "pct": round(float(twin["比例"]), 4),
    }

    # ---------------- fig03：角色分布 ----------------
    roles = pd.read_csv(C.TABLE_DIR / "03_全體_角色勾選.csv")
    roles = roles[roles["選項"].isin(C.ROLE_LADDER)].copy()
    roles["原始選項"] = roles["選項"].map(C.ROLE_ORIGINAL)
    roles = roles.set_index("選項").loc[C.ROLE_LADDER].reset_index()
    out["figures"]["fig03_roles"] = {
        "type": "hbar",
        "title": "擔任過哪些角色（複選，由淺到深排列）",
        "subtitle": "分母＝101 位曾接觸者｜可複選，加總會超過 100%",
        "denomNote": "分母＝101 位曾接觸公民科技者",
        "sortByOrder": True,
        "items": [
            {"label": r["原始選項"], "shortLabel": C.ROLE_SHORT[r["選項"]],
             "pct": round(float(r["比例"]), 4), "n": int(r["票數"]), "d": int(r["分母"])}
            for _, r in roles.iterrows()
        ],
    }

    # ---------------- fig04：參與深度分布 ----------------
    summary = pd.read_csv(C.TABLE_DIR / "01_衍生變項摘要.csv")
    depth = summary[summary["變項"] == "參與深度"].copy()
    depth_order = list(C.DEPTH_LABEL.values()) + ["以上都不太像我"]
    depth = depth.set_index("類別").reindex(depth_order).reset_index()
    out["figures"]["fig04_depth"] = {
        "type": "hbar",
        "title": "參與深度：四成的人只站在第一階",
        "subtitle": "分母＝101 位曾接觸者｜灰色那列是逃生選項，不在深度軸上、未給權重",
        "denomNote": "分母＝101 位曾接觸公民科技者",
        "sortByOrder": True,
        "escapeLabel": "以上都不太像我",
        "items": [
            {"label": r["類別"], "pct": round(float(r["比例"]), 4),
             "n": int(r["人數"]), "d": int(r["分母"])}
            for _, r in depth.iterrows()
        ],
    }

    # ---------------- fig05：困擾五級分布（堆疊橫條） ----------------
    dist = pd.read_csv(C.TABLE_DIR / "03_困擾_五級分布.csv").sort_values(
        "3分以上_比例", ascending=False)
    score_cols = ["1分_幾乎沒影響", "2分_有點困擾但還能處理", "3分_明顯卡住我、拖慢進度",
                  "4分_受挫到萌生退意", "5分_困擾到專案無法持續"]
    out["figures"]["fig05_trouble"] = {
        "type": "stacked-hbar",
        "title": "每項困難的困擾程度分布（1–5 分完整呈現）",
        "subtitle": "依「3 分以上人數」由多到少排列｜此題沒有「沒遇到」選項，"
                     "1 分同時包含「沒發生過」與「發生了但不影響」",
        "denomNote": "分母＝47 位曾參與者（每題皆為 47 人作答）",
        "seriesLabels": ["1：幾乎沒影響", "2：有點困擾但還能處理", "3：明顯卡住我、拖慢進度",
                          "4：受挫到萌生退意", "5：困擾到專案無法持續"],
        "seriesColors": C.PALETTE["trouble_scale"],
        "items": [
            {
                "label": r["困難"],
                "d": int(r["合計"]),
                "counts": [int(r[c]) for c in score_cols],
                "pct3plus": round(float(r["3分以上_比例"]), 4),
                "n3plus": int(r["3分以上_合計"]),
                "pct4plus": round(float(r["4分以上_比例"]), 4),
                "n4plus": int(r["4分以上_合計"]),
            }
            for _, r in dist.iterrows()
        ],
    }

    # ---------------- fig06：年齡×持續動機（雙向橫條，三面板） ----------------
    lf = pd.read_csv(C.TABLE_DIR / "03_年齡×持續動機_lift.csv")
    lf = lf[lf["選項"].isin(C.MOTIVES)].copy()
    panels = []
    for age in C.AGE_COARSE_ORDER:
        d = lf[lf["分群"] == age].copy()
        if d.empty:
            continue
        denom = int(d["分母"].iloc[0])
        d["高出百分點"] = (d["群內比例"] - d["全體比例"]) * 100
        d = d.sort_values("高出百分點", ascending=False)
        panels.append({
            "group": age,
            "d": denom,
            "items": [
                {"label": r["選項"], "n": int(r["分子"]), "d": int(r["分母"]),
                 "groupPct": round(float(r["群內比例"]), 4),
                 "basePct": round(float(r["全體比例"]), 4),
                 "diffPts": round(float(r["高出百分點"]), 2)}
                for _, r in d.iterrows()
            ],
        })
    out["figures"]["fig06_age_motive"] = {
        "type": "diverging",
        "title": "不同世代，現在的動機不一樣",
        "subtitle": "每一條＝該世代勾這個動機的比例，與全體 47 位曾參與者相差幾個百分點。"
                     "往右（暖色）＝高於全體，往左（淡藍）＝低於全體。",
        "denomNote": "三個世代各有 10／19／18 人；此題可複選",
        "panels": panels,
    }

    # ---------------- fig07：資源 ----------------
    out["figures"]["fig07_resources"] = hbar_dataset(
        "03_全體_資源.csv", "選項", "比例", "票數",
        "曾參與過專案的人，用過哪些資源",
        "分母＝47 位曾參與者｜可複選，加總會超過 100%",
        "分母＝47 位曾參與過專案的人")

    # ---------------- fig08：專長 ----------------
    out["figures"]["fig08_skills"] = hbar_dataset(
        "03_全體_專長.csv", "選項", "比例", "票數",
        "曾參與過專案的人，貢獻過哪些專長",
        "分母＝47 位曾參與者｜可複選，加總會超過 100%｜常見一人多工",
        "分母＝47 位曾參與過專案的人")

    # ---------------- fig09：g0v 消息管道 ----------------
    out["figures"]["fig09_channel"] = hbar_dataset(
        "03_全體_g0v消息管道.csv", "選項", "比例", "票數",
        "大家從哪裡得知 g0v 的活動消息",
        "全體 N=127，複選｜「親友推薦」與「g0v 社群管道」並列第一（各 51 人），"
        "意味著觸及仍有一半依賴人際網絡",
        "分母＝全體 127 人", min_votes=3)

    # ---------------- fig10：未參與原因 ----------------
    out["figures"]["fig10_notjoin"] = hbar_dataset(
        "03_未參與原因.csv", "選項", "比例", "票數",
        "從未接觸者說，是什麼擋住了他們",
        "此題複選，最多選 3 個原因｜分母＝26 位「從未接觸公民科技」者（全數作答）｜"
        "注意：被選為主要對象的「接觸未參與」54 人，問卷未問此題",
        "分母＝26 位從未接觸公民科技者")

    # ---------------- fig11：三層 × 活動意願 ----------------
    def layered_grouped(csv_name, title, subtitle, denom_note, topn=None):
        t = pd.read_csv(C.TABLE_DIR / csv_name)
        t = t[t["選項"] != "其他（自由填答）"]
        if topn:
            order = (t.groupby("選項")["分子"].sum()
                      .sort_values(ascending=False).head(topn).index)
            t = t[t["選項"].isin(order)]
            option_order = list(order)
        else:
            option_order = list(dict.fromkeys(t["選項"]))
        dens = {g: int(t.loc[t["分群"] == g, "分母"].iloc[0]) for g in C.LAYER_ORDER
                if (t["分群"] == g).any()}
        options = []
        for opt in option_order:
            sub = t[t["選項"] == opt]
            byLayer = {}
            for _, r in sub.iterrows():
                byLayer[r["分群"]] = {
                    "n": int(r["分子"]), "d": int(r["分母"]),
                    "pct": round(float(r["群內比例"]), 4),
                }
            options.append({"label": opt, "byLayer": byLayer})
        return {
            "type": "grouped-hbar-layers",
            "title": title,
            "subtitle": subtitle,
            "denomNote": denom_note,
            "layerDenoms": dens,
            "options": options,
        }

    out["figures"]["fig11_events"] = layered_grouped(
        "03_三層×活動意願.csv",
        "三群人分別最想報名哪些活動",
        "此題複選｜各群的勾選率（分母為該群有作答人數）",
        "從未接觸 26 人／接觸未參與 54 人／曾參與 47 人")

    # ---------------- fig12：狩野落點（全體，散佈圖） ----------------
    kano_all = pd.read_csv(C.TABLE_DIR / "02_狩野_全體.csv")
    out["figures"]["fig12_kano_all"] = {
        "type": "scatter-kano",
        "title": "五個文章主題的狩野落點（全體）",
        "subtitle": "N=126｜SI 0–1、DSI 0～−1 全幅，分界線 0.5／−0.5 位於正中央\n"
                     "五個主題全部落在「魅力 A」，其中「落地、接進體制」最靠近期望 O 邊界",
        "denomNote": "分母＝126 位有作答者（全體 127 人中 126 人答了狩野題）",
        "items": [
            {"num": C.KANO_NUM[r["主題"]], "label": C.KANO_SHORT[r["主題"]],
             "fullLabel": r["主題"], "si": round(float(r["SI"]), 3),
             "dsi": round(float(r["DSI"]), 3), "quadrant": r["落點"]}
            for _, r in kano_all.iterrows()
        ],
    }

    # ---------------- fig13：狩野落點（三層，小倍數） ----------------
    kl = pd.read_csv(C.TABLE_DIR / "02_狩野_三層.csv")
    panels13 = []
    for layer in C.LAYER_ORDER:
        s = kl[kl["分群"] == layer]
        panels13.append({
            "layer": layer,
            "n": int(s["群體N"].iloc[0]),
            "items": [
                {"num": C.KANO_NUM[r["主題"]], "label": C.KANO_SHORT[r["主題"]],
                 "fullLabel": r["主題"], "si": round(float(r["SI"]), 3),
                 "dsi": round(float(r["DSI"]), 3), "quadrant": r["落點"]}
                for _, r in s.iterrows()
            ],
        })
    out["figures"]["fig13_kano_layers"] = {
        "type": "scatter-kano-panels",
        "title": "三群人分別覺得哪些主題值得寫",
        "subtitle": "「捲動更多人」③ 與「留住夥伴」④ 對還沒接觸的人落在「無差別」，"
                     "對另外兩群都是「魅力」：沒進場的人感受不到團隊經營的痛",
        "denomNote": "每個面板都是完整的狩野四象限；同一個編號在三個面板中是同一個主題",
        "legend": [{"num": n, "label": C.KANO_SHORT[t]} for t, n in C.KANO_NUM.items()],
        "panels": panels13,
    }

    # ---------------- fig14：三層 × 議題領域 ----------------
    out["figures"]["fig14_domains"] = layered_grouped(
        "03_三層×議題領域.csv",
        "想先看哪些議題領域的資料清單",
        "此題複選，最多選 5 個領域｜各群的勾選率（分母為該群有作答人數）｜還沒接觸的人有 26 位",
        "從未接觸 26 人／接觸未參與 54 人／曾參與 47 人", topn=12)

    # ---------------- fig15：三層 × 跨領域工具 ----------------
    out["figures"]["fig15_tools"] = layered_grouped(
        "03_三層×跨領域工具.csv",
        "想看哪些跨領域工具的介紹",
        "此題複選，最多選 3 個工具｜各群的勾選率（分母為該群有作答人數）｜還沒接觸的人有 26 位",
        "從未接觸 26 人／接觸未參與 54 人／曾參與 47 人", topn=7)

    # ---------------- 輔助表：文中引用但非圖表的數字 ----------------
    gender = pd.read_csv(C.TABLE_DIR / "03_全體_性別分布.csv")
    out["tables"]["性別分布"] = rows(gender, ["性別", "人數", "分母", "比例"])

    ident = pd.read_csv(C.TABLE_DIR / "03_全體_身分分布.csv")
    out["tables"]["身分分布"] = rows(ident, ["身分", "人數", "分母", "比例"])

    g0v = pd.read_csv(C.TABLE_DIR / "03_全體_g0v參加經驗.csv")
    out["tables"]["g0v參加經驗"] = rows(g0v, ["分群", "類別", "分子", "分母", "比例"])

    fund_crit = pd.read_csv(C.TABLE_DIR / "03_出資者_評估準則.csv")
    out["tables"]["出資者評估準則"] = rows(fund_crit, ["選項", "票數", "分母", "比例"])

    fund_stage = pd.read_csv(C.TABLE_DIR / "03_出資者_資源沙漠階段.csv")
    out["tables"]["出資者資源沙漠階段"] = rows(fund_stage, ["選項", "票數", "分母", "比例"])

    role_overlap = pd.read_csv(C.TABLE_DIR / "03_角色_動手做但沒用過.csv")
    out["tables"]["角色_動手做但沒用過"] = rows(role_overlap, ["類別", "分子", "分母", "比例"])

    open_summary = pd.read_csv(C.TABLE_DIR / "09_開放題_總表.csv")
    out["tables"]["開放題總表"] = rows(
        open_summary, ["題目", "主題", "筆數", "分母", "比例"])

    region_link = pd.read_csv(C.TABLE_DIR / "09_開放題_地區連結.csv")
    out["tables"]["開放題地區連結"] = rows(region_link, ["主題", "筆數", "分母", "比例"])

    region_link_twin = pd.read_csv(C.TABLE_DIR / "09_開放題_地區連結×雙北.csv")
    out["tables"]["開放題地區連結×雙北"] = rows(
        region_link_twin, ["主題", "全體有填答者中的人數", "全體有填答者", "住雙北且有此連結", "住雙北人數"])

    path = WEB_DATA_DIR / "figures.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 同時輸出 .js 版本：網頁用 <script src> 載入，不用 fetch。
    # 原因：file:// 開啟本機 HTML 時，fetch() 讀同層 json 會被瀏覽器 CORS 擋下，
    # 但 <script src="data/figures.js"> 沒有這個限制，離線、雙擊開檔都能跑（D1／D2）。
    js_path = WEB_DATA_DIR / "figures.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("// 由 13_web_data.py 自動產生，不要手改。\n")
        f.write("window.FIGDATA = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")

    print(f"→ 已輸出 {path} 與 {js_path.name}"
          f"（{len(out['figures'])} 張圖、{len(out['tables'])} 個輔助表）")


if __name__ == "__main__":
    main()
