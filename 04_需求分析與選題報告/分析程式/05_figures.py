# -*- coding: utf-8 -*-
"""
05_figures.py — 所有圖表輸出。

依 dataviz skill 的程序：先選圖形（依資料要做的事），再依職能指派顏色，
顏色已用 validate_palette.js 驗證（見 common.PALETTE 註解）。

圖形選擇：
  · 量值排序（困擾、活動意願、管道、地區）→ 橫條，單一數列不放圖例，直接標數值
  · 量值矩陣（資源×階段）→ 熱區，單一色相由淺到深
  · 極性矩陣（年齡×動機 lift，中點 1.0）→ 分歧配色，兩色相＋中性灰中點
  · 兩點之間的變化（初次→持續動機）→ 斜線圖，兩端直接標示
  · 二維落點（狩野 SI×DSI）→ 散佈圖＋四象限
  · 分群比較（三層×需求）→ 分組橫條，固定色序＋圖例

所有圖都附對應的數據 CSV（分析結果/），滿足 relief rule 與可追溯性。

輸出：圖表v2/*.png

執行：python3 05_figures.py
"""

import re

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import common as C

plt = C.setup_matplotlib()
SEQ = LinearSegmentedColormap.from_list("seq", C.PALETTE["seq"])
DIV = LinearSegmentedColormap.from_list(
    "div", [C.PALETTE["div_low"], C.PALETTE["div_mid"], C.PALETTE["div_high"]])


def titles(ax, title, subtitle="", extra_pad=0.0):
    """
    標題與副標一律用 axes 座標手動排版：副標可能有多行，
    交給 set_title 的 pad 會與副標重疊（實際渲染後目視確認過）。

    extra_pad：座標區上方另有元素（例如狩野圖的象限標籤框）時，把標題再往上推。
    """
    lines = subtitle.count("\n") + 1 if subtitle else 0
    sub_y = 1.015 + extra_pad
    title_y = sub_y + 0.036 * lines + 0.012
    if subtitle:
        ax.text(0, sub_y, subtitle, transform=ax.transAxes, fontsize=8.5,
                color="#52514e", va="bottom", linespacing=1.5)
    ax.text(0, title_y, title, transform=ax.transAxes, fontsize=13,
            color="#0b0b0b", va="bottom")


def style_axes(ax, xlabel="", title="", subtitle=""):
    ax.grid(axis="x", color=C.PALETTE["grid"], linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9, color="#52514e")
    if title:
        titles(ax, title, subtitle)


def spread(values, min_gap):
    """
    標籤防重疊：把靠得太近的標籤位置推開，回傳每個原始位置對應的繪製位置。
    數值相同或相近時（例如兩條線都收在 15），文字才不會疊在一起。
    """
    order = np.argsort(values)
    placed = np.array(values, dtype=float)
    for k in range(1, len(order)):
        i, j = order[k - 1], order[k]
        if placed[j] - placed[i] < min_gap:
            placed[j] = placed[i] + min_gap
    return placed


def hbar(df, label_col, value_col, num_col, denom, title, subtitle, fname,
         color=None, figsize=None):
    """橫條：單一數列不放圖例，每條直接標「比例（分子/分母）」。"""
    d = df.sort_values(value_col)
    fig, ax = plt.subplots(figsize=figsize or (9, 0.42 * len(d) + 1.8))
    bars = ax.barh(d[label_col], d[value_col], height=0.62,
                   color=color or C.PALETTE["primary"], zorder=2)
    for bar, v, n in zip(bars, d[value_col], d[num_col]):
        ax.text(v + max(d[value_col]) * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{v:.0%}  ({int(n)}/{denom})", va="center", fontsize=8.5, color="#52514e")
    ax.set_xlim(0, max(d[value_col]) * 1.28)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    style_axes(ax, title=title, subtitle=subtitle)
    C.save_fig(fig, fname)
    plt.close(fig)


def main():
    T = C.TABLE_DIR

    # ---------------- 1. 困擾：完整五級分布 ----------------
    # （原本另有一張只畫「3 分以上」的橫條，與五級堆疊圖重複且資訊較少，已移除）
    # 困擾：完整五級堆疊（1–5 分全部顯示）
    # 不要只畫「3 分以上／4 分以上」的合計——那會讓「有幾個人給到 5 分」完全看不見。
    # 但 5 分在各題只有 0–3 人，單獨畫一張又幾乎全是雜訊，故用堆疊呈現完整分布。
    dist = pd.read_csv(T / "03_困擾_五級分布.csv").sort_values("3分以上_比例")
    score_cols = [c for c in dist.columns if re.match(r"^[1-5]分_", c)]
    # 1、2 分用淺灰（沒卡住），3–5 分用逐漸加深的暖色（卡住的程度）
    stack_colors = ["#e8e8e4", "#cfcfc9", "#f4c6ad", "#e8895b", "#b5342a"]
    fig, ax = plt.subplots(figsize=(11, 0.5 * len(dist) + 2.4))
    left = np.zeros(len(dist))
    ypos = np.arange(len(dist))
    for col, colr in zip(score_cols, stack_colors):
        vals = dist[col].values
        ax.barh(ypos, vals, left=left, height=0.66, color=colr,
                label=col.replace("_", "："), zorder=2)
        for y, v, l in zip(ypos, vals, left):
            if v >= 3:                       # 太窄的格子不標，避免疊字
                ax.text(l + v / 2, y, str(int(v)), ha="center", va="center",
                        fontsize=8.5, color="#0b0b0b")
        left += vals
    ax.set_yticks(ypos, dist["困難"], fontsize=9)
    ax.set_xlim(0, 47)
    ax.set_xlabel("人數（每題皆為 47 位曾參與者）", fontsize=9, color="#52514e")
    ax.legend(frameon=False, fontsize=8, ncol=5, loc="upper center",
              bbox_to_anchor=(0.5, -0.09))
    ax.grid(axis="x", color=C.PALETTE["grid"], lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=9)
    titles(ax, "每項困難的困擾程度分布（1–5 分完整呈現）",
           "依「3 分以上人數」由多到少排列｜格內數字為人數，3 人以下未標\n"
           "此題沒有「沒遇到」選項，所以 1 分同時包含「沒發生過」與「發生了但不影響」")
    C.save_fig(fig, "02_困擾_五級分布")
    plt.close(fig)

    # ---------------- 2a. 狩野落點圖（全體，單張）----------------
    for src, fname, title, sub in [
        ("02_狩野_全體.csv", "03_狩野落點_全體", "五個文章主題的狩野落點（全體）",
         "N=126｜SI 0–1、DSI 0～−1 全幅，分界線 0.5／−0.5 位於正中央\n"
         "五個主題全部落在「魅力 A」，其中「落地、接進體制」最靠近期望 O 邊界"),
    ]:
        k = pd.read_csv(T / src)
        k["短名"] = k["主題"].map(C.KANO_SHORT)
        fig, ax = plt.subplots(figsize=(10, 7.2))

        # 一定要用全幅座標軸（SI 0–1、DSI 0～−1）。
        # 一旦為了把點放大而縮放座標軸，0.5／−0.5 分界線就不在正中央，
        # 四個角落的象限標籤便對不上它們實際代表的區域，圖會誤導人。
        ax.set_xlim(0, 1)
        ax.set_ylim(-1, 0)
        ax.axvline(0.5, color=C.PALETTE["neutral"], lw=1, ls="--", zorder=1)
        ax.axhline(-0.5, color=C.PALETTE["neutral"], lw=1, ls="--", zorder=1)

        # 象限標籤放在座標區「外面」的四個角，做成圓角標籤框，
        # 才不會與資料點、圖例搶位置，也不會被誤認成資料標註。
        # 刻度刻意避開 0 與 1 兩端，四個角才空得出來放象限框（與參考圖一致）
        ax.set_xticks([0.25, 0.50, 0.75])
        ax.set_yticks([0.0, -0.25, -0.50, -0.75])
        box = dict(boxstyle="round,pad=0.55", facecolor="#dce6f7",
                   edgecolor="none")
        # 往外挪一點：貼太近會蓋住 y 軸最上方的 0.00 刻度文字
        for (bx, by), txt, ha, va in [((-0.055, 1.035), "無差別", "left", "bottom"),
                                      ((1.055, 1.035), "魅力", "right", "bottom"),
                                      ((-0.055, -0.045), "基本", "left", "top"),
                                      ((1.055, -0.045), "期望", "right", "top")]:
            ax.text(bx, by, txt, transform=ax.transAxes, fontsize=12,
                    color="#1b3a63", ha=ha, va=va, bbox=box, zorder=5)

        ax.scatter(k["SI"], k["DSI"], s=140, color=C.PALETTE["primary"],
                   edgecolor=C.PALETTE["surface"], linewidth=2, zorder=3)
        s = k.sort_values("DSI")
        for (_, r), ly in zip(s.iterrows(), spread(s["DSI"].tolist(), 0.085)):
            ax.annotate(f"{C.KANO_NUM[r['主題']]} {r['短名']}　({r['SI']:.2f}, {r['DSI']:.2f})",
                        (r["SI"], r["DSI"]), xytext=(0.02, ly),
                        fontsize=9, color="#52514e", ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=C.PALETTE["grid"], lw=0.9))
        ax.set_xlabel("SI 滿意度增加指數 →", fontsize=9, color="#52514e")
        ax.set_ylabel("← DSI 不滿意度消除指數", fontsize=9, color="#52514e")
        ax.grid(color=C.PALETTE["grid"], lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(length=0, labelsize=9)
        for side in ("top", "right"):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_color(C.PALETTE["grid"])
        # 上方兩個象限框佔了 ~0.07 的高度，標題要再往上推才不會疊到
        titles(ax, title, sub, extra_pad=0.075)
        C.save_fig(fig, fname)
        plt.close(fig)

    # ------------- 2a-2. 舊報告圖 3-1 的更新版（沿用 v1 視覺語言，只換數字）-------------
    # v2.docx 內嵌的圖 3-1 原本是 N=120 版，表格更新到 N=126 後圖表會自相矛盾。
    # 這裡重畫同一張圖：彩色象限底 ＋ 象限說明文字，維持 v1 的樣子，只有數據換新。
    ka = pd.read_csv(T / "02_狩野_全體.csv")
    # 尺寸鎖定 1560x1118（dpi 150），與 docx 內嵌原圖同長寬比，換圖時才不會被拉伸
    fig, ax = plt.subplots(figsize=(1560 / 150, 1118 / 150))
    ax.set_xlim(0, 1)
    ax.set_ylim(-1, 0)
    quad = [((0.5, -0.5, 0.5, 0.5), "#efefec"),      # 左上 無差異 I
            ((0.5, -0.5, 0.5, 0.5), None)]
    ax.add_patch(plt.Rectangle((0, -0.5), 0.5, 0.5, facecolor="#efefec", zorder=0))
    ax.add_patch(plt.Rectangle((0.5, -0.5), 0.5, 0.5, facecolor="#fbecd9", zorder=0))
    ax.add_patch(plt.Rectangle((0, -1), 0.5, 0.5, facecolor="#e8f1e8", zorder=0))
    ax.add_patch(plt.Rectangle((0.5, -1), 0.5, 0.5, facecolor="#e2ebf6", zorder=0))
    ax.axvline(0.5, color="#8a8a85", lw=1.2, ls="--", zorder=1)
    ax.axhline(-0.5, color="#8a8a85", lw=1.2, ls="--", zorder=1)

    n_valid = int(ka["有作答"].max())
    # 右側兩個象限的說明靠右對齊、貼著邊界（沿用 v1 的擺法）：
    # 資料點集中在 SI 0.6–0.8，說明文字若置中會壓到「留住夥伴」的標籤。
    quad_text = [
        (0.25, -0.06, "center", 0.25, "center", "無差異 I", "#8a8a85",
         "有沒有這篇文章，讀者\n都無感。\n→ 寫了 CP 值低，可略過"),
        (0.75, -0.06, "center", 0.985, "right", "魅力 A（驚喜加分）", "#c8621f",
         "有→驚喜、大加分；沒有→也不會怪你。\n→ 差異化亮點，本次 5 主題全落此區"),
        (0.25, -0.56, "center", 0.25, "center", "基本 M（必備門檻）", "#3f7d46",
         "有→視為理所當然；\n沒有→會不滿、扣分。\n→ 沒寫像缺漏，必補"),
        (0.75, -0.56, "center", 0.985, "right", "期望 O（越多越好）", "#2a5f9e",
         "有→滿意度線性上升；\n沒有→明顯失望。\n→ 投資報酬穩定，該寫"),
    ]
    for qx, qy, hha, bx, bha, head, colr, body in quad_text:
        ax.text(qx, qy, head, fontsize=13, color=colr, ha=hha, va="top", zorder=2)
        ax.text(bx, qy - 0.055, body, fontsize=9, color="#52514e",
                ha=bha, va="top", linespacing=1.6, zorder=2)

    # 標籤位置沿用 v1 的擺法，並避開彼此
    label_off = {
        "怎麼捲動更多人（包含不會寫程式的人）一起參與": (-0.055, 0.052, "center"),
        "怎麼留住夥伴、維持團隊運作的能量": (0.055, 0.052, "center"),
        "如何發起一個公民科技專案": (-0.035, -0.075, "center"),
        "沒有現成資料時，怎麼搜尋、整理或自建資料集": (0.075, 0.030, "left"),
        "怎麼讓做好的東西真正落地、接進體制": (0.022, 0.048, "left"),
    }
    ax.scatter(ka["SI"], ka["DSI"], s=170, color="#b5342a",
               edgecolor="#ffffff", linewidth=2, zorder=4)
    for _, r in ka.iterrows():
        dx, dy, ha = label_off[r["主題"]]
        ax.text(r["SI"] + dx, r["DSI"] + dy,
                f"{C.KANO_SHORT[r['主題']]}\nSI={r['SI']:.2f}",
                fontsize=9.5, color="#b5342a", ha=ha, va="center",
                linespacing=1.5, zorder=5)

    ax.set_xlabel("SI 滿意影響力 →（有這篇文章能加多少分；越右越加分）", fontsize=10, color="#333")
    ax.set_ylabel("DSI 不滿意影響力 ↓（沒這篇文章會扣多少分；越下越扣分）", fontsize=10, color="#333")
    ax.set_title(f"狩野模型四象限 × 5 個方法論文章主題（有效樣本 {n_valid} 份）",
                 fontsize=14, pad=14)
    ax.tick_params(length=0, labelsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color("#cccccc")
    C.save_fig(fig, "00_狩野四象限說明圖_N126", bbox=None)
    plt.close(fig)

    # ---------------- 2b. 狩野落點：入坑三層（小倍數）----------------
    # 三層 15 個點畫在同一張圖，只有 5 個標得到名字、其餘 10 個無法對應主題。
    # 改用小倍數：一層一個面板，每個點都標編號 ①–⑤，下方一次列出對照表。
    # 編號沿用舊報告附錄表 10 的 ①–⑤，兩份文件可以互相對照。
    kl = pd.read_csv(T / "02_狩野_三層.csv")
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.9), sharex=True, sharey=True)
    for ax, layer in zip(axes, C.LAYER_ORDER):
        s = kl[kl["分群"] == layer]
        n = int(s["群體N"].iloc[0])
        ax.set_xlim(0, 1)
        ax.set_ylim(-1, 0)
        ax.set_xticks([0.25, 0.50, 0.75])
        ax.set_yticks([0.0, -0.25, -0.50, -0.75])
        ax.axvline(0.5, color=C.PALETTE["neutral"], lw=1, ls="--", zorder=1)
        ax.axhline(-0.5, color=C.PALETTE["neutral"], lw=1, ls="--", zorder=1)
        # 象限標示：小倍數裡改用面板內的淡色小字，12 個標籤框會太吵
        for (qx, qy), txt, ha, va in [((0.03, -0.03), "無差別", "left", "top"),
                                      ((0.97, -0.03), "魅力", "right", "top"),
                                      ((0.03, -0.97), "基本", "left", "bottom"),
                                      ((0.97, -0.97), "期望", "right", "bottom")]:
            ax.text(qx, qy, txt, fontsize=8, color="#a8a8a2", ha=ha, va=va)

        ax.scatter(s["SI"], s["DSI"], s=90, color=C.PALETTE["layers"][layer],
                   edgecolor=C.PALETTE["surface"], linewidth=1.6, zorder=3)
        # 編號放在點的外側並做碰撞避讓：兩個主題落點很近時（例如曾參與層的 ③④），
        # 把編號畫在點「裡面」會互相遮住，看不出哪個點是哪個主題。
        placed = []
        for _, r in s.sort_values("SI").iterrows():
            x, y = r["SI"], r["DSI"]
            for dx, dy in [(10, 9), (10, -12), (-12, 9), (-12, -12), (0, 15), (0, -17)]:
                if all(abs(x - px) > 0.05 or abs(y - py) > 0.06 or (dx, dy) != off
                       for px, py, off in placed):
                    break
            placed.append((x, y, (dx, dy)))
            ax.annotate(C.KANO_NUM[r["主題"]], (x, y), xytext=(dx, dy),
                        textcoords="offset points", fontsize=10.5,
                        color=C.PALETTE["layers"][layer], ha="center", va="center", zorder=4)
        note = "，人數少僅供參考" if n < 30 else ""
        ax.set_title(f"{C.LAYER_PLAIN[layer]}（{n} 人{note}）", fontsize=11, pad=8)
        ax.grid(color=C.PALETTE["grid"], lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(length=0, labelsize=8.5)
        for side in ("top", "right"):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_color(C.PALETTE["grid"])

    axes[0].set_ylabel("← DSI 不滿意度消除指數", fontsize=9, color="#52514e")
    axes[1].set_xlabel("SI 滿意度增加指數 →", fontsize=9, color="#52514e")

    # 編號對照表：一次列出，三個面板共用
    legend = "　".join(f"{C.KANO_NUM[t]} {C.KANO_SHORT[t]}" for t in C.KANO_NUM)
    fig.text(0.5, -0.02, legend, ha="center", fontsize=9.5, color="#52514e")
    fig.text(0.5, -0.075,
             "每個面板都是完整的狩野四象限（SI 0–1、DSI 0～−1，分界線在正中央）；"
             "同一個編號在三個面板中是同一個主題，可直接橫向比較落點位移。",
             ha="center", fontsize=8.5, color="#52514e")
    fig.suptitle("三群人分別覺得哪些主題值得寫", fontsize=13, x=0.09, ha="left", y=1.04)
    fig.text(0.09, 0.99, "「捲動更多人」③ 與「留住夥伴」④ 對還沒接觸的人落在「無差別」，"
                         "對另外兩群都是「魅力」：沒進場的人感受不到團隊經營的痛",
             ha="left", fontsize=8.5, color="#52514e")
    C.save_fig(fig, "04_狩野落點_三層")
    plt.close(fig)

    # ---------------- 3. 資源 × 專案階段（順序型熱區）----------------
    rs = pd.read_csv(T / "03_資源×專案階段.csv")
    rs = rs[rs["選項"] != "所屬社團夥伴一起討論"]          # 單一自由填答，不入矩陣
    piv = rs.pivot(index="選項", columns="分群", values="群內比例")
    piv = piv.reindex(columns=[c for c in C.STAGE_COARSE_ORDER if c in piv.columns])
    piv = piv.loc[piv.mean(axis=1).sort_values(ascending=False).index]
    denoms = {g: int(rs.loc[rs["分群"] == g, "分母"].iloc[0]) for g in piv.columns}
    nums = rs.pivot(index="選項", columns="分群", values="分子").reindex(
        index=piv.index, columns=piv.columns)

    fig, ax = plt.subplots(figsize=(8.2, 0.62 * len(piv) + 2.4))
    im = ax.imshow(piv.values, cmap=SEQ, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(piv.columns)),
                  [f"{c}\n(N={denoms[c]})" for c in piv.columns], fontsize=9)
    ax.set_yticks(range(len(piv.index)), piv.index, fontsize=9)
    for i in range(len(piv.index)):
        for j in range(len(piv.columns)):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.0%}\n({int(nums.values[i, j])}/{denoms[piv.columns[j]]})",
                    ha="center", va="center", fontsize=8,
                    color="#ffffff" if v > 0.55 else "#0b0b0b")
    ax.set_xticks(np.arange(-.5, len(piv.columns), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(piv.index), 1), minor=True)
    ax.grid(which="minor", color=C.PALETTE["surface"], linewidth=2)
    ax.tick_params(which="both", length=0)
    titles(ax, "不同階段的專案，用到哪些資源",
           "格內＝該階段中用過該資源的比例（人數/該階段人數）｜47 位曾參與者，各階段只有 6–17 人，僅供參考")
    fig.colorbar(im, ax=ax, shrink=0.6, label="群內比例")
    C.save_fig(fig, "05_資源×專案階段")
    plt.close(fig)

    # ---------------- 3b. 出資端與提案端的資源落差（兩個面板對照）----------------
    # 兩邊問的不是同一題，也不是同一套選項，所以不畫成同一組長條：
    #   左＝出資者答「最難找資源的是哪個階段」（27 人，只給早期／落地／維運三個選項）
    #   右＝提案端答「這個專案用過哪些資源」中勾「主要靠我自己想辦法」的比例
    #       （依填答者最近參與的專案所在階段分組，另有「停擺」一組，出資者那題沒有）
    # 用同一個 y 軸順序（早期→落地→維運）並把「落地」標成強調色，讓落差看得出來。
    FUND_TO_STAGE = {
        "還在很早期、只有想法的": "早期（探索或開發中）",
        "已經做出原型、要往落地走的": "落地",
        "已經上線、要長期維運的": "維運",
    }
    fd = pd.read_csv(T / "03_出資者_資源沙漠階段.csv")
    unknown = set(fd["選項"]) - set(FUND_TO_STAGE)
    assert not unknown, f"出資者階段題出現未預期選項：{sorted(unknown)}"
    fd["階段"] = fd["選項"].map(FUND_TO_STAGE)
    fd_n = int(fd["分母"].iloc[0])

    sf = rs[rs["選項"] == "主要靠我自己想辦法"].copy()

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.2))
    panels = [
        (axes[0], fd.set_index("階段"), "比例", "票數", fd_n,
         # 問卷設計稿把這題標為複選，但實際作答裡沒有任何人複選（票數 14+10+3 剛好等於
         # 作答人數 27），所以圖上照實描述作答狀況，不宣稱表單的題型設定。
         f"出資者認為最難找資源的階段", f"曾出錢支持過專案的 {fd_n} 人，作答中每人都只選了一個"),
        (axes[1], sf.set_index("分群"), "群內比例", "分子", None,
         "提案端說「主要靠我自己想辦法」的比例",
         "依每個人最近參與的專案所在階段分組"),
    ]
    for ax, d, vcol, ncol, fixed_den, title, sub in panels:
        stages = [s for s in C.STAGE_COARSE_ORDER if s in d.index]
        y = np.arange(len(stages))[::-1]
        for yi, st in zip(y, stages):
            v = float(d.loc[st, vcol])
            n = int(d.loc[st, ncol])
            den = fixed_den if fixed_den else int(d.loc[st, "分母"])
            hot = st == "落地"
            ax.barh(yi, v, height=0.6, zorder=2,
                    color=C.PALETTE["accent"] if hot else C.PALETTE["neutral"])
            ax.text(v + 0.015, yi, f"{v:.0%}  ({n}/{den})",
                    va="center", fontsize=8.5, color="#52514e")
        ax.set_yticks(y, [s.replace("（探索或開發中）", "") for s in stages], fontsize=9.5)
        ax.set_xlim(0, 0.72)
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
        style_axes(ax, title=title, subtitle=sub)

    fig.text(0.5, -0.10,
             "出資者覺得最不缺資源的「落地」（11%），正是提案端最常說只能靠自己的一段（35%）。"
             "兩題問法不同：一邊問難易感受、一邊問實際用過哪些資源，用得少也可能只是還沒用到。",
             ha="center", fontsize=8.5, color="#52514e")
    C.save_fig(fig, "17_出資端與提案端的資源落差")
    plt.close(fig)

    # ---------------- 4. 年齡 × 持續動機：與全體的差距（雙向橫條）----------------
    # 原本畫成熱區，但同一個視覺通道塞了三種意思（顏色＝與全體相比、格內數字＝群內比例、
    # 白色＝人數太少不比），讀者分不出來；而且這題是複選，一欄的分子相加會超過該群人數，
    # 熱區的排版會誘導人去直欄相加。
    # 改成單一語意的雙向條：位置＝與全體的差距，右（暖色）＝高於全體、左（淡藍）＝低於全體，
    # 長度＝差幾個百分點。只用一個視覺通道表達一件事，方向與長度都不必再另外解釋。
    # 用百分點而不是倍數：各群只有 10／19／18 人，分子多在 5 人以下，
    # 倍數會被一兩個人左右（同 common.LIFT_MIN_NUMERATOR 的理由）。
    lf = pd.read_csv(T / "03_年齡×持續動機_lift.csv")
    lf = lf[lf["選項"].isin(C.MOTIVES)].copy()
    lf["高出百分點"] = (lf["群內比例"] - lf["全體比例"]) * 100
    ages = [a for a in C.AGE_COARSE_ORDER if a in set(lf["分群"])]
    dens = {g: int(lf.loc[lf["分群"] == g, "分母"].iloc[0]) for g in ages}
    BELOW = "#b9d0ed"                      # 淡藍＝低於全體，與暖色的「高於」分邊

    fig, axes = plt.subplots(
        len(ages), 1, figsize=(11.4, 0.5 * len(C.MOTIVES) * len(ages) + 1.1 * len(ages) + 2.4),
        gridspec_kw={"hspace": 0.42})
    axes = np.atleast_1d(axes)
    lim = max(lf["高出百分點"].abs()) * 1.75

    for ax, g in zip(axes, ages):
        d = lf[lf["分群"] == g].sort_values("高出百分點", ascending=False)
        y = np.arange(len(d))[::-1]
        ax.barh(y, d["高出百分點"], height=0.62, zorder=2,
                color=[C.PALETTE["accent"] if v > 0 else BELOW for v in d["高出百分點"]])
        for yi, (_, r) in zip(y, d.iterrows()):
            v = r["高出百分點"]
            lab = (f'{r["群內比例"]:.0%}（{int(r["分子"])}/{int(r["分母"])}）'
                   f'，{"高出" if v > 0 else "低了"} {abs(v):.0f} 個百分點')
            ax.text(v + (lim * 0.02 if v > 0 else -lim * 0.02), yi, lab,
                    va="center", ha="left" if v > 0 else "right",
                    fontsize=8.5, color="#52514e")
        ax.axvline(0, color="#0b0b0b", lw=1.0, zorder=3)
        ax.set_yticks(y, list(d["選項"]), fontsize=9)
        ax.set_ylim(-0.7, len(d) - 0.3)
        ax.set_xlim(-lim, lim)
        ax.set_xticks([])
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(length=0)
        n_up = int((d["高出百分點"] > 0).sum())
        ax.text(0, 1.0, f"{g}（{dens[g]} 人）　{n_up} 個高於全體、{len(d) - n_up} 個低於全體",
                transform=ax.transAxes, fontsize=10.5, fontweight="bold",
                color="#0b0b0b", va="bottom")

    fig.suptitle("不同世代，現在的動機不一樣", fontsize=13.5, fontweight="bold",
                 x=0.012, ha="left", y=1.0)
    fig.text(0.012, 0.962,
             "每一條＝該世代勾這個動機的比例，與全體 47 位曾參與者相差幾個百分點。"
             "往右（暖色）＝高於全體，往左（淡藍）＝低於全體。",
             ha="left", fontsize=8.5, color="#52514e", transform=fig.transFigure)
    fig.text(0.012, -0.01,
             "這題可複選，每人平均勾 2.3 個，所以同一個世代各條的人數相加會超過該世代的總人數。"
             "三個世代各只有 10／19／18 人，差異僅供參考。",
             ha="left", fontsize=8.5, color="#52514e", linespacing=1.6)
    C.save_fig(fig, "06_年齡×持續動機")
    plt.close(fig)

    # ---------------- 5. 動機流向（斜線圖）----------------
    fl = pd.read_csv(T / "04_動機_流向.csv").sort_values("初次_人數", ascending=False)
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    left_y = spread(fl["初次_人數"].tolist(), 1.5)
    right_y = spread(fl["持續_人數"].tolist(), 1.5)
    for (_, r), ly, ry in zip(fl.iterrows(), left_y, right_y):
        color = (C.SERIES[1] if r["淨變化"] > 0
                 else C.PALETTE["neutral"] if r["淨變化"] == 0 else C.SERIES[0])
        ax.plot([0, 1], [r["初次_人數"], r["持續_人數"]], color=color, lw=2, zorder=2)
        ax.scatter([0, 1], [r["初次_人數"], r["持續_人數"]], s=42, color=color,
                   edgecolor=C.PALETTE["surface"], linewidth=1.6, zorder=3)
        ax.text(-0.035, ly, f"{r['動機']}　{int(r['初次_人數'])}",
                ha="right", va="center", fontsize=8.5, color="#52514e")
        ax.text(1.035, ry,
                f"{int(r['持續_人數'])}　留存 {int(r['留存'])}／新增 {int(r['新增'])}",
                ha="left", va="center", fontsize=8.5, color="#52514e")
    ax.set_xlim(-0.62, 1.42)
    ax.set_ylim(3, 42)
    ax.set_xticks([0, 1], ["第一次投入的契機", "現在還留下來的原因"], fontsize=10)
    ax.set_yticks([])
    ax.grid(axis="y", color=C.PALETTE["grid"], lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=9)
    ax.spines["left"].set_visible(False)
    titles(ax, "動機從入門到現在，怎麼移動",
           "同一批 47 位曾參與者的配對比較，數字為人數（分母 47）｜橘＝淨增加、藍＝淨減少、灰＝持平\n"
           "總量看似穩定，但 19/47（40%）的人，動機組合其實換過")
    C.save_fig(fig, "07_動機流向")
    plt.close(fig)

    # ---------------- 6. 活動意願 ----------------
    ev = pd.read_csv(T / "03_全體_活動意願.csv")
    ev = ev[ev["票數"] >= 3]
    hbar(ev, "選項", "比例", "票數", int(ev["分母"].iloc[0]),
         "如果揪松團辦這些活動，大家最想報名哪一個",
         f"全體 N={int(ev['分母'].iloc[0])}，每人最多選 2 個｜受「最多選 2」限制，需求只會被低估",
         "08_活動意願", color=C.SERIES[1])

    # ---------------- 7. 三層 × 議題領域／工具 ----------------
    for src, fname, title, topn in [
        ("03_三層×議題領域.csv", "09_三層×議題領域", "想先看哪些議題領域的資料清單", 12),
        ("03_三層×跨領域工具.csv", "10_三層×跨領域工具", "想看哪些跨領域工具的介紹", 7),
    ]:
        t = pd.read_csv(T / src)
        order = (t.groupby("選項")["分子"].sum().sort_values(ascending=False).head(topn).index)
        t = t[t["選項"].isin(order)]
        piv = t.pivot(index="選項", columns="分群", values="群內比例").reindex(
            index=list(order)[::-1], columns=C.LAYER_ORDER)
        dens = {g: int(t.loc[t["分群"] == g, "分母"].iloc[0]) for g in C.LAYER_ORDER}
        fig, ax = plt.subplots(figsize=(9.5, 0.52 * len(piv) + 2.2))
        y = np.arange(len(piv))
        for k, layer in enumerate(C.LAYER_ORDER):
            ax.barh(y + (1 - k) * 0.26, piv[layer], height=0.24,
                    color=C.PALETTE["layers"][layer],
                    label=f"{C.LAYER_PLAIN[layer]}（{dens[layer]} 人）", zorder=2)
        for k, layer in enumerate(C.LAYER_ORDER):
            for yi, v in zip(y + (1 - k) * 0.26, piv[layer]):
                ax.text(v + 0.008, yi, f"{v:.0%}", va="center", fontsize=7.5, color="#52514e")
        ax.set_yticks(y, piv.index, fontsize=9)
        ax.set_xlim(0, piv.values.max() * 1.20)
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
        ax.legend(frameon=False, fontsize=8.5, loc="lower right")
        style_axes(ax, title=title,
                   subtitle="各群的勾選率（分母為該群有作答人數）｜還沒接觸的人只有 26 位，僅供參考")
        C.save_fig(fig, fname)
        plt.close(fig)

    # ---------------- 8. 生態系：管道與地區 ----------------
    ch = pd.read_csv(T / "03_全體_g0v消息管道.csv")
    ch = ch[ch["票數"] >= 3]
    hbar(ch, "選項", "比例", "票數", int(ch["分母"].iloc[0]),
         "大家從哪裡得知 g0v 的活動消息",
         f"全體 N={int(ch['分母'].iloc[0])}，複選｜「親友推薦」與「g0v 社群管道」並列第一（各 51 人），"
         "意味著觸及仍有一半依賴人際網絡",
         "11_g0v消息管道")

    rg = pd.read_csv(T / "03_全體_居住地.csv")
    hbar(rg, "選項", "比例", "票數", int(rg["分母"].iloc[0]),
         "填答者的居住地分布",
         f"全體 N={int(rg['分母'].iloc[0])}｜雙北合計逾六成，反映問卷經 g0v 管道發放的取樣偏誤",
         "12_居住地分布", color=C.PALETTE["neutral"])

    nj = pd.read_csv(T / "03_未參與原因.csv")
    hbar(nj, "選項", "比例", "票數", int(nj["分母"].iloc[0]),
         "從未接觸者說，是什麼擋住了他們",
         "分母＝26 位「從未接觸公民科技」者（全數作答），人數少僅供參考｜"
         "注意：被選為主要對象的「接觸未參與」54 人，問卷未問此題",
         "13_未參與原因", color=C.SERIES[2])

    # ---------------- 9. 角色與參與深度（§3 原本沒有任何圖）----------------
    roles = pd.read_csv(T / "03_全體_角色勾選.csv")
    roles = roles[roles["選項"].isin(C.ROLE_LADDER)].copy()
    roles["短名"] = roles["選項"].map(C.ROLE_SHORT)
    order = [C.ROLE_SHORT[r] for r in C.ROLE_LADDER]        # 由淺到深，不依票數排序
    roles = roles.set_index("短名").loc[order].reset_index()
    breadth = pd.read_csv(T / "03_角色廣度分布.csv")

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(13.5, 4.6),
                                   gridspec_kw={"width_ratios": [1.35, 1]})
    # 左：各角色勾選率，維持「由淺到深」的順序（不是由多到少），才看得出階梯形狀
    ypos = np.arange(len(roles))[::-1]
    axa.barh(ypos, roles["比例"], height=0.6, color=C.PALETTE["primary"], zorder=2)
    for y, v, n in zip(ypos, roles["比例"], roles["票數"]):
        axa.text(v + 0.012, y, f"{v:.0%}（{int(n)}/101）", va="center",
                 fontsize=8.5, color="#52514e")
    axa.set_yticks(ypos, roles["短名"])
    axa.set_xlim(0, 1.12)
    axa.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    axa.grid(axis="x", color=C.PALETTE["grid"], lw=0.8, zorder=0)
    axa.set_axisbelow(True)
    axa.tick_params(length=0, labelsize=9.5)
    axa.set_title("擔任過哪些角色（複選，由淺到深排列）", fontsize=11, loc="left", pad=8)

    # 右：角色廣度＝一個人勾了幾種角色
    axb.bar(breadth["勾選角色數"], breadth["人數"], width=0.62,
            color=C.PALETTE["accent"], zorder=2)
    for x, n, r in zip(breadth["勾選角色數"], breadth["人數"], breadth["比例"]):
        axb.text(x, n + 1, f"{int(n)}\n{r:.0%}", ha="center", fontsize=8.5, color="#52514e")
    axb.set_xticks(breadth["勾選角色數"])
    axb.set_ylim(0, breadth["人數"].max() * 1.25)
    axb.grid(axis="y", color=C.PALETTE["grid"], lw=0.8, zorder=0)
    axb.set_axisbelow(True)
    axb.tick_params(length=0, labelsize=9.5)
    axb.set_xlabel("一個人勾了幾種角色", fontsize=9, color="#52514e")
    axb.set_title("角色廣度分布", fontsize=11, loc="left", pad=8)

    fig.suptitle("角色分布：多數人只站在一個位置", fontsize=13, x=0.045, ha="left", y=1.06)
    fig.text(0.045, 1.0,
             "分母＝101 位曾接觸者（其中 99 人有有效角色）｜"
             "近半數（46 人）只勾了一種角色，勾滿五種的有 10 人",
             ha="left", fontsize=8.5, color="#52514e")
    C.save_fig(fig, "14_角色分布與廣度")
    plt.close(fig)

    # 角色重疊矩陣：直接呈現「不是巢狀階梯」這個事實
    ov = pd.read_csv(T / "03_角色重疊矩陣.csv")
    mat = ov[[f"也勾{s}" for s in order]].values
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    ax.imshow(mat, cmap=SEQ, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(order)), order, fontsize=9.5)
    ax.set_yticks(range(len(order)),
                  [f"{s}\n(n={int(n)})" for s, n in zip(ov["勾了（列）"], ov["該角色人數"])],
                  fontsize=9)
    for i in range(len(order)):
        for j in range(len(order)):
            v = mat[i, j]
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=9.5,
                    color="#ffffff" if v > 0.55 else "#0b0b0b")
    ax.set_xticks(np.arange(-.5, len(order), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(order), 1), minor=True)
    ax.grid(which="minor", color=C.PALETTE["surface"], linewidth=2)
    ax.tick_params(which="both", length=0)
    titles(ax, "角色之間不是巢狀階梯",
           "列＝勾了該角色的人，格內＝其中「也」勾了欄角色的比例\n"
           "若真是由淺到深的巢狀階梯，左下三角應該全部是 100%——實際上並不是"
           "（例如勾「發起者」的人只有 82% 也勾了使用者）")
    C.save_fig(fig, "15_角色重疊矩陣")
    plt.close(fig)

    # 參與深度分布（§3.1 原本只有表）
    idx_df = pd.read_csv(T / "01_衍生變項.csv", index_col=0, keep_default_na=False)
    depth_order = list(C.DEPTH_LABEL.values()) + ["以上都不太像我（不在此軸）"]
    dc = idx_df["參與深度"].value_counts()
    vals = [int(dc.get(d, 0)) for d in depth_order]
    labels = [d.replace("（不在此軸）", "") for d in depth_order]
    colors = [C.PALETTE["primary"]] * 5 + [C.PALETTE["neutral"]]
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    ypos = np.arange(len(labels))[::-1]
    ax.barh(ypos, vals, height=0.62, color=colors, zorder=2)
    for y, v in zip(ypos, vals):
        ax.text(v + 0.6, y, f"{v}（{v / 101:.0%}）", va="center", fontsize=9, color="#52514e")
    ax.set_yticks(ypos, labels)
    ax.set_xlim(0, max(vals) * 1.22)
    ax.grid(axis="x", color=C.PALETTE["grid"], lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelsize=9.5)
    titles(ax, "參與深度：四成的人只站在第一階",
           "分母＝101 位曾接觸者｜灰色那列是逃生選項，不在深度軸上、未給權重")
    C.save_fig(fig, "16_參與深度分布")
    plt.close(fig)

    print("\n完成。所有圖已輸出到 圖表v2/，每張圖對應的數據 CSV 在 分析結果/。")


if __name__ == "__main__":
    main()
