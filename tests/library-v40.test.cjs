// v40: редактура библиотеки и переименование «Переходная игра» → «Переход в атаку».
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].split('\nrestoreDraft();')[0];

function app() {
  const node = { addEventListener() {} };
  const storage = new Map();
  const context = vm.createContext({
    window: node, document: { ...node, getElementById: () => node, querySelectorAll: () => [], querySelector: () => null }, navigator: {},
    confirm: () => true, clearTimeout() {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  return { run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')) };
}

test('library: 161 drills, stable ids, every drill in a known category, old category name gone', () => {
  const a = app();
  const r = a.read(`({ n: seedExercises.length, ids: new Set(seedExercises.map((e) => e.id)).size,
    unknown: seedExercises.filter((e) => !strokes.includes(e.stroke)).map((e) => e.id),
    old: seedExercises.filter((e) => e.stroke === 'Переходная игра').length,
    inList: strokes.includes('Переход в атаку') && !strokes.includes('Переходная игра'),
    renamed: seedExercises.filter((e) => e.stroke === 'Переход в атаку').map((e) => e.id).sort(),
    suggested: suggestedStroke('подход к сетке') })`);
  assert.equal(r.n, 161); assert.equal(r.ids, 161);
  assert.deepEqual(r.unknown, []); assert.equal(r.old, 0); assert.equal(r.inList, true);
  assert.deepEqual(r.renamed, ['kb25', 'kb26', 'kb27', 'kb28', 'tr01', 'tr02', 'tr03', 'tr04', 'tr05', 'tr06']);
  assert.equal(r.suggested, 'Переход в атаку');
});

test('saved data with the old category name is read under the new name; user edits are kept', () => {
  const a = app();
  const r = a.read(`(() => {
    const s = normalizeStore({
      customExercises: [{ id: 'my1', title: 'Мой подход', stroke: 'Переходная игра', brief: 'своё' }],
      exerciseOverrides: { tr01: { brief: 'Моё описание подхода', stroke: 'Переходная игра' } },
      plans: [{ id: 'p1', date: '2026-01-10', studentIds: [], sections: { main: [{ id: 'tr01', title: 'Подход', stroke: 'Переходная игра', minutes: 15 }], warmup: [], points: [], cooldown: [] } },
              { id: 'p2', date: '2026-01-11', studentIds: [], items: [{ id: 'kb25', title: 'Подход', stroke: 'Переходная игра' }] }]
    });
    store = s;
    return { custom: s.customExercises[0].stroke, ov: s.exerciseOverrides.tr01.stroke, plan: s.plans[0].sections.main[0].stroke,
      planTitle: s.plans[0].sections.main[0].title, legacy: s.plans[1].sections.main[0].stroke,
      merged: getEx('tr01').brief, mergedStroke: getEx('tr01').stroke, untouched: getEx('tr02').stroke };
  })()`);
  assert.deepEqual(r, { custom: 'Переход в атаку', ov: 'Переход в атаку', plan: 'Переход в атаку', planTitle: 'Подход', legacy: 'Переход в атаку',
    merged: 'Моё описание подхода', mergedStroke: 'Переход в атаку', untouched: 'Переход в атаку' });
});

test('pilot drills keep their choreography consistent with the text', () => {
  const a = app();
  const r = a.read(`['gs01', 'nt02', 'kb01'].map((id) => { const e = getEx(id), t = animDrillText(e); return [id, !!drillChoreo(e), /тренер/.test(t), /ученик/.test(t)]; })`);
  assert.deepEqual(r, [['gs01', true, true, true], ['nt02', true, true, true], ['kb01', true, true, true]]);
  assert.match(a.run(`getEx('gs01').setup`), /Тренер и ученик/);
});
