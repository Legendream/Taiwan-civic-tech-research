# -*- coding: utf-8 -*-
"""
18_copyedit_apply.py — 把審定後的改稿稿件套回展示網頁。

網頁文字散在四個地方，各自用最小幅度的方式替換：
  · docs/index.html      依段落編號找到原始碼裡的那個元素，只換它裡面的文字
                          （側欄目錄、封面數字、表格逐格、頁面標題與描述同理）
  · 13_web_data.py       圖表的標題、副標、分母說明（改程式裡的字串，重跑後才會進 figures.json）
  · docs/js/app.js       身分推薦的說明文字與章節連結文字
沒有改動的段落，原始碼一個字都不碰。

套用後用 --check 核對：重新從網頁原始碼匯出每一段，和稿件逐段比對，必須一字不差。

執行：
  python3 18_copyedit_apply.py <審定稿件>            # 套用
  python3 13_web_data.py                              # 重新產生圖表資料
  python3 18_copyedit_apply.py <審定稿件> --check     # 核對
"""

import ast
import html as htmllib
import io
import json
import re
import sys
import tokenize
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

WEB_DATA_PY = HERE / "13_web_data.py"
MARKS = ("〔鎖〕", "〔維持〕")


def strip_marks(t):
    for m in MARKS:
        t = t.replace(m, "")
    return t


# ================================================================ Markdown → HTML（只處理稿件用到的行內語法）

INLINE_RE = re.compile(r"\*\*(.+?)\*\*|\[\^(\d+)\]|\[([^\]]*)\]\(([^)]*)\)")


def md_to_html(text):
    out, pos = [], 0
    for m in INLINE_RE.finditer(text):
        out.append(htmllib.escape(text[pos:m.start()], quote=False))
        if m.group(1) is not None:
            out.append(f"<strong>{md_to_html(m.group(1))}</strong>")
        elif m.group(2) is not None:
            n = m.group(2)
            out.append(f'<sup><a href="#fn{n}">{n}</a></sup>')
        else:
            label, href = md_to_html(m.group(3)), m.group(4)
            if href.startswith("#"):
                out.append(f'<a href="{href}">{label}</a>')
            else:
                out.append(f'<a href="{htmllib.escape(href)}" target="_blank" rel="noopener">{label}</a>')
        pos = m.end()
    out.append(htmllib.escape(text[pos:], quote=False))
    return "".join(out).replace("\n", "<br>")       # 段內換行還原成 <br>


def plain(text):
    """比對用：拿掉標記、行內語法與空白差異。"""
    t = strip_marks(text)
    t = re.sub(r"\[\^(\d+)\]", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    return re.sub(r"\s+", "", t.replace("**", ""))


# ================================================================ 稿件解析

def parse_table(text):
    caption, rows = None, []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("表格標題："):
            caption = line[len("表格標題："):]
        elif line.startswith("|") and not re.fullmatch(r"\|(-+\|)+", line):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return caption, rows


def parse_fig(text):
    fields, cur = {}, None
    keymap = {"圖標題": "title", "圖副標": "subtitle", "分母說明": "denomNote"}
    for line in text.split("\n"):
        m = re.match(r"^(圖標題|圖副標|分母說明)：(.*)$", line)
        if m:
            cur = keymap[m.group(1)]
            fields[cur] = m.group(2)
        elif cur:
            fields[cur] += "\n" + line
    return {k: strip_marks(v) for k, v in fields.items()}


def parse_nav(text):
    out = []
    for line in text.split("\n"):
        m = re.match(r"^【(.*)】$", line)
        out.append(m.group(1) if m else re.sub(r"^[　\s]*- ", "", line))
    return out


def parse_persona(text):
    lines = text.split("\n")
    why = lines[0]
    labels = [re.sub(r"^- ", "", ln) for ln in lines[1:] if ln.startswith("- ")]
    return strip_marks(why), [strip_marks(x) for x in labels]


# ================================================================ 套用

def python_string_runs(src):
    """回傳 [(起點, 終點, 字串值)]：相鄰的字串常值（隱式串接）算同一段。"""
    lines = src.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    runs, cur = [], None
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.STRING:
            s = starts[tok.start[0] - 1] + tok.start[1]
            e = starts[tok.end[0] - 1] + tok.end[1]
            try:
                val = ast.literal_eval(tok.string)
            except ValueError:             # f-string 等非固定字串：不可能是要找的文案，切斷這一段
                if cur:
                    runs.append(cur)
                cur = None
                continue
            if cur and isinstance(val, str):
                cur = (cur[0], e, cur[2] + val)
            else:
                cur = (s, e, val)
        elif tok.type in (tokenize.NL, tokenize.COMMENT):
            continue
        else:
            if cur:
                runs.append(cur)
            cur = None
    return runs


def replace_string_literal(src, old, new, where):
    """把程式裡值等於 old 的字串常值換成 new。同一句被多張圖共用時，呼叫端已確認每張圖都改成同一句。"""
    hits = [r for r in python_string_runs(src) if r[2] == old]
    if not hits:
        raise SystemExit(f"{where}：程式裡找不到字串「{old[:40]}」")
    for s, e, _ in sorted(hits, key=lambda h: -h[0]):
        src = src[:s] + json.dumps(new, ensure_ascii=False) + src[e:]
    return src


def html_spans(b, new, cur):
    """一個段落要在 index.html 裡替換的位置與內容：[(起點, 終點, 新內容)]。
    只處理寫在 HTML 裡的段落；圖表、身分推薦、頁面標題描述、介面文字由呼叫端另外處理。"""
    kind = b["kind"]
    spans = []
    if kind == "表格":
        cap, rows = parse_table(new)
        old_rows = b["rows"]
        if [len(r) for r in rows] != [len(r) for r in old_rows]:
            raise SystemExit(f"[{b['id']}] 表格欄列數和網頁不同")
        if cap is not None and b["cap_node"] is not None and plain(cap) != plain(b["caption"]):
            n = b["cap_node"]
            spans.append((n.inner_start, n.inner_end, md_to_html(strip_marks(cap))))
        for r, (nrow, orow) in enumerate(zip(rows, old_rows)):
            for c, (nc, oc) in enumerate(zip(nrow, orow)):
                if plain(nc) != plain(oc):
                    n = b["cells"][r][c]
                    spans.append((n.inner_start, n.inner_end, md_to_html(strip_marks(nc))))
    elif kind == "側欄目錄":
        new_items, nodes = parse_nav(new), b["nodes"]
        old_items = parse_nav(cur)
        if len(new_items) != len(nodes):
            raise SystemExit(f"[{b['id']}] 側欄目錄項目數和網頁不同")
        for n, o, t in zip(nodes, old_items, new_items):
            if t != o:
                spans.append((n.inner_start, n.inner_end, md_to_html(t)))
    elif kind == "封面數字":
        num_node, label_node = b["nodes"]
        m = re.match(r"^(\S+)\s+(.*)$", strip_marks(new))
        spans.append((num_node.inner_start, num_node.inner_end, htmllib.escape(m.group(1))))
        spans.append((label_node.inner_start, label_node.inner_end, md_to_html(m.group(2))))
    elif kind == "小標":
        frag = b["frag_nodes"]
        if len(frag) != 1:
            raise SystemExit(f"[{b['id']}] 小標的結構不是單一元素，無法安全替換")
        spans.append((frag[0].start, frag[0].end, md_to_html(strip_marks(new))))
    else:
        n = b["node"]
        spans.append((n.inner_start, n.inner_end, md_to_html(strip_marks(new))))
    return spans


def apply_spans(html_text, spans):
    for s_, e, r in sorted(spans, key=lambda x: -x[0]):
        html_text = html_text[:s_] + r + html_text[e:]
    return html_text


def apply(draft_path):
    draft = dict(RT.parse_draft(draft_path))
    html_text = EX.INDEX_HTML.read_text(encoding="utf-8")
    figs = EX.load_figures()
    blocks = {b["id"]: b for b in EX.walk(html_text)}
    if set(blocks) != set(draft):
        raise SystemExit(f"稿件段落和網頁不一致：多 {set(draft) - set(blocks)}、少 {set(blocks) - set(draft)}")

    spans, web_src, js_src = [], WEB_DATA_PY.read_text(encoding="utf-8"), EX.APP_JS.read_text(encoding="utf-8")
    changed = []
    fig_repl = {}            # 圖表文字：舊字串 → 新字串（同一句被多張圖共用時，必須改成同一句）
    for bid, new in draft.items():
        b = blocks[bid]
        kind = b["kind"]
        cur = EX.editable_text(b, figs)
        if kind == "表格":
            table_spans = html_spans(b, new, cur)
            if table_spans:
                spans += table_spans
                changed.append(bid)
            continue
        if plain(new) == plain(cur) and strip_marks(new) == cur:
            continue
        changed.append(bid)
        if kind == "圖表":
            fig = figs["figures"][b["fig"]]
            for key, val in parse_fig(new).items():
                if val != fig.get(key):
                    if fig_repl.get(fig[key], val) != val:
                        raise SystemExit(f"[{bid}] {key}：「{fig[key]}」被多張圖共用，但各圖改成不同說法")
                    fig_repl[fig[key]] = val
        elif kind == "身分推薦":
            why, labels = parse_persona(new)
            route = b["route"]
            m = re.search(route["key"] + r":\s*\{.*?why:\s*(.*?),\n\s*sections:", js_src, re.S)
            js_src = js_src[:m.start(1)] + json.dumps(why, ensure_ascii=False) + js_src[m.end(1):]
            for (anchor, old_label), new_label in zip(route["sections"], labels):
                if old_label != new_label:
                    old_lit = f'["{anchor}", "{old_label}"]'
                    if js_src.count(old_lit) != 1:
                        raise SystemExit(f"[{bid}] app.js 找不到唯一的 {old_lit}")
                    js_src = js_src.replace(old_lit, f'["{anchor}", {json.dumps(new_label, ensure_ascii=False)}]')
        elif kind in ("側欄目錄", "封面數字", "小標"):
            spans += html_spans(b, new, cur)
        elif kind == "頁面標題":
            html_text = html_text.replace(f"<title>{cur}</title>", f"<title>{htmllib.escape(new)}</title>", 1)
        elif kind == "頁面描述":
            html_text = html_text.replace(f'content="{cur}"', f'content="{htmllib.escape(new)}"', 1)
        elif kind == "介面文字":
            raise SystemExit("介面文字由程式產生，這支腳本不處理；稿件裡的 ui 段落應維持原樣")
        else:
            spans += html_spans(b, new, cur)

    # 被共用的圖表字串，也要確認沒改的圖不會被連帶改到
    for fid, fig in figs["figures"].items():
        bid = f"fig-{fid}"
        new_fields = parse_fig(draft[bid])
        for key in ("title", "subtitle", "denomNote"):
            if fig.get(key) in fig_repl and new_fields.get(key) != fig_repl[fig[key]]:
                raise SystemExit(f"[{bid}] {key}：和別張圖共用的字串被改了，但這張圖的稿件沒有跟著改")
    for old, new_val in fig_repl.items():
        web_src = replace_string_literal(web_src, old, new_val, "圖表文字")

    # <head> 的替換不影響之後的索引位置？會影響：所以先套 spans（索引以原始檔為準），head 在最後處理
    if any(blocks[k]["kind"] in ("頁面標題", "頁面描述") for k in changed):
        # 頁面標題與描述已直接改進 html_text；spans 位置在 <head> 之後，需依長度差平移
        orig = EX.INDEX_HTML.read_text(encoding="utf-8")
        shift = len(html_text) - len(orig)
        head_end = orig.index("</title>")
        spans = [(s + shift, e + shift, r) if s > head_end else (s, e, r) for s, e, r in spans]
    html_text = apply_spans(html_text, spans)

    EX.INDEX_HTML.write_text(html_text, encoding="utf-8")
    WEB_DATA_PY.write_text(web_src, encoding="utf-8")
    EX.APP_JS.write_text(js_src, encoding="utf-8")
    print(f"套用 {len(changed)} 段（index.html 替換 {len(spans)} 處）")
    print("下一步：python3 13_web_data.py，再用 --check 核對")


def check(draft_path):
    draft = dict(RT.parse_draft(draft_path))
    figs = EX.load_figures()
    blocks = {b["id"]: b for b in EX.walk(EX.INDEX_HTML.read_text(encoding="utf-8"))}
    bad = []
    for bid, new in draft.items():
        b = blocks[bid]
        if b["kind"] == "表格":
            cap, rows = parse_table(new)
            ok = ([[plain(c) for c in r] for r in rows] == [[plain(c) for c in r] for r in b["rows"]]
                  and (cap is None or plain(cap) == plain(b["caption"])))
        else:
            ok = plain(new) == plain(EX.editable_text(b, figs))
        if not ok:
            bad.append(bid)
    print(f"核對 {len(draft)} 段：和稿件不一致 {len(bad)} 段")
    for bid in bad:
        print(f"  [{bid}]\n    稿件：{strip_marks(draft[bid])[:120]}\n    網頁：{EX.editable_text(blocks[bid], figs)[:120]}")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法：python3 18_copyedit_apply.py <審定稿件> [--check]")
    path = Path(sys.argv[1])
    if "--check" in sys.argv:
        check(path)
    else:
        apply(path)
