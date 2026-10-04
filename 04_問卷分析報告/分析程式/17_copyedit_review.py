# -*- coding: utf-8 -*-
"""
17_copyedit_review.py — 檢查改稿者交回的稿件，有沒有改到不該改的東西。

拿 改稿包/改稿稿件.md（匯出的原稿）和交回的稿件逐段比對，用程式抓得到的問題全部列出：
  1. 段落編號：有沒有少段、多段、順序變了
  2. 事實卡與稿件結構：正文以外的文字（事實卡、標題、標記）有沒有被動到
  3. 數字：改寫後新出現的數字，必須是原段落或事實卡裡就有的；原本的數字消失也列出
  4. 〔鎖〕〔維持〕引號：內容和數量都要一模一樣
  5. 連結網址：不能改
  6. 破折號：全篇不能有
  7. 因果字眼變多、推測字眼變少：列出來給人判斷（不一定是錯，但最容易在這裡悄悄改變意思）
  8. 表格：列數、欄數不變

程式只負責抓「看得出來的」問題。改寫後的意思有沒有變、有沒有擴大範圍、
有沒有加入事實卡沒有的說法，仍然要逐段人工對照事實卡判斷，報告最後附上每一段的改前改後。

執行：python3 17_copyedit_review.py <交回的稿件路徑> [輸出報告路徑]
"""

import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

import common as C

HERE = Path(__file__).parent
ORIGINAL = C.OUT_DIR / "改稿包" / "改稿稿件.md"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RT = _load("rt", "16_copyedit_roundtrip.py")
EX = _load("ex", "15_copyedit_export.py")

CAUSAL = ["因為", "由於", "導致", "造成", "所以", "因此", "因而", "使得", "於是", "證明", "顯示出"]
HEDGE = ["可能", "或許", "也許", "極可能", "推測", "似乎", "大概", "傾向", "或是"]
DASH_RE = re.compile(r"——|—|－－")
MARK_RE = re.compile(r"〔(鎖|維持)〕「([^」]*)」")
LINK_RE = re.compile(r"\]\(([^)]*)\)")


def fact_cards(path):
    """每段正文結束之後、到下一段開始之前的文字（事實卡、標題）。"""
    text = path.read_text(encoding="utf-8")
    return RT.BLOCK_RE.sub(lambda m: f"<!-- 正文 {m.group(1)} -->", text)


def card_of(path, bid):
    """這一段的事實卡，加上所在區段開頭的「本節共通界線」。"""
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"<!-- 正文結束 {re.escape(bid)} -->\n(.*?)(?=\n### \[|\n---\n|\Z)", text, re.S)
    card = m.group(1) if m else ""
    start = text.find(f"<!-- 正文開始 {bid} -->")
    sec = text.rfind("\n## ", 0, start)
    note = re.search(r"本節共通界線.*", text[sec:start]) if sec >= 0 else None
    return card + ("\n" + note.group(0) if note else "")


def numbers(text):
    t = re.sub(r"\]\([^)]*\)", "]", text)
    return [re.sub(r"\s", "", m.group(0)) for m in EX.TOKEN_RE.finditer(t)]


def number_values(text):
    """抽出文字裡出現過的所有數值（給「新數字是否在事實卡裡」用）。
    事實卡的百分比多帶一位小數（51.9%），正文常寫成整數（52%），所以把四捨五入後的整數也算進去。"""
    vals = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"\]\([^)]*\)", "]", text)))
    return vals | {str(int(float(v) + 0.5)) for v in vals if "." in v}


def table_shape(text):
    rows = [ln for ln in text.split("\n") if ln.strip().startswith("|")
            and not re.fullmatch(r"\|(-+\|)+", ln.strip())]
    return [len(r.strip().strip("|").split("|")) for r in rows]


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：python3 17_copyedit_review.py <交回的稿件> [輸出報告]")
    returned = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else returned.parent / "檢查報告.md"

    orig = RT.parse_draft(ORIGINAL)
    new = RT.parse_draft(returned)
    a, b = dict(orig), dict(new)
    problems, warnings = [], []

    # 1. 段落編號
    missing = [k for k in a if k not in b]
    extra = [k for k in b if k not in a]
    if missing:
        problems.append(f"少了段落：{missing}")
    if extra:
        problems.append(f"多出段落：{extra}")
    if [k for k, _ in orig if k in b] != [k for k, _ in new if k in a]:
        problems.append("段落順序和原稿不同")

    # 2. 事實卡與結構
    if fact_cards(ORIGINAL) != fact_cards(returned):
        import difflib
        d = [ln for ln in difflib.unified_diff(fact_cards(ORIGINAL).split("\n"),
                                               fact_cards(returned).split("\n"), lineterm="", n=0)
             if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
        problems.append("正文以外的文字（事實卡、標題、標記）被改動：\n" +
                        "\n".join(f"    {ln[:160]}" for ln in d[:40]))

    changed = [k for k in a if k in b and a[k] != b[k]]
    per_block = {}
    for k in changed:
        o, n = a[k], b[k]
        notes = []
        card = card_of(ORIGINAL, k)
        # 3. 數字
        no, nn = Counter(numbers(o)), Counter(numbers(n))
        allowed = number_values(o) | number_values(card)
        for tok in nn - no:
            vals = set(re.findall(r"\d+(?:\.\d+)?", tok))
            if not vals <= allowed:
                notes.append(("問題", f"新出現的數字「{tok}」不在原段落或事實卡裡"))
            else:
                notes.append(("提醒", f"新寫出的數字「{tok}」（事實卡裡有，請確認用在正確的對象上）"))
        for tok in no - nn:
            notes.append(("提醒", f"原本的數字「{tok}」不見了"))
        # 4. 鎖定引號
        if Counter(MARK_RE.findall(o)) != Counter(MARK_RE.findall(n)):
            notes.append(("問題", f"〔鎖〕〔維持〕引號被改動：原 {MARK_RE.findall(o)} → 改 {MARK_RE.findall(n)}"))
        # 5. 連結
        if Counter(LINK_RE.findall(o)) != Counter(LINK_RE.findall(n)):
            notes.append(("問題", "連結網址被改動"))
        # 7. 因果與推測字眼
        for w in CAUSAL:
            if n.count(w) > o.count(w):
                notes.append(("提醒", f"因果字眼「{w}」變多（{o.count(w)} → {n.count(w)}）"))
        for w in HEDGE:
            if n.count(w) < o.count(w):
                notes.append(("提醒", f"推測字眼「{w}」變少（{o.count(w)} → {n.count(w)}）"))
        # 8. 表格
        if table_shape(o) != table_shape(n):
            notes.append(("問題", f"表格形狀改變：{table_shape(o)} → {table_shape(n)}"))
        per_block[k] = notes

    # 6. 破折號（全篇正文）
    for k, n in new:
        if DASH_RE.search(n) and not DASH_RE.search(a.get(k, "")):
            per_block.setdefault(k, []).append(("問題", "新增了破折號"))
        elif DASH_RE.search(n):
            per_block.setdefault(k, []).append(("提醒", "原稿就有破折號，改稿沒有拿掉"))

    n_prob = len(problems) + sum(1 for v in per_block.values() for lv, _ in v if lv == "問題")
    n_warn = sum(1 for v in per_block.values() for lv, _ in v if lv == "提醒")

    lines = [f"# 改稿檢查報告\n",
             f"> 由 `分析程式/17_copyedit_review.py` 產生。原稿：`改稿包/改稿稿件.md`；"
             f"交回稿：`{returned.name}`。\n",
             f"- 段落：原稿 {len(a)} 段、交回 {len(b)} 段，有改動的 {len(changed)} 段",
             f"- 程式抓到的**問題** {n_prob} 項、**提醒** {n_warn} 項（提醒不一定是錯，要人判斷）\n"]
    lines.append("## 一、整份稿件的問題\n")
    lines += [f"- {p}" for p in problems] or ["（無）"]
    lines.append("\n## 二、逐段改前改後\n")
    for k in changed:
        lines.append(f"### [{k}]\n")
        for lv, msg in per_block.get(k, []):
            lines.append(f"- **{lv}**：{msg}")
        lines.append(f"\n**改前**\n\n> {a[k]}\n\n**改後**\n\n> {b[k]}\n")
    others = [k for k in per_block if k not in changed and per_block[k]]
    if others:
        lines.append("## 三、沒有改動、但有提醒的段落\n")
        for k in others:
            lines += [f"- `[{k}]` {msg}" for _, msg in per_block[k]]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"有改動 {len(changed)} 段｜問題 {n_prob} 項｜提醒 {n_warn} 項")
    print(f"輸出：{out_path}")


if __name__ == "__main__":
    main()
