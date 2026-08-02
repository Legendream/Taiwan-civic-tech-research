# -*- coding: utf-8 -*-
"""
14_web_number_check.py — 稽核展示網頁上出現的每一個百分比。

依開發五站流程站③自我驗證的要求（同 06_number_index.py 的精神）：
網頁上的數字不能是手打出來的、對不上資料就要讓腳本失敗。

⚠️ 裸百分比（沒有附 n/d 的「N%」）用的是寬鬆檢查：只驗證這個數值在全部
   分析結果/*.csv 或 99_數字索引.csv 裡「存在某處」，不驗證它對應的是報告裡
   「正確的那一格」（例如相對變化率「−15%」這類非簡單分子分母的衍生指標）。
   這類值本次是逐句核對報告定稿抄錄過來的，可信度來自報告本文已通過的
   06_number_index.py 稽核；帶 n/d 的百分比（本腳本佔多數）才是嚴格逐一核對。

分兩層稽核：
  1. docs/data/figures.json 內部一致性——每個圖表資料點的「比例」都必須等於
     「分子/分母」，抓的是 13_web_data.py 算錯或資料被手動改過的情形。
  2. docs/index.html 正文裡手寫的百分比——每一處「N%」或「N%（a/b）」，
     都要能在 分析結果/*.csv 或 99_數字索引.csv 裡找到對應的分子／分母組合，
     抓的是「照抄報告文字時改動了數字」的情形。

圖表本身的數字（由 JS 在瀏覽器端從 figures.json 動態產生）不會出現在
index.html 的原始檔案文字裡，所以這支腳本天生只查得到「手寫進 HTML 的數字」，
剛好就是需要人工核對、容易手滑的那些。

執行：python3 14_web_number_check.py
"""

import json
import re
import sys

import pandas as pd

import common as C

DOCS_DIR = C.PROJ / "docs"
REPORT_MD = C.OUT_DIR / "公民科技生態系分析報告_定稿.md"
FIGURES_JSON = DOCS_DIR / "data" / "figures.json"
INDEX_HTML = DOCS_DIR / "index.html"

FAIL = []


def fail(msg):
    FAIL.append(msg)


# ---------------------------------------------------------------- 第一層：figures.json 內部一致性

def check_figures_json():
    data = json.loads(FIGURES_JSON.read_text(encoding="utf-8"))
    checked = 0

    def check_frac(label, n, d, pct, tol=0.002):
        nonlocal checked
        if d == 0:
            return
        checked += 1
        expect = n / d
        if abs(expect - pct) > tol:
            fail(f"[figures.json] {label}：n/d={n}/{d}={expect:.4f}，但存的 pct={pct:.4f}")

    for key, fig in data["figures"].items():
        t = fig["type"]
        if t in ("hbar", "donut"):
            for it in fig["items"]:
                check_frac(f"{key} / {it['label']}", it["n"], it["d"], it["pct"])
        elif t == "stacked-hbar":
            for it in fig["items"]:
                check_frac(f"{key} / {it['label']} (3+)", it["n3plus"], it["d"], it["pct3plus"])
                check_frac(f"{key} / {it['label']} (4+)", it["n4plus"], it["d"], it["pct4plus"])
        elif t == "diverging":
            for panel in fig["panels"]:
                for it in panel["items"]:
                    check_frac(f"{key} / {panel['group']} / {it['label']}",
                               it["n"], it["d"], it["groupPct"])
                    expect_diff = round((it["groupPct"] - it["basePct"]) * 100, 1)
                    checked += 1
                    if abs(expect_diff - round(it["diffPts"], 1)) > 0.15:
                        fail(f"[figures.json] {key} / {it['label']}：diffPts 應為 "
                             f"{expect_diff}，但存的是 {it['diffPts']}")
        elif t == "grouped-hbar-layers":
            for opt in fig["options"]:
                for layer, d in opt["byLayer"].items():
                    check_frac(f"{key} / {opt['label']} / {layer}", d["n"], d["d"], d["pct"])
        elif t in ("scatter-kano",):
            for it in fig["items"]:
                checked += 1
                if not (0 <= it["si"] <= 1 and -1 <= it["dsi"] <= 0):
                    fail(f"[figures.json] {key} / {it['label']}：SI/DSI 超出合理範圍 "
                         f"({it['si']}, {it['dsi']})")
        elif t == "scatter-kano-panels":
            for panel in fig["panels"]:
                for it in panel["items"]:
                    checked += 1
                    if not (0 <= it["si"] <= 1 and -1 <= it["dsi"] <= 0):
                        fail(f"[figures.json] {key} / {panel['layer']} / {it['label']}："
                             f"SI/DSI 超出合理範圍")
    return checked


# ---------------------------------------------------------------- 第二層：index.html 正文手寫數字

def strip_html(raw):
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return raw


def build_ground_truth():
    """回傳 (pair_set, pct_value_set)：
    pair_set = 所有 CSV 裡出現過的 (分子, 分母) 組合。
    pct_value_set = 所有 CSV 裡「比例」欄或 99_數字索引「數字」欄換算出的百分比數值。
    """
    pair_set = set()
    pct_values = set()

    num_cols = ["分子", "票數", "筆數", "人數", "全體有填答者中的人數", "住雙北且有此連結"]
    den_cols = ["分母", "群體N", "全體有填答者", "住雙北人數"]

    for csv_path in sorted(C.TABLE_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        except Exception:
            continue
        cols = df.columns
        for nc in num_cols:
            if nc not in cols:
                continue
            for dc in den_cols:
                if dc not in cols:
                    continue
                for n_raw, d_raw in zip(df[nc], df[dc]):
                    try:
                        n, d = int(float(n_raw)), int(float(d_raw))
                        if d > 0:
                            pair_set.add((n, d))
                    except ValueError:
                        continue
        # 任何看起來是「比例」的欄位都收，不只有叫「比例」的欄——
        # 04_動機_流向.csv 的「留存率」、「初次_比例」、「持續_比例」都是同類數字，
        # 只認字面叫「比例」的欄會漏掉這些同樣經過稽核的數字。
        ratio_cols = [c for c in cols if "比例" in c or c.endswith("率")]
        for rc in ratio_cols:
            for v in df[rc]:
                try:
                    pct_values.add(round(float(v) * 100, 1))
                except ValueError:
                    continue

    index_csv = C.TABLE_DIR / "99_數字索引.csv"
    if index_csv.exists():
        idx = pd.read_csv(index_csv, dtype=str, keep_default_na=False)
        for n_raw, d_raw, num_raw in zip(idx["分子"], idx["分母"], idx["數字"]):
            try:
                n, d = int(float(n_raw)), int(float(d_raw))
                if d > 0:
                    pair_set.add((n, d))
            except ValueError:
                pass
            m = re.match(r"([\d.]+)%", str(num_raw))
            if m:
                pct_values.add(round(float(m.group(1)), 1))

    return pair_set, pct_values


PCT_WITH_FRAC = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*[（(]\s*(\d+)\s*/\s*(\d+)\s*[）)]")
PCT_BARE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def check_index_html(pair_set, pct_values):
    raw = INDEX_HTML.read_text(encoding="utf-8")
    visible = strip_html(raw)

    # 先找「N%（a/b）」，把命中的範圍記下來，剩下的裸 % 才用寬鬆規則查
    consumed_spans = []
    frac_checked = 0
    for m in PCT_WITH_FRAC.finditer(visible):
        consumed_spans.append((m.start(), m.end()))
        pct, n, d = float(m.group(1)), int(m.group(2)), int(m.group(3))
        frac_checked += 1
        expect = 100 * n / d
        if abs(expect - pct) > 0.6:
            fail(f"[index.html] 「{m.group(0)}」：{n}/{d} 應約為 {expect:.1f}%，"
                 f"與標示的 {pct}% 對不上")
            continue
        if (n, d) not in pair_set:
            fail(f"[index.html] 「{m.group(0)}」：找不到任何一份 分析結果/*.csv "
                 f"或 99_數字索引.csv 有 {n}/{d} 這組分子分母")

    def in_consumed(pos):
        return any(s <= pos < e for s, e in consumed_spans)

    bare_checked = 0
    for m in PCT_BARE.finditer(visible):
        if in_consumed(m.start()):
            continue
        bare_checked += 1
        pct = float(m.group(1))
        # 容差 0.6：報告正文常把 CSV 的一位小數（如 65.4%）四捨五入寫成整數（65%），
        # 標準四捨五入誤差上限是 0.5，多留一點浮點數安全邊界。
        if not any(abs(pct - v) <= 0.6 for v in pct_values):
            fail(f"[index.html] 裸百分比「{m.group(0)}」：在所有 分析結果/*.csv 的「比例」欄"
                 f"或 99_數字索引.csv 的「數字」欄裡，都找不到約 {pct}% 這個值")

    return frac_checked, bare_checked


def main():
    print("== 第一層：figures.json 內部一致性 ==")
    n1 = check_figures_json()
    print(f"  檢查了 {n1} 個資料點")

    print("== 建立稽核用的分子分母／比例值集合 ==")
    pair_set, pct_values = build_ground_truth()
    print(f"  {len(pair_set)} 組 (分子,分母)、{len(pct_values)} 個相異比例值")

    print("== 第二層：docs/index.html 正文的手寫百分比 ==")
    n2, n3 = check_index_html(pair_set, pct_values)
    print(f"  帶分子分母的百分比 {n2} 處、裸百分比 {n3} 處")

    print()
    if FAIL:
        print(f"❌ 共 {len(FAIL)} 處未通過：")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    else:
        total = n1 + n2 + n3
        print(f"✅ 全部通過（共核對 {total} 處數字）")


if __name__ == "__main__":
    main()
