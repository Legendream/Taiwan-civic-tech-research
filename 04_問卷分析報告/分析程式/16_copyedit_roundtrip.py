# -*- coding: utf-8 -*-
"""
16_copyedit_roundtrip.py — 核對《改稿稿件.md》的正文和網頁實際顯示的文字一字不差。

為什麼要有這支腳本
------------------
15_copyedit_export.py 是從 index.html 原始碼切出段落。如果切的時候漏段、斷句、
把連結或粗體轉錯，改稿包就不是網頁的全文，改完套回去也會缺東西。
這支腳本換一條路徑核對：拿**瀏覽器實際算繪出來的畫面文字**（含 JS 產生的圖表標題、
身分推薦），和改稿稿件逐段比對。

兩個方向都查：
  1. 改稿稿件 → 畫面：每一段正文都要在畫面上找得到，順序也要一致（差異必須是零）
  2. 畫面 → 改稿稿件：畫面上沒被任何一段涵蓋的文字全部列出來，逐條說明為什麼不在改稿範圍
     （圖表資料表、圖示等由程式從資料產生的內容）

也提供 parse_draft()，之後讀回改過的稿件時共用。

畫面文字怎麼取得
----------------
在瀏覽器打開網頁，於開發者主控台執行下面這段，把結果存成 JSON：

    document.querySelectorAll('details').forEach(d => d.open = true);
    const persona = {};
    document.querySelectorAll('.persona-btn').forEach(b => {
      b.click(); persona[b.dataset.persona] = document.getElementById('personaResult').innerText; });
    const clone = document.body.cloneNode(true);
    clone.querySelectorAll('script,style,svg').forEach(e => e.remove());
    clone.style.position = 'absolute'; clone.style.left = '-99999px';
    document.body.appendChild(clone);
    const dump = {title: document.title,
      description: document.querySelector('meta[name=description]').content,
      body: clone.innerText, persona};
    clone.remove();
    copy(JSON.stringify(dump));   // 複製到剪貼簿，貼進 rendered.json

執行：python3 16_copyedit_roundtrip.py <rendered.json>
"""

import json
import re
import sys

import common as C

DRAFT_MD = C.OUT_DIR / "改稿包" / "改稿稿件.md"

BLOCK_RE = re.compile(r"<!-- 正文開始 (\S+) -->\n(.*?)\n<!-- 正文結束 \1 -->", re.S)


def parse_draft(path=DRAFT_MD):
    """回傳 [(段落編號, 正文原樣), ...]，依稿件順序。"""
    return BLOCK_RE.findall(path.read_text(encoding="utf-8"))


def to_plain_segments(bid, text):
    """把稿件正文（Markdown＋改稿標記）轉回畫面上會看到的文字片段。"""
    text = text.replace("〔鎖〕", "").replace("〔維持〕", "")
    text = re.sub(r"\[\^(\d+)\]", r"\1", text)                 # 註腳
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)        # 連結
    text = text.replace("**", "")
    segs = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or re.fullmatch(r"\|(-+\|)+", line):
            continue
        if line.startswith("|"):
            segs += [c.strip() for c in line.strip("|").split("|") if c.strip()]
            continue
        line = re.sub(r"^(表格標題|圖標題|圖副標|分母說明)：", "", line)
        line = re.sub(r"^【(.*)】$", r"\1", line)
        line = re.sub(r"^[　\s]*- ", "", line)
        segs.append(line)
    return segs


def norm(s):
    return re.sub(r"\s+", "", s)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：python3 16_copyedit_roundtrip.py <rendered.json>")
    dump = json.loads(open(sys.argv[1], encoding="utf-8").read())
    body = norm(dump["body"])
    persona = {k: norm(v) for k, v in dump["persona"].items()}
    covered = [False] * len(body)

    missing, out_of_order, pos, n_seg = [], [], 0, 0
    for bid, raw in parse_draft():
        segs = to_plain_segments(bid, raw)
        for seg in segs:
            s = norm(seg)
            n_seg += 1
            if bid == "meta-title":
                ok = s == norm(dump["title"])
            elif bid == "meta-description":
                ok = s == norm(dump["description"])
            elif bid.startswith("persona-route-"):
                ok = s in persona[bid.split("-")[-1]]
            elif bid == "ui":
                # 「☀️ 淺色」只在深色模式出現、「☰ 章節」只在手機版顯示，桌機淺色畫面上看不到
                ok = s in body or s in ("☀️淺色", "☰章節")
                for m in re.finditer(re.escape(s), body):        # 介面文字重複出現，全部標記
                    covered[m.start():m.end()] = [True] * len(s)
            else:
                i = body.find(s, pos)
                if i < 0:
                    j = body.find(s)
                    if j < 0:
                        missing.append((bid, seg))
                        continue
                    out_of_order.append((bid, seg))
                    i = j
                else:
                    pos = i + len(s)
                covered[i:i + len(s)] = [True] * len(s)
                continue
            if not ok:
                missing.append((bid, seg))

    # 畫面上沒被涵蓋的文字，依連續區段列出
    leftovers, cur = [], ""
    for ch, c in zip(body, covered):
        if c:
            if cur:
                leftovers.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        leftovers.append(cur)

    print(f"改稿稿件共 {n_seg} 個文字片段")
    print(f"  在畫面上找不到：{len(missing)}")
    for bid, seg in missing:
        print(f"    [{bid}] {seg[:80]}")
    print(f"  順序和畫面不一致：{len(out_of_order)}")
    for bid, seg in out_of_order:
        print(f"    [{bid}] {seg[:80]}")
    print(f"\n畫面上沒被改稿稿件涵蓋的文字：{len(leftovers)} 段（逐段列出，需人工確認都屬於程式產生的內容）")
    for x in leftovers:
        print("   ", x[:160] + ("…" if len(x) > 160 else ""))
    if missing or out_of_order:
        sys.exit(1)


if __name__ == "__main__":
    main()
