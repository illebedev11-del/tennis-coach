"""Run with Python Playwright and its Chromium browser (or CHROMIUM_PATH)."""
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def check(browser, width, height):
    context = browser.new_context(
        viewport={"width": width, "height": height}, is_mobile=True,
        has_touch=True, reduced_motion="reduce", accept_downloads=True,
    )
    page = context.new_page()
    page.set_default_timeout(7000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", lambda dialog: dialog.accept())
    page.add_init_script("""try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}""")
    page.goto((Path(__file__).resolve().parents[1] / "index.html").as_uri())

    def action(name):
        return page.locator(f'[data-action="{name}"]:visible').last

    def fits():
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

    page.locator('[data-view="exercises"]').tap()
    page.locator("#search").fill("форхенд")
    expect(page.locator("#exerciseList")).to_contain_text("Форхенд", ignore_case=True)
    fits()
    page.locator("#search").fill("обратный кросс")
    page.locator('[data-action="toggle-fold"][data-fold="filters"]').tap()
    page.locator("#format").select_option("С корзиной")
    drill = page.locator('[data-action="detail-ex"][data-id="kb29"]')
    drill.get_by_role("heading").tap()
    expect(page.locator("#overlay")).to_contain_text("Широкая подача и обратный кросс форхендом")
    page.locator('[data-action="toggle-fold"][data-fold="drill-steps-kb29"]').tap()
    expect(page.locator('#overlay .pre-line')).to_be_visible()
    fits()
    action("close-overlay").tap()
    page.locator('[data-view="students"]').tap()
    card = page.locator('[data-action="student-detail"]').first
    card.scroll_into_view_if_needed()
    bounds = card.bounding_box()
    touch = context.new_cdp_session(page)
    touch.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [
        {"x": bounds["x"] + bounds["width"] / 2, "y": bounds["y"] + bounds["height"] / 2}
    ]})
    expect(page.locator('.peek-menu')).to_be_visible()
    touch.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.keyboard.press("Escape")
    expect(page.locator('.peek-menu')).to_have_count(0)
    card.tap()
    expect(page.locator("#overlay")).to_contain_text("История занятий")
    action("close-overlay").tap()
    page.locator('[data-view="training"]').tap()
    action("new-note").tap()
    page.locator('#note-form [data-action="who-toggle"][data-kind="g"]').first.tap()
    page.locator('#note-form [name="attendance"][value="demo2"]').locator("..").tap()
    page.locator('#note-form [name="notes"]').fill("Мобильная групповая тренировка")
    page.locator('#note-form [type="submit"]').tap()
    expect(page.locator("#overlay")).to_contain_text("Были:")
    fits()
    action("close-overlay").tap()
    # Seed a saved plan and a changed group. Use the actual report and correction forms.
    plan_id = page.evaluate("""() => {
        store.students.push(normalizeStudent({id:'guest', name:'Вера'}));
        draft.who=legacyWho('group','demog1'); draft.sections.main=[seedExercises[0].id]; savePlan();
        getGroup('demog1').studentIds=['demo2','guest']; persist();
        return store.plans.at(-1).id;
    }""")
    page.evaluate("id => openPlan(id)", plan_id)
    report = page.locator('#finish-plan-form')
    # Everyone planned is pre-checked; only the planned people are listed.
    expect(report.locator('[name="attendance"][value="demo1"]')).to_be_checked()
    expect(report.locator('[name="attendance"][value="demo2"]')).to_be_checked()
    expect(report.locator('[name="attendance"][value="guest"]')).to_have_count(0)
    report.locator('[name="attendance"][value="demo2"]').locator("..").tap()
    report.locator('[data-action="att-add"]').tap()
    report.locator('.att-search').fill("Вер")
    report.locator('[data-action="att-pick"][data-id="guest"]').tap()
    page.reload()
    page.evaluate("id => openPlan(id)", plan_id)
    expect(report.locator('[name="attendance"][value="guest"]')).to_be_checked()
    expect(report.locator('[name="attendance"][value="demo2"]')).not_to_be_checked()
    report.locator('[name="success"]').fill("20 кроссов")
    report.locator('[type="submit"]').tap()
    expect(page.locator("#overlay")).to_contain_text("20 кроссов")
    action("edit-attendance").tap()
    correction = page.locator('#attendance-form')
    correction.locator('[value="demo1"]').locator("..").tap()
    correction.locator('[type="submit"]').tap()
    expect(page.locator("#overlay")).to_contain_text("Были: Вера")
    fits()
    action("close-overlay").tap()
    action("info").tap()
    with page.expect_download() as pending:
        action("export-data").tap()
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "backup.json"
        pending.value.save_as(file)
        original = json.loads(file.read_text())
        assert len(original["data"]["plans"]) == 2
        page.evaluate("store.plans = []; persist();")
        page.locator('#import-file').set_input_files(file)
        page.locator('[data-action="restore-merge"]:visible').wait_for()
        page.locator('[data-action="restore-merge"]:visible').tap()
        page.wait_for_function("store.plans.length === 2")
        page.reload()
        page.wait_for_function("store.plans && store.plans.length === 2")
        assert page.evaluate("plansForStudent('demo1').length") == 1
        assert page.evaluate("plansForStudent('demo2').length") == 0
        assert page.evaluate("id => getPlan(id).actualStudentIds", plan_id) == ["guest"]
        assert page.evaluate("id => getPlan(id).plannedStudentIds", plan_id) == ["demo1", "demo2"]
        action("info").tap()
        with page.expect_download() as recovery:
            action("export-previous").tap()
        recovery.value.save_as(file)
        assert json.loads(file.read_text())["data"]["plans"] == []
    fits()
    assert not errors, errors
    context.close()
    print(f"PASS {width}×{height}: navigation, search, student history, group note, attendance draft, report, correction, export/import, recovery")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
        for viewport in [(375, 812), (390, 844), (844, 390)]:
            check(browser, *viewport)
        browser.close()
