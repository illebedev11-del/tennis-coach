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

function seedStudent(a) {
  a.run(`
    store.students = [normalizeStudent({id:'s1', name:'Игорь', age:'32', level:'Средний', hand:'right', priority:'Бэкхенд', demo:true})];
    store.groups = [normalizeGroup({id:'g1', name:'Вечерняя', studentIds:['s1','s2'], demo:true})];
    store.students.push(normalizeStudent({id:'s2', name:'Максим', age:'34', level:'Средний', hand:'left', demo:true}));
    store.plans = [];
  `);
}

const ilya = "{id:'coach_ilya',name:'Илья'}";
const ilona = "{id:'coach_ilona',name:'Илона'}";

function note(a, id, date, coach, studentIds, exercises, goal, extra = '') {
  const items = (exercises || []).map((eid) => `{id:'${eid}',title:(getEx('${eid}')||{title:'${eid}'}).title}`).join(',');
  a.run(`store.plans.push(normalizePlan({
    id:'${id}', kind:'note', status:'done', date:'${date}',
    studentIds:${JSON.stringify(studentIds)}, actualStudentIds:${JSON.stringify(studentIds)},
    coaches:[${coach}], goal:${JSON.stringify(goal || '')}, notes:${JSON.stringify(goal || '')},
    sections:{warmup:[], main:[${items}], points:[], cooldown:[]}${extra}
  }));`);
}

test('v54: stats counts, weekly bars, top drills and stale list from records', () => {
  const a = app();
  seedStudent(a);
  const rows = [
    ['01', '2026-09-14', ilya, ['gs02', 'se02', 'mv05'], 'Стабильность бэкхенда, вторая подача.'],
    ['02', '2026-09-21', ilona, ['tr06', 'gs08'], 'Укороченный и игра в короткий кросс.'],
    ['03', '2026-09-28', ilya, ['nt04', 'gs02', 'se08'], ''],
    ['04', '2026-10-05', ilya, ['gs02', 'gs05', 'mv01'], ''],
    ['05', '2026-10-09', ilona, ['nt01'], 'Игра у сетки, удары с лёта.'],
    ['06', '2026-10-14', ilya, ['se02', 'se12', 'rv01'], ''],
    ['07', '2026-10-19', ilya, ['gs02', 'se08', 'se15'], ''],
    ['08', '2026-10-23', ilona, ['gs02', 'gs08', 'mv05'], ''],
    ['09', '2026-10-28', ilya, ['se02', 'rv01', 'rv04'], ''],
    ['10', '2026-11-02', ilya, ['gs02', 'tr02', 'gs05'], ''],
    ['11', '2026-11-07', ilona, ['gs02', 'mv05'], ''],
    ['12', '2026-11-11', ilya, ['se02', 'se12', 'gs04'], ''],
    ['13', '2026-11-16', ilya, ['gs02', 'gs05', 'se08'], ''],
    ['14', '2026-11-20', ilona, ['gs02', 'rv01', 'mv01'], ''],
    ['15', '2026-11-23', ilya, ['gs02', 'se02', 'mv05'], 'Бэкхенд под темпом и вторая подача.']
  ];
  for (const [id, date, coach, ex, goal] of rows) note(a, 'p' + id, date, coach, ['s1'], ex, goal);

  const s = a.read("studentStats('s1', '2026-11-28')");
  assert.equal(s.count, 15);
  assert.equal(s.last30, 6);
  assert.equal(s.last, '2026-11-23');
  assert.equal(a.run("agoLabel('2026-11-23', '2026-11-28')"), '5 дней назад');
  const byCoach = Object.fromEntries(s.coaches.map((c) => [c.id, c.count]));
  assert.equal(byCoach.coach_ilya, 10);
  assert.equal(byCoach.coach_ilona, 5);
  assert.equal(s.top[0].count, 10);
  assert.match(s.top[0].title, /Кросс бэкхендом/);
  assert.equal(s.top[1].count, 5);
  assert.match(s.top[1].title, /Вторая подача/);
  assert.ok(s.stale.length >= 1);
  assert.ok(s.stale.every((e) => e.last <= '2026-11-07'));
  assert.match(s.stale[0].title, /Укороченный/);
  const weekTotals = s.weeks.map((w) => w.total);
  assert.equal(weekTotals.reduce((n, x) => n + x, 0), 15);
  assert.ok(s.weeks.some((w) => w.total === 2 && w.by.coach_ilya === 1 && w.by.coach_ilona === 1));

  const markup = a.run("studentStatsHTML('s1', '2026-11-28')");
  assert.match(markup, /Статистика/);
  assert.match(markup, /занятий всего/);
  assert.match(markup, />15</);
  assert.match(markup, /По неделям/);
  assert.match(markup, /Чаще всего работали над/);
  assert.match(markup, /Давно не повторяли/);
  assert.doesNotMatch(markup, /Сводка/);
});

test('v54: no sessions — a calm one-liner, no tiles or chart', () => {
  const a = app();
  seedStudent(a);
  const s = a.read("studentStats('s1', '2026-11-28')");
  assert.equal(s.count, 0);
  assert.equal(s.last30, 0);
  assert.deepEqual(s.top, []);
  const markup = a.run("studentStatsHTML('s1', '2026-11-28')");
  assert.match(markup, /Проведённых тренировок пока нет/);
  assert.doesNotMatch(markup, /stats-tiles/);
  assert.doesNotMatch(markup, /По неделям/);
  assert.doesNotMatch(markup, /Чаще всего/);
  assert.equal(a.run("studentSummaryHTML('nobody')").includes('Проведённых тренировок пока нет'), true);
});

test('v54: one or two sessions show tiles only; stale list only if 3+ weeks old', () => {
  const a = app();
  seedStudent(a);
  note(a, 'fresh1', '2026-11-26', ilya, ['s1'], ['gs02'], 'Кросс');
  note(a, 'fresh2', '2026-11-20', ilya, ['s1'], ['se02'], 'Подача');
  let markup = a.run("studentStatsHTML('s1', '2026-11-28')");
  const s = a.read("studentStats('s1', '2026-11-28')");
  assert.equal(s.count, 2);
  assert.equal(s.last30, 2);
  assert.match(markup, /stats-tiles/);
  assert.match(markup, />2</);
  assert.doesNotMatch(markup, /По неделям/);
  assert.doesNotMatch(markup, /Чаще всего работали над/);
  assert.doesNotMatch(markup, /Давно не повторяли/);

  a.run("store.plans = []");
  note(a, 'old', '2026-10-20', ilya, ['s1'], ['nt04'], 'Смэш');
  note(a, 'new', '2026-11-25', ilya, ['s1'], ['gs02'], 'Кросс');
  markup = a.run("studentStatsHTML('s1', '2026-11-28')");
  assert.equal(a.read("studentStats('s1', '2026-11-28')").count, 2);
  assert.doesNotMatch(markup, /По неделям/);
  assert.doesNotMatch(markup, /Чаще всего работали над/);
  assert.match(markup, /Давно не повторяли/);
  assert.match(markup, /Свеча и смэш|смэш/i);
});

test('v54: group sessions count for members; absences do not', () => {
  const a = app();
  seedStudent(a);
  a.run(`
    store.plans.push(normalizePlan({
      id:'grp-open', kind:'note', status:'done', date:'2026-11-10',
      studentIds:[], groupIds:['g1'], coaches:[${ilya}],
      goal:'Групповая игра', notes:'Групповая игра',
      sections:{main:[{id:'gs02', title:'Кросс бэкхендом'}]}
    }));
  `);
  assert.equal(a.read("studentStats('s1', '2026-11-28')").count, 1);
  assert.equal(a.read("studentStats('s2', '2026-11-28')").count, 1);

  a.run("store.plans = []");
  a.run(`
    store.plans.push(normalizePlan({
      id:'grp-att', kind:'note', status:'done', date:'2026-11-10',
      studentIds:[], groupIds:['g1'], groupMembers:{g1:['s1','s2']},
      actualStudentIds:['s2'], coaches:[${ilya}],
      goal:'Только Максим', notes:'Только Максим',
      sections:{main:[{id:'gs02', title:'Кросс бэкхендом'}]}
    }));
  `);
  assert.equal(a.read("studentStats('s1', '2026-11-28')").count, 0);
  assert.equal(a.read("studentStats('s2', '2026-11-28')").count, 1);
});

test('v54: goal text adds a topic once, not twice if the drill is already listed', () => {
  const a = app();
  seedStudent(a);
  note(a, 'g1', '2026-11-20', ilya, ['s1'], ['gs02'], 'Стабильность бэкхенда');
  const s = a.read("studentStats('s1', '2026-11-28')");
  const titles = s.top.map((e) => e.title + ':' + e.count);
  assert.ok(titles.some((t) => /Кросс бэкхендом/.test(t) && t.endsWith(':1')));
  assert.ok(!s.top.some((e) => e.key === 'topic_bh'), titles);
});

test('v54: relative dates and short titles', () => {
  const a = app();
  assert.equal(a.run("agoLabel('2026-11-28', '2026-11-28')"), 'сегодня');
  assert.equal(a.run("agoLabel('2026-11-27', '2026-11-28')"), 'вчера');
  assert.equal(a.run("agoLabel('2026-11-23', '2026-11-28')"), '5 дней назад');
  assert.equal(a.run("agoLabel('2026-11-07', '2026-11-28')"), '3 недели назад');
  assert.equal(a.run("shortExTitle('Кросс бэкхендом: двое по очереди против одного')"), 'Кросс бэкхендом');
  assert.equal(a.run("shortExTitle('Укороченный против соперника в глубине')"), 'Укороченный');
  assert.equal(a.run("shortExTitle('Свеча и смэш с отходом от сетки')"), 'Свеча и смэш');
});

test('v54: no demo seed in the shipped app', () => {
  const sw = fs.readFileSync(path.join(__dirname, '../sw.js'), 'utf8');
  assert.match(sw, /VERSION = 'v5\d-2026\d{4}'/);
  assert.doesNotMatch(html, /demo_stat_/);
  assert.doesNotMatch(html, /ensureDemoStats/);
  const a = app();
  assert.equal(a.read("store.plans.filter((p) => String(p.id||'').startsWith('demo_stat_')).length"), 0);
});
