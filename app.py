from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from playwright.async_api import async_playwright
from playwright.async_api import Page, TimeoutError
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv
import re
import json
import base64
import os



# service_account_b64 = os.environ["GOOGLE_CREDENTIALS"]
# service_account_json = base64.b64decode(service_account_b64).decode("utf-8")
# service_account_info = json.loads(service_account_json)

# creds = Credentials.from_service_account_info(
#     service_account_info,
#     scopes=["https://www.googleapis.com/auth/spreadsheets"]
# )

# Flow: 
# GHL fires the webhook → 
# FastAPI receives order → 
# Playwright logs in & creates a New Sale on Boulevard with the order details.

# Load variables from .env into environment
load_dotenv()

LOGIN_URL = "https://dashboard.boulevard.io/login-v2"
HOME_URL = "https://dashboard.boulevard.io/home"

EMAIL = os.getenv("BLVD_EMAIL")
PASSWORD = os.getenv("BLVD_PASSWORD")
SESSION_FILE = "session.json"

app = FastAPI()


# 1️⃣ Google Service Account credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_json = base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_B64")).decode("utf-8")
service_account_info = json.loads(service_account_json)
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

# 2️⃣ Connect to Google Sheets
client = gspread.authorize(creds)

# Replace with your sheet ID and sheet name
SPREADSHEET_ID = "1CVJHvISuAmADdmG9GjLM_zzpgD4daQ_CDtEHfvbBjNM"
SHEET_NAME = "Sheet1"

# Create a worksheet object you can reuse
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)


sample_order = {
  "event": "payment_received",
  "payment": {
    "transaction_id": "string",
    "source": "Consultation",               
    "currency_symbol": "$",
    "currency_code": "USD",
    "sub_total_amount": "decimal_string",
    "discount_amount": "decimal_string",
    "coupon_code": "string or null",
    "tax_amount": "decimal_string",
    "created_on": "timestamp",
    "total_amount": "decimal_string",
    "payment_status": "Success" or "Failed",
    "gateway": "Stripe",
    "method": "card" ,
    "card": {
      "last4": "1234",
      "brand": "Visa"
    }
  },
  "customer": {
    "id": "string",
    "first_name": "Amanda",
    "last_name": "Martini",
    "name": "Amanda Martini",
    "email": "eyedocmartini@gmail.com",
    "phone": "(361) 876-0047",
    "address": "string",
    "city": "string",
    "state": "string",
    "country": "string",
    "postal_code": "string"
  },
  "invoice": {
    "name": "string",
    "number": "string",
    "issue_date": "date_string",
    "due_date": "date_string",
    "url": "string",
    "recorded_by": "string"
  }
}

async def is_logged_in(page):
    try:
        await page.goto(HOME_URL, wait_until="load", timeout=10000)
    except TimeoutError:
        return False

    # Check for a known element that only exists when logged in
    return await page.is_visible("css=horizontal-menu")  # adjust selector

async def login(context, page):
    await page.goto(LOGIN_URL, wait_until="load", timeout=30000)

    # Ensure we are actually on the login page
    if not await page.is_visible("input[name='email']"):
        print("Already logged in or redirected")
        return


    await page.fill("input[name='email']", EMAIL)
    await page.fill("input[name='password']", PASSWORD)
    await page.click("button[type='submit']")
    await page.wait_for_selector("horizontal-menu", timeout=30000)
    await context.storage_state(path=SESSION_FILE)
    print("Login successful, session saved.")

async def check_client_record(page: Page, name: str, timeout: int = 10000) -> bool:
    """
    Waits up to `timeout` ms to see if the 'No results found' element appears.
    Returns:
        True  -> record exists
        False -> no record found
    """
    try:
        # Search for client by name
        await page.wait_for_selector("#client-search-input", timeout=10000)
        await page.type("#client-search-input", name)  # replace with order_data name

        # check if the no results element appears
        await page.wait_for_timeout(20000)  # wait a bit for search to process
         # Wait for either the "No results found" element or timeout   
        is_visible = await page.is_visible(
            "tbody[data-testid='table-body'] span:has-text('No results found')")
        if is_visible:
            return False
        else:
            return True

    except TimeoutError:
        # Timed out → records likely exist
        print("Timeout waiting for 'No results found' element. Assuming records do not exist.")
        return False


async def get_first_client_record(page: Page, name: str) -> dict | None:
    """
    Returns a dict with the first row's name, email, and phone.
    If no rows are present, returns None.
    """
    # Search for client by name
    await page.wait_for_selector("#client-search-input", timeout=10000)
    #clear input first
    await page.fill("#client-search-input", "")
    await page.type("#client-search-input", name)  # replace with order_data name

    await page.wait_for_timeout(40000)  # wait a bit for search to process
    row_locator = page.locator("tbody[data-testid='table-body'] tr").first

    # Check if there is at least 1 row
    if await row_locator.count() == 0:
        print("No client records found.")
        return None

    # Adjust nth() indexes if your table column order differs
    name  = (await row_locator.locator("td").nth(0).inner_text()).strip()
    email = (await row_locator.locator("td").nth(3).inner_text()).strip()
    phone = (await row_locator.locator("td").nth(2).inner_text()).strip()

    return {
        "name": re.sub(r"^[A-Z]\s*\n", "", name).strip(),   # removes T\n, extra spaces, auto generated
        "email": " ".join(email.split()).strip(),
        "phone": phone
    }
    
async def create_client_record(page: Page, client: dict) -> bool:
    print("Creating new client record...")
    try:
        await page.get_by_role("button", name="Add client").click()

        await page.wait_for_selector('#create-client-form')
        form = page.locator('#create-client-form')

        await form.get_by_label("First name").fill(client.get("first_name", ""))
        await form.get_by_label("Last name").fill(client.get("last_name", ""))
        await form.get_by_label("Email address").fill(client.get("email", ""))
        await form.get_by_label("Phone number").fill(client.get("phone", ""))

        # Submit the form
        # Hide for testing
        print("Client profile created. (Submission skipped in test mode.)")
        #await form.locator('button[type="submit"]').click()

        # await form.get_by_role("button", name="Create client").click()

        return True
    except Exception as e:
        print("Error creating client:", e)
        return False


async def wait_until_homepage_load(page, check_selector="a.top-link[href='/clients']", total_timeout=120, interval=5):
    """
    Repeatedly check if the given selector is visible until logged in or timeout.
    total_timeout: total seconds to wait before giving up
    interval: seconds between checks
    """
    elapsed = 0
    while elapsed < total_timeout:
        # If element is visible, user is logged in
        if await page.is_visible(check_selector):
            print("✅ Logged in!")
            return True
        print(f"⏳ Not logged in yet... waited {elapsed}/{total_timeout} seconds")
        await page.wait_for_timeout(interval * 1000)
        elapsed += interval
    return False  # Timed out


async def run_playwright(sale_data: dict):
    """
    sale_data contains GHL order info.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, devtools=False)  # set headless=True for production
        context = await browser.new_context()
        page = await context.new_page()

        sale_customer = sale_data.get("customer", {})
        sale_payment = sale_data.get("payment", {})
        

        # 1️⃣ Go to login page first
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")


        # 2️⃣ Wait up to 30 seconds to see if we are auto-logged in
        try:
            await page.wait_for_function(
                f"window.location.href === '{HOME_URL}'",
                timeout=10000  # 30 seconds
            )
            print("✅ Already logged in!")
            # You can now continue to home actions
            return
        except:
            print("⏳ Still on login page, need to check login form...")


        # 3️⃣ Check if the email input exists (user must log in)
        try:
            await page.wait_for_selector("input[name='email']", timeout=20000)
            print("🔑 Login form is present. Proceed with login.")
            # 👉 Perform login steps here if you have credentials
            await page.fill("input[name='email']", EMAIL)
            await page.fill("input[name='password']", PASSWORD)
            await page.click("button[type='submit']")
        except:
            print("⚠️ Neither home nor login form appeared. Check the page or URL.")


        # Go to Client profile page
        print("Waiting for home page to load...")
        await page.wait_for_timeout(10000)

        # Start checking in a loop
        logged_in = await wait_until_homepage_load(page, total_timeout=120, interval=5)

        if not logged_in:
            print("❌ Still not logged in after 120 seconds. Closing browser.")
            await browser.close()
            return
   
        await page.click("a.top-link[href='/clients']")



        # ✅ Modular check
        has_record = await check_client_record(page, sale_customer.get("name", ""))
        print("Record exists:", has_record)


        if not has_record:
            # wait a bit for the search to process
            await page.wait_for_timeout(5000)
            has_record = await create_client_record(page, sale_customer)
            print("Rechecked record exists:", has_record)

        # if name found, verify email and phone matches
        if has_record:
            first_record = await get_first_client_record(page, sale_customer.get("name", ""))
            if first_record:
                client_name = first_record["name"].lower()
                client_email = first_record["email"].lower()
                client_phone = first_record["phone"].replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

                print("First record:", first_record)

                # Compare with sale_data customer info
                
                sale_name = sale_customer.get("name", "").lower()
                sale_email = sale_customer.get("email", "").lower()
                sale_phone = sale_customer.get("phone", "").replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

                # create a simple match logic
                name_match = client_name == sale_name
                email_match = client_email == sale_email
                phone_match = client_phone == sale_phone
                print(f"Name match: {name_match}, Email match: {email_match}, Phone match: {phone_match}")
                
                if name_match and (email_match and phone_match):
                    print("Client verified.")
                    # select the client
                    await page.locator("tbody[data-testid='table-body'] tr").first.click()
                    #wait for the pop up to load
                    # await page.wait_for_selector(
                    #     'md-sidenav[md-component-id="ClientProfile"]',
                    #     timeout=10000  
                    # )

                    # Click the "New Sale" button inside that container
                    await page.click(
                        'button.tertiary.md-button[aria-label="New Sale"]',
                        timeout=10000
                    )

                    # Wait for the checkout modal to appear
                    await page.wait_for_selector(
                        'div.modal-dock modal.checkout-modal',
                        timeout=10000
                    )
                    print("New Sale modal opened.")

                    # Fill in product details here
                    #fl-input-2485
                    #

                    container = page.locator(
                        'md-input-container:has(label:has-text("Search by product name, SKU, or barcode"))'
                    ).nth(0)   # use nth(1), nth(2), etc. for the desired one
                    await container.click()
                    print("Typing product name...", sale_payment.get("source", ""))
                    await container.type(sale_payment.get("source", ""))

                    #await page.fill("input[name='fl-input-2485']", sale_payment.get("source", ""))
                    # wait for a bit to see the product suggestion
                    #to delete
                    await page.wait_for_timeout(5000)
                    #select the first suggestion
                    await page.keyboard.press("ArrowDown")
                    await page.keyboard.press("Enter")
                    #to delete
                    await page.wait_for_timeout(10000)

                    await page.locator('md-tabs-canvas md-tab-item .target[data-tab="Other"]').click()

                    # select payment method
                    method_select = page.locator(
                        'div.MuiSelect-root[role="button"]#mui-component-select-method'
                    )

                    if await method_select.is_visible():
                        await method_select.click()

                    await page.locator("span:text('GoHighLevel')").scroll_into_view_if_needed()
                    await page.click("ul[role='listbox'] span:has-text('GoHighLevel')")
                    print("Product added to the sale.")

                    # Click Charge button
                    charge_btn = page.locator('button[aria-label="Add Other Payment"]')
                    if await charge_btn.is_visible() and await charge_btn.is_enabled():
                        print("Clicking Charge button...")
                        #await charge_btn.click()


            else:
                print("No visible rows despite has_record=True")



        # Save session
        #await context.storage_state(path=SESSION_FILE)
        #pause 20 seconds
        await page.wait_for_timeout(120000)
        await browser.close()



# ---- API Routes ----
@app.post("/webhook/ghl-order")
async def ghl_webhook(request: Request, background_tasks: BackgroundTasks):

    """
    Insert order into Google Sheets with 'pending' status.
    """



    """
    GHL will POST here when an order is completed.

    """
    if not EMAIL or not PASSWORD:
        raise HTTPException(status_code=500, detail="Boulevard credentials not set in environment.")

    payload = await request.json()

    #test only 
    #payload = sample_order

    #prod

    print("Received payload:", payload)
    try:
        data = payload.get("customer", {})
        # create variable current datetime string
        date_str = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_values = [data["name"], data["email"], data["phone"], "pending", date_str]
        sheet.append_row(row_values)
        # gspread append_row returns nothing, but you can calculate row index:
        row_index = len(sheet.get_all_values())  # last row index
        print(f"Inserted row {row_index} with pending status.")
    except Exception as e:
        print("Error inserting row into Google Sheets:", e)
        raise HTTPException(status_code=500, detail="Error inserting row into Google Sheets.")

    # Immediately return 200 to GHL, run automation in background
    print("Background task started...")
    try:

        background_tasks.add_task(run_playwright, payload)
        return {"status": "success"}
    except Exception as e:
        print("Error starting background task:", e)
        raise HTTPException(status_code=500, detail="Error starting background task.")


@app.post("/webhook-test/ghl-order")
async def test():
    """
    Insert order into Google Sheets with 'pending' status.
    """
    # 1️⃣ Insert row with 'pending' status
    
    data = sample_order.get("customer", {})
    # create variable current datetime string
    date_str = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_values = [data["name"], data["email"], data["phone"], "pending", date_str]
    sheet.append_row(row_values)
    # gspread append_row returns nothing, but you can calculate row index:
    row_index = len(sheet.get_all_values())  # last row index
    print(f"Inserted row {row_index} with pending status.")
    #return {"status": "done"}


    """
    GHL will POST here when an order is completed.

    """
    print("Background task started...")
    await run_playwright(sample_order)
    # Immediately return 200 to GHL, run automation in background
    return {"status": "done"}


# @app.post("/run")
# async def run_task():
#     if not EMAIL or not PASSWORD:
#         raise HTTPException(status_code=500, detail="Credentials not set in environment.")
#     await run_playwright()
#     return {"status": "Automation completed"}
