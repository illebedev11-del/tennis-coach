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

test('календарь: сетка месяца, сегодня, отметки двух тренеров разными цветами, занятия дня по времени', () => {
  const a = app();
  const r = a.read(`(() => {
    store.coaches = [{ id: 'c1', name: 'Илья' }, { id: 'c2', name: 'Илона' }];
    const st = store.students[0] || { id: 's1', name: 'Маша' };
    if (!store.students.length) store.students.push(st);
    const today = dateISO();
    const base = { kind: 'note', status: 'done', studentIds: [st.id], studentId: st.id, targetType: 'student', studentName: st.name, groupIds: [], notes: 'кросс', sections: emptySections() };
    store.plans = [{ ...base, id: 'a', date: today, time: '18:00', coaches: [{ id: 'c1', name: 'Илья' }] }, { ...base, id: 'b', date: today, time: '09:30', coaches: [{ id: 'c2', name: 'Илона' }] }];
    calMonth = ''; calDay = '';
    const html = sessCalHTML();
    const [Y, M] = today.split('-').map(Number);
    return { html, days: new Date(Y, M, 0).getDate() };
  })()`);
  const cells = r.html.match(/data-action="cal-day"/g) || [];
  assert.equal(cells.length, r.days);
  assert.ok(/cal-d is-today is-sel has/.test(r.html));
  const dots = r.html.match(/is-today[^>]*>.*?<span class="cal-dots">(.*?)<\/span>/)[1];
  assert.equal((dots.match(/<i /g) || []).length, 2, 'два цвета у дня с двумя тренерами');
  assert.ok(/Илья/.test(r.html) && /Илона/.test(r.html), 'подпись цветов');
  assert.ok(r.html.indexOf('09:30') < r.html.indexOf('18:00'), 'занятия дня по времени');
});
