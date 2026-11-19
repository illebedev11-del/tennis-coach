"""Reminder gestures and personal groups in mobile Chrome."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
    for width in (390, 430):
        for theme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": width, "height": 932},
                is_mobile=True, has_touch=True, color_scheme=theme, reduced_motion="reduce")
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: d.accept("Мой шаблон") if d.type == "prompt" else d.accept())
            page.goto((Path(__file__).resolve().parents[1] / "index.html").as_uri())
            date = page.evaluate("""() => {
                const date=isoShift(dateISO(),-1);
                store.plans.push({id:'due',kind:'plan',status:'planned',date,
                    studentIds:[],groupIds:['demog1'],plannedStudentIds:['demo1','demo2'],sections:emptySections()});
                persist(); render(); return date;
            }""")
            reminder = page.locator('[data-action="report-reminder"][data-id="due"]')
            expect(reminder).to_contain_text("Нет записи за")
            reminder.tap()
            expect(page.locator('#note-form [name="date"]')).to_have_value(date)
            expect(page.locator('#note-form')).to_contain_text("Вечерняя группа")
            page.locator('#note-form [name="notes"]').fill("Работали над подачей")
            page.locator('#note-form [type="submit"]').tap()
            page.locator('[data-action="close-overlay"]:visible').last.tap()
            expect(reminder).to_have_count(0)
            page.evaluate("""() => {
                store.plans=store.plans.filter(p=>p.kind!=='note'); persist(); render();
            }""")
            # Use the same pointer path as the application swipe handler.
            box = reminder.bounding_box()
            y = box["y"] + box["height"]/2
            touch = ctx.new_cdp_session(page)
            touch.send("Input.dispatchTouchEvent", {"type":"touchStart","touchPoints":[{"x":width-35,"y":y}]})
            for x in (width-70,width-130,width-200,45):
                touch.send("Input.dispatchTouchEvent", {"type":"touchMove","touchPoints":[{"x":x,"y":y}]})
            touch.send("Input.dispatchTouchEvent", {"type":"touchEnd","touchPoints":[]})
            expect(reminder).to_have_count(0)
            page.reload()
            expect(reminder).to_have_count(0)
            page.locator('[data-view="exercises"]').tap()
            page.evaluate("""() => {
                store.exerciseOverrides.gs01={title:'Мой кросс'};
                store.customExercises.push({...seedExercises[0],id:'own',title:'Моя разминка'});
                persist(); updateExerciseList();
            }""")
            mine = page.locator('[data-fold="excat-Мои"]')
            expect(mine).to_be_visible()
            expect(mine.locator('.exercise-title')).to_have_count(2)
            expect(mine).to_contain_text("моё")
            mine.locator('.fold-head').first.tap()
            page.evaluate("updateExerciseList()")
            mine.locator('.fold-head').first.tap()
            expect(mine.locator('.exercise-title')).to_have_count(2)
            page.locator('#search').fill("Мой кросс")
            expect(mine.locator('.exercise-title')).to_have_count(1)
            page.locator('[data-view="training"]').tap()
            page.evaluate("""() => {
                draft.sections.main=['gs01']; ui.folds['new-plan']=true; render();
            }""")
            page.locator('[data-action="save-template"]').tap()
            expect(page.locator('.template-groups .tpl-row').first).to_contain_text("Мои")
            expect(page.locator('.template-groups .tpl-row').first).to_contain_text("Мой шаблон")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
            ctx.close()
            print(f"PASS {width}, {theme}: reminder date, save, swipe, reload, personal exercises, new template")
    browser.close()
