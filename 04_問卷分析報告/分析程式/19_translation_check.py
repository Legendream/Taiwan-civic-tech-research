# -*- coding: utf-8 -*-
"""
19_translation_check.py — 逐段核對英文譯稿的數字和中文版一致。

翻譯最怕的不是文筆，是數字在翻的過程中被改掉、漏掉或多出來。這支腳本拿
英文完整版譯稿和中文改稿包（＝目前中文網頁），用同一個段落編號逐段比對：
每段裡出現的數字（含百分比、分子分母、人數）必須一模一樣。

中英文寫法本來就不同的地方（中文用「第三章」、英文用「Chapter 3」；
中文「近九成」英文寫「nine in ten」），列在 EXPECTED 裡逐條說明；
沒有說明的差異一律讓腳本失敗。

另外檢查：
  · 段落編號：譯稿要涵蓋中文版除圖表以外的全部段落
  · 連結網址：每段的網址要和中文版一致（列在 LINK_CHANGES 的刻意更動除外）
  · 粗體段數：中文有粗體的段落，英文也要有

執行：python3 19_translation_check.py
"""

import re
import sys
from collections import Counter
from pathlib import Path

import common as C

HERE = Path(__file__).parent


def _load(name, file):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RT = _load("rt", "16_copyedit_roundtrip.py")

ZH = C.OUT_DIR / "改稿包" / "改稿稿件.md"
EN = C.OUT_DIR / "英文版" / "完整版譯稿.md"

# 中英寫法不同、但不是錯誤的數字差異：(段落) → {"zh": [...], "en": [...], "why": 說明}
# zh／en 列的是「只出現在該語言」的數字
EXPECTED = {
    "nav": {"zh": [], "en": ['1', '2', '3', '4', '5', '6', '7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "top-04": {"zh": ['7'], "en": [], "why": "日期寫法：中文 2026/7/20，英文 20 July 2026"},
    "intro-03": {"zh": ['07'], "en": [], "why": "日期寫法：中文 2026/07/20，英文 20 July 2026"},
    "intro-04": {"zh": [], "en": ['19'], "why": "〔脈絡〕中文「疫情期間」，英文寫明 COVID-19 讓國際讀者知道是哪一場疫情"},
    "persona-route-newcomer": {"zh": [], "en": ['1', '1', '7', '7', '7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "persona-route-doing": {"zh": [], "en": ['3', '3', '4', '4', '5', '5'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "persona-route-funder": {"zh": [], "en": ['6', '6'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "summary-02": {"zh": [], "en": ['1'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "summary-04": {"zh": [], "en": ['2'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "summary-06": {"zh": [], "en": ['3'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "summary-08": {"zh": [], "en": ['4'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch1-02": {"zh": [], "en": ['1', '60'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字；「逾六成」英文寫 over 60%"},
    "ch2-01": {"zh": [], "en": ['2'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch2-2-04": {"zh": [], "en": ['7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch2-2-05": {"zh": [], "en": ['3', '5'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch3-01": {"zh": [], "en": ['3'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch4-01": {"zh": [], "en": ['4'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch4-1-06": {"zh": [], "en": ['20'], "why": "英文多寫一次「Of the original 20」，指同一段的 20 人，讓 6 人（30%）的分母清楚"},
    "ch5-01": {"zh": [], "en": ['5'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch5-2-04": {"zh": [], "en": ['3', '7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch5-3-04": {"zh": [], "en": ['3'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch6-01": {"zh": [], "en": ['6'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "ch7-01": {"zh": [], "en": ['7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "rec-1-02": {"zh": [], "en": ['1'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "rec-1-3-05": {"zh": [], "en": ['7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "rec-1-4-04": {"zh": [], "en": ['6'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "rec-1-4-05": {"zh": [], "en": ['5'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "rec-1-4-06": {"zh": [], "en": ['3', '4'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "reflect-1-02": {"zh": [], "en": ['1'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "reflect-1-04": {"zh": [], "en": ['1', '4', '4', '5', '6', '7'], "why": "中文用國字章節編號（第三章、一、），英文用阿拉伯數字"},
    "about-07": {"zh": ['7'], "en": [], "why": "日期寫法：中文 2026/7/20，英文 20 July 2026"},
    "about-05": {"zh": ['0'], "en": [], "why": "g0v 名稱由來：中文寫「把 gov 的 o 換成 0」，英文寫 a zero"},
}

# 刻意拿掉的連結：(段落, 中文網址)。中文同一句連續連了兩次 g0v.tw，英文句構只需要一次
LINK_REMOVED = {("intro-02", "https://g0v.tw/")}

# 刻意更動的連結：(段落, 中文網址) → 英文網址
LINK_CHANGES = {
    ("top-05", "https://claire-cheng.com/zh"): "https://claire-cheng.com/en",
    ("about-02", "https://claire-cheng.com/zh"): "https://claire-cheng.com/en",
    ("about-06", "https://claire-cheng.com/zh"): "https://claire-cheng.com/en",
}

NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
LINK_RE = re.compile(r"\]\(([^)]*)\)")


def numbers(text):
    t = LINK_RE.sub("]", text)          # 網址裡的數字不算
    return Counter(NUM_RE.findall(t))


def main():
    zh = dict(RT.parse_draft(ZH))
    en = dict(RT.parse_draft(EN))
    problems, explained = [], []

    missing = [k for k in zh if k not in en and not k.startswith("fig-")]
    if missing:
        problems.append(f"譯稿缺少段落：{missing}")
    extra = [k for k in en if k not in zh]
    if extra:
        problems.append(f"譯稿多出中文版沒有的段落：{extra}")

    for k, e in en.items():
        if k not in zh:
            continue
        z = zh[k]
        only_zh = numbers(z) - numbers(e)
        only_en = numbers(e) - numbers(z)
        if only_zh or only_en:
            exp = EXPECTED.get(k)
            got = {"zh": sorted(only_zh.elements()), "en": sorted(only_en.elements())}
            if exp and sorted(exp["zh"]) == got["zh"] and sorted(exp["en"]) == got["en"]:
                explained.append(f"[{k}] {exp['why']}")
            else:
                problems.append(f"[{k}] 數字不一致：只在中文 {got['zh']}、只在英文 {got['en']}")
        zl = [LINK_CHANGES.get((k, u), u) for u in LINK_RE.findall(z)]
        for kk, u in LINK_REMOVED:
            if kk == k and u in zl:
                zl.remove(u)
        el = LINK_RE.findall(e)
        if Counter(zl) != Counter(el):
            problems.append(f"[{k}] 連結不一致：中文 {zl}、英文 {el}")
        if ("**" in z) != ("**" in e):
            problems.append(f"[{k}] 粗體不一致（中文{'有' if '**' in z else '沒有'}、英文{'有' if '**' in e else '沒有'}）")

    stale = [k for k in EXPECTED if k not in [p.split("]")[0][1:] for p in explained]]
    if stale:
        problems.append(f"EXPECTED 有用不到的條目：{stale}")

    print(f"核對 {len(en)} 段：已說明的寫法差異 {len(explained)} 處、問題 {len(problems)} 處")
    for x in explained:
        print("  ✓", x)
    for p in problems:
        print("  ✗", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
