# -*- coding: utf-8 -*-
"""
05_figures.py — 所有圖表輸出。

依 dataviz skill 的程序：先選圖形（依資料要做的事），再依職能指派顏色，
顏色已用 validate_palette.js 驗證（見 common.PALETTE 註解）。

圖形選擇：
  · 量值排序（困擾、資源、專長、管道、地區、角色）→ 橫條，單一數列不放圖例，直接標數值
  · 極性矩陣（年齡×動機 lift，中點 1.0）→ 分歧配色，兩色相＋中性灰中點
  · 二維落點（狩野 SI×DSI）→ 散佈圖＋四象限
  · 分群比較（三層×需求）→ 分組橫條，固定色序＋圖例
  · 單選互斥分層（127 人分三層）→ 甜甜圈圖，色隨身分固定

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
    C.save_fig(fig, "05_困擾_五級分布")
    plt.close(fig)

    # ---------------- 2a. 狩野落點圖（全體，單張）----------------
    for src, fname, title, sub in [
        ("02_狩野_全體.csv", "12_狩野落點_全體", "五個文章主題的狩野落點（全體）",
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
        ax.set_title(f"{C.LAYER_PLAIN[layer]}（{n} 人）", fontsize=11, pad=8)
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
    C.save_fig(fig, "13_狩野落點_三層")
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
             "三個世代各有 10／19／18 人。",
             ha="left", fontsize=8.5, color="#52514e", linespacing=1.6)
    C.save_fig(fig, "06_年齡×持續動機")
    plt.close(fig)

    # ---------------- 7. 三層 × 議題領域／工具 ----------------
    for src, fname, title, topn in [
        ("03_三層×議題領域.csv", "14_三層×議題領域", "想先看哪些議題領域的資料清單", 12),
        ("03_三層×跨領域工具.csv", "15_三層×跨領域工具", "想看哪些跨領域工具的介紹", 7),
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
                   subtitle="各群的勾選率（分母為該群有作答人數）｜還沒接觸的人有 26 位")
        C.save_fig(fig, fname)
        plt.close(fig)

    # ---------------- 8. 生態系：管道與地區 ----------------
    ch = pd.read_csv(T / "03_全體_g0v消息管道.csv")
    ch = ch[ch["票數"] >= 3]
    hbar(ch, "選項", "比例", "票數", int(ch["分母"].iloc[0]),
         "大家從哪裡得知 g0v 的活動消息",
         f"全體 N={int(ch['分母'].iloc[0])}，複選｜「親友推薦」與「g0v 社群管道」並列第一（各 51 人），"
         "意味著觸及仍有一半依賴人際網絡",
         "09_g0v消息管道")

    rg = pd.read_csv(T / "03_全體_居住地.csv")
    hbar(rg, "選項", "比例", "票數", int(rg["分母"].iloc[0]),
         "填答者的居住地分布",
         f"全體 N={int(rg['分母'].iloc[0])}｜雙北合計逾六成，反映問卷經 g0v 管道發放的取樣偏誤",
         "02_居住地分布", color=C.PALETTE["neutral"])

    nj = pd.read_csv(T / "03_未參與原因.csv")
    hbar(nj, "選項", "比例", "票數", int(nj["分母"].iloc[0]),
         "從未接觸者說，是什麼擋住了他們",
         "分母＝26 位「從未接觸公民科技」者（全數作答）｜"
         "注意：被選為主要對象的「接觸未參與」54 人，問卷未問此題",
         "10_未參與原因", color=C.SERIES[2])

    # ---------------- 9. 角色分布（§3 原本沒有任何圖）----------------
    roles = pd.read_csv(T / "03_全體_角色勾選.csv")
    roles = roles[roles["選項"].isin(C.ROLE_LADDER)].copy()
    roles["短名"] = roles["選項"].map(C.ROLE_SHORT)
    order = [C.ROLE_SHORT[r] for r in C.ROLE_LADDER]        # 由淺到深，不依票數排序
    roles = roles.set_index("短名").loc[order].reset_index()

    # 標籤用問卷 Q3 逐字選項，不用短名——短名離開問卷脈絡後看不出在講哪個角色
    roles_full = roles.copy()
    roles_full["問卷原始選項"] = roles_full["選項"].map(C.ROLE_ORIGINAL)
    hbar(roles_full, "問卷原始選項", "比例", "票數", 101,
         "擔任過哪些角色（複選，選項照問卷 Q3 逐字）",
         "分母＝101 位曾接觸者｜可複選，加總會超過 100%",
         "03_角色分布_問卷原始選項", figsize=(10.5, 3.6))

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
    C.save_fig(fig, "04_參與深度分布")
    plt.close(fig)

    # ---------------- 19. 入坑分層：127 人分成三層（單選、互斥，適合圓餅圖） ----------------
    layer_counts = idx_df["入坑分層"].value_counts()
    layer_vals = [int(layer_counts.get(l, 0)) for l in C.LAYER_ORDER]
    layer_colors = [C.PALETTE["layers"][l] for l in C.LAYER_ORDER]
    total = sum(layer_vals)

    pd.DataFrame({
        "分層": C.LAYER_ORDER,
        "人數": layer_vals,
        "分母": total,
        "比例": [v / total for v in layer_vals],
    }).to_csv(T / "01_入坑分層分布.csv", index=False, encoding="utf-8-sig")

    layer_labels_wrapped = [C.LAYER_PLAIN[l].replace("，", "，\n") for l in C.LAYER_ORDER]
    fig, ax = plt.subplots(figsize=(7.4, 6.4))
    wedges, _ = ax.pie(
        layer_vals, colors=layer_colors, startangle=90, counterclock=False,
        wedgeprops={"width": 0.55, "edgecolor": C.PALETTE["surface"], "linewidth": 2})
    for w, label, v in zip(wedges, layer_labels_wrapped, layer_vals):
        ang = np.deg2rad((w.theta2 + w.theta1) / 2)
        ax.text(np.cos(ang) * 0.76, np.sin(ang) * 0.76, f"{label}\n{v} 人（{v / total:.0%}）",
                ha="center", va="center", fontsize=9, color="#ffffff", linespacing=1.4)
    ax.set_aspect("equal")
    titles(ax, "127 位填答者，分成三層",
           f"分母＝全體 {total} 人｜色隨身分固定：聽過或看過＝綠、接觸未參與＝橘、做過專案＝藍")
    C.save_fig(fig, "01_入坑分層分布")
    plt.close(fig)

    # ---------------- 21. 用過哪些資源（複選，Q「這個專案曾使用過哪些資源？」）----------------
    resources = pd.read_csv(T / "03_全體_資源.csv")
    hbar(resources, "選項", "比例", "票數", 47,
         "曾參與過專案的人，用過哪些資源",
         "分母＝47 位曾參與者｜可複選，加總會超過 100%",
         "07_全體_資源")

    # ---------------- 22. 貢獻過哪些專長（複選）----------------
    skills = pd.read_csv(T / "03_全體_專長.csv")
    hbar(skills, "選項", "比例", "票數", 47,
         "曾參與過專案的人，貢獻過哪些專長",
         "分母＝47 位曾參與者｜可複選，加總會超過 100%｜常見一人多工",
         "08_全體_專長")

    print("\n完成。所有圖已輸出到 圖表v2/，每張圖對應的數據 CSV 在 分析結果/。")


if __name__ == "__main__":
    main()
