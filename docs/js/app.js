/* app.js — 章節導覽、閱讀進度、手機選單、身分推薦。不依賴任何外部函式庫。 */
(function () {
  "use strict";

  // ---------------------------------------------------------------- 手機側邊欄
  var sidebar = document.getElementById("sidebar");
  var overlay = document.getElementById("sidebarOverlay");
  var toggleBtn = document.getElementById("mobileNavToggle");

  function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("open");
    toggleBtn.setAttribute("aria-expanded", "true");
  }
  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("open");
    toggleBtn.setAttribute("aria-expanded", "false");
  }
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      if (sidebar.classList.contains("open")) closeSidebar(); else openSidebar();
    });
    overlay.addEventListener("click", closeSidebar);
    sidebar.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", closeSidebar);
    });
  }

  // ---------------------------------------------------------------- 閱讀進度
  var progressFill = document.getElementById("progressFill");
  function updateProgress() {
    var doc = document.documentElement;
    var scrollable = doc.scrollHeight - doc.clientHeight;
    var pct = scrollable > 0 ? (doc.scrollTop || document.body.scrollTop) / scrollable : 0;
    if (progressFill) progressFill.style.width = Math.min(100, Math.max(0, pct * 100)) + "%";
  }
  window.addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();

  // ---------------------------------------------------------------- Scrollspy
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".sidebar nav a[href^='#']"));
  var sections = navLinks
    .map(function (a) {
      var id = a.getAttribute("href").slice(1);
      var target = document.getElementById(id);
      return target ? { link: a, target: target } : null;
    })
    .filter(Boolean);

  function onScrollSpy() {
    var y = window.scrollY + 120;
    var current = null;
    sections.forEach(function (s) {
      if (s.target.offsetTop <= y) current = s;
    });
    navLinks.forEach(function (a) { a.classList.remove("active"); });
    if (current) current.link.classList.add("active");
  }
  window.addEventListener("scroll", onScrollSpy, { passive: true });
  onScrollSpy();

  // ---------------------------------------------------------------- 身分推薦
  // 介面文字。中文頁用預設值；英文頁在載入本檔前設定 window.APP_TEXT、window.PERSONA_ROUTES_OVERRIDE 覆蓋。
  var UI = Object.assign({
    startWith: "建議先讀：",
    dark: "🌙 深色", light: "☀️ 淺色",
    toDark: "切換成深色模式", toLight: "切換成淺色模式",
  }, window.APP_TEXT || {});

  var PERSONA_ROUTES = window.PERSONA_ROUTES_OVERRIDE || {
    newcomer: {
      label: "我是新手，還在了解這個圈子",
      why: "第七章發現，新人進不來的第一大原因，是「不知道有哪些專案」，而不是能力不夠。建議你先讀第一章看看這群人都在哪裡、第七章弄清楚入口到底斷在哪，最後再看研究建議 1.3 的各階段資源規劃。",
      sections: [
        ["#ch1", "第一章：這群人是誰、在哪裡"],
        ["#ch7", "第七章：這個圈子的入口在哪、斷在哪"],
        ["#rec-1-3", "研究建議 1.3：照接觸深淺規劃的資源建議"],
      ],
    },
    doing: {
      label: "我正在做（或做過）公民科技專案",
      why: "這三章只針對「做過專案的 47 人」來談，聊聊大家實際卡住的痛點（第三章）、動機怎麼隨時間改變（第四章），還有手邊到底有哪些資源能用（第五章），最貼合你現在遇到的狀況。",
      sections: [
        ["#ch3", "第三章：讓貢獻者感到心累的是什麼"],
        ["#ch4", "第四章：動機換過一輪，流失最多的是什麼"],
        ["#ch5", "第五章：專案裡最常派上用場的資源"],
      ],
    },
    funder: {
      label: "我可能提供資源，或想支持社群經營",
      why: "第六章整理了出資者自身的評估準則、研究建議 1.4 歸納了資金以外的支持形式；第 3.2 節則提醒：決定權越大的人越容易累垮，是長期支持專案時值得留意的風險。",
      sections: [
        ["#ch6", "第六章：出資者怎麼評估專案"],
        ["#rec-1-4", "研究建議 1.4：可以怎麼支持公民科技生態系"],
        ["#ch3-2", "第 3.2 節：決定權越大的人，越容易被累垮"],
      ],
    },
  };

  var personaButtons = document.querySelectorAll(".persona-btn");
  var personaResult = document.getElementById("personaResult");
  personaButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      personaButtons.forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var key = btn.getAttribute("data-persona");
      var route = PERSONA_ROUTES[key];
      if (!route || !personaResult) return;
      var html = "<p class=\"persona-why\">" + route.why + "</p>" + UI.startWith + "<ul>" +
        route.sections.map(function (s) {
          return '<li><a href="' + s[0] + '">' + s[1] + "</a></li>";
        }).join("") + "</ul>";
      personaResult.innerHTML = html;
    });
  });

  // ---------------------------------------------------------------- 深色／淺色手動切換
  // 預設跟隨訪客系統設定；按過一次之後記住選擇（localStorage），下次來也維持這個選擇。
  var themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    var mql = window.matchMedia("(prefers-color-scheme: dark)");

    function effectiveTheme() {
      var stored = localStorage.getItem("theme");
      return stored || (mql.matches ? "dark" : "light");
    }
    function applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      themeToggle.textContent = theme === "dark" ? UI.light : UI.dark;
      themeToggle.setAttribute("aria-label", theme === "dark" ? UI.toLight : UI.toDark);
    }

    applyTheme(effectiveTheme());
    themeToggle.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      localStorage.setItem("theme", next);
      applyTheme(next);
    });
    // 使用者還沒手動選過的話，系統深色/淺色切換時網頁也跟著換
    mql.addEventListener("change", function () {
      if (!localStorage.getItem("theme")) applyTheme(effectiveTheme());
    });
  }
})();
