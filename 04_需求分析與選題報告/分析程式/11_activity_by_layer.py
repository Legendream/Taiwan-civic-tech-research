# -*- coding: utf-8 -*-
"""
11_activity_by_layer.py — 三層對活動的偏好差異（圖 7-3）。

補第 7 章「入門型與深度型的活動，服務的是不同的人」的圖：同一批活動意願數字
（03_三層×活動意願.csv），依三層分組橫向比較，取代只用文字描述的排序落差。

輸出：圖表v2/18_三層×活動意願.png

執行：python3 11_activity_by_layer.py
"""

import numpy as np
import pandas as pd

import common as C

plt = C.setup_matplotlib()
import matplotlib.ticker as mticker

T = C.TABLE_DIR


def main():
    d = pd.read_csv(T / "03_三層×活動意願.csv")
    short = {"公民科技資料庫入門": "資料庫入門"}
    d["主題"] = d["選項"].str.split("：").str[0].replace(short)

    # 不用 C.LAYER_PLAIN：那份白話標籤把 L_NEVER 寫成「還沒接觸的人」，
    # 但這一層實際是「聽過或看過、只是還沒真正參與」，兩者不同義
    # （這份報告這一輪已把正文與其他新圖的用字改到跟問卷題目一致）。
    lay = {
        C.L_NEVER: "聽過或看過，還沒參與（26 人）",
        C.L_AWARE: "接觸過，還沒做過專案（54 人）",
        C.L_DONE: "做過專案（47 人）",
    }
    d = d[d["分群"].isin(lay)]

    order = ["公私協力怎麼談", "公民科技實戰心法", "資料庫入門", "用 AI 幫你提案"]
    groups = C.LAYER_ORDER
    colors = ["#F2A65A", "#E8743B", "#B5451B"]

    fig, ax = plt.subplots(figsize=(11, 5.2))
    y = np.arange(len(order))
    h = 0.26
    for k, g in enumerate(groups):
        sub = d[d["分群"] == g].set_index("主題")
        missing = set(order) - set(sub.index)
        assert not missing, f"{g} 缺少主題：{missing}"
        vals = [sub.loc[t, "群內比例"] * 100 for t in order]
        nums = [f"{int(sub.loc[t,'分子'])}/{int(sub.loc[t,'分母'])}" for t in order]
        bars = ax.barh(y + (1 - k) * h, vals, height=h, color=colors[k], label=lay[g])
        for b, v, n in zip(bars, vals, nums):
            ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.0f}%（{n}）",
                    va="center", fontsize=8.5, color="#444")

    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(0, 88)
    ax.set_xlabel("該群裡把這個活動列入的比例", fontsize=10)
    ax.set_title("同一場活動，不同的人想要的不一樣\n", fontsize=15, fontweight="bold",
                 loc="left", pad=26)
    fig.text(0.125, 0.935,
             "每個人最多挑 2 個活動。「資料庫入門」在還沒實際參與的人裡最受歡迎，"
             "「公私協力怎麼談」則是做過專案的人最想要的。",
             fontsize=9.5, color="#666", ha="left", va="bottom")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.xaxis.grid(True, color="#DDD", lw=0.6)
    ax.set_axisbelow(True)
    C.save_fig(fig, "18_三層×活動意願")
    plt.close(fig)
    print("已產出 圖表v2/18_三層×活動意願.png")


if __name__ == "__main__":
    main()
