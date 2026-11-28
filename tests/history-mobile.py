"""Search and student summary in mobile Chrome, light and dark."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
    for width in (390, 430):
        for theme in ("light", "dark"):
            context = browser.new_context(viewport={"width": width, "height": 932},
                is_mobile=True, has_touch=True, color_scheme=theme, reduced_motion="reduce")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.add_init_script("""try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}""")
            page.goto((Path(__file__).resolve().parents[1] / "index.html").as_uri())
            page.evaluate("""() => {
                store.students[0].name = 'Алёна';
                store.plans.push({id:'search-test',kind:'note',status:'done',date:dateISO(),
                    studentIds:['demo1'],actualStudentIds:['demo1'],plannedStudentIds:['demo1'],
                    notes:'Что делали: приём',summary:{success:'Глубокий приём'},
                    sections:{main:[{id:'gs01',title:'Кросс'}]}});
                ui.folds['saved-plans']=true; render();
            }""")
            search = page.get_by_role("searchbox", name="Поиск по занятиям")
            search.fill("ПРИЕМ")
            card = page.locator('#sess-list [data-id="search-test"][data-action="view-plan"]')
            expect(card.locator("mark").first).to_be_visible()
            card.locator("b").tap()
            expect(page.locator("#overlay")).to_contain_text("приём")
            page.locator('[data-action="close-overlay"]:visible').last.tap()
            search.fill("алена")
            expect(card).to_be_visible()
            page.locator('[data-view="students"]').tap()
            page.locator('[data-action="student-detail"][data-id="demo1"]').tap()
            expect(page.locator("#overlay")).to_contain_text("Статистика")
            expect(page.locator("#overlay")).to_contain_text("занятий всего")
            expect(page.locator("#stats-block")).to_contain_text("1")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
            context.close()
            print(f"PASS {width}, {theme}: search, highlight, open record, summary")
    browser.close()
