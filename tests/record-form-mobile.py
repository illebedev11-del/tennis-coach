"""v46 QA: форма записи, выбор упражнений, отчёт, время, разделы, тосты, имитация экранной клавиатуры (WebKit)."""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1]); shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v46'); shots.mkdir(parents=True, exist_ok=True)
KB = """(() => {
  const vv = new EventTarget();
  Object.assign(vv, {height: innerHeight, width: innerWidth, offsetTop: 0, offsetLeft: 0, scale: 1});
  Object.defineProperty(window, 'visualViewport', {value: vv, configurable: true});
  window.testKeyboard = (h, top = 0) => { vv.height = h; vv.offsetTop = top; vv.dispatchEvent(new Event('resize')); };
})()"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, hgt in ((390, 844), (430, 932)):
        for theme in ('light', 'dark'):
            tag = f'{w}-{theme}'
            c = b.new_context(viewport={'width': w, 'height': hgt}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
            pg = c.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('dialog', lambda d: d.accept('Турнирная подготовка') if d.type == 'prompt' else d.accept())
            pg.add_init_script(KB)
            pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
            pg.get_by_role('button', name='Записать занятие', exact=True).tap(); pg.wait_for_timeout(500)
            form = pg.locator('#note-form')
            form.locator('[data-action="who-toggle"][data-kind="s"]').first.tap()
            check('Игорь' in form.locator('#note-who-v').inner_text(), f'{tag}: student row value')
            form.locator('[name="time"]').fill('18:00'); pg.wait_for_timeout(50)
            check(form.locator('[data-ios-for="time"]').inner_text() == '18:00', f'{tag}: time row text')
            form.locator('[name="notes"]').fill('Кросс справа и подача с первым ударом. Закончили приёмом в центр.')
            form.locator('.fold[data-fold="note-who"] .fold-head').tap(); pg.wait_for_timeout(350)
            form.locator('[data-action="note-ex-add"]').tap(); pg.wait_for_timeout(500)
            pg.locator('#note-ex-q').fill('кросс'); pg.wait_for_timeout(150)
            rows = pg.locator('#note-ex-list .pick-row')
            check(rows.count() >= 3, f'{tag}: search finds exercises ({rows.count()})')
            for i in range(3): rows.nth(i).tap(); pg.wait_for_timeout(50)
            pg.wait_for_timeout(200)
            check(pg.locator('#note-ex-done').inner_text().strip() == 'Готово · 3', f'{tag}: done label')
            if tag == '390-light': pg.screenshot(path=str(shots / 'v46-pick-390.png'))
            pg.locator('#note-ex-done').tap(); pg.wait_for_timeout(700)
            check(form.locator('.nex-card').count() == 3, f'{tag}: three cards')
            check(form.locator('#note-ex-count').inner_text() == '3 из 3', f'{tag}: counter after add')
            pg.evaluate("el('note-ex-track').scrollLeft = 0"); pg.wait_for_timeout(300)
            check(form.locator('#note-ex-count').inner_text() == '1 из 3', f'{tag}: counter after swipe back')
            card = form.locator('.nex-card').first.bounding_box(); fbox = form.bounding_box()
            check(abs(card['width'] - fbox['width']) < 2, f'{tag}: card full width {card["width"]} vs {fbox["width"]}')
            form.locator('[name="exnote:0"]').fill('Глубже по диагонали')
            pg.evaluate("""() => {
              const wrap=document.getElementById('note-ex-wrap'), sc=wrap && wrap.closest('#overlay .modal');
              if (sc && wrap) sc.scrollTop = Math.max(0, wrap.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop - 80);
            }"""); pg.wait_for_timeout(200)
            def visible(sel, in_foot=False):
                return pg.evaluate("""([sel, inFoot]) => {
                  const e=document.querySelector(sel), m=document.querySelector('#overlay .modal'), f=document.querySelector('#note-form .form-actions');
                  if (!e || !m || !f) return false;
                  const r=e.getBoundingClientRect(), b=m.getBoundingClientRect(), fr=f.getBoundingClientRect();
                  if (r.height < 1 || r.top < b.top-1 || r.bottom > b.bottom+1) return false;
                  return inFoot ? (r.top >= fr.top-1 && r.bottom <= fr.bottom+1) : r.bottom <= fr.top+2;
                }""", [sel, in_foot])
            dbg = pg.evaluate("(() => { const R = (s) => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom)]; }; return { card: R('.nex-card'), dots: R('.nex-dots'), m: R('#overlay .modal'), f: R('#note-form .form-actions'), st: document.querySelector('#overlay .modal').scrollTop }; })()")
            check(visible('.nex-card') and visible('#note-ex-count') and visible('.nex-dots'), f'{tag}: card and 1 of 3 visible above footer {dbg}')
            # v49: закреплены только «Сохранить/Отмена»; «Добавить упражнение» и «Отчёт» — в общей прокрутке, не под кнопками
            check(visible('#note-form button[type="submit"]', True), f'{tag}: save always visible')
            pg.evaluate("document.querySelector('.fold[data-fold=\"note-report\"]').scrollIntoView({block:'center'})"); pg.wait_for_timeout(200)
            check(visible('[data-action="note-ex-add"]') and visible('.fold[data-fold="note-report"] .fold-head'), f'{tag}: add and report reachable above the buttons')
            if tag == '390-light': pg.screenshot(path=str(shots / 'v46-form-390.png'))
            if tag == '390-dark': pg.screenshot(path=str(shots / 'v46-form-390-dark.png'))
            check(form.locator('.fold[data-fold="note-report"] .fold-title').inner_text() == 'Добавить отчёт', f'{tag}: report folded title')
            check('Только текст' not in form.inner_text(), f'{tag}: hint removed')
            form.locator('.fold[data-fold="note-report"] .fold-head').tap(); pg.wait_for_timeout(450)
            form.locator('[name="success"]').fill('Стабильный кросс')
            hs = form.locator('[name="difficulty"]').bounding_box()['height']
            check(hs < 60, f'{tag}: compact report field {hs}')
            check(visible('#note-form button[type="submit"]', True), f'{tag}: save visible with report open')
            pg.evaluate("document.querySelector('#overlay .modal').scrollTo({top: 99999})"); pg.wait_for_timeout(200)
            check(visible('[name="next"]') and visible('#note-form button[type="submit"]', True), f'{tag}: last report field reachable, save visible')
            if tag == '390-light': pg.screenshot(path=str(shots / 'v46-report-390.png'))
            # keyboard simulation: the sheet must ride with the keyboard, not jump
            form.locator('[name="next"]').focus()
            kbh = hgt - 380
            samples = pg.evaluate("""(h) => new Promise(res => { const s = document.querySelector('#overlay .sheet'); const out = [];
                testKeyboard(h); const t0 = performance.now();
                const tick = () => { out.push(Math.round(s.getBoundingClientRect().bottom)); if (performance.now() - t0 < 450) requestAnimationFrame(tick); else res(out); };
                requestAnimationFrame(tick); })""", kbh)
            mono = all(samples[i] >= samples[i + 1] - 1 for i in range(len(samples) - 1))
            check(max(samples) - min(samples) <= 1, f'{tag}: v50 window stays still when keyboard opens {samples[:3]}..{samples[-2:]}')
            pg.wait_for_timeout(500); vis = pg.evaluate("""(h) => { const f = document.activeElement, m = f.closest('.modal'); const r = f.getBoundingClientRect(), b = m.getBoundingClientRect(); return r.top >= b.top - 1 && r.bottom <= h + 1; }""", kbh)
            check(vis, f'{tag}: focused field visible above keyboard')
            samples = pg.evaluate("""(h) => new Promise(res => { const s = document.querySelector('#overlay .sheet'); const out = [];
                document.activeElement.blur(); testKeyboard(h); const t0 = performance.now();
                const tick = () => { out.push(Math.round(s.getBoundingClientRect().bottom)); if (performance.now() - t0 < 450) requestAnimationFrame(tick); else res(out); };
                requestAnimationFrame(tick); })""", hgt)
            mono = all(samples[i] <= samples[i + 1] + 1 for i in range(len(samples) - 1))
            check(max(samples) - min(samples) <= 1, f'{tag}: v50 window stays still when keyboard closes {samples[:3]}..{samples[-2:]}')
            form.locator('[type="submit"]').tap(); pg.wait_for_timeout(700)
            plan = pg.evaluate("store.plans.at(-1)")
            check(plan.get('time') == '18:00' and len(plan['sections']['main']) == 3 and plan['sections']['main'][0].get('note') == 'Глубже по диагонали' and plan['summary']['success'] == 'Стабильный кросс', f'{tag}: saved record')
            ov = pg.locator('#overlay').inner_text()
            ov = pg.locator('#overlay').text_content(); check('Упражнения' in ov and '18:00' in ov and 'Глубже по диагонали' in ov, f'{tag}: record view shows exercises/time')
            pg.locator('[data-action="close-overlay"]:visible').last.tap(); pg.wait_for_timeout(500)
            # edit restores carousel + report
            pg.evaluate("openNoteForm({id: store.plans.at(-1).id})"); pg.wait_for_timeout(500)
            check(pg.locator('#note-form .nex-card').count() == 3 and pg.locator('#note-form [name="time"]').input_value() == '18:00', f'{tag}: edit restores')
            check(pg.locator('#note-form .fold[data-fold="note-report"]').get_attribute('class').find('is-open') >= 0, f'{tag}: report open when filled')
            pg.locator('[data-action="close-overlay"]:visible').last.tap(); pg.wait_for_timeout(500)
            # toast matches card edges
            pg.evaluate("toast('Проверка ширины')"); pg.wait_for_timeout(350)
            tb = pg.locator('#toast .toast').last.bounding_box(); cb = pg.locator('.main .fold').first.bounding_box()
            check(abs(tb['x'] - cb['x']) < 1.5 and abs(tb['width'] - cb['width']) < 1.5, f'{tag}: toast edges {tb["x"]},{tb["width"]} vs {cb["x"]},{cb["width"]}')
            # library sections
            pg.locator('[data-view="exercises"]').click(); pg.wait_for_timeout(400)
            pg.evaluate("store.exerciseOverrides.gs01 = {title: 'Мой кросс'}; persist(); updateExerciseList()")
            pg.locator('[data-action="lib-sections"]').tap(); pg.wait_for_timeout(450)
            pg.locator('[data-action="lib-new"]').tap(); pg.wait_for_timeout(200)
            sid = pg.evaluate("store.library.sections[0] && store.library.sections[0].id")
            check(bool(sid), f'{tag}: section created')
            for _ in range(3): pg.locator(f'.lsec-row[data-key="{sid}"] [data-dir="-1"]').tap(); pg.wait_for_timeout(60)
            pg.evaluate("document.querySelectorAll('#toast .toast').forEach(n => n.remove())")
            if tag == '390-light': pg.screenshot(path=str(shots / 'v46-sections-390.png'))
            pg.locator('[data-action="close-overlay"]:visible').last.tap(); pg.wait_for_timeout(500)
            pg.evaluate("openExercise('nt02', {source:'library'})"); pg.wait_for_timeout(500)
            pg.locator('#ex-sec').select_option(sid); pg.wait_for_timeout(150)
            pg.locator('[data-action="close-overlay"]:visible').last.tap(); pg.wait_for_timeout(500)
            sec = pg.locator(f'.fold[data-fold="excat-{sid}"]')
            check(sec.count() == 1 and sec.locator('.fold-count').inner_text() == '1', f'{tag}: exercise in own section')
            groups = pg.evaluate("groupExercises(allExercises()).map(g => [g[0], g[1].map(e => e.id)])")
            check(sum(1 for g in groups if 'gs01' in g[1]) == 2, f'{tag}: edited built-in in Мои and its section')
            pg.locator('[data-action="lib-sections"]').tap(); pg.wait_for_timeout(450)
            pg.locator(f'.lsec-row[data-key="{sid}"] [data-action="lib-delete"]').tap(); pg.wait_for_timeout(150)
            check('Куда их перенести' in pg.locator('#lib-sec-body').inner_text(), f'{tag}: delete asks where to move')
            pg.locator('[data-action="lib-del-to"][data-to=""]').tap(); pg.wait_for_timeout(150)
            check(pg.evaluate("store.library.sections.length") == 0 and pg.evaluate("Object.keys(store.library.place).length") == 0, f'{tag}: section deleted, exercises back')
            pg.locator('[data-action="close-overlay"]:visible').last.tap(); pg.wait_for_timeout(400)
            # reload keeps data
            pg.reload(); pg.wait_for_timeout(500)
            check(pg.evaluate("store.plans.at(-1).time") == '18:00', f'{tag}: reload keeps record')
            check(pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f'{tag}: no horizontal scroll')
            check(not errs, f'{tag}: page errors {errs}')
            print('done', tag)
            c.close()
    b.close()
print("FAILS", fails)
assert not fails, fails
print("PASS WebKit 390/430 light/dark: record form, picker, report, time, keyboard ride, toast edges, library sections")
