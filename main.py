import asyncio
import os
import time
from playwright.async_api import async_playwright
import telebot

BOT_TOKEN = '8407490230:AAHjhQCu-k7Y6VcvzWKyQiNXnOUJabQgmVg'
ADMIN_ID = 6843321125
bot = telebot.TeleBot(BOT_TOKEN)

CARD_NUMBER = "4059986126444431"
CARD_EXPIRY = "11/30"
CARD_CVC = "947"

CUSTOMER = {
    "email": "wafabro6576@gmail.com",
    "first_name": "Wafa",
    "last_name": "Bro",
    "address": "Hillside, West Coker Road",
    "city": "West Coker",
    "postcode": "BA22 9AA",
    "phone": "20177748870",
}

# المنتج الجديد
PRODUCT_NAME = "Black Rubber Ferrule for Seat Sticks"


def send_log(msg):
    print(msg)
    try:
        bot.send_message(ADMIN_ID, f"🤖 <b>Log:</b>\n<code>{msg}</code>", parse_mode='HTML')
    except Exception as e:
        print(f"Telegram error: {e}")


async def accept_cookies(page):
    for sel in ['button:has-text("Accept All")', '#onetrust-accept-btn-handler',
                'button:has-text("Essential Only")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(800)
                return True
        except Exception:
            pass
    return False


async def wait_for_any(page, selectors, timeout=8000):
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    return loc
            except Exception:
                pass
        await page.wait_for_timeout(300)
    return None


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            viewport={"width": 412, "height": 915},
        )
        page = await context.new_page()

        try:
            send_log("🔍 Searching for product...")
            await page.goto("https://www.stickandcaneshop.co.uk/",
                            wait_until="domcontentloaded", timeout=30000)
            await accept_cookies(page)

            search_input = page.locator('input[name="for"]').first
            await search_input.fill("Black Rubber Ferrule")
            await search_input.press("Enter")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)

            send_log("🛒 Opening product page...")
            product_link = page.locator(
                f'a:has-text("Black Rubber Ferrule")'
            ).first
            if await product_link.is_visible():
                await product_link.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)
            else:
                raise Exception("Product link not found")

            send_log("➕ Adding product to basket...")
            await accept_cookies(page)
            add_to_cart_btn = page.locator(
                'button:has-text("Add to Bag"), button:has-text("Add to Basket"), '
                'button:has-text("Add to Cart"), input[value*="Add to Basket"], '
                '.add-to-basket, .add-to-cart'
            ).first
            await add_to_cart_btn.click()
            await page.wait_for_timeout(2000)

            send_log("🛒 Going to basket...")
            await page.goto("https://www.stickandcaneshop.co.uk/basket",
                            wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            send_log("👉 Clicking Checkout...")
            checkout_btn = page.locator(
                'a:has-text("Checkout"), button:has-text("Checkout"), '
                'input[value*="Checkout"], .checkout-button, #checkout'
            ).first
            if await checkout_btn.is_visible():
                await checkout_btn.click()
            else:
                send_log("⚠️ Checkout button not found, trying direct URL...")
                await page.goto("https://www.stickandcaneshop.co.uk/checkout",
                                wait_until="domcontentloaded", timeout=30000)

            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            await accept_cookies(page)

            send_log("👤 Selecting 'New Customer'...")
            try:
                await page.locator('label:has-text("I am a new customer")').first.click()
                await page.wait_for_timeout(1200)
            except Exception as e:
                send_log(f"⚠️ radio click issue: {e}")

            send_log("📧 Waiting for email input...")
            email_locator = await wait_for_any(
                page,
                ['input[name="email"]', 'input[type="email"]', 'input[name="billing_email"]'],
                timeout=10000,
            )
            if not email_locator:
                await page.screenshot(path="no_email.png", full_page=True)
                with open("no_email.png", 'rb') as photo:
                    bot.send_photo(ADMIN_ID, photo, caption="🚨 حقل الإيميل مش ظهر")
                os.remove("no_email.png")
                raise Exception("Email input not found")

            await email_locator.fill(CUSTOMER["email"])
            send_log("✅ Email filled.")
            await page.wait_for_timeout(1000)

            send_log("🚶 Choosing 'Checkout as a Guest'...")
            guest_btn = await wait_for_any(
                page,
                ['button:has-text("Checkout as a Guest")',
                 'a:has-text("Checkout as a Guest")',
                 'input[value*="Guest"]',
                 'button:has-text("Guest")'],
                timeout=8000,
            )
            if guest_btn:
                await guest_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(4000)  # زيادة الانتظار
                send_log("✅ Guest checkout selected.")
            else:
                raise Exception("Guest button not found")

            # 10. ملء فورم الشحن - مع انتظار أطول
            send_log("📝 Filling customer info...")
            await page.wait_for_timeout(3000)  # انتظار إضافي

            first_name_input = page.locator(
                'input[name="first_name"], input[name="billing_first_name"]'
            ).first
            if not await first_name_input.is_visible(timeout=10000):  # زيادة المهلة
                await page.screenshot(path="no_form.png", full_page=True)
                with open("no_form.png", 'rb') as photo:
                    bot.send_photo(ADMIN_ID, photo, caption="🚨 فورم الشحن مش ظهر")
                os.remove("no_form.png")
                raise Exception("Shipping form not found")

            await first_name_input.fill(CUSTOMER["first_name"])
            await page.locator(
                'input[name="last_name"], input[name="billing_last_name"]'
            ).first.fill(CUSTOMER["last_name"])
            await page.locator(
                'input[name="address1"], input[name="billing_address1"], input[name="address"]'
            ).first.fill(CUSTOMER["address"])
            await page.locator(
                'input[name="city"], input[name="billing_city"]'
            ).first.fill(CUSTOMER["city"])
            await page.locator(
                'input[name="postcode"], input[name="billing_postcode"], input[name="zip"]'
            ).first.fill(CUSTOMER["postcode"])
            await page.locator(
                'input[name="phone"], input[name="telephone"], input[name="billing_phone"]'
            ).first.fill(CUSTOMER["phone"])
            send_log("✅ Customer form filled.")

            # 11. Submit & Continue
            send_log("➡️ Submitting form...")
            submit_btn = page.locator(
                'button:has-text("Submit & Continue"), button:has-text("Continue"), '
                'input[value*="Submit"]'
            ).first
            if await submit_btn.is_visible(timeout=2000):
                await submit_btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(3000)

            # 12. اختيار الفيزا
            send_log("💳 Selecting Credit/Debit Card...")
            card_label = await wait_for_any(
                page,
                ['label:has-text("Credit / Debit Card")',
                 'label:has-text("Credit/Debit Card")',
                 'label:has-text("Card")'],
                timeout=10000,
            )
            if not card_label:
                await page.screenshot(path="no_card.png", full_page=True)
                with open("no_card.png", 'rb') as photo:
                    bot.send_photo(ADMIN_ID, photo, caption="🚨 صفحة الدفع مش ظهر")
                os.remove("no_card.png")
                raise Exception("Card payment option not found")

            await card_label.click()
            await page.wait_for_timeout(1500)

            # 13. ملء الكارت
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
            if await accept_checkbox.is_visible(timeout=2000):
                await accept_checkbox.check()

            send_log("🚀 Clicking 'Complete Purchase'...")
            await page.locator('#input_submit').click()
            await page.wait_for_timeout(10000)

            page_text = await page.inner_text("body")
            if "Transaction Not Allowed" in page_text:
                send_log("❌ Result: Transaction Not Allowed")
            elif "Purchase Unsuccessful" in page_text:
                send_log("❌ Result: Purchase Unsuccessful")
            elif "Unfortunately your purchase has not been successfully approved" in page_text:
                send_log("❌ Result: Not Approved")
            elif "Order Complete" in page_text or "Thank you" in page_text:
                send_log("✅ Result: Order Complete!")
            else:
                send_log("⚠️ Unknown response. Check screenshot.")

            screenshot_path = "result_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            with open(screenshot_path, 'rb') as photo:
                bot.send_photo(ADMIN_ID, photo, caption="📸 Final Result")
            os.remove(screenshot_path)

        except Exception as e:
            send_log(f"❌ CRITICAL ERROR: {str(e)}")
            try:
                await page.screenshot(path="error_screenshot.png", full_page=True)
                with open("error_screenshot.png", 'rb') as photo:
                    bot.send_photo(ADMIN_ID, photo, caption="🚨 Error Screenshot")
                os.remove("error_screenshot.png")
            except Exception as ss_error:
                send_log(f"Screenshot failed: {ss_error}")
        finally:
            await browser.close()


if __name__ == "__main__":
    send_log("🚀 Bot started.")
    while True:
        try:
            asyncio.run(main())
            send_log("✅ Completed.")
            time.sleep(30)
        except Exception as e:
            send_log(f"❌ Crashed: {e}")
            time.sleep(10)
