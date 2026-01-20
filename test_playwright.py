from playwright.sync_api import sync_playwright

def run():
    print("Attempting to launch Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print("Chromium launched successfully.")
        page = browser.new_page()
        page.goto("http://example.com")
        print("Page title:", page.title())
        browser.close()
    print("Playwright test complete.")

if __name__ == "__main__":
    run()
