"""v48 QA (WebKit 390/430, светлая и тёмная): четыре вкладки помещаются, воздух у фильтра и поиска, карточка занятия,
вкладка «Календарь» (точки = занятия, плавное листание), анимации вместо схем, нижние строки не спрятаны."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v48'); shots.mkdir(parents=True, exist_ok=True)
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
    mk('v47h', 20, '10:00', st[1], 0, 'Розыгрыши.', [], null),
    mk('v47i', 0, '13:00', st[2], 0, 'Подача.', [], null),
    mk('v47j', 3, '19:00', st[1], 1, 'Игра на счёт, второй сет.', [], null)
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
            tag = f'{w}-{theme}'; main = w == 390
            sfx = '-dark' if theme == 'dark' else ''
            c = b.new_context(viewport={'width': w, 'height': hgt}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
            pg = c.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda d: d.accept())
            pg.add_init_script("""try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}""")
            pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
            pg.evaluate(SEED); pg.wait_for_timeout(400)
            # вкладки
            nav = pg.evaluate("""() => [...document.querySelectorAll('.nav-item')].map((n) => { const r = n.getBoundingClientRect(), s = n.querySelector('span:not(.nav-indicator)'); return { t: s.textContent, l: r.left, r: r.right, ok: s.scrollWidth <= s.clientWidth + 1, vw: innerWidth }; })""")
            check([x['t'] for x in nav] == ['Тренировки', 'Календарь', 'Ученики', 'Упражнения'], f'{tag}: tab order {[x["t"] for x in nav]}')
            check(all(x['l'] >= 0 and x['r'] <= x['vw'] + 0.5 and x['ok'] for x in nav), f'{tag}: four tabs fit {nav}')
            if tag == '390-light': pg.screenshot(path=str(shots / 'v48-tabs-390.png'), clip={'x': 0, 'y': hgt - 90, 'width': w, 'height': 90})
            # воздух у поиска
            fold = pg.locator('.fold[data-fold="saved-plans"]')
            if 'is-open' not in (fold.get_attribute('class') or ''):
                fold.locator('.fold-head').first.tap(); pg.wait_for_timeout(500)
            check(pg.locator('.sess-seg').count() == 0, f'{tag}: no list/calendar switch')
            pg.evaluate("document.querySelector('#sess-filter').scrollIntoView({block:'start'}); window.scrollBy(0,-90)"); pg.wait_for_timeout(300)
            g = pg.evaluate("""() => { const r = (s) => document.querySelector(s).getBoundingClientRect(); return { filt: r('#sess-filter'), search: r('#sess-search'), day: r('#sess-list .sess-day') }; }""")
            check(g['search']['top'] - g['filt']['bottom'] >= 10, f"{tag}: air filter→search")
            check(g['day']['top'] - g['search']['bottom'] >= 16, f"{tag}: air search→first date")
            # карточка занятия
            pg.locator('.sess-card[data-id="v47a"]').first.tap(); pg.wait_for_timeout(900)
            m = pg.locator('#overlay .modal').last
            top = pg.evaluate("""() => { const m = [...document.querySelectorAll('#overlay .modal')].pop(); const q = (s) => { const e = m.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { t: r.top, b: r.bottom, l: r.left, r: r.right, text: e.textContent.trim() }; };
              const hs = [...m.querySelectorAll('.nv-h')].map((e) => { const c = getComputedStyle(e); return [e.textContent.trim(), c.fontSize, c.color, c.fontWeight]; });
              return { eyebrow: q('.nv-top .eyebrow'), edit: q('.nv-edit'), close: q('.nv-top .icon-button'), title: q('.nv-title'), by: q('.nv-by'), first: q('.nv-block'), hs, pill: m.querySelectorAll('.pill').length, bottom: q('.nv-bottom'), del: q('.nv-del'), copy: q('[data-action="copy-plan"]') }; }""")
            check(' · ' in top['eyebrow']['text'] and 'Занятие' not in top['eyebrow']['text'] and '18:00' in top['eyebrow']['text'], f"{tag}: date and time in one line {top['eyebrow']['text']}")
            check(abs(top['edit']['t'] - top['close']['t']) < 10 and top['edit']['r'] <= top['close']['l'] + 1, f'{tag}: edit next to close')
            check(top['pill'] == 0, f'{tag}: no «Запись» pill')
            gap_name = top['by']['t'] - top['title']['b']
            gap_sec = top['first']['t'] - top['by']['b']
            check(top['by'] and 2 <= gap_name <= 10, f"{tag}: author just under name ({gap_name:.0f}px)")
            check(16 <= gap_sec <= 24, f"{tag}: space before «Что делали» ({gap_sec:.0f}px)")
            heads = {x[0] for x in top['hs']}
            check({'Что делали', 'Упражнения', 'Отчёт'} <= heads, f'{tag}: three blocks {heads}')
            check(len({tuple(x[1:]) for x in top['hs']}) == 1, f"{tag}: same heading style {top['hs']}")
            check(m.locator('.nv-fold.is-open').count() == 0 and m.locator('.nex-card').count() == 3 and m.locator('.nex-count').inner_text() == '1 из 3', f'{tag}: report folded, carousel 1 of 3')
            pg.wait_for_timeout(500)
            check(m.locator('.nex-card .court-anim[data-mounted]').count() >= 1 and m.locator('svg.court').count() == 0, f'{tag}: mini animation, no scheme')
            if tag == '390-light': pg.screenshot(path=str(shots / 'v48-card-390.png'))
            if tag == '390-dark': pg.screenshot(path=str(shots / 'v48-card-390-dark.png'))
            m.locator('.nv-h-btn').tap(); pg.wait_for_timeout(700)
            check(m.locator('.nv-fold.is-open').count() == 1 and m.locator('.nv-report').is_visible() and 'Стабильный кросс' in m.locator('.nv-report').inner_text(), f'{tag}: report expands')
            pg.evaluate("(() => { const m = [...document.querySelectorAll('#overlay .modal')].pop(); m.scrollTop = m.scrollHeight; })()"); pg.wait_for_timeout(300)
            bt = pg.evaluate("""() => { const m = [...document.querySelectorAll('#overlay .modal')].pop(), mr = m.getBoundingClientRect(), d = m.querySelector('.nv-del').getBoundingClientRect(), c = m.querySelector('[data-action="copy-plan"]').getBoundingClientRect(); return { delB: d.bottom, mB: mr.bottom, cT: c.top, cB: c.bottom, dT: d.top, color: getComputedStyle(m.querySelector('.nv-del')).color }; }""")
            check(bt['delB'] <= bt['mB'] - 12 and bt['cT'] >= 0, f'{tag}: bottom buttons reachable with air {bt}')
            check(bt['dT'] - bt['cB'] >= 8, f'{tag}: gap between buttons')
            check(bt['color'].startswith('rgb(192, 57, 43)') or bt['color'].startswith('rgb(255, 122, 110)'), f"{tag}: delete is red {bt['color']}")
            if main and theme == 'light': pg.screenshot(path=str(shots / 'v48-card-report-390.png'))
            # без упражнений блока нет
            pg.evaluate("closeModal()"); pg.wait_for_timeout(500)
            pg.evaluate("openPlan('v47d')"); pg.wait_for_timeout(800)
            check(pg.locator('#overlay .modal').last.locator('.nex').count() == 0 and 'Упражнения' not in pg.locator('#overlay .modal').last.locator('.nv-h').all_inner_texts(), f'{tag}: no exercises block when empty')
            check(pg.locator('#overlay .modal').last.locator('#nv-report').count() == 0, f'{tag}: no report row when no report')
            pg.evaluate("closeModal()"); pg.wait_for_timeout(500)
            # календарь
            pg.locator('.nav-item[data-view="calendar"]').tap(); pg.wait_for_timeout(700)
            cal = pg.locator('#sess-cal')
            days = pg.evaluate("(() => { const [Y,M] = dateISO().split('-').map(Number); return new Date(Y, M, 0).getDate(); })()")
            pane = cal.locator('.cal-pane').nth(1)
            check(pane.locator('.cal-d:not(.is-blank)').count() == days, f'{tag}: month grid')
            check(pane.locator('.cal-d.is-today.is-sel').count() == 1, f'{tag}: today selected')
            ok = pg.evaluate("""() => { const out = []; document.querySelectorAll('#cal-track .cal-pane')[1].querySelectorAll('.cal-d.has').forEach((b) => out.push([b.dataset.d, +b.dataset.n, b.querySelectorAll('.cal-dots i').length, !!b.querySelector('.cal-more')])); return out; }""")
            check(all(d[2] == min(d[1], 3) and d[3] == (d[1] > 3) for d in ok), f'{tag}: dots = sessions {ok}')
            today_dots = pg.evaluate("document.querySelector('#cal-track .cal-pane:nth-child(2) .cal-d.is-today .cal-dots').children.length")
            n_today = pg.evaluate("plansToday = store.plans.filter(p => p.date === dateISO() && calDone(p)).length")
            check(today_dots == min(n_today, 3) and cal.locator('.cal-item').count() == n_today, f'{tag}: today dots {today_dots} = list {cal.locator(".cal-item").count()} = {n_today}')
            check(cal.locator('.cal-item').first.locator('.cal-time').inner_text() == '09:30', f'{tag}: day list sorted by time')
            if tag == '390-light': pg.screenshot(path=str(shots / 'v48-calendar-390.png'))
            if tag == '390-dark': pg.screenshot(path=str(shots / 'v48-calendar-390-dark.png'))
            # листание: плавное, ~0,42 с, не мгновенно
            t0 = pg.evaluate("(() => { const t = document.getElementById('cal-title').textContent; return t; })()")
            cal.locator('[data-action="cal-next"]').tap(); pg.wait_for_timeout(120)
            mid = pg.evaluate("(() => { const tr = document.getElementById('cal-track'); return { m: calMonth, x: new DOMMatrix(getComputedStyle(tr).transform).m41, w: document.getElementById('cal-view').clientWidth }; })()")
            check(-2 * mid['w'] < mid['x'] < -mid['w'] and mid['m'] != '', f"{tag}: mid-slide, not instant {mid}")
            pg.wait_for_timeout(150)
            still = pg.evaluate("document.getElementById('cal-title').textContent")
            check(pg.evaluate("calBusy") is True and still == t0, f'{tag}: month still sliding at ~270 ms')
            pg.wait_for_timeout(450)
            check(pg.evaluate("calBusy") is False and pg.evaluate("document.getElementById('cal-title').textContent") != t0, f'{tag}: month changed after slide')
            cal.locator('[data-action="cal-prev"]').tap(); pg.wait_for_timeout(750)
            check(pg.evaluate("document.getElementById('cal-title').textContent") == t0, f'{tag}: back to the month')
            for _ in range(2):
                cal.locator('[data-action="cal-next"]').tap(); pg.wait_for_timeout(700)
            cal.locator('[data-action="cal-today"]').tap(); pg.wait_for_timeout(750)
            check(pg.evaluate("document.getElementById('cal-title').textContent") == t0 and pg.evaluate("calBusy") is False, f'{tag}: «Сегодня» returns from two months away')
            pg.evaluate("document.getElementById('cal-filter').selectedIndex = 1; document.getElementById('cal-filter').dispatchEvent(new Event('change', { bubbles: true }))"); pg.wait_for_timeout(400)
            check(pg.locator('#cal-filter').count() == 1 and cal.locator('.cal-item').count() <= n_today, f'{tag}: filter in calendar')
            pg.evaluate("document.getElementById('cal-filter').selectedIndex = 0; document.getElementById('cal-filter').dispatchEvent(new Event('change', { bubbles: true }))"); pg.wait_for_timeout(300)
            cal.locator('.cal-item').first.tap(); pg.wait_for_timeout(800)
            check('Воле у сетки' in pg.locator('#overlay').inner_text(), f'{tag}: tap on session opens record')
            pg.evaluate("closeModal()"); pg.wait_for_timeout(500)
            # библиотека: только анимации
            pg.locator('.nav-item[data-view="exercises"]').tap(); pg.wait_for_timeout(600)
            folds = pg.locator('#exerciseList .fold:not(.is-open) .fold-head')
            if folds.count(): folds.first.tap(); pg.wait_for_timeout(1500)
            st = pg.evaluate("({ svg: document.querySelectorAll('svg.court').length, mounted: document.querySelectorAll('#exerciseList .court-anim[data-mounted]').length })")
            check(st['svg'] == 0 and st['mounted'] >= 1, f'{tag}: library animations only {st}')
            check(not errs, f'{tag}: page errors {errs}')
            print('done', tag); c.close()
    b.close()
print('FAILS', fails)
if fails: sys.exit(1)
print('PASS v48 WebKit 390/430 light/dark')
