"""v48 QA (WebKit 390): добавление 2 и 3 упражнений в запись — и при изменении, и при создании. Форма должна оставаться живой:
листается, карусель свайпается, поля печатаются, сохранение работает."""
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
    mk('v47h', 20, '10:00', st[1], 0, 'Розыгрыши.', [], null)
  ];
  persist(); navigate('training'); render();
}"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
def alive(pg, form, tag, n):
    """форма живая: листаемая часть не сжата, карточка целиком на виду, карусель листается, поля печатаются, кнопки видны"""
    g = pg.evaluate("""() => { const q = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { t: r.top, b: r.bottom, h: r.height }; };
      const m = q('#overlay .modal');
      return { scroll: q('#overlay .modal'), card: q('.nex-card'), save: q('#note-form button[type="submit"]'), add: q('[data-action="note-ex-add"]'), modal: m, vh: innerHeight }; }""")
    check(g['scroll']['h'] >= 400, f"{tag}: scroll area not squeezed ({g['scroll']['h']:.0f}px)")
    check(g['save']['b'] <= g['modal']['b'] + 1 and g['save']['t'] >= g['modal']['t'], f'{tag}: save button visible')
    check(g['add']['b'] <= g['modal']['b'] + 1, f'{tag}: add row visible')
    sc = pg.locator('#overlay .modal')
    pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 0})"); pg.wait_for_timeout(150)
    pg.evaluate("document.querySelector('#note-ex-wrap').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(300)
    g2 = pg.evaluate("""() => { const s = document.querySelector('#overlay .modal').getBoundingClientRect(), c = document.querySelector('.nex-card').getBoundingClientRect(); return { top: c.top - s.top, bottom: s.bottom - c.bottom, h: c.height, sh: s.height }; }""")
    check(g2['top'] >= -1 and g2['bottom'] >= -1, f"{tag}: card fully inside scroll area {g2}")
    tr = form.locator('#note-ex-track')
    tr.evaluate("t => t.scrollTo({left: t.clientWidth + 10})"); pg.wait_for_timeout(500)
    check(form.locator('#note-ex-count').inner_text().startswith('2 из'), f'{tag}: carousel swipes ({form.locator("#note-ex-count").inner_text()})')
    ta = form.locator('[name="exnote:1"]'); ta.tap(); ta.fill('заметка ' + tag); pg.wait_for_timeout(100)
    check(ta.input_value() == 'заметка ' + tag, f'{tag}: note editable')
    sc.evaluate("s => s.scrollTo({top: 0})"); pg.wait_for_timeout(150)
    pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 99999})"); pg.wait_for_timeout(200)
    check(sc.evaluate("s => s.scrollTop") > 0, f'{tag}: form scrolls')
    nt = form.locator('[name="notes"]'); sc.evaluate("s => s.scrollTo({top: 0})"); pg.wait_for_timeout(150)
    nt.scroll_into_view_if_needed(); nt.tap(); nt.fill('Проверка формы ' + tag); pg.wait_for_timeout(100)
    check(nt.input_value() == 'Проверка формы ' + tag, f'{tag}: text editable')
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, hgt in ((390, 844), (430, 932)):
        for theme in ('light', 'dark'):
            tag0 = f'{w}-{theme}'
            c = b.new_context(viewport={'width': w, 'height': hgt}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
            pg = c.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda d: d.accept())
            pg.add_init_script("""try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}""")
            pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
            pg.evaluate(SEED); pg.wait_for_timeout(400)
            for mode in ('edit', 'new'):
                for count in (2, 3):
                    tag = f'{tag0} {mode} +{count}'
                    if mode == 'edit':
                        pg.evaluate("navigate('training'); render()"); pg.wait_for_timeout(300)
                        pg.evaluate("openPlan('v47c')"); pg.wait_for_timeout(700)
                        pg.locator('#overlay [data-action="edit-note"]').first.tap(); pg.wait_for_timeout(800)
                    else:
                        pg.evaluate("navigate('training'); render()"); pg.wait_for_timeout(300)
                        pg.get_by_role('button', name='Записать занятие', exact=True).tap(); pg.wait_for_timeout(700)
                        pg.locator('#note-form [data-action="who-toggle"][data-kind="s"]').first.tap(); pg.wait_for_timeout(100)
                        pg.locator('#note-form [name="notes"]').fill('Новая запись'); pg.wait_for_timeout(100)
                    form = pg.locator('#note-form')
                    have = form.locator('.nex-card').count()
                    form.locator('[data-action="note-ex-add"]').tap(); pg.wait_for_timeout(700)
                    pg.locator('#note-ex-q').fill('кросс'); pg.wait_for_timeout(250)
                    rows = pg.locator('#note-ex-list .pick-row')
                    for i in range(count): rows.nth(i + (10 if count == 3 else 0)).tap(); pg.wait_for_timeout(120)
                    pg.locator('#note-ex-done').tap(); pg.wait_for_timeout(1200)
                    check(form.locator('.nex-card').count() == have + count, f'{tag}: cards {form.locator(".nex-card").count()} (was {have}, added {count})')
                    alive(pg, form, tag, have + count)
                    if mode == 'edit' and count == 2 and w == 390:
                        pg.evaluate("(() => { const t = document.querySelector('#note-ex-track'); t.scrollTo({left: t.clientWidth + 10}); const sc = document.querySelector('#overlay .modal'); const w = document.querySelector('#note-ex-wrap'); sc.scrollTop = Math.max(0, w.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop - 8); })()"); pg.wait_for_timeout(500)
                        pg.screenshot(path=str(shots / ('v48-form-2ex-390' + ('-dark' if theme == 'dark' else '') + '.png')))
                    form.locator('button[type="submit"]').tap(); pg.wait_for_timeout(900)
                    check(pg.locator('#note-form').count() == 0, f'{tag}: saved and closed')
                    pg.evaluate("document.querySelectorAll('#overlay .veil').length && closeModal()"); pg.wait_for_timeout(400)
            check(not errs, f'page errors {errs}')
            c.close()
    b.close()
print('FAILS', fails)
if fails: sys.exit(1)
print('PASS v48 WebKit 390: add 2 and 3 exercises, edit and create')
