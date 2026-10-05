// 21_word_export.js — 由 21_word_export.py 注入網頁執行，不需要手動跑。
// 把網頁正文序列化成區塊清單（標題、段落、清單、表格、重點卡），圖表 SVG 轉成 PNG，
// 全部 POST 回本機伺服器，再由 21_word_export.py 組成 Word。
window.__export = async function (prefix) {
  document.documentElement.setAttribute('data-theme', 'light');
  const blocks = [];
  const lang = document.documentElement.lang.startsWith('en') ? 'en' : 'zh';
  const BLOCK = new Set(['P', 'UL', 'OL', 'TABLE', 'H1', 'H2', 'H3', 'H4', 'DIV', 'SECTION', 'HEADER', 'DETAILS', 'FOOTER', 'LI', 'BLOCKQUOTE']);

  function runs(node, fmt = {}, out = []) {
    for (const n of node.childNodes) {
      if (n.nodeType === 3) {
        const t = n.textContent.replace(/\s+/g, ' ');
        if (t) out.push({ text: t, ...fmt });
      } else if (n.nodeType === 1) {
        if (n.getAttribute('aria-hidden') === 'true') continue;
        const tag = n.tagName;
        if (tag === 'BR') { out.push({ text: '\n', ...fmt }); continue; }
        if (BLOCK.has(tag)) continue;
        if (n.classList.contains('step-why')) out.push({ text: lang === 'en' ? ': ' : '：', ...fmt });   // 行動呼籲：連結與說明之間
        if (tag === 'A' && n.textContent.trim().startsWith('↩')) continue;   // 網頁專用的「回到正文」連結
        const f = { ...fmt };
        if (tag === 'STRONG' || tag === 'B') f.bold = true;
        if (tag === 'EM' || tag === 'I') f.italic = true;
        if (tag === 'SUP') f.sup = true;
        if (tag === 'A') { const h = n.getAttribute('href') || ''; if (h && !h.startsWith('#')) f.link = new URL(h, location.href).href.replace(location.origin, 'https://report.claire-cheng.com'); }
        runs(n, f, out);
      }
    }
    return out;
  }
  function trim(rs) {
    rs = rs.filter(r => r.text !== '');
    if (rs.length) { rs[0].text = rs[0].text.replace(/^\s+/, ''); rs[rs.length - 1].text = rs[rs.length - 1].text.replace(/\s+$/, ''); }
    return rs.filter(r => r.text !== '');
  }
  const emit = (b) => { if (b.runs) { b.runs = trim(b.runs); if (!b.runs.length) return; } blocks.push(b); };

  async function list(el, depth) {
    const ordered = el.tagName === 'OL';
    for (const li of el.children) {
      emit({ t: 'li', ordered, depth, runs: runs(li) });
      for (const c of li.children) if (BLOCK.has(c.tagName)) await walk(c, depth + 1);
    }
  }
  function table(t) {
    const rows = [...t.querySelectorAll('tr')].map(tr => [...tr.children].map(td => trim(runs(td))));
    const cap = t.querySelector('caption');
    blocks.push({ t: 'table', header: !!t.querySelector('thead'), caption: cap ? trim(runs(cap)) : [], rows });
  }
  async function chart(b) {
    const name = b.dataset.chart;
    const svg = b.querySelector('svg');
    const vb = svg.viewBox.baseVal;
    const clone = svg.cloneNode(true);
    const src = svg.querySelectorAll('*'), dst = clone.querySelectorAll('*');
    const PROPS = ['fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'opacity', 'fill-opacity', 'font-family', 'font-size', 'font-weight', 'text-anchor', 'dominant-baseline'];
    src.forEach((e, i) => { const cs = getComputedStyle(e); PROPS.forEach(p => { const v = cs.getPropertyValue(p); if (v) dst[i].style.setProperty(p, v); }); dst[i].style.cursor = ''; });
    clone.querySelectorAll('title').forEach(x => x.remove());
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', vb.width); clone.setAttribute('height', vb.height);
    const scale = 3;
    const img = new Image();
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(clone));
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = vb.width * scale; cv.height = vb.height * scale;
    const ctx = cv.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.drawImage(img, 0, 0, cv.width, cv.height);
    const file = `${prefix}_${name}.png`;
    await fetch('/' + file, { method: 'POST', body: cv.toDataURL('image/png') });
    const note = b.querySelector('.chart-note');
    blocks.push({ t: 'img', file, w: vb.width, h: vb.height,
      title: trim(runs(b.querySelector('.chart-title'))), subtitle: trim(runs(b.querySelector('.chart-subtitle'))),
      note: note ? trim(runs(note)) : [] });
  }
  async function persona(sec) {
    for (const c of sec.children) if (/^H\d$|^P$/.test(c.tagName)) await walk(c);
    for (const btn of sec.querySelectorAll('.persona-btn')) {
      btn.click();
      emit({ t: 'p', style: 'bold', runs: [{ text: btn.textContent.replace(/^[^\p{L}\p{N}"']+/u, ''), bold: true }] });
      for (const c of sec.querySelector('.persona-result').childNodes) {
        if (c.nodeType === 3 && c.textContent.trim()) emit({ t: 'p', runs: [{ text: c.textContent.trim() }] });
        else if (c.nodeType === 1) await walk(c);
      }
    }
  }

  async function walk(el, depth = 0) {
    const tag = el.tagName, cls = el.classList;
    if (el.getAttribute('aria-hidden') === 'true') return;
    if (cls.contains('download-row') || cls.contains('cover-illo') || cls.contains('cover-stats') || cls.contains('lang-toggle') || cls.contains('layer-toggle') || cls.contains('data-table-toggle')) return;
    if (cls.contains('chart-block')) return chart(el);
    if (cls.contains('persona-picker')) return persona(el);
    if (cls.contains('insight-card')) {
      return emit({ t: 'callout', label: el.querySelector('.insight-label')?.textContent.trim() || '', runs: runs(el.querySelector('.insight-text')) });
    }
    if (/^H[1-4]$/.test(tag)) return emit({ t: 'h', level: +tag[1], part: cls.contains('part-title'), runs: runs(el) });
    if (tag === 'P') return emit({ t: 'p', cls: el.className, fn: /^fn\d/.test(el.id), runs: runs(el) });
    if (tag === 'UL' || tag === 'OL') return list(el, depth);
    if (tag === 'TABLE') return table(el);
    if (tag === 'SUMMARY') return;
    for (const c of el.children) await walk(c, depth);
  }

  const root = document.querySelector('#main .content') || document.querySelector('main');
  await walk(root);
  await fetch('/' + prefix + '_blocks.json', { method: 'POST', body: JSON.stringify(blocks) });
  return blocks.length;
};

// 網址帶 ?export=summary 或 ?export=full 時，頁面載入完自動匯出，完成後通知伺服器
window.addEventListener('load', async () => {
  const m = location.search.match(/export=(\w+)/);
  if (!m) return;
  await new Promise(r => setTimeout(r, 500));
  try {
    await window.__export(m[1]);
    await fetch('/__done', { method: 'POST', body: 'ok' });
  } catch (e) {
    await fetch('/__done', { method: 'POST', body: 'ERROR ' + e });
  }
});
