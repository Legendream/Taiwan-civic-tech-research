# -*- coding: utf-8 -*-
"""
01_indices.py — 建立衍生變項（指數）。

依計畫第三節的修正版定義：
  · 角色廣度 與 最深角色 是兩個獨立變項（廣度≠深度，不可混為一個「勾選數」）
  · 參與深度序位 1–5，「以上都不太像我」為獨立類別、不給權重
  · 困擾題主指標為 %≥3 / %≥4（實際問卷無「沒遇到」選項，平均值系統性低估）

輸出：分析結果/01_衍生變項.csv（人層級，後續腳本以 index 併回）
      分析結果/01_衍生變項摘要.csv

執行：python3 01_indices.py
"""

import numpy as np
import pandas as pd

import common as C


def build(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out[C.LAYER] = df[C.LAYER]

    # ---------- 角色：廣度 與 最深階 ----------
    ladder_pos = {r: i + 1 for i, r in enumerate(C.ROLE_LADDER)}

    def roles_of(v):
        return [o.strip() for o in str(v).split(C.MULTI_SELECT_SEP)
                if o.strip() and o.strip() in ladder_pos]

    roles = df[C.C_ROLES].apply(roles_of)
    out["角色廣度"] = roles.apply(lambda rs: len(rs) if rs else np.nan)
    out["最深角色階"] = roles.apply(lambda rs: max(ladder_pos[r] for r in rs) if rs else np.nan)
    out["最深角色"] = out["最深角色階"].apply(
        lambda p: C.ROLE_SHORT[C.ROLE_LADDER[int(p) - 1]] if pd.notna(p) else "")
    for r in C.ROLE_LADDER:
        out[f"角色_{C.ROLE_SHORT[r]}"] = roles.apply(lambda rs, r=r: int(r in rs))

    # ---------- 參與深度（Q4）----------
    depth_raw = df[C.C_DEPTH].str.strip()
    out["參與深度序位"] = depth_raw.map(C.DEPTH_ORDER)          # 逃生選項→NaN，不給權重
    out["參與深度"] = out["參與深度序位"].map(C.DEPTH_LABEL).fillna("")
    out.loc[depth_raw == C.DEPTH_ESCAPE, "參與深度"] = "以上都不太像我（不在此軸）"
    # 二分：方向決策者（共創／發起）vs 執行協力者（接收／通報／協力）
    def decision_position(d):
        """參與深度序位 → 決策位置。NaN（逃生選項）不在這條軸上，回傳空字串。"""
        if pd.isna(d):
            return ""
        return "方向決策者" if d >= 4 else "執行協力者"

    out["決策位置"] = out["參與深度序位"].apply(decision_position)

    # ---------- 投入強度、活躍度、階段 ----------
    out["投入強度序位"] = df[C.C_HOURS].str.strip().map(C.HOURS_ORDER)
    out["投入時數"] = df[C.C_HOURS].str.strip()
    out["活躍度序位"] = df[C.C_LAST_CONTACT].str.strip().map(C.RECENCY_ORDER)
    out["專案階段"] = df[C.C_STAGE].str.strip()
    out["專案階段_合併"] = out["專案階段"].map(C.STAGE_COARSE).fillna("")

    # ---------- 困擾指標 ----------
    tcols = [c for c in df.columns if c.startswith(C.TROUBLE_PREFIX)]
    scores = df[tcols].apply(lambda s: s.str.strip().map(C.TROUBLE_SCALE))
    out["困擾_平均"] = scores.mean(axis=1)                      # 次要指標，必附註低估
    out["困擾_最高"] = scores.max(axis=1)
    out["困擾_達3項數"] = (scores >= 3).sum(axis=1).where(scores.notna().any(axis=1))
    out["困擾_達4項數"] = (scores >= 4).sum(axis=1).where(scores.notna().any(axis=1))

    # ---------- 其他分群變項 ----------
    out["年齡"] = df[C.C_AGE].str.strip()
    out["性別"] = df[C.C_GENDER].str.strip()
    out["身分"] = df[C.C_IDENTITY].str.strip()
    out["曾出資"] = df[C.C_FUNDED].str.strip()
    out["同時進行專案數"] = df[C.C_N_PROJECTS].str.strip()
    return out


def summarise(out: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(var, value, n, denom, note=""):
        rows.append({"變項": var, "類別": value, "人數": n, "分母": denom,
                     "比例": n / denom if denom else np.nan,
                     "信賴度": C.subgroup_confidence(n), "備註": note})

    done = out[out[C.LAYER] == C.L_DONE]
    contacted = out[out[C.LAYER] != C.L_NEVER]

    for v, n in out["角色廣度"].value_counts().sort_index().items():
        add("角色廣度（勾選數）", f"{int(v)} 個角色", int(n), len(contacted))
    for v, n in out.loc[out["最深角色"] != "", "最深角色"].value_counts().items():
        add("最深角色", v, int(n), len(contacted))
    for lab in C.DEPTH_LABEL.values():
        n = int((out["參與深度"] == lab).sum())
        add("參與深度", lab, n, len(contacted))
    n_escape = int((out["參與深度"] == "以上都不太像我（不在此軸）").sum())
    add("參與深度", "以上都不太像我", n_escape, len(contacted), "獨立類別，未給權重")
    for v, n in out.loc[out["決策位置"] != "", "決策位置"].value_counts().items():
        add("決策位置", v, int(n), int((out["決策位置"] != "").sum()))
    for v, n in done["投入時數"].value_counts().items():
        add("投入強度（過去30天）", v, int(n), len(done))
    for v in C.STAGE_COARSE_ORDER:
        n = int((done["專案階段_合併"] == v).sum())
        add("專案階段（合併）", v, n, len(done))
    for v, n in out["年齡"].value_counts().items():
        add("年齡", v, int(n), len(out))
    return pd.DataFrame(rows)


def main():
    df = C.load_clean()
    out = build(df)
    out.to_csv(C.TABLE_DIR / "01_衍生變項.csv", index=True, encoding="utf-8-sig")
    print(f"衍生變項：{len(out)} 列 × {len(out.columns)} 欄 → 01_衍生變項.csv")

    # ---- 自我檢查 ----
    contacted = out[out[C.LAYER] != C.L_NEVER]
    # 101 位曾接觸者中，2 人的角色題「只」填了自由填答（第 81、123 列，皆為接觸未參與層），
    # 無可對應的角色階，故角色廣度有效者為 99 人。
    assert out["角色廣度"].notna().sum() == 99, \
        f"角色廣度應有 99 人，實得 {out['角色廣度'].notna().sum()}"
    assert (out["參與深度序位"].notna().sum() + (out["參與深度"] == "以上都不太像我（不在此軸）").sum()) == 101, \
        "參與深度＋逃生選項應等於 101 位曾接觸者"
    assert out.loc[out[C.LAYER] == C.L_DONE, "困擾_平均"].notna().sum() == 47, "困擾指標應涵蓋 47 位曾參與者"
    assert out.loc[out[C.LAYER] != C.L_DONE, "困擾_平均"].notna().sum() == 0, "非曾參與者不應有困擾分數"
    print("  ✓ 衍生變項檢查通過")

    summ = summarise(out)
    C.save_table(summ, "01_衍生變項摘要")

    pd.set_option("display.width", 160, "display.max_rows", 80)
    print()
    print(summ.assign(比例=lambda d: (d["比例"] * 100).round(1).astype(str) + "%").to_string(index=False))
    print(f"\n※ 困擾指標註記：{C.TROUBLE_CAVEAT}")


if __name__ == "__main__":
    main()
