// v46: время и упражнения в записи, свои разделы библиотеки, сводка.
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



test('record keeps time and exercises with notes through save, normalize and backup', () => {
  const a = app();
  a.run(`store.plans.push({id:'n1',kind:'note',status:'done',date:'2026-11-20',time:'18:30',studentIds:['demo1'],notes:'Кросс',
    sections:{...emptySections(), main:[{...snapshotExercise(getEx('gs01')), note:'Глубже'}, snapshotExercise(getEx('nt02'))]}});
    persist();`);
  const back = a.read("normalizeStore(JSON.parse(JSON.stringify(decodeBackup(JSON.parse(JSON.stringify(backupObject()))).data))).plans.find(p=>p.id==='n1')");
  assert.equal(back.time, '18:30');
  assert.deepEqual(back.sections.main.map(e=>[e.id,e.note||'']), [['gs01','Глубже'],['nt02','']]);
  assert.deepEqual(a.read("planExercises(store.plans.find(p=>p.id==='n1')).map(e=>e.id)"), ['gs01','nt02']);
  assert.equal(a.read("'time' in normalizePlan({id:'x',date:'2026-11-20',time:'bad'})"), false);
  const row = a.read("normNoteRow({time:'09:05',exercises:[{id:'gs01',title:'Кросс',note:'а'},{id:'',title:'x'}]})");
  assert.equal(row.time, '09:05');
  assert.equal(row.exercises.length, 1);
});

test('old data without library stays intact; broken library entries are dropped', () => {
  const a = app();
  const s = a.read(`normalizeStore({students:[{id:'s1',name:'Ира'}],plans:[{id:'p',date:'2026-11-01',notes:'x',kind:'note'}],
    library:{sections:[{id:'ls_a',title:'Подготовка'},{id:'bad',title:'x'},{id:'ls_b',title:''}],order:['ls_a',5,'Подача'],place:{gs01:'ls_a',nt02:'ls_zzz'}}})`);
  assert.equal(s.plans.length, 1);
  assert.deepEqual(s.library.sections, [{id:'ls_a',title:'Подготовка'}]);
  assert.deepEqual(s.library.order, ['ls_a','Подача']);
  assert.deepEqual(s.library.place, {gs01:'ls_a'});
  assert.deepEqual(a.read('normalizeStore({}).library'), {sections:[],order:[],place:{}});
});

test('custom sections: order, placement, delete with moving exercises', () => {
  const a = app();
  a.run(`toast=()=>{}; document.getElementById=()=>null; prompt=()=>'Подготовка к турниру'; libNew();`);
  const id = a.read('store.library.sections[0].id');
  a.run(`store.library.place.gs01='${id}'; store.exerciseOverrides.nt02={title:'Мой залп'};`);
  let groups = a.read('groupExercises(allExercises()).map(g=>[g[0],g[1].map(e=>e.id)])');
  const sec = groups.find(g=>g[0]===id);
  assert.deepEqual(sec[1], ['gs01']);
  assert.ok(!groups.filter(g=>g[0]!==id && g[0]!=='Мои').some(g=>g[1].includes('gs01')));
  const mine = groups.find(g=>g[0]==='Мои')[1];
  assert.ok(mine.includes('nt02'));
  assert.equal(groups.filter(g=>g[1].includes('nt02')).length, 2);
  a.run(`libMove('${id}', -1)`);
  const keys = a.read('libSectionList().map(s=>s.key)');
  assert.ok(keys.indexOf(id) === keys.indexOf('Другое') - 1);
  a.run(`libDeleteTo('${id}', '')`);
  assert.equal(a.read('store.library.sections.length'), 0);
  assert.equal(a.read("'gs01' in store.library.place"), false);
  groups = a.read('groupExercises(allExercises()).map(g=>[g[0],g[1].map(e=>e.id)])');
  assert.ok(groups.some(g=>g[0]!=='Мои' && g[1].includes('gs01')));
});

test('student summary: palette-friendly headings and correct grammar', () => {
  const a = app();
  a.run(`store.plans.push({id:'n1',kind:'note',status:'done',date:dateISO(),studentIds:['demo1'],actualStudentIds:['demo1'],plannedStudentIds:['demo1'],notes:'Подача',sections:emptySections()});`);
  const html = a.run("studentSummaryHTML('demo1')");
  assert.match(html, /1 из 1 занятия /);
  assert.match(html, /Последние записи/);
  assert.doesNotMatch(html, /Над чем работали/);
});
