import os
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load variables from .env into environment
load_dotenv()

LOGIN_URL = "https://dashboard.boulevard.io/login-v2"
HOME_URL = "https://dashboard.boulevard.io/home"

EMAIL = os.getenv("BLVD_EMAIL")
PASSWORD = os.getenv("BLVD_PASSWORD")
SESSION_FILE = "session.json"

app = FastAPI()

async def is_logged_in(page):
    await page.goto(HOME_URL, wait_until="domcontentloaded")
    try:
        await page.wait_for_selector("navigation", timeout=5000)
        return True
    except:
        return False

async def login(context, page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await page.fill("input[name='email']", EMAIL)
    await page.fill("input[name='password']", PASSWORD)
    await page.click("button[type='submit']")
    await page.wait_for_selector("horizontal-menu", timeout=30000)
    await context.storage_state(path=SESSION_FILE)

async def run_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # cloud friendly
        try:
            context = await browser.new_context(storage_state=SESSION_FILE)
        except Exception:
            context = await browser.new_context()
        page = await context.new_page()

        if not await is_logged_in(page):
            await login(context, page)

        await page.click("a.top-link[href='/sales']")
        await page.click("button:has-text('New Sale')", timeout=10000)

        await context.storage_state(path=SESSION_FILE)
        await browser.close()

@app.post("/run")
async def run_task():
    if not EMAIL or not PASSWORD:
        raise HTTPException(status_code=500, detail="Credentials not set in environment.")
    await run_playwright()
    return {"status": "Automation completed"}
