const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const sw = fs.readFileSync(path.join(__dirname, '../sw.js'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].split('\nrestoreDraft();')[0];

function app() {
  const storage = new Map();
  const node = { addEventListener() {}, body: null };
  const context = vm.createContext({
    window: node,
    document: { ...node, getElementById: () => null, querySelectorAll: () => [], querySelector: () => null, createElement: null, body: null },
    navigator: {}, confirm: () => true, clearTimeout() {}, setTimeout() {}, FormData: class {},
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) }
  });
  const run = (code) => vm.runInContext(code, context);
  run(script);
  return { run };
}

test('v55: version bump', () => {
  assert.match(sw, /VERSION = 'v55-20261128'/);
  assert.match(html, /sw\.js\?v=55/);
});

test('v55: one motion timing for windows, blocks and the calendar', () => {
  const a = app();
  assert.equal(a.run('SHEET_MS'), 350);
  assert.equal(a.run('FOLD_OPEN_MS'), 350);
  assert.equal(a.run('FOLD_CLOSE_MS'), 350);
  assert.equal(a.run('CAL_MS'), 350);
  assert.equal(a.run('CAL_EASE'), a.run('FOLD_EASE'));
  assert.match(html, /--dur-sheet:350ms/);
});

test('v55: iOS easing curve starts at 0, ends at 1 and never overshoots', () => {
  const a = app();
  let prev = -1;
  for (let i = 0; i <= 20; i += 1) {
    const v = a.run(`easeIOS(${i / 20})`);
    assert.ok(v >= prev - 1e-9 && v <= 1 + 1e-9, `step ${i}: ${v}`);
    prev = v;
  }
  assert.ok(Math.abs(a.run('easeIOS(0)')) < 1e-3);
  assert.ok(Math.abs(a.run('easeIOS(1)') - 1) < 1e-3);
});

test('v55: calendar title is a strip of three months that slides with the grid', () => {
  const a = app();
  a.run("calMonth = '2026-11'");
  const t = a.run('calTitleTrackHTML()');
  assert.equal((t.match(/class="cal-tm"/g) || []).length, 3);
  assert.match(t, /Октябрь[\s\S]*Ноябрь[\s\S]*Декабрь/);
  assert.equal((t.match(/aria-hidden="true"/g) || []).length, 2);
  assert.match(a.run("calTitleHTML('2027-01')"), /Январь <span class="cal-y">2027<\/span>/);
});

test('v55: tabs switch without the crossfade; cards no longer zoom into windows', () => {
  assert.match(html, /const enter = false;/);
  assert.match(html, /const f = null;\n  flipFrom = null;/);
  assert.match(html, /is-push/);
  assert.match(html, /function revealOnExpand/);
  assert.match(html, /function miniSnap/);
});
