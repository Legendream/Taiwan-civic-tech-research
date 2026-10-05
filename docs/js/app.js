/* app.js — 章節導覽、閱讀進度、手機目錄、身分推薦、圖表收合。不依賴任何外部函式庫。
 * 2026-10 重設計：移除深色模式切換；精華版的章節目錄、段落編號、分段進度、
 * 完整版的章節切換都由這支程式從既有標題產生，不需要改產生程式。
 * 沒有 JavaScript 時頁面仍可完整閱讀，只是少了這些導覽輔助。
 */
(function () {
  "use strict";

  // 介面文字。中文頁用預設值；英文頁在載入本檔前設定 window.APP_TEXT、window.PERSONA_ROUTES_OVERRIDE 覆蓋。
  var UI = Object.assign({
    tocTitle: "本頁章節",
    startWith: "建議先讀：",
    nextChapter: "下一章",
    readPct: "已讀 {p}%",
  }, window.APP_TEXT || {});

  var doc = document.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var isDesktop = function () { return window.matchMedia("(min-width: 1024px)").matches; };

  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function scrollPct() {
    var se = document.scrollingElement || doc;
    var max = se.scrollHeight - window.innerHeight;
    return max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
  }
  function onScroll(fn) {
    var ticking = false;
    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { ticking = false; fn(); });
    }, { passive: true });
    window.addEventListener("resize", fn);
    fn();
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // ================================================================ 精華版
  var summary = document.querySelector(".summary-page");
  if (summary) {
    var heads = Array.prototype.slice.call(summary.querySelectorAll(":scope > h2[id]"));
    var total = heads.length;

    // 每段 h2 上方加「03 / 06」，同時收集目錄項目
    var tocItems = heads.map(function (h, i) {
      var num = el("p", "sec-num", pad2(i + 1) + " / " + pad2(total));
      num.setAttribute("aria-hidden", "true");
      h.parentNode.insertBefore(num, h);
      return { id: h.id, n: pad2(i + 1), text: h.textContent };
    });

    function buildList() {
      var ol = el("ol");
      tocItems.forEach(function (t) {
        var li = el("li");
        var a = el("a");
        a.href = "#" + t.id;
        a.appendChild(el("span", "toc-n", t.n));
        a.appendChild(document.createTextNode(t.text));
        li.appendChild(a);
        ol.appendChild(li);
      });
      return ol;
    }

    // 手機：封面下方的目錄
    var cover = summary.querySelector(".cover");
    if (cover && total) {
      var toc = el("nav", "page-toc");
      toc.setAttribute("aria-label", UI.tocTitle);
      toc.appendChild(el("p", "toc-title", UI.tocTitle));
      toc.appendChild(buildList());
      cover.appendChild(toc);
    }

    // 桌機：左側章節軌
    var layout = document.querySelector(".layout");
    var main = document.getElementById("main");
    var railLinks = [];
    if (layout && main && total) {
      var rail = el("nav", "page-rail");
      rail.setAttribute("aria-label", UI.tocTitle);
      var box = el("div", "rail-box");
      box.appendChild(el("p", "toc-title", UI.tocTitle));
      var list = buildList();
      box.appendChild(list);
      rail.appendChild(box);
      layout.insertBefore(rail, main);
      railLinks = Array.prototype.slice.call(list.querySelectorAll("a"));
    }

    // 頂列下方的分段進度
    var topbar = document.querySelector(".topbar");
    var segFills = [], segLabel = null;
    if (topbar && total) {
      var seg = el("div", "seg-progress");
      seg.setAttribute("aria-hidden", "true");
      var segs = el("div", "segs");
      heads.forEach(function () {
        var s = el("i", "seg");
        var b = el("b");
        s.appendChild(b);
        segs.appendChild(s);
        segFills.push(b);
      });
      seg.appendChild(segs);
      segLabel = el("span", "seg-label", "0 / " + total);
      seg.appendChild(segLabel);
      topbar.appendChild(seg);
    }

    onScroll(function () {
      var line = isDesktop() ? 120 : 150;
      var cur = -1, frac = 0;
      for (var i = 0; i < heads.length; i++) {
        if (heads[i].getBoundingClientRect().top <= line) cur = i;
      }
      if (cur >= 0) {
        var top = heads[cur].getBoundingClientRect().top;
        var nextTop = cur + 1 < heads.length
          ? heads[cur + 1].getBoundingClientRect().top
          : summary.getBoundingClientRect().bottom;
        var span = nextTop - top;
        frac = span > 0 ? Math.min(1, Math.max(0, (line - top) / span)) : 1;
      }
      segFills.forEach(function (b, i) {
        b.style.width = (i < cur ? 100 : i === cur ? Math.round(frac * 100) : 0) + "%";
      });
      if (segLabel) segLabel.textContent = (cur + 1) + " / " + total;
      railLinks.forEach(function (a, i) { a.classList.toggle("active", i === Math.max(cur, 0)); });
    });

    // 手機上把標記 data-fold="mobile" 的圖表收進「展開」，點開再畫
    if (!isDesktop()) {
      var figs = (window.FIGDATA && window.FIGDATA.figures) || {};
      summary.querySelectorAll('.chart-block[data-fold="mobile"]').forEach(function (block) {
        var fig = figs[block.getAttribute("data-chart")];
        var det = el("details", "chart-fold");
        var sum = el("summary", null, fig ? fig.title : block.getAttribute("data-chart"));
        det.appendChild(sum);
        block.parentNode.insertBefore(det, block);
        det.appendChild(block);
        det.addEventListener("toggle", function () {
          if (det.open && window.ChartKit && window.ChartKit.render) window.ChartKit.render(block);
        });
      });
    }
  }

  // ================================================================ 完整版：章節導覽
  var sidebar = document.getElementById("sidebar");
  if (sidebar) {
    var overlay = document.getElementById("sidebarOverlay");
    var toggleBtn = document.getElementById("mobileNavToggle");
    var closeBtn = document.getElementById("sheetClose");

    function openSheet() {
      sidebar.classList.add("open");
      if (overlay) overlay.classList.add("open");
      if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      var cur = sidebar.querySelector("a.active");
      if (cur) cur.scrollIntoView({ block: "center" });
      if (closeBtn) closeBtn.focus();
    }
    function closeSheet(returnFocus) {
      if (!sidebar.classList.contains("open")) return;
      sidebar.classList.remove("open");
      if (overlay) overlay.classList.remove("open");
      if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      if (returnFocus && toggleBtn) toggleBtn.focus();
    }
    if (toggleBtn) toggleBtn.addEventListener("click", openSheet);
    if (closeBtn) closeBtn.addEventListener("click", function () { closeSheet(true); });
    if (overlay) overlay.addEventListener("click", function () { closeSheet(true); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSheet(true);
    });
    sidebar.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { closeSheet(false); });
    });
    window.addEventListener("resize", function () { if (isDesktop()) closeSheet(false); });

    // 章節結構：大部（nav h2）→ 章（第一層連結）→ 小節（.sub 連結）
    var navLinks = Array.prototype.slice.call(sidebar.querySelectorAll("nav a[href^='#']"));
    var entries = navLinks.map(function (a) {
      var target = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
      if (!target) return null;
      var isSub = !!a.closest(".sub");
      var topLi = isSub ? a.closest(".sub").closest("li") : a.closest("li");
      var topLink = topLi ? topLi.querySelector(":scope > a") : a;
      var ul = topLi ? topLi.parentNode : null;
      var group = ul && ul.previousElementSibling && ul.previousElementSibling.tagName === "H2"
        ? ul.previousElementSibling.textContent : "";
      return { link: a, target: target, isSub: isSub, topLi: topLi, topLink: topLink, group: group };
    }).filter(Boolean);

    var dockPart = document.getElementById("dockPart");
    var dockCh = document.getElementById("dockCh");
    var fills = document.querySelectorAll(".progress-fill");
    var pctLabel = document.getElementById("progressLabel");

    onScroll(function () {
      var y = window.scrollY + (isDesktop() ? 120 : 160);
      var cur = null;
      entries.forEach(function (s) {
        if (s.target.getBoundingClientRect().top + window.scrollY <= y) cur = s;
      });
      entries.forEach(function (s) {
        s.link.classList.remove("active", "cur");
        if (s.topLi) s.topLi.classList.remove("open");
      });
      if (cur) {
        cur.link.classList.add("active");
        if (cur.topLi) cur.topLi.classList.add("open");
        if (cur.isSub && cur.topLink) cur.topLink.classList.add("cur");
        if (dockPart) dockPart.textContent = cur.group;
        if (dockCh) dockCh.textContent = cur.isSub && cur.topLink
          ? cur.topLink.textContent + " › " + cur.link.textContent
          : cur.link.textContent;
      }
      var p = scrollPct();
      fills.forEach(function (f) { f.style.width = Math.round(p * 100) + "%"; });
      if (pctLabel) pctLabel.textContent = UI.readPct.replace("{p}", Math.round(p * 100));
    });

    // 每一章結尾加「下一章」（只加在研究發現、研究建議、反思這幾類章節）
    var tops = entries.filter(function (s) { return !s.isSub; });
    tops.forEach(function (s, i) {
      var sec = s.target;
      var next = tops[i + 1];
      if (!next || sec.tagName !== "SECTION" || !/^(ch\d|rec-|reflect-)/.test(sec.id)) return;
      var nav = el("nav", "chapter-pager");
      nav.setAttribute("aria-label", UI.nextChapter);
      var a = el("a");
      a.href = "#" + next.target.id;
      var wrap = el("span");
      wrap.appendChild(el("span", "pager-k", UI.nextChapter));
      wrap.appendChild(el("span", "pager-t", next.link.textContent));
      a.appendChild(wrap);
      nav.appendChild(a);
      sec.appendChild(nav);
    });
  }

  // ================================================================ 身分推薦
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
      why: "這三章只針對 47 位實作者來談，聊聊大家實際卡住的痛點（第三章）、動機怎麼隨時間改變（第四章），還有手邊到底有哪些資源能用（第五章），最貼合你現在遇到的狀況。",
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

  var personaButtons = Array.prototype.slice.call(document.querySelectorAll(".persona-btn"));
  var personaResult = document.getElementById("personaResult");
  function pickPersona(btn, moveFocus) {
    personaButtons.forEach(function (b) {
      var on = b === btn;
      b.classList.toggle("active", on);
      b.setAttribute("aria-checked", on ? "true" : "false");
      b.tabIndex = on ? 0 : -1;
    });
    if (moveFocus) btn.focus();
    var route = PERSONA_ROUTES[btn.getAttribute("data-persona")];
    if (!route || !personaResult) return;
    personaResult.textContent = "";
    personaResult.appendChild(el("p", "persona-why", route.why));
    personaResult.appendChild(el("p", "route-label", UI.startWith));
    var ol = el("ol", "route");
    route.sections.forEach(function (s) {
      var li = el("li");
      var a = el("a", null, s[1]);
      a.href = s[0];
      li.appendChild(a);
      ol.appendChild(li);
    });
    personaResult.appendChild(ol);
  }
  personaButtons.forEach(function (btn, i) {
    btn.tabIndex = i === 0 ? 0 : -1;
    btn.addEventListener("click", function () { pickPersona(btn, false); });
    // 單選群組的鍵盤操作：方向鍵在選項間移動
    btn.addEventListener("keydown", function (e) {
      var d = (e.key === "ArrowRight" || e.key === "ArrowDown") ? 1
        : (e.key === "ArrowLeft" || e.key === "ArrowUp") ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      var n = personaButtons[(i + d + personaButtons.length) % personaButtons.length];
      pickPersona(n, true);
    });
  });

  if (reduceMotion) doc.style.scrollBehavior = "auto";
})();
