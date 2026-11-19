// v40: редактура библиотеки и переименование «Переходная игра» → «Переход в атаку».
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].split('\nrestoreDraft();')[0];

function app(storage = new Map()) {
  const node = { addEventListener() {} };
  const context = vm.createContext({
    window: node, document: { ...node, getElementById: () => node, querySelectorAll: () => [], querySelector: () => null }, navigator: {},
    confirm: () => true, clearTimeout() {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  return { storage, run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')) };
}


test('past plans need notes for the same date and participants; today, future and completed plans are excluded', () => {
  const a = app();
  a.run(`store.plans = [
    {id:'due',kind:'plan',status:'planned',date:'2026-11-17',studentIds:['demo1']},
    {id:'today',status:'planned',date:'2026-11-19',studentIds:['demo1']},
    {id:'future',status:'planned',date:'2026-11-20',studentIds:['demo1']},
    {id:'done',status:'done',date:'2026-11-17',studentIds:['demo1']},
    {id:'report',status:'planned',date:'2026-11-17',studentIds:['demo1'],summary:{success:'Глубина'}},
    {id:'group',status:'planned',date:'2026-11-16',groupIds:['demog1'],studentIds:[]},
    {id:'other-note',kind:'note',date:'2026-11-17',studentIds:['demo2'],notes:'Кросс'}
  ];`);
  assert.deepEqual(a.read("reportReminders('2026-11-19').map(p => p.id)"), ['due','group']);
  a.run("store.plans.push({id:'note',kind:'note',date:'2026-11-17',studentIds:['demo1'],notes:'Подача'})");
  assert.deepEqual(a.read("reportReminders('2026-11-19').map(p => p.id)"), ['group']);
  a.run("store.plans.push({id:'gnote',kind:'note',date:'2026-11-16',groupIds:['demog1'],studentIds:[],notes:'Воллей'})");
  assert.deepEqual(a.read("reportReminders('2026-11-19')"), []);
});

test('hidden reminders survive reload; opening preselects original date and group without modifying stored data', () => {
  const a = app();
  a.run(`renderKeepScroll = toast = () => {};
    store.plans=[{id:'due',date:'2026-11-17',status:'planned',studentIds:[],groupIds:['demog1']}];
    const before=JSON.stringify(store); let prefill;
    openNoteForm=opts => {prefill=opts.prefill};
    openReportReminder('due'); hideReportReminder('due');`);
  assert.equal(a.run('JSON.stringify(store)'), a.run('before'));
  assert.deepEqual(a.read('prefill.who.groupIds'), ['demog1']);
  assert.equal(a.run('prefill.date'), '2026-11-17');
  assert.deepEqual(a.read("reportReminders('2026-11-19')"), []);
  const b = app(a.storage);
  b.run("store.coachId=" + JSON.stringify(a.run('store.coachId')) + ";store.plans=" + JSON.stringify(a.read('store.plans')));
  assert.deepEqual(b.read("reportReminders('2026-11-19')"), []);
  b.run("store.plans[0].date='2026-11-18'");
  assert.equal(b.read("reportReminders('2026-11-19')").length, 1);
});

test('my exercises are grouped first without duplicates and keep filters; new templates appear first', () => {
  const a = app();
  a.run(`store.exerciseOverrides.gs01={title:'Мой кросс'};
    store.diagramOverrides.nt02=[];
    store.customExercises=[{...seedExercises[0],id:'my',title:'Моя разминка'}];`);
  const groups = a.read('groupExercises(allExercises()).map(([name,items]) => [name,items.map(e=>e.id)])');
  assert.equal(groups[0][0], 'Мои');
  assert.deepEqual(groups[0][1].sort(), ['gs01','my','nt02']);
  const ids=groups.flatMap(g=>g[1]);
  assert.equal(ids.length,new Set(ids).size);
  a.run("q='мой кросс'");
  assert.deepEqual(a.read('filterExercises().map(e=>e.id)'), ['gs01']);
  a.run(`prompt = () => 'Моя подача'; draft.sections.main=['gs01'];
    saveTemplateFrom(draft.sections, () => 10, false, '');
  `);
  const html=a.run('templateChipsHTML()');
  assert.ok(html.indexOf('Мои') < html.indexOf('Взрослые'));
  assert.match(html, /Моя подача/);
  assert.match(html, /моё/);
});
