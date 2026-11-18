const CSRF = document.querySelector('meta[name=csrf]').content;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function renderTable(cols, rows) {
  if (!cols.length) return '';
  if (!rows.length) return '<p class="hint">(no rows returned)</p>';
  const head = cols.map(c => `<th>${esc(c)}</th>`).join('');
  const body = rows.map(r => '<tr>' + r.map(v => {
    const t = v === null ? '<span class="muted">NULL</span>' : esc(v);
    return String(v).includes('\n') ? `<td><pre>${esc(v)}</pre></td>` : `<td>${t}</td>`;
  }).join('') + '</tr>').join('');
  return `<div class="tablewrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderSteps(steps) {
  return steps.map(s => `
    <div class="step ${s.error ? 'bad' : ''}">
      <h5>${esc(s.label)}</h5>
      ${s.note ? `<div class="note">${esc(s.note)}</div>` : ''}
      ${s.sql ? `<pre>${esc(s.sql)}</pre>` : ''}
      ${s.error ? `<div class="err">${esc(s.error)}</div>` : ''}
      ${!s.error && s.rowcount !== null && !s.columns.length ? `<div class="hint">Rows affected: ${s.rowcount}</div>` : ''}
      ${renderTable(s.columns, s.rows)}
    </div>`).join('');
}

async function runDemo(key, params, out) {
  out.innerHTML = '<p class="hint">Executing statement inside MySQL 8.0...</p>';
  try {
    const r = await fetch('/api/concepts/run', {method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': CSRF},
      body: JSON.stringify({key, params})});
    const j = await r.json();
    out.innerHTML = j.error ? `<div class="err">${esc(j.error)}</div>` : renderSteps(j.steps);
  } catch (e) { out.innerHTML = `<div class="err">${esc(e)}</div>`; }
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-run]');
  if (!b) return;
  const box = b.closest('.demo');
  const params = {};
  box.querySelectorAll('[data-param]').forEach(i => params[i.dataset.param] = i.value);
  runDemo(b.dataset.run, params, box.querySelector('.out'));
});

document.querySelectorAll('.table-preview').forEach(el => {
  runDemo('table', {table: el.dataset.table}, el);
});
// Lazy "relevant table" panels: load when opened (and immediately if rendered open)
const loadTable = d => { if (d.open && !d.dataset.loaded) { d.dataset.loaded = 1; runDemo('table', {table: d.dataset.table}, d.querySelector('.tp')); } };
document.querySelectorAll('details.lazy').forEach(d => { d.addEventListener('toggle', () => loadTable(d)); loadTable(d); });

// Subscription form: only offer versions that belong to the chosen API
const apiSel = document.getElementById('sub-api'), verSel = document.getElementById('sub-ver');
if (apiSel && verSel) {
  const filter = () => { let first = null;
    [...verSel.options].forEach(o => { const ok = o.dataset.api === apiSel.value; o.hidden = !ok; if (ok && !first) first = o; });
    if (verSel.selectedOptions[0]?.hidden && first) verSel.value = first.value; };
  apiSel.addEventListener('change', filter); filter();
}
