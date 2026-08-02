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
  var PERSONA_ROUTES = {
    newcomer: {
      label: "我是新手，還在了解這個圈子",
      why: "第七章顯示，擋住新人的頭號原因是「不知道有哪些專案」而非能力不足，"
        + "所以先看第一章認識這群人、第七章看入口斷在哪，再看研究建議 1.3 的分階段資源規劃。",
      sections: [
        ["#ch1", "第一章：這群人是誰、在哪裡"],
        ["#ch7", "第七章：這個圈子的入口在哪、斷在哪"],
        ["#rec-1-3", "研究建議 1.3：依接觸程度規劃的資源建議"],
      ],
    },
    doing: {
      label: "我正在做（或做過）公民科技專案",
      why: "這三章都只問「做過專案的 47 人」，談的是實際卡關的痛點（第三章）、"
        + "動機怎麼變化（第四章）、手上有什麼資源可用（第五章），最貼近你現在的處境。",
      sections: [
        ["#ch3", "第三章：讓貢獻者感到心累的是什麼"],
        ["#ch4", "第四章：動機換過一輪，流失最多的是什麼"],
        ["#ch5", "第五章：專案裡最頻繁使用的資源"],
      ],
    },
    funder: {
      label: "我可能提供資源，或想支持社群經營",
      why: "第六章是出資者自己的評估準則、研究建議 1.4 整理了資源以外的支持形式，"
        + "第 3.2 節則提醒：決定權越大的人越容易累垮，是長期支持專案時值得留意的風險。",
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
      var html = "<p class=\"persona-why\">" + route.why + "</p>建議先讀：<ul>" +
        route.sections.map(function (s) {
          return '<li><a href="' + s[0] + '">' + s[1] + "</a></li>";
        }).join("") + "</ul>";
      personaResult.innerHTML = html;
    });
  });

})();
