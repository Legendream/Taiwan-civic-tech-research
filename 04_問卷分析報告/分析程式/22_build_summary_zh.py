# -*- coding: utf-8 -*-
"""
22_build_summary_zh.py — 產生中文精華版首頁 docs/index.html。

來源只有一份：中文精華版/精華版_初稿.md（每段附〔根據〕）。
這支腳本拿掉〔根據〕與檔頭說明，寫出上線用的 中文精華版/精華版.md，再轉成網頁。
Markdown 轉 HTML 沿用英文精華版的做法（20_build_english.py 的 md_block_to_html），版面共用同一份 CSS。

舊連結相容：完整版原本就在網址根目錄，外面流傳的連結常帶章節錨點（例如 /#ch3）。
首頁找不到那個錨點時，自動轉到 full/ 的同一個章節。

執行：python3 22_build_summary_zh.py
"""

import html as htmllib
import re
from pathlib import Path

import common as C

HERE = Path(__file__).parent


def _load(name, file):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EN = _load("en", "20_build_english.py")
AP = EN.AP

DOCS = C.PROJ / "docs"
ZH_DIR = C.OUT_DIR / "中文精華版"
DRAFT_MD = ZH_DIR / "精華版_初稿.md"
ONLINE_MD = ZH_DIR / "精華版.md"

# 舊連結帶著完整版的章節錨點時，轉到 full/ 的同一處
ANCHOR_REDIRECT = """<script>
  // 完整版原本放在網址根目錄；舊連結的章節錨點（例如 /#ch3）在首頁找不到時，轉到完整版的同一處
  (function () {
    function go() {
      var h = location.hash.slice(1);
      if (h && !document.getElementById(decodeURIComponent(h))) location.replace("full/" + location.hash);
    }
    go();
    window.addEventListener("hashchange", go);
  })();
</script>"""


def online_text():
    """初稿 → 上線版：只留分隔線之後的正文，拿掉〔根據〕段落。"""
    src = DRAFT_MD.read_text(encoding="utf-8")
    body = src.split("\n---\n", 1)[1].strip("\n")
    paras = [p for p in body.split("\n\n") if not p.startswith("〔根據〕")]
    return "\n\n".join(paras) + "\n"


def write_online_md(body):
    ONLINE_MD.write_text(
        "# 中文精華版（上線用）\n\n"
        "> 由 `精華版_初稿.md` 拿掉〔根據〕自動產生（22_build_summary_zh.py），不要手改；要改內容請改初稿。\n\n"
        "<!-- 正文開始 -->\n" + body + "<!-- 正文結束 -->\n", encoding="utf-8")


def build(body):
    lines = body.split("\n")
    title = lines[0].lstrip("# ").strip()
    subtitle = lines[2].strip("* ")
    content = EN.md_block_to_html(lines[4:])
    # 中文標題轉不出英文 slug，改用流水號當錨點
    n = iter(range(1, 100))
    content = re.sub(r'<h2 id="">', lambda m: f'<h2 id="sec-{next(n)}">', content)
    desc = "127 位 g0v.tw 參與者告訴我們：怎麼進來、卡在哪裡、為什麼留下。臺灣公民科技調查的 5 分鐘精華版。"
    html = f"""<html lang="zh-Hant">
<meta charset="utf-8">
<title>{htmllib.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{htmllib.escape(desc)}">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="css/style.css">
{EN.head_links("/", "/", "/en/")}
<a class="skip-link" href="#main">跳到主要內容</a>

<div class="layout">
  <main id="main">
    <div class="content summary-page">

      <header id="top" class="cover">
        <p class="cover-eyebrow"><a href="https://g0v.tw/" target="_blank" rel="noopener">g0v.tw</a> 揪松團問卷調查 · 5 分鐘精華版</p>
        <h1 class="report-title">{AP.md_to_html(title)}</h1>
        <p class="cover-hook">{AP.md_to_html(subtitle)}</p>
        <p class="meta-line">作者：鄭婷宇　｜　資料範圍：截至 2026/7/20，共 127 份有效填答</p>
      </header>

{content}

      <p class="cta-row"><a class="download-link" href="full/">閱讀完整版報告 →</a></p>

      <footer>
        <p>CC BY 4.0, by <a href="https://g0v.tw/" target="_blank" rel="noopener">g0v.tw</a> jothon &amp; <a href="https://claire-cheng.com/zh" target="_blank" rel="noopener">Claire Cheng</a></p>
      </footer>
    </div>
  </main>
</div>

{EN.lang_toggle("en/", "English", "Read in English")}
<button type="button" class="theme-toggle" id="themeToggle" aria-label="切換深色／淺色模式">🌙 深色</button>

{ANCHOR_REDIRECT}
<script src="data/figures.js"></script>
<script src="js/charts.js"></script>
<script src="js/app.js"></script>
"""
    out = DOCS / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def main():
    body = online_text()
    if "〔根據〕" in body:
        raise SystemExit("上線版還有〔根據〕：請確認每個〔根據〕都自成一段")
    write_online_md(body)
    out = build(body)
    print(f"✅ 已產生 {ONLINE_MD.relative_to(C.PROJ)}、{out.relative_to(C.PROJ)}")


if __name__ == "__main__":
    main()
