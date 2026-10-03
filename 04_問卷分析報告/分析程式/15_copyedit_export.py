# -*- coding: utf-8 -*-
"""
15_copyedit_export.py — 把展示網頁的全部文字匯出成「改稿包」，每段附事實卡。

用途：網頁文案要交給其他 AI 工具（Antigravity）改寫得更口語。
最高原則是正確性，所以每一段正文旁邊都附上「這段話的事實根據」：
  · 段落裡每一個數字取自哪一題、分子分母、分母是誰、信賴度
  · 段落引用的問卷選項／題目原文（上鎖，一字不能改）
  · 這段話的論點界線（相關不是因果、只適用哪一群人、樣本多小）

產物（都在 04_問卷分析報告/改稿包/）：
  改稿稿件.md    逐段的「正文｜可改寫」＋「事實卡｜不可改動」
  待裁決清單.md  網頁現有文字與資料或選項原文對不上的地方，給 Claire 裁決

段落切法與編號
--------------
依 index.html 的 DOM 順序，取最內層的文字區塊（標題、段落、清單項、表格、
重點卡、封面統計），每個區塊一個編號：<最近的錨點 id>-<流水號>，例如 ch3-2-03。
錨點取網頁本身的 id（top、intro、ch3-2⋯），所以編號和網頁位置一一對應。
圖表文字（標題、副標、分母說明、選項）來自 docs/data/figures.json，
身分推薦文字來自 docs/js/app.js，各自插在網頁裡出現的位置。

數字怎麼對到來源
----------------
每個段落的每個數字，都要在 copyedit_facts.py 的 FACTS 裡人工指定來源。
這支腳本負責：
  1. 從段落文字抽出所有數字（百分比、人數、「近九成」「排第四」這類量詞）
  2. 核對 FACTS 指定的數字清單與實際抽到的完全一致（多一個、少一個都失敗）
  3. 回 分析結果/*.csv 重算每一個數字，對不上就失敗
     （已知、待 Claire 裁決的問題寫在 copyedit_facts.KNOWN_ISSUES，改列進待裁決清單）
自動配對容易「算術對、題目錯」（見 12_source_audit.py 的說明），所以這裡不做自動配對。

執行：python3 15_copyedit_export.py
"""

import difflib
import json
import re
import sys
from html.parser import HTMLParser

import pandas as pd

import common as C
import copyedit_facts as CF

DOCS = C.PROJ / "docs"
INDEX_HTML = DOCS / "index.html"
FIGURES_JSON = DOCS / "data" / "figures.json"
APP_JS = DOCS / "js" / "app.js"
OUT = C.OUT_DIR / "改稿包"
DRAFT_MD = OUT / "改稿稿件.md"
ISSUES_MD = OUT / "待裁決清單.md"

# ================================================================ HTML → 區塊

BLOCK_TAGS = {"h1", "h2", "h3", "p", "li", "caption", "tr", "button", "summary"}
VOID = {"meta", "link", "br", "img", "input", "hr", "use", "circle", "path", "rect", "line"}
SKIP_TAGS = {"script", "style", "svg", "title", "head"}
# 重複出現的介面文字：不逐處列出，集中在最後的「介面文字」區塊列一次
UI_ONCE = {"看完整說明", "跳到主要內容"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def cls(self):
        return self.attrs.get("class", "").split()


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def iter_nodes(node):
    for ch in node.children:
        if isinstance(ch, Node):
            yield ch
            yield from iter_nodes(ch)


def inline_md(node):
    """把一個區塊內的行內元素轉成 Markdown（粗體、連結、註腳）。"""
    out = []
    for ch in node.children:
        if isinstance(ch, str):
            out.append(ch)
            continue
        if ch.tag in SKIP_TAGS:
            continue
        inner = inline_md(ch)
        if ch.tag in ("strong", "b"):
            # 粗體記號緊貼文字；原本包在粗體裡的頭尾空白移到記號外面
            lead = inner[:len(inner) - len(inner.lstrip())]
            tail = inner[len(inner.rstrip()):]
            out.append(f"{lead}**{inner.strip()}**{tail}")
        elif ch.tag == "a":
            href = ch.attrs.get("href", "")
            out.append(f"[{inner}]({href})" if href and not href.startswith("#fn") else inner)
        elif ch.tag == "sup":
            out.append(f"[^{inner.strip()}]")
        else:
            out.append(inner)
    return "".join(out)


def norm_ws(s):
    # 照瀏覽器的規則收合空白：連續空白（含原始碼換行縮排）變成一個半形空格。
    # 全形空格（U+3000）不是 HTML 空白，保留原樣。
    return re.sub(r"[ \t\r\n]+", " ", s).strip()


def has_block_child(node):
    for ch in node.children:
        if isinstance(ch, Node) and ch.tag not in SKIP_TAGS:
            if (ch.tag in BLOCK_TAGS or ch.tag in ("table", "ul", "ol", "div")
                    or has_block_child(ch)):
                return True
    return False


def parse_persona_routes():
    """從 app.js 取出身分推薦的三組文字。"""
    js = APP_JS.read_text(encoding="utf-8")
    routes = []
    for key in ("newcomer", "doing", "funder"):
        m = re.search(key + r":\s*\{(.*?)\n    \},", js, re.S)
        body = m.group(1)
        why_parts = re.search(r"why:\s*(.*?),\n\s*sections:", body, re.S).group(1)
        why = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', why_parts))
        secs = re.findall(r'\["(#[^"]+)",\s*"([^"]+)"\]', body)
        label = re.search(r'label:\s*"([^"]+)"', body).group(1)
        routes.append({"key": key, "label": label, "why": why, "sections": secs})
    return routes


def walk(html_text):
    tb = TreeBuilder()
    tb.feed(html_text)
    blocks = []
    state = {"anchor": "head", "seq": {}}
    ui = []

    def new_id():
        a = state["anchor"]
        state["seq"][a] = state["seq"].get(a, 0) + 1
        return f"{a}-{state['seq'][a]:02d}"

    def add(kind, text, **extra):
        text = text.strip()
        if not text:
            return
        blocks.append({"id": new_id(), "anchor": state["anchor"], "kind": kind,
                       "text": text, **extra})

    def visit(node):
        if isinstance(node, str) or node.tag in SKIP_TAGS:
            return
        if node.attrs.get("id") and node.tag in ("section", "header", "h3"):
            state["anchor"] = node.attrs["id"]
        cls = node.cls()

        if node.tag == "aside":                       # 側欄目錄：整份當一個區塊
            items = []
            for a in iter_nodes(node):
                if a.tag == "h2":
                    items.append(f"【{norm_ws(inline_md(a))}】")
                elif a.tag == "a":
                    depth = "　　" if "sub" in a.parent.parent.cls() else ""
                    items.append(f"{depth}- {norm_ws(inline_md(a))}")
            blocks.append({"id": "nav", "anchor": "nav", "kind": "側欄目錄",
                           "text": "\n".join(items)})
            return
        if "chart-block" in cls:
            key = node.attrs["data-chart"]
            blocks.append({"id": f"fig-{key}", "anchor": state["anchor"], "kind": "圖表",
                           "fig": key, "text": ""})
            return
        if node.tag == "table":
            rows, cap, dyn = [], "", None
            for n in iter_nodes(node):
                if n.tag == "caption":
                    cap = norm_ws(inline_md(n))
                elif n.tag == "tr":
                    rows.append([norm_ws(inline_md(c)) for c in n.children
                                 if isinstance(c, Node) and c.tag in ("td", "th")])
                elif n.tag == "tbody" and n.attrs.get("id"):
                    dyn = n.attrs["id"]
            text = "\n".join(" ｜ ".join(r) for r in rows)
            blocks.append({"id": new_id(), "anchor": state["anchor"], "kind": "表格",
                           "caption": cap, "rows": rows, "dynamic": dyn, "text": text})
            return
        if "stat" in cls and node.tag == "div":
            add("封面數字", " ".join(norm_ws(inline_md(c)) for c in node.children
                                    if isinstance(c, Node)))
            return
        if "persona-result" in cls:
            for r in parse_persona_routes():
                text = r["why"] + "\n" + "\n".join(f"- {lbl}" for _, lbl in r["sections"])
                blocks.append({"id": f"persona-route-{r['key']}", "anchor": "persona",
                               "kind": "身分推薦", "text": text, "route": r})
            return
        if node.tag in BLOCK_TAGS and not has_block_child(node):
            text = norm_ws(inline_md(node))
            if node.tag in ("summary",) or text in UI_ONCE:
                if text not in ui:
                    ui.append(text)
                return
            if node.tag == "button":
                ui.append(text)
                return
            kind = {"h1": "標題", "h2": "標題", "h3": "標題", "caption": "表格標題"}.get(
                node.tag, "清單項" if node.tag == "li" else "段落")
            if "insight-text" in cls:
                kind = "重點卡"
            elif "lede" in cls:
                kind = "引言"
            add(kind, text)
            return
        if node.tag in BLOCK_TAGS:
            # 區塊裡同時有行內文字與子區塊（例如摘要的 <li><strong>…</strong><p>…</p></li>）：
            # 子區塊之前的行內文字自成一段
            buf = Node("frag", [], None)
            for ch in node.children:
                if isinstance(ch, Node) and (ch.tag in BLOCK_TAGS or has_block_child(ch)):
                    add("小標", norm_ws(inline_md(buf)))
                    buf = Node("frag", [], None)
                    visit(ch)
                else:
                    buf.children.append(ch)
            add("段落", norm_ws(inline_md(buf)))
            return
        if node.tag == "a" and "skip-link" in cls:
            ui.append(norm_ws(inline_md(node)))
            return
        for ch in node.children:
            visit(ch)

    visit(tb.root)

    # <head> 裡的頁面標題與描述（搜尋結果、分享預覽會顯示）
    title = re.search(r"<title>(.*?)</title>", html_text).group(1)
    desc = re.search(r'<meta name="description" content="([^"]+)"', html_text).group(1)
    head = [{"id": "meta-title", "anchor": "meta", "kind": "頁面標題", "text": title},
            {"id": "meta-description", "anchor": "meta", "kind": "頁面描述", "text": desc}]
    ui += [t for t, _ in CF.UI_EXTRA if t not in ui]
    ui_block = {"id": "ui", "anchor": "ui", "kind": "介面文字", "text": "\n".join(ui)}
    return head + blocks + [ui_block]


def load_figures():
    return json.loads(FIGURES_JSON.read_text(encoding="utf-8"))


def fig_text(fig):
    """圖表裡可以改寫的文字：標題、副標、分母說明。"""
    parts = [("圖標題", fig.get("title")), ("圖副標", fig.get("subtitle")),
             ("分母說明", fig.get("denomNote"))]
    return [(k, v) for k, v in parts if v]


def fig_labels(fig):
    """圖表裡上鎖的選項文字（含分子分母，供事實卡用）。"""
    out = []
    for it in fig.get("items") or []:
        lab = it.get("fullLabel") or it["label"]
        if "n" in it and it.get("d"):
            out.append(f"{lab}（{it['n']}/{it['d']}，{it['n'] / it['d'] * 100:.1f}%）")
        elif "n3plus" in it:
            out.append(f"{lab}（3 分以上 {it['n3plus']}/{it['d']}，"
                       f"{it['pct3plus'] * 100:.1f}%；4 分以上 {it['n4plus']}/{it['d']}，"
                       f"{it['pct4plus'] * 100:.1f}%）")
        elif "si" in it:
            out.append(f"{it.get('num', '')} {lab}（SI {it['si']}、DSI {it['dsi']}，{it['quadrant']}）")
        else:
            out.append(lab)
    for opt in fig.get("options") or []:
        cells = "；".join(f"{CF.LAYER_PLAIN.get(k, k)} {v['n']}/{v['d']}（{v['pct'] * 100:.1f}%）"
                         for k, v in opt["byLayer"].items())
        out.append(f"{opt['label']}（{cells}）")
    for p in fig.get("panels") or []:
        g = p.get("group") or p.get("layer")
        for it in p["items"]:
            if "groupPct" in it:
                out.append(f"［{g}］{it['label']}（{it['n']}/{it['d']}＝{it['groupPct'] * 100:.1f}%，"
                           f"全體 {it['basePct'] * 100:.1f}%，差 {it['diffPts']:+.1f} 個百分點）")
            else:
                out.append(f"［{g}］{it.get('num', '')} {it.get('fullLabel') or it['label']}"
                           f"（SI {it['si']}、DSI {it['dsi']}，{it['quadrant']}）")
    for key in ("seriesLabels",):
        for s in fig.get(key) or []:
            out.append(f"評分量尺：{s}")
    for lg in fig.get("legend") or []:
        out.append(f"圖例：{lg['num']} {lg['label']}")
    if fig.get("escapeLabel"):
        out.append(f"（逃生選項）{fig['escapeLabel']}")
    return out


def editable_text(b, figs):
    """每個區塊要交給改稿者的文字。圖表區塊合併標題／副標／分母說明。"""
    if b["kind"] == "圖表":
        return "\n".join(f"{k}：{v}" for k, v in fig_text(figs["figures"][b["fig"]]))
    return b["text"]


# ================================================================ 數字抽取

TOKEN_RE = re.compile(
    r"(?<![\d.])\d+(?:\.\d+)?\s*%(?:\s*[（(]\s*\d+\s*/\s*\d+\s*[）)])?"  # 百分比，可帶分子分母
    r"|(?<![\d.])\d+\s*與\s*\d+\s*個百分點"                         # 「21 與 20 個百分點」
    r"|(?<![\d.])\d+\s*多個"                                        # 「10 多個領域」
    r"|(?<![\d.])\d+\s*(?:個人|人|位(?!於)|份|個|種|類|張)"         # 人數與其他量詞
    r"|(?:近|超過|不到|逾)?[一二三四五六七八九十]成"                # 「近九成」「四成」
    r"|超過半數|過半數|過半|半數"
    r"|第[一二三四五六七八九十](?![章節])"                          # 排名（「第四」）；章節互指不算
)


def strip_links(t):
    return re.sub(r"\]\([^)]*\)", "]", t)


def tokens_of(b, figs):
    if b["kind"] == "表格":
        toks = []
        for row in b["rows"]:
            for cell in row:
                cell_t = strip_links(cell)
                if re.fullmatch(r"\d+", cell_t.strip()):
                    toks.append(cell_t.strip())
                else:
                    toks += [m.group(0) for m in TOKEN_RE.finditer(cell_t)]
        return toks
    text = strip_links(editable_text(b, figs))
    return [m.group(0) for m in TOKEN_RE.finditer(text)]


# ================================================================ 引號文字 vs 選項原文

def original_texts():
    """引號文字可以對照的「原文」：
    · 問卷選項（實際上線版本，取自 99_數字索引 的項目，即回收資料裡的選項字串）
    · 問卷題目（00_欄位辨識表 的欄名；矩陣題的「[子題]」拆出來當選項）
    · 圖表上的選項簡稱與圖例（網頁自己的標籤，引用時要和圖上一致）
    """
    idx = pd.read_csv(C.TABLE_DIR / "99_數字索引.csv")
    items = set()
    for it in idx["項目"]:
        items.add(str(it).split("／")[-1].replace("（%≥3）", ""))
    questions = set()
    for c in pd.read_csv(C.TABLE_DIR / "00_欄位辨識表.csv")["欄位"]:
        c = str(c).strip()
        m = re.match(r"(.*?)\s*\[(.+)\]$", c)
        if m:
            questions.add(m.group(1))
            items.add(m.group(2))
        else:
            questions.add(c)
    figs = load_figures()["figures"]
    for f in figs.values():
        for it in (f.get("items") or []) + (f.get("options") or []) + (f.get("legend") or []):
            for k in ("label", "shortLabel", "fullLabel"):
                if it.get(k):
                    items.add(it[k])
    return items, questions


def _plain(q):
    return strip_links(q).replace("[", "").replace("]", "")


def classify_quote(q, items, questions):
    qq = _plain(q)
    if qq in CF.QUOTE_OVERRIDES:
        return "近似選項", CF.QUOTE_OVERRIDES[qq]
    qq_noq = qq.rstrip("？?")
    for o in items:
        variants = {o, o.split("：")[0], o.split("，")[0], re.sub(r"[（(].*?[）)]", "", o).strip()}
        if qq in variants:
            return "選項原文", o
    for qs in questions:
        if qq_noq == qs.rstrip("？?") or (len(qq_noq) >= 8 and qq_noq in qs):
            return "題目原文", qs
    best = max(questions, key=lambda o: difflib.SequenceMatcher(None, qq, o).ratio())
    if len(qq) >= 8 and difflib.SequenceMatcher(None, qq, best).ratio() >= 0.6:
        return "近似題目", best
    best = max(items, key=lambda o: difflib.SequenceMatcher(None, qq, o).ratio())
    if len(qq) >= 4 and difflib.SequenceMatcher(None, qq, best).ratio() >= 0.6:
        return "近似選項", best
    return None, None


QUOTE_RE = re.compile(r"「([^「」]+)」")


# ================================================================ 事實卡

def check_and_render_facts(b, toks, figs, issues):
    """核對 FACTS 與抽到的數字一致，回傳事實卡的條列文字。"""
    spec = CF.FACTS.get(b["id"], [])
    want = [s[0] for s in spec]
    if want != toks:
        raise SystemExit(
            f"[{b['id']}] FACTS 的數字清單與段落實際抽到的不一致\n"
            f"  段落抽到：{toks}\n  FACTS 寫：{want}")
    lines = []
    for tok, ref, *note in spec:
        ok, desc = CF.evaluate(tok, ref, figs)
        key = (b["id"], tok)
        if not ok:
            if key in CF.KNOWN_ISSUES:
                issues.append((b["id"], tok, CF.KNOWN_ISSUES[key], desc))
                desc = "⚠️ 待裁決：" + CF.KNOWN_ISSUES[key] + "｜" + desc
            else:
                raise SystemExit(f"[{b['id']}] 數字「{tok}」重算對不上：{desc}")
        lines.append(f"「{tok}」→ {desc}" + (f"｜{note[0]}" if note and note[0] else ""))
    stale = [k for k in CF.KNOWN_ISSUES if k[0] == b["id"] and k[1] not in toks]
    if stale:
        raise SystemExit(f"KNOWN_ISSUES 有用不到的條目：{stale}")
    return lines


# ================================================================ 輸出

RULES_HEAD = """# 網頁改稿稿件

> 這份稿件是 [report.claire-cheng.com](https://report.claire-cheng.com/) 的全部文字，
> 依網頁出現順序排列，由 `分析程式/15_copyedit_export.py` 產生。
> **改稿前先讀同資料夾的《改稿守則.md》。**

## 使用方式

- 每一段有固定編號，例如 `[ch3-2-03]`。編號不能改，也不能刪掉或合併段落
- 只能改 `<!-- 正文開始 -->` 與 `<!-- 正文結束 -->` 之間的文字
- 每段下面的「事實卡」是這段話的事實根據，**不可改動、不可複製進正文**
- 正文裡標成 〔鎖〕「…」 的引號內容是問卷選項或題目原文，一字不能改
- 標成 〔待裁決〕「…」 的引號，目前和原文不一致，等 Claire 決定前先不要動

"""


def render(blocks, figs, items, questions):
    issues, quote_issues = [], []
    out = [RULES_HEAD]
    cur_anchor = None
    n_tokens = n_locked = 0
    for b in blocks:
        toks = tokens_of(b, figs)
        n_tokens += len(toks)
        fact_lines = check_and_render_facts(b, toks, figs, issues)

        text = editable_text(b, figs)
        if b["kind"] == "表格":
            rows = b["rows"]
            md = []
            if b.get("caption"):
                md.append(f"表格標題：{b['caption']}\n")
            if rows:
                md.append("| " + " | ".join(rows[0]) + " |")
                md.append("|" + "---|" * len(rows[0]))
                md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
            text = "\n".join(md)

        # 引號上鎖
        def lock(m):
            nonlocal n_locked
            kind, src = classify_quote(m.group(1), items, questions)
            if kind in ("選項原文", "題目原文"):
                n_locked += 1
                return f"〔鎖〕「{m.group(1)}」"
            if kind in ("近似選項", "近似題目"):
                quote_issues.append((b["id"], m.group(1), src))
                return f"〔待裁決〕「{m.group(1)}」"
            return m.group(0)
        if b["kind"] not in ("側欄目錄", "介面文字"):
            text = QUOTE_RE.sub(lock, text)

        if b["anchor"] != cur_anchor:
            cur_anchor = b["anchor"]
            title = CF.ANCHOR_TITLES.get(cur_anchor)
            if not title or b["kind"] == "標題":
                title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", b["text"]) if b["kind"] == "標題" else cur_anchor
            out.append(f"\n---\n\n## {title}　`#{cur_anchor}`\n")
            if cur_anchor in CF.ANCHOR_NOTES:
                out.append("> **本節共通界線**：" + CF.ANCHOR_NOTES[cur_anchor] + "\n")

        out.append(f"### [{b['id']}]　{b['kind']}\n")
        out.append(f"<!-- 正文開始 {b['id']} -->")
        out.append(text)
        out.append(f"<!-- 正文結束 {b['id']} -->\n")

        card = []
        if b["kind"] == "表格" and b.get("dynamic"):
            card.append(f"表格內容由程式從資料自動產生（{b['dynamic']}），見下方「表格資料」，不可改")
            card += [f"表格資料：{r}" for r in CF.dynamic_table_rows(b["dynamic"], figs)]
        if b["kind"] == "圖表":
            fig = figs["figures"][b["fig"]]
            card.append("圖上的選項文字與數字（不可改，由程式從資料產生）：")
            card += [f"　{x}" for x in fig_labels(fig)]
        if b["id"] == "ui":
            card.append("這些文字散在各處或由程式產生，改了要動到程式碼："
                        + "；".join(f"「{t}」＝{src}" for t, src in CF.UI_EXTRA)
                        + "；「☰ 章節」只在手機版顯示")
        card += fact_lines
        for c in CF.CLAIMS.get(b["id"], []):
            card.append(f"論點與界線：{c}")
        if card:
            out.append("> **事實卡｜不可改動**")
            out += [f"> - {c}" for c in card]
            out.append("")
    return "\n".join(out) + "\n", issues, quote_issues, n_tokens, n_locked


def render_issues(issues, quote_issues):
    out = ["# 待裁決清單\n",
           "> 由 `分析程式/15_copyedit_export.py` 產生。這些是**網頁現有文字**的問題，",
           "> 不是改稿造成的。每一條請 Claire 決定怎麼處理；這次的 PR 不改網頁。\n"]
    out.append("## 一、數字或說法與資料對不上\n")
    if issues:
        out.append("| 段落 | 原文 | 問題 | 資料實際是 |")
        out.append("|---|---|---|---|")
        for bid, tok, why, desc in issues:
            out.append(f"| `{bid}` | {tok} | {why} | {desc} |")
    else:
        out.append("（無）")
    out.append("\n## 二、引號內容與問卷選項原文不一致\n")
    out.append("引號代表照引原文。以下引述和原文有出入，請決定要改回原文照引，"
               "還是拿掉引號改成描述。\n")
    if quote_issues:
        groups = {}
        for bid, q, src in quote_issues:
            groups.setdefault(src, []).append((bid, q))
        out.append(f"共 {len(quote_issues)} 處，依對應的原文分成 {len(groups)} 組。"
                   "建議先定一條通則（例如「引號內一律照原文全引；想用簡稱就拿掉引號」），"
                   "再看有沒有要例外處理的。\n")
        out.append("| 最接近的原文（問卷選項、題目或圖表標籤） | 網頁目前寫的（段落） |")
        out.append("|---|---|")
        for src, lst in groups.items():
            cells = "<br>".join(f"「{q}」（`{bid}`）" for bid, q in lst)
            out.append(f"| {src} | {cells} |")
    out.append("\n## 三、其他\n")
    out += [f"- {x}" for x in CF.OTHER_ISSUES]
    return "\n".join(out) + "\n"


def main():
    html = INDEX_HTML.read_text(encoding="utf-8")
    blocks = walk(html)
    figs = load_figures()
    if "--tokens" in sys.argv:              # 開發用：列出每段抽到的數字，寫 FACTS 時對照
        for b in blocks:
            t = tokens_of(b, figs)
            if t:
                print(b["id"], t)
        return
    ids = {b["id"] for b in blocks}
    anchors = {b["anchor"] for b in blocks}
    stray = ([k for k in CF.FACTS if k not in ids] + [k for k in CF.CLAIMS if k not in ids]
             + [k for k in CF.ANCHOR_NOTES if k not in anchors])
    if stray:
        raise SystemExit(f"copyedit_facts.py 指到不存在的段落或區段（網頁改版後編號位移？）：{stray}")
    items, questions = original_texts()
    md, issues, quote_issues, n_tok, n_lock = render(blocks, figs, items, questions)
    OUT.mkdir(exist_ok=True)
    DRAFT_MD.write_text(md, encoding="utf-8")
    ISSUES_MD.write_text(render_issues(issues, quote_issues), encoding="utf-8")
    print(f"段落 {len(blocks)} 個、數字 {n_tok} 處（全部有指定來源並重算通過，"
          f"其中 {len(issues)} 處列入待裁決）")
    print(f"上鎖引述 {n_lock} 處、與原文不一致的引述 {len(quote_issues)} 處")
    print(f"輸出：{DRAFT_MD.relative_to(C.PROJ)}、{ISSUES_MD.relative_to(C.PROJ)}")


if __name__ == "__main__":
    main()
