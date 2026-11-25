// v47: анимация по описанию своего упражнения, подсказки при неясном тексте, анимации вместо схем, календарь занятий.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].split('\nrestoreDraft();')[0];

function app(store) {
  const node = { addEventListener() {} };
  const storage = new Map(Object.entries(store || {}));
  const context = vm.createContext({
    window: node, document: { ...node, getElementById: () => node, querySelectorAll: () => [], querySelector: () => null }, navigator: {},
    confirm: () => true, clearTimeout() {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  return { run, read: (code) => JSON.parse(run('JSON.stringify(' + code + ')')) };
}

// типичные описания тренера: [название, описание, что должно быть в сцене, состав]
const CASES = [
  ['Форхенд кросс с корзины', 'Тренер набрасывает с корзины, ученик бьёт форхенд кроссом глубоко, 5 раз', ['feed', 'drive'], 'cp'],
  ['Бэкхенд по линии', 'Тренер с корзины, ученик бьёт бэкхенд по линии', ['feed', 'drive'], 'cp'],
  ['Справа и слева в центр', 'Тренер набрасывает, ученик чередуя справа и слева бьёт в центр', ['feed', 'drive'], 'cp'],
  ['Кросс справа с тренером', 'Тренер играет с учеником кросс справа, держим мяч в игре', ['drive'], 'cp'],
  ['Подача в оба квадрата', 'Ученик подаёт в оба квадрата, 4 подачи, в т', ['serve'], 'p'],
  ['Приём подачи', 'Тренер подаёт, ученик принимает и отвечает кроссом', ['serve', 'drive'], 'cp'],
  ['Подача и приём в парах', 'Двое учеников: один подаёт, второй принимает в центр', ['serve', 'drive'], 'pp'],
  ['Подход и воле', 'Тренер даёт короткий мяч, ученик выходит к сетке подходом по линии и завершает с лёта', ['feed', 'drive', 'volley'], 'cp'],
  ['Воле у сетки', 'Ученик стоит у сетки, тренер набрасывает, справа и слева в угол', ['feed', 'volley'], 'cp'],
  ['Смэш', 'Тренер даёт свечу, ученик отходит и бьёт смэш', ['lob', 'smash'], 'cp'],
  ['Свеча', 'Тренер у сетки, ученик с задней линии бьёт свечу через тренера', ['feed', 'lob'], 'cp'],
  ['Перекидка в парах', 'Ученики в парах играют друг с другом по линии', ['drive'], 'pp'],
  ['Группа с корзины', 'Группа из трёх учеников по очереди бьёт форхенд кросс с корзины', ['feed', 'drive'], 'cpp'],
  ['Резаный бэкхенд', 'Тренер набрасывает, ученик бьёт резаный бэкхенд глубоко по линии', ['feed', 'slice'], 'cp'],
  ['Игра с лёта', 'Двое учеников у сетки играют с лёта друг с другом', ['volley'], 'pp']
];
const exOf = (c, i) => ({ id: 'user_v47_' + i, title: c[0], brief: c[1], setup: '', steps: '', stroke: 'Удары с отскока', format: '', diagram: 'crossMirror', goals: [], minutes: 10, level: 'Любой' });

test('описания тренера превращаются в сцену без ошибок: мяч в корте, через сетку, никто не идёт сквозь сетку', () => {
  const a = app();
  for (const [i, c] of CASES.entries()) {
    const r = a.read(`(() => { const e = ${JSON.stringify(exOf(c, i))}; const info = choreoFromText(e); const ch = info.ch;
      if (!ch) return { none: true, hints: info.hints };
      const run = animCompile(ch, false, 'direct');
      const splits = run.hits.filter((x) => x.foot && run.tracks[x.to] && run.tracks[x.to].c.role !== 'coach').map((x) => run.tracks[x.to].ev.some((v) => v.type === 'split' && Math.abs(v.tc - x.tc) < 1));
      return { kinds: [...new Set(ch.shots.map((s) => s.kind).filter(Boolean))], cast: ch.cast.map((x) => x.role[0]).join(''), b: animBounceIssues(ch, e), r: animRouteIssues(ch), shown: !!drillChoreo(e), splits,
        coachStarts: ch.cast.some((x) => x.role === 'coach') }; })()`);
    assert.ok(!r.none, c[0] + ': сцена не построена ' + JSON.stringify(r.hints));
    assert.deepEqual(r.b, [], c[0] + ': отскоки');
    assert.deepEqual(r.r, [], c[0] + ': пути');
    assert.ok(r.shown, c[0] + ': сцена не прошла проверки');
    for (const k of c[2]) assert.ok(r.kinds.includes(k), c[0] + ': нет удара ' + k + ' (' + r.kinds + ')');
    assert.equal(r.cast, c[3], c[0] + ': состав');
    assert.ok(r.splits.every(Boolean), c[0] + ': разножка у принимающего');
  }
});

test('неясное описание: подсказка, что уточнить; без ударов — без выдуманной сцены', () => {
  const a = app();
  const r = a.read(`(() => {
    const mk = (t) => ({ id: 'user_x', title: t, brief: t, setup: '', steps: '', stroke: 'Другое', format: '', diagram: 'crossMirror' });
    return { fh: choreoFromText(mk('Форхенд')), stretch: choreoFromText(mk('Растяжка мышц ног после тренировки')), kids: choreoFromText({ ...mk('Форхенд кросс'), court: 'red' }) };
  })()`);
  assert.ok(r.fh.ch, 'короткое описание — простая сцена по умолчанию');
  assert.ok(r.fh.hints.some((x) => /кто бьёт/.test(x)) && r.fh.hints.some((x) => /направлени/.test(x)));
  assert.equal(r.stretch.ch, null);
  assert.ok(/какие удары/.test(r.stretch.hints[0]));
  assert.equal(r.kids.ch, null);
});

test('изменённое стандартное упражнение анимируется по новому тексту; правка названия не ломает готовую сцену', () => {
  const a = app();
  const r = a.read(`(() => {
    const id = seedExercises.find((e) => DRILL_CHOREO[e.id] && e.stroke === 'Удары с отскока').id;
    store.exerciseOverrides[id] = { title: 'Новое имя' };
    const keep = drillChoreo(getEx(id)) === DRILL_CHOREO[id];
    store.exerciseOverrides[id] = { brief: 'Тренер набрасывает с корзины, ученик бьёт бэкхенд по линии', steps: '' };
    animChecked.clear();
    const ch = drillChoreo(getEx(id));
    return { keep, gen: !!(ch && ch.generated), hints: animHints(getEx(id)) };
  })()`);
  assert.ok(r.keep);
  assert.ok(r.gen);
  assert.deepEqual(r.hints, []);
});

test('схем больше нет: карточки, карусель записи и план показывают анимацию', () => {
  const a = app();
  const r = a.read(`(() => {
    const e = seedExercises[5];
    const p = { id: 'p1', kind: 'note', date: '2026-11-20', notes: 'x', sections: { ...emptySections(), main: [{ ...snapshotExercise(e), note: 'держать темп' }, snapshotExercise(seedExercises[9])] } };
    return { card: exerciseCard(e), view: noteViewExHTML(planExercises(p)), plan: planItemDetails(snapshotExercise(e), 1, false), preview: pickerPreviewHTML(e) };
  })()`);
  for (const [k, v] of Object.entries(r)) {
    assert.ok(/court-anim/.test(v), k + ': нет анимации');
    assert.ok(!/<svg[^>]*class="court/.test(v) && !/zoom-court/.test(v), k + ': осталась схема');
  }
  assert.ok(/1 из 2/.test(r.view) && /держать темп/.test(r.view));
});

test('календарь: одна точка на занятие (цвет тренера), не больше трёх и «+», число точек = числу занятий в списке дня', () => {
  const a = app();
  const r = a.read(`(() => {
    store.coaches = [{ id: 'c1', name: 'Илья' }, { id: 'c2', name: 'Илона' }];
    if (!store.students.length) store.students.push({ id: 's1', name: 'Маша' });
    const st = store.students[0];
    const today = dateISO(), ym = today.slice(0, 7);
    const base = { kind: 'note', status: 'done', studentIds: [st.id], studentId: st.id, targetType: 'student', studentName: st.name, groupIds: [], notes: 'кросс', sections: emptySections() };
    const I = [{ id: 'c1', name: 'Илья' }], O = [{ id: 'c2', name: 'Илона' }];
    let n = 0;
    const mk = (day, coaches, time) => ({ ...base, id: 'p' + (n += 1), date: ym + '-' + day, time, coaches });
    store.plans = [
      mk('10', [...I, ...O], '10:00'),
      mk('11', I, '09:00'), mk('11', I, '12:00'),
      mk('12', I, '09:00'), mk('12', O, '10:00'), mk('12', [], '11:00'), mk('12', O, '12:00'), mk('12', I, '13:00')
    ];
    calMonth = ''; calDay = '';
    const out = {};
    for (const d of ['10', '11', '12', '13']) {
      calDay = ym + '-' + d;
      const html = sessCalHTML();
      const cell = html.match(new RegExp('data-d="' + ym + '-' + d + '"[^>]*>.*?<span class="cal-dots">(.*?)</span></button>'))[1];
      const list = html.split('id="cal-day"')[1];
      out[d] = { dots: (cell.match(/<i /g) || []).length, more: /cal-more/.test(cell), items: (list.match(/class="cal-item"/g) || []).length, colors: (cell.match(/background:([^"]+)"/g) || []) };
    }
    return out;
  })()`);
  assert.equal(r['10'].dots, 1, 'одно занятие с двумя тренерами — одна точка');
  assert.equal(r['11'].dots, 2, 'два занятия — две точки');
  assert.equal(r['12'].dots, 3); assert.ok(r['12'].more, 'пять занятий — три точки и «+»');
  assert.equal(r['13'].dots, 0);
  for (const d of ['10', '11', '12', '13']) assert.equal(r[d].dots + (r[d].more ? 2 : 0) >= Math.min(r[d].items, 3), true, d + ': точки не меньше списка');
  assert.equal(r['10'].items, 1); assert.equal(r['11'].items, 2); assert.equal(r['12'].items, 5);
  assert.ok(r['11'].colors.every((c) => /wine/.test(c)), 'Илья — цвет по умолчанию');
});
