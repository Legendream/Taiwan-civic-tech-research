// 由 20_build_english.py 自動產生，不要手改。英文頁在 charts.js、app.js 之前載入。
window.CHART_TEXT = {
  sep: ". ",
  wordWrap: true,
  maxLines: 3,
  score3Val: function (pct, n, d) { return "3+: " + pct + " (" + n + "/" + d + ")"; },
  pctFrac: function (pct, n, d) { return pct + " (" + n + "/" + d + ")"; },
  pctN: function (pct, n) { return pct + " (" + n + ")"; },
  gap: " ",
  score3Tip: "Rated 3 or higher: ",
  score4Tip: "Rated 4 or higher: ",
  peoplePct: function (n, pct) { return n + " people (" + pct + ")"; },
  people: function (n) { return n + " people"; },
  withN: function (lab, n) { return lab + " (" + n + ")"; },
  panelHead: function (group, d, up, down) {
    return group + " (" + d + " people): " + up + " above overall, " + down + " below";
  },
  diffTip: function (g, n, d, b, isUp, pts) {
    return "This group: " + g + " (" + n + "/" + d + ") | Overall: " + b + " | " + pts + " points " + (isUp ? "higher" : "lower");
  },
  kanoI: "Indifferent", kanoA: "Attractive", kanoM: "Must-be", kanoO: "Performance",
  viewTable: "View data table",
  thItems: ["Option", "Share", "Count", "Base"],
  thTrouble: ["Difficulty", "Rated 3+", "Rated 4+", "Base"],
  thAge: ["Age group", "Motive", "Group share", "Overall share", "Difference (points)"],
  thKano: ["Topic", "SI", "DSI", "Category"],
  thKanoLayers: ["Group", "Topic", "SI", "DSI", "Category"],
  thLayered: ["Option", "Group", "Share", "Count", "Base"],
  toggleAria: "Switch group view",
  allGroups: "All three groups",
  only: "Only: ",
  noData: "(Chart data not found: ",
  badType: "(Unsupported chart type: ",
  close: ")"
};
window.APP_TEXT = {
 "tocTitle": "On this page",
 "startWith": "Start with:",
 "nextChapter": "Next chapter",
 "readPct": "{p}% read"
};
window.PERSONA_ROUTES_OVERRIDE = {
 "newcomer": {
  "why": "Chapter 7 found that the number one reason newcomers don't get in is \"not knowing which projects exist\", not a lack of skills. Start with Chapter 1 to see who these people are and where they are, then Chapter 7 to see where the way in breaks, and finally Recommendation 1.3 for resources at each stage.",
  "sections": [
   [
    "#ch1",
    "Chapter 1: Who they are and where they are"
   ],
   [
    "#ch7",
    "Chapter 7: Where the way in is, and where it breaks"
   ],
   [
    "#rec-1-3",
    "Recommendation 1.3: Resources for each level of involvement"
   ]
  ]
 },
 "doing": {
  "why": "These three chapters focus only on \"the 47 who have worked on a project\": the problems they actually ran into (Chapter 3), how their motives changed over time (Chapter 4), and the resources they had to work with (Chapter 5). They are closest to what you are dealing with now.",
  "sections": [
   [
    "#ch3",
    "Chapter 3: What wears Builders down"
   ],
   [
    "#ch4",
    "Chapter 4: Motives change, and which one fades most"
   ],
   [
    "#ch5",
    "Chapter 5: The resources projects use most"
   ]
  ]
 },
 "funder": {
  "why": "Chapter 6 covers how funders themselves assess projects. Recommendation 1.4 sums up forms of support beyond money. Section 3.2 is a reminder: the more say people have, the more likely they are to burn out, a risk worth watching when you support a project over the long term.",
  "sections": [
   [
    "#ch6",
    "Chapter 6: How funders assess projects"
   ],
   [
    "#rec-1-4",
    "Recommendation 1.4: How to support the civic tech ecosystem"
   ],
   [
    "#ch3-2",
    "Section 3.2: The more say people have, the more likely they are to burn out"
   ]
  ]
 }
};
