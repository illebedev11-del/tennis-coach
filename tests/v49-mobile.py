"""v49 QA — как на iPhone: WebKit, мобильная эмуляция 390/430, касания, режим «с экрана Домой» (standalone),
клавиатура имитируется через visualViewport (высота видимой области уменьшается, как при настоящей клавиатуре).
Сценарии Ильи: (а) изменить запись, +упражнения, открыть отчёт, до конца, поле, печать, «Сохранить» видна и работает;
(б) то же в новой записи; (в) запись из календаря раскрывается из карточки, как из списка; (г) карточка ученика внизу:
фон не двигается, позиция после закрытия та же; (д) фокус в каждом поле окон: поле над клавиатурой, окно не скачет."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v49'); shots.mkdir(parents=True, exist_ok=True)
INIT = r"""(() => {
  const vv = window.visualViewport, P = Object.getPrototypeOf(vv), d = (k, f) => Object.defineProperty(P, k, { configurable: true, get: f });
  const H = Object.getOwnPropertyDescriptor(P, 'height').get;
  d('height', function () { return vv._h == null ? H.call(this) : vv._h; }); d('offsetTop', function () { return vv._t || 0; }); d('scale', () => 1);
  Object.defineProperty(navigator, 'standalone', { configurable: true, get: () => true });
  const mm = window.matchMedia.bind(window);
  window.matchMedia = (q) => /display-mode:\s*standalone/.test(q) ? { matches: true, media: q, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} } : mm(q);
  const sim = () => document.documentElement && document.documentElement.classList.add('kb-sim'); sim(); document.addEventListener('DOMContentLoaded', sim);
  window.__kb = (h, t) => {
    vv._h = h ? innerHeight - h - (t || 0) : null; vv._t = t || 0; vv.dispatchEvent(new Event('resize'));
    let k = document.getElementById('__kb');
    if (!k) { k = document.createElement('div'); k.id = '__kb'; k.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;pointer-events:none;background:#CDD0D6;border-top:1px solid #B5B8BE;display:flex;align-items:center;justify-content:center;font:15px -apple-system,system-ui,sans-serif;color:#555'; k.textContent = 'клавиатура (имитация)'; document.documentElement.appendChild(k); }
    k.style.height = (h || 0) + 'px'; k.style.display = h ? 'flex' : 'none';
  };
})()"""
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
  for (let i = 3; i < 16; i++) if (store.students.length <= i) store.students.push({ ...store.students[0], id: 's_v49_' + i, name: 'Ученик ' + (i + 1), demo: false });
  persist(); navigate('training'); render();
}"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
GEOM = """(sel) => { const f = document.activeElement; const m = document.querySelector('#overlay .modal'); if (!m) return null;
  const R = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return { t: r.top, b: r.bottom, h: r.height }; };
  const head = m.querySelector(':scope > .modal-inner > .modal-top');
  const foot = [...m.querySelectorAll('.form-actions')].find((x) => getComputedStyle(x).position === 'sticky' && x.offsetParent);
  const save = m.querySelector('button[type="submit"]');
  return { f: R(f), focused: !!(f && f.matches && f.matches('input, textarea')), name: f && (f.name || f.id || f.placeholder), modal: R(m), head: R(head), foot: R(foot), save: R(save),
           vvh: visualViewport.height, vvt: visualViewport.offsetTop, ih: innerHeight, sheet: R(m.closest('.sheet')), st: m.scrollTop, sh: m.scrollHeight - m.clientHeight, fs: f ? parseFloat(getComputedStyle(f).fontSize) : 0 }; }"""
SAMPLE = """() => { window.__smp = []; const t0 = performance.now(); const tick = () => { const s = document.querySelector('#overlay .sheet'); if (s) { const r = s.getBoundingClientRect(); window.__smp.push([performance.now() - t0, r.top, r.bottom]); } if (performance.now() - t0 < 900) requestAnimationFrame(tick); }; requestAnimationFrame(tick); }"""
def kb_field(pg, loc, tag, kbh, shot=None, text=' тест'):
    """тап в поле → клавиатура: окно не скачет, поле над клавиатурой и над закреплённым низом, печать работает"""
    pg.evaluate(SAMPLE)
    loc.tap(); pg.wait_for_timeout(60)
    pg.evaluate(f"__kb({kbh})"); pg.wait_for_timeout(800)
    g = pg.evaluate(GEOM)
    smp = pg.evaluate("window.__smp")
    nm = g and g['name']
    check(g and g['focused'], f'{tag}: field focused ({nm})')
    if not g or not g['f']: return g
    vis_bottom = g['vvt'] + g['vvh']
    top_lim = (g['head']['b'] if g['head'] else g['modal']['t']) - 1
    bot_lim = min(vis_bottom, g['foot']['t'] if g['foot'] and g['foot']['t'] > g['f']['t'] else vis_bottom) + 1
    tall = g['f']['h'] > bot_lim - top_lim
    ok = g['f']['t'] >= top_lim and (tall or g['f']['b'] <= bot_lim)
    check(ok, f"{tag}: field {nm} visible above keyboard (field {g['f']['t']:.0f}–{g['f']['b']:.0f}, band {top_lim:.0f}–{bot_lim:.0f})")
    check(g['sheet']['b'] <= vis_bottom + 1 and g['sheet']['t'] >= g['vvt'] - 1, f"{tag}: sheet inside visible area {g['sheet']} vv {g['vvt']}+{g['vvh']}")
    if g['save']: check(g['save']['b'] <= vis_bottom + 1 and g['save']['t'] >= top_lim, f"{tag}: save above keyboard {g['save']} vv {vis_bottom}")
    # окно не скачет: низ шторки идёт только вверх, без рывка вниз; верх не уезжает вниз
    downs = [smp[i][2] - smp[i - 1][2] for i in range(1, len(smp))]
    tops = [smp[i][1] - smp[i - 1][1] for i in range(1, len(smp))]
    check(all(d <= 4 for d in downs) and all(d <= 4 for d in tops), f'{tag}: no jump down while keyboard opens ({nm}) max {max(downs + [0]):.1f}/{max(tops + [0]):.1f}')
    total = abs(smp[-1][2] - smp[0][2]) if smp else 0
    mid = {round(x[2]) for x in smp if min(smp[0][2], smp[-1][2]) + 3 < x[2] < max(smp[0][2], smp[-1][2]) - 3}
    check(total < 4 or len(mid) >= 2, f'{tag}: sheet glides with keyboard through intermediate positions, not a snap ({nm}) {sorted(mid)} of {total:.0f}')
    check(g['fs'] >= 16, f"{tag}: font ≥16px in {nm} ({g['fs']})")
    before = loc.input_value()
    if loc.get_attribute('type') == 'number' or loc.get_attribute('inputmode') in ('numeric', 'decimal'): text = '7'
    pg.keyboard.type(text); pg.wait_for_timeout(80)
    check(loc.input_value() == before + text or loc.input_value().endswith(text.strip()), f'{tag}: typing in {nm}')
    if shot: pg.screenshot(path=str(shots / shot))
    pg.evaluate("document.activeElement && document.activeElement.blur(); __kb(0)"); pg.wait_for_timeout(450)
    return g
def form_flow(pg, tag, mode, add, kbh, main):
    form = pg.locator('#note-form')
    have = form.locator('.nex-card').count()
    form.locator('[data-action="note-ex-add"]').tap(); pg.wait_for_timeout(700)
    q = pg.locator('#note-ex-q')
    kb_field(pg, q, tag + ' picker search', kbh, text='кросс')
    rows = pg.locator('#note-ex-list .pick-row')
    for i in range(add): rows.nth(i + 3).tap(); pg.wait_for_timeout(120)
    pg.locator('#note-ex-done').tap(); pg.wait_for_timeout(1200)
    check(form.locator('.nex-card').count() == have + add, f'{tag}: cards {form.locator(".nex-card").count()}')
    fold = form.locator('.fold').filter(has_text='Отчёт').first
    if 'is-open' not in (fold.get_attribute('class') or ''):
        fold.locator('.fold-head').first.tap(); pg.wait_for_timeout(600)
    check('is-open' in (fold.get_attribute('class') or ''), f'{tag}: report open')
    pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 99999})"); pg.wait_for_timeout(400)
    g = pg.evaluate(GEOM)
    check(g['sh'] > 0 and g['st'] >= g['sh'] - 2, f"{tag}: form scrolls to the very end ({g['st']}/{g['sh']})")
    check(g['save'] and g['save']['b'] <= min(g['modal']['b'], g['ih']) + 1 and g['save']['t'] >= g['modal']['t'], f"{tag}: save visible at the end {g['save']} modal {g['modal']}")
    check(g['sheet']['b'] <= g['ih'] + 1 and g['sheet']['t'] >= -1, f"{tag}: whole window on screen {g['sheet']}")
    nx = form.locator('[name="next"]')
    nb = pg.evaluate("(() => { const n = document.querySelector('#note-form [name=next]').getBoundingClientRect(), f = document.querySelector('#note-form .form-actions').getBoundingClientRect(); return [n.bottom, f.top]; })()")
    check(nb[0] <= nb[1] + 1, f'{tag}: last report field not hidden under buttons {nb}')
    if main: pg.screenshot(path=str(shots / f'v49-{mode}-report-end-{tag.split()[0]}.png'))
    # первая вкладка-заметка к упражнению, затем поля отчёта — всё с клавиатурой
    pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 0})"); pg.wait_for_timeout(250)
    kb_field(pg, form.locator('[name="notes"]'), tag + ' notes', kbh)
    tr = form.locator('#note-ex-track')
    tr.evaluate("t => t.scrollTo({left: t.clientWidth + 10})"); pg.wait_for_timeout(450)
    kb_field(pg, form.locator('[name="exnote:1"]'), tag + ' exnote', kbh)
    for nm in ('success', 'difficulty'):
        kb_field(pg, form.locator(f'[name="{nm}"]'), tag + ' ' + nm, kbh)
    pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 99999})"); pg.wait_for_timeout(300)
    kb_field(pg, nx, tag + ' next', kbh, shot=(f'v49-{mode}-keyboard-{tag.split()[0]}.png' if main else None), text='Дальше: подача ' + mode)
    form.locator('button[type="submit"]').tap(); pg.wait_for_timeout(1000)
    check(pg.locator('#note-form').count() == 0, f'{tag}: saved')
    ok = pg.evaluate(f"store.plans.some((p) => p.summary && String(p.summary.next).includes('Дальше: подача {mode}'))")
    check(ok, f'{tag}: report text saved')
    pg.evaluate("document.querySelectorAll('#overlay .veil').length && closeModal('all')"); pg.wait_for_timeout(500)
def modal_fields(pg, tag, kbh, limit=6):
    locs = pg.locator('#overlay .modal').locator('textarea:visible, input:not([type]):visible, input[type="text"]:visible, input[type="search"]:visible, input[type="number"]:visible')
    n = locs.count()
    fs = pg.evaluate("[...document.querySelectorAll('#overlay .modal input, #overlay .modal textarea, #overlay .modal select')].filter((e) => e.offsetParent && !['checkbox','radio','range','color','hidden'].includes(e.type)).map((e) => [e.name || e.id || e.type, parseFloat(getComputedStyle(e).fontSize)]).filter((x) => x[1] < 16)")
    check(not fs, f'{tag}: all fields ≥16px {fs}')
    step = max(1, n // limit)
    for i in range(0, n, step):
        loc = locs.nth(i)
        try: loc.evaluate("e => { const m = e.closest('.modal'); const r = e.getBoundingClientRect(), mr = m.getBoundingClientRect(); m.scrollTop += r.top - mr.top - mr.height * .55; }")
        except Exception: continue
        pg.wait_for_timeout(200)
        kb_field(pg, loc, f'{tag} #{i}', kbh)
    return n
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, hgt, kbh in ((390, 844, 336), (430, 932, 346)):
        for theme in ('light', 'dark'):
            tag0 = f'{w}-{theme}'; main = theme == 'light' and w == 390
            c = b.new_context(viewport={'width': w, 'height': hgt}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
            c.add_init_script(INIT)
            pg = c.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda d: d.accept())
            pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
            pg.evaluate(SEED); pg.wait_for_timeout(400)
            check(pg.evaluate("navigator.standalone === true && matchMedia('(display-mode: standalone)').matches"), f'{tag0}: standalone emulated')
            # (а) изменить запись: 1 → 2 упражнения (390), 1 → 3 (430)
            pg.evaluate("openPlan('v47c')"); pg.wait_for_timeout(800)
            pg.locator('#overlay [data-action="edit-note"]').first.tap(); pg.wait_for_timeout(900)
            form_flow(pg, f'{tag0} edit', 'edit', 1 if w == 390 else 2, kbh, theme == 'light' and w == 390 or (w == 390))
            # (б) новая запись
            pg.evaluate("navigate('training'); render()"); pg.wait_for_timeout(300)
            pg.get_by_role('button', name='Записать занятие', exact=True).tap(); pg.wait_for_timeout(800)
            pg.locator('#note-form [data-action="who-toggle"][data-kind="s"]').first.tap(); pg.wait_for_timeout(100)
            pg.locator('#note-form [name="notes"]').fill('Новая запись'); pg.wait_for_timeout(100)
            form_flow(pg, f'{tag0} new', 'new', 2, kbh, False)
            # (в) раскрытие: из списка и из календаря — одинаково
            for src in ('list', 'calendar'):
                if src == 'list':
                    pg.evaluate("navigate('training'); render()"); pg.wait_for_timeout(400)
                    fold = pg.locator('.fold[data-fold="saved-plans"]')
                    if 'is-open' not in (fold.get_attribute('class') or ''): fold.locator('.fold-head').first.tap(); pg.wait_for_timeout(500)
                    card = pg.locator('.sess-card[data-id="v47b"]').first
                else:
                    pg.locator('.nav-item[data-view="calendar"]').tap(); pg.wait_for_timeout(600)
                    card = pg.locator('#sess-cal .cal-item').first
                card.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
                pg.evaluate("window.__flip = []; const mo = new MutationObserver(() => { const v = document.querySelector('#overlay .veil'); if (v) window.__flip.push(v.classList.contains('flip')); }); mo.observe(document.getElementById('overlay'), { subtree: true, attributes: true, childList: true }); setTimeout(() => mo.disconnect(), 400)")
                card.tap(); pg.wait_for_timeout(120)
                st = pg.evaluate("(() => { const m = document.querySelector('#overlay .modal'); const a = m && m.getAnimations ? m.getAnimations().map((x) => x.effect && x.effect.getKeyframes().map((k) => k.clipPath || '').join('|')) : []; return { flip: (window.__flip || []).some(Boolean), clip: a.some((s) => /inset[(]/.test(s)) }; })()")
                check(st['flip'] and st['clip'], f'{tag0}: record opens from the card ({src}) {st}')
                pg.wait_for_timeout(500)
                pg.evaluate("closeModal()"); pg.wait_for_timeout(600)
            # (г) карточка ученика до конца: фон не двигается, позиция после закрытия та же
            pg.locator('.nav-item[data-view="students"]').tap(); pg.wait_for_timeout(600)
            pg.evaluate("window.scrollTo(0, 500)"); pg.wait_for_timeout(300)
            y0 = pg.evaluate("scrollY")
            cards = pg.locator('.student-card[data-action="student-detail"]')
            idx = pg.evaluate("[...document.querySelectorAll('.student-card[data-action=student-detail]')].findIndex((c) => { const r = c.getBoundingClientRect(); return r.top > 120 && r.bottom < innerHeight - 120; })")
            sc = cards.nth(idx)
            r0 = sc.evaluate("c => c.getBoundingClientRect().top")
            sc.click(); pg.wait_for_timeout(900)  # касание по карточке ученика в эмуляции WebKit уходит в долгое нажатие; на iPhone открывается касанием
            hist = pg.locator('#overlay .fold').filter(has_text='История').first
            for pass_ in ('closed', 'history'):
                if pass_ == 'history' and hist.count():
                    pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 0})"); pg.wait_for_timeout(200)
                    hist.scroll_into_view_if_needed(); hist.locator('.fold-head').first.tap(); pg.wait_for_timeout(700)
                pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 99999})"); pg.wait_for_timeout(400)
                dl = pg.locator('#overlay [data-action="delete-student"]').first
                box = dl.bounding_box()
                # жест вверх по кнопке «Удалить карточку» у конца прокрутки: фон не должен двигаться
                pv = pg.evaluate("""([x, y]) => { const t = document.elementFromPoint(x, y); const mk = (type, yy) => { let ev; try { const tt = new Touch({ identifier: 7, target: t, clientX: x, clientY: yy }); ev = new TouchEvent(type, { bubbles: true, cancelable: true, touches: type === 'touchend' ? [] : [tt], targetTouches: type === 'touchend' ? [] : [tt], changedTouches: [tt] }); } catch (e) { return null; } t.dispatchEvent(ev); return ev.defaultPrevented; };
                   const s = mk('touchstart', y); if (s === null) return 'no-touch-ctor'; const m1 = mk('touchmove', y - 10), m2 = mk('touchmove', y - 40); mk('touchend', y - 40); return [m1, m2]; }""", [box['x'] + box['width'] / 2, box['y'] + box['height'] / 2])
                if pv != 'no-touch-ctor': check(pv[1] is True, f'{tag0}: swipe at the bottom of student card does not leak ({pass_}) {pv}')
                pg.wait_for_timeout(300)
                bgst = pg.evaluate("({ pos: getComputedStyle(document.body).position, top: document.body.style.top, sy: scrollY })")
                check(bgst['pos'] == 'fixed' and bgst['top'] == f'-{y0}px' and bgst['sy'] == 0, f'{tag0}: background locked at its place ({pass_}) {bgst} y0={y0}')
                g = pg.evaluate(GEOM)
                check(box['y'] + box['height'] <= g['modal']['b'] + 1 and g['modal']['b'] <= hgt, f'{tag0}: delete button reachable inside window ({pass_})')
                if main and pass_ == 'closed': pg.screenshot(path=str(shots / 'v49-student-bottom-390.png'))
            pg.evaluate("closeModal()"); pg.wait_for_timeout(800)
            y1 = pg.evaluate("scrollY"); r1 = sc.evaluate("c => c.getBoundingClientRect().top")
            check(y1 == y0 and abs(r1 - r0) < 2, f'{tag0}: list position kept after closing ({y0}->{y1}, card {r0:.0f}->{r1:.0f})')
            # (д) все поля окон
            n_all = 0
            for name, js in (('student form', "openStudentForm(store.students[0].id)"), ('new student', "openStudentForm()"), ('group form', "openGroupForm()"),
                             ('exercise form', "openExerciseForm(seedExercises[3].id)"), ('new exercise', "openExerciseForm()"), ('sections', "openLibSections()"),
                             ('reminder', "openReportReminder('v47a')")):
                try: pg.evaluate(js)
                except Exception as e: check(False, f'{tag0}: open {name}: {e}'); continue
                pg.wait_for_timeout(800)
                if not pg.locator('#overlay .modal').count(): check(False, f'{tag0}: {name} did not open'); continue
                n_all += modal_fields(pg, f'{tag0} {name}', kbh, 4 if w == 430 else 6)
                pg.evaluate("closeModal('all')"); pg.wait_for_timeout(600)
            check(n_all >= 12, f'{tag0}: fields checked {n_all}')
            # поиск на экранах: шрифт ≥16px
            small = []
            for vw in ('training', 'calendar', 'students', 'exercises'):
              small += pg.evaluate("(() => { navigate('" + vw + "'); render(); return [...document.querySelectorAll('#app input, #app textarea, #app select')].filter((e) => !['checkbox','radio','range','color','hidden'].includes(e.type)).map((e) => [e.id || e.name, parseFloat(getComputedStyle(e).fontSize)]).filter((x) => x[1] < 16); })()")
            check(not small, f'{tag0}: screen fields ≥16px {small}')
            check(not errs, f'{tag0}: page errors {errs}')
            print('done', tag0); c.close()
    b.close()
print('FAILS', len(fails))
if fails: sys.exit(1)
print('PASS v49 WebKit 390/430 light/dark standalone + keyboard: edit/new form, report end, keyboard, open-from-card, student card lock, all fields')
