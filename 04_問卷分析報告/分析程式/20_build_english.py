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
    'aria-label="切換深色／淺色模式">🌙 深色<': 'aria-label="Switch between dark and light mode">🌙 Dark<',
    ">☰ 章節<": ">☰ Contents<",
    "🌱 我是新手，還在了解這個圈子": "🌱 I'm new and still getting to know the community",
    "🔧 我正在做（或做過）公民科技專案": "🔧 I'm working on (or have worked on) a civic tech project",
    "💡 我可能提供資源，或想支持社群經營": "💡 I might provide resources, or want to support the community",
    'aria-label="公民科技參與示意圖：外圈是旁觀者，中圈是通報者，核心是圍著電腦動手做專案的貢獻者"':
        'aria-label="Illustration of civic tech involvement: onlookers in the outer ring, contributors of information in the middle ring, and builders working around a laptop at the core"',
    '"%（" + r["票數"] + "/" + r["分母"] + "）"': '"% (" + r["票數"] + "/" + r["分母"] + ")"',
    "<!-- 外圈：聽過或看過（旁觀）-->": "",
    "<!-- 中圈：接觸未參與（通報、關注）-->": "",
    "<!-- 核心：做過專案，圍著一台筆電動手做 -->": "",
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

APP_TEXT_EN = {"startWith": "Start with:", "dark": "🌙 Dark", "light": "☀️ Light",
               "toDark": "Switch to dark mode", "toLight": "Switch to light mode"}


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
    return f'<a class="lang-toggle" href="{href}" hreflang="{"zh-Hant" if label == "中文" else "en"}" title="{title}">{label}</a>'


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
    html = '<html lang="en">\n' + html
    # 中文版的「English」切換鈕換成「中文」，並在封面上方提示可以先看精華版
    for a, b in [(lang_toggle("../en/full/", "English", "Read in English"),
                  lang_toggle("../../full/", "中文", "閱讀中文版")),
                 ('<div class="summary-hint">第一次來？<a href="../">先看 5 分鐘精華版</a>。</div>',
                  '<p class="summary-hint">New here? <a href="../">Start with the 5-minute summary</a>.</p>')]:
        if a not in html:
            raise SystemExit(f"模板裡找不到要替換的文字：{a[:40]}")
        html = html.replace(a, b)
    out = DOCS / "en" / "full" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# ---------------------------------------------------------------- 精華版

FIG_MARK = re.compile(r"^\[chart:(\w+)\]$")


def md_block_to_html(lines):
    """精華版用到的 Markdown：標題、段落、清單、表格、粗體、連結、圖表標記。"""
    out, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln:
            i += 1
            continue
        m = FIG_MARK.match(ln)
        if m:
            out.append(f'<div class="chart-block" data-chart="{m.group(1)}"></div>')
        elif ln.startswith("### "):
            out.append(f"<h3>{AP.md_to_html(ln[4:])}</h3>")
        elif ln.startswith("## "):
            slug = re.sub(r"[^a-z0-9]+", "-", ln[3:].lower()).strip("-")
            out.append(f'<h2 id="{slug}">{AP.md_to_html(ln[3:])}</h2>')
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{AP.md_to_html(lines[i][2:].strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
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
        i += 1
    return "\n".join(out)


def build_summary():
    src = SUMMARY_MD.read_text(encoding="utf-8")
    body = src.split("<!-- 正文開始 -->", 1)[1].split("<!-- 正文結束 -->", 1)[0].strip("\n")
    lines = body.split("\n")
    title = lines[0].lstrip("# ").strip()
    subtitle = lines[2].strip("* ") if len(lines) > 2 else ""
    content = md_block_to_html(lines[4:])
    desc = ("What 127 people around g0v.tw, Taiwan's grassroots civic tech community, "
            "told us about getting in, getting stuck, and staying. A 5-minute summary.")
    html = f"""<html lang="en">
<meta charset="utf-8">
<title>{htmllib.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{htmllib.escape(desc)}">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="../css/style.css">
{head_links("/en/", "/", "/en/")}
<a class="skip-link" href="#main">Skip to main content</a>

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

{lang_toggle("../", "中文", "閱讀中文版")}
<button type="button" class="theme-toggle" id="themeToggle" aria-label="Switch between dark and light mode">🌙 Dark</button>

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
