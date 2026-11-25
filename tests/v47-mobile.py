"""v47 QA (WebKit 390/430, светлая и тёмная): воздух у поиска и фильтра, просмотр записи (отчёт свёрнут, карусель
с анимацией), календарь занятий, анимации вместо схем во всех местах, нижние строки не спрятаны."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v47'); shots.mkdir(parents=True, exist_ok=True)
SEED = """() => {
  ['Игорь Петров', 'Маша Соколова', 'Даня Орлов'].forEach((n, i) => { if (store.students.length <= i) store.students.push({ id: 's_v47_' + i, name: n, age: '', level: 'Средний', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() }); });
  const st = store.students.slice(0, 3);
  const today = dateISO();
  const ex = (i, note) => ({ ...snapshotExercise(seedExercises[i]), ...(note ? { note } : {}) });
  const co = [{ id: 'coach_ilya', name: 'Илья' }, { id: 'coach_ilona', name: 'Илона' }];
  const mk = (id, shift, time, s, c, notes, exs, summary) => ({ id, kind: 'note', status: 'done', date: isoShift(today, -shift), ...(time ? { time } : {}),
    targetType: 'student', studentId: s.id, studentName: s.name, studentIds: [s.id], groupIds: [], coaches: c ? [co[c - 1]] : [], actualStudentIds: [s.id],
    goal: notes, notes, sections: { ...emptySections(), main: exs }, summary, createdAt: nowISO(), createdBy: store.coachId });
  store.plans = [
    mk('v47a', 0, '18:00', st[0], 1, 'Кросс справа и подача с первым ударом. Закончили приёмом в центр.', [ex(5, 'Глубже по диагонали'), ex(9), ex(40)], { success: 'Стабильный кросс справа', difficulty: 'Второй мяч после подачи', next: 'Подача + первый удар в угол' }),
    mk('v47b', 0, '09:30', st[1], 2, 'Воле у сетки и смэш.', [ex(60)], null),
    mk('v47c', 2, '17:00', st[2], 1, 'Бэкхенд по линии с корзины.', [ex(20)], { success: 'Ровнее по линии', difficulty: '', next: '' }),
    mk('v47d', 3, '', st[0], 2, 'Игра на счёт.', [], null),
    mk('v47e', 6, '19:00', st[1], 1, 'Подход и выход к сетке.', [ex(70)], null),
    mk('v47f', 6, '11:00', st[2], 2, 'Приём подачи.', [], null),
    mk('v47g', 12, '18:30', st[0], 1, 'Работа ног.', [], null),
    mk('v47h', 20, '10:00', st[1], 0, 'Розыгрыши.', [], null)
  ];
  persist(); navigate('training'); render();
}"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, hgt in ((390, 844), (430, 932)):
        for theme in ('light', 'dark'):
            tag = f'{w}-{theme}'; main = tag == '390-light'
            c = b.new_context(viewport={'width': w, 'height': hgt}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
            pg = c.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda d: d.accept())
            pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
            pg.evaluate(SEED); pg.wait_for_timeout(400)
            pg.evaluate("localStorage.removeItem('tennis_coach_sess_view_v1'); setSessView('list')")
            fold = pg.locator('.fold[data-fold="saved-plans"]')
            if 'is-open' not in (fold.get_attribute('class') or ''):
                fold.locator('.fold-head').first.tap(); pg.wait_for_timeout(500)
            pg.evaluate("document.querySelector('.sess-seg').scrollIntoView({block:'start'}); window.scrollBy(0,-70)"); pg.wait_for_timeout(300)
            g = pg.evaluate("""() => { const r = (s) => document.querySelector(s).getBoundingClientRect();
              const day = document.querySelector('#sess-list .sess-day');
              return { seg: r('.sess-seg'), filt: r('#sess-filter'), search: r('#sess-search'), day: day.getBoundingClientRect() }; }""")
            check(g['filt']['top'] - g['seg']['bottom'] >= 10, f"{tag}: air seg→filter {g['filt']['top'] - g['seg']['bottom']}")
            check(g['search']['top'] - g['filt']['bottom'] >= 10, f"{tag}: air filter→search {g['search']['top'] - g['filt']['bottom']}")
            check(g['day']['top'] - g['search']['bottom'] >= 16, f"{tag}: air search→first date {g['day']['top'] - g['search']['bottom']}")
            if main: pg.screenshot(path=str(shots / 'v47-filter-search-390.png'))
            # просмотр записи
            pg.locator('.sess-card[data-id="v47a"]').first.tap(); pg.wait_for_timeout(900)
            m = pg.locator('#overlay .modal').last
            rf = m.locator('.fold[data-fold="note-view-report"]')
            check(rf.count() == 1 and 'is-open' not in (rf.get_attribute('class') or ''), f'{tag}: report folded')
            check(m.locator('.detail-section h4', has_text='Что получилось').count() == 0, f'{tag}: no separate report blocks')
            check(m.locator('.nex-card').count() == 3 and m.locator('.nex-count').inner_text() == '1 из 3', f'{tag}: view carousel 1 of 3')
            pg.wait_for_timeout(600)
            check(m.locator('.nex-card .court-anim[data-mounted]').count() >= 1, f'{tag}: mini animation mounted in view')
            check(m.locator('svg.court').count() == 0, f'{tag}: no static scheme in view')
            if main: pg.screenshot(path=str(shots / 'v47-record-view-390.png'))
            m.locator('.nex-track').evaluate("t => t.scrollLeft = t.clientWidth + 10"); pg.wait_for_timeout(400)
            check(m.locator('.nex-count').inner_text() == '2 из 3', f'{tag}: view carousel swipe')
            rf.locator('.fold-head').tap(); pg.wait_for_timeout(600)
            check('is-open' in (rf.get_attribute('class') or '') and 'Стабильный кросс' in rf.inner_text(), f'{tag}: report expands')
            bottom = pg.evaluate("""() => { const m = [...document.querySelectorAll('#overlay .modal')].pop(); m.scrollTop = m.scrollHeight; const sc = m.closest('.sheet') || m;
              const b = m.querySelector('.detail-bottom').getBoundingClientRect(); return { b: b.bottom, h: innerHeight }; }""")
            pg.wait_for_timeout(200)
            check(bottom['b'] <= bottom['h'] + 1, f'{tag}: bottom buttons reachable {bottom}')
            if main: pg.screenshot(path=str(shots / 'v47-record-view-report-390.png'))
            pg.evaluate("closeModal()"); pg.wait_for_timeout(500)
            # календарь
            pg.locator('.sess-seg button[data-v="cal"]').tap(); pg.wait_for_timeout(500)
            cal = pg.locator('#sess-cal')
            check(cal.is_visible() and not pg.locator('#sess-pane-list').is_visible(), f'{tag}: calendar shown, list hidden')
            days = pg.evaluate("(() => { const [Y,M] = dateISO().split('-').map(Number); return new Date(Y, M, 0).getDate(); })()")
            check(cal.locator('.cal-d:not(.is-blank)').count() == days, f'{tag}: month grid')
            check(cal.locator('.cal-d.is-today.is-sel').count() == 1, f'{tag}: today selected')
            check(cal.locator('.cal-d.is-today .cal-dots i').count() == 2, f'{tag}: two coach colors today')
            items = cal.locator('.cal-item')
            check(items.count() == 2 and items.first.locator('.cal-time').inner_text() == '09:30', f'{tag}: day list sorted by time')
            pg.evaluate("document.querySelector('.cal').scrollIntoView({block:'start'}); window.scrollBy(0,-64)"); pg.wait_for_timeout(300)
            lastb = pg.evaluate("""() => { const it = [...document.querySelectorAll('.cal-item')].pop(); const tb = document.querySelector('.tabbar, nav.tabs, .bottom-nav');
              const r = it.getBoundingClientRect(); return { b: r.bottom, lim: tb ? tb.getBoundingClientRect().top : innerHeight }; }""")
            if main: pg.screenshot(path=str(shots / 'v47-calendar-390.png'))
            if tag == '390-dark': pg.screenshot(path=str(shots / 'v47-calendar-390-dark.png'))
            if lastb['b'] > lastb['lim']:
                pg.evaluate("window.scrollBy(0, 200)"); pg.wait_for_timeout(200)
            # день без времени и другой цвет
            d3 = pg.evaluate("isoShift(dateISO(), -3)")
            if d3[:7] == pg.evaluate("dateISO().slice(0,7)"):
                cal.locator(f'.cal-d[data-d="{d3}"]').tap(); pg.wait_for_timeout(300)
                check('Без' in cal.locator('.cal-item .cal-time').first.inner_text(), f'{tag}: no-time label')
            cal.locator('[data-action="cal-prev"]').tap(); pg.wait_for_timeout(350)
            check(cal.locator('.cal-today').count() == 1, f'{tag}: today button in other month')
            cal.locator('.cal-today').tap(); pg.wait_for_timeout(350)
            cal.locator('.cal-item').first.tap(); pg.wait_for_timeout(800)
            check(pg.locator('#overlay .modal').last.locator('.modal-head, h2').first.count() >= 1 and 'Воле у сетки' in pg.locator('#overlay').inner_text(), f'{tag}: tap opens record')
            pg.evaluate("closeModal()"); pg.wait_for_timeout(500)
            # фильтр работает и в календаре
            pg.select_option('#sess-filter', index=1); pg.wait_for_timeout(400)
            check(cal.locator('.cal-item').count() <= 1, f'{tag}: filter applies to calendar')
            pg.select_option('#sess-filter', index=0); pg.wait_for_timeout(200)
            pg.evaluate("setSessView('list')")
            # библиотека: только анимации, играют только видимые
            pg.evaluate("navigate('exercises'); render(); window.scrollTo(0,0)"); pg.wait_for_timeout(500)
            folds = pg.locator('#exerciseList .fold:not(.is-open) .fold-head')
            if folds.count(): folds.first.tap(); pg.wait_for_timeout(1500)
            st = pg.evaluate("""() => ({ svg: document.querySelectorAll('svg.court').length, mini: document.querySelectorAll('#exerciseList .court-anim').length,
              mounted: document.querySelectorAll('#exerciseList .court-anim[data-mounted]').length,
              vis: [...animInsts].filter((i) => i.visible).length, all: animInsts.size })""")
            check(st['svg'] == 0, f'{tag}: no static scheme in library {st}')
            check(st['mounted'] >= 1 and st['mounted'] < max(2, st['mini']), f'{tag}: lazy mount {st}')
            if main: pg.screenshot(path=str(shots / 'v47-library-390.png'))
            check(not errs, f'{tag}: page errors {errs}')
            print('done', tag); c.close()
    b.close()
print('FAILS', fails)
if fails: sys.exit(1)
print('PASS v47 WebKit 390/430 light/dark')
