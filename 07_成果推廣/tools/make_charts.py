#!/usr/bin/env python3
"""簡報專用圖表產生器：從 docs/data/figures.json 重繪 5 張圖成獨立 SVG。

數字全部取自 figures.json（與網頁同一份、已通過 14_web_number_check.py 稽核），
不手抄。圖內文字一律 >= 14px，標題交給簡報 HTML 的卡片標題，不放在圖內。

用法：python3 07_成果推廣/tools/make_charts.py
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "docs/data/figures.json").read_text(encoding="utf8"))
FIG = DATA["figures"]
OUT = ROOT / "07_成果推廣/assets/charts"
OUT.mkdir(parents=True, exist_ok=True)

FONT = "'PingFang TC','Heiti TC','Noto Sans TC',sans-serif"
INK, SUB, GRID, FAINT = "#0b0b0b", "#52514e", "#e4e4e0", "#8a8a85"
GREEN, ORANGE, BLUE, GRAY = "#1baf7a", "#eb6834", "#2a78d6", "#d3d3cd"


def pct(x):
    return int(x * 100 + 0.5)


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}">{body}</svg>')


def text(x, y, s, size=18, fill=INK, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{s}</text>')


def write(name, content):
    (OUT / name).write_text(content, encoding="utf8")
    print("wrote", name)


def hbar(name, items, labels, color, n_hi, w=600, row=76):
    """標籤在上、長條在下的橫條圖；前 n_hi 條上色，其餘灰。"""
    h = row * len(items) + 8
    bar_max = w - 150
    parts = []
    for i, it in enumerate(items):
        y = 8 + i * row
        c = color if i < n_hi else GRAY
        parts.append(text(0, y + 22, labels[i], 20, INK if i < n_hi else SUB, 700 if i < n_hi else 400))
        bw = max(4, bar_max * it["pct"])
        parts.append(f'<rect x="0" y="{y + 32}" width="{bw:.1f}" height="24" rx="5" fill="{c}"/>')
        parts.append(text(bw + 10, y + 51, f'{pct(it["pct"])}%', 22, INK, 700))
        parts.append(text(bw + 10 + 56, y + 51, f'{it["n"]}/{it["d"]}', 16, FAINT))
    write(name, svg(w, h, "".join(parts)))


def chart_notjoin():
    items = FIG["fig10_notjoin"]["items"][:5]
    labels = ["不知道有哪些專案或議題", "身邊沒人帶，怕融不進去", "找不到入口、不知如何加入",
              "覺得要會寫程式、門檻太高", "沒有時間"]
    hbar("notjoin.svg", items, labels, GREEN, 3)


def chart_resources():
    items = FIG["fig07_resources"]["items"][:5]
    labels = ["人脈（社群介紹的專家）", "經費（獎助金、標案）", "公開資料、開放資料",
              "場地（例如 NPO Hub）", "現成數位工具或平台"]
    hbar("resources.svg", items, labels, BLUE, 1)


def chart_layers():
    items = FIG["fig01_layers"]["items"]
    colors = [GREEN, ORANGE, BLUE]
    size, cx, cy, r, sw = 400, 200, 200, 135, 86
    parts, start = [], -math.pi / 2
    total = sum(i["n"] for i in items)
    for it, col in zip(items, colors):
        ang = 2 * math.pi * it["n"] / total
        end = start + ang
        x1, y1 = cx + r * math.cos(start), cy + r * math.sin(start)
        x2, y2 = cx + r * math.cos(end), cy + r * math.sin(end)
        large = 1 if ang > math.pi else 0
        parts.append(f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" '
                     f'fill="none" stroke="{col}" stroke-width="{sw}"/>')
        mid = (start + end) / 2
        lx, ly = cx + r * math.cos(mid), cy + r * math.sin(mid)
        parts.append(text(f"{lx:.1f}", f"{ly - 2:.1f}", f'{it["n"]} 人', 22, "#fff", 700, "middle"))
        parts.append(text(f"{lx:.1f}", f"{ly + 22:.1f}", f'{pct(it["pct"])}%', 18, "#fff", 400, "middle"))
        start = end
    parts.append(text(cx, cy + 4, f"{total}", 44, INK, 700, "middle"))
    parts.append(text(cx, cy + 32, "位填答者", 18, SUB, 400, "middle"))
    write("layers.svg", svg(size, size, "".join(parts)))


def chart_kano():
    pts = FIG["fig12_kano_all"]["items"]
    W, H = 640, 400
    px0, py0, pw, ph = 56, 12, 360, 320
    xlo, xhi, ylo, yhi = 0.45, 0.85, -0.55, -0.15  # 局部放大
    X = lambda v: px0 + (v - xlo) / (xhi - xlo) * pw
    Y = lambda v: py0 + (v - yhi) / (ylo - yhi) * ph
    parts = [f'<rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" fill="#fafaf8" stroke="{GRID}"/>']
    # 分界線：x=0.5、y=-0.5
    parts.append(f'<line x1="{X(0.5):.1f}" y1="{py0}" x2="{X(0.5):.1f}" y2="{py0 + ph}" stroke="{FAINT}" stroke-dasharray="5 4"/>')
    parts.append(f'<line x1="{px0}" y1="{Y(-0.5):.1f}" x2="{px0 + pw}" y2="{Y(-0.5):.1f}" stroke="{FAINT}" stroke-dasharray="5 4"/>')
    parts.append(text(px0 + pw - 8, py0 + 26, "魅力型", 20, GREEN, 700, "end"))
    parts.append(text(px0 + pw - 8, Y(-0.5) + 24, "期望型", 20, FAINT, 700, "end"))
    parts.append(text(X(0.5) + 8, py0 + ph - 8, "SI 0.5", 14, FAINT))
    # 軸刻度
    for v in (0.5, 0.6, 0.7, 0.8):
        parts.append(text(f"{X(v):.1f}", py0 + ph + 22, f"{v:.1f}", 14, SUB, 400, "middle"))
    parts.append(text(px0 + pw / 2, py0 + ph + 48, "滿意增益 SI →（越右越想看）", 16, SUB, 400, "middle"))
    for v in (-0.2, -0.3, -0.4, -0.5):
        parts.append(text(px0 - 8, f"{Y(v) + 5:.1f}", f"{v:.1f}", 14, SUB, 400, "end"))
    # 點
    for p in pts:
        c = ORANGE if p["num"] == "⑤" else INK
        x, y = X(p["si"]), Y(p["dsi"])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{c}"/>')
        parts.append(text(f"{x:.1f}", f"{y + 5:.1f}", p["num"], 14, "#fff", 700, "middle"))
    # 圖例
    lx = px0 + pw + 28
    for i, p in enumerate(pts):
        y = 46 + i * 56
        c = ORANGE if p["num"] == "⑤" else INK
        parts.append(f'<circle cx="{lx + 12}" cy="{y - 6}" r="12" fill="{c}"/>')
        parts.append(text(lx + 12, y - 1, p["num"], 14, "#fff", 700, "middle"))
        parts.append(text(lx + 34, y, p["label"], 18, INK, 700 if p["num"] == "⑤" else 400))
        parts.append(text(lx + 34, y + 22, f'SI {p["si"]:.2f}', 14, FAINT))
    write("kano.svg", svg(W, H, "".join(parts)))


def chart_trouble():
    items = FIG["fig05_trouble"]["items"][:5]
    cols = FIG["fig05_trouble"]["seriesColors"]
    labels = ["專案難有穩定進度，容易停滯", "成果很難真正發揮影響力", "核心成員累垮，一個人撐全案",
              "找不到願意一起做的夥伴", "公務員不信任、不給資訊"]
    w, row, bar_w = 600, 62, 440
    parts = []
    for i, it in enumerate(items):
        y = 4 + i * row
        parts.append(text(0, y + 22, labels[i], 20, INK, 400))
        x = 0
        for cnt, col in zip(it["counts"], cols):
            sw_ = bar_w * cnt / it["d"]
            if cnt:
                parts.append(f'<rect x="{x:.1f}" y="{y + 30}" width="{sw_:.1f}" height="24" fill="{col}"/>')
                if cnt >= 3:
                    tc = "#fff" if col in cols[3:] else INK
                    parts.append(text(f"{x + sw_ / 2:.1f}", y + 47, cnt, 14, tc, 700, "middle"))
            x += sw_
        parts.append(text(bar_w + 14, y + 49, f'3 分以上 {pct(it["pct3plus"])}%', 18, INK, 700))
    ly = 4 + 5 * row + 6
    short = ["1 幾乎沒影響", "2 有點困擾", "3 明顯卡住", "4 萌生退意", "5 無法持續"]
    lx = 0
    for col, s in zip(cols, short):
        parts.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" fill="{col}"/>')
        parts.append(text(lx + 20, ly + 13, s, 14, SUB))
        lx += 122
    write("trouble.svg", svg(w, ly + 26, "".join(parts)))


if __name__ == "__main__":
    chart_notjoin()
    chart_resources()
    chart_layers()
    chart_kano()
    chart_trouble()
