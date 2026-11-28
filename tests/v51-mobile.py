"""v51 QA — автор занятия (Илья / Илона): WebKit, 390/430, светлая и тёмная тема.
Переключатель в новой и изменяемой записи, запоминание выбора, автор в списке, карточке, календаре, фильтр «Все / Илья / Илона»,
старые записи без автора = Илья, нет горизонтальной прокрутки."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v51'); shots.mkdir(parents=True, exist_ok=True)
SHOT = len(sys.argv) > 3
SEED = """() => {
  ['Игорь Петров', 'Маша Соколова', 'Даня Орлов'].forEach((n, i) => { if (store.students.length <= i) store.students.push({ id: 's_v51_' + i, name: n, age: '', level: 'Средний', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() }); });
  const st = store.students.slice(0, 3), today = dateISO();
  const co = [{ id: 'coach_ilya', name: 'Илья' }, { id: 'coach_ilona', name: 'Илона' }];
  const mk = (id, shift, time, s, c, notes) => normalizePlan({ id, kind: 'note', status: 'done', date: isoShift(today, -shift), ...(time ? { time } : {}),
    targetType: 'student', studentId: s.id, studentName: s.name, studentIds: [s.id], groupIds: [], ...(c ? { coaches: [co[c - 1]] } : {}), actualStudentIds: [s.id],
    goal: notes, notes, sections: emptySections(), summary: null, createdAt: nowISO(), createdBy: store.coachId });
  store.plans = [
    mk('a1', 0, '18:00', st[0], 1, 'Кросс справа и подача с первым ударом.'),
    mk('a2', 0, '09:30', st[1], 2, 'Воле у сетки и смэш.'),
    mk('a3', 2, '17:00', st[2], 1, 'Бэкхенд по линии с корзины.'),
    mk('a4', 3, '', st[0], 2, 'Игра на счёт.'),
    mk('a5', 6, '19:00', st[1], 0, 'Старая запись без автора.'),
    mk('a6', 12, '18:30', st[2], 2, 'Работа ног.')
  ];
  persist(); navigate('training'); render();
}"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
def seg_state(pg, sel):
    return pg.evaluate("""(sel) => { const s = document.querySelector(sel); if (!s) return null; const on = s.querySelector('.coach-opt.is-on'), th = s.querySelector('.coach-thumb');
      const a = on && on.getBoundingClientRect(), t = th.getBoundingClientRect(), r = s.getBoundingClientRect();
      return { on: on && on.textContent, id: on && on.dataset.id, checked: [...s.querySelectorAll('[role=radio]')].filter((b) => b.getAttribute('aria-checked') === 'true').length,
               n: s.querySelectorAll('.coach-opt').length, h: Math.min(...[...s.querySelectorAll('.coach-opt')].map((b) => b.getBoundingClientRect().height)),
               dx: a ? Math.abs(a.left - t.left) : 99, w: r.width, right: r.right }; }""", sel)
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, hgt in ((390, 844), (430, 932)):
        for theme in ('light', 'dark'):
            tag = f'{w}-{theme}'
            c = b.new_context(viewport={'width': w, 'height': hgt}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
            pg = c.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
            pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
            pg.evaluate("localStorage.removeItem('tennis_coach_last_coach')")
            pg.evaluate(SEED); pg.wait_for_timeout(400)
            # старая запись без автора → Илья; данные не потеряны
            check(pg.evaluate("getPlan('a5').coaches.map((c) => c.name).join()") == 'Илья', f'{tag}: old record = Илья')
            check(pg.evaluate("normalizePlan({id:'x',date:'2026-01-01',sections:{}}).coaches[0].id") == 'coach_ilya', f'{tag}: migration default')
            check(pg.evaluate("planAuthors(getPlan('a2')).map((c) => c.name).join()") == 'Илона', f'{tag}: author a2')
            # список: автор в каждой строке, фильтр
            pg.evaluate("ui.folds['saved-plans'] = true; navigate('training'); render()"); pg.wait_for_timeout(500)
            for i in range(0, 1):
                pass
            cards = pg.locator('#sess-list .sess-card')
            n_all = cards.count()
            check(n_all >= 5 and pg.locator('#sess-list .sess-card .author').count() == n_all, f'{tag}: author in every row ({n_all})')
            fs = seg_state(pg, '.coach-seg.is-filter')
            check(fs and fs['n'] == 3 and fs['on'] == 'Все' and fs['dx'] <= 1.5, f'{tag}: filter seg {fs}')
            pg.locator('.coach-seg.is-filter [data-id="coach_ilona"]').first.scroll_into_view_if_needed()
            if SHOT and w == 390: pg.screenshot(path=str(shots / f'v51-list-{theme}-390.png'))
            pg.locator('.coach-seg.is-filter [data-id="coach_ilona"]').first.tap(); pg.wait_for_timeout(450)
            names = pg.evaluate("[...document.querySelectorAll('#sess-list .sess-card .author')].map((e) => e.textContent.trim())")
            check(names and all(x == 'Илона' for x in names) and len(names) == 3, f'{tag}: filter Илона {names}')
            fs = seg_state(pg, '.coach-seg.is-filter'); check(fs['on'] == 'Илона' and fs['dx'] <= 1.5, f'{tag}: filter thumb moved {fs}')
            pg.locator('.coach-seg.is-filter [data-id="coach_ilya"]').first.tap(); pg.wait_for_timeout(450)
            names = pg.evaluate("[...document.querySelectorAll('#sess-list .sess-card .author')].map((e) => e.textContent.trim())")
            check(names and all(x == 'Илья' for x in names) and len(names) == 3, f'{tag}: filter Илья (incl. old record) {names}')
            pg.locator('.coach-seg.is-filter [data-id=""]').first.tap(); pg.wait_for_timeout(450)
            check(pg.locator('#sess-list .sess-card').count() == n_all, f'{tag}: filter Все')
            # карточка записи: автор виден
            pg.evaluate("openPlan('a2')"); pg.wait_for_timeout(800)
            check(pg.locator('#overlay .nv-by .author').first.text_content().strip() == 'Илона', f'{tag}: author in record card')
            if SHOT and w == 390: pg.screenshot(path=str(shots / f'v51-card-{theme}-390.png'))
            # изменить: автор переключается и сохраняется, возвращаемся в карточку
            pg.locator('#overlay [data-action="edit-note"]').first.tap(); pg.wait_for_timeout(900)
            s = seg_state(pg, '#note-form .coach-seg')
            check(s and s['n'] == 2 and s['on'] == 'Илона' and s['checked'] == 1 and s['dx'] <= 1.5 and s['h'] >= 36, f'{tag}: edit seg shows author {s}')
            pg.locator('#note-form .coach-seg [data-id="coach_ilya"]').tap(); pg.wait_for_timeout(500)
            s = seg_state(pg, '#note-form .coach-seg'); check(s['on'] == 'Илья' and s['dx'] <= 1.5, f'{tag}: edit seg switched {s}')
            pg.locator('#note-form button[type="submit"]').tap(); pg.wait_for_timeout(900)
            check(pg.evaluate("getPlan('a2').coaches.map((c) => c.id).join()") == 'coach_ilya', f'{tag}: edit saved author')
            pg.evaluate("closeModal('all')"); pg.wait_for_timeout(500)
            # новая запись: по умолчанию тот, кого выбирали в последний раз, и выбор запоминается
            pg.evaluate("localStorage.setItem('tennis_coach_last_coach', 'coach_ilona'); navigate('training'); render()"); pg.wait_for_timeout(300)
            pg.get_by_role('button', name='Записать занятие', exact=True).tap(); pg.wait_for_timeout(800)
            s = seg_state(pg, '#note-form .coach-seg'); check(s and s['on'] == 'Илона', f'{tag}: new note defaults to last coach {s}')
            if SHOT and w == 390: pg.screenshot(path=str(shots / f'v51-form-{theme}-390.png'))
            pg.locator('#note-form .coach-seg [data-id="coach_ilya"]').tap(); pg.wait_for_timeout(300)
            check(pg.evaluate("localStorage.getItem('tennis_coach_last_coach')") == 'coach_ilya', f'{tag}: choice remembered on device')
            pg.locator('#note-form .coach-seg [data-id="coach_ilona"]').tap(); pg.wait_for_timeout(300)
            pg.locator('#note-form [data-action="who-toggle"][data-kind="s"]').first.tap(); pg.wait_for_timeout(100)
            pg.locator('#note-form [name="notes"]').fill('Новая запись Илоны'); pg.wait_for_timeout(100)
            pg.locator('#note-form button[type="submit"]').tap(); pg.wait_for_timeout(900)
            rec = pg.evaluate("(() => { const q = store.plans.find((x) => x.notes === 'Новая запись Илоны'); return q && q.coaches.map((c) => c.name).join(); })()")
            check(rec == 'Илона', f'{tag}: new record author {rec}')
            check(pg.locator('#overlay .nv-by .author').first.text_content().strip() == 'Илона', f'{tag}: saved record opens with author')
            pg.evaluate("closeModal('all')"); pg.wait_for_timeout(500)
            # следующая новая запись начинается с Илоны
            pg.get_by_role('button', name='Записать занятие', exact=True).tap(); pg.wait_for_timeout(800)
            s = seg_state(pg, '#note-form .coach-seg'); check(s and s['on'] == 'Илона', f'{tag}: next new note defaults to Илона {s}')
            pg.evaluate("closeModal('all')"); pg.wait_for_timeout(500)
            # форма нового плана и окно «Кто на занятии»
            pg.evaluate("navigate('training'); render()"); pg.wait_for_timeout(300)
            check(pg.locator('#app .coach-seg[data-scope="plan"] .coach-opt').count() == 2, f'{tag}: plan form has seg')
            pg.evaluate("openWhoEditor('a1')"); pg.wait_for_timeout(700)
            s = seg_state(pg, '#overlay .coach-seg'); check(s and s['on'] == 'Илья', f'{tag}: who editor seg {s}')
            pg.evaluate("closeModal('all')"); pg.wait_for_timeout(500)
            # календарь: имя тренера и цвет у занятия
            pg.evaluate("navigate('calendar'); render()"); pg.wait_for_timeout(600)
            items = pg.evaluate("[...document.querySelectorAll('.cal-item')].map((e) => [e.querySelector('small em').textContent, e.querySelector('.cal-bar').style.background])")
            check(items and all(x[0] in ('Илья', 'Илона') for x in items), f'{tag}: calendar item author {items}')
            check(len({x[1] for x in items}) == 2, f'{tag}: two coach colours {items}')
            if SHOT and w == 390: pg.screenshot(path=str(shots / f'v51-calendar-{theme}-390.png'))
            # без горизонтальной прокрутки
            for vw in ('training', 'calendar'):
                pg.evaluate("navigate('" + vw + "'); render()"); pg.wait_for_timeout(300)
                check(pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f'{tag}: no horizontal scroll in {vw}')
            check(not errs, f'{tag}: page errors {errs}')
            print('done', tag); c.close()
    b.close()
print('FAILS', len(fails))
if fails: sys.exit(1)
print('PASS v51 WebKit 390/430 light/dark: автор записи, запоминание, список, карточка, календарь, фильтр, миграция')
