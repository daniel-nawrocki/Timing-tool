const state = { holes: [], rows: [], activeRowId: null, options: [], selectedOption: null };
const palette = ['#175cd3', '#16a34a', '#dc6803', '#7a5af8', '#087443', '#c11574', '#344054', '#0e7090'];

const plot = document.getElementById('plot');
const statusEl = document.getElementById('status');
const activeRowEl = document.getElementById('activeRow');
const startFromPrevEl = document.getElementById('startFromPrev');
const optionSelectEl = document.getElementById('optionSelect');

const rowColor = (id) => palette[(id - 1) % palette.length];
const setStatus = (v) => statusEl.textContent = typeof v === 'string' ? v : JSON.stringify(v, null, 2);
const getActiveRow = () => state.rows.find((r) => r.row_id === Number(state.activeRowId));
const holeRow = (id) => state.rows.find((r) => r.hole_ids.includes(id));
const getDelay = (id) => state.selectedOption?.timing.find((t) => t.hole_id === id)?.delay_ms;

function renderRowDropdown() {
  activeRowEl.innerHTML = state.rows.map((r) => `<option value="${r.row_id}">Row ${r.row_id}</option>`).join('');
  if (state.activeRowId) activeRowEl.value = state.activeRowId;
}

function addRow() {
  const nextId = state.rows.length + 1;
  state.rows.push({ row_id: nextId, hole_ids: [], start_from_prev_hole: 1 });
  state.activeRowId = nextId;
  renderRowDropdown();
  renderPlot();
}

function assignHoles(ids) {
  const row = getActiveRow();
  if (!row) return;
  state.rows.forEach((r) => { r.hole_ids = r.hole_ids.filter((id) => !ids.includes(id)); });
  ids.forEach((id) => { if (!row.hole_ids.includes(id)) row.hole_ids.push(id); });
  row.start_from_prev_hole = Number(startFromPrevEl.value || 1);
  renderPlot();
}

function getBounds() {
  const xs = state.holes.map((h) => h.x), ys = state.holes.map((h) => h.y);
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
}

function toSvgPoint(x, y, b) {
  const W = 900, H = 650, pad = 40;
  return {
    x: pad + ((x - b.minX) / ((b.maxX - b.minX) || 1)) * (W - pad * 2),
    y: H - (pad + ((y - b.minY) / ((b.maxY - b.minY) || 1)) * (H - pad * 2)),
  };
}

function renderPlot() {
  plot.innerHTML = '';
  if (!state.holes.length) return;
  const b = getBounds();

  state.holes.forEach((h) => {
    const p = toSvgPoint(h.x, h.y, b);
    const row = holeRow(h.id);
    const delay = getDelay(h.id);

    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x);
    c.setAttribute('cy', p.y);
    c.setAttribute('r', 7);
    c.setAttribute('class', `hole ${row ? '' : 'unassigned'}`);
    c.setAttribute('fill', row ? rowColor(row.row_id) : '#d0d5dd');
    c.addEventListener('click', () => assignHoles([h.id]));

    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', p.x + 10);
    t.setAttribute('y', p.y - 8);
    t.setAttribute('font-size', '11');
    t.textContent = delay === undefined ? h.id : `${h.id} (${delay}ms)`;

    plot.append(c, t);
  });
}

function renderOptionSelect() {
  optionSelectEl.innerHTML = state.options.map((opt, i) => {
    const m = opt.metrics;
    return `<option value="${i}">Opt ${opt.option_id}: HH ${opt.hole_to_hole_ms} / RR ${opt.row_to_row_ms} / Max(8ms) ${m.max_holes_per_8ms}</option>`;
  }).join('');

  if (state.options.length) {
    optionSelectEl.value = '0';
    state.selectedOption = state.options[0];
  }
  renderPlot();
}

function summaryRows(option) {
  const m = option.metrics;
  return [
    { section: 'timings', name: 'row_1_hole_to_hole_ms', value: option.hole_to_hole_ms },
    { section: 'timings', name: 'row_2_row_to_row_ms', value: option.row_to_row_ms },
    { section: 'timings', name: 'row_3_max_holes_per_8ms', value: m.max_holes_per_8ms },
    ...m.holes_per_8ms.map((w) => ({ section: 'holes_per_8ms', name: `${w.window_start_ms}-${w.window_end_ms}`, value: w.hole_count })),
  ];
}

async function upload(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/upload', { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Upload failed');

  state.holes = data.holes;
  state.rows = [];
  state.options = [];
  state.selectedOption = null;
  document.getElementById('exportBtn').disabled = true;
  addRow();
  setStatus({ uploaded: data.count });
}

async function optimize() {
  const payload = {
    holes: state.holes,
    rows: state.rows,
    constraints: {
      hole_to_hole_min: Number(document.getElementById('hmin').value),
      hole_to_hole_max: Number(document.getElementById('hmax').value),
      row_to_row_min: Number(document.getElementById('rmin').value),
      row_to_row_max: Number(document.getElementById('rmax').value),
    },
  };
  const res = await fetch('/api/optimize', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Optimize failed');

  state.options = data.options || [];
  renderOptionSelect();
  document.getElementById('exportBtn').disabled = state.options.length === 0;
  setStatus(data.metrics);
}

async function exportCsv() {
  if (!state.selectedOption) return;
  const payload = {
    timing: state.selectedOption.timing,
    summary: summaryRows(state.selectedOption),
  };
  const res = await fetch('/api/export', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Export failed');

  const blob = new Blob([data.csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'timing-results.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function rectToSvg(evt) {
  const rect = plot.getBoundingClientRect();
  return { x: ((evt.clientX - rect.left) / rect.width) * 900, y: ((evt.clientY - rect.top) / rect.height) * 650 };
}

let drag = null;
plot.addEventListener('mousedown', (e) => {
  if (!state.holes.length) return;
  drag = { start: rectToSvg(e) };
  const box = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  box.id = 'selection-box';
  box.setAttribute('class', 'selection');
  plot.appendChild(box);
});
plot.addEventListener('mousemove', (e) => {
  if (!drag) return;
  drag.end = rectToSvg(e);
  const x = Math.min(drag.start.x, drag.end.x), y = Math.min(drag.start.y, drag.end.y);
  const w = Math.abs(drag.end.x - drag.start.x), h = Math.abs(drag.end.y - drag.start.y);
  const box = document.getElementById('selection-box');
  if (box) { box.setAttribute('x', x); box.setAttribute('y', y); box.setAttribute('width', w); box.setAttribute('height', h); }
});
plot.addEventListener('mouseup', () => {
  if (!drag || !drag.end) { drag = null; document.getElementById('selection-box')?.remove(); return; }
  const [x1, x2] = [Math.min(drag.start.x, drag.end.x), Math.max(drag.start.x, drag.end.x)];
  const [y1, y2] = [Math.min(drag.start.y, drag.end.y), Math.max(drag.start.y, drag.end.y)];
  const b = getBounds();
  const ids = state.holes.filter((h) => {
    const p = toSvgPoint(h.x, h.y, b);
    return p.x >= x1 && p.x <= x2 && p.y >= y1 && p.y <= y2;
  }).map((h) => h.id);
  if (ids.length) assignHoles(ids);
  drag = null;
  document.getElementById('selection-box')?.remove();
});

document.getElementById('csvFile').addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  try { await upload(file); } catch (err) { setStatus(err.message); }
});
document.getElementById('newRowBtn').addEventListener('click', addRow);
activeRowEl.addEventListener('change', () => {
  state.activeRowId = Number(activeRowEl.value);
  startFromPrevEl.value = getActiveRow()?.start_from_prev_hole || 1;
});
startFromPrevEl.addEventListener('change', () => {
  const row = getActiveRow();
  if (row) row.start_from_prev_hole = Number(startFromPrevEl.value || 1);
});
optionSelectEl.addEventListener('change', () => {
  state.selectedOption = state.options[Number(optionSelectEl.value)] || null;
  if (state.selectedOption) setStatus(state.selectedOption.metrics);
  renderPlot();
});

document.getElementById('optimizeBtn').addEventListener('click', async () => { try { await optimize(); } catch (err) { setStatus(err.message); } });
document.getElementById('exportBtn').addEventListener('click', async () => { try { await exportCsv(); } catch (err) { setStatus(err.message); } });