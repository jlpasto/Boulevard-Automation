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
  "contact_id": "bxoY65VIdH7laJEOHB4Y",
  "first_name": "Jarrett",
  "last_name": "atherton",
  "full_name": "Jarrett atherton",
  "email": "jarrettatherton@yahoo.com",
  "phone": "+13616586981",
  "tags": "toxins,aspire,26march,for the marketing bulk mssg,toxin,podium trans 09-12,won",
  "address1": "3528 LAWNVIEW ST",
  "city": "CORPUS CHRISTI",
  "state": "Texas",
  "country": "US",
  "date_created": "2025-01-06T16:51:42.192Z",
  "postal_code": "78411",
  "contact_source": "payment_link",
  "full_address": "3528 LAWNVIEW ST, CORPUS CHRISTI Texas 78411",
  "contact_type": "customer",
  "location": {
    "name": "Oceana Luxe Medspa",
    "address": "5242 Holly Rd",
    "city": "Corpus Christi",
    "state": "TX",
    "country": "US",
    "postalCode": "78411",
    "fullAddress": "5242 Holly Rd, Corpus Christi TX 78411",
    "id": "CDR4h44AJ3Ic84nDuigS"
  },
  "user": {
    "firstName": "Amanda",
    "lastName": "Trevino",
    "email": "atrevino@oceanaluxemedspa.com",
    "phone": "+13617791925"
  },
  "workflow": {
    "id": "b7709c6d-9e11-402b-887d-7446a2d67081",
    "name": "Link Payment Paid In Full"
  },
  "payment": {
    "transaction_id": "68d6d4c7545d5d40279ea742",
    "source": "payment_link",
    "payment_status": "succeeded",
    "global_product_ids": [
      "68bb319c9d588d8bc08de5f9"
    ],
    "global_product_price_ids": [
      "68bb319c9d588df1608de604"
    ],
    "line_items": [
      {
        "id": "68bb319c9d588df1608de604",
        "title": "Botox Special - Botox special",
        "image": "https://storage.googleapis.com/builder-preview/payment/product/product-placeholder.png",
        "price": 832,
        "quantity": 1,
        "line_subtotal": 832,
        "line_discount": 0,
        "line_tax": 0,
        "line_price": 832,
        "product_type": "one_time",
        "line_setup_fee": 0,
        "product_submission_type": 1,
        "meta": {
          "product_id": "68bb319c9d588d8bc08de5f9",
          "price_id": "68bb319c9d588df1608de604",
          "order_id": "68d6d4c44d731375fc5561bb"
        }
      }
    ],
    "sub_total_amount": 832,
    "discount_amount": 0,
    "tax_amount": 0,
    "total_amount": 832,
    "method": "gateway",
    "gateway": "stripe",
    "card": {
      "brand": "visa",
      "last4": "4593"
    },
    "currency_symbol": "$",
    "currency_code": "USD",
    "created_at": "2025-09-26T18:00:39.769Z",
    "created_on": "September 26, 2025",
    "customer": {
      "id": "bxoY65VIdH7laJEOHB4Y",
      "first_name": "Jarrett",
      "last_name": "atherton",
      "name": "Jarrett atherton",
      "email": "jarrettatherton@yahoo.com",
      "phone": "+13616586981",
      "address": "3528 LAWNVIEW ST",
      "city": "CORPUS CHRISTI",
      "state": "Texas",
      "country": "US",
      "postal_code": "78411"
    },
    "miscellaneous_charges": 0
  },
  "triggerData": {},
  "contact": {
    "attributionSource": {
      "sessionSource": "CRM UI",
      "medium": "csv_import",
      "mediumId": "null"
    },
    "lastAttributionSource": {
      "sessionSource": "Direct traffic",
      "url": "https://services.leadconnectorhq.com/links/r/2/eyJhbGciOiJIUzI1NiJ9.eyJsaW5rX2lkIjoiZEhBTnZkRFhEZmF0WWdzSnh5QTYiLCJjb250YWN0X2lkIjoiYnhvWTY1VklkSDdsYUpFT0hCNFkiLCJkb21haW4iOiJtc2dzbmRyLmNvbSIsIm1lc3NhZ2VUeXBlIjoic21zIiwibWVzc2FnZUlkIjoiaXRnUEQ4V0hLdG9qODZoYXVaVUQifQ.3gxgFmUmhlYHE0KcjFKePThruoo8sgWOSPykGGa2cQY",
      "utmSource": "null",
      "utmMedium": "null",
      "utmContent": "null",
      "utmTerm": "null",
      "utmKeyword": "null",
      "utmMatchtype": "null",
      "referrer": "null",
      "gclid": "null",
      "userAgent": "null",
      "ip": "null",
      "gaClientId": "null",
      "gaSessionId": "null",
      "medium": "null",
      "mediumId": "null",
      "adName": "null",
      "adGroupId": "null",
      "adSetId": "null",
      "adId": "null",
      "gbraid": "null",
      "wbraid": "null"
    }
  },
  "attributionSource": {},
  "customData": {}
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
        await page.get_by_role("button", name="Add client").wait_for(state="visible")
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


async def run_playwright(payload: dict):
    """
    sale_data contains GHL order info.
    """

    try:

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, devtools=False)  # set headless=True for production
            context = await browser.new_context()
            page = await context.new_page()

            client = {
                "first_name": payload.get("first_name", ""),
                "last_name": payload.get("last_name", ""),
                "full_name": payload.get("full_name", ""),
                "email": payload.get("email", ""),
                "phone": payload.get("phone", "")
            }

            # Payment details
            payment = payload.get("payment", {})
            transaction_id = payment.get("transaction_id", "")
            source = payment.get("source", "")
            payment_status = payment.get("payment_status", "")
            line_items = payment.get("line_items", [])
            title = ", ".join([item.get("title", "") for item in line_items])
            sub_total_amount = payment.get("sub_total_amount", 0)
            discount_amount = payment.get("discount_amount", 0)
            tax_amount = payment.get("tax_amount", 0)
            total_amount = payment.get("total_amount", 0)




            # 1️⃣ Go to login page first
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")

            # # 2️⃣ Wait up to 30 seconds to see if we are auto-logged in
            # try:
            #     await page.wait_for_function(
            #         f"window.location.href === '{HOME_URL}'",
            #         timeout=10000  # 30 seconds
            #     )
            #     print("✅ Already logged in!")
            #     # proceed to logout first
         
            # except:
            #     print("⏳ Still on login page, need to check login form...")


            await page.wait_for_selector("input[name='email']", timeout=20000)
            print("🔑 Login form is present. Proceed with login.")
            # 👉 Perform login steps here if you have credentials
            await page.fill("input[name='email']", EMAIL)
            await page.fill("input[name='password']", PASSWORD)
            await page.click("button[type='submit']")

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
            has_record = await check_client_record(page, client["full_name"])
            print("Record exists:", has_record)


            if not has_record:
                # wait a bit for the search to process
                await page.wait_for_timeout(5000)
                has_record = await create_client_record(page, client)
                print("Rechecked record exists:", has_record)

            # if name found, verify email and phone matches
            if has_record:
                first_record = await get_first_client_record(page, client["full_name"])
                if first_record:
                    client_name = first_record["name"].lower()
                    client_email = first_record["email"].lower()
                    client_phone = (first_record["phone"][2:] if first_record["phone"].startswith("+1") else first_record["phone"]).replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

                    print("First record:", first_record)

                    # Compare with sale_data customer info
                    
                    sale_name = client["full_name"].lower()
                    sale_email = client["email"].lower()
                    sale_phone = (client["phone"][2:] if client["phone"].startswith("+1") else client["phone"]).replace("-", "").replace("(", "").replace(")", "").replace(" ", "")

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
                        print("Typing product name...", title)
                        await container.type(title)

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
    except Exception as e:
        sheet.update_cell(payload["row_index"], 16, "failed")  # (row, column, value)
        # update row - failed


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

        # Customer details
        contact_id = payload.get("contact_id", "")
        first_name = payload.get("first_name", "")
        last_name = payload.get("last_name", "")
        full_name = payload.get("full_name", "")
        email = payload.get("email", "")
        phone = payload.get("phone", "")
        tags = payload.get("tags", [])
        address1 = payload.get("address1", "")
        city = payload.get("city", "")
        state = payload.get("state", "")
        country = payload.get("country", "")
        postal_code = payload.get("postal_code", "")
        full_address = payload.get("full_address", "")

        # Payment details
        payment = payload.get("payment", {})
        transaction_id = payment.get("transaction_id", "")
        source = payment.get("source", "")
        payment_status = payment.get("payment_status", "")
        line_items = payment.get("line_items", [])
        title = ", ".join([item.get("title", "") for item in line_items])
        sub_total_amount = payment.get("sub_total_amount", 0)
        discount_amount = payment.get("discount_amount", 0)
        tax_amount = payment.get("tax_amount", 0)
        total_amount = payment.get("total_amount", 0)
        method = payment.get("method", "")
        gateway = payment.get("gateway", "")
        card = payment.get("card", {})
        card_brand = card.get("brand", "")
        card_last4 = card.get("last4", "")
        currency_symbol = payment.get("currency_symbol", "")
        currency_code = payment.get("currency_code", "")
        created_at = payment.get("created_at", "")
        created_on = payment.get("created_on", "")
        miscellaneous_charges = payment.get("miscellaneous_charges", 0)

        # create variable current datetime string
        date_str = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_values = [contact_id, first_name, email, phone, full_address, transaction_id, payment_status, title, sub_total_amount, total_amount, gateway, card_brand, card_last4, currency_code, created_on, "pending", date_str]
        sheet.append_row(row_values)
        # gspread append_row returns nothing, but you can calculate row index:
        row_index = len(sheet.get_all_values())  # last row index
        print(f"Inserted row {row_index} with pending status.")
        payload["row_index"] = row_index
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
    payload = sample_order

    # Customer details
    contact_id = payload.get("contact_id", "")
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    full_name = payload.get("full_name", "")
    email = payload.get("email", "")
    phone = payload.get("phone", "")
    tags = payload.get("tags", [])
    address1 = payload.get("address1", "")
    city = payload.get("city", "")
    state = payload.get("state", "")
    country = payload.get("country", "")
    postal_code = payload.get("postal_code", "")
    full_address = payload.get("full_address", "")

    # Payment details
    payment = payload.get("payment", {})
    transaction_id = payment.get("transaction_id", "")
    source = payment.get("source", "")
    payment_status = payment.get("payment_status", "")
    line_items = payment.get("line_items", [])
    title = ", ".join([item.get("title", "") for item in line_items])
    sub_total_amount = payment.get("sub_total_amount", 0)
    discount_amount = payment.get("discount_amount", 0)
    tax_amount = payment.get("tax_amount", 0)
    total_amount = payment.get("total_amount", 0)
    method = payment.get("method", "")
    gateway = payment.get("gateway", "")
    card = payment.get("card", {})
    card_brand = card.get("brand", "")
    card_last4 = card.get("last4", "")
    currency_symbol = payment.get("currency_symbol", "")
    currency_code = payment.get("currency_code", "")
    created_at = payment.get("created_at", "")
    created_on = payment.get("created_on", "")
    miscellaneous_charges = payment.get("miscellaneous_charges", 0)

    # create variable current datetime string
    date_str = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_values = [contact_id, first_name, email, phone, full_address, transaction_id, payment_status, title, sub_total_amount, total_amount, gateway, card_brand, card_last4, currency_code, created_on, "pending", date_str]
    sheet.append_row(row_values)
    # gspread append_row returns nothing, but you can calculate row index:
    row_index = len(sheet.get_all_values())  # last row index
    print(f"Inserted row {row_index} with pending status.")
    #return {"status": "done"}
    payload["row_index"] = row_index


    """
    GHL will POST here when an order is completed.

    """
    print("Background task started...")
    await run_playwright(payload)
    # Immediately return 200 to GHL, run automation in background
    return {"status": "done"}


# @app.post("/run")
# async def run_task():
#     if not EMAIL or not PASSWORD:
#         raise HTTPException(status_code=500, detail="Credentials not set in environment.")
#     await run_playwright()
#     return {"status": "Automation completed"}
