import asyncio
import os
import time
from playwright.async_api import async_playwright
import telebot

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN = '8407490230:AAHjhQCu-k7Y6VcvzWKyQiNXnOUJabQgmVg'
ADMIN_ID = 6843321125
bot = telebot.TeleBot(BOT_TOKEN)

# بيانات الكارت
CARD_NUMBER = "4059986126444431"
CARD_EXPIRY = "11/30"
CARD_CVC = "947"

# بيانات العميل
CUSTOMER = {
    "email": "wafabro6576@gmail.com",
    "first_name": "Wafa",
    "last_name": "Bro",
    "address": "Hillside, West Coker Road",
    "city": "West Coker",
    "postcode": "BA22 9AA",
    "phone": "20177748870",
}

PRODUCT_CODE = "VER001071" 

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

def send_log(msg):
    print(msg)
    try:
        bot.send_message(ADMIN_ID, f"🤖 <b>Log:</b>\n<code>{msg}</code>", parse_mode='HTML')
    except Exception as e:
        print(f"Telegram error: {e}")

# ═══════════════════════════════════════════════════════════════════
# MAIN SCRIPT
# ═══════════════════════════════════════════════════════════════════

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            viewport={"width": 412, "height": 915},
        )
        page = await context.new_page()

        try:
            # 1. البحث عن المنتج
            send_log("🔍 Searching for product...")
            await page.goto("https://www.stickandcaneshop.co.uk/", wait_until="domcontentloaded", timeout=30000)
            
            search_input = page.locator('input[name="for"]').first
            await search_input.fill(PRODUCT_CODE)
            await search_input.press("Enter")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)

            # 2. الضغط على المنتج
            send_log("🛒 Opening product page...")
            product_link = page.locator(f'a:has-text("{PRODUCT_CODE}"), a:has-text("Rubber Tip")').first
            if await product_link.is_visible():
                await product_link.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)
            else:
                raise Exception("Product link not found")

            # 3. إضافة المنتج للسلة
            send_log("➕ Adding product to basket...")
            
            # تخطي الكوكيز
            try:
                cookie_btn = page.locator('button:has-text("Accept All")').first
                if await cookie_btn.is_visible(timeout=3000):
                    await cookie_btn.click()
                    send_log("🍪 Cookies accepted.")
                    await page.wait_for_timeout(1000)
            except: pass

            add_to_cart_btn = page.locator('button:has-text("Add to Bag"), button:has-text("Add to Basket"), button:has-text("Add to Cart"), input[value*="Add to Basket"], .add-to-basket, .add-to-cart').first
            await add_to_cart_btn.click()
            await page.wait_for_timeout(2000)

            # 4. الذهاب للسلة
            send_log("🛒 Going to basket...")
            await page.goto("https://www.stickandcaneshop.co.uk/basket", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # 5. الضغط على Checkout
            send_log("👉 Clicking Checkout...")
            checkout_btn = page.locator('a:has-text("Checkout"), button:has-text("Checkout"), input[value*="Checkout"], .checkout-button, #checkout').first
            if await checkout_btn.is_visible():
                await checkout_btn.click()
            else:
                send_log("⚠️ Checkout button not found, trying direct URL...")
                await page.goto("https://www.stickandcaneshop.co.uk/checkout", wait_until="domcontentloaded", timeout=30000)

            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)

            # 6. الموافقة على الكوكيز (مهم جداً هنا)
            send_log("🍪 Accepting cookies on checkout page...")
            try:
                cookie_btn = page.locator('button:has-text("Accept All")').first
                if await cookie_btn.is_visible(timeout=3000):
                    await cookie_btn.click()
                    send_log("✅ Cookies accepted on checkout.")
                    await page.wait_for_timeout(1000)
            except: pass

            # 7. اختيار "I am a new customer" و الضغط على Continue
            send_log("👤 Selecting 'New Customer'...")
            try:
                # بنجرب نختار الـ radio بتاع "I am a new customer"
                new_customer_radio = page.locator('input[type="radio"][value*="new"], label:has-text("I am a new customer")').first
                if await new_customer_radio.is_visible(timeout=3000):
                    await new_customer_radio.click()
                    send_log("✅ New customer selected.")
                    await page.wait_for_timeout(1000)
                
                # بنضغط على زرار Continue أو Proceed
                continue_btn = page.locator('button:has-text("Continue"), input[value*="Continue"], button:has-text("Proceed"), input[value*="Proceed"]').first
                if await continue_btn.is_visible(timeout=3000):
                    await continue_btn.click()
                    send_log("✅ Clicked Continue.")
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(2000)
            except Exception as e:
                send_log(f"⚠️ Could not handle customer step: {e}")

            # 8. ملء فورم البيانات (لو ظهر)
            send_log("📝 Filling customer info...")
            
            email_input = page.locator('input[name="email"], input[type="email"]').first
            if await email_input.is_visible(timeout=2000):
                await email_input.fill(CUSTOMER["email"])
                send_log("✅ Email filled.")

            first_name_input = page.locator('input[name="first_name"], input[name="billing_first_name"]').first
            if await first_name_input.is_visible(timeout=2000):
                await first_name_input.fill(CUSTOMER["first_name"])
                send_log("✅ First name filled.")

            last_name_input = page.locator('input[name="last_name"], input[name="billing_last_name"]').first
            if await last_name_input.is_visible(timeout=2000):
                await last_name_input.fill(CUSTOMER["last_name"])
                send_log("✅ Last name filled.")

            address_input = page.locator('input[name="address1"], input[name="billing_address1"], input[name="address"]').first
            if await address_input.is_visible(timeout=2000):
                await address_input.fill(CUSTOMER["address"])
                send_log("✅ Address filled.")

            city_input = page.locator('input[name="city"], input[name="billing_city"]').first
            if await city_input.is_visible(timeout=2000):
                await city_input.fill(CUSTOMER["city"])
                send_log("✅ City filled.")

            postcode_input = page.locator('input[name="postcode"], input[name="billing_postcode"], input[name="zip"]').first
            if await postcode_input.is_visible(timeout=2000):
                await postcode_input.fill(CUSTOMER["postcode"])
                send_log("✅ Postcode filled.")

            phone_input = page.locator('input[name="phone"], input[name="telephone"], input[name="billing_phone"]').first
            if await phone_input.is_visible(timeout=2000):
                await phone_input.fill(CUSTOMER["phone"])
                send_log("✅ Phone filled.")

            # 9. الضغط على Submit & Continue (لو ظهر)
            send_log("➡️ Clicking Submit & Continue...")
            submit_btn = page.locator('button:has-text("Submit & Continue"), button:has-text("Continue"), input[value*="Submit"]').first
            if await submit_btn.is_visible(timeout=2000):
                await submit_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)

            # 10. اختيار الفيزا
            send_log("💳 Selecting Credit/Debit Card...")
            await page.locator('label:has-text("Credit / Debit Card")').click()
            await page.wait_for_timeout(1500)

            # 11. ملء الكارت
            send_log("🔢 Filling card number...")
            frame_number = page.frame_locator('iframe[name="braintree-hosted-field-number"]')
            await frame_number.locator('input').press_sequentially(CARD_NUMBER, delay=20)

            send_log("📅 Filling expiry date...")
            frame_exp = page.frame_locator('iframe[name="braintree-hosted-field-expirationDate"]')
            await frame_exp.locator('input').press_sequentially(CARD_EXPIRY, delay=20)

            send_log("🔒 Filling CVV...")
            frame_cvv = page.frame_locator('iframe[name="braintree-hosted-field-cvv"]')
            await frame_cvv.locator('input').press_sequentially(CARD_CVC, delay=20)

            # 12. الموافقة على الشروط
            send_log("✅ Checking Terms & Conditions...")
            accept_checkbox = page.locator('input[name="accept"]')
            if await accept_checkbox.is_visible(timeout=2000):
                await accept_checkbox.check()
                send_log("✅ Terms accepted.")

            # 13. الضغط على Complete Purchase
            send_log("🚀 Clicking 'Complete Purchase'...")
            await page.locator('#input_submit').click()

            # 14. استنى الرد
            send_log("⏳ Waiting for final response...")
            await page.wait_for_timeout(10000)

            # 15. استخراج النتيجة
            page_text = await page.inner_text("body")
            if "Transaction Not Allowed" in page_text:
                send_log("❌ Result: Transaction Not Allowed")
            elif "Purchase Unsuccessful" in page_text:
                send_log("❌ Result: Purchase Unsuccessful")
            elif "Unfortunately your purchase has not been successfully approved" in page_text:
                send_log("❌ Result: Purchase Unsuccessful (Not Approved)")
            elif "Order Complete" in page_text or "Thank you" in page_text:
                send_log("✅ Result: Order Complete / Charge Successful!")
            else:
                send_log("⚠️ Unknown response. Check screenshot.")

            # 16. اسكرين شوت
            screenshot_path = "result_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            with open(screenshot_path, 'rb') as photo:
                bot.send_photo(ADMIN_ID, photo, caption="📸 Final Result Screenshot")
            send_log("📸 Screenshot sent.")
            os.remove(screenshot_path)

        except Exception as e:
            error_msg = f"❌ CRITICAL ERROR: {str(e)}"
            send_log(error_msg)
            try:
                error_screenshot = "error_screenshot.png"
                await page.screenshot(path=error_screenshot, full_page=True)
                with open(error_screenshot, 'rb') as photo:
                    bot.send_photo(ADMIN_ID, photo, caption="🚨 Error Screenshot")
                os.remove(error_screenshot)
            except Exception as ss_error:
                send_log(f"Failed to capture error screenshot: {ss_error}")

        finally:
            await browser.close()

# ═══════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    send_log("🚀 Bot started. Waiting for errors...")
    while True:
        try:
            asyncio.run(main())
            send_log("✅ Process completed successfully.")
            time.sleep(30) 
        except Exception as e:
            send_log(f"❌ Process crashed: {e}")
            time.sleep(10)
