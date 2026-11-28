"""v55 QA: плавность как в iPhone. WebKit 390×844, касания. Кадры и видео — в папку screens (v55-*).
Вкладки без растворения, месяц едет вместе с сеткой, шапка докручивается, «Все ученики» отпускает фокус,
«Отчёт» показывается целиком, окна выезжают снизу, профиль ученика въезжает справа и уходит вправо."""
import sys, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/workspace/tennis-coach-v1/screens'); shots.mkdir(parents=True, exist_ok=True)
OWNER = "try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}"
SEED = r"""() => {
  const names = ['Игорь Петров','Маша Соколова','Даня Орлов','Лиза Миронова','Артём Белов','Соня Котова','Глеб Жуков','Вера Лосева'];
  store.students = names.map((n, i) => normalizeStudent({ id: 's' + i, name: n, age: String(20 + i), level: 'Средний', hand: 'right', priority: 'Стабильность бэкхенда.' }));
  store.groups = [];
  const today = dateISO();
  const co = [{ id: 'coach_ilya', name: 'Илья' }, { id: 'coach_ilona', name: 'Илона' }];
  const mk = (id, shift, s, c, notes, summary) => normalizePlan({ id, kind: 'note', status: 'done', date: isoShift(today, -shift), time: '18:00',
    studentId: s.id, studentIds: [s.id], actualStudentIds: [s.id], groupIds: [], coaches: [co[c]], goal: notes, notes,
    sections: { ...emptySections(), main: [snapshotExercise(seedExercises[5]), snapshotExercise(seedExercises[9])] }, summary });
  store.plans = [];
  for (let i = 0; i < 12; i += 1) store.plans.push(mk('p' + i, i * 2, store.students[i % 8], i % 2, 'Кросс справа и подача с первым ударом. Закончили приёмом в центр.',
    { success: 'Стабильный кросс справа, ровнее по глубине, меньше ошибок в сетку.', difficulty: 'Второй мяч после подачи — поздно встаёт в стойку.', next: 'Подача + первый удар в угол, потом игра на счёт до 7.' }));
  persist();
}"""
fails = []
def check(ok, msg):
    print(('OK  ' if ok else 'FAIL') + ' ' + msg)
    if not ok: fails.append(msg)

def frames(pg, name, n=6, gap=60):
    for i in range(n):
        pg.screenshot(path=str(shots / f'v55-{name}-{i}.png'))
        pg.wait_for_timeout(gap)

TOUCH = """(o) => { const el = document.elementFromPoint(o.x, o.y) || document.body;
  const t = { identifier: 1, target: el, clientX: o.x, clientY: o.y, pageX: o.x, pageY: o.y + scrollY };
  const ev = new Event(o.type, { bubbles: true, cancelable: true });
  const list = o.type === 'touchend' ? [] : [t];
  Object.defineProperty(ev, 'touches', { value: list }); Object.defineProperty(ev, 'targetTouches', { value: list }); Object.defineProperty(ev, 'changedTouches', { value: [t] });
  el.dispatchEvent(ev); }"""

with sync_playwright() as p:
    browser = p.webkit.launch()
    vid = shots / 'v55-video'
    shutil.rmtree(vid, ignore_errors=True)
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              locale='ru-RU', timezone_id='Europe/Moscow', record_video_dir=str(vid), record_video_size={'width': 390, 'height': 844})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(OWNER)
    pg.goto(Path(root, 'index.html').as_uri()); pg.wait_for_timeout(500)
    pg.evaluate(SEED); pg.evaluate('render()'); pg.wait_for_timeout(400)

    # 1. вкладки
    tops, heads, navs = {}, set(), set()
    for v, label in [('calendar', 'Календарь'), ('students', 'Ученики'), ('exercises', 'Упражнения'), ('training', 'Тренировки')]:
        pg.tap(f'.nav-item[data-view="{v}"]')
        pg.wait_for_timeout(30)
        st = pg.evaluate("""() => ({ ghost: document.querySelectorAll('.view-ghost').length, enter: !!document.querySelector('.main.view-enter'),
          t: Math.round(document.querySelector('.section-head .view-title').getBoundingClientRect().top), op: getComputedStyle(document.querySelector('.main')).opacity,
          head: JSON.stringify(document.querySelector('header.top').getBoundingClientRect()), nav: JSON.stringify(document.querySelector('.nav').getBoundingClientRect()) })""")
        tops[v] = st['t']; heads.add(st['head']); navs.add(st['nav'])
        check(st['ghost'] == 0 and not st['enter'] and st['op'] == '1', f'tab {label}: shown at once, no crossfade {st["ghost"]},{st["enter"]},{st["op"]}')
        pg.screenshot(path=str(shots / f'v55-tab-{v}.png'))
    check(len(set(tops.values())) == 1, f'same title position on every tab {tops}')
    check(len(heads) == 1 and len(navs) == 1, f'top bar and tab bar do not move ({len(heads)}, {len(navs)})')
    # память прокрутки по вкладкам
    pg.tap('.nav-item[data-view="exercises"]'); pg.wait_for_timeout(100)
    pg.evaluate('window.scrollTo(0, 600)'); pg.wait_for_timeout(250)
    y0 = pg.evaluate('scrollY')
    pg.tap('.nav-item[data-view="students"]'); pg.wait_for_timeout(100)
    pg.tap('.nav-item[data-view="exercises"]'); pg.wait_for_timeout(100)
    check(abs(pg.evaluate('scrollY') - y0) <= 2, f'exercises tab keeps its scroll ({y0} -> {pg.evaluate("scrollY")})')

    # 2. месяц
    pg.tap('.nav-item[data-view="calendar"]'); pg.wait_for_timeout(200)
    pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(100)
    pg.tap('.cal-arrow.is-next')
    pg.wait_for_timeout(110)
    mid = pg.evaluate("""() => { const tr = document.getElementById('cal-track'), tt = document.getElementById('cal-ttrack'), v = document.getElementById('cal-view');
      const a = new DOMMatrix(getComputedStyle(tr).transform).m41, b = new DOMMatrix(getComputedStyle(tt).transform).m41;
      return { grid: (a + v.clientWidth) / -v.clientWidth, title: (b + tt.offsetWidth / 3) / -(tt.offsetWidth / 3), op: getComputedStyle(document.getElementById('cal-title')).opacity }; }""")
    pg.screenshot(path=str(shots / 'v55-month-mid.png'))
    check(0.15 < mid['grid'] < 0.99 and abs(mid['grid'] - mid['title']) < 0.06 and mid['op'] == '1', f'month title slides together with the grid {mid}')
    pg.wait_for_timeout(450)
    pg.screenshot(path=str(shots / 'v55-month-after.png'))
    title = pg.evaluate("document.querySelector('#cal-title .cal-tm:not([aria-hidden])').textContent")
    vis = pg.evaluate("""() => { const b = document.getElementById('cal-title').getBoundingClientRect(); return [...document.querySelectorAll('#cal-title .cal-tm')].filter((n) => { const r = n.getBoundingClientRect(); return r.right > b.left + 2 && r.left < b.right - 2; }).length; }""")
    check(vis == 1, f'after the swipe one month title is visible: {title} ({vis})')
    pg.tap('.cal-arrow:not(.is-next)'); pg.wait_for_timeout(500)

    # 3. шапка докручивается
    pg.tap('.nav-item[data-view="training"]'); pg.wait_for_timeout(200)
    pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(200)
    m = pg.evaluate("(() => { measureMiniBar(); return { start: Math.max(0, miniMetrics.top - miniMetrics.barH - 4), h: miniMetrics.h }; })()")
    for direction, label in [(1, 'down → collapses'), (-1, 'up → expands')]:
        base = m['start'] if direction > 0 else m['start'] + m['h']
        pg.evaluate(f'window.scrollTo(0, {base})'); pg.wait_for_timeout(250)
        pg.evaluate(TOUCH, {'type': 'touchstart', 'x': 200, 'y': 500})
        for k in range(1, 6):
            pg.evaluate(f'window.scrollTo(0, {base + direction * m["h"] * 0.08 * k})'); pg.wait_for_timeout(16)
        pg.evaluate(TOUCH, {'type': 'touchend', 'x': 200, 'y': 500})
        pg.wait_for_timeout(60)
        pg.screenshot(path=str(shots / f'v55-header-{"collapse" if direction > 0 else "expand"}-released.png'))
        pg.wait_for_timeout(700)
        y = pg.evaluate('scrollY'); p_ = pg.evaluate('miniMetrics.p')
        pg.screenshot(path=str(shots / f'v55-header-{"collapse" if direction > 0 else "expand"}-settled.png'))
        check(p_ in (0, 1) and (p_ == 1) == (direction > 0), f'header snaps when released mid-way ({label}) p={p_} y={y}')
        ov = pg.evaluate("""() => { const t = document.querySelector('.section-head .view-title'), b = document.getElementById('mini-bar');
          return { big: +getComputedStyle(t).opacity, mini: +getComputedStyle(b).opacity }; }""")
        check(not (ov['big'] > 0.05 and ov['mini'] > 0.05), f'titles never overlap {ov}')
    pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)

    # 4. «Все ученики»
    sel = pg.locator('#sess-filter')
    if sel.count():
        sel.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
        sel.focus()
        sel.select_option(index=1); pg.wait_for_timeout(60)
        st = pg.evaluate("(() => { const s = document.getElementById('sess-filter'); return { focused: document.activeElement === s, shadow: getComputedStyle(s).boxShadow }; })()")
        pg.screenshot(path=str(shots / 'v55-filter-after-pick.png'))
        check(not st['focused'], f'«Все ученики» lets go right after a pick {st}')
        sel.select_option(index=0); pg.wait_for_timeout(100)
        check(pg.evaluate("document.getElementById('sess-filter').value") == '', 'can pick again immediately')
    else:
        check(False, 'sess-filter present')
    hov = pg.evaluate("""() => { let n = 0; for (const sh of document.styleSheets) { try { for (const r of sh.cssRules) if (r.selectorText && r.selectorText.includes(':hover')) n++; } catch (e) {} } return n; }""")
    check(hov == 0, f'no sticky hover highlights on a touch screen ({hov} rules left)')

    # 5. окно занятия: выезжает снизу; «Отчёт» показывается целиком
    pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(200)
    card = pg.locator('.sess-card[data-action="view-plan"]').first
    card.scroll_into_view_if_needed(); pg.wait_for_timeout(250)
    card.tap(); pg.wait_for_timeout(40)
    open_tr = []
    for i in range(5):
        open_tr.append(pg.evaluate("(() => { const s = document.querySelector('#overlay .sheet'); const m = new DOMMatrix(getComputedStyle(s).transform); return [Math.round(m.m41), Math.round(m.m42), !!document.querySelector('.veil.flip')]; })()"))
        pg.screenshot(path=str(shots / f'v55-modal-open-{i}.png')); pg.wait_for_timeout(45)
    check(any(t[1] > 20 for t in open_tr) and all(t[0] == 0 and not t[2] for t in open_tr), f'session window slides up from the bottom, no zoom {open_tr}')
    pg.wait_for_timeout(400)
    rep = pg.locator('#nv-report .nv-h-btn')
    if rep.count():
        pg.evaluate("(() => { const m = document.querySelector('#overlay .modal'); const r = document.getElementById('nv-report'); m.scrollTop = 0; const mr = m.getBoundingClientRect(); const rr = r.getBoundingClientRect(); if (rr.bottom < mr.bottom - 40) { const sp = document.createElement('div'); sp.style.height = (mr.bottom - rr.bottom - 30) + 'px'; r.before(sp); } })()")
        pg.wait_for_timeout(100)
        pg.screenshot(path=str(shots / 'v55-report-before.png'))
        rep.tap(); pg.wait_for_timeout(180)
        pg.screenshot(path=str(shots / 'v55-report-mid.png'))
        pg.wait_for_timeout(450)
        pg.screenshot(path=str(shots / 'v55-report-open.png'))
        r = pg.evaluate("(() => { const m = document.querySelector('#overlay .modal').getBoundingClientRect(); const b = document.getElementById('nv-report').getBoundingClientRect(); return { mb: Math.round(m.bottom), rb: Math.round(b.bottom), rt: Math.round(b.top), mt: Math.round(m.top) }; })()")
        check(r['rb'] <= r['mb'] and r['rt'] >= r['mt'], f'«Отчёт» scrolls into view when opened {r}')
        sc = pg.evaluate("document.querySelector('#overlay .modal').scrollTop")
        rep.tap(); pg.wait_for_timeout(500)
        check(pg.evaluate("!document.getElementById('nv-report').classList.contains('is-open')"), f'«Отчёт» closes (scroll was {sc})')
    else:
        check(False, 'report present')
    pg.locator('#overlay .icon-button[data-action="close-overlay"]').first.tap(); pg.wait_for_timeout(40)
    close_tr = []
    for i in range(5):
        close_tr.append(pg.evaluate("(() => { const s = document.querySelector('#overlay .sheet, #leaving .sheet'); if (!s) return null; const m = new DOMMatrix(getComputedStyle(s).transform); return [Math.round(m.m41), Math.round(m.m42)]; })()"))
        pg.screenshot(path=str(shots / f'v55-modal-close-{i}.png')); pg.wait_for_timeout(45)
    pg.wait_for_timeout(400)
    seen = [t for t in close_tr if t]
    check(bool(seen) and any(t[1] > 20 for t in seen) and all(t[0] == 0 for t in seen) and pg.evaluate("!document.querySelector('#overlay .veil')"), f'session window slides down to close {close_tr}')

    # 6. профиль ученика: въезжает справа, «назад», уезжает вправо, смахивание от края
    pg.tap('.nav-item[data-view="students"]'); pg.wait_for_timeout(250)
    pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(150)
    before = pg.evaluate("(() => { const c = document.querySelectorAll('.student-card')[1].getBoundingClientRect(); return Math.round(c.top); })()")
    pg.locator('.student-card[data-action="student-detail"]').first.click(); pg.wait_for_timeout(40)
    push_tr = []
    for i in range(5):
        push_tr.append(pg.evaluate("(() => { const s = document.querySelector('#overlay .sheet'); const m = new DOMMatrix(getComputedStyle(s).transform); return [Math.round(m.m41), Math.round(m.m42)]; })()"))
        pg.screenshot(path=str(shots / f'v55-profile-push-{i}.png')); pg.wait_for_timeout(45)
    pg.wait_for_timeout(350)
    pg.screenshot(path=str(shots / 'v55-profile-open.png'))
    full = pg.evaluate("(() => { const s = document.querySelector('#overlay .sheet').getBoundingClientRect(); return { w: Math.round(s.width), h: Math.round(s.height), back: !!document.querySelector('#overlay .push-back'), x: Math.round(s.left) }; })()")
    check(any(t[0] > 30 for t in push_tr) and all(t[1] == 0 for t in push_tr), f'profile pushes in from the right {push_tr}')
    check(full['w'] == 390 and full['h'] >= 800 and full['back'] and full['x'] == 0, f'profile fills the screen with a back arrow {full}')
    pg.locator('#overlay .push-back').tap(); pg.wait_for_timeout(40)
    pop_tr = []
    for i in range(5):
        pop_tr.append(pg.evaluate("(() => { const s = document.querySelector('#overlay .sheet, #leaving .sheet'); if (!s) return null; const m = new DOMMatrix(getComputedStyle(s).transform); return [Math.round(m.m41), Math.round(m.m42)]; })()"))
        pg.screenshot(path=str(shots / f'v55-profile-pop-{i}.png')); pg.wait_for_timeout(45)
    pg.wait_for_timeout(400)
    after = pg.evaluate("(() => { const c = document.querySelectorAll('.student-card')[1].getBoundingClientRect(); return Math.round(c.top); })()")
    seen = [t for t in pop_tr if t]
    check(bool(seen) and any(t[0] > 30 for t in seen) and all(t[1] == 0 for t in seen), f'back slides the profile out to the right {pop_tr}')
    check(before == after and pg.evaluate("!document.querySelector('#overlay .veil')"), f'the card below does not jump ({before} → {after})')
    # смахивание от левого края
    pg.locator('.student-card[data-action="student-detail"]').nth(1).click(); pg.wait_for_timeout(600)
    try:
        pg.evaluate(TOUCH, {'type': 'touchstart', 'x': 8, 'y': 400})
        for x in (30, 70, 120, 170, 220):
            pg.evaluate(TOUCH, {'type': 'touchmove', 'x': x, 'y': 404}); pg.wait_for_timeout(16)
        pg.screenshot(path=str(shots / 'v55-profile-edge-swipe.png'))
        drag = pg.evaluate("Math.round(new DOMMatrix(getComputedStyle(document.querySelector('#overlay .sheet')).transform).m41)")
        pg.evaluate(TOUCH, {'type': 'touchend', 'x': 220, 'y': 404}); pg.wait_for_timeout(600)
        check(drag > 150 and pg.evaluate("!document.querySelector('#overlay .veil')"), f'edge swipe follows the finger ({drag}px) and goes back')
    except Exception as e:
        check(False, f'edge swipe could not be simulated: {e}')

    check(not errs, f'no page errors {errs}')
    ctx.close()
    vids = sorted(vid.glob('*.webm'))
    if vids:
        vids[-1].rename(shots / 'v55-walkthrough.webm')
    shutil.rmtree(vid, ignore_errors=True)
    browser.close()
print('FAILS:', len(fails))
sys.exit(1 if fails else 0)
