import asyncio
import os
import time
import random
from playwright.async_api import async_playwright
import telebot

# ═══════════════════════════════════════════════════════════════════
# CONFIG — غير التوكن هنا
# ═══════════════════════════════════════════════════════════════════

# ⚠️ غير التوكن ده بتوكن جديد من BotFather
BOT_TOKEN = '8407490230:AAF3AXyYqAdkVg34orbBVj2NvCuOhKTPfk0'
ADMIN_ID = 6843321125
bot = telebot.TeleBot(BOT_TOKEN)

CARD_NUMBER = "4059986126444431"
CARD_EXPIRY = "11/30"
CARD_CVC = "947"

PRODUCT_URL = "https://www.stickandcaneshop.co.uk/black-rubber-ferrule-for-seat-sticks"

REAL_NAMES = ["ahmed", "mohamed", "mahmoud", "mustafa", "khaled", "omar", "youssef",
              "karim", "hassan", "tarek", "wafa", "sara", "laila", "nour", "mona",
              "heba", "dina", "aya", "mariam", "salma", "john", "james", "david",
              "michael", "robert", "william", "thomas", "daniel", "matthew", "joseph"]

LAST_NAMES = ["Ali", "Hassan", "Ibrahim", "Mostafa", "Mahmoud", "Salem", "Farag", "Smith", "Johnson", "Brown", "Davis", "Miller"]

def generate_email():
    first = random.choice(REAL_NAMES).capitalize()
    last = random.choice(LAST_NAMES).capitalize()
    number = random.randint(100, 9999)
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    return f"{first}.{last}.{number}@{random.choice(domains)}"

CUSTOMER = {
    "email": "",
    "first_name": random.choice(["Ahmed", "Mohamed", "Mahmoud", "Wafa", "Sara", "Laila", "Omar", "Khaled"]),
    "last_name": random.choice(LAST_NAMES),
    "address": "Hillside, West Coker Road",
    "city": "West Coker",
    "postcode": "BA22 9AA",
    "phone": "20177748870",
}

def send_log(msg):
    print(msg)

def send_telegram(msg):
    try:
        bot.send_message(ADMIN_ID, msg, parse_mode='HTML')
        time.sleep(2)
    except Exception as e:
        print(f"Telegram error: {e}")

async def safe_screenshot(page, path, caption=""):
    try:
        await page.screenshot(path=path, full_page=False)
        if os.path.getsize(path) > 5 * 1024 * 1024:
            from PIL import Image
            img = Image.open(path)
            img.thumbnail((1280, 1280))
            img.save(path)
        with open(path, 'rb') as photo:
            bot.send_photo(ADMIN_ID, photo, caption=caption)
        os.remove(path)
    except Exception as e:
        print(f"⚠️ Screenshot failed: {e}")
        try:
            os.remove(path)
        except:
            pass

async def accept_cookies(page):
    selectors = [
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
        '#onetrust-accept-btn-handler',
        'button:has-text("Essential Only")',
        '.cc-btn.cc-allow',
        '#ccc-notify-accept',
        '.cookie-accept',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible(timeout=2000):
                await btn.click(force=True)
                await page.wait_for_timeout(800)
                return True
        except Exception:
            pass
    try:
        await page.evaluate("""
            const banners = document.querySelectorAll('#onetrust-consent-sdk, .cookie-banner, #cookie-banner, .cc-window, .cookie-notice, [class*="cookie"]');
            banners.forEach(b => b.remove());
        """)
        return True
    except:
        return False

async def wait_for_any(page, selectors, timeout=8000):
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    return loc
            except Exception:
                pass
        await page.wait_for_timeout(300)
    return None

async def try_guest_checkout(page, email_locator, guest_btn):
    for attempt in range(6):
        email = generate_email()
        CUSTOMER["email"] = email
        send_log(f"📧 Trying email: {email} (attempt {attempt+1})")

        await email_locator.fill("", force=True)
        await email_locator.fill(email, force=True)
        
        # نضغط على "Checkout as a Guest" بطريقة JavaScript
        send_log("🖱️ Clicking 'Checkout as a Guest' via JS...")
        try:
            await page.evaluate("""
                const btn = document.querySelector('button:has-text("Checkout as a Guest"), a:has-text("Checkout as a Guest"), input[value*="Guest"]');
                if (btn) btn.click();
            """)
        except:
            await guest_btn.click(force=True)
        
        # نستنى لحد ما الصفحة تتغير (حد أقصى 20 ثانية)
        try:
            await page.wait_for_selector('input[name="first_name"], input[name="billing_first_name"], input[name="firstName"]', timeout=20000)
            send_log(f"✅ Shipping form appeared after email: {email}")
            return email
        except:
            # لو مفيش فورم شحن، يمكن ظهرت رسالة خطأ
            error_popup = page.locator('text="Please check the email address"')
            if await error_popup.count() > 0 and await error_popup.first.is_visible():
                send_log(f"⚠️ Email rejected: {email}")
                ok_btn = page.locator('button:has-text("OK"), .modal button, .popup button').first
                if await ok_btn.count() > 0:
                    await ok_btn.click(force=True)
                    await page.wait_for_timeout(1000)
                email_locator = await wait_for_any(
                    page,
                    ['input[name="email"]', 'input[type="email"]', 'input[name="billing_email"]'],
                    timeout=5000,
                )
                if not email_locator:
                    raise Exception("Email field disappeared after popup")
                continue
            else:
                await safe_screenshot(page, "guest_error.png", "🚨 فورم الشحن مش ظهر بعد Guest")
                raise Exception("Shipping form did not appear")

    raise Exception("All email attempts failed")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        try:
            send_log("🔗 Opening product page...")
            await page.goto(PRODUCT_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)
            await accept_cookies(page)

            send_log("➕ Adding product to basket...")
            add_to_cart_btn = page.locator(
                'button:has-text("Add to Bag"), button:has-text("Add to Basket"), '
                'button:has-text("Add to Cart"), input[value*="Add to Basket"], '
                '.add-to-basket, .add-to-cart'
            ).first
            if not await add_to_cart_btn.is_visible(timeout=5000):
                raise Exception("Add to cart button not found")

            await add_to_cart_btn.click()
            await page.wait_for_timeout(3000)

            send_log("🛒 Going to basket...")
            await page.goto("https://www.stickandcaneshop.co.uk/basket",
                            wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)
            await accept_cookies(page)

            send_log("👉 Clicking Checkout...")
            checkout_btn = page.locator(
                'a:has-text("Checkout"), button:has-text("Checkout"), '
                'input[value*="Checkout"], .checkout-button, #checkout'
            ).first
            if await checkout_btn.is_visible(timeout=3000):
                await checkout_btn.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
            else:
                send_log("⚠️ Checkout button not found, trying direct URL...")
                await page.goto("https://www.stickandcaneshop.co.uk/checkout",
                                wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

            await accept_cookies(page)

            send_log("👤 Selecting 'New Customer'...")
            try:
                await page.locator('label:has-text("I am a new customer")').first.click(force=True)
                await page.wait_for_timeout(2000)
            except Exception as e:
                send_log(f"⚠️ radio click issue: {e}")

            send_log("📧 Waiting for email input...")
            email_locator = await wait_for_any(
                page,
                ['input[name="email"]', 'input[type="email"]', 'input[name="billing_email"]'],
                timeout=10000,
            )
            if not email_locator:
                raise Exception("Email input not found")

            send_log("🚶 Choosing 'Checkout as a Guest'...")
            guest_btn = await wait_for_any(
                page,
                ['button:has-text("Checkout as a Guest")',
                 'a:has-text("Checkout as a Guest")',
                 'input[value*="Guest"]',
                 'button:has-text("Guest")'],
                timeout=8000,
            )
            if not guest_btn:
                raise Exception("Guest button not found")

            successful_email = await try_guest_checkout(page, email_locator, guest_btn)
            send_log(f"✅ Guest checkout successful with: {successful_email}")

            send_log("📝 Filling customer info...")
            
            await page.wait_for_timeout(2000)

            first_name_loc = page.locator(
                'input[name="first_name"], input[name="billing_first_name"], input[name="firstName"]'
            ).first
            if not await first_name_loc.count() > 0:
                await safe_screenshot(page, "no_form.png", "🚨 فورم الشحن مش ظهر بعد الانتظار")
                raise Exception("Shipping form not found after wait")

            await first_name_loc.fill(CUSTOMER["first_name"], force=True)
            await page.locator('input[name="last_name"], input[name="billing_last_name"], input[name="lastName"]').first.fill(CUSTOMER["last_name"], force=True)
            await page.locator('input[name="address1"], input[name="billing_address1"], input[name="address"], input[name="addressLine1"]').first.fill(CUSTOMER["address"], force=True)
            await page.locator('input[name="city"], input[name="billing_city"], input[name="townCity"]').first.fill(CUSTOMER["city"], force=True)
            await page.locator('input[name="postcode"], input[name="billing_postcode"], input[name="zip"]').first.fill(CUSTOMER["postcode"], force=True)
            await page.locator('input[name="phone"], input[name="telephone"], input[name="billing_phone"], input[name="phoneNumber"]').first.fill(CUSTOMER["phone"], force=True)
            
            country_select = page.locator('select[name="country"], select[name="billing_country"]').first
            if await country_select.count() > 0:
                try:
                    await country_select.select_option(label="United Kingdom")
                except:
                    pass

            send_log("✅ Customer form filled.")

            send_log("➡️ Submitting form...")
            submit_btn = page.locator(
                'button:has-text("Submit & Continue"), button:has-text("Continue"), '
                'input[value*="Submit"], button[type="submit"]'
            ).first
            if await submit_btn.count() > 0:
                await submit_btn.click(force=True)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(5000)

            send_log("💳 Selecting Credit/Debit Card...")
            card_label = await wait_for_any(
                page,
                ['label:has-text("Credit / Debit Card")',
                 'label:has-text("Credit/Debit Card")',
                 'label:has-text("Card")',
                 'input[value*="card"]'],
                timeout=10000,
            )
            if not card_label:
                await safe_screenshot(page, "no_card.png", "🚨 صفحة الدفع مش ظهر")
                raise Exception("Card payment option not found")

            await card_label.click(force=True)
            await page.wait_for_timeout(2000)

            send_log("🔢 Filling card...")
            await page.frame_locator(
                'iframe[name="braintree-hosted-field-number"]'
            ).locator('input').press_sequentially(CARD_NUMBER, delay=20)
            await page.frame_locator(
                'iframe[name="braintree-hosted-field-expirationDate"]'
            ).locator('input').press_sequentially(CARD_EXPIRY, delay=20)
            await page.frame_locator(
                'iframe[name="braintree-hosted-field-cvv"]'
            ).locator('input').press_sequentially(CARD_CVC, delay=20)

            accept_checkbox = page.locator('input[name="accept"]')
            if await accept_checkbox.count() > 0:
                await accept_checkbox.check(force=True)

            send_log("🚀 Clicking 'Complete Purchase'...")
            await page.locator('#input_submit').click(force=True)
            await page.wait_for_timeout(10000)

            page_text = await page.inner_text("body")
            if "Transaction Not Allowed" in page_text:
                result = "❌ Transaction Not Allowed"
            elif "Purchase Unsuccessful" in page_text:
                result = "❌ Purchase Unsuccessful"
            elif "Unfortunately your purchase has not been successfully approved" in page_text:
                result = "❌ Not Approved"
            elif "Order Complete" in page_text or "Thank you" in page_text:
                result = "✅ Order Complete!"
            else:
                result = "⚠️ Unknown response"

            send_log(result)
            send_telegram(result)
            await safe_screenshot(page, "result_screenshot.png", result)

        except Exception as e:
            err = f"❌ CRITICAL ERROR: {str(e)}"
            send_log(err)
            send_telegram(err)
            await safe_screenshot(page, "error_screenshot.png", "🚨 Error Screenshot")
        finally:
            await browser.close()

if __name__ == "__main__":
    send_telegram("🚀 Bot started. Running process...")
    while True:
        try:
            asyncio.run(main())
            send_telegram("✅ Process completed.")
            time.sleep(30)
        except Exception as e:
            send_telegram(f"❌ Crashed: {e}")
            time.sleep(10)
