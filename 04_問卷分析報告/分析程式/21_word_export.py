# -*- coding: utf-8 -*-
"""
21_word_export.py — 把網頁（中英文的精華版、完整版）轉成 Word 檔，文字和圖放在一起。

給想拿報告去用、但不方便用網頁的人（例如揪松團）。內容直接取自網頁上實際顯示的文字，
所以網頁改了，重跑這支就會跟著更新，不會出現 Word 和網頁說法不一致。

做法：
  1. 起一個本機伺服器提供 docs/，並把 21_word_export.js 注入英文頁
  2. 用無頭 Chrome（桌機寬度 1400px）開頁面，JS 把正文序列化、圖表 SVG 轉成 PNG 傳回
  3. 用 python-docx 組成 Word

和網頁刻意不同的地方（只在網頁上有作用的介面）：
  · 拿掉下載按鈕、封面插圖與關鍵數字、「View data table」、分群切換按鈕、
    「Read more」摺疊標籤、註腳的「↩ Back to text」
  · 「依身分選讀」在網頁上要按按鈕，Word 改成三段文字列出
  · 有分群切換的圖只放預設的「All three groups」畫面

需要：Google Chrome、python-docx（pip3 install python-docx）
執行：python3 21_word_export.py
輸出：../英文版/Word版/*.docx、../中文網頁版Word/*.docx
"""

import json
import re
import shutil
import subprocess
import tempfile
import threading
import base64
import http.server
import functools
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent.parent / "docs"
EN_OUT = HERE.parent / "英文版" / "Word版"
ZH_OUT = HERE.parent / "中文網頁版Word"   # 網頁版的副本；交付甲方的正式定稿仍是 公民科技生態系分析報告_定稿.docx
JS = HERE / "21_word_export.js"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# (代號, 網頁路徑, 輸出資料夾, 檔名, 語言)
PAGES = [("summary", "en/", EN_OUT, "Taiwan civic tech survey - summary (EN).docx", "en"),
         ("full", "en/full/", EN_OUT, "Taiwan civic tech survey - full report (EN).docx", "en"),
         ("zh_summary", "", ZH_OUT, "臺灣公民科技生態系調查－精華版（網頁版）.docx", "zh"),
         ("zh_full", "full/", ZH_OUT, "臺灣公民科技生態系調查－完整版（網頁版）.docx", "zh")]
TIMEOUT = 90   # 每頁最多等幾秒

MAX_W, MAX_H = 6.5, 8.0   # 圖片最大寬高（吋），讓標題和圖能放在同一頁
def link(par, text, url, bold=False, size=None):
    r_id = par.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), r_id)
    r = OxmlElement('w:r'); rp = OxmlElement('w:rPr')
    if bold: rp.append(OxmlElement('w:b'))
    c = OxmlElement('w:color'); c.set(qn('w:val'), '1F5FBF'); rp.append(c)
    u = OxmlElement('w:u'); u.set(qn('w:val'), 'single'); rp.append(u)
    if size: sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(int(size * 2))); rp.append(sz)
    r.append(rp); t = OxmlElement('w:t'); t.text = text; t.set(qn('xml:space'), 'preserve'); r.append(t); h.append(r); par._p.append(h)
def fill(par, runs, size=None, bold=None):
    for x in runs:
        if x.get('link'): link(par, x['text'], x['link'], x.get('bold') or bold, size); continue
        r = par.add_run(x['text']); r.bold = bold or x.get('bold'); r.italic = x.get('italic'); r.font.superscript = x.get('sup')
        if size: r.font.size = Pt(size)
    return par
def build(D, stem, out_path, lang_code="en"):
    blocks = json.load(open(f"{D}/{stem}_blocks.json"))
    doc = Document(); st = doc.styles['Normal']; st.font.name = 'Calibri'; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), 'PingFang TC')   # 中文字（人名、署名）用的字型
    lang = OxmlElement('w:lang'); lang.set(qn('w:val'), 'en-US' if lang_code == 'en' else 'zh-TW'); lang.set(qn('w:eastAsia'), 'zh-TW'); st.element.rPr.append(lang)
    if lang_code == 'zh':   # 標題樣式也用中文字型，否則 Word 會用預設的日文明體
        for name in ('Title', 'Heading 1', 'Heading 2', 'Heading 3'):
            hs = doc.styles[name]; hs.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'PingFang TC')
    colon = ': ' if lang_code == 'en' else '：'
    has_parts = any(x.get('part') for x in blocks)
    last_lv = 0
    for s in doc.sections: s.left_margin = s.right_margin = Inches(0.9)
    for b in blocks:
        t = b['t']
        if t == 'h':
            if b['level'] == 1: lv = 0
            elif has_parts: lv = 1 if b.get('part') else b['level']
            else: lv = b['level'] - 1
            lv = min(lv, 3, last_lv + 1); last_lv = max(lv, 1)   # 不跳層
            fill(doc.add_heading(level=lv), b['runs'])
        elif t == 'p':
            p = fill(doc.add_paragraph(), b['runs'], size=9.5 if b.get('fn') else None)
        elif t == 'li':
            text = ''.join(r['text'] for r in b['runs'])
            if b['ordered'] and re.match(r'\d+\.', text):   # 網頁文字本身已帶編號，不再加自動編號
                p = fill(doc.add_paragraph(), b['runs']); p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.keep_with_next = True
            else:
                style = ('List Number' if b['ordered'] else 'List Bullet') + (' 2' if b['depth'] else '')
                fill(doc.add_paragraph(style=style), b['runs'])
        elif t == 'callout':
            p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.3)
            r = p.add_run(b['label'] + colon); r.bold = True; r.font.color.rgb = RGBColor(0x1B, 0x8F, 0x64)
            fill(p, b['runs'])
        elif t == 'table':
            if b.get('caption'):
                p = fill(doc.add_paragraph(), b['caption'], bold=True); p.paragraph_format.keep_with_next = True
            rows = b['rows']; n = max(len(r) for r in rows)
            tb = doc.add_table(rows=len(rows), cols=n); tb.style = 'Table Grid'
            if b['header']:   # 表頭列跨頁時重複出現
                trPr = tb.rows[0]._tr.get_or_add_trPr(); h = OxmlElement('w:tblHeader'); h.set(qn('w:val'), 'true'); trPr.append(h)
            for row in tb.rows:   # 同一列不拆到兩頁
                row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    fill(tb.cell(i, j).paragraphs[0], cell, bold=(i == 0 and b['header']) or None)
            doc.add_paragraph()
        elif t == 'img':
            p = fill(doc.add_paragraph(), b['title'], bold=True); p.paragraph_format.keep_with_next = True
            if b['subtitle']:
                p = fill(doc.add_paragraph(), b['subtitle'], size=9.5); p.paragraph_format.keep_with_next = True
            w = min(MAX_W, b['w'] / 100, MAX_H * b['w'] / b['h'])
            doc.add_picture(f"{D}/{b['file']}", width=Inches(w))
            doc.paragraphs[-1].paragraph_format.keep_with_next = bool(b['note'])
            if b['note']: fill(doc.add_paragraph(), b['note'], size=9.5)
    doc.save(out_path)
    print(f"✅ {out_path.name}：{len(blocks)} 段、{sum(b['t'] == 'img' for b in blocks)} 張圖")


def serve(tmp, done):
    """提供 docs/；英文頁注入匯出腳本；收 POST 存到暫存資料夾。"""
    class H(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            path, _, query = self.path.partition("?")
            if path == "/__word_export.js":
                return self._send(JS.read_bytes(), "application/javascript")
            if "export=" in query and path in ("/", "/full/", "/en/", "/en/full/"):
                html = (DOCS / path.strip("/") / "index.html").read_text(encoding="utf-8")
                html += '\n<script src="/__word_export.js"></script>\n'   # 網頁沒有 </body>，接在最後
                return self._send(html.encode("utf-8"), "text/html; charset=utf-8")
            return super().do_GET()

        def do_POST(self):
            data = self.rfile.read(int(self.headers["Content-Length"]))
            name = Path(self.path.partition("?")[0]).name
            if name == "__done":
                done["msg"] = data.decode("utf-8"); done["event"].set()
            else:
                if name.endswith(".png"):
                    data = base64.b64decode(data.split(b",", 1)[1])
                (tmp / name).write_bytes(data)
            self.send_response(204); self.end_headers()

        def _send(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def capture(port, page, stem, done, tmp):
    done["event"].clear(); done["msg"] = ""
    profile = tempfile.mkdtemp()
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                             "--window-size=1400,900", f"--user-data-dir={profile}",
                             f"http://127.0.0.1:{port}/{page}?export={stem}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not done["event"].wait(TIMEOUT):
            raise SystemExit(f"❌ {page} 等了 {TIMEOUT} 秒沒有完成匯出")
        if done["msg"] != "ok":
            raise SystemExit(f"❌ {page} 匯出失敗：{done['msg']}")
    finally:
        proc.terminate(); proc.wait()
        shutil.rmtree(profile, ignore_errors=True)


def main():
    done = {"event": threading.Event(), "msg": ""}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        srv = serve(tmp, done)
        try:
            for stem, page, out_dir, out, lang_code in PAGES:
                out_dir.mkdir(parents=True, exist_ok=True)
                capture(srv.server_address[1], page, stem, done, tmp)
                build(tmp, stem, out_dir / out, lang_code)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    main()
