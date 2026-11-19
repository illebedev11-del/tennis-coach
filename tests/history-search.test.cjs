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


test('search matches reports, historical names and exercise titles ignoring case and ё; escapes markup', () => {
  const a = app();
  a.run(`store.plans = [
    {id:'old',date:'2025-01-01',kind:'note',notes:'Что делали',studentIds:['demo1'],names:{gone:'Алёна'},summary:{success:'Точный приём'},sections:{main:[{id:'gs01',title:'Глубокий кросс'}]}},
    {id:'new',date:'2026-11-19',kind:'note',notes:'Кросс',studentIds:['demo1']}
  ];`);
  for (const q of ['АЛЕНА','ПРИЕМ','глубокий','что делали']) {
    a.run('sessQuery = ' + JSON.stringify(q));
    assert.match(a.run('sessListInnerHTML()'), /data-id="old"/);
    assert.match(a.run('sessListInnerHTML()'), /<mark>/);
  }
  a.run("sessQuery='кросс'");
  const output = a.run('sessListInnerHTML()');
  assert.ok(output.indexOf('data-id="new"') < output.indexOf('data-id="old"'));
  a.run("sessQuery='<img>'");
  assert.equal(a.run("searchHighlight('<img>')"), '<mark>&lt;img&gt;</mark>');
  a.run("sessQuery='нет совпадений'");
  assert.match(a.run('sessListInnerHTML()'), /Ничего не найдено/);
});

test('summary counts completed attendance, deduplicates exercises per session and never writes data', () => {
  const a = app();
  a.run(`store.plans = [
    {id:'done',date:'2026-11-18',status:'done',studentIds:['demo1'],actualStudentIds:['demo1'],plannedStudentIds:['demo1'],goal:'Глубина',sections:{main:[{id:'gs01',title:'Кросс'},{id:'gs01',title:'Кросс'}]}},
    {id:'miss',date:'2026-11-17',status:'done',studentIds:[],actualStudentIds:[],plannedStudentIds:['demo1']},
    {id:'future',date:'2026-11-20',status:'planned',studentIds:['demo1']},
    {id:'unknown',date:'2026-11-16',status:'done',studentIds:['demo1'],actualStudentIds:['demo1'],attendanceInferred:true,groupIds:['g']},
    {id:'note',date:'2026-10-01',kind:'note',studentIds:['demo1'],notes:'Подача'}
  ]; const before = JSON.stringify(store);`);
  const r = a.read("studentSummary('demo1', '2026-11-19')");
  assert.equal(r.count, 3);
  assert.equal(r.last, '2026-11-18');
  assert.equal(r.monthTotal, 2);
  assert.equal(r.monthAttended, 1);
  assert.equal(r.unknown, 1);
  assert.equal(r.exercises[0].count, 1);
  assert.equal(a.run('JSON.stringify(store)'), a.run('before'));
  assert.equal(a.read("studentSummary('nobody', '2026-11-19')").count, 0);
  assert.match(a.run("studentSummaryHTML('nobody')"), /Проведённых тренировок пока нет/);
});
