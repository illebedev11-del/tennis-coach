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
    confirm: () => true, clearTimeout() {}, FormData: class {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  run('render = navigate = openPlan = closeModal = toast = haptic = () => {}; restoreDraft();');
  return { run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')), storage };
}
const old = "{id:'p1',kind:'note',status:'done',date:'2026-11-01',targetType:'student',studentId:'demo1',studentIds:['demo1'],groupIds:[],goal:'Старая',notes:'Старая',sections:{},summary:null}";

test('v51: old records without an author become Илья, nothing else changes', () => {
  const a = app();
  assert.deepEqual(a.read(`normalizePlan(${old}).coaches`), [{ id: 'coach_ilya', name: 'Илья' }]);
  assert.equal(a.read(`normalizePlan(${old}).notes`), 'Старая');
  assert.deepEqual(a.read(`normalizePlan({...${old}, coaches:[{id:'coach_ilona',name:'Илона'}]}).coaches`), [{ id: 'coach_ilona', name: 'Илона' }]);
});
test('v51: a new record gets the last-used coach, the choice is remembered, and saving keeps it', () => {
  const a = app();
  assert.equal(a.run('lastCoachId()'), 'coach_ilya');
  a.run("draft.who = legacyWho('student','demo1'); draft.sections.main = [seedExercises[0].id]; coachPick('plan', 'coach_ilona'); savePlan();");
  assert.equal(a.storage.get('tennis_coach_last_coach'), 'coach_ilona');
  assert.deepEqual(a.read('store.plans.at(-1).coaches.map((c) => c.id)'), ['coach_ilona']);
  assert.equal(a.run('lastCoachId()'), 'coach_ilona');
  assert.deepEqual(a.read("whoGet('plan').coachIds"), ['coach_ilona']);
});
test('v51: switching the author keeps a second coach, never duplicates, and does not count as a participant', () => {
  const a = app();
  a.run("draft.who = {coachIds:['coach_ilya','coach_ilona'],studentIds:['demo1'],groupIds:[]}; coachPick('plan','coach_ilona');");
  assert.deepEqual(a.read('draft.who.coachIds'), ['coach_ilona', 'coach_ilya']);
  assert.equal(a.run("whoCount(whoGet('plan'))"), 2);
  assert.equal(a.run("whoCount({coachIds:['coach_ilya'],studentIds:[],groupIds:[]})"), 0);
});
test('v51: a record shows players only in its title, the author is shown separately', () => {
  const a = app();
  assert.equal(a.run(`targetOfPlan(normalizePlan({...${old}, coaches:[{id:'coach_ilya',name:'Илья'}]})).name`), 'Игорь (демо)');
  assert.match(a.run(`authorHTML(normalizePlan(${old}))`), /Илья/);
});
