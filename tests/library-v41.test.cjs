// v41: единый вид карточек — пронумерованные шаги, без обращения на «вы», подача «в «Т»».
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const start = html.indexOf('const seedExercises = ') + 'const seedExercises = '.length;
const seed = JSON.parse(html.slice(start, html.indexOf('\n];\n', start) + 2));
const TEXT = ['title', 'brief', 'setup', 'steps', 'cue', 'errors', 'easier', 'harder', 'metric', 'equipment'];

test('every drill has numbered steps 1., 2., 3. …', () => {
  const bad = seed.filter((e) => e.steps.split('\n').some((line, i) => !line.startsWith(`${i + 1}. `))).map((e) => e.id);
  assert.deepEqual(bad, []);
});

test('drill texts do not address the reader as «вы»', () => {
  const vy = /(^|[^А-Яа-яЁё])([Вв]ы|[Вв]ас|[Вв]аш[а-яё]*|[А-Яа-яЁё]+(ьте|йте|ите)(сь)?)(?![А-Яа-яЁё])/g;
  const allowed = new Set(['защите']);
  const hits = [];
  for (const e of seed) for (const f of TEXT) for (const m of (e[f] || '').matchAll(vy)) if (!allowed.has(m[2].toLowerCase())) hits.push(`${e.id}.${f}: ${m[2]}`);
  assert.deepEqual(hits, []);
});

test('serve direction to the centre line is written «в «Т»»', () => {
  const hits = seed.filter((e) => TEXT.some((f) => /([Пп]одач[аиу]|подавать) в центр(?!альн)/.test(e[f] || ''))).map((e) => e.id);
  assert.deepEqual(hits, []);
  assert.equal(seed.find((e) => e.id === 'se10').title, 'Подача в «Т» и в корпус');
});
