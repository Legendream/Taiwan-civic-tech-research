# -*- coding: utf-8 -*-
"""
共用設定：路徑、欄位常數、選項歸併表、分層定義、序位對照、繪圖樣式。

所有分析腳本都從這裡取設定，避免同一組定義散落在多個檔案裡各自漂移。

⚠️ 個資原則：原始 CSV 含 email 與電話，任何分析腳本都不得直接讀它。
   只有 00_clean.py 可以讀原始檔，其餘一律讀 CLEAN_CSV。
"""

from pathlib import Path

# ---------------------------------------------------------------- 路徑

PROJ = Path(__file__).resolve().parents[2]           # g0v civic tech guide/
RAW_DIR = PROJ / "03_問卷回收資料"
OUT_DIR = PROJ / "04_問卷分析報告"

RAW_CSV = RAW_DIR / "臺灣公民科技參與者的需求調查 _至 2026_7_24 的填答 - 表單回覆 1.csv"
OLD_CSV = RAW_DIR / "去識別化給 AI 分析＿用科技促進公眾利益，最難的是什麼？臺灣公民科技參與者的需求調查 - 表單回覆 1.csv"
CLEAN_CSV = RAW_DIR / "去識別化_至20260724.csv"      # 00_clean.py 產出，之後只讀這份

TABLE_DIR = OUT_DIR / "分析結果"                      # 每張圖對應的數據 CSV
FIG_DIR = OUT_DIR / "圖表v2"                          # PNG

for _d in (TABLE_DIR, FIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 欄位常數
# 注意：原始表頭有數欄帶前導空白（Google 表單匯出所致），載入時一律 strip，
# 這裡的常數用 strip 後的名稱。

C_TS = "時間戳記"
C_LAST_CONTACT = "你最近一次接觸公民科技專案，大概是什麼時候？"
C_ROLES = "你曾經在公民科技專案裡，擔任過哪些角色？"
C_DEPTH = "下面哪一句，最貼近你在公民科技圈子做的事？"
C_EVER = "你曾經參與過公民科技專案嗎？"

C_PROJ_DESC = "你最近參與的那個公民科技專案，是為了解決什麼問題？"
C_STAGE = "這個專案目前進行到哪個階段？"
C_SKILLS = "在這個專案裡，你主要的專長、或協助的任務是？"
C_RESOURCES = "這個專案從開始到現在，曾使用過哪些資源？"
C_HOURS = "過去 30 天，你大約花了多少時間在這個專案？"

C_ACTION_TEXT = "面對這些困難，你有採取什麼行動去解決嗎？"
C_MOTIVE_FIRST = "你第一次投入公民科技專案時的契機是？"
C_MOTIVE_NOW = "那現在讓你留下來繼續做的，又是什麼？"
C_N_PROJECTS = "你現在手上同時在進行幾個公民科技專案？"
C_NOT_JOIN_WHY = "你聽過或看過公民科技，但還沒真正參與，最主要的原因是什麼？（請最多選 3 個原因）"

C_DOMAINS = "我們會整理「某個議題領域有哪些現成資料可以用」的清單。你最想先看到哪些領域？請選最多 5 個領域"
C_TOOLS = "下面這些「跨領域都用得到的工具」，你最想看哪些介紹？請選最多 3 個工具"
C_EVENTS = "如果 g0v 揪松團舉辦下面這些活動，你最想報名的是哪兩個？"

C_FUNDED = "你曾經為公民科技專案提供經費方面的支持嗎？"
C_FUND_DESC = "你最近一次出錢，或是調度經費支持的專案，該專案是在做什麼？"
C_FUND_CRITERIA = "你在決定要不要支持一個專案時，最看重哪些？請最多選 3 個因素"
C_FUND_HARDEST = "以你的觀察，最難找到資源的，是處在哪個階段的專案？"

C_G0V_LAST = "你最近一次參加 g0v.tw 的活動，是什麼時候？"
C_G0V_EVENTS = "承上，你參加過哪些 g0v 活動？"
C_G0V_CHANNEL = "你現在主要透過哪些管道，得知 g0v 的活動消息？"
C_INFO_CHANNEL = "整體來說，你主要透過哪些管道吸收公民科技的資訊？"

C_AGE = "你的年齡？"
C_IDENTITY = "你目前主要的身分或工作場域是？"
C_ORG_TEXT = "可以多分享一點你所屬的組織或團體嗎？"
C_GENDER = "你的性別？"
C_REGION = "你目前居住在哪個區域？"
C_REGION_LINK = "除了居住地，你還跟哪些地區有比較深的連結？"

# 個資欄：00_clean.py 直接整欄刪除，絕不進入去識別化檔
PII_COLS = [
    "如果你願意「參加抽獎」及「接收本計畫的更新資訊」，請留下 email",
    "你的聯絡電話 (僅用於獲獎者 email 之外的備用聯繫管道)",
]

MULTI_SELECT_SEP = ", "   # Google 表單複選題的分隔字串

# ---------------------------------------------------------------- 分層定義

LAYER = "入坑分層"
L_NEVER = "從未接觸"        # 預期 N=26，L1
L_AWARE = "接觸未參與"      # 預期 N=54，L2
L_DONE = "曾參與"           # 預期 N=47，L2
LAYER_ORDER = [L_NEVER, L_AWARE, L_DONE]
LAYER_EXPECTED_N = {L_NEVER: 26, L_AWARE: 54, L_DONE: 47}

# 圖表專用的白話標籤。對外報告不讓「三層」這個分析術語進正文，
# 但圖上原本會直接印出 L_NEVER／L_AWARE／L_DONE，等於把術語帶回來。
# ⚠️ 只用於圖表標籤，**不可**拿去改 CSV 的分群欄——那些值是各腳本互相比對的鍵，
#    改了會讓 06_number_index.py 與 10_role_crosstab.py 的守門檢查失效。
LAYER_PLAIN = {
    L_NEVER: "聽過或看過，還沒接觸",
    L_AWARE: "接觸過，還沒做過專案",
    L_DONE: "做過專案",
}

NEVER_CONTACT_VALUE = "我從未接觸過公民科技，只有聽過或看過"

# 最近一次接觸時間：活躍度序位（「從未接觸」不在此軸上，給 None）
RECENCY_ORDER = {
    "最近一個月內": 5,
    "1 到 6 個月前": 4,
    "7 到 12 個月前": 3,
    "超過 1 年、3 年內": 2,
    "超過 3 年以前": 1,
}

# 信賴度門檻（沿用 satisfaction-survey-analyzer 的三層紀律）
def confidence(n: int) -> str:
    """N → 信賴度標籤。子群 N<30 一律 L1「僅供參考」。"""
    if n >= 200:
        return "L3"
    if n >= 80:
        return "L2"
    if n >= 30:
        return "L1"
    return "L1（樣本過小，僅供參考）"


def subgroup_confidence(n: int) -> str:
    """分群比較用：L2 需 N≥30、L3 需 N≥50。"""
    if n >= 50:
        return "L3"
    if n >= 30:
        return "L2"
    return "L1（僅供參考）"


# ---------------------------------------------------------------- 序位對照

# Q4 參與深度：主動權由低到高。
# ⚠️「以上都不太像我」不是尺度上的一點（多為純出資者等不在這條軸上的人），
#    給 None、排成獨立類別，絕不賦予權重——否則整條軸失真。
DEPTH_ORDER = {
    "接收資訊：關心某些議題，會去看相關資料或成果，比較少自己動手做": 1,
    "主動通報：我會按照專案方的需求，協助提供資訊。例如回報路況、上傳環境污染的資料": 2,
    "協力參與：我會加入別人發起的專案，一起出力、把事情做出來。我比較少參與專案方向的決策": 3,
    "共創解法：我會跟大家一起把問題定義清楚、一起設計怎麼解決。我的行動，會影響專案進行的方向": 4,
    "發起專案：我常常是起頭的那個人，自己發現問題、自己找夥伴、啟動專案": 5,
}
DEPTH_ESCAPE = "以上都不太像我，我以別的形式接觸公民科技專案"
DEPTH_LABEL = {1: "接收資訊", 2: "主動通報", 3: "協力參與", 4: "共創解法", 5: "發起專案"}

# 角色階梯：由淺到深。用於「最深角色」；同時另計「角色廣度」＝勾選數。
# ⚠️ 勾選數雖由淺到深遞減（90 / 48 / 33 / 28 / 17），但**這不是巢狀結構**：
#    勾「落地推廣」者有 7 人沒勾「使用者」、勾「發起」者有 8 人沒勾「落地推廣」。
#    只有「出資者 ⊆ 使用者」完全成立。故「最深角色」＝此人勾過的最深一階，
#    不可解讀成他同時具備所有較淺階的經驗。重疊結構見 03_角色重疊矩陣.csv。
ROLE_LADDER = [
    "使用過某個公民科技工具、服務，或參與討論的人",
    "協助落地應用，或推廣給更多使用者的人",
    "參與籌備、開發、設計或維護的人",
    "發起專案的人",
    "出錢或調度資源的人",
]
ROLE_SHORT = {
    "使用過某個公民科技工具、服務，或參與討論的人": "使用者",
    "協助落地應用，或推廣給更多使用者的人": "落地推廣",
    "參與籌備、開發、設計或維護的人": "開發維護",
    "發起專案的人": "發起者",
    "出錢或調度資源的人": "出資者",
}
# Q3 問卷題本的逐字選項（問卷設計v.6.md:52-56）。上面 ROLE_LADDER 的字句是報告改寫過的版本，
# 這份留給需要對照「跟問卷一模一樣」措辭的場合用。
ROLE_ORIGINAL = {
    "使用過某個公民科技工具、服務，或參與討論的人": "主要是「使用者」：用過某個工具或服務，或在找有沒有工具能幫上忙",
    "協助落地應用，或推廣給更多使用者的人": "幫忙設計、幫忙落地或推廣，但不主導開發、也沒出錢的人",
    "參與籌備、開發、設計或維護的人": "實際動手做、或負責後續維護的人",
    "發起專案的人": "發想點子、定義問題、發起專案的人",
    "出錢或調度資源的人": "出錢或調度資源的人",
}
# 複選題的「其他」自由填答：畫圖與製表時一律收斂成「其他（自由填答）」。
# 受訪者原句可能很長、也可能透露個人狀態（例如自述性格），不適合整句放上圖表。
# 原句保留在去識別化 CSV 供質性分析引用（引用時再個別去識別化）。
FREETEXT_BUCKET = "其他（自由填答）"


def bucket_freetext(options, valid):
    """把不在 valid 清單中的自由填答收斂成 FREETEXT_BUCKET。"""
    return [o if o in valid else FREETEXT_BUCKET for o in options]


def bucket_and_dedupe(value, valid):
    """
    複選題單格字串 → 收斂自由填答並去重 → 重新組回字串。

    ⚠️ 去重是必要的，不是保險。bucket_freetext 把所有非正式選項映到同一個字串，
       若某人的自由填答本身含分隔字串「, 」（例如「自己的存款, 朋友借的場地」），
       explode_multi 會把它切成多個 token 而全部收斂成同一選項，該人就對同一選項
       貢獻多票——pct_table 的「單一選項票數＝人數」不變式因此失效，
       群內比例可能 >1（實測：票數 2／分母 1／比例 2.0）。
       dict.fromkeys 去重且保留原順序。
    """
    opts = [o.strip() for o in str(value).split(MULTI_SELECT_SEP) if o.strip()]
    return MULTI_SELECT_SEP.join(dict.fromkeys(bucket_freetext(opts, set(valid))))


# ---------------------------------------------------------------- lift 的分子下限
# 分子低於此值時，lift 由 1–4 個人決定，只是雜訊——而且放大方向永遠是
# 「讓小群看起來特別」，一律留空並在「lift留空原因」欄說明。
# ⚠️ 這條政策必須套用到**每一個**輸出 lift 的地方。曾經只實作一半
#    （只加在 10_role_crosstab.py 的 multi_by_masks，trouble_by_group 漏掉），
#    結果 21/65 列違反了同一份檔案自己寫的規則。放在共用檔就是為了不再各寫一份。
LIFT_MIN_NUMERATOR = 5


def lift_blank_reason(n: int) -> str:
    return f"勾選人數少於 {LIFT_MIN_NUMERATOR} 人，倍數會被一兩個人左右" if n < LIFT_MIN_NUMERATOR else ""


def lift_or_blank(group_p, base_p, numerator):
    """算 lift；分子不足或基準為 0 時回傳 None。"""
    if not base_p or numerator < LIFT_MIN_NUMERATOR:
        return None
    return round(group_p / base_p, 2)


# 角色題混進的自由填答（非角色），歸為「其他」不計入階梯與廣度
ROLE_JUNK = {
    "2025/11/01 帶東京都世田谷區議員們 g0v 台北社群空間交流",
    "好像沒有特別參與過",
}

# 年齡：原始 5 層用於全體分布；但在曾參與層（N=47）切 5 層會出現 N=2 的格
# （20 歲以下僅 2 人，lift 由 1/2 人決定＝雜訊），故交叉分析一律用收合後的 3 層：
# 30 歲以下 10 人／31–40 歲 19 人／41 歲以上 18 人。
AGE_ORDER = ["20 歲以下", "21 到 30 歲", "31 到 40 歲", "41 到 50 歲", "51 歲以上"]
AGE_COARSE = {
    "20 歲以下": "30 歲以下",
    "21 到 30 歲": "30 歲以下",
    "31 到 40 歲": "31 到 40 歲",
    "41 到 50 歲": "41 歲以上",
    "51 歲以上": "41 歲以上",
}
AGE_COARSE_ORDER = ["30 歲以下", "31 到 40 歲", "41 歲以上"]

# 動機題（Q12 初次／Q13 持續）共用的正式選項。
# 依 Klandermans 志願參與四類動機（集體／規範／報酬｛聲望、社交｝／認同）＋內在樂趣。
# 兩題選項相同，才能做同一批人的配對流向；選項外的自由填答單獨歸類，不塞進既有選項。
MOTIVES = [
    "我很認同這件事想達成的目標",
    "我認同這個社群，想成為其中一員",
    "純粹覺得好玩、有趣",
    "想認識新朋友、找到同好",
    "身邊有人在做，我就跟著加入",
    "累積作品集，練功或建立好名聲",
]
MOTIVE_TYPE = {
    "我很認同這件事想達成的目標": "集體（認同目標）",
    "我認同這個社群，想成為其中一員": "認同（社群歸屬）",
    "純粹覺得好玩、有趣": "內在樂趣",
    "想認識新朋友、找到同好": "報酬（社交）",
    "身邊有人在做，我就跟著加入": "規範（人際）",
    "累積作品集，練功或建立好名聲": "報酬（聲望）",
}

# 專長題的正式選項（複選）。選項外的一律是「其他」自由填答（實得 3 筆，各 1 人）。
# ⚠️ 這一題曾經完全沒有輸出表：常數定義在這裡、00_clean.py 也有清理，但沒有任何腳本
#    把它統計出來，06_number_index.py 自然索引不到，而報告第 5.1 節引用了 9 個專長數字。
#    「算術自洽但無來源可追」正是 61/126 那類錯誤能存活的環境，故補上 03_全體_專長。
SKILL_OPTS = [
    "議題研究",
    "專案管理",
    "行銷推廣",
    "行政、後勤",
    "文案撰寫",
    "寫程式",
    "活絡氣氛與關係維繫（舉例：讓夥伴彼此熟識、張羅食物，維持協作順暢）",
    "體驗設計（UI／UX）",
    "視覺設計",
]

# 資源題的正式選項（Q9 複選）。選項外的一律是「其他」自由填答，須經 bucket_freetext
# 收斂——否則 n=1 的個人語句會與正式選項並排、還會算出誇張的 lift。
RESOURCE_OPTS = [
    "人脈（例如：由社群介紹可諮詢的專家）",
    "經費（例如：獎助金、標案或機構支持費用）",
    "公開資料或開放資料（例如：政治獻金資料集）",
    "場地（例如：NPO Hub）",
    "現成的數位工具或平台（例如：Pol.is）",
    "政府窗口（例如：協助將專案成果結合到體制內）",
    "主要靠我自己想辦法",
]

# ---------------------------------------------------------------- 各複選題的正式選項
# 用途：把選項外的自由填答收斂成 FREETEXT_BUCKET（見 bucket_and_dedupe）。
#
# ⚠️ 判斷「哪些是正式選項」不能靠 02_問卷設計/問卷設計v.6.md——**實際上線的表單與設計稿有落差**
#    （已知案例：困擾題上線版少了「沒遇到」選項；領域題的選項文字也與設計稿不同）。
#    這份清單是從實際回收資料判讀出來的，並經 Claire 對照表單確認過兩個邊界案例：
#      · 活動意願的「目前都沒有特別想參加」→ **是正式選項**（表單同時另有「其他」欄）
#      · g0v 消息管道的 HackMD 活動彙整頁 → **是正式選項，且是甲方提供的，要獨立分析**
#    兩者都不可併進「其他」——併掉會丟失有意義的類別。
#
# 新增或修改本表時，03_crosstab.py 的守門會檢查：清單裡的每個選項都必須真的出現在資料中
# （擋打錯字），且會列出資料中不在清單裡的值（讓人確認那些真的是自由填答）。
VALID_OPTS = {
    C_DOMAINS: [
        "政府預算、決算與標案（看政府的錢怎麼花）", "地方發展與地方創生", "防災與災害應變",
        "假訊息與詐騙防治", "環境汙染與公害", "法律、立法歷程", "居住與租屋",
        "生態與生物多樣性", "交通與道路安全", "水環境（河川、海洋）", "健康與醫療",
        "土地使用與違章建築", "教育、親子與兒少青年", "司法判決資料", "選舉與政見資料",
        "語言與溝通（例如台語、點字）",
    ],
    C_TOOLS: [
        "群眾協力與通報工具（讓沒有技術背景的人，也能簡單回報、標記，一起累積資料）",
        "AI 應用（用 AI 整理、查證資料等）", "資料視覺化工具",
        "地理資訊與地圖工具（GIS、線上地圖）",
        "民意蒐集與線上審議工具（例如問卷、Polis、討論平台）",
        "怎麼找到現成的研究成果（學術論文、政府委辦研究、考察報告）",
        "開放協作知識庫（維基百科、Wikidata 等共筆知識）",
    ],
    C_EVENTS: [
        "公私協力怎麼談：一起討論公部門和民間合作的方法，以及常卡在哪",
        "公民科技實戰心法：從真實案例復盤，學前人怎麼把專案做起來",
        "公民科技資料庫入門：學會用網站和 AI 問答，快速查專案、看懂專案怎麼組成",
        "用 AI 幫你提案：從零開始，動手把點子變成專案構想和藍圖",
        "目前都沒有特別想參加",          # 正式選項，不是自由填答（Claire 已對照表單確認）
    ],
    C_G0V_CHANNEL: [
        "g0v 社群管道（FB_Threads_Instgram)", "親友推薦", "g0v Slack",
        "揪松團每月電子報", "揪松團 LINE 群組", "都沒有，我之前不太清楚這些管道",
        # 甲方提供的正式選項，要獨立分析——不可併進「其他」
        "社群活動資訊彙整網頁（https://g0v.hackmd.io/@jothon/event）",
    ],
    C_INFO_CHANNEL: [
        "非營利組織（例如：開放文化基金會、地球公民基金會）",
        "開源社群（例如：COSCUP、SITCON、g0v）",
        "研究單位", "學校", "我還不熟悉相關資訊管道", "政府單位", "企業",
    ],
    C_REGION: [
        "台北市", "新北市", "桃園市", "台中市", "北部其他（基隆、新竹市、新竹縣）",
        "台南市", "高雄市", "東部區域（宜蘭、花蓮、台東）",
        "中部區域（苗栗、彰化、南投、雲林）", "南部其他（嘉義市、嘉義縣、屏東）",
        "目前居住於海外",
    ],
    C_G0V_EVENTS: [
        "我沒參加過 g0v 的活動", "g0v Summit（兩年一次的高峰會）", "雙月大黑客松（大松）",
        "各專案的小聚（例如國會松、數位韌性松）", "零時小學校",
    ],
    C_RESOURCES: RESOURCE_OPTS,
    C_SKILLS: SKILL_OPTS,
    C_MOTIVE_FIRST: MOTIVES,
    C_MOTIVE_NOW: MOTIVES,
}

# 過去 30 天投入時數：序位
HOURS_ORDER = {
    "幾乎沒有": 1,
    "1 到 5 小時": 2,
    "6 到 20 小時": 3,
    "21 小時以上": 4,
}

# 專案階段：N=47 撐不起原始 5 分格，一律用收合後的 COARSE。
#
# ⚠️ 合併類別的名稱不可寫成「A／B」。原本第一類叫「早期（挖坑／跳坑）」，
#    本意是「這一格裝的是挖坑的人**或**跳坑的人」，但在「一列一個人」的逐人表裡，
#    讀者會讀成「這個人挖坑**又**跳坑」——實際發生過（Claire 核對逐人表時就這樣讀）。
#    改成「探索或開發中」：用「或」而非「／」，並且拿掉「挖坑／跳坑」這組 g0v 圈內術語，
#    因為報告要服務看不懂這些詞的圈外讀者（同「內部術語不進正文」的原則）。
#    原始選項的括號裡仍保有挖坑／跳坑，圈內人對得上。
STAGE_COARSE = {
    "正在探索要解決的問題（挖坑）": "早期（探索或開發中）",
    "正在開發、籌備、執行（跳坑）": "早期（探索或開發中）",
    "已經有原型或成果，正在努力讓成果可以影響到目標受眾（落地）": "落地",
    "持續運作、長期經營（維運）": "維運",
    "暫時擱置，或停止運作": "停擺",
}
STAGE_COARSE_ORDER = ["早期（探索或開發中）", "落地", "維運", "停擺"]

# 困擾量表：實際上線的表單「沒有」沒遇到欄，只有 1–5 強制作答。
# ⚠️「1」把「沒發生過」和「發生了但無感」混在一起 → 平均值系統性低估。
#    主要指標用 %≥3 與 %≥4，平均分只當次要且必須附註。
TROUBLE_PREFIX = "下面這些困難，各自對你造成多大的困擾？"
TROUBLE_SCALE = {
    "1：幾乎沒影響": 1,
    "2：有點困擾但還能處理": 2,
    "3：明顯卡住我、拖慢進度": 3,
    "4：受挫到萌生退意": 4,
    "5：困擾到專案無法持續": 5,
}
TROUBLE_CAVEAT = (
    "此題實際上線版本沒有「沒遇到」選項，13 題皆為 1–5 強制作答，"
    "「1：幾乎沒影響」混合了「沒發生過」與「發生了但無感」兩種情況，"
    "故平均值系統性低估，主要指標採 %≥3。"
)

# 狩野五點量表（功能型／反功能型共用）
KANO_LIKE = "喜歡"
KANO_MUST = "應該的"
KANO_NEUTRAL = "沒意見"
KANO_LIVE = "能忍受"
KANO_DISLIKE = "不喜歡"
KANO_FUNC_PREFIX = "如果有下面這些文章可以參考，你的感覺是？"
KANO_DYSF_PREFIX = "如果沒有下面這些文章可以參考，你的感覺是？"

# 主題編號：沿用舊報告附錄表 10 已在用的 ①–⑤，兩份文件才對得起來
KANO_NUM = {
    "如何發起一個公民科技專案": "①",
    "沒有現成資料時，怎麼搜尋、整理或自建資料集": "②",
    "怎麼捲動更多人（包含不會寫程式的人）一起參與": "③",
    "怎麼留住夥伴、維持團隊運作的能量": "④",
    "怎麼讓做好的東西真正落地、接進體制": "⑤",
}

# 圖表用短名（原題目過長，落點圖標不下）
KANO_SHORT = {
    "如何發起一個公民科技專案": "發起專案",
    "沒有現成資料時，怎麼搜尋、整理或自建資料集": "找資料／建資料",
    "怎麼捲動更多人（包含不會寫程式的人）一起參與": "捲動更多人參與",
    "怎麼留住夥伴、維持團隊運作的能量": "留住夥伴",
    "怎麼讓做好的東西真正落地、接進體制": "落地、接進體制",
}

# 狩野評估對照表：KANO_TABLE[功能型答案][反功能型答案] → A/O/M/I/R/Q
# 出處：satisfaction-survey-analyzer/references/methodology.md（標準 Kano 評估表）
KANO_TABLE = {
    KANO_LIKE:    {KANO_LIKE: "Q", KANO_MUST: "A", KANO_NEUTRAL: "A", KANO_LIVE: "A", KANO_DISLIKE: "O"},
    KANO_MUST:    {KANO_LIKE: "R", KANO_MUST: "I", KANO_NEUTRAL: "I", KANO_LIVE: "I", KANO_DISLIKE: "M"},
    KANO_NEUTRAL: {KANO_LIKE: "R", KANO_MUST: "I", KANO_NEUTRAL: "I", KANO_LIVE: "I", KANO_DISLIKE: "M"},
    KANO_LIVE:    {KANO_LIKE: "R", KANO_MUST: "I", KANO_NEUTRAL: "I", KANO_LIVE: "I", KANO_DISLIKE: "M"},
    KANO_DISLIKE: {KANO_LIKE: "R", KANO_MUST: "R", KANO_NEUTRAL: "R", KANO_LIVE: "R", KANO_DISLIKE: "Q"},
}

# ---------------------------------------------------------------- 選項歸併表
# Google 表單「其他」自由填答造成的重複選項。不合併會把同一個管道拆兩半、嚴重低估。
OPTION_MERGE = {
    C_G0V_CHANNEL: {
        "g0v 社群管道（FB_threads_Instgram)": "g0v 社群管道（FB_Threads_Instgram)",
        "g0v slack": "g0v Slack",
    },
    # 註：不要在這裡放人名歸併規則。人名去識別化（00_clean.py 步驟 2）先於選項歸併執行，
    #     值到這裡已經是 "[去識別化]"，任何以原始人名為鍵的規則都永遠不會命中。
}

# 去識別化：開放題中出現的人名（社群成員），代換為佔位字串。
# 組織／專案名稱保留（沿用前一版去識別化檔的標準），但報告引述時仍須去識別化。
NAME_REDACTIONS = {"chewei": "[去識別化]", "Chewei": "[去識別化]"}

# ---------------------------------------------------------------- 繪圖樣式

CJK_FONT = "Heiti TC"        # 本機已確認可用；備援 PingFang HK

# 配色取自 dataviz skill 的參考調色盤（validated default palette）前三槽。
# 已用 scripts/validate_palette.js --mode light --pairs all 驗證：
#   亮度帶 PASS｜彩度下限 PASS｜色盲分離 ΔE 9.2 PASS｜正常視覺 ΔE 24.0 PASS
#   對比 WARN（aqua 2.74:1）→ 依 relief rule，所有圖一律附直接數值標籤＋對應數據 CSV
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]     # 類別色，固定順序、不循環
PALETTE = {
    "primary": SERIES[0],
    "accent": SERIES[1],
    "neutral": "#8a8a85",
    "grid": "#e4e4e0",
    "surface": "#fcfcfb",
    # 三層固定配色：色隨實體，不隨排序改變
    "layers": {L_NEVER: SERIES[2], L_AWARE: SERIES[1], L_DONE: SERIES[0]},
    # 順序型（量值）：單一色相由淺到深
    "seq": ["#eaf1fb", "#c3d9f4", "#8db8ea", "#5695de", "#2a78d6", "#1b5296"],
    # 分歧型（極性，用於 lift 以 1.0 為中點）：兩色相＋中性灰中點，絕不彩虹
    "div_low": "#2a78d6", "div_mid": "#e8e8e6", "div_high": "#eb6834",
}


def setup_matplotlib():
    """套用中文字型與統一樣式。每支繪圖腳本開頭呼叫一次。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = [CJK_FONT, "PingFang HK", "Heiti TC"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    return plt


# ---------------------------------------------------------------- 工具函式


def load_clean():
    """載入去識別化後的資料。所有分析腳本的唯一入口。"""
    import pandas as pd
    if not CLEAN_CSV.exists():
        raise FileNotFoundError(f"找不到 {CLEAN_CSV}，請先執行 00_clean.py")
    df = pd.read_csv(CLEAN_CSV, dtype=str, keep_default_na=False)
    return df


def explode_multi(df, col):
    """複選題 → 長表（一列一個勾選項）。回傳 DataFrame[idx, 選項]。"""
    import pandas as pd
    rows = []
    for idx, val in df[col].items():
        for opt in str(val).split(MULTI_SELECT_SEP):
            opt = opt.strip()
            if opt:
                rows.append({"idx": idx, "選項": opt})
    return pd.DataFrame(rows)


def pct_table(df, col, denom=None):
    """
    複選題勾選率表：選項 → 票數 / 分母 / 比例。
    分母預設＝有作答該題的人數（不是全體），並一併輸出，確保數字可追溯。

    ⚠️ 「票數」是**勾選次數**，不是人數。單一選項的票數＝人數（一個人不會勾同一項兩次），
       但**多個選項的票數不可相加當人數**——會把複選同時勾多項的人重複計。
       要算「勾了這幾項當中任一項的人有幾個」，一律用 people_count()。
       （曾發生過：台北 41 票＋新北 39 票＝80，但實際住雙北的是 79 人，
        因為有 1 人同時勾了台北／新北／桃園。）
    """
    import pandas as pd
    answered = (df[col].astype(str).str.strip() != "").sum()
    d = denom if denom is not None else answered
    long = explode_multi(df, col)
    if long.empty:
        return pd.DataFrame(columns=["選項", "票數", "分母", "比例"])
    counts = long["選項"].value_counts().rename_axis("選項").reset_index(name="票數")
    counts["分母"] = d
    counts["比例"] = counts["票數"] / d
    return counts.sort_values("票數", ascending=False).reset_index(drop=True)


def people_count(df, col, options):
    """
    複選題：勾了 options 當中**任一項**的「人數」（去重），不是票數加總。
    回傳 (人數, 分母)。分母＝該題有作答的人數。

    這是 pct_table 的配對函式：凡是報告要寫「某幾個選項合計佔幾成」，都必須用這個，
    不能把 pct_table 的票數相加。
    """
    wanted = set(options)
    hit = 0
    for val in df[col]:
        picked = {o.strip() for o in str(val).split(MULTI_SELECT_SEP) if o.strip()}
        if picked & wanted:
            hit += 1
    denom = int((df[col].astype(str).str.strip() != "").sum())
    return hit, denom


def save_table(df, name, note=""):
    """輸出數據 CSV 到 分析結果/，供報告、簡報、網站取用。"""
    path = TABLE_DIR / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  → 表 {path.name}  ({len(df)} 列)" + (f"  // {note}" if note else ""))
    return path


def save_fig(fig, name, bbox="tight"):
    """
    bbox=None：輸出完整畫布，尺寸＝figsize × dpi，用於需要精確長寬比的圖
    （例如要換進 docx、不能被拉伸的圖）。

    ⚠️ 不能直接把 None 傳給 savefig(bbox_inches=...)——那會退回讀 rcParams
       的 savefig.bbox（本專案設為 "tight"），等於沒有生效。必須明確給 figure 的 bbox。
    """
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches=(fig.bbox_inches if bbox is None else bbox))
    print(f"  → 圖 {path.name}")
    return path
