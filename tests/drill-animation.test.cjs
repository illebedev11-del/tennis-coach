// Анимации упражнений: каждый отскок — внутри одиночного корта, с запасом от линий.
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

// Независимая проверка тех же правил: 0,5 м от боковой одиночной (для направленных), 1,5 м от задней, без направления — ближе к центру.
const SIDE_L = 1.37 + 0.5, SIDE_R = 9.6 - 0.5, BASE_FAR = 1.5, BASE_NEAR = 23.77 - 1.5;
function bounceProblems(list) {
  const bad = [];
  for (const { id, ch, outOk } of list) {
    for (const [i, s] of ch.shots.entries()) {
      if (!s.bounce) continue;
      if (s.out && outOk) continue;
      const [x, y] = s.bounce;
      const hitterFar = (ch.start[s.by] || [0, 0])[1] < 11.885;
      if (hitterFar ? y <= 11.885 : y >= 11.885) bad.push(`${id}#${i}: отскок на стороне бьющего`);
      if (y < BASE_FAR - 1e-9 || y > BASE_NEAR + 1e-9) bad.push(`${id}#${i}: ближе 1,5 м к задней (${y})`);
      if (s.dir) { if (x < SIDE_L - 1e-9 || x > SIDE_R + 1e-9) bad.push(`${id}#${i}: ближе 0,5 м к боковой (${x})`); }
      else if (Math.abs(x - 5.485) > 2 + 1e-9) bad.push(`${id}#${i}: без направления, а далеко от центра (${x})`);
    }
  }
  return bad;
}

test('pilot choreographies: every bounce inside the singles court with margins', () => {
  const a = app();
  const list = a.read(`Object.keys(DRILL_CHOREO).map((id) => ({ id, ch: DRILL_CHOREO[id], outOk: animOutAllowed(getEx(id)), issues: animBounceIssues(DRILL_CHOREO[id], getEx(id)) }))`);
  assert.ok(list.length >= 3);
  for (const x of list) assert.deepEqual(x.issues, [], x.id);
  assert.deepEqual(bounceProblems(list), []);
  // пилоты реально показываются
  assert.deepEqual(a.read(`['gs01','nt02','kb01'].map((id) => !!drillChoreo(getEx(id)))`), [true, true, true]);
});

test('fallback generator: every bounce inside the singles court with margins', () => {
  const a = app();
  const list = a.read(`seedExercises.map((e) => ({ id: e.id, ch: choreoFallback(e), outOk: animOutAllowed(e) })).filter((x) => x.ch).map((x) => ({ ...x, issues: animBounceIssues(x.ch, getEx(x.id)) }))`);
  assert.ok(list.length > 40, 'fallback compiled for ' + list.length);
  for (const x of list) assert.deepEqual(x.issues, [], x.id);
  assert.deepEqual(bounceProblems(list), []);
});

test('validator rejects bounces near the lines and in the alley', () => {
  const a = app();
  const bad = a.read(`(() => {
    const base = DRILL_CHOREO.gs01, e = getEx('gs01');
    const mk = (b, extra) => ({ ...base, shots: [{ ...base.shots[0], bounce: b, ...(extra || {}) }] });
    const fy = base.shots[0].bounce[1];
    return [
      animBounceIssues(mk([1.6, fy]), e).length > 0,        // ближе 0,5 м к боковой
      animBounceIssues(mk([0.8, fy]), e).length > 0,        // коридор
      animBounceIssues(mk([5.0, fy < 11.885 ? 1.0 : 22.8]), e).length > 0, // у задней
      animBounceIssues(mk([5.0, fy], { dir: '' }), e).length === 0,
      animBounceIssues(mk([8.5, fy], { dir: '' }), e).length > 0  // без направления — к центру
    ];
  })()`);
  assert.deepEqual(bad, [true, true, true, true, true]);
});

test('casting: the coach plays with the student unless the drill says students play each other', () => {
  const a = app();
  const r = a.read(`(() => ({
    pilots: ['gs01', 'nt02', 'kb01'].map((id) => { const ch = DRILL_CHOREO[id], l = animSideLabels(ch); return [ch.cast.some((c) => c.role === 'coach'), l.far, l.near]; }),
    fallbackCoach: seedExercises.map((e) => [e, choreoFallback(e)]).filter((x) => x[1]).every(([e, ch]) => ch.cast.some((c) => c.role === 'coach') === !animStudentsOnly(e)),
    pairs: animStudentsOnly({ title: 'Кросс в парах', brief: 'Ученики играют друг с другом' }),
    plain: animStudentsOnly({ title: 'Кросс с партнёром', brief: 'Игроки за задними линиями' })
  }))()`);
  assert.deepEqual(r.pilots, [[true, 'Тренер', 'Ученик'], [true, 'Тренер', 'Ученик'], [true, 'Тренер', 'Ученик']]);
  assert.equal(r.fallbackCoach, true);
  assert.equal(r.pairs, true);
  assert.equal(r.plain, false);
});

test('walk paths: nobody walks through the net or over the bags at the bench', () => {
  const a = app();
  const r = a.read(`['gs01','nt02','kb01'].flatMap((id) => [false, true].flatMap((mir) => ['intro', 'bench'].map((md) => {
    const run = animCompile(DRILL_CHOREO[id], mir, md);
    let minX = 99, cross = 0;
    for (const tr of run.cast) {
      let prev = null;
      for (let t = 0; t < run.tEnd; t += 20) {
        if (tr.ev.some((e) => e.type === 'sit' && t >= e.t0 && t < e.t1)) { prev = null; continue; }
        const p = animTrackPos(tr, t).p;
        minX = Math.min(minX, p[0]);
        if (prev && (prev[1] - NET_Y) * (p[1] - NET_Y) < 0 && p[0] > -ANIM_POST - 0.1 && p[0] < COURT_W + ANIM_POST + 0.1) cross += 1;
        prev = p;
      }
    }
    return [id + (mir ? '-left' : '') + '-' + md, minX >= ANIM_BENCH.x + 0.75, cross];
  })))`);
  for (const [name, clear, cross] of r) { assert.equal(clear, true, name + ': too close to the bench bags'); assert.equal(cross, 0, name + ': walks through the net'); }
});
