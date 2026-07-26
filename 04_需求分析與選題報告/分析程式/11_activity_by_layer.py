import sys; sys.path.insert(0, "分析程式")
import common as C
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

C.setup_matplotlib() if hasattr(C, "setup_matplotlib") else None
plt.rcParams["font.sans-serif"] = [C.CJK_FONT, "PingFang HK", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

d = pd.read_csv("分析結果/03_三層×活動意願.csv")
short = {"公私協力怎麼談": "公私協力怎麼談", "公民科技實戰心法": "公民科技實戰心法",
         "公民科技資料庫入門": "資料庫入門", "用 AI 幫你提案": "用 AI 幫你提案"}
d["主題"] = d["選項"].str.split("：").str[0].replace(short)
lay = {"從未接觸": "聽過或看過，還沒參與（26 人）",
       "接觸未參與": "接觸過，還沒做過專案（54 人）",
       "曾參與": "做過專案（47 人）"}
d = d[d["分群"].isin(lay)]
order = ["公私協力怎麼談", "公民科技實戰心法", "資料庫入門", "用 AI 幫你提案"]
groups = ["從未接觸", "接觸未參與", "曾參與"]
colors = ["#F2A65A", "#E8743B", "#B5451B"]

fig, ax = plt.subplots(figsize=(11, 5.2))
y = np.arange(len(order)); h = 0.26
for k, g in enumerate(groups):
    sub = d[d["分群"] == g].set_index("主題")
    vals = [sub.loc[t, "群內比例"] * 100 if t in sub.index else 0 for t in order]
    nums = [f"{int(sub.loc[t,'分子'])}/{int(sub.loc[t,'分母'])}" if t in sub.index else "" for t in order]
    bars = ax.barh(y + (1 - k) * h, vals, height=h, color=colors[k], label=lay[g])
    for b, v, n in zip(bars, vals, nums):
        ax.text(v + 1, b.get_y() + b.get_height()/2, f"{v:.0f}%（{n}）",
                va="center", fontsize=8.5, color="#444")

ax.set_yticks(y); ax.set_yticklabels(order, fontsize=11)
ax.invert_yaxis(); ax.set_xlim(0, 88)
ax.set_xlabel("該群裡把這個活動列入的比例", fontsize=10)
ax.set_title("同一場活動，不同的人想要的不一樣\n", fontsize=15, fontweight="bold", loc="left", pad=26)
fig.text(0.125, 0.935, "每個人最多挑 2 個活動。「資料庫入門」在還沒實際參與的人裡最受歡迎，"
                       "「公私協力怎麼談」則是做過專案的人最想要的。",
         fontsize=9.5, color="#666", ha="left", va="bottom")
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=100, decimals=0))
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.xaxis.grid(True, color="#DDD", lw=0.6); ax.set_axisbelow(True)
fig.savefig("圖表v2/18_三層×活動意願.png", bbox_inches="tight")
print("已產出 圖表v2/18_三層×活動意願.png")
