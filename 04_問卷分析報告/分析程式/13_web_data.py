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


# 網頁上三群的稱呼（好奇者／使用者／實作者，對應英文版 Curious／Users／Builders）。
# 只用於網頁圖表；報告 PNG 圖仍用 common.LAYER_PLAIN，CSV 的分群鍵值一律不動。
WEB_LAYER_PLAIN = {C.L_NEVER: "好奇者", C.L_AWARE: "使用者", C.L_DONE: "實作者"}


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
            "pct": round(float(r[value_col]), 6),
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


def exact_ratios(out):
    """有分子分母的比例，一律改用分子÷分母重算。

    分析結果/*.csv 的比例欄只存到小數第 4 位（例如 14/26 存成 0.5385），
    charts.js 再四捨五入到小數 1 位就變成 53.9%，但 14/26 實際是 53.85%→53.8%。
    兩次四捨五入會讓少數格子的尾數差 0.1，所以網頁資料不沿用 CSV 的比例欄。
    """
    for fig in out["figures"].values():
        for it in fig.get("items") or []:
            if it.get("n") is not None and it.get("d") and "pct" in it:
                it["pct"] = it["n"] / it["d"]
            if "n3plus" in it:
                it["pct3plus"] = it["n3plus"] / it["d"]
                it["pct4plus"] = it["n4plus"] / it["d"]
        for opt in fig.get("options") or []:
            for v in opt["byLayer"].values():
                v["pct"] = v["n"] / v["d"]
        for panel in fig.get("panels") or []:
            for it in panel["items"]:
                if "groupPct" in it:
                    it["groupPct"] = it["n"] / it["d"]


# ---------------------------------------------------------------- 英文版

EN_TERMS = C.OUT_DIR / "英文版" / "圖表與介面譯名.csv"
# 同一個中文字串在不同圖表裡意思不同時，依圖表另外指定（狩野圖的「發起專案」是文章主題簡稱，不是參與深度）
EN_PER_FIGURE = {
    "fig12_kano_all": {"發起專案": "Starting a project"},
    "fig13_kano_layers": {"發起專案": "Starting a project"},
}
# 會顯示在畫面上的欄位；其他欄位（layerOrder、byLayer 的鍵、panels 的 layer）是程式內部的鍵，不翻
EN_DISPLAY_KEYS = {"title", "subtitle", "denomNote", "label", "shortLabel", "fullLabel",
                   "group", "escapeLabel", "quadrant", "主題", "選項"}


def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def build_english(out):
    """以中文版資料為底，只換顯示文字；數字完全共用，不會對不上。"""
    import copy
    terms = pd.read_csv(EN_TERMS, dtype=str).set_index("中文")["英文"].to_dict()
    en = copy.deepcopy(out)
    missing = set()

    def tr(val, fig=None):
        val_key = val
        if fig and val_key in EN_PER_FIGURE.get(fig, {}):
            return EN_PER_FIGURE[fig][val_key]
        if val_key in terms:
            return terms[val_key]
        missing.add(val_key)
        return val

    def walk(node, fig=None):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in EN_DISPLAY_KEYS and isinstance(v, str) and has_cjk(v):
                    node[k] = tr(v, fig)
                elif k == "seriesLabels":
                    node[k] = [tr(x, fig) for x in v]
                else:
                    walk(v, fig)
        elif isinstance(node, list):
            for x in node:
                walk(x, fig)

    for fid, fig in en["figures"].items():
        walk(fig, fid)
    # 三群的英文名從報告用的中文標籤翻（中文網頁的「使用者」和角色短名同字，不能直接查表）
    en["layerPlain"] = {k: tr(C.LAYER_PLAIN[k]) for k in en["layerPlain"]}
    for it in en["figures"]["fig01_layers"]["items"]:
        it["label"] = en["layerPlain"][it["key"]]
    for t in ("開放題總表", "出資者評估準則"):
        walk(en["tables"][t])
    en["meta"]["sample_note"] = "Data: 127 valid survey responses collected up to 20 July 2026"
    if missing:
        raise SystemExit("英文對照表缺少這些圖表文字（請補進 英文版/圖表與介面譯名.csv）：\n  "
                         + "\n  ".join(sorted(missing)))
    return en


def write_data(obj, stem):
    path = WEB_DATA_DIR / f"{stem}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    # 同時輸出 .js 版本：網頁用 <script src> 載入，不用 fetch。
    # 原因：file:// 開啟本機 HTML 時，fetch() 讀同層 json 會被瀏覽器 CORS 擋下，
    # 但 <script src="data/figures.js"> 沒有這個限制，離線、雙擊開檔都能跑（D1／D2）。
    js_path = WEB_DATA_DIR / f"{stem}.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("// 由 13_web_data.py 自動產生，不要手改。\n")
        f.write("window.FIGDATA = ")
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    return path, js_path


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
        "layerPlain": WEB_LAYER_PLAIN,
        "figures": {},
        "tables": {},
    }

    # ---------------- fig01：入坑分層（甜甜圈） ----------------
    lay = pd.read_csv(C.TABLE_DIR / "01_入坑分層分布.csv")
    out["figures"]["fig01_layers"] = {
        "type": "donut",
        "title": "127 位填答者分成三群",
        "subtitle": "分母＝全體 127 人（綠：好奇者、橘：使用者、藍：實作者）",
        "items": [
            {"label": WEB_LAYER_PLAIN[r["分層"]], "key": r["分層"],
             "pct": round(float(r["比例"]), 6), "n": int(r["人數"]), "d": int(r["分母"])}
            for _, r in lay.iterrows()
        ],
    }

    # ---------------- fig02：居住地分布 ----------------
    out["figures"]["fig02_region"] = hbar_dataset(
        "03_全體_居住地.csv", "選項", "比例", "票數",
        "填答者的居住地分布",
        "全體 N=127，雙北合計逾六成",
        "分母＝全體 127 人")
    twin = pd.read_csv(C.TABLE_DIR / "03_全體_居住地_雙北合計.csv").iloc[0]
    out["tables"]["雙北合計"] = {
        "n": int(twin["分子"]), "d": int(twin["分母"]), "pct": round(float(twin["比例"]), 6),
    }

    # ---------------- fig03：角色分布 ----------------
    roles = pd.read_csv(C.TABLE_DIR / "03_全體_角色勾選.csv")
    roles = roles[roles["選項"].isin(C.ROLE_LADDER)].copy()
    roles = roles.set_index("選項").loc[C.ROLE_LADDER].reset_index()
    out["figures"]["fig03_roles"] = {
        "type": "hbar",
        "title": "曾擔任過的角色（複選，由淺到深排列）",
        "subtitle": "分母＝101 位曾接觸者（複選，加總超過 100%）",
        "denomNote": "分母＝101 位曾接觸公民科技者",
        "sortByOrder": True,
        "items": [
            {"label": r["選項"], "shortLabel": C.ROLE_SHORT[r["選項"]],
             "pct": round(float(r["比例"]), 6), "n": int(r["票數"]), "d": int(r["分母"])}
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
        "title": "參與深度分布：四成的人只落在第一階",
        "subtitle": "分母＝101 位曾接觸者（灰色選項不在深度軸上、未計權重）",
        "denomNote": "分母＝101 位曾接觸公民科技者",
        "sortByOrder": True,
        "escapeLabel": "以上都不太像我",
        "items": [
            {"label": r["類別"], "pct": round(float(r["比例"]), 6),
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
        "title": "各項困難的困擾程度分布（完整呈現 1 到 5 分）",
        "subtitle": "依「3 分以上人數」由多到少排列（無「沒遇到」選項，評 1 分包含「沒發生過」與「發生了但不影響」）",
        "denomNote": "分母＝47 位實作者（每題皆為 47 人作答）",
        "seriesLabels": ["1：幾乎沒影響", "2：有點困擾但還能處理", "3：明顯卡住我、拖慢進度",
                          "4：受挫到萌生退意", "5：困擾到專案無法持續"],
        "seriesColors": C.PALETTE["trouble_scale"],
        "items": [
            {
                "label": r["困難"],
                "d": int(r["合計"]),
                "counts": [int(r[c]) for c in score_cols],
                "pct3plus": round(float(r["3分以上_比例"]), 6),
                "n3plus": int(r["3分以上_合計"]),
                "pct4plus": round(float(r["4分以上_比例"]), 6),
                "n4plus": int(r["4分以上_合計"]),
            }
            for _, r in dist.iterrows()
        ],
    }

    # ---------------- fig06：年齡×持續動機（雙向橫條，三面板） ----------------
    lf = pd.read_csv(C.TABLE_DIR / "03_年齡×持續動機_lift.csv")
    lf = lf[lf["選項"].isin(C.MOTIVES)].copy()
    # 全體比例改用「持續動機人數 ÷ 47」重算：CSV 的「全體比例」只存到小數第 4 位
    flow = pd.read_csv(C.TABLE_DIR / "04_動機_流向.csv").set_index("動機")
    base = {m: int(flow.loc[m, "持續_人數"]) / int(flow.loc[m, "分母"]) for m in flow.index}
    panels = []
    for age in C.AGE_COARSE_ORDER:
        d = lf[lf["分群"] == age].copy()
        if d.empty:
            continue
        denom = int(d["分母"].iloc[0])
        d["群內比例"] = d["分子"] / d["分母"]
        d["全體比例"] = d["選項"].map(base)
        d["高出百分點"] = (d["群內比例"] - d["全體比例"]) * 100
        d = d.sort_values("高出百分點", ascending=False)
        panels.append({
            "group": age,
            "d": denom,
            "items": [
                {"label": r["選項"], "n": int(r["分子"]), "d": int(r["分母"]),
                 "groupPct": round(float(r["群內比例"]), 6),
                 "basePct": round(float(r["全體比例"]), 6),
                 "diffPts": round(float(r["高出百分點"]), 2)}
                for _, r in d.iterrows()
            ],
        })
    out["figures"]["fig06_age_motive"] = {
        "type": "diverging",
        "title": "不同世代留在專案的動機差異",
        "subtitle": "各長條代表該世代勾選比例與全體 47 人的差距（百分點）。向右為高於全體，向左為低於全體。",
        "denomNote": "三個年齡層分別為 10、19、18 人（可複選）",
        "panels": panels,
    }

    # ---------------- fig07：資源 ----------------
    out["figures"]["fig07_resources"] = hbar_dataset(
        "03_全體_資源.csv", "選項", "比例", "票數",
        "實作者用過哪些資源",
        "分母＝47 位實作者（複選，加總超過 100%）",
        "分母＝47 位實作者")

    # ---------------- fig08：專長 ----------------
    out["figures"]["fig08_skills"] = hbar_dataset(
        "03_全體_專長.csv", "選項", "比例", "票數",
        "實作者貢獻過哪些專長",
        "分母＝47 位實作者（複選，加總超過 100%，常見一人多工）",
        "分母＝47 位實作者")

    # ---------------- fig09：g0v 消息管道 ----------------
    out["figures"]["fig09_channel"] = hbar_dataset(
        "03_全體_g0v消息管道.csv", "選項", "比例", "票數",
        "填答者從哪裡得知 g0v.tw 的活動消息",
        "全體 N=127（複選）。「親友推薦」與「g0v 社群管道」並列單選第一（各 51 人）；五個官方管道合計觸及 65%，高於親友推薦的 40%",
        "分母＝全體 127 人", min_votes=3)

    # ---------------- fig10：未參與原因 ----------------
    out["figures"]["fig10_notjoin"] = hbar_dataset(
        "03_未參與原因.csv", "選項", "比例", "票數",
        "好奇者還沒參與，是什麼擋住了他們",
        "最多選 3 項。分母＝26 位好奇者（54 位使用者未問此題）",
        "分母＝26 位好奇者")

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
                    "pct": round(float(r["群內比例"]), 6),
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
        "複選，最多選 2 個。各群長條代表該群勾選率",
        "好奇者 26 人、使用者 54 人、實作者 47 人")

    # ---------------- fig12：狩野落點（全體，散佈圖） ----------------
    kano_all = pd.read_csv(C.TABLE_DIR / "02_狩野_全體.csv")
    out["figures"]["fig12_kano_all"] = {
        "type": "scatter-kano",
        "title": "五個文章主題的狩野落點（全體填答者）",
        "subtitle": "N=126｜SI 0–1、DSI 0～−1 全幅，分界線 0.5／−0.5 位於正中央。五個主題全部落在「魅力 A」，其中「落地、接進體制」最靠近期望 O 邊界",
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
        "subtitle": "「捲動更多人」③ 與「留住夥伴」④ 對好奇者落在「無差別」，對另外兩群人都是「魅力」：沒進場的人感受不到團隊經營的痛",
        "denomNote": "每個面板都是完整的狩野四象限；同一個編號在三個面板中代表同一個主題",
        "legend": [{"num": n, "label": C.KANO_SHORT[t]} for t, n in C.KANO_NUM.items()],
        "panels": panels13,
    }

    # ---------------- fig14：三層 × 議題領域 ----------------
    out["figures"]["fig14_domains"] = layered_grouped(
        "03_三層×議題領域.csv",
        "各群填答者最想先看哪些議題領域的資料清單",
        "此題複選，最多選 5 個領域｜各群勾選率（分母為該群有作答人數）｜好奇者有 26 位",
        "好奇者 26 人、使用者 54 人、實作者 47 人", topn=12)

    # ---------------- fig15：三層 × 跨領域工具 ----------------
    out["figures"]["fig15_tools"] = layered_grouped(
        "03_三層×跨領域工具.csv",
        "各群填答者最想看哪些跨領域工具的介紹",
        "此題複選，最多選 3 個工具｜各群勾選率（分母為該群有作答人數）｜好奇者有 26 位",
        "好奇者 26 人、使用者 54 人、實作者 47 人", topn=7)

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

    exact_ratios(out)

    path, js_path = write_data(out, "figures")
    write_data(build_english(out), "figures_en")

    print(f"→ 已輸出 {path} 與 {js_path.name}，以及英文版 figures_en.json／.js"
          f"（{len(out['figures'])} 張圖、{len(out['tables'])} 個輔助表）")


if __name__ == "__main__":
    main()
