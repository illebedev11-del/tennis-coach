const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].split('\nrestoreDraft();')[0];

function app(storage = new Map(), failWrite = () => false) {
  const node = { addEventListener() {} };
  const context = vm.createContext({
    window: node, document: { ...node, getElementById: () => node, querySelectorAll: () => [], querySelector: () => null }, navigator: {},
    confirm: () => true, clearTimeout() {},
    FormData: class { constructor(form) { return form; } },
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem(key, value) {
        if (failWrite(key)) throw Error('quota');
        storage.set(key, value);
      },
      removeItem: (key) => storage.delete(key)
    }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  // Keep actual persistence, form handlers and models. Skip presentation in the Node suite.
  run(`render = navigate = openPlan = openGroup = closeModal = toast = haptic = () => {};
    restoreDraft();`);
  return { run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')), storage };
}

function sessions(a) {
  a.run(`store = normalizeStore(store); store.students.push(normalizeStudent({id:'third', name:'Вера'}));
    const group = store.groups[0];
    const who = legacyWho('group', group.id);
    draft.who = who; draft.sections.main = [seedExercises[0].id]; savePlan();
    const plan = store.plans[0];
    const form = {getAll: () => ['demo1','demo2'], get: k => ({id:plan.id,success:'Глубина'})[k], querySelectorAll: () => []};
    finishPlanFromForm(form);
    whoForms.note = who;
    const noteForm = {elements:{notes:{value:'Кроссы'}},querySelectorAll:() => []};
    saveNoteFromForm(noteForm);
    const note = store.plans[1];
    saveGroupFromForm({get: k => ({id:group.id,name:group.name})[k],getAll: () => ['demo2','third']});
  `);
}

test('group plan, report and note retain their roster after group changes, edits and reload', () => {
  const a = app();
  sessions(a);
  a.run(`whoForms.note = who; noteForm.elements.id = {value:note.id};
    noteForm.elements.notes.value = 'Розыгрыши'; saveNoteFromForm(noteForm);
    whoForms.edit = who; saveWhoEditor(plan.id);
    deleteStudent('demo1');`);
  const b = app(a.storage);
  // v35: deleting a student keeps the sessions signed with the name (same rule as the swipe delete with «Вернуть»).
  assert.deepEqual(b.read("['demo1','demo2','third'].map(id => plansForStudent(id).length)"), [2,2,0]);
  assert.equal(b.run("getStudent('demo1')"), null);
  assert.equal(b.run("store.plans[0].names.demo1"), 'Игорь');
  assert.equal(b.run("store.plans[0].summary.success"), 'Глубина');
  assert.equal(b.run("store.plans[1].notes"), 'Розыгрыши');
});

test('legacy group records get the group roster once: plans as planned, past sessions as inferred attendance', () => {
  const a = app();
  a.run(`const ex = seedExercises[0];
    store = normalizeStore({...clone(store), plans:[
      {id:'old', kind:'plan', status:'done', targetType:'group', groupId:'demog1', studentNotes:{demo2:'Есть прогресс'}, sections:{main:[ex]}},
      {id:'oldnote', kind:'note', groupIds:['demog1'], studentIds:[], notes:'Игра у сетки'},
      {id:'soon', kind:'plan', groupIds:['demog1'], studentIds:[], sections:{main:[ex]}},
      {id:'gone', kind:'note', groupIds:['nogroup'], studentIds:[], studentNotes:{demo1:'Подача'}, notes:'Без группы'}]});
    persist();`);
  assert.deepEqual(a.read("['old','oldnote','soon','gone'].map(id => planStudentIds(getPlan(id)))"),
    [['demo1','demo2'], ['demo1','demo2'], ['demo1','demo2'], ['demo1']]);
  assert.deepEqual(a.read("[getPlan('old').attendanceInferred, getPlan('oldnote').attendanceInferred, getPlan('soon').actualStudentIds, getPlan('gone').actualStudentIds]"),
    [true, true, null, null]);
  assert.deepEqual(a.read("getPlan('old').plannedStudentIds"), ['demo1','demo2']);
  assert.match(a.run("groupAttendanceHTML(getPlan('old'))"), /Состав по группе: Игорь.*, Максим/);
  assert.match(a.run("groupAttendanceHTML(getPlan('gone'))"), /не сохранился/);
  assert.doesNotMatch(a.run("groupAttendanceHTML(getPlan('old'))"), /не был записан/);
  // Idempotent: a second pass changes nothing.
  assert.equal(a.run("normalizeStore(clone(store)), normalizeStore.migrated"), 0);
  assert.deepEqual(a.read("normalizeStore(clone(store)).plans"), a.read("store.plans"));
  // Later group edits do not move old sessions.
  a.run("getGroup('demog1').studentIds=['demo2']; persist();");
  const b = app(a.storage);
  assert.deepEqual(b.read("['demo1','demo2'].map(id => plansForStudent(id).length)"), [4,3]);
  // Correction replaces the inferred roster with real attendance; the named note stays.
  b.run("saveAttendance({get:()=>'old', getAll:()=>['demo1']})");
  assert.deepEqual(b.read("[planStudentIds(getPlan('old')), getPlan('old').attendanceInferred ?? null]"), [['demo1'], null]);
  assert.equal(b.run("getPlan('old').studentNotes.demo2"), 'Есть прогресс');
  assert.match(b.run("groupAttendanceHTML(getPlan('old'))"), /Были: Игорь.* · не было: Максим/);
});

test('backup restores all data and draft types after reload and preserves the replaced state', () => {
  const a = app();
  sessions(a);
  a.run(`draft.goal = 'Черновик плана'; draft.who = who; draft.sections.main=[seedExercises[1].id]; persistDraft();
    saveNoteDraft(NOTE_NEW, {who, notes:'Незаконченная запись'});
    draft.who = who; savePlan(); const pending = store.plans.at(-1);
    draft.goal='Ещё один план'; persistDraft();
    saveReportDraft(pending.id,{next:'Шаг к мячу',studentNotes:{demo2:'Баланс'}});
    const copy = JSON.parse(JSON.stringify(backupObject()));
    store.students[0].name='Новое имя'; store.plans=[]; persist();
    draft.goal='После копии'; persistDraft(); saveNoteDraft('unrelated',{notes:'Лишнее'});
    importFromObject(copy);`);
  const b = app(a.storage);
  assert.deepEqual(b.read('store'), a.read('normalizeStore(copy.data)'));
  assert.deepEqual(b.read('backupObject().drafts'), a.read('copy.drafts'));
  assert.equal(b.run('JSON.parse(localStorage.getItem(storagePrefix + PREVIOUS_BACKUP)).drafts.plan.goal'), 'После копии');
  assert.equal(b.run('JSON.parse(localStorage.getItem(storagePrefix + PREVIOUS_BACKUP)).data.students[0].name'), 'Новое имя');
  b.run(`const old = {app:'tennis-coach-v1',version:2,data:store}; delete old.data.coaches;
    importFromObject(old);`);
  assert.deepEqual(b.read('[draft.goal,loadNoteDrafts(),loadReportDrafts()]'), ['',{},{}]);
});

test('invalid collections, rows, exercise snapshots and drafts cannot replace local data', () => {
  const a = app();
  sessions(a);
  const before = [...a.storage];
  for (const mutation of [
    "delete x.data.groups", "x.data.students=[null]", "x.data.plans[0].sections.main=[null]",
    "x.data.students.push(x.data.students[0])", "x.drafts.reports=[]", "x.version=99",
    "x.data.plans[0].groupMembers.demog1='invalid'", "x.drafts.plan.sections.main=[null]",
    "x.data.plans[0].actualStudentIds=[null]", "x.drafts.reports.bad={success:'',difficulty:'',next:'',actualStudentIds:{}}"
  ]) {
    assert.throws(() => a.run(`{const x=clone(backupObject()); ${mutation}; importFromObject(x);}`), /format/);
    assert.deepEqual([...a.storage], before);
  }
});

test('write failures during staging, saving previous data or switching datasets leave active data intact', () => {
  for (const at of [1,2,3,4,5,6]) {
    let remaining = Infinity;
    const a = app(new Map(), () => --remaining === 0);
    sessions(a);
    const before = a.read('normalizeStore(clone(store))');
    remaining = at;
    assert.throws(() => a.run("const x=clone(backupObject()); x.data.plans=[]; importFromObject(x)"), /storage/);
    assert.deepEqual(app(a.storage).read('store'), before);
    assert.equal(a.run('store.plans.length'), 2);
  }
});

test('export includes typed note and report drafts even if browser storage is full', () => {
  let full = false;
  const a = app(new Map(), () => full);
  sessions(a);
  full = true;
  a.run(`saveNoteDraft(NOTE_NEW, {who, notes:'Последняя правка'});
    saveReportDraft(plan.id, {next:'Повторить'});`);
  assert.equal(a.run('backupObject().drafts.notes[NOTE_NEW].notes'), 'Последняя правка');
  assert.equal(a.run('backupObject().drafts.reports[plan.id].next'), 'Повторить');
});

test('finishing a plan requires actual attendance and permits an absent player and a substitute', () => {
  const a = app();
  a.run(`store.students.push(normalizeStudent({id:'sub',name:'Вера'}));
    draft.who=legacyWho('group','demog1'); draft.sections.main=[seedExercises[0].id]; savePlan();
    const p=store.plans[0]; getGroup('demog1').studentIds=['demo2','sub'];
    let selected=[]; const form={get:k=>k==='id'?p.id:'',getAll:()=>selected,querySelectorAll:()=>[]};
    finishPlanFromForm(form);`);
  assert.equal(a.run('p.status'), 'planned');
  a.run("selected=['demo1','sub']; finishPlanFromForm(form); getGroup('demog1').studentIds=[]; persist();");
  const b = app(a.storage);
  assert.deepEqual(b.read('store.plans[0].groupMembers.demog1'), ['demo1','demo2']);
  assert.deepEqual(b.read('planStudentIds(store.plans[0])'), ['demo1','sub']);
  assert.deepEqual(b.read("['demo1','demo2','sub'].map(doneCountForStudent)"), [1,0,1]);
});

test('replacing a legacy note group with A removes B from attendance but preserves B’s historical note', () => {
  const a = app();
  a.run(`const old=normalizePlan({id:'old',kind:'note',groupId:'demog1',studentNotes:{demo2:'Смена хвата'}});
    store.plans=[old]; whoForms.note=legacyWho('student','demo1');
    saveNoteFromForm({elements:{id:{value:'old'},notes:{value:'Форхенд'}},querySelectorAll:()=>[]});`);
  const b = app(a.storage);
  assert.deepEqual(b.read("planStudentIds(getPlan('old'))"), ['demo1']);
  assert.equal(b.run("getPlan('old').studentNotes.demo2"), 'Смена хвата');
  assert.equal(b.run("plansForStudent('demo2').length"), 0);
  assert.match(b.run("personNotesHTML(getPlan('old'))"), /Смена хвата/);
});

test('a completed plan with only its planned group snapshot reads as attendance by the group and stays correctable', () => {
  const a = app();
  a.run(`store = normalizeStore({...clone(store), plans:[{id:'old',kind:'plan',status:'done',groupIds:['demog1'],
    groupMembers:{demog1:['demo1','demo2']}, recordedStudentIds:[], studentNotes:{demo2:'Подача'}, sections:{main:[seedExercises[0]]}}]});
    const p = getPlan('old'); whoForms.edit=whoOfPlan(p); saveWhoEditor(p.id);`);
  assert.deepEqual(a.read("planStudentIds(getPlan('old'))"), ['demo1','demo2']);
  assert.match(a.run("groupAttendanceHTML(getPlan('old'))"), /Состав по группе/);
  a.run("whoForms.edit=legacyWho('student','demo1'); saveWhoEditor('old'); importFromObject(clone(backupObject()));");
  assert.deepEqual(a.read("planStudentIds(getPlan('old'))"), ['demo1']);
  assert.equal(a.run("getPlan('old').studentNotes.demo2"), 'Подача');
  assert.equal(a.run("plansForStudent('demo2').length"), 0);
});

test('older app versions see the same data after a restore, and their later edits are adopted without losing attendance', () => {
  const a = app();
  sessions(a);
  a.run("importFromObject(clone(backupObject()));");
  assert.ok(a.run("storagePrefix").length > 0);
  // The legacy key mirrors the active dataset for an older cached version.
  assert.equal(a.storage.get('tennis_coach_app_v1'), a.storage.get(a.run('storagePrefix') + 'tennis_coach_app_v1'));
  // An older version (without attendance fields) edits the mirror.
  const older = JSON.parse(a.storage.get('tennis_coach_app_v1'));
  older.students[0].name = 'Игорь (правка в старой версии)';
  for (const row of older.plans) { delete row.actualStudentIds; delete row.groupMembers; delete row.plannedStudentIds; }
  a.storage.set('tennis_coach_app_v1', JSON.stringify(older));
  const b = app(a.storage);
  assert.equal(b.run('store.students[0].name'), 'Игорь (правка в старой версии)');
  assert.deepEqual(b.read('store.plans[0].groupMembers.demog1'), ['demo1','demo2']);
  assert.deepEqual(b.read('planStudentIds(store.plans[0])'), ['demo1','demo2']);
  assert.equal(a.storage.get('tennis_coach_app_v1'), a.storage.get(b.run('storagePrefix') + 'tennis_coach_app_v1'));
  // Only one pre-restore copy is kept, no matter how many restores.
  b.run("importFromObject(clone(backupObject())); importFromObject(clone(backupObject()));");
  assert.equal([...b.storage.keys()].filter((k) => k.endsWith('_before_import')).length, 1);
});

test('corrected attendance, archived notes and attendance-only drafts survive export and restore', () => {
  const a = app();
  sessions(a);
  a.run(`plan.studentNotes.demo2='Приём подачи';
    saveAttendance({get:()=>plan.id,getAll:()=>['third']});
    draft.who=who; draft.sections.main=[seedExercises[0].id]; savePlan();
    const pending=store.plans.at(-1);
    saveReportDraft(pending.id,{actualStudentIds:['third']});
    saveNoteDraft(NOTE_NEW,{who,actualStudentIds:['demo2'],notes:'Черновик'});
    const saved=clone(backupObject()); store.plans=[]; importFromObject(saved);`);
  const b = app(a.storage);
  assert.deepEqual(b.read('store.plans[0].plannedStudentIds'), ['demo1','demo2']);
  assert.deepEqual(b.read('planStudentIds(store.plans[0])'), ['third']);
  assert.match(b.run('personNotesHTML(store.plans[0])'), /Приём подачи/);
  assert.deepEqual(b.read('getReportDraft(store.plans.at(-1).id).actualStudentIds'), ['third']);
  assert.deepEqual(b.read('readNoteDraft(NOTE_NEW).actualStudentIds'), ['demo2']);
});

test('a corrected individual session shows the substitute in the title and the original student in the plan', () => {
  const a = app();
  a.run(`draft.who=legacyWho('student','demo1'); draft.sections.main=[seedExercises[0].id]; savePlan();
    const p=store.plans[0]; finishPlanFromForm({get:k=>k==='id'?p.id:'',getAll:()=>['demo2'],querySelectorAll:()=>[]});`);
  assert.equal(a.run('targetOfPlan(p).student.id'), 'demo2');
  assert.deepEqual(a.read('p.plannedStudentIds'), ['demo1']);
});
