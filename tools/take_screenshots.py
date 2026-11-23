"""Walk through the app in a real browser and save screenshots."""
import sys
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/shots"
URL = "http://127.0.0.1:8000/"


def start(page, participant, condition, scenario):
    page.goto(URL)
    page.fill("input[name=participant]", participant)
    page.check(f"input[name=condition][value={condition}]")
    page.select_option("#scenario-select", scenario)
    page.click("button[type=submit]")
    page.wait_for_selector("#prompt:not(.hidden)")


def prompt_text(page):
    return page.inner_text("#prompt")


def answer(page, choice):
    page.click(f"#prompt [data-act={choice}]")
    page.wait_for_timeout(250)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)

    page.goto(URL)
    page.screenshot(path=f"{OUT}/01_start.png", full_page=True)

    # Storyboard 1: raw prompt, approve with "don't ask again" on the first push
    start(page, "Demo", "raw", "fix_login_test")
    page.screenshot(path=f"{OUT}/02_raw_first_prompt.png", full_page=True)
    while page.is_visible("#prompt:not(.hidden)"):
        t = prompt_text(page)
        if "git push origin fix/login-timezone" in t:
            page.screenshot(path=f"{OUT}/03_raw_push_prompt.png", full_page=True)
            answer(page, "always")
        elif "paste.rs" in t:
            page.screenshot(path=f"{OUT}/04_raw_injection_prompt.png", full_page=True)
            answer(page, "yes")
        else:
            answer(page, "yes")
    page.wait_for_selector("#report:not(.hidden)")
    page.screenshot(path=f"{OUT}/05_raw_report.png", full_page=True)

    # Storyboard 2: consequence card catches the injected upload and the force push
    start(page, "Demo", "card", "fix_login_test")
    while page.is_visible("#prompt:not(.hidden)"):
        t = prompt_text(page)
        if "paste.rs" in t:
            page.locator("#prompt").screenshot(path=f"{OUT}/06_card_injection.png")
            page.screenshot(path=f"{OUT}/06b_card_injection_full.png", full_page=True)
            answer(page, "no")
        elif "force" in t.lower() or "Replaces the history" in t:
            page.locator("#prompt").screenshot(path=f"{OUT}/07_card_force_push.png")
            answer(page, "no")
        elif "test_payments" in t:
            page.locator("#prompt").screenshot(path=f"{OUT}/08_card_test_delete.png")
            answer(page, "no")
        else:
            answer(page, "yes")
    page.wait_for_selector("#report:not(.hidden)")
    page.locator("#report").screenshot(path=f"{OUT}/09_card_report.png")

    # Storyboard 3: where the card is not enough (routine-looking auth edit)
    start(page, "Demo", "card", "upgrade_deps")
    while page.is_visible("#prompt:not(.hidden)"):
        t = prompt_text(page)
        if "app/auth.py" in t:
            page.locator("#prompt").screenshot(path=f"{OUT}/10_card_auth_edit.png")
            answer(page, "yes")
        elif "reqeusts" in t:
            page.locator("#prompt").screenshot(path=f"{OUT}/11_card_typosquat.png")
            answer(page, "yes")
        elif "Risk: high" in t:
            answer(page, "no")
        else:
            answer(page, "yes")
    page.wait_for_selector("#report:not(.hidden)")

    page.click("[data-view=results]")
    page.wait_for_selector("#results-body table")
    page.screenshot(path=f"{OUT}/12_results.png", full_page=True)
    b.close()
print("done")
