# -*- coding: utf-8 -*-
"""
11_activity_by_layer.py — 三層對活動的偏好差異（圖 7-3）。

補第 7 章「入門型與深度型的活動，服務的是不同的人」的圖：同一批活動意願數字
（03_三層×活動意願.csv），依三層分組橫向比較，取代只用文字描述的排序落差。

輸出：圖表v2/11_三層×活動意願.png

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

    # 標籤照問卷 Q17a 逐字選項（含冒號後的說明），不縮寫成活動短名——
    # 短名離開問卷脈絡後看不出在講哪個活動，讀者需要冒號後的說明才認得出來。
    # 只在冒號處插入換行方便橫式長條圖排版，文字本身不刪減。

    lay = {layer: f"{C.LAYER_PLAIN[layer]}（{n} 人）"
           for layer, n in C.LAYER_EXPECTED_N.items()}
    d = d[d["分群"].isin(lay)]

    order = [
        "公私協力怎麼談：一起討論公部門和民間合作的方法，以及常卡在哪",
        "公民科技實戰心法：從真實案例復盤，學前人怎麼把專案做起來",
        "公民科技資料庫入門：學會用網站和 AI 問答，快速查專案、看懂專案怎麼組成",
        "用 AI 幫你提案：從零開始，動手把點子變成專案構想和藍圖",
    ]
    labels = [t.replace("：", "：\n", 1) for t in order]
    groups = C.LAYER_ORDER
    # 三層一律用 PALETTE["layers"]（綠／橘／藍），與 01、13、14、15 同一套。
    # 原本這裡寫死一組橘色階，是全部圖表裡唯一沒跟到共用配色的地方。
    colors = [C.PALETTE["layers"][g] for g in groups]

    fig, ax = plt.subplots(figsize=(13, 6.8))
    y = np.arange(len(order))
    h = 0.26
    for k, g in enumerate(groups):
        sub = d[d["分群"] == g].set_index("選項")
        missing = set(order) - set(sub.index)
        assert not missing, f"{g} 缺少主題：{missing}"
        vals = [sub.loc[t, "群內比例"] * 100 for t in order]
        nums = [f"{int(sub.loc[t,'分子'])}/{int(sub.loc[t,'分母'])}" for t in order]
        # (k - 1)：讓長條由上到下是綠、橘、藍，與圖例同序，也與 14、15 一致。
        bars = ax.barh(y + (k - 1) * h, vals, height=h, color=colors[k], label=lay[g])
        for b, v, n in zip(bars, vals, nums):
            ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.0f}%（{n}）",
                    va="center", fontsize=8.5, color="#444")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
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
    C.save_fig(fig, "11_三層×活動意願")
    plt.close(fig)
    print("已產出 圖表v2/11_三層×活動意願.png")


if __name__ == "__main__":
    main()
