from fastapi import FastAPI
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import time
from dotenv import load_dotenv


# Load variables from .env into environment
load_dotenv()
LOGIN_URL = "https://dashboard.boulevard.io/login-v2"
HOME_URL = "https://dashboard.boulevard.io/home"
EMAIL = "jhonloydpastorin.03@gmail.com"
PASSWORD= "d"

def is_logged_in(page):
    page.goto(HOME_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_selector("navigation", timeout=5000)
        print("Logged-in using existing session.")
        return True
    except Exception:
        return False
    
def login(context, page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.fill("input[name='email']", EMAIL)
    page.fill("input[name='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_selector("horizontal-menu", timeout=30000)
    context.storage_state(path="session.json")
    print("Logged in and session saved.")
    time.sleep(5)  # ensure full load


def main():
    print("Starting script...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, devtools=True, slow_mo=200)
        try:
            context = browser.new_context(storage_state="session.json")
        except Exception:
            context = browser.new_context()
        page = context.new_page()
        if not is_logged_in(page):
            login(context, page)

        # click sales
        page.click("a.top-link[href='/sales']")
        print("Clicked Sales link.  ")
        
        # click new sale
        page.click("button:has-text('New Sale')", timeout=10000)
        print("Clicked New Sale button.  ")



        context.storage_state(path="session.json")
        print("All suppliers processed.")
        page.wait_for_timeout(10000)  # keeps it open for 10 seconds
        browser.close()

if __name__ == "__main__":
    main()

