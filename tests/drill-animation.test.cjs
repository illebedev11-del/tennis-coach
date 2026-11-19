// v43: анимации всех встроенных упражнений — сцена есть у каждого, отскоки по правилам,
// никто не ходит сквозь сетку и по лавочке, состав совпадает с текстом, надписи рисуются.
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

const NET_Y = 11.885;
// Независимая геометрия кортов (как на статичной схеме)
const GEO = {
  full: { l: 1.37, r: 9.6, dl: 0, dr: 10.97, top: 0, bot: 23.77, base: 1.5, serv: [5.485, 18.285], net: [-0.91, 11.88] },
  orange: { l: 1.37, r: 9.6, dl: 1.37, dr: 9.6, top: 2.74, bot: 21.03, base: 1.0, serv: [5.485, 18.285], net: [0.6, 10.37] },
  red: { l: 2.435, r: 8.535, dl: 2.435, dr: 8.535, top: 5.485, bot: 18.285, base: 0.8, serv: null, net: [1.9, 9.07] }
};
const EPS = 1e-9;

let cache = null;
function all() {
  if (cache) return cache;
  const a = app();
  cache = a.read(`seedExercises.map((e) => {
    const ch = DRILL_CHOREO[e.id];
    if (!ch) return { id: e.id, missing: true };
    const court = ch.court || courtKind(e);
    const c2 = { ...ch, court };
    const runs = [];
    for (const mir of [false, true]) for (const md of ['intro', 'bench', 'direct']) {
      const run = animCompile(c2, mir, md), paths = [];
      for (const tr of run.cast) {
        const pts = [];
        for (let t = 0; t < run.tEnd; t += 40) {
          const sit = tr.ev.some((v) => v.type === 'sit' && t >= v.t0 && t < v.t1);
          pts.push([...animTrackPos(tr, t).p, sit ? 1 : 0]);
        }
        paths.push({ id: tr.c.id, pts });
      }
      runs.push({ mir, md, paths, bounces: md === 'direct' && !mir ? run.bounces : null, tEnd: run.tEnd });
    }
    const text = animDrillText(e);
    return { id: e.id, court, ch, text, shown: !!drillChoreo(e), spec: animSpecIssues(c2), bounce: animBounceIssues(c2, e), route: animRouteIssues(c2),
      outOk: animOutAllowed(e), wide: /парн/.test(text), labels: animSideLabels(c2), font: Object.keys(ANIM_FONT), runs };
  })`);
  return cache;
}

test('every built-in drill has a valid hand-written choreography that is shown', () => {
  const list = all();
  assert.equal(list.length, 161);
  const missing = list.filter((x) => x.missing).map((x) => x.id);
  assert.deepEqual(missing, []);
  for (const x of list) {
    assert.equal(x.shown, true, x.id + ' не показывается');
    assert.deepEqual(x.spec, [], x.id);
    assert.ok(x.ch.shots.length >= 2, x.id + ': слишком мало шагов');
    const sec = x.runs.find((r) => r.md === 'intro' && !r.mir).tEnd / 1000;
    assert.ok(sec > 6 && sec < 40, x.id + ': длительность ' + sec);
  }
  // пилоты v39 сохранены
  const by = Object.fromEntries(list.map((x) => [x.id, x]));
  assert.deepEqual(by.nt02.ch.start, { p: [5.1, 18.7], c: [7.3, -0.25] });
  assert.deepEqual(by.kb01.ch.shots[0].bounce, [7.9, 20.4]);
  assert.ok(by.gs01.ch.shots.length > 0);
});

test('bounces follow the rules: other side, inside the court with margins, serves in the diagonal box', () => {
  const bad = [];
  for (const x of all()) {
    assert.deepEqual(x.bounce, [], x.id);
    const g = GEO[x.court];
    const b = x.runs.find((r) => r.bounces).bounces;
    for (const s of b) {
      const [bx, by] = s.B, tag = `${x.id}#${s.i}`;
      const hitterFar = s.hy < NET_Y;
      if (!s.same && (hitterFar ? by <= NET_Y : by >= NET_Y)) bad.push(tag + ' на своей стороне');
      if (s.out && x.outOk) continue;
      if (s.kind === 'serve') {
        const sl = g.serv ? (by > NET_Y ? g.serv[1] : g.serv[0]) : (by > NET_Y ? g.bot : g.top);
        if (by > NET_Y ? by > sl - 0.2 + EPS || by < NET_Y + 0.2 - EPS : by < sl + 0.2 - EPS || by > NET_Y - 0.2 + EPS) bad.push(tag + ' подача мимо квадрата');
        if (bx < g.l + 0.2 - EPS || bx > g.r - 0.2 + EPS) bad.push(tag + ' подача за боковую');
        if (g.serv && !s.straight && (s.hx - 5.485) * (bx - 5.485) > 0) bad.push(tag + ' подача не по диагонали');
        continue;
      }
      const lo = x.wide && s.dir ? g.dl : g.l, hi = x.wide && s.dir ? g.dr : g.r;
      if (s.dir) { if (bx < lo + 0.5 - EPS || bx > hi - 0.5 + EPS) bad.push(tag + ' у боковой ' + bx); }
      else if (Math.abs(bx - 5.485) > 2 + EPS) bad.push(tag + ' без направления далеко от центра ' + bx);
      if (by < g.top + g.base - EPS || by > g.bot - g.base + EPS) bad.push(tag + ' у задней ' + by);
    }
  }
  assert.deepEqual(bad, []);
});

test('routes: nobody walks through the net, over the bench bags, or stands on the net or the labels', () => {
  const bad = [];
  for (const x of all()) {
    assert.deepEqual(x.route, [], x.id);
    const g = GEO[x.court];
    for (const r of x.runs) for (const p of r.paths) {
      let prev = null;
      for (const [px, py, sit] of p.pts) {
        const name = `${x.id}/${p.id}/${r.md}${r.mir ? '/левша' : ''}`;
        if (sit) { prev = null; continue; }
        if (prev && (prev[1] - NET_Y) * (py - NET_Y) < 0) {
          const u = (NET_Y - prev[1]) / (py - prev[1]), cx = prev[0] + (px - prev[0]) * u;
          if (cx > g.net[0] - 0.1 && cx < g.net[1] + 0.1) { bad.push(name + ' сквозь сетку'); break; }
        }
        if (px < -1.75 && px > -2.75 && py > 6 && py < 17.5) { bad.push(name + ' по лавочке'); break; }
        prev = [px, py];
      }
    }
  }
  assert.deepEqual([...new Set(bad)], []);
});

test('casting matches the text: a coach is on court exactly when the drill mentions the coach', () => {
  for (const x of all()) {
    const coach = x.ch.cast.some((c) => c.role === 'coach');
    assert.equal(coach, /тренер/.test(x.text), x.id);
  }
});

test('labels name who stands on each side and every glyph renders within the field', () => {
  const ok = new Set(['', 'Тренер', 'Ученик', 'Ученики', 'Тренер и ученик', 'Тренер и ученики']);
  for (const x of all()) {
    const font = new Set(x.font);
    for (const side of ['far', 'near']) {
      const t = x.labels[side];
      assert.ok(ok.has(t), x.id + ' ' + side + ': ' + t);
      assert.ok([...t.toUpperCase()].every((c) => font.has(c)), x.id + ': нет глифа в «' + t + '»');
      const n = [...t].length;
      assert.ok(n * 6 + Math.max(0, n - 1) <= 124, x.id + ': надпись не помещается');
    }
    // надпись соответствует тем, кто стоит на стороне в начале
    const cast = x.ch.cast.filter((c) => !c.aside);
    const far = cast.filter((c) => x.ch.start[c.id][1] < NET_Y), near = cast.filter((c) => x.ch.start[c.id][1] > NET_Y);
    if (!x.ch.labels) {
      assert.equal(x.labels.far === '', far.length === 0, x.id + ' far');
      assert.equal(x.labels.near === '', near.length === 0, x.id + ' near');
      for (const [list, t] of [[far, x.labels.far], [near, x.labels.near]]) {
        if (!list.length) continue;
        assert.equal(/Тренер/.test(t), list.some((c) => c.role === 'coach'), x.id + ': ' + t);
        assert.equal(/ученик/i.test(t), list.some((c) => c.role !== 'coach'), x.id + ': ' + t);
      }
    }
  }
});

test('validators reject bad scenes', () => {
  const a = app();
  const r = a.read(`(() => {
    const e = getEx('gs01'), base = DRILL_CHOREO.gs01, s0 = base.shots[0];
    const mk = (b, extra) => ({ ...base, shots: [{ ...s0, bounce: b, ...(extra || {}) }] });
    const fy = s0.bounce[1];
    const se = getEx('se04'), sv = DRILL_CHOREO.se04;
    const mkS = (b) => ({ ...sv, shots: [{ ...sv.shots[0], bounce: b }] });
    const walk = { ...base, shots: [{ move: { [base.cast[0].id]: [5.0, NET_Y - 3] }, mode: 'jog' }] };
    return [
      animBounceIssues(mk([1.6, fy]), e).length > 0,
      animBounceIssues(mk([0.8, fy]), e).length > 0,
      animBounceIssues(mk([5.0, fy < 11.885 ? 1.0 : 22.8]), e).length > 0,
      animBounceIssues(mk([5.0, fy], { dir: '' }), e).length === 0,
      animBounceIssues(mk([8.5, fy], { dir: '' }), e).length > 0,
      animBounceIssues(mkS([7.0, 9.8]), se).length > 0,   // подача не по диагонали
      animBounceIssues(mkS([3.0, 4.0]), se).length > 0,   // подача за линию подачи
      animSpecIssues({ ...base, zones: [{ at: [1, 1] }] }).length > 0,
      animSpecIssues({ ...base, shots: [{ by: 'nobody' }] }).length > 0,
      animRouteIssues({ ...base, start: { ...base.start, [base.cast[0].id]: [5.0, NET_Y] } }).length > 0
    ];
  })()`);
  assert.deepEqual(r, [true, true, true, true, true, true, true, true, true, true]);
});

test('user-edited drills fall back to a generated scene or the static scheme', () => {
  const a = app();
  const r = a.read(`(() => {
    const before = drillChoreo(getEx('kb05')) === DRILL_CHOREO.kb05;
    store.exerciseOverrides = Object.assign(store.exerciseOverrides || {}, { kb05: { steps: '1. Своё описание без схемы.' } });
    const e = getEx('kb05'), ch = drillChoreo(e);
    const own = { id: 'u-own-1', title: 'Своё упражнение', brief: 'Кросс с партнёром', setup: '', steps: '1. Кросс.', format: 'С партнёром', diagram: 'cross' };
    const och = drillChoreo(own);
    const valid = (c, x) => !c || (animBounceIssues(c, x).length === 0 && animRouteIssues(c).length === 0);
    const fbs = seedExercises.map((x) => [x, choreoFallback(x)]).filter((p) => p[1]).map(([x, c]) => { c.court = c.court || courtKind(x); return valid(c, x); });
    return { before, edited: animEdited('kb05'), notBuiltin: ch !== DRILL_CHOREO.kb05, valid: valid(ch, e), own: valid(och, own), fbs: fbs.length, fbOk: fbs.every(Boolean) };
  })()`);
  assert.equal(r.before, true);
  assert.equal(r.edited, true);
  assert.equal(r.notBuiltin, true);
  assert.equal(r.valid, true);
  assert.equal(r.own, true);
  assert.ok(r.fbs > 40);
  assert.equal(r.fbOk, true);
});
