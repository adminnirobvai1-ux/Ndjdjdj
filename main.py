import os
import pty
import subprocess
import re
import time
import threading
from datetime import datetime, timedelta
import pytz
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# কনফিগারেশন
BOT_TOKEN = os.getenv("BOT_TOKEN", "8991156137:AAHW2Vk30vxB5WpmV1qXIXz5j2eG94VCXlI")
ADMIN_ID = 8707571669
ADMIN_USERNAME = "@DARK67HACK"
CHANNEL_URL = "https://t.me/DARK67HACK"
BKASH_NUMBER = "01870829343"
NAGAD_NUMBER = "01876685711"
PER_DAY_CUSTOM_PRICE = 40

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
BD_TZ = pytz.timezone("Asia/Dhaka")

# ডেটাবেস
users = {}
terminals = {}
pending_requests = {}
terminal_counter = 1
request_counter = 100
lock = threading.Lock()

# ম্যাথমেটিক্যাল বোল্ড রূপান্তরকারী
BOLD_MAP = {
    'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈',
    'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑',
    'S': '𝐒', 'T': '𝐓', 'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
    '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
}

def to_p_font(text):
    return "".join(BOLD_MAP.get(c, c) for c in str(text))

# প্যাকেজ তালিকা (মেয়াদ ও প্রাইস)
PACKAGES = {
    "pkg_7d": {"name": f"✦ {to_p_font('7 DAYS')}", "days": 7, "price": 75},
    "pkg_15d": {"name": f"✦ {to_p_font('15 DAYS')}", "days": 15, "price": 135},
    "pkg_1m": {"name": f"✦ {to_p_font('1 MONTH')}", "days": 30, "price": 250},
    "pkg_2m": {"name": f"✦ {to_p_font('2 MONTHS')}", "days": 60, "price": 480},
    "pkg_1y": {"name": f"✦ {to_p_font('1 YEAR')}", "days": 365, "price": 1500},
}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "balance": 0, 
            "referred_by": None, 
            "referrals": 0, 
            "active_vps": None,
            "state": None,
            "temp_pkg": None,
            "temp_method": None
        }
    return users[uid]

def spawn_sshx():
    try:
        master, slave = pty.openpty()
        env = os.environ.copy()
        env["SHELL"] = "/bin/bash"
        env["TERM"] = "xterm-256color"

        cmd = "curl -sSf https://sshx.io/get | sh -s run"
        proc = subprocess.Popen(
            ["bash", "-c", cmd],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
            preexec_fn=os.setsid,
            env=env
        )
        os.close(slave)
    except Exception as e:
        print(f"Spawn error: {e}")
        return None, None, None

    url = None
    buffer = ""
    start_time = time.time()

    while time.time() - start_time < 25:
        try:
            chunk = os.read(master, 1024).decode("utf-8", errors="ignore")
            if chunk:
                buffer += chunk
                match = re.search(r"https://sshx\.io/s/[A-Za-z0-9_-]+#[A-Za-z0-9_-]+", buffer)
                if not match:
                    match = re.search(r"https://sshx\.io/s/[^\s\x1b\r\n]+", buffer)
                if match:
                    url = match.group(0).strip()
                    break
        except Exception:
            break
        time.sleep(0.2)

    if not url:
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:
            pass
        try:
            os.close(master)
        except Exception:
            pass
        return None, None, None

    return proc, master, url

def kill_terminal(term_id):
    with lock:
        if term_id in terminals:
            info = terminals[term_id]
            try:
                os.killpg(os.getpgid(info["proc"].pid), 9)
            except Exception:
                pass
            try:
                os.close(info["master_fd"])
            except Exception:
                pass
            uid = info.get("user_id")
            if uid and uid in users:
                users[uid]["active_vps"] = None
            del terminals[term_id]
            return True
    return False

def schedule_auto_kill(term_id, delay_seconds, user_id, expire_label):
    def _runner():
        time.sleep(delay_seconds)
        if kill_terminal(term_id):
            try:
                msg = (
                    f"⩇⩇:⩇⩇ <b>{to_p_font('DURATION EXPIRED')}</b>\n\n"
                    f"✦ Your Terminal #{to_p_font(term_id)} has reached its limit ({to_p_font(expire_label)}) and was shut down."
                )
                bot.send_message(user_id, msg, parse_mode="HTML")
            except Exception:
                pass
    t = threading.Thread(target=_runner, daemon=True)
    t.start()

def create_and_send_vps(target_user_id, days):
    global terminal_counter
    proc, master_fd, url = spawn_sshx()
    if not url:
        bot.send_message(target_user_id, f"✦ <b>{to_p_font('DEPLOYMENT FAILED')}</b>\nদয়া করে ওনারের সাথে যোগাযোগ করুন।", parse_mode="HTML")
        return False

    delay_sec = days * 86400
    expire_dt = datetime.now(BD_TZ) + timedelta(days=days)
    expire_str = expire_dt.strftime("%d %b %Y, %I:%M %p")

    with lock:
        t_id = terminal_counter
        terminal_counter += 1
        terminals[t_id] = {
            "proc": proc,
            "master_fd": master_fd,
            "url": url,
            "user_id": target_user_id,
            "expire_at": expire_dt
        }
        users[target_user_id]["active_vps"] = t_id

    schedule_auto_kill(t_id, delay_sec, target_user_id, expire_str)

    msg = (
        f"✦ <b>{to_p_font('DEPLOYMENT SUCCESSFUL')}</b>\n\n"
        f"⛃ <b>{to_p_font('INSTANCE ID')}:</b> <code>{to_p_font(t_id)}</code>\n"
        f"⩇⩇:⩇⩇ <b>{to_p_font('EXPIRES ON')}:</b> {to_p_font(expire_str)}\n"
        f"𓊕 <b>{to_p_font('ACCESS')}:</b> {to_p_font('ROOT SHELL READY')}\n\n"
        f"নিচের বাটনে চাপ দিয়ে আপনার টার্মিনাল ওপেন করুন:"
    )

    markup = types.InlineKeyboardMarkup()
    btn_term = types.InlineKeyboardButton(f"✦ {to_p_font('LAUNCH TERMINAL')}", url=url)
    markup.add(btn_term)

    bot.send_message(target_user_id, msg, parse_mode="HTML", reply_markup=markup)
    return True

# নিচের কিবোর্ড মেনুবার (৪টি বাটন)
def main_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton(f"𔒝 {to_p_font('PROFILE')}")
    b2 = types.KeyboardButton(f"⛃ {to_p_font('BALANCE')}")
    b3 = types.KeyboardButton(f"♞ {to_p_font('REFERRAL')}")
    b4 = types.KeyboardButton(f"✦ {to_p_font('PLANS & PRICING')}")
    markup.add(b1, b2, b3, b4)
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = message.from_user.id
    u_data = get_user(uid)

    # রেফারেল ট্র্যাকিং
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        ref_id = int(parts[1])
        if ref_id != uid and u_data["referred_by"] is None:
            u_data["referred_by"] = ref_id
            ref_user = get_user(ref_id)
            ref_user["balance"] += 1
            ref_user["referrals"] += 1
            try:
                bot.send_message(
                    ref_id,
                    f"⚝ <b>{to_p_font('NEW REFERRAL JOINED')}</b>\n"
                    f"✦ You received {to_p_font(1)} BDT. Balance: {to_p_font(ref_user['balance'])} BDT",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # সম্পূর্ণ একটি মাত্র মেসেজে ওনার ইউজারনেম, চ্যানেল লিংক এবং মেনুবার কিবোর্ড
    welcome_msg = (
        "﷽\n\n"
        f"✦ <b>{to_p_font('ASSALAMU ALAIKUM')}</b>\n\n"
        "আসসালামু আলাইকুম, আশা করি আপনারা সবাই ভালো আছেন।\n"
        "আমাদের বটটি ব্যবহার করার জন্য আপনাকে অনেক ধন্যবাদ।\n\n"
        f"⛃ <b>{to_p_font('OWNER')}:</b> {ADMIN_USERNAME}\n"
        f"𓊕 <b>{to_p_font('STATUS')}:</b> {to_p_font('ONLINE')}\n\n"
        f"➠ <b>{to_p_font('COMMUNITY CHANNEL')}:</b>\n"
        f"𓆩♛𓆪 <a href=\"{CHANNEL_URL}\"><b>[{to_p_font('CLICK HERE TO JOIN OUR CHANNEL')}]</b></a>\n\n"
        "<i>নিচের মেনুবার থেকে আপনার কাঙ্ক্ষিত অপশনটি বেছে নিন:</i>"
    )

    bot.send_message(
        message.chat.id, 
        welcome_msg, 
        parse_mode="HTML", 
        reply_markup=main_reply_keyboard(),
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda msg: msg.text and to_p_font('PROFILE') in msg.text)
def handle_profile(message):
    uid = message.from_user.id
    u_data = get_user(uid)
    active = u_data.get("active_vps")
    status = f"{to_p_font('RUNNING')} (#{to_p_font(active)})" if active else to_p_font("NONE")

    txt = (
        f"𔒝 <b>{to_p_font('USER PROFILE DETAILS')}</b>\n\n"
        f"⛃ <b>{to_p_font('USER ID')}:</b> <code>{to_p_font(uid)}</code>\n"
        f"⛁ <b>{to_p_font('WALLET BALANCE')}:</b> {to_p_font(u_data['balance'])} BDT\n"
        f"♞ <b>{to_p_font('TOTAL REFERRALS')}:</b> {to_p_font(u_data['referrals'])}\n"
        f"✦ <b>{to_p_font('ACTIVE PLAN')}:</b> {status}"
    )
    bot.reply_to(message, txt, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text and to_p_font('BALANCE') in msg.text)
def handle_balance(message):
    uid = message.from_user.id
    u_data = get_user(uid)
    txt = (
        f"⛃ <b>{to_p_font('ACCOUNT BALANCE')}</b>\n\n"
        f"✦ <b>{to_p_font('BALANCE')}:</b> {to_p_font(u_data['balance'])} BDT\n"
        f"♞ <b>{to_p_font('INVITED USERS')}:</b> {to_p_font(u_data['referrals'])}\n\n"
        f"❂ Invite {to_p_font(20)} users to get a {to_p_font('7 DAYS')} access free."
    )
    bot.reply_to(message, txt, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text and to_p_font('REFERRAL') in msg.text)
def handle_referral(message):
    uid = message.from_user.id
    u_data = get_user(uid)
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={uid}"

    txt = (
        f"♞ <b>{to_p_font('REFERRAL PORTAL')}</b>\n\n"
        f"✦ <b>{to_p_font('YOUR LINK')}:</b>\n<code>{ref_link}</code>\n\n"
        f"⛁ <b>{to_p_font('REWARD')}:</b> {to_p_font(1)} BDT per refer\n"
        f"𔒝 <b>{to_p_font('PROGRESS')}:</b> {to_p_font(u_data['referrals'])}/{to_p_font(20)}\n\n"
        f"২০টি রেফার সম্পন্ন হলে নিচের ক্লেইম বাটন দিয়ে ৭ দিনের অ্যাক্সেস নিন।"
    )

    markup = types.InlineKeyboardMarkup()
    claim_btn = types.InlineKeyboardButton(f"⍟ {to_p_font('CLAIM 7 DAYS FREE')}", callback_data="claim_referral")
    markup.add(claim_btn)

    bot.reply_to(message, txt, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text and to_p_font('PLANS & PRICING') in msg.text)
def handle_plans(message):
    txt = (
        f"✦ <b>{to_p_font('AVAILABLE PLANS')}</b>\n\n"
        f"নিচের তালিকা থেকে আপনার পছন্দের প্যাকেজ বেছে নিন:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for pkg_id, info in PACKAGES.items():
        btn_label = f"{info['name']} ⎯ {to_p_font(info['price'])} BDT"
        buttons.append(types.InlineKeyboardButton(btn_label, callback_data=f"selpkg_{pkg_id}"))
    
    btn_custom = types.InlineKeyboardButton(f"❖ {to_p_font('CUSTOM DAYS PLAN')}", callback_data="custom_days_req")
    markup.add(*buttons)
    markup.add(btn_custom)

    bot.reply_to(message, txt, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("selpkg_"))
def handle_package_selection(call):
    pkg_id = call.data.replace("selpkg_", "")
    if pkg_id not in PACKAGES:
        return
    pkg = PACKAGES[pkg_id]
    uid = call.from_user.id
    u_data = get_user(uid)
    u_data["temp_pkg"] = {"name": pkg["name"], "days": pkg["days"], "price": pkg["price"]}

    txt = (
        f"✦ <b>{to_p_font('SELECT PAYMENT METHOD')}</b>\n\n"
        f"✦ <b>{to_p_font('PLAN')}:</b> {pkg['name']}\n"
        f"⛃ <b>{to_p_font('PRICE')}:</b> {to_p_font(pkg['price'])} BDT\n\n"
        f"আপনি দয়া করে পেমেন্ট পদ্ধতি সিলেক্ট করুন নগদ না বিকাশ।"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    b_bkash = types.InlineKeyboardButton(f"✦ {to_p_font('BKASH')}", callback_data="pay_method_bkash")
    b_nagad = types.InlineKeyboardButton(f"✦ {to_p_font('NAGAD')}", callback_data="pay_method_nagad")
    markup.add(b_bkash, b_nagad)

    bot.send_message(call.message.chat.id, txt, parse_mode="HTML", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "custom_days_req")
def handle_custom_days_req(call):
    uid = call.from_user.id
    u_data = get_user(uid)
    u_data["state"] = "awaiting_custom_days"

    msg = (
        f"❖ <b>{to_p_font('CUSTOM DURATION PLAN')}</b>\n\n"
        f"প্রতি দিনের জন্য খরচ: {to_p_font(PER_DAY_CUSTOM_PRICE)} BDT\n"
        f"আপনি কত দিনের জন্য নিতে চান? শুধু দিনের সংখ্যাটি লিখে পাঠান (যেমন: 2 বা 5):"
    )
    bot.send_message(call.message.chat.id, msg, parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_method_"))
def handle_payment_method(call):
    method = call.data.replace("pay_method_", "")
    uid = call.from_user.id
    u_data = get_user(uid)
    
    if not u_data.get("temp_pkg"):
        bot.answer_callback_query(call.id, "সেশন পাওয়া যায়নি। পুনরায় সিলেক্ট করুন।")
        return

    u_data["temp_method"] = method
    u_data["state"] = "awaiting_payment_proof"
    pkg = u_data["temp_pkg"]

    number = BKASH_NUMBER if method == "bkash" else NAGAD_NUMBER
    method_title = "BKASH" if method == "bkash" else "NAGAD"

    txt = (
        f"✦ <b>{to_p_font(method_title + ' PAYMENT')}</b>\n\n"
        f"✦ <b>{to_p_font('PLAN')}:</b> {pkg['name']}\n"
        f"⛃ <b>{to_p_font('PRICE')}:</b> {to_p_font(pkg['price'])} BDT\n\n"
        f"✦ <b>{to_p_font('NUMBER')}:</b> <code>{number}</code> (Personal)\n\n"
        f"দয়া করে উপরের নম্বরে <b>{to_p_font(pkg['price'])} BDT</b> সেন্ড মানি করুন।\n"
        f"টাকা পাঠানোর পর ট্রানজেকশন/আইডি কোড এবং স্ক্রিনশট এখানে পাঠান।\n"
        f"দয়া করে সেন্ড মানি করে অপেক্ষা করুন। ওনার যাচাই করে অ্যাক্টিভ করে দেবে।"
    )

    bot.send_message(call.message.chat.id, txt, parse_mode="HTML")
    bot.answer_callback_query(call.id)

# ইউজার থেকে কাস্টম দিন অথবা পেমেন্ট প্রুফ রিসিভ করা
@bot.message_handler(content_types=['text', 'photo'])
def handle_user_input(message):
    uid = message.from_user.id
    u_data = get_user(uid)

    if u_data.get("state") == "awaiting_custom_days" and message.text:
        if not message.text.isdigit() or int(message.text) <= 0:
            bot.reply_to(message, "সঠিক দিনের সংখ্যা লিখুন (যেমন: 2 বা 5):")
            return
        days = int(message.text)
        price = days * PER_DAY_CUSTOM_PRICE
        u_data["temp_pkg"] = {"name": f"✦ {to_p_font(str(days) + ' DAYS')}", "days": days, "price": price}
        u_data["state"] = None

        txt = (
            f"✦ <b>{to_p_font('SELECT PAYMENT METHOD')}</b>\n\n"
            f"✦ <b>{to_p_font('PLAN')}:</b> {u_data['temp_pkg']['name']}\n"
            f"⛃ <b>{to_p_font('PRICE')}:</b> {to_p_font(price)} BDT\n\n"
            f"দয়া করে পেমেন্ট পদ্ধতি সিলেক্ট করুন নগদ না বিকাশ।"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        b_bkash = types.InlineKeyboardButton(f"✦ {to_p_font('BKASH')}", callback_data="pay_method_bkash")
        b_nagad = types.InlineKeyboardButton(f"✦ {to_p_font('NAGAD')}", callback_data="pay_method_nagad")
        markup.add(b_bkash, b_nagad)
        bot.reply_to(message, txt, parse_mode="HTML", reply_markup=markup)
        return

    if u_data.get("state") == "awaiting_payment_proof":
        global request_counter
        req_id = request_counter
        request_counter += 1

        pkg = u_data.get("temp_pkg", {})
        method = u_data.get("temp_method", "None").upper()
        uname = f"@{message.from_user.username}" if message.from_user.username else "No Username"

        proof_text = message.caption if message.caption else (message.text if message.text else "Proof Attached")
        photo_id = message.photo[-1].file_id if message.photo else None

        with lock:
            pending_requests[req_id] = {
                "user_id": uid,
                "days": pkg.get("days", 7),
                "pkg_name": pkg.get("name", "Standard"),
                "price": pkg.get("price", 0),
                "method": method
            }

        # ওনারের নিকট Approve ও Reject বাটনসহ বার্তা পাঠানো
        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        btn_yes = types.InlineKeyboardButton(f"✓ {to_p_font('APPROVE')}", callback_data=f"adm_yes_{req_id}")
        btn_no = types.InlineKeyboardButton(f"✕ {to_p_font('REJECT')}", callback_data=f"adm_no_{req_id}")
        admin_markup.add(btn_yes, btn_no)

        admin_txt = (
            f"⛃ <b>{to_p_font('NEW PAYMENT PROOF RECEIVED')}</b>\n\n"
            f"✦ <b>{to_p_font('ORDER ID')}:</b> #{to_p_font(req_id)}\n"
            f"✦ <b>{to_p_font('USER')}:</b> {uname} (<code>{to_p_font(uid)}</code>)\n"
            f"✦ <b>{to_p_font('PACKAGE')}:</b> {pkg.get('name')}\n"
            f"⛃ <b>{to_p_font('PRICE')}:</b> {to_p_font(pkg.get('price'))} BDT\n"
            f"⛁ <b>{to_p_font('METHOD')}:</b> {to_p_font(method)}\n"
            f"✎ <b>{to_p_font('DETAILS / TRX')}:</b>\n<code>{proof_text}</code>"
        )

        try:
            if photo_id:
                bot.send_photo(ADMIN_ID, photo_id, caption=admin_txt, parse_mode="HTML", reply_markup=admin_markup)
            else:
                bot.send_message(ADMIN_ID, admin_txt, parse_mode="HTML", reply_markup=admin_markup)
        except Exception as e:
            print(f"Admin send error: {e}")

        u_data["state"] = None
        u_data["temp_pkg"] = None
        u_data["temp_method"] = None

        confirm_msg = (
            f"✦ <b>{to_p_font('SUBMITTED SUCCESSFULLY')}</b>\n\n"
            f"আপনার মেসেজটি সাবমিট করা হয়েছে। দয়া করে অপেক্ষা করুন।\n"
            f"ওনার তথ্য যাচাই করে টার্মিনাল অনুমোদন করবেন।"
        )
        bot.reply_to(message, confirm_msg, parse_mode="HTML")

# ওনার বাটন হ্যান্ডলার (APPROVE / REJECT)
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def handle_admin_decision(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "অনুমোদন কেবল ওনারের জন্য।", show_alert=True)
        return

    parts = call.data.split("_")
    action = parts[1]
    req_id = int(parts[2])

    with lock:
        req = pending_requests.get(req_id)

    if not req:
        bot.answer_callback_query(call.id, "এই অনুরোধটি আর সক্রিয় নেই।")
        return

    target_uid = req["user_id"]
    days = req["days"]

    if action == "yes":
        bot.answer_callback_query(call.id, "অনুমোদিত হয়েছে। প্রসেস চলছে...")
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.send_message(ADMIN_ID, f"✓ <b>{to_p_font('ORDER #' + str(req_id) + ' APPROVED')}</b>", parse_mode="HTML")
        
        bot.send_message(target_uid, f"✦ <b>{to_p_font('ORDER APPROVED')}</b>\nআপনার পেমেন্ট সফলভাবে অনুমোদিত হয়েছে। টার্মিনাল চালু হচ্ছে...", parse_mode="HTML")
        success = create_and_send_vps(target_uid, days)
        if not success:
            bot.send_message(ADMIN_ID, f"⚝ ইউজার <code>{target_uid}</code> এর টার্মিনাল চালু করতে ব্যর্থ হয়েছে।")

    elif action == "no":
        bot.answer_callback_query(call.id, "অনুরোধটি বাতিল করা হয়েছে।")
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        bot.send_message(ADMIN_ID, f"✕ <b>{to_p_font('ORDER #' + str(req_id) + ' REJECTED')}</b>", parse_mode="HTML")
        
        reject_msg = (
            f"✕ <b>{to_p_font('ORDER REJECTED')}</b>\n\n"
            f"দুঃখিত, আপনার পেমেন্ট তথ্যটি সঠিক না থাকায় অনুরোধটি বাতিল করা হয়েছে।"
        )
        bot.send_message(target_uid, reject_msg, parse_mode="HTML")

    with lock:
        if req_id in pending_requests:
            del pending_requests[req_id]

@bot.callback_query_handler(func=lambda call: call.data == "claim_referral")
def handle_claim_referral(call):
    uid = call.from_user.id
    u_data = get_user(uid)
    if u_data["referrals"] >= 20:
        u_data["referrals"] -= 20
        bot.send_message(call.message.chat.id, f"⚝ {to_p_font('DEPLOYING YOUR 7 DAYS ACCESS')}...")
        create_and_send_vps(uid, days=7)
    else:
        bot.answer_callback_query(call.id, f"পর্যাপ্ত রেফার নেই! সম্পন্ন: {u_data['referrals']}/20", show_alert=True)

# ওনার টার্মিনাল কন্ট্রোল
@bot.message_handler(commands=['kill'])
def handle_kill(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "ব্যবহারবিধি: <code>/kill <term_id></code>", parse_mode="HTML")
        return
    tid = int(parts[1])
    if kill_terminal(tid):
        bot.reply_to(message, f"✕ <b>{to_p_font('TERMINATED')}</b> Instance #{to_p_font(tid)}", parse_mode="HTML")
    else:
        bot.reply_to(message, f"ইনস্ট্যান্স #{to_p_font(tid)} পাওয়া যায়নি।", parse_mode="HTML")

@bot.message_handler(commands=['list'])
def handle_list(message):
    if message.from_user.id != ADMIN_ID:
        return
    with lock:
        if not terminals:
            bot.reply_to(message, f"❂ {to_p_font('NO ACTIVE SESSIONS')}", parse_mode="HTML")
            return
        items = list(terminals.items())

    res = f"𓆩♛𓆪 <b>{to_p_font('ACTIVE INSTANCES')}</b>\n\n"
    for tid, info in items:
        exp = info["expire_at"].strftime("%d %b, %I:%M %p")
        res += (
            f"✦ <b>ID:</b> <code>{to_p_font(tid)}</code> | User: <code>{to_p_font(info['user_id'])}</code>\n"
            f"⩇⩇:⩇⩇ Exp: {to_p_font(exp)}\n"
            f"✕ Kill: <code>/kill {tid}</code>\n\n"
        )
    bot.reply_to(message, res, parse_mode="HTML")

if __name__ == "__main__":
    print("Engine Started: Listening for requests...")
    time.sleep(2)
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10, logger_level=None)
        except ApiTelegramException as e:
            if e.error_code == 409:
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
