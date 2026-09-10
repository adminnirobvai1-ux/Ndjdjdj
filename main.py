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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8765791320:AAFCB4Ls3ASrPW_91m6uZhmIexqRrbk9nY0")
ADMIN_ID = 8707571669
CHANNEL_URL = "https://t.me/DARK67HACK"
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

BD_TZ = pytz.timezone("Asia/Dhaka")

# ডেটাবেস
users = {}
terminals = {}
terminal_counter = 1
lock = threading.Lock()

# ম্যাথমেটিক্যাল বোল্ড রূপান্তরকারী (A-Z, 0-9)
BOLD_MAP = {
    'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈',
    'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑',
    'S': '𝐒', 'T': '𝐓', 'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
    '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
}

def to_p_font(text):
    """সাধারণ টেক্সটকে প্রিমিয়াম ফন্টে কনভার্ট করার ফাংশন"""
    return "".join(BOLD_MAP.get(c, c) for c in str(text))

# প্যাকেজ কনফিগারেশন
PACKAGES = {
    "pkg_7d": {"name": f"✦ {to_p_font('7 DAYS VPS')}", "days": 7, "price": 20},
    "pkg_15d": {"name": f"✦ {to_p_font('15 DAYS VPS')}", "days": 15, "price": 40},
    "pkg_1m": {"name": f"✦ {to_p_font('1 MONTH VPS')}", "days": 30, "price": 70},
    "pkg_2m": {"name": f"✦ {to_p_font('2 MONTHS VPS')}", "days": 60, "price": 130},
    "pkg_1y": {"name": f"✦ {to_p_font('1 YEAR VPS')}", "days": 365, "price": 500},
}

def get_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0, "referred_by": None, "referrals": 0, "active_vps": None}
    return users[uid]

def spawn_sshx():
    """রিয়েল sshx টার্মিনাল এক্সিকিউশন ও লিঙ্ক ক্যাচিং"""
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
    """টার্মিনাল প্রক্রিয়া বন্ধ করা"""
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
    """মেয়াদ শেষে স্বয়ংক্রিয়ভাবে টার্মিনাল বন্ধ করা"""
    def _runner():
        time.sleep(delay_seconds)
        if kill_terminal(term_id):
            try:
                msg = (
                    f"⩇⩇:⩇⩇ <b>{to_p_font('TERMINAL EXPIRED')}</b>\n\n"
                    f"✦ Your Terminal #{to_p_font(term_id)} has reached its duration limit ({to_p_font(expire_label)}) and was shut down."
                )
                bot.send_message(user_id, msg, parse_mode="HTML")
            except Exception:
                pass
    t = threading.Thread(target=_runner, daemon=True)
    t.start()

def main_reply_keyboard():
    """৪টি প্রধান মেনু বাটন"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton(f"𔒝 {to_p_font('PROFILE')}")
    b2 = types.KeyboardButton(f"⛃ {to_p_font('BALANCE')}")
    b3 = types.KeyboardButton(f"♞ {to_p_font('REFERRAL')}")
    b4 = types.KeyboardButton(f"✦ {to_p_font('BUY VPS')}")
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

    # সালাম এবং ওয়েলকাম বার্তা
    welcome_msg = (
        "﷽\n\n"
        f"✦ <b>{to_p_font('ASSALAMU ALAIKUM')}</b>\n\n"
        "আসসালামু আলাইকুম, আশা করি আপনারা সবাই ভালো আছেন।\n"
        "আমাদের বটটি স্টার্ট করার জন্য আপনাকে অনেক অনেক ধন্যবাদ।\n\n"
        f"⛃ <b>{to_p_font('OWNER ID')}:</b> <code>{to_p_font(ADMIN_ID)}</code>\n"
        f"𓊕 <b>{to_p_font('SYSTEM')}:</b> {to_p_font('ACTIVE')}"
    )

    markup = types.InlineKeyboardMarkup()
    btn_chan = types.InlineKeyboardButton(f"𓆩♛𓆪 {to_p_font('JOIN OFFICIAL CHANNEL')}", url=CHANNEL_URL)
    markup.add(btn_chan)

    bot.send_message(message.chat.id, welcome_msg, parse_mode="HTML", reply_markup=main_reply_keyboard())
    bot.send_message(message.chat.id, f"➠ <b>{to_p_font('COMMUNITY CHANNEL')}:</b>", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text and to_p_font('PROFILE') in msg.text)
def handle_profile(message):
    uid = message.from_user.id
    u_data = get_user(uid)
    active = u_data.get("active_vps")
    vps_status = f"{to_p_font('RUNNING')} (#{to_p_font(active)})" if active else to_p_font("NONE")

    txt = (
        f"𔒝 <b>{to_p_font('USER PROFILE DETAILS')}</b>\n\n"
        f"⛃ <b>{to_p_font('USER ID')}:</b> <code>{to_p_font(uid)}</code>\n"
        f"⛁ <b>{to_p_font('WALLET BALANCE')}:</b> {to_p_font(u_data['balance'])} BDT\n"
        f"♞ <b>{to_p_font('TOTAL REFERRALS')}:</b> {to_p_font(u_data['referrals'])}\n"
        f"✦ <b>{to_p_font('ACTIVE VPS')}:</b> {vps_status}"
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
        f"❂ Invite {to_p_font(20)} users to get a {to_p_font('7 DAYS')} VPS entirely free."
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
        f"২০টি রেফার সফল হলে নিচের ক্লেইম বাটন দিয়ে ৭ দিনের VPS নিয়ে নিন।"
    )

    markup = types.InlineKeyboardMarkup()
    claim_btn = types.InlineKeyboardButton(f"⍟ {to_p_font('CLAIM 7 DAYS FREE VPS')}", callback_data="claim_referral")
    markup.add(claim_btn)

    bot.reply_to(message, txt, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text and to_p_font('BUY VPS') in msg.text)
def handle_buy_vps(message):
    txt = (
        f"✦ <b>{to_p_font('AVAILABLE VPS PACKAGES')}</b>\n\n"
        f"Select your plan to continue:\n"
        f"নিচের তালিকা থেকে আপনার পছন্দের মেয়াদ বেছে নিন:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for pkg_id, info in PACKAGES.items():
        btn_label = f"{info['name']} - {to_p_font(info['price'])} BDT"
        buttons.append(types.InlineKeyboardButton(btn_label, callback_data=f"buy_{pkg_id}"))
    markup.add(*buttons)

    bot.reply_to(message, txt, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_package_selection(call):
    pkg_id = call.data.replace("buy_", "")
    if pkg_id not in PACKAGES:
        return
    pkg = PACKAGES[pkg_id]
    uid = call.from_user.id
    u_data = get_user(uid)

    txt = (
        f"✦ <b>{to_p_font('PLAN CONFIRMATION')}</b>\n\n"
        f"❂ <b>{to_p_font('PACKAGE')}:</b> {pkg['name']}\n"
        f"⛃ <b>{to_p_font('PRICE')}:</b> {to_p_font(pkg['price'])} BDT\n"
        f"⛁ <b>{to_p_font('YOUR BALANCE')}:</b> {to_p_font(u_data['balance'])} BDT\n\n"
        f"<b>{to_p_font('PAYMENT DETAILS')}:</b>\n"
        f"Send Money to our Bkash/Nagad:\n"
        f"📱 <code>017XXXXXXXX</code> (Personal)\n\n"
        f"টাকা পাঠানোর পর ট্রানজেকশন আইডি এবং স্ক্রিনশট ওনারকে দিন।"
    )

    markup = types.InlineKeyboardMarkup()
    btn_confirm = types.InlineKeyboardButton(f"✉ {to_p_font('SEND PROOF TO ADMIN')}", callback_data=f"req_{pkg_id}")
    markup.add(btn_confirm)

    bot.send_message(call.message.chat.id, txt, parse_mode="HTML", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("req_"))
def handle_admin_request(call):
    pkg_id = call.data.replace("req_", "")
    pkg = PACKAGES.get(pkg_id, {})
    uid = call.from_user.id
    uname = f"@{call.from_user.username}" if call.from_user.username else "No Username"

    admin_msg = (
        f"⛃ <b>{to_p_font('NEW PURCHASE REQUEST')}</b>\n\n"
        f"👤 <b>{to_p_font('USER')}:</b> {uname} (<code>{to_p_font(uid)}</code>)\n"
        f"📦 <b>{to_p_font('TIER')}:</b> {pkg.get('name')}\n"
        f"💰 <b>{to_p_font('PRICE')}:</b> {to_p_font(pkg.get('price'))} BDT\n\n"
        f"<b>{to_p_font('TO APPROVE RUN')}:</b>\n"
        f"<code>/activate {uid} {pkg.get('days')}</code>"
    )
    try:
        bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
        bot.send_message(call.message.chat.id, f"✦ <b>{to_p_font('REQUEST SENT')}</b>\nআপনার রিকোয়েস্ট অ্যাডমিনের নিকট পাঠানো হয়েছে। যাচাই শেষে টার্মিনাল দেওয়া হবে।", parse_mode="HTML")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {e}")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "claim_referral")
def handle_claim_referral(call):
    uid = call.from_user.id
    u_data = get_user(uid)
    if u_data["referrals"] >= 20:
        u_data["referrals"] -= 20
        bot.send_message(call.message.chat.id, f"⚝ {to_p_font('DEPLOYING YOUR 7 DAYS VPS')}...")
        create_and_send_vps(uid, days=7)
    else:
        bot.answer_callback_query(call.id, f"পর্যাপ্ত রেফার নেই! রেফার হয়েছে: {u_data['referrals']}/20", show_alert=True)

def create_and_send_vps(target_user_id, days):
    """VPS তৈরি ও ব্যবহারকারীকে লিঙ্ক পাঠানো"""
    global terminal_counter
    proc, master_fd, url = spawn_sshx()
    if not url:
        bot.send_message(target_user_id, f"⚠️ {to_p_font('DEPLOYMENT FAILED')}")
        return

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
        f"✦ <b>{to_p_font('VPS DEPLOYMENT SUCCESSFUL')}</b>\n\n"
        f"⛃ <b>{to_p_font('INSTANCE ID')}:</b> <code>{to_p_font(t_id)}</code>\n"
        f"⩇⩇:⩇⩇ <b>{to_p_font('EXPIRES ON')}:</b> {to_p_font(expire_str)}\n"
        f"𓊕 <b>{to_p_font('ACCESS')}:</b> {to_p_font('ROOT SHELL READY')}\n\n"
        f"👇 <i>Click the button below to launch:</i>"
    )

    markup = types.InlineKeyboardMarkup()
    btn_term = types.InlineKeyboardButton(f"🌐 {to_p_font('LAUNCH TERMINAL')}", url=url)
    markup.add(btn_term)

    bot.send_message(target_user_id, msg, parse_mode="HTML", reply_markup=markup)

# ================= অ্যাডমিন কমান্ড ================= #

@bot.message_handler(commands=['activate'])
def handle_activate(message):
    """ওনার টার্মিনাল অনুমোদন করবেন: /activate <USER_ID> <DAYS>"""
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: <code>/activate <user_id> <days></code>", parse_mode="HTML")
        return
    target_uid = int(parts[1])
    days = int(parts[2])

    create_and_send_vps(target_uid, days)
    bot.reply_to(message, f"✦ <b>{to_p_font('ACTIVATED')}</b> {to_p_font(days)} Days VPS for <code>{to_p_font(target_uid)}</code>", parse_mode="HTML")

@bot.message_handler(commands=['kill'])
def handle_kill(message):
    """যেকোনো ইউজারের VPS তাত্ক্ষণিক অফ করতে: /kill <TERM_ID>"""
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: <code>/kill <term_id></code>", parse_mode="HTML")
        return
    tid = int(parts[1])
    if kill_terminal(tid):
        bot.reply_to(message, f"🛑 <b>{to_p_font('TERMINATED')}</b> VPS #{to_p_font(tid)}", parse_mode="HTML")
    else:
        bot.reply_to(message, f"❌ Terminal #{to_p_font(tid)} not active.", parse_mode="HTML")

@bot.message_handler(commands=['list'])
def handle_list(message):
    """চলমান টার্মিনালগুলোর তালিকা দেখতে: /list"""
    if message.from_user.id != ADMIN_ID:
        return
    with lock:
        if not terminals:
            bot.reply_to(message, f"❂ {to_p_font('NO ACTIVE TERMINALS')}", parse_mode="HTML")
            return
        items = list(terminals.items())

    res = f"𓆩♛𓆪 <b>{to_p_font('ACTIVE INSTANCES LIST')}</b>\n\n"
    for tid, info in items:
        exp = info["expire_at"].strftime("%d %b, %I:%M %p")
        res += (
            f"✦ <b>ID:</b> <code>{to_p_font(tid)}</code> | User: <code>{to_p_font(info['user_id'])}</code>\n"
            f"⩇⩇:⩇⩇ Exp: {to_p_font(exp)}\n"
            f"🛑 Kill: <code>/kill {tid}</code>\n\n"
        )
    bot.reply_to(message, res, parse_mode="HTML")

# অটো-রিকানেক্ট পোলিং
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
