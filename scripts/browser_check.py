"""Local browser QA using an installed Edge; screenshots remain ignored artifacts."""
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
artifacts = root/"artifacts"
artifacts.mkdir(exist_ok=True)
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8080")
    page.get_by_role("heading", name="Welcome to your workspace.").wait_for()
    page.screenshot(path=str(artifacts/"login-dark.png"), full_page=True)
    page.get_by_role("button", name="Enter workspace").click()
    page.get_by_role("heading", name="Your cases. Moving forward.").wait_for()
    page.screenshot(path=str(artifacts/"queue-dark.png"), full_page=True)
    assert page.locator(".case-card").count() == 12
    page.get_by_role("button", name="Singapore", exact=True).click()
    assert page.locator(".case-card").count() == 4
    page.get_by_placeholder("Find a company or case").fill("Helios")
    assert page.locator(".case-card").count() == 1
    page.get_by_role("button", name="Review & chase").click()
    page.get_by_role("heading", name="Helios Maritime Ltd").wait_for()
    page.screenshot(path=str(artifacts/"workspace-dark.png"), full_page=True)
    for path, title in (("/nudges", "A timely nudge. A human touch."), ("/trace", "Every step. An open book."), ("/studio", "The right words. Your standards."), ("/finops", "Clarity on cost. Focus on impact."), ("/policy", "A clear answer. A source to trust.")):
        page.goto("http://127.0.0.1:8080"+path)
        page.get_by_role("heading", name=title).wait_for()
        assert page.locator("body").evaluate("e => e.scrollWidth <= innerWidth"), path
        page.screenshot(path=str(artifacts/(path[1:]+"-dark.png")), full_page=True)
    page.get_by_role("button", name="Toggle color theme").click()
    page.screenshot(path=str(artifacts/"policy-light.png"), full_page=True)
    page.goto("http://127.0.0.1:8080")
    page.get_by_role("heading", name="Your cases. Moving forward.").wait_for()
    page.screenshot(path=str(artifacts/"queue-light.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(artifacts/"queue-mobile.png"), full_page=True)
    assert page.locator("body").evaluate("e => e.scrollWidth <= innerWidth")
    page.get_by_role("button", name="Toggle navigation").click()
    page.get_by_role("link", name="FinOps & Impact").click()
    page.get_by_role("heading", name="Clarity on cost. Focus on impact.").wait_for()
    assert page.locator("body").evaluate("e => e.scrollWidth <= innerWidth")
    assert not errors, errors
    browser.close()
print("Browser QA passed: login, filtering, case review, all seven authenticated pages, theme toggle and mobile navigation; no browser errors.")
