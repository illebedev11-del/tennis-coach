"""v52 QA: вопрос «Кто пользуется этим телефоном?» и переименование старых записей без автора."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v52'); shots.mkdir(parents=True, exist_ok=True)
SHOT = True
SEED = """() => {
  store.students = [{ id: 's1', name: 'Ваня', age: '', level: 'Средний', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() }];
  const st = store.students[0];
  const ilya = { id: 'coach_ilya', name: 'Илья' }, ilona = { id: 'coach_ilona', name: 'Илона' };
  const mk = (id, at, coaches, notes) => normalizePlan({ id, kind: 'note', status: 'done', date: '2026-11-20', time: '18:00',
    targetType: 'student', studentId: st.id, studentName: st.name, studentIds: [st.id], groupIds: [], coaches, actualStudentIds: [st.id],
    goal: notes, notes, sections: emptySections(), summary: null, createdAt: at, createdBy: store.coachId });
  store.plans = [
    mk('old-empty', '2026-11-10T10:00:00.000Z', [ilya], 'Старая запись без автора'),
    mk('old-ilona', '2026-11-10T10:00:00.000Z', [ilona], 'Уже была Илона'),
    mk('new-ilya', '2026-11-28T10:30:00.000Z', [ilya], 'Новая после обновления')
  ];
  persist(); navigate('training'); render();
}"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
with sync_playwright() as p:
    b = p.webkit.launch()
    for theme in ('light', 'dark'):
        tag = theme
        c = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
        pg = c.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
        pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(500)
        # даже на пустом запуске вопрос появляется и его нельзя закрыть касанием фона
        check(pg.locator('#owner-prompt.is-on').count() == 1, f'{tag}: prompt on empty launch')
        title = pg.locator('#owner-title').inner_text()
        check(title == 'Кто пользуется этим телефоном?', f'{tag}: title {title}')
        pg.locator('#owner-prompt').tap(position={'x': 8, 'y': 8}); pg.wait_for_timeout(300)
        check(pg.locator('#owner-prompt.is-on').count() == 1, f'{tag}: veil does not dismiss')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        check(pg.locator('#owner-prompt.is-on').count() == 1, f'{tag}: Escape does not dismiss')
        # размеры как у системного окна
        box = pg.evaluate("""() => { const a = document.querySelector('.owner-alert'), t = document.querySelector('.owner-title'), b = [...document.querySelectorAll('.owner-btn')].map((x) => x.getBoundingClientRect());
          const r = a.getBoundingClientRect(); return { w: r.width, h: r.height, tw: t.getBoundingClientRect().width, bh: Math.min(...b.map((x) => x.height)), n: b.length, left: r.left, right: r.right, vw: innerWidth }; }""")
        check(box['n'] == 2 and box['bh'] >= 44 and box['w'] <= 270.5 and box['left'] > 20 and box['right'] < box['vw'] - 20, f'{tag}: alert geometry {box}')
        if SHOT and theme == 'light':
            pg.screenshot(path=str(shots / 'v52-owner-prompt-light-390.png'))
        if SHOT and theme == 'dark':
            pg.screenshot(path=str(shots / 'v52-owner-prompt-dark-390.png'))
        pg.evaluate("closeOwnerPrompt()"); pg.wait_for_timeout(300)
        c.close()

        # отдельный запуск: данные + выбор Илоны
        c = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
        pg = c.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
        pg.evaluate("document.getElementById('owner-prompt') && document.getElementById('owner-prompt').remove()");
        pg.evaluate(SEED); pg.wait_for_timeout(300)
        pg.evaluate("maybeOwnerPrompt()"); pg.wait_for_timeout(400)
        check(pg.locator('#owner-prompt.is-on').count() == 1, f'{tag}: prompt with data')
        pg.locator('#owner-prompt .owner-btn[data-id="coach_ilona"]').tap(); pg.wait_for_timeout(700)
        check(pg.locator('#owner-prompt').count() == 0, f'{tag}: prompt closed after choice')
        state = pg.evaluate("""() => ({
          owner: localStorage.getItem('tennis_coach_device_owner'),
          last: localStorage.getItem('tennis_coach_last_coach'),
          map: Object.fromEntries(store.plans.map((p) => [p.id, p.coaches.map((c) => c.id).join('+')])),
          def: lastCoachId()
        })""")
        check(state['owner'] == 'coach_ilona' and state['last'] == 'coach_ilona' and state['def'] == 'coach_ilona', f'{tag}: owner stored {state}')
        check(state['map']['old-empty'] == 'coach_ilona', f'{tag}: old auto-filled became Илона {state["map"]}')
        check(state['map']['old-ilona'] == 'coach_ilona', f'{tag}: explicit Илона kept')
        check(state['map']['new-ilya'] == 'coach_ilya', f'{tag}: post-v51 Илья kept {state["map"]}')
        # повторный запуск не показывает вопрос
        pg.reload(); pg.wait_for_timeout(500)
        check(pg.locator('#owner-prompt').count() == 0, f'{tag}: prompt only once')
        # в настройках можно сменить имя: записи не трогаем
        pg.evaluate("settings()"); pg.wait_for_timeout(600)
        check(pg.locator('#coach-settings .coach-seg .coach-opt.is-on').inner_text().strip() == 'Илона', f'{tag}: settings shows Илона')
        before = pg.evaluate("JSON.stringify(store.plans.map((p) => p.coaches))")
        pg.locator('#coach-settings [data-action="set-owner"][data-id="coach_ilya"]').tap(); pg.wait_for_timeout(400)
        after = pg.evaluate("JSON.stringify(store.plans.map((p) => p.coaches))")
        check(before == after, f'{tag}: settings change does not touch records')
        check(pg.evaluate("localStorage.getItem('tennis_coach_device_owner')") == 'coach_ilya', f'{tag}: settings updates default')
        check(not errs, f'{tag}: page errors {errs}')
        print('done', tag); c.close()
    b.close()
print('FAILS', len(fails))
if fails: sys.exit(1)
print('PASS v52 WebKit 390 light/dark: prompt, reassignment, settings default')
