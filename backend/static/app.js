const state = { holes: [], rows: [], activeRowId: null, timing: null };
const palette = ['#175cd3','#16a34a','#dc6803','#7a5af8','#087443','#c11574','#344054','#0e7090'];

const plot = document.getElementById('plot');
const statusEl = document.getElementById('status');
const activeRowEl = document.getElementById('activeRow');
const startFromPrevEl = document.getElementById('startFromPrev');

function setStatus(v){ statusEl.textContent = typeof v === 'string' ? v : JSON.stringify(v, null, 2); }
function rowColor(id){ return palette[(id - 1) % palette.length]; }
function getActiveRow(){ return state.rows.find(r => r.row_id === Number(state.activeRowId)); }
function holeRow(id){ return state.rows.find(r => r.hole_ids.includes(id)); }

function renderLegend(){
  document.getElementById('legend').innerHTML = state.rows.map(
    r => `<span class="swatch"><i style="background:${rowColor(r.row_id)}"></i>Row ${r.row_id} (${r.hole_ids.length})</span>`
  ).join('');
}
function renderRowDropdown(){
  activeRowEl.innerHTML = state.rows.map(r => `<option value="${r.row_id}">Row ${r.row_id}</option>`).join('');
  if (state.activeRowId) activeRowEl.value = state.activeRowId;
  renderLegend();
}
function addRow(){
  const id = state.rows.length + 1;
  state.rows.push({ row_id:id, hole_ids:[], start_from_prev_hole:1 });
  state.activeRowId = id;
  renderRowDropdown();
  renderPlot();
}
function assignHolesToActive(ids){
  const row = getActiveRow();
  if (!row) return;
  state.rows.forEach(r => r.hole_ids = r.hole_ids.filter(id => !ids.includes(id)));
  ids.forEach(id => { if (!row.hole_ids.includes(id)) row.hole_ids.push(id); });
  row.start_from_prev_hole = Number(startFromPrevEl.value || 1);
  renderPlot(); renderLegend();
}
function getBounds(){
  const xs = state.holes.map(h => h.x), ys = state.holes.map(h => h.y);
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
}
function toSvgPoint(x,y,b){
  const W=900,H=650,pad=40;
  const nx=(x-b.minX)/((b.maxX-b.minX)||1), ny=(y-b.minY)/((b.maxY-b.minY)||1);
  return { x: pad + nx*(W-pad*2), y: H-(pad+ny*(H-pad*2)) };
}
function renderPlot(){
  plot.innerHTML = '';
  if (!state.holes.length) return;
  const b = getBounds();
  state.holes.forEach(h => {
    const p = toSvgPoint(h.x,h.y,b), r = holeRow(h.id);
    const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx',p.x); c.setAttribute('cy',p.y); c.setAttribute('r',7);
    c.setAttribute('class',`hole ${r?'':'unassigned'}`);
    c.setAttribute('fill', r ? rowColor(r.row_id) : '#d0d5dd');
    c.addEventListener('click',()=>assignHolesToActive([h.id]));
    const t = document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x',p.x+9); t.setAttribute('y',p.y-9); t.setAttribute('font-size','11'); t.textContent=h.id;
    plot.appendChild(c); plot.appendChild(t);
  });
}

function clientRectToSvg(evt){
  const rect = plot.getBoundingClientRect();
  return { x: ((evt.clientX-rect.left)/rect.width)*900, y: ((evt.clientY-rect.top)/rect.height)*650 };
}
let drag=null;
plot.addEventListener('mousedown',(e)=>{ if(!state.holes.length) return; drag={start:clientRectToSvg(e)}; const box=document.createElementNS('http://www.w3.org/2000/svg','rect'); box.id='selection-box'; box.setAttribute('class','selection'); plot.appendChild(box); });
plot.addEventListener('mousemove',(e)=>{ if(!drag) return; drag.end=clientRectToSvg(e); const x=Math.min(drag.start.x,drag.end.x), y=Math.min(drag.start.y,drag.end.y), w=Math.abs(drag.end.x-drag.start.x), h=Math.abs(drag.end.y-drag.start.y); const box=document.getElementById('selection-box'); if(box){ box.setAttribute('x',x); box.setAttribute('y',y); box.setAttribute('width',w); box.setAttribute('height',h);} });
plot.addEventListener('mouseup',()=>{ if(!drag || !drag.end){ drag=null; document.getElementById('selection-box')?.remove(); return; } const x1=Math.min(drag.start.x,drag.end.x), x2=Math.max(drag.start.x,drag.end.x), y1=Math.min(drag.start.y,drag.end.y), y2=Math.max(drag.start.y,drag.end.y); const b=getBounds(); const selected=state.holes.filter(h=>{ const p=toSvgPoint(h.x,h.y,b); return p.x>=x1&&p.x<=x2&&p.y>=y1&&p.y<=y2; }).map(h=>h.id); if(selected.length) assignHolesToActive(selected); drag=null; document.getElementById('selection-box')?.remove(); });

async function uploadCsv(file){
  const fd = new FormData(); fd.append('file', file);
  const res = await fetch('/api/upload', { method:'POST', body:fd });
  const data = await res.json(); if(!res.ok) throw new Error(data.error || 'Upload failed');
  state.holes=data.holes; state.rows=[]; state.timing=null; document.getElementById('exportBtn').disabled=true;
  addRow(); renderPlot(); setStatus({ message:'CSV uploaded', holeCount:data.count });
}
async function optimize(){
  const payload = {
    holes: state.holes,
    rows: state.rows.map(r => ({ ...r, start_from_prev_hole:Number(r.start_from_prev_hole || 1) })),
    constraints: {
      hole_to_hole_min:Number(document.getElementById('hmin').value),
      hole_to_hole_max:Number(document.getElementById('hmax').value),
      row_to_row_min:Number(document.getElementById('rmin').value),
      row_to_row_max:Number(document.getElementById('rmax').value),
    },
  };
  const res = await fetch('/api/optimize',{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
  const data = await res.json(); if(!res.ok) throw new Error(data.error || 'Optimize failed');
  state.timing = data.timing; document.getElementById('exportBtn').disabled=false; setStatus(data);
}
async function exportCsv(){
  const res = await fetch('/api/export',{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ timing:state.timing })});
  const data = await res.json(); if(!res.ok) throw new Error(data.error || 'Export failed');
  const blob = new Blob([data.csv], { type:'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='timing.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
}

document.getElementById('csvFile').addEventListener('change', async (e)=>{ const f=e.target.files[0]; if(!f) return; try{ await uploadCsv(f);}catch(err){ setStatus(err.message);} });
document.getElementById('newRowBtn').addEventListener('click', addRow);
activeRowEl.addEventListener('change',()=>{ state.activeRowId=Number(activeRowEl.value); const r=getActiveRow(); startFromPrevEl.value=r?.start_from_prev_hole || 1; });
startFromPrevEl.addEventListener('change',()=>{ const r=getActiveRow(); if(r) r.start_from_prev_hole=Number(startFromPrevEl.value || 1); });
document.getElementById('optimizeBtn').addEventListener('click', async ()=>{ try{ await optimize(); }catch(err){ setStatus(err.message);} });
document.getElementById('exportBtn').addEventListener('click', async ()=>{ try{ await exportCsv(); }catch(err){ setStatus(err.message);} });
