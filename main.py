import asyncio
import os
from playwright.async_api import async_playwright
import telebot

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN = '8407490230:AAHjhQCu-k7Y6VcvzWKyQiNXnOUJabQgmVg'
ADMIN_ID = 6843321125
bot = telebot.TeleBot(BOT_TOKEN)

CARD_NUMBER = "4059986126444431"
CARD_EXPIRY = "11/30"
CARD_CVC = "947"

# رابط المنتج
PRODUCT_URL = "https://www.stickandcaneshop.co.uk/small-replacement-rubber-tip-for-veritas-ferrule/"

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
# MAIN
# ═══════════════════════════════════════════════════════════════════

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            viewport={"width": 412, "height": 915},
        )
        page = await context.new_page()

        try:
            # 1. افتح المنتج وأضفه للسلة
            send_log("🌐 Opening product page...")
            await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=30000)
            
            send_log("🛒 Adding product to basket...")
            # دور على زرار الإضافة للسلة
            add_to_cart_btn = page.locator('button:has-text("Add to Basket"), button:has-text("Add to Cart"), input[value*="Add to Basket"], input[value*="Add to Cart"]').first
            await add_to_cart_btn.click()
            await page.wait_for_timeout(1500)

            # 2. روح للسلة واضغط Checkout
            send_log("🛒 Going to Basket...")
            await page.goto("https://www.stickandcaneshop.co.uk/basket", wait_until="domcontentloaded", timeout=30000)
            
            send_log("👉 Clicking Checkout...")
            checkout_btn = page.locator('a:has-text("Checkout"), button:has-text("Checkout"), input[value*="Checkout"]').first
            await checkout_btn.click()
            
            # استنى صفحة الدفع تحمل
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)

            # 3. اختيار الفيزا
            send_log("💳 Selecting Credit/Debit Card...")
            await page.locator('label:has-text("Credit / Debit Card")').click()
            await page.wait_for_timeout(1000)

            # 4. ملء الكارت
            send_log("🔢 Filling card number...")
            frame_number = page.frame_locator('iframe[name="braintree-hosted-field-number"]')
            await frame_number.locator('input').press_sequentially(CARD_NUMBER, delay=20)

            send_log("📅 Filling expiry date...")
            frame_exp = page.frame_locator('iframe[name="braintree-hosted-field-expirationDate"]')
            await frame_exp.locator('input').press_sequentially(CARD_EXPIRY, delay=20)

            send_log("🔒 Filling CVV...")
            frame_cvv = page.frame_locator('iframe[name="braintree-hosted-field-cvv"]')
            await frame_cvv.locator('input').press_sequentially(CARD_CVC, delay=20)

            # 5. الموافقة على الشروط
            send_log("✅ Checking Terms & Conditions...")
            await page.locator('input[name="accept"]').check()

            # 6. اضغط على الدفع
            send_log("🚀 Clicking 'Complete Purchase'...")
            await page.locator('#input_submit').click()

            # 7. استنى الرد
            send_log("⏳ Waiting for final response...")
            await page.wait_for_timeout(10000)

            # 8. النتيجة
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

            # 9. اسكرين شوت
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

if __name__ == "__main__":
    asyncio.run(main())
