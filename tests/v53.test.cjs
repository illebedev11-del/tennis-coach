const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].split('\nrestoreDraft();')[0];

function app(storage = new Map()) {
  const node = { addEventListener() {}, body: null };
  const context = vm.createContext({
    window: node,
    document: { ...node, getElementById: () => null, querySelectorAll: () => [], querySelector: () => null, createElement: null, body: null },
    navigator: { share: undefined, canShare: undefined },
    confirm: () => true, clearTimeout() {}, setTimeout() {}, FormData: class {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  run('render = navigate = openPlan = closeModal = toast = haptic = refreshCoachSettings = closeOwnerPrompt = updateExerciseList = () => {}; restoreDraft();');
  return { run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')), storage };
}

function stamp(daysAgo) {
  return new Date(Date.now() - daysAgo * 864e5).toISOString();
}

test('v53: a copy contains students, groups, sessions, coaches, custom drills and templates', () => {
  const a = app();
  a.run(`
    store.students.push(normalizeStudent({id:'s_new', name:'Ваня'}));
    store.customExercises.push({id:'user_x', title:'Моё', brief:'Кратко', stroke:'Удары с отскока', goals:['Стабильность'], format:'С тренером', level:'Любой', minutes:10});
    store.templates.push(normalizeTemplate({id:'tpl_x', title:'Мой шаблон', kids:false, blocks:{warmup:10,main:20,points:10,cooldown:5}, items:{warmup:[],main:[],points:[],cooldown:[]}}));
    draft.who = legacyWho('student','s_new'); draft.sections.main = [seedExercises[0].id]; savePlan();
  `);
  const copy = a.read('backupObject()');
  assert.equal(copy.app, 'tennis-coach-v1');
  assert.equal(copy.version, 3);
  assert.ok(copy.exportedAt);
  assert.ok(copy.data.students.some((s) => s.name === 'Ваня'));
  assert.ok(copy.data.groups.length >= 1);
  assert.ok(copy.data.plans.length >= 1);
  assert.ok(copy.data.coaches.some((c) => c.id === 'coach_ilya'));
  assert.ok(copy.data.customExercises.some((e) => e.id === 'user_x'));
  assert.ok(copy.data.templates.some((t) => t.id === 'tpl_x'));
  assert.match(a.run('backupFileName()'), /^Tennis Coach — копия \d{2}\.\d{2}\.\d{4}\.json$/);
});

test('v53: merge adds only new ids, keeps local records, and stores a safety copy', () => {
  const a = app();
  a.run(`
    store.students = [normalizeStudent({id:'keep', name:'Местный'}), normalizeStudent({id:'same', name:'Как было'})];
    store.plans = [normalizePlan({id:'p_keep', date:'2026-11-01', kind:'note', status:'done', notes:'Своё', goal:'Своё', studentIds:['keep'], coaches:[{id:'coach_ilya',name:'Илья'}], sections:{}})];
    persist();
  `);
  const incoming = a.read(`({
    exportedAt: nowISO(), app:'tennis-coach-v1', version:3,
    data: {
      ...store,
      students: [normalizeStudent({id:'same', name:'Из файла'}), normalizeStudent({id:'new', name:'Новый'})],
      plans: [normalizePlan({id:'p_keep', date:'2026-11-01', kind:'note', status:'done', notes:'Чужое', goal:'Чужое', studentIds:['same'], sections:{}}),
              normalizePlan({id:'p_new', date:'2026-11-02', kind:'note', status:'done', notes:'Новое', goal:'Новое', studentIds:['new'], sections:{}})]
    },
    drafts:{plan:null,notes:{},reports:{}}
  })`);
  const added = a.run('applyBackup(' + JSON.stringify(incoming) + ', "merge").added');
  assert.equal(added.students, 1);
  assert.equal(added.plans, 1);
  const names = a.read("store.students.map((s) => s.id+':'+s.name).sort()");
  assert.deepEqual(names, ['keep:Местный', 'new:Новый', 'same:Как было']);
  assert.equal(a.run("store.plans.find((p) => p.id==='p_keep').notes"), 'Своё');
  assert.equal(a.run("store.plans.find((p) => p.id==='p_new').notes"), 'Новое');
  const safety = a.read("JSON.parse(localStorage.getItem(storagePrefix + PREVIOUS_BACKUP))");
  assert.equal(safety.data.plans.length, 1);
  assert.ok(safety.data.students.every((s) => s.id !== 'new'));
});

test('v53: replace swaps all data and keeps a safety copy that can be undone', () => {
  const a = app();
  a.run(`store.students = [normalizeStudent({id:'old', name:'Было'})]; store.plans = []; persist();`);
  const incoming = a.read(`({
    exportedAt: nowISO(), app:'tennis-coach-v1', version:3,
    data: { ...defaultStore(), students:[normalizeStudent({id:'new', name:'Из копии'})], plans:[], groups:[], templates:[], customExercises:[], coaches:defaultCoaches() },
    drafts:{plan:null,notes:{},reports:{}}
  })`);
  a.run('importFromObject(' + JSON.stringify(incoming) + ')');
  assert.deepEqual(a.read("store.students.map((s) => s.name)"), ['Из копии']);
  const safety = a.read("JSON.parse(localStorage.getItem(storagePrefix + PREVIOUS_BACKUP))");
  assert.deepEqual(safety.data.students.map((s) => s.name), ['Было']);
  a.run('importFromObject(JSON.parse(localStorage.getItem(storagePrefix + PREVIOUS_BACKUP)))');
  assert.deepEqual(a.read("store.students.map((s) => s.name)"), ['Было']);
});

test('v53: a broken file is rejected and current data stays', () => {
  const a = app();
  const before = a.read('store');
  assert.throws(() => a.run("decodeBackup({app:'nope'})"), /format/);
  assert.throws(() => a.run("applyBackup({app:'nope'}, 'replace')"), /format/);
  assert.deepEqual(a.read('store'), before);
});

test('v53: the reminder appears after 14 days when there are records, and not on an empty install', () => {
  const a = app();
  a.run('store.plans = []; setBackupMeta({lastExportAt:"", dismissedAt:""});');
  assert.equal(a.run('backupDue()'), null);
  a.run(`store.plans = [normalizePlan({id:'p1', date:'2026-11-01', kind:'note', status:'done', notes:'Есть', goal:'Есть', sections:{}})];
    setBackupMeta({lastExportAt:"", dismissedAt:""});`);
  assert.ok(a.run('backupDue() && backupDue().days > 14'));
  a.run('setBackupMeta({lastExportAt: nowISO(), dismissedAt:""});');
  assert.equal(a.run('backupDue()'), null);
  a.run(`setBackupMeta({lastExportAt: "${stamp(15)}", dismissedAt:""});`);
  assert.ok(a.run('backupDue() && backupDue().days >= 14'));
  a.run(`setBackupMeta({lastExportAt: "${stamp(15)}", dismissedAt: nowISO()});`);
  assert.equal(a.run('backupDue()'), null);
});
