/* charts.js — 通用 SVG 圖表渲染器。
 * 讀 window.FIGDATA（由 13_web_data.py 產生），依 type 畫成對應圖形。
 * 不依賴任何外部函式庫；所有文字都是 SVG <text>，可選取、可被螢幕閱讀器讀到。
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var PAL = (window.FIGDATA && window.FIGDATA.palette) || {
    primary: "#2a78d6", accent: "#eb6834", neutral: "#8a8a85", grid: "#e4e4e0",
    layers: { "從未接觸": "#1baf7a", "接觸未參與": "#eb6834", "曾參與": "#2a78d6" },
  };
  var LAYER_ORDER = (window.FIGDATA && window.FIGDATA.layerOrder) ||
    ["從未接觸", "接觸未參與", "曾參與"];
  var LAYER_PLAIN = (window.FIGDATA && window.FIGDATA.layerPlain) || {};

  function el(tag, attrs, children) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) {
      if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  function text(x, y, str, attrs) {
    var t = el("text", Object.assign({ x: x, y: y }, attrs || {}));
    t.textContent = str;
    return t;
  }

  function pct0(p) { return Math.round(p * 100) + "%"; }
  function pct1(p) { return (Math.round(p * 1000) / 10).toFixed(1) + "%"; }

  function measureText(str, fontSize) {
    // CJK 字寬粗估：中文字約等於字高，英數約 0.55 倍。避免載入字型量測的開銷。
    var w = 0;
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      w += (c > 255) ? fontSize : fontSize * 0.58;
    }
    return w;
  }

  function wrapLabel(str, maxWidth, fontSize) {
    if (measureText(str, fontSize) <= maxWidth) return [str];
    var lines = [], cur = "";
    for (var i = 0; i < str.length; i++) {
      var next = cur + str[i];
      if (measureText(next, fontSize) > maxWidth && cur.length > 0) {
        lines.push(cur);
        cur = str[i];
      } else {
        cur = next;
      }
    }
    if (cur) lines.push(cur);
    return lines.slice(0, 2); // 最多兩行，避免長標籤把圖撐爆
  }

  // ---------------------------------------------------------------- tooltip
  var tip;
  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement("div");
    tip.className = "chart-tip";
    tip.setAttribute("role", "status");
    tip.hidden = true;
    document.body.appendChild(tip);
    return tip;
  }

  function showTip(evt, html) {
    var t = ensureTip();
    t.innerHTML = html;
    t.hidden = false;
    var x = (evt.touches ? evt.touches[0].clientX : evt.clientX) + 14;
    var y = (evt.touches ? evt.touches[0].clientY : evt.clientY) + 14;
    var vw = window.innerWidth, vh = window.innerHeight;
    t.style.left = Math.min(x, vw - 220) + "px";
    t.style.top = Math.min(y, vh - 70) + "px";
  }
  function hideTip() { if (tip) tip.hidden = true; }

  function bindHover(target, htmlFn) {
    target.addEventListener("mousemove", function (e) { showTip(e, htmlFn()); });
    target.addEventListener("mouseleave", hideTip);
    target.addEventListener("touchstart", function (e) { showTip(e, htmlFn()); }, { passive: true });
    target.style.cursor = "pointer";
  }

  // ---------------------------------------------------------------- 共用外框
  function mountSVG(container, width, height, ariaLabel) {
    container.innerHTML = "";
    var svg = el("svg", {
      viewBox: "0 0 " + width + " " + height,
      width: "100%",
      height: height,
      role: "img",
      "aria-label": ariaLabel,
      preserveAspectRatio: "xMinYMin meet",
    });
    var titleEl = document.createElementNS(NS, "title");
    titleEl.textContent = ariaLabel;
    svg.appendChild(titleEl);
    container.appendChild(svg);
    return svg;
  }

  function chartWidth(container) {
    var w = container.clientWidth || container.parentElement.clientWidth || 340;
    return Math.max(280, Math.min(w, 900));
  }

  // ---------------------------------------------------------------- hbar
  function renderHbar(container, fig) {
    var W = chartWidth(container);
    var labelFS = 13, valueFS = 12.5;
    var barH = 16, rowGap = 10, labelGap = 4;
    var leftPad = 4;
    var maxValW = Math.max.apply(null, fig.items.map(function (d) {
      return measureText(pct0(d.pct) + "（" + d.n + "/" + d.d + "）", valueFS);
    }));
    var rightPad = Math.min(W * 0.4, maxValW + 16);
    var barMaxW = W - leftPad - rightPad;
    var maxPct = Math.max.apply(null, fig.items.map(function (d) { return d.pct; })) || 1;

    var items = fig.items;
    var rowTops = [];
    var y = 8;
    items.forEach(function (d) {
      var lines = wrapLabel(d.label, W - leftPad - 4, labelFS);
      var lh = lines.length * (labelFS + 2);
      rowTops.push({ y: y, lines: lines });
      y += lh + labelGap + barH + rowGap;
    });
    var H = y + 4;

    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);

    items.forEach(function (d, i) {
      var rt = rowTops[i];
      var ly = rt.y;
      rt.lines.forEach(function (line) {
        svg.appendChild(text(leftPad, ly + labelFS, line,
          { "font-size": labelFS, fill: "#2a2a28", "font-weight": 500 }));
        ly += labelFS + 2;
      });
      var barY = ly + labelGap;
      var bw = Math.max(2, (d.pct / maxPct) * barMaxW);
      var rect = el("rect", {
        x: leftPad, y: barY, width: bw, height: barH,
        fill: PAL.primary, rx: 2,
      });
      svg.appendChild(rect);
      svg.appendChild(text(leftPad + bw + 6, barY + barH - 3,
        pct0(d.pct) + "（" + d.n + "/" + d.d + "）",
        { "font-size": valueFS, fill: "#52514e" }));

      var hit = el("rect", {
        x: 0, y: rt.y, width: W, height: (barY + barH) - rt.y, fill: "transparent",
      });
      bindHover(hit, function () {
        return "<strong>" + escapeHtml(d.label) + "</strong><br>" +
          pct1(d.pct) + "　(" + d.n + " / " + d.d + ")";
      });
      svg.appendChild(hit);
    });
    appendCaption(container, fig.denomNote);
  }

  // ---------------------------------------------------------------- stacked-hbar
  function renderStackedHbar(container, fig) {
    var W = chartWidth(container);
    var labelFS = 12.5, valueFS = 11;
    var barH = 20, rowGap = 14, labelGap = 4;
    var leftPad = 4;
    var maxValW = Math.max.apply(null, fig.items.map(function (d) {
      return measureText("3分以上 " + pct0(d.pct3plus) + "（" + d.n3plus + "/" + d.d + "）", valueFS);
    }));
    var rightPad = Math.min(W * 0.55, maxValW + 14);
    var barMaxW = W - leftPad - rightPad;
    var maxTotal = Math.max.apply(null, fig.items.map(function (d) { return d.d; }));

    var rowTops = [];
    var y = 8;
    fig.items.forEach(function (d) {
      var lines = wrapLabel(d.label, W - leftPad - 4, labelFS);
      rowTops.push({ y: y, lines: lines });
      y += lines.length * (labelFS + 2) + labelGap + barH + rowGap;
    });
    var legendEntries = fig.seriesLabels.map(function (lab, si) {
      return { lab: lab, color: fig.seriesColors[si], w: 16 + measureText(lab, 10.5) + 18 };
    });
    var legendLines = wrapFlow(legendEntries, W - leftPad);
    var legendH = legendLines.length * 16 + 12;
    var H = y + legendH;

    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);

    fig.items.forEach(function (d, i) {
      var rt = rowTops[i];
      var ly = rt.y;
      rt.lines.forEach(function (line) {
        svg.appendChild(text(leftPad, ly + labelFS, line,
          { "font-size": labelFS, fill: "#2a2a28", "font-weight": 500 }));
        ly += labelFS + 2;
      });
      var barY = ly + labelGap;
      var x = leftPad;
      d.counts.forEach(function (c, si) {
        var w = (c / maxTotal) * barMaxW;
        if (w > 0) {
          var rect = el("rect", {
            x: x, y: barY, width: w, height: barH, fill: fig.seriesColors[si],
          });
          svg.appendChild(rect);
          if (c >= 3) {
            svg.appendChild(text(x + w / 2, barY + barH / 2 + 4, String(c),
              { "font-size": valueFS, fill: "#0b0b0b", "text-anchor": "middle" }));
          }
        }
        x += w;
      });
      svg.appendChild(text(x + 8, barY + barH - 5,
        "3分以上 " + pct0(d.pct3plus) + "（" + d.n3plus + "/" + d.d + "）",
        { "font-size": valueFS, fill: "#52514e" }));

      var hit = el("rect", { x: 0, y: rt.y, width: W, height: (barY + barH) - rt.y, fill: "transparent" });
      bindHover(hit, function () {
        return "<strong>" + escapeHtml(d.label) + "</strong><br>" +
          "3 分以上：" + pct1(d.pct3plus) + " (" + d.n3plus + "/" + d.d + ")<br>" +
          "4 分以上：" + pct1(d.pct4plus) + " (" + d.n4plus + "/" + d.d + ")";
      });
      svg.appendChild(hit);
    });

    // 圖例
    legendLines.forEach(function (line, li) {
      var lx = leftPad, lyLegend = y + 18 + li * 16;
      line.forEach(function (entry) {
        var sw = el("rect", { x: lx, y: lyLegend - 10, width: 12, height: 12, fill: entry.color });
        svg.appendChild(sw);
        svg.appendChild(text(lx + 16, lyLegend, entry.lab, { "font-size": 10.5, fill: "#52514e" }));
        lx += entry.w;
      });
    });
    appendCaption(container, fig.denomNote);
  }

  // ---------------------------------------------------------------- donut
  function renderDonut(container, fig) {
    var W = chartWidth(container);
    var size = Math.min(W, 420);
    var H = size + 70;
    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);
    var cx = W / 2, cy = size / 2 + 10, r = size / 2 - 30, rInner = r * 0.55;
    var total = fig.items.reduce(function (s, d) { return s + d.n; }, 0);
    var startAngle = -Math.PI / 2;

    fig.items.forEach(function (d) {
      var angle = (d.n / total) * Math.PI * 2;
      var endAngle = startAngle + angle;
      var largeArc = angle > Math.PI ? 1 : 0;
      var x1 = cx + r * Math.cos(startAngle), y1 = cy + r * Math.sin(startAngle);
      var x2 = cx + r * Math.cos(endAngle), y2 = cy + r * Math.sin(endAngle);
      var xi1 = cx + rInner * Math.cos(endAngle), yi1 = cy + rInner * Math.sin(endAngle);
      var xi2 = cx + rInner * Math.cos(startAngle), yi2 = cy + rInner * Math.sin(startAngle);
      var color = PAL.layers[d.key] || PAL.primary;
      var path = "M " + x1 + " " + y1 +
        " A " + r + " " + r + " 0 " + largeArc + " 1 " + x2 + " " + y2 +
        " L " + xi1 + " " + yi1 +
        " A " + rInner + " " + rInner + " 0 " + largeArc + " 0 " + xi2 + " " + yi2 + " Z";
      var p = el("path", { d: path, fill: color, stroke: "#fff", "stroke-width": 2 });
      svg.appendChild(p);
      bindHover(p, function () {
        return "<strong>" + escapeHtml(d.label) + "</strong><br>" + pct1(d.pct) + " (" + d.n + " / " + d.d + ")";
      });

      var midAngle = (startAngle + endAngle) / 2;
      var lx = cx + (r + rInner) / 2 * Math.cos(midAngle);
      var ly = cy + (r + rInner) / 2 * Math.sin(midAngle);
      var lines = wrapLabel(d.label, r * 1.1, 12);
      lines.forEach(function (line, li) {
        svg.appendChild(text(lx, ly + li * 13 - (lines.length - 1) * 6.5, line,
          { "font-size": 11.5, fill: "#fff", "text-anchor": "middle", "font-weight": 600 }));
      });
      svg.appendChild(text(lx, ly + lines.length * 13 - (lines.length - 1) * 6.5,
        d.n + " 人（" + pct0(d.pct) + "）",
        { "font-size": 10.5, fill: "#fff", "text-anchor": "middle" }));

      startAngle = endAngle;
    });
    appendCaption(container, fig.denomNote);
  }

  // ---------------------------------------------------------------- diverging (fig06)
  function renderDiverging(container, fig) {
    var W = chartWidth(container);
    var labelFS = 12, valueFS = 11;
    var barBandH = 16, rowH = labelFS + 6 + barBandH + 10;
    var panelGap = 28, headH = 24;
    var midX = W * 0.42;
    var edgePad = 4;
    var maxAbs = 0;
    fig.panels.forEach(function (p) {
      p.items.forEach(function (it) { maxAbs = Math.max(maxAbs, Math.abs(it.diffPts)); });
    });
    var scale = (Math.min(midX, W - midX) - 14) / (maxAbs * 1.15 || 1);

    var headLinesByPanel = fig.panels.map(function (p) {
      var nUp = p.items.filter(function (it) { return it.diffPts > 0; }).length;
      return wrapLabel(p.group + "（" + p.d + " 人）　" + nUp + " 個高於全體、" +
        (p.items.length - nUp) + " 個低於全體", W - 8, 12.5);
    });
    var panelHeights = fig.panels.map(function (p, pi) {
      return headH + (headLinesByPanel[pi].length - 1) * 15 + p.items.length * rowH + 8;
    });
    var H = panelHeights.reduce(function (a, b) { return a + b + panelGap; }, 0) + 10;
    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);

    var y = 8;
    fig.panels.forEach(function (p, pi) {
      var headLines = headLinesByPanel[pi];
      headLines.forEach(function (line, li) {
        svg.appendChild(text(4, y + 14 + li * 15, line,
          { "font-size": 12.5, fill: "#0b0b0b", "font-weight": 700 }));
      });
      var rowY = y + headH + (headLines.length - 1) * 15;
      svg.appendChild(el("line", {
        x1: midX, x2: midX, y1: rowY - 4, y2: rowY + p.items.length * rowH,
        stroke: "#0b0b0b", "stroke-width": 1,
      }));
      p.items.forEach(function (it, ri) {
        var rTop = rowY + ri * rowH;
        svg.appendChild(text(midX, rTop + labelFS, it.label,
          { "font-size": labelFS, fill: "#2a2a28", "text-anchor": "middle" }));

        var barY = rTop + labelFS + 6;
        var barW = Math.abs(it.diffPts) * scale;
        var isUp = it.diffPts > 0;
        var x = isUp ? midX : midX - barW;
        var rect = el("rect", {
          x: x, y: barY, width: barW, height: barBandH,
          fill: isUp ? PAL.accent : "#b9d0ed",
        });
        svg.appendChild(rect);

        var valLabel = pct0(it.groupPct) + "（" + it.n + "/" + it.d + "）";
        var valW = measureText(valLabel, valueFS);
        var outsideX = isUp ? x + barW + 6 : x - 6;
        var fitsOutside = isUp
          ? (outsideX + valW <= W - edgePad)
          : (outsideX - valW >= edgePad);
        var valX, anchor, color;
        if (fitsOutside) {
          valX = outsideX; anchor = isUp ? "start" : "end"; color = "#52514e";
        } else {
          // 空間不夠時把數值標籤搬進色塊裡，避免超出畫布被裁掉
          valX = isUp ? x + barW - 5 : x + 5; anchor = isUp ? "end" : "start"; color = "#ffffff";
        }
        svg.appendChild(text(valX, barY + barBandH - 3, valLabel,
          { "font-size": valueFS, fill: color, "text-anchor": anchor }));

        var hit = el("rect", { x: 0, y: rTop, width: W, height: rowH, fill: "transparent" });
        bindHover(hit, function () {
          return "<strong>" + escapeHtml(p.group) + " / " + escapeHtml(it.label) + "</strong><br>" +
            "群內：" + pct1(it.groupPct) + " (" + it.n + "/" + it.d + ")　全體：" + pct1(it.basePct) +
            "　" + (isUp ? "高出" : "低了") + " " + Math.abs(Math.round(it.diffPts)) + " 個百分點";
        });
        svg.appendChild(hit);
      });
      y += panelHeights[pi] + panelGap;
    });
    appendCaption(container, fig.denomNote);
  }

  // ---------------------------------------------------------------- scatter-kano
  function kanoPlot(svg, x0, y0, size, items, fontScale) {
    fontScale = fontScale || 1;
    var pad = 34 * fontScale;
    var plotSize = size - pad * 1.6;
    function px(si) { return x0 + pad + si * plotSize; }
    function py(dsi) { return y0 + pad * 0.6 + (-dsi) * plotSize; }

    svg.appendChild(el("rect", {
      x: x0, y: y0, width: size, height: size, fill: "none",
      stroke: PAL.grid, "stroke-width": 1,
    }));
    // 分界線
    svg.appendChild(el("line", { x1: px(0.5), x2: px(0.5), y1: py(0), y2: py(-1), stroke: PAL.neutral, "stroke-dasharray": "3,3" }));
    svg.appendChild(el("line", { x1: px(0), x2: px(1), y1: py(-0.5), y2: py(-0.5), stroke: PAL.neutral, "stroke-dasharray": "3,3" }));
    var qFS = 11 * fontScale;
    svg.appendChild(text(px(0) + 2, py(0) - 4, "無差別", { "font-size": qFS, fill: "#a8a8a2" }));
    svg.appendChild(text(px(1) - 2, py(0) - 4, "魅力", { "font-size": qFS, fill: "#a8a8a2", "text-anchor": "end" }));
    svg.appendChild(text(px(0) + 2, py(-1) + qFS, "基本", { "font-size": qFS, fill: "#a8a8a2" }));
    svg.appendChild(text(px(1) - 2, py(-1) + qFS, "期望", { "font-size": qFS, fill: "#a8a8a2", "text-anchor": "end" }));

    items.forEach(function (it) {
      var cx = px(it.si), cy = py(it.dsi);
      var c = el("circle", { cx: cx, cy: cy, r: 7 * fontScale, fill: it.color || PAL.primary, stroke: "#fff", "stroke-width": 1.5 });
      svg.appendChild(c);
      svg.appendChild(text(cx, cy + 3.5 * fontScale, it.num,
        { "font-size": 9 * fontScale, fill: "#fff", "text-anchor": "middle", "font-weight": 700 }));
      var hit = el("circle", { cx: cx, cy: cy, r: 14 * fontScale, fill: "transparent" });
      bindHover(hit, function () {
        return "<strong>" + it.num + " " + escapeHtml(it.fullLabel) + "</strong><br>" +
          "SI " + it.si.toFixed(2) + "　DSI " + it.dsi.toFixed(2) + "　" + it.quadrant;
      });
      svg.appendChild(hit);
    });
  }

  function renderScatterKano(container, fig) {
    var W = chartWidth(container);
    var size = Math.min(W, 480);
    var legendH = fig.items.length * 16 + 10;
    var H = size + legendH + 20;
    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);
    kanoPlot(svg, (W - size) / 2, 4, size, fig.items);
    var ly = size + 22;
    fig.items.forEach(function (it) {
      svg.appendChild(text(4, ly, it.num + " " + it.label + "　(" + it.si.toFixed(2) + ", " + it.dsi.toFixed(2) + ")",
        { "font-size": 12, fill: "#52514e" }));
      ly += 16;
    });
    appendCaption(container, fig.denomNote);
  }

  function renderScatterKanoPanels(container, fig) {
    var W = chartWidth(container);
    var perRow = W >= 600 ? 3 : 1;
    var panelSize = perRow === 3 ? (W - 24) / 3 : Math.min(W, 380);
    var fontScale = perRow === 3 ? 0.82 : 1;
    var rows = Math.ceil(fig.panels.length / perRow);
    var panelH = panelSize + 24;
    var legendEntries = fig.legend.map(function (l) {
      return { text: l.num + " " + l.label, w: measureText(l.num + " " + l.label, 11) + 18 };
    });
    var legendLines = wrapFlow(legendEntries, W - 8);
    var legendH = legendLines.length * 16 + 12;
    var H = rows * panelH + legendH + 10;
    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);

    fig.panels.forEach(function (p, i) {
      var col = i % perRow, row = Math.floor(i / perRow);
      var x0 = col * (panelSize + 12), y0 = row * panelH + 20;
      svg.appendChild(text(x0 + 4, y0 - 4,
        LAYER_PLAIN[p.layer] || p.layer, { "font-size": 12, fill: "#0b0b0b", "font-weight": 700 }));
      svg.appendChild(text(x0 + panelSize - 4, y0 - 4, p.n + " 人",
        { "font-size": 11, fill: "#52514e", "text-anchor": "end" }));
      var colored = p.items.map(function (it) {
        return Object.assign({}, it, { color: PAL.layers[p.layer] });
      });
      kanoPlot(svg, x0, y0, panelSize, colored, fontScale);
    });

    legendLines.forEach(function (line, li) {
      var lx = 4, ly = rows * panelH + 18 + li * 16;
      line.forEach(function (entry) {
        svg.appendChild(text(lx, ly, entry.text, { "font-size": 11, fill: "#52514e" }));
        lx += entry.w;
      });
    });
    appendCaption(container, fig.denomNote);
  }

  // ---------------------------------------------------------------- grouped-hbar-layers（含分群切換）
  function renderGroupedLayers(container, fig, activeLayer) {
    var W = chartWidth(container);
    var labelFS = 12.5, valueFS = 10.5;
    var leftPad = 4, rightPad = 60;
    var barMaxW = W - leftPad - rightPad;

    var mode = activeLayer || "all";
    var options = fig.options.slice();

    if (mode !== "all") {
      options.sort(function (a, b) {
        return (b.byLayer[mode] ? b.byLayer[mode].pct : 0) - (a.byLayer[mode] ? a.byLayer[mode].pct : 0);
      });
    }

    var subBarH = 12, subGap = 2, groupGap = 10, labelGap = 4;
    var nSeries = mode === "all" ? LAYER_ORDER.length : 1;
    var groupH = nSeries * (subBarH + subGap);

    var rowTops = [];
    var y = 8;
    options.forEach(function (o) {
      var lines = wrapLabel(o.label, W - leftPad - 4, labelFS);
      rowTops.push({ y: y, lines: lines });
      y += lines.length * (labelFS + 2) + labelGap + groupH + groupGap;
    });
    var legendEntries = LAYER_ORDER.map(function (layer) {
      var denom = fig.layerDenoms[layer];
      var lab = (LAYER_PLAIN[layer] || layer) + (denom ? "（" + denom + " 人）" : "");
      return { layer: layer, lab: lab, w: 15 + measureText(lab, 10.5) + 22 };
    });
    var legendLines = mode === "all" ? wrapFlow(legendEntries, W - leftPad) : [];
    var legendH = legendLines.length ? legendLines.length * 18 + 10 : 0;
    var H = y + legendH + 6;

    var svg = mountSVG(container, W, H, fig.title + "。" + fig.subtitle);
    var maxPct = 0;
    options.forEach(function (o) {
      (mode === "all" ? LAYER_ORDER : [mode]).forEach(function (layer) {
        if (o.byLayer[layer]) maxPct = Math.max(maxPct, o.byLayer[layer].pct);
      });
    });
    maxPct = maxPct || 1;

    options.forEach(function (o, oi) {
      var rt = rowTops[oi];
      var ly = rt.y;
      rt.lines.forEach(function (line) {
        svg.appendChild(text(leftPad, ly + labelFS, line,
          { "font-size": labelFS, fill: "#2a2a28", "font-weight": 500 }));
        ly += labelFS + 2;
      });
      var barY = ly + labelGap;
      var layers = mode === "all" ? LAYER_ORDER : [mode];
      layers.forEach(function (layer, li) {
        var d = o.byLayer[layer];
        var by = barY + li * (subBarH + subGap);
        if (!d) return;
        var bw = Math.max(2, (d.pct / maxPct) * barMaxW);
        var rect = el("rect", { x: leftPad, y: by, width: bw, height: subBarH, fill: PAL.layers[layer], rx: 2 });
        svg.appendChild(rect);
        svg.appendChild(text(leftPad + bw + 5, by + subBarH - 2, pct0(d.pct),
          { "font-size": valueFS, fill: "#52514e" }));
        var hit = el("rect", { x: 0, y: by, width: W, height: subBarH, fill: "transparent" });
        bindHover(hit, function () {
          return "<strong>" + escapeHtml(o.label) + "</strong><br>" +
            (LAYER_PLAIN[layer] || layer) + "：" + pct1(d.pct) + " (" + d.n + "/" + d.d + ")";
        });
        svg.appendChild(hit);
      });
      y = barY + groupH + groupGap;
    });

    legendLines.forEach(function (line, li) {
      var lx = leftPad, lyLegend = y + 14 + li * 18;
      line.forEach(function (entry) {
        var sw = el("rect", { x: lx, y: lyLegend - 10, width: 11, height: 11, fill: PAL.layers[entry.layer] });
        svg.appendChild(sw);
        svg.appendChild(text(lx + 15, lyLegend, entry.lab, { "font-size": 10.5, fill: "#52514e" }));
        lx += entry.w;
      });
    });
    appendCaption(container, fig.denomNote);
  }

  // 依可用寬度把一排項目換行；items 需附 w（該項目含間距的佔用寬度）
  function wrapFlow(items, maxWidth) {
    var lines = [[]], widths = [0];
    items.forEach(function (it) {
      var li = lines.length - 1;
      if (widths[li] > 0 && widths[li] + it.w > maxWidth) {
        lines.push([]); widths.push(0); li++;
      }
      lines[li].push(it);
      widths[li] += it.w;
    });
    return lines;
  }

  // ---------------------------------------------------------------- 數據表（C3：每張圖可展開看數據）
  function buildDataTable(fig) {
    var det = document.createElement("details");
    det.className = "data-table-toggle";
    var sum = document.createElement("summary");
    sum.textContent = "看數據表";
    det.appendChild(sum);
    var wrap = document.createElement("div");
    wrap.className = "table-wrap";
    var table = document.createElement("table");

    function rowsFromItems(headers, rowsArr) {
      var thead = document.createElement("thead");
      var tr = document.createElement("tr");
      headers.forEach(function (h) {
        var th = document.createElement("th"); th.textContent = h; tr.appendChild(th);
      });
      thead.appendChild(tr);
      table.appendChild(thead);
      var tbody = document.createElement("tbody");
      rowsArr.forEach(function (r) {
        var row = document.createElement("tr");
        r.forEach(function (v) {
          var td = document.createElement("td"); td.textContent = v; row.appendChild(td);
        });
        tbody.appendChild(row);
      });
      table.appendChild(tbody);
    }

    if (fig.type === "hbar" || fig.type === "donut") {
      rowsFromItems(["選項", "比例", "分子", "分母"], fig.items.map(function (d) {
        return [d.label, pct1(d.pct), d.n, d.d];
      }));
    } else if (fig.type === "stacked-hbar") {
      rowsFromItems(["困難", "3分以上", "4分以上", "分母"], fig.items.map(function (d) {
        return [d.label, pct1(d.pct3plus) + "（" + d.n3plus + "）", pct1(d.pct4plus) + "（" + d.n4plus + "）", d.d];
      }));
    } else if (fig.type === "diverging") {
      var out = [];
      fig.panels.forEach(function (p) {
        p.items.forEach(function (it) {
          out.push([p.group, it.label, pct1(it.groupPct), pct1(it.basePct), (it.diffPts > 0 ? "+" : "") + it.diffPts.toFixed(1)]);
        });
      });
      rowsFromItems(["世代", "動機", "群內比例", "全體比例", "差幾個百分點"], out);
    } else if (fig.type === "scatter-kano") {
      rowsFromItems(["主題", "SI", "DSI", "落點"], fig.items.map(function (it) {
        return [it.num + " " + it.fullLabel, it.si.toFixed(3), it.dsi.toFixed(3), it.quadrant];
      }));
    } else if (fig.type === "scatter-kano-panels") {
      var out2 = [];
      fig.panels.forEach(function (p) {
        p.items.forEach(function (it) {
          out2.push([LAYER_PLAIN[p.layer] || p.layer, it.num + " " + it.fullLabel, it.si.toFixed(3), it.dsi.toFixed(3), it.quadrant]);
        });
      });
      rowsFromItems(["分群", "主題", "SI", "DSI", "落點"], out2);
    } else if (fig.type === "grouped-hbar-layers") {
      var out3 = [];
      fig.options.forEach(function (o) {
        LAYER_ORDER.forEach(function (layer) {
          var d = o.byLayer[layer];
          if (d) out3.push([o.label, LAYER_PLAIN[layer] || layer, pct1(d.pct), d.n, d.d]);
        });
      });
      rowsFromItems(["選項", "分群", "比例", "分子", "分母"], out3);
    }
    wrap.appendChild(table);
    det.appendChild(wrap);
    return det;
  }

  // ---------------------------------------------------------------- caption / helpers
  function appendCaption(container, note) {
    if (!note) return;
    var cap = document.createElement("div");
    cap.className = "chart-note";
    cap.textContent = note;
    container.appendChild(cap);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // ---------------------------------------------------------------- 分群切換 UI
  function addLayerToggle(wrap, fig, renderFn, initialKey) {
    var bar = document.createElement("div");
    bar.className = "layer-toggle";
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", "切換分群檢視");
    var options = [{ key: "all", label: "三群並排" }].concat(
      LAYER_ORDER.map(function (l) { return { key: l, label: "只看：" + (LAYER_PLAIN[l] || l) }; })
    );
    var chartDiv = document.createElement("div");
    var active = initialKey || "all";
    options.forEach(function (opt) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = opt.label;
      btn.className = "layer-toggle-btn" + (opt.key === active ? " active" : "");
      btn.addEventListener("click", function () {
        Array.prototype.forEach.call(bar.children, function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        wrap.dataset.activeLayer = opt.key;
        renderFn(chartDiv, fig, opt.key);
      });
      bar.appendChild(btn);
    });
    wrap.appendChild(bar);
    wrap.appendChild(chartDiv);
    renderFn(chartDiv, fig, active);
    return chartDiv;
  }

  // ---------------------------------------------------------------- 主入口
  var RENDERERS = {
    "hbar": renderHbar,
    "stacked-hbar": renderStackedHbar,
    "donut": renderDonut,
    "diverging": renderDiverging,
    "scatter-kano": renderScatterKano,
    "scatter-kano-panels": renderScatterKanoPanels,
  };

  function prependHeader(container, fig) {
    var h = document.createElement("h4");
    h.className = "chart-title";
    h.textContent = fig.title;
    var sub = document.createElement("div");
    sub.className = "chart-subtitle";
    sub.textContent = fig.subtitle;
    container.appendChild(h);
    container.appendChild(sub);
  }

  function renderOne(container) {
    var key = container.getAttribute("data-chart");
    var fig = window.FIGDATA.figures[key];
    if (!fig) {
      container.textContent = "（找不到圖表資料：" + key + "）";
      return;
    }
    container.innerHTML = "";
    prependHeader(container, fig);
    if (fig.type === "grouped-hbar-layers") {
      var keepLayer = container.dataset.activeLayer || "all";
      addLayerToggle(container, fig, renderGroupedLayers, keepLayer);
      container.appendChild(buildDataTable(fig));
      return;
    }
    var fn = RENDERERS[fig.type];
    if (!fn) {
      var msg = document.createElement("p");
      msg.textContent = "（不支援的圖表類型：" + fig.type + "）";
      container.appendChild(msg);
      return;
    }
    var chartDiv = document.createElement("div");
    container.appendChild(chartDiv);
    fn(chartDiv, fig);
    container.appendChild(buildDataTable(fig));
  }

  function renderAll() {
    var containers = document.querySelectorAll("[data-chart]");
    containers.forEach(renderOne);
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      clearTimeout(t);
      var args = arguments;
      t = setTimeout(function () { fn.apply(null, args); }, ms);
    };
  }

  window.ChartKit = { renderAll: renderAll };

  document.addEventListener("DOMContentLoaded", renderAll);
  window.addEventListener("resize", debounce(renderAll, 250));
})();
