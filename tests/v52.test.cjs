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
    window: node, document: { ...node, getElementById: () => null, querySelectorAll: () => [], querySelector: () => null, createElement: null, body: null },
    navigator: {}, confirm: () => true, clearTimeout() {}, setTimeout() {}, FormData: class {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  run('render = navigate = openPlan = closeModal = toast = haptic = refreshCoachSettings = closeOwnerPrompt = () => {}; restoreDraft();');
  return { run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')), storage };
}

function seedPlans(a) {
  a.run(`
    const st = store.students[0];
    const ilya = { id: 'coach_ilya', name: 'Илья' };
    const ilona = { id: 'coach_ilona', name: 'Илона' };
    const base = { kind: 'note', status: 'done', date: '2026-11-20', targetType: 'student', studentId: st.id, studentName: st.name, studentIds: [st.id], groupIds: [], actualStudentIds: [st.id], goal: 'Тема', notes: 'Тема', sections: emptySections(), summary: null, createdBy: store.coachId };
    store.plans = [
      { ...base, id: 'old-empty', createdAt: '2026-11-10T10:00:00.000Z', coaches: [ilya] },
      { ...base, id: 'old-no-date', coaches: [ilya] },
      { ...base, id: 'old-ilona', createdAt: '2026-11-10T10:00:00.000Z', coaches: [ilona] },
      { ...base, id: 'old-both', createdAt: '2026-11-10T10:00:00.000Z', coaches: [ilya, ilona] },
      { ...base, id: 'new-ilya', createdAt: '2026-11-28T10:00:00.000Z', coaches: [ilya] },
      { ...base, id: 'new-ilona', createdAt: '2026-11-28T10:00:00.000Z', coaches: [ilona] }
    ];
  `);
}

test('v52: records without an author still normalize to Илья, and the v51 cutoff is 28 Nov 2026, 12:46 Moscow time', () => {
  const a = app();
  assert.equal(a.run('V51_SINCE'), Date.parse('2026-11-28T12:46:00+03:00'));
  const p = a.read("normalizePlan({id:'x',date:'2026-01-01',sections:{}})");
  assert.deepEqual(p.coaches, [{ id: 'coach_ilya', name: 'Илья' }]);
  assert.equal(a.run('createdBeforeV51({createdAt:"2026-11-28T09:45:59.000Z"})'), true);
  assert.equal(a.run('createdBeforeV51({createdAt:"2026-11-28T12:46:00+03:00"})'), false);
  assert.equal(a.run('createdBeforeV51({})'), true);
});

test('v52: choosing Илона on first launch reassigns only auto-filled single-Илья records from before v51', () => {
  const a = app();
  seedPlans(a);
  assert.deepEqual(a.read("orphanedAuthorPlans().map((p) => p.id).sort()"), ['old-empty', 'old-no-date']);
  const n = a.run("chooseDeviceOwner('coach_ilona', true)");
  assert.equal(n, 2);
  const after = a.read("Object.fromEntries(store.plans.map((p) => [p.id, p.coaches.map((c) => c.id).join('+')]))");
  assert.equal(after['old-empty'], 'coach_ilona');
  assert.equal(after['old-no-date'], 'coach_ilona');
  assert.equal(after['old-ilona'], 'coach_ilona');
  assert.equal(after['old-both'], 'coach_ilya+coach_ilona');
  assert.equal(after['new-ilya'], 'coach_ilya');
  assert.equal(after['new-ilona'], 'coach_ilona');
  assert.equal(a.storage.get('tennis_coach_device_owner'), 'coach_ilona');
  assert.equal(a.storage.get('tennis_coach_last_coach'), 'coach_ilona');
  assert.equal(a.run('lastCoachId()'), 'coach_ilona');
  assert.equal(a.run('deviceOwnerId()'), 'coach_ilona');
});

test('v52: choosing Илья on first launch does not rename any records', () => {
  const a = app();
  seedPlans(a);
  assert.equal(a.run("chooseDeviceOwner('coach_ilya', true)"), 0);
  assert.deepEqual(a.read("store.plans.find((p) => p.id === 'old-empty').coaches"), [{ id: 'coach_ilya', name: 'Илья' }]);
  assert.equal(a.storage.get('tennis_coach_device_owner'), 'coach_ilya');
});

test('v52: changing the owner later in settings only changes the default, not records', () => {
  const a = app();
  seedPlans(a);
  a.run("chooseDeviceOwner('coach_ilya', true)");
  const before = a.read('store.plans');
  assert.equal(a.run("chooseDeviceOwner('coach_ilona', false)"), 0);
  assert.deepEqual(a.read('store.plans'), before);
  assert.equal(a.run('deviceOwnerId()'), 'coach_ilona');
  assert.equal(a.run('lastCoachId()'), 'coach_ilona');
});

test('v52: the first-launch prompt is needed until a choice is stored, including on an empty install', () => {
  const a = app();
  a.run('store.plans = []');
  assert.equal(a.run('deviceOwnerId()'), '');
  assert.equal(a.run("Boolean(!deviceOwnerId())"), true);
  a.run("chooseDeviceOwner('coach_ilona', true)");
  assert.equal(a.run('deviceOwnerId()'), 'coach_ilona');
  assert.equal(a.run("chooseDeviceOwner('coach_ilona', true)"), 0);
});
