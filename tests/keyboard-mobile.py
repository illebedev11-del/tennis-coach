"""WebKit regression for the note form when the visible viewport shrinks."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

output = Path(os.getenv("SCREENSHOT_DIR", "/tmp/tennis-keyboard"))
output.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.webkit.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844},
        is_mobile=True, has_touch=True, device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Model the visual viewport separately from the layout viewport, as with the iOS keyboard.
    page.add_init_script("""try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}""")
    page.add_init_script("""(() => {
        const viewport = new EventTarget();
        Object.assign(viewport, {height:844,width:390,offsetTop:0,offsetLeft:0,scale:1});
        Object.defineProperty(window,'visualViewport',{value:viewport,configurable:true});
        window.testKeyboard = (height, top=0) => {
            viewport.height=height; viewport.offsetTop=top;
            viewport.dispatchEvent(new Event('resize'));
        };
    })()""")
    page.goto((Path(__file__).resolve().parents[1] / "index.html").as_uri())
    page.get_by_role('button', name='Записать занятие', exact=True).tap()
    page.locator('#note-form [data-action="who-toggle"][data-kind="s"]').first.tap()
    notes = page.locator('#note-form [name="notes"]')
    notes.tap()
    page.evaluate("testKeyboard(460)")
    page.wait_for_function("document.documentElement.classList.contains('kb-on')")

    def visible_field(field):
        # Привязываемся к самому полю: в CI WebKit фокус иногда сбрасывается, а длинное поле
        # не умещается целиком в видимую область — это уже проявлялось как ложный таймаут (v50, v51).
        el = field.element_handle()
        field.evaluate("el => el.focus()")
        page.wait_for_function("""el => {
            if (!el || !el.isConnected) return false;
            if (document.activeElement !== el) el.focus();
            const modal = el.closest('.modal');
            if (!modal) return false;
            const r = el.getBoundingClientRect(), m = modal.getBoundingClientRect();
            const vv = window.visualViewport;
            const bot = Math.min(m.bottom, ((vv && vv.offsetTop) || 0) + (vv ? vv.height : innerHeight));
            if (r.height > bot - m.top + 2) return r.top < bot && r.bottom > m.top;
            return r.top >= m.top - 1 && r.bottom <= bot + 1;
        }""", arg=el)
        # v49: поле плавно прокручивается над закреплённым низом — ждём окончания плавной прокрутки
        page.wait_for_function("""el => {
            const r = el.getBoundingClientRect();
            const vv = window.visualViewport;
            const bot = ((vv && vv.offsetTop) || 0) + (vv ? vv.height : innerHeight);
            const y = Math.min(Math.max(r.top + Math.min(35, r.height / 2), 1), bot - 1);
            const hit = document.elementFromPoint(r.left + 20, y);
            return hit === el || (hit && el.contains(hit));
        }""", arg=el, timeout=2500)

    visible_field(notes)
    notes.press_sequentially("Работали над подачей. ", delay=25)
    notes.press("Enter")
    notes.press_sequentially("Сохраняем равновесие после удара.", delay=25)
    visible_field(notes)
    # v50: закреплённый низ остаётся на месте (клавиатура наезжает на него), окно не меняет размер
    expect(page.locator('#note-form .form-actions')).to_have_css("position", "sticky")
    assert page.evaluate("document.querySelector('#overlay .sheet').getBoundingClientRect().bottom > 700")
    page.screenshot(path=output / "note-keyboard-390.png")

    notes.fill("\n".join(["Длинная запись о тренировке"] * 18))
    notes.press("End")
    visible_field(notes)
    # v46: отчёт свёрнут в «Добавить отчёт»
    page.locator('#note-form .fold[data-fold="note-report"] .fold-head').first.tap()
    page.wait_for_function("""() => document.querySelector('#note-form .fold[data-fold="note-report"]').classList.contains('is-open')""")
    page.wait_for_timeout(450)
    for name in ("success","difficulty","next"):
        field = page.locator(f'#note-form [name="{name}"]')
        field.evaluate("el => el.focus()")
        field.press_sequentially("Мяч в глубину.", delay=25)
        visible_field(field)
    page.screenshot(path=output / "report-keyboard-390.png")
    page.evaluate("testKeyboard(430,30)")
    page.wait_for_function("document.documentElement.style.getPropertyValue('--vvt') === '30px'")
    visible_field(page.locator('#note-form [name="next"]'))
    page.evaluate("document.activeElement.blur(); testKeyboard(844)")
    page.wait_for_function("!document.documentElement.classList.contains('kb-on')")
    expect(notes).to_have_value("\n".join(["Длинная запись о тренировке"] * 18))
    page.locator('#note-form [type="submit"]').tap()
    expect(page.locator("#overlay")).to_contain_text("Длинная запись о тренировке")
    assert page.evaluate("store.plans.at(-1).summary.next") == "Мяч в глубину."
    assert not errors, errors
    print("PASS WebKit 390: keyboard open/close, viewport pan, multiline input, field visibility, unobstructed typing, save")
    browser.close()
