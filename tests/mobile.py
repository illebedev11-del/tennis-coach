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
    page.goto((Path(__file__).resolve().parents[1] / "index.html").as_uri())

    def action(name):
        return page.locator(f'[data-action="{name}"]:visible').last

    def fits():
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

    page.locator('[data-view="exercises"]').tap()
    page.locator("#search").fill("форхенд")
    expect(page.locator("#exerciseList")).to_contain_text("Форхенд", ignore_case=True)
    fits()
    page.locator('[data-view="students"]').tap()
    page.locator('[data-action="student-detail"]').first.tap()
    expect(page.locator("#overlay")).to_contain_text("История занятий")
    action("close-overlay").tap()
    page.locator('[data-view="training"]').tap()
    action("new-note").tap()
    page.locator('#note-form [data-action="who-toggle"][data-kind="g"]').first.tap()
    page.locator('#note-form [name="notes"]').fill("Мобильная групповая тренировка")
    page.locator('#note-form [type="submit"]').tap()
    expect(page.locator("#overlay")).to_contain_text("Участники:")
    fits()
    action("close-overlay").tap()
    action("info").tap()
    with page.expect_download() as pending:
        action("export-data").tap()
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "backup.json"
        pending.value.save_as(file)
        original = json.loads(file.read_text())
        assert len(original["data"]["plans"]) == 1
        page.evaluate("store.plans = []; persist();")
        page.locator('#import-file').set_input_files(file)
        page.wait_for_function("store.plans.length === 1")
        page.reload()
        assert page.evaluate("plansForStudent('demo1').length") == 1
        action("info").tap()
        with page.expect_download() as recovery:
            action("export-previous").tap()
        recovery.value.save_as(file)
        assert json.loads(file.read_text())["data"]["plans"] == []
    fits()
    assert not errors, errors
    context.close()
    print(f"PASS {width}×{height}: navigation, search, student history, group note, export/import, recovery")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
        for viewport in [(375, 812), (390, 844), (844, 390)]:
            check(browser, *viewport)
        browser.close()
