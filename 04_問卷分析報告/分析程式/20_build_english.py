# -*- coding: utf-8 -*-
"""
20_build_english.py — 產生英文網頁：精華版 docs/en/ 與完整版 docs/en/full/。

完整版：以中文完整版 docs/full/index.html 為模板，依段落編號換成英文譯稿
        （英文版/完整版譯稿.md），結構與中文版一模一樣。
        圖表讀 docs/data/figures_en.js（13_web_data.py 產生，數字與中文版共用）。
精華版：由 英文版/精華版.md 轉成網頁，版面沿用同一份 CSS。
介面文字：docs/js/i18n_en.js（圖表程式與 app.js 的英文文字、身分推薦）。

產生後會檢查：英文頁畫面上不能殘留中文（刻意保留的人名、資料授權名稱除外）。

執行：python3 20_build_english.py
"""

import html as htmllib
import json
import re
import sys
from pathlib import Path

import common as C

HERE = Path(__file__).parent


def _load(name, file):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EX = _load("ex", "15_copyedit_export.py")
RT = _load("rt", "16_copyedit_roundtrip.py")
AP = _load("ap", "18_copyedit_apply.py")

DOCS = C.PROJ / "docs"
EN_DIR = C.OUT_DIR / "英文版"
FULL_DRAFT = EN_DIR / "完整版譯稿.md"
SUMMARY_MD = EN_DIR / "精華版.md"
CTA_MD = EN_DIR / "行動呼籲.md"
SITE = "https://report.claire-cheng.com"

# 英文頁上刻意保留的中文（人名、資料授權的署名名稱）
ALLOWED_CJK = ["鄭婷宇", "臺灣公民科技推廣問卷填寫者", "零時政府"]

# 寫在 index.html 裡、不屬於任何段落的介面文字與屬性
HTML_UI = {
    ">跳到主要內容<": ">Skip to main content<",
    'aria-label="章節導覽"': 'aria-label="Contents"',
    'aria-label="依身分推薦閱讀"': 'aria-label="Reading suggestions by role"',
    "<summary>看完整說明</summary>": "<summary>Read more</summary>",
    '<span class="insight-label">重點</span>': '<span class="insight-label">Key point</span>',
    ">目錄<": ">Contents<",                      # 側欄標題與手機章節列的按鈕
    'aria-label="關閉目錄"': 'aria-label="Close contents"',
    ">已讀 0%<": ">0% read<",
    'id="dockPart">報告<': 'id="dockPart">Report<',
    'id="dockCh">封面<': 'id="dockCh">Cover<',
    'aria-label="127 位填答者：好奇者 26 人、使用者 54 人、實作者 47 人"':
        'aria-label="127 respondents: 26 Curious, 54 Users, 47 Builders"',
    ">127 份有效填答<": ">127 valid responses<",
    '<div class="bl-t">好奇者<': '<div class="bl-t">The Curious<',
    '<div class="bl-t">使用者<': '<div class="bl-t">The Users<',
    '<div class="bl-t">實作者<': '<div class="bl-t">The Builders<',
    'aria-label="照你的身分，挑這幾章先看"': 'aria-label="Where to start, based on who you are"',
    ">我是新手，還在了解這個圈子<": ">I'm new and still getting to know the community<",
    ">我正在做（或做過）公民科技專案<": ">I'm working on (or have worked on) a civic tech project<",
    ">我可能提供資源，或想支持社群經營<": ">I might provide resources, or want to support the community<",
    'data-label="本報告的結論"': 'data-label="This report\'s conclusion"',
    'data-label="另一種可能的解釋"': 'data-label="Another possible explanation"',
    '"%（" + r["票數"] + "/" + r["分母"] + "）"': '"% (" + r["票數"] + "/" + r["分母"] + ")"',
}

CHART_TEXT_EN = """{
  sep: ". ",
  wordWrap: true,
  maxLines: 3,
  score3Val: function (pct, n, d) { return "3+: " + pct + " (" + n + "/" + d + ")"; },
  pctFrac: function (pct, n, d) { return pct + " (" + n + "/" + d + ")"; },
  pctN: function (pct, n) { return pct + " (" + n + ")"; },
  gap: " ",
  score3Tip: "Rated 3 or higher: ",
  score4Tip: "Rated 4 or higher: ",
  peoplePct: function (n, pct) { return n + " people (" + pct + ")"; },
  people: function (n) { return n + " people"; },
  withN: function (lab, n) { return lab + " (" + n + ")"; },
  panelHead: function (group, d, up, down) {
    return group + " (" + d + " people): " + up + " above overall, " + down + " below";
  },
  diffTip: function (g, n, d, b, isUp, pts) {
    return "This group: " + g + " (" + n + "/" + d + ") | Overall: " + b + " | " + pts + " points " + (isUp ? "higher" : "lower");
  },
  kanoI: "Indifferent", kanoA: "Attractive", kanoM: "Must-be", kanoO: "Performance",
  viewTable: "View data table",
  thItems: ["Option", "Share", "Count", "Base"],
  thTrouble: ["Difficulty", "Rated 3+", "Rated 4+", "Base"],
  thAge: ["Age group", "Motive", "Group share", "Overall share", "Difference (points)"],
  thKano: ["Topic", "SI", "DSI", "Category"],
  thKanoLayers: ["Group", "Topic", "SI", "DSI", "Category"],
  thLayered: ["Option", "Group", "Share", "Count", "Base"],
  toggleAria: "Switch group view",
  allGroups: "All three groups",
  only: "Only: ",
  noData: "(Chart data not found: ",
  badType: "(Unsupported chart type: ",
  close: ")"
}"""

APP_TEXT_EN = {"tocTitle": "On this page", "startWith": "Start with:", "nextChapter": "Next chapter",
               "readPct": "{p}% read"}


def build_i18n(draft):
    """docs/js/i18n_en.js：圖表與 app.js 的英文文字，身分推薦取自譯稿。"""
    routes = {}
    for r in EX.parse_persona_routes():
        text = draft[f"persona-route-{r['key']}"]
        why, labels = AP.parse_persona(text)
        if len(labels) != len(r["sections"]):
            raise SystemExit(f"[persona-route-{r['key']}] 章節連結數和中文版不同")
        routes[r["key"]] = {"why": why, "sections": [[a, l] for (a, _), l in zip(r["sections"], labels)]}
    js = ("// 由 20_build_english.py 自動產生，不要手改。英文頁在 charts.js、app.js 之前載入。\n"
          f"window.CHART_TEXT = {CHART_TEXT_EN};\n"
          f"window.APP_TEXT = {json.dumps(APP_TEXT_EN, ensure_ascii=False, indent=1)};\n"
          f"window.PERSONA_ROUTES_OVERRIDE = {json.dumps(routes, ensure_ascii=False, indent=1)};\n")
    (DOCS / "js" / "i18n_en.js").write_text(js, encoding="utf-8")


def lang_toggle(href, label, title):
    lang = "zh-Hant" if label == "中文" else "en"
    return f'<a class="lang-toggle" href="{href}" hreflang="{lang}" lang="{lang}" title="{title}">{label}</a>'


def topbar(brand, toggle):
    """頂列：品牌名＋語言切換（四頁共用）。"""
    return f'<header class="topbar">\n  <a class="brand" href="#top">{brand}</a>\n  {toggle}\n</header>\n'


def head_links(canonical, zh, en):
    return (f'<link rel="canonical" href="{SITE}{canonical}">\n'
            f'<link rel="alternate" hreflang="zh-Hant" href="{SITE}{zh}">\n'
            f'<link rel="alternate" hreflang="en" href="{SITE}{en}">\n')


# 中文完整版 <head> 裡的 canonical 與語言對照，英文完整版整段換掉
ZH_FULL_HEAD = ('<link rel="stylesheet" href="../css/style.css">\n'
                '<link rel="canonical" href="https://report.claire-cheng.com/full/">\n'
                '<link rel="alternate" hreflang="zh-Hant" href="https://report.claire-cheng.com/full/">\n'
                '<link rel="alternate" hreflang="en" href="https://report.claire-cheng.com/en/full/">\n')


def build_full(draft):
    zh_html = EX.INDEX_HTML.read_text(encoding="utf-8")
    figs = EX.load_figures()
    blocks = {b["id"]: b for b in EX.walk(zh_html)}
    missing = [k for k in blocks if k not in draft and blocks[k]["kind"] != "圖表"]
    if missing:
        raise SystemExit(f"譯稿缺少段落：{missing}")

    spans = []
    for bid, b in blocks.items():
        if b["kind"] in ("圖表", "身分推薦", "介面文字", "頁面標題", "頁面描述"):
            continue
        spans += AP.html_spans(b, draft[bid], EX.editable_text(b, figs))
    html = AP.apply_spans(zh_html, spans)

    html = html.replace(f"<title>{blocks['meta-title']['text']}</title>",
                        f"<title>{htmllib.escape(draft['meta-title'])}</title>", 1)
    html = html.replace(f'content="{blocks["meta-description"]["text"]}"',
                        f'content="{htmllib.escape(draft["meta-description"])}"', 1)
    for a, b in HTML_UI.items():
        if a not in html:
            raise SystemExit(f"模板裡找不到要替換的介面文字：{a[:40]}")
        html = html.replace(a, b)

    # 資源路徑、語言、英文資料與介面文字
    for a, b in [(ZH_FULL_HEAD, '<link rel="stylesheet" href="../../css/style.css">\n'
                                + head_links("/en/full/", "/full/", "/en/full/")),
                 ('<script src="../data/figures.js"></script>',
                  '<script src="../../js/i18n_en.js"></script>\n<script src="../../data/figures_en.js"></script>'),
                 ('<script src="../js/charts.js"></script>', '<script src="../../js/charts.js"></script>'),
                 ('<script src="../js/app.js"></script>', '<script src="../../js/app.js"></script>')]:
        if a not in html:
            raise SystemExit(f"模板裡找不到要替換的路徑：{a[:40]}")
        html = html.replace(a, b)
    html = html.replace('<html lang="zh-Hant">', '<html lang="en">', 1)
    # 中文版的「English」切換鈕換成「中文」，並在封面上方提示可以先看精華版
    # 行動呼籲：中文卡片整段換成英文卡片（位置和中文版相同）
    pat = re.compile(r"(<!-- 行動呼籲開始[^>]*-->\n).*?(\n *<!-- 行動呼籲結束 -->)", re.S)
    if len(pat.findall(html)) != 1:
        raise SystemExit("模板裡找不到行動呼籲的插入點標記")
    html = pat.sub(lambda m: m.group(1) + cta_html(CTA_MD, "") + m.group(2), html)
    for a, b in [(lang_toggle("../en/full/", "English", "Read in English"),
                  lang_toggle("../../full/", "中文", "閱讀中文版")),
                 ('<a class="brand" href="#top">g0v.tw 揪松團問卷調查</a>',
                  '<a class="brand" href="#top">A survey by g0v.tw Jothon</a>'),
                 ('<div class="summary-hint">第一次來？<a href="../">先看 5 分鐘精華版</a>。</div>',
                  '<p class="summary-hint">New here? <a href="../">Start with the 5-minute summary</a>.</p>')]:
        if a not in html:
            raise SystemExit(f"模板裡找不到要替換的文字：{a[:40]}")
        html = html.replace(a, b)
    # 封面下載鈕：新版設計拿掉 📄 並加上按鈕 class（譯稿保留原樣，在這裡修）
    for a_, b_ in [('<a href="https://drive.google.com/file/d/1sjmVg55kwz9KhXLgtFsSFg_uNhs2AjOz/view?usp=sharing" target="_blank" rel="noopener"> 📄 Download',
                    '<a class="download-link" href="https://drive.google.com/file/d/1sjmVg55kwz9KhXLgtFsSFg_uNhs2AjOz/view?usp=sharing" target="_blank" rel="noopener">Download'),
                   ('<a href="#intro">Start reading ↓</a>', '<a class="btn-ghost" href="#intro">Start reading ↓</a>')]:
        if a_ not in html:
            raise SystemExit(f"找不到封面按鈕：{a_[:50]}")
        html = html.replace(a_, b_)
    # 對立假設表：結論句尾的「(Chapter N)」改成換行加小標籤
    html, n_ref = re.subn(r' \(Chapter (\d+)\)</td>', r'<br><a class="ch-ref" href="#ch\1">Chapter \1</a></td>', html)
    if n_ref != 6:
        raise SystemExit(f"對立假設表應有 6 個章節小標籤，實際 {n_ref}")
    out = DOCS / "en" / "full" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# ---------------------------------------------------------------- 行動呼籲（中英文共用，22_build_summary_zh.py 也用這支）

CTA_LINE = re.compile(r"^- \[(.+?)\]\((.+?)\)(?:：|: )(.+)$")


def _strip_emoji(s):
    """卡片標題開頭的 emoji 拿掉（線條圖示由 CSS 依卡片順序加）。"""
    return re.sub(r"^[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]+\s*", "", s)


def cta_html(md_path, full_prefix):
    """行動呼籲.md → 三張卡片。full_prefix：精華版是 "full/"，完整版是 ""。
    標題和第一張卡片之間可以有一行說明（英文版用來提醒連結頁面多為華語）。"""
    src = md_path.read_text(encoding="utf-8")
    body = src.split("<!-- 正文開始 -->", 1)[1].split("<!-- 正文結束 -->", 1)[0]
    title, note, cards, cur = "", "", [], None
    for ln in body.strip().split("\n"):
        ln = ln.strip()
        if ln.startswith("## "):
            title = ln[3:]
        elif ln.startswith("### "):
            cur = {"head": ln[4:], "items": []}
            cards.append(cur)
        elif ln.startswith("- "):
            m = CTA_LINE.match(ln)
            if not m or cur is None:
                raise SystemExit(f"{md_path.name} 格式不對：{ln}")
            text, href, why = m.groups()
            href = href.replace("{FULL}", full_prefix)
            ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
            cur["items"].append(f'<li><a href="{htmllib.escape(href)}"{ext}>{htmllib.escape(text)}</a>'
                                f'<span class="step-why">{htmllib.escape(why)}</span></li>')
        elif ln and title and not cards and not note:
            note = ln
        elif ln:
            raise SystemExit(f"{md_path.name} 有無法辨識的行：{ln}")
    h2_cls = "" if full_prefix else ' class="part-title"'   # 完整版：和「授權與資料來源」同一層
    if len(cards) != 3 or not title:
        raise SystemExit(f"{md_path.name} 應該有一個 ## 標題與三張 ### 卡片")
    note_html = f"        <p>{htmllib.escape(note)}</p>\n" if note else ""
    cards_html = "\n".join(
        f'          <div class="next-step-card"><h3>{htmllib.escape(_strip_emoji(c["head"]))}</h3>'
        f'<ul>{"".join(c["items"])}</ul></div>' for c in cards)
    return (f'      <section class="next-steps" id="next-steps">\n'
            f'        <h2{h2_cls}>{htmllib.escape(title)}</h2>\n{note_html}'
            f'        <div class="next-steps-grid">\n{cards_html}\n        </div>\n'
            f'      </section>')


# ---------------------------------------------------------------- 精華版

FIG_MARK = re.compile(r"^\[chart:(\w+)(?:\|(fold))?\]$")
STAT_ITEM = re.compile(r"^(.+?)[：:]\s*<strong>(\d+)%</strong>(.*)$")
# 「我們可以怎麼做」「延伸閱讀」底下的清單加 class（中英文標題）
LIST_CLASS = {"我們可以怎麼做": "actions", "What other communities can borrow": "actions",
              "延伸閱讀": "reading", "Explore more": "reading"}
DOT_ROW = re.compile(r"^(.+?) \| (\d+) \| (\d+) \| (.+)$")


def _numbers(text):
    return set(re.findall(r"\d+", text))


def stats_html(items):
    """全部都是「文字：**NN%**」的清單 → 大數字清單；`**NN%**` 後面還有字的整列變淡並加標籤。"""
    lis = []
    for it in items:
        m = STAT_ITEM.match(it)
        label, pct, rest = m.groups()
        rest = rest.strip().lstrip("，,、 ").strip()
        tag = f'<span class="tag">{rest}</span>' if rest else ""
        cls = "stat muted" if rest else "stat"
        lis.append(f'<li class="{cls}"><span class="stat-num">{pct}%</span>'
                   f'<span class="stat-label">{label.strip()}{tag}</span>'
                   f'<span class="bar" aria-hidden="true"><b style="width:{pct}%"></b></span></li>')
    return '<ul class="stats">' + "".join(lis) + "</ul>"


def dot_compare_html(rows, context):
    """::: dot-compare（標籤 | 總人數 | 達標人數 | 右側文字）→ 點陣對照。數字必須出現在前一段內文，否則失敗。"""
    cmps = []
    for r in rows:
        m = DOT_ROW.match(r)
        if not m:
            raise SystemExit(f"dot-compare 格式不對：{r}")
        label, total, on, n_text = m.groups()
        total, on = int(total), int(on)
        if not {str(total), str(on)} <= _numbers(context):
            raise SystemExit(f"dot-compare 的數字 {total}/{on} 沒有出現在前一段內文，請兩邊一起改：{label}")
        dots = '<i class="dot on"></i>' * on + '<i class="dot"></i>' * (total - on)
        cmps.append(f'<div class="cmp"><span class="cmp-label">{AP.md_to_html(label)}</span>'
                    f'<span class="dots">{dots}</span><span class="cmp-n">{AP.md_to_html(n_text)}</span></div>')
    return '<div class="dot-compare" aria-hidden="true">' + "".join(cmps) + "</div>"


def shift_html(rows, context):
    """::: shift（第一列＝兩個欄名；之後每列：標籤 | 之前 | 現在）→ 動機前後變化。數字必須出現在同一節內文。"""
    head = [c.strip() for c in rows[0].split("|")]
    out = [f'<div class="shift-head"><span></span><span>{AP.md_to_html(head[0])}</span>'
           f'<span></span><span>{AP.md_to_html(head[1])}</span></div>']
    for r in rows[1:]:
        label, a, b = [c.strip() for c in r.split("|")]
        if not {a, b} <= _numbers(context):
            raise SystemExit(f"shift 的數字 {a}→{b} 沒有出現在同一節內文，請兩邊一起改：{label}")
        cls = " up" if int(b) > int(a) else " down" if int(b) < int(a) else ""
        out.append(f'<div class="shift-row"><span>{AP.md_to_html(label)}</span><span class="shift-n">{a}</span>'
                   f'<span class="shift-arrow">→</span><span class="shift-n{cls}">{b}</span></div>')
    return '<div class="shift" aria-hidden="true">' + "".join(out) + "</div>"


def md_block_to_html(lines):
    """精華版用到的 Markdown：標題、段落、清單、表格、粗體、連結、圖表標記。"""
    out, i = [], 0
    in_finding, h2_title, section_text = False, "", ""   # 「發現」h3 各包成一張 article
    used_list_cls = set()

    def close_finding():
        nonlocal in_finding
        if in_finding:
            out.append("</article>")
            in_finding = False

    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln:
            i += 1
            continue
        m = FIG_MARK.match(ln)
        if m:
            fold = ' data-fold="mobile"' if m.group(2) else ""
            out.append(f'<div class="chart-block" data-chart="{m.group(1)}"{fold}></div>')
        elif ln.startswith("::: "):
            kind, rows = ln[4:].strip(), []
            i += 1
            while i < len(lines) and lines[i].rstrip() != ":::":
                rows.append(lines[i].strip())
                i += 1
            if kind == "dot-compare":
                out.append(dot_compare_html(rows, section_text))
            elif kind == "shift":
                # shift 放在 h3 之後、內文之前：往後看同一節的內文
                nxt, j = [], i + 1
                while j < len(lines) and not lines[j].startswith(("#", "::: ")):
                    nxt.append(lines[j])
                    j += 1
                out.append(shift_html(rows, " ".join(nxt)))
            else:
                raise SystemExit(f"不認得的區塊：::: {kind}")
        elif ln.startswith("### "):
            close_finding()
            out.append("<article class=\"finding\">")
            in_finding = True
            out.append(f"<h3>{AP.md_to_html(ln[4:])}</h3>")
        elif ln.startswith("## "):
            close_finding()
            h2_title = ln[3:].strip()
            slug = re.sub(r"[^a-z0-9]+", "-", ln[3:].lower()).strip("-")
            out.append(f'<h2 id="{slug}">{AP.md_to_html(ln[3:])}</h2>')
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(AP.md_to_html(lines[i][2:].strip()))
                i += 1
            if all(STAT_ITEM.match(x) for x in items):
                out.append(stats_html(items))
            else:
                cls = f' class="{LIST_CLASS[h2_title]}"' if h2_title in LIST_CLASS else ""
                used_list_cls.add(LIST_CLASS.get(h2_title))
                out.append(f"<ul{cls}>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.fullmatch(r"\|(-+\|)+", lines[i].strip()):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head = "".join(f"<th>{AP.md_to_html(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{AP.md_to_html(c)}</td>" for c in r) + "</tr>"
                           for r in rows[1:])
            out.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
                       f"<tbody>{body}</tbody></table></div>")
            continue
        else:
            para = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(
                    r"^(#|- |\||\[chart:)", lines[i + 1]):
                i += 1
                para.append(lines[i].rstrip())
            out.append(f"<p>{AP.md_to_html(' '.join(para))}</p>")
            section_text = " ".join(para)
        i += 1
    close_finding()
    if {"actions", "reading"} - used_list_cls:
        raise SystemExit("精華版找不到「我們可以怎麼做／延伸閱讀」（或 What other communities can borrow／Explore more）底下的清單，"
                         "標題改名時請同步改 LIST_CLASS")
    return "\n".join(out)


def build_summary():
    src = SUMMARY_MD.read_text(encoding="utf-8")
    body = src.split("<!-- 正文開始 -->", 1)[1].split("<!-- 正文結束 -->", 1)[0].strip("\n")
    lines = body.split("\n")
    title = lines[0].lstrip("# ").strip()
    subtitle = lines[2].strip("* ") if len(lines) > 2 else ""
    content = md_block_to_html(lines[4:])
    # 行動呼籲放在「What other communities can borrow」之後、「About this survey」之前
    about = content.find('<h2 id="about-this-survey">')
    if about < 0:
        raise SystemExit("精華版找不到「About this survey」，無法放行動呼籲")
    content = content[:about] + cta_html(CTA_MD, "full/") + "\n" + content[about:]
    desc = ("What 127 people around g0v.tw, Taiwan's grassroots civic tech community, "
            "told us about getting in, getting stuck, and staying. A 5-minute summary.")
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>{htmllib.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{htmllib.escape(desc)}">
<meta name="color-scheme" content="only light">
<link rel="stylesheet" href="../css/style.css">
{head_links("/en/", "/", "/en/")}
<a class="skip-link" href="#main">Skip to main content</a>

{topbar("A survey by g0v.tw Jothon", lang_toggle("../", "中文", "閱讀中文版"))}
<div class="layout">
  <main id="main">
    <div class="content summary-page">

      <header id="top" class="cover">
        <p class="cover-eyebrow">A survey by <a href="https://g0v.tw/" target="_blank" rel="noopener">g0v.tw</a> Jothon · 5-minute summary</p>
        <h1 class="report-title">{AP.md_to_html(title)}</h1>
        <p class="cover-hook">{AP.md_to_html(subtitle)}</p>
        <p class="meta-line">By Claire Cheng | 127 valid responses collected up to 20 July 2026</p>
      </header>

{content}

      <p class="cta-row"><a class="download-link" href="full/">Read the full report →</a></p>

      <footer>
        <p>CC BY 4.0, by <a href="https://g0v.tw/" target="_blank" rel="noopener">g0v.tw</a> jothon &amp; <a href="https://claire-cheng.com/en" target="_blank" rel="noopener">Claire Cheng</a></p>
      </footer>
    </div>
  </main>
</div>

<script src="../js/i18n_en.js"></script>
<script src="../data/figures_en.js"></script>
<script src="../js/charts.js"></script>
<script src="../js/app.js"></script>
"""
    out = DOCS / "en" / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def visible_cjk(path):
    t = path.read_text(encoding="utf-8")
    t = re.sub(r"<script\b.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r'(href|hreflang|title|data-chart|id|class)="[^"]*"', " ", t)
    for a in ALLOWED_CJK:
        t = t.replace(a, "")
    t = t.replace("中文", "")                      # 語言切換鈕
    return sorted(set(re.findall(r"[　-〿一-鿿＀-￯][^<\n]{0,20}", t)))


def main():
    draft = dict(RT.parse_draft(FULL_DRAFT))
    build_i18n(draft)
    full = build_full(draft)
    summary = build_summary()
    bad = []
    for p in (full, summary):
        left = visible_cjk(p)
        if left:
            bad.append((p, left))
    for p, left in bad:
        print(f"✗ {p.relative_to(C.PROJ)} 畫面上還有中文：")
        for x in left[:30]:
            print("   ", x)
    if bad:
        sys.exit(1)
    print(f"✅ 已產生 {summary.relative_to(C.PROJ)}、{full.relative_to(C.PROJ)}、docs/js/i18n_en.js")


if __name__ == "__main__":
    main()
