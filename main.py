# -*- coding: utf-8 -*-
"""
=============================================================================
DRX-TM WinGo 30S Professional Auto Signal Telegram Bot (VIP Edition)
Features & Architecture:
  1. Mandatory Channel Subscription (@DARK67HACK) Verification
  2. Referral Verification System (1 Referral required for normal users)
  3. Owner Bypass & Control (Owner ID: 8707571669)
  4. Dynamic Channel Registration via /admin88 with Inline UI
  5. Schedule Management via /TM command (Private confirmation only)
  6. Advanced Prediction Engines:
     - TIGER PRO (Moving Average, Frequency & Trend Analytics)
     - RED PRO (Sequence Pattern Matching)
     - GREEN PRO (Markov Transition Chain)
  7. Visual Sticker Feedback: Start, Win, Loss, Morning & Safe End Stickers
  8. Safe Exit Strategy: Schedule শেষ হলেও লসে বন্ধ হবে না, উইন হওয়ার পর এন্ড স্টিকার দিয়ে থামবে
  9. VIP Font Converter & Multi-threaded Safe Data Fetching
=============================================================================
"""

import time
import random
import re
import threading
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter
import telebot
from telebot import types

# =========================================================
# CONFIGURATION & CONSTANTS
# =========================================================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
OWNER_ID = 8707571669
REQUIRED_CHANNEL = "@DARK67HACK"
CHANNEL_URL = "https://t.me/DARK67HACK"

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BACKUP_API_URL = "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# =========================================================
# STICKER IDS
# =========================================================
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

# =========================================================
# BOT & THREAD-SAFE STATE STORAGE
# =========================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db_lock = threading.Lock()

# ইউজার ও সেশন ডাটাবেস
# Format:
# users_db[user_id] = {
#     "channel_id": None,
#     "schedules": [],
#     "state": "WAITING",  # WAITING, RUNNING, STOPPING
#     "target_issue": None,
#     "pending_pred": None,
#     "last_was_win": True,
#     "referrals": set(),
#     "referred_by": None
# }
users_db = {}
LAST_MORNING_DATE = None

# =========================================================
# VIP FONT ENGINE (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
# =========================================================
def to_vip(text: str) -> str:
    res = []
    for ch in str(text):
        code = ord(ch)
        if 65 <= code <= 90:
            res.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:
            res.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:
            res.append(chr(0x1D7CE + (code - 48)))
        else:
            res.append(ch)
    return "".join(res)

# =========================================================
# PREDICTION ENGINES
# =========================================================
VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

def get_color(num: int) -> str:
    if num in VIOLET_NUMBERS:
        return "VIOLET"
    return "RED" if num in RED_NUMBERS else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num in BIG_NUMBERS else "SMALL"

def calculate_tiger_pro(market_records):
    """
    Engine 1: TIGER PRO - Deep Analytics, Moving Average & Trend
    """
    if len(market_records) < 20:
        return "BIG"

    sample = market_records[:100]
    last_num = sample[0]["number"]

    # ১. মুভিং এভারেজ চেক (গত ১০ রাউন্ড)
    recent_10_nums = [x["number"] for x in sample[:10]]
    avg_10 = sum(recent_10_nums) / 10.0

    # ২. ফ্রিকোয়েন্সি এবং ট্রেন্ড ভ্যালিডেশন
    if avg_10 > 4.8:
        pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"

    return pred_size

def calculate_red_pro(market_records):
    """
    Engine 2: RED PRO - Sequence Pattern Matching
    """
    if len(market_records) < 25:
        return "BIG"
    t1, t2 = market_records[0]["number"], market_records[1]["number"]
    found_idx = -1
    for i in range(20, len(market_records) - 2):
        if (market_records[i]["number"], market_records[i + 1]["number"]) in [(t1, t2), (t2, t1)]:
            found_idx = i
            break
    n_above = market_records[found_idx - 1]["number"] if found_idx != -1 else (t1 + 3) % 10
    n_below = market_records[found_idx + 2]["number"] if found_idx != -1 else (t2 + 7) % 10
    avg = (n_above + n_below) / 2.0
    return "BIG" if avg >= 4.5 else "SMALL"

def calculate_green_pro(market_records):
    """
    Engine 3: GREEN PRO - Markov Transition Chain
    """
    if len(market_records) < 15:
        return "SMALL"
    sample = market_records[:100]
    latest = sample[0]["number"]
    transitions = [sample[idx]["number"] for idx in range(len(sample) - 1) if sample[idx + 1]["number"] == latest]
    if transitions:
        cands = [n for n, _ in Counter(transitions).most_common(2)]
        avg = sum(cands) / float(len(cands))
        return "BIG" if avg >= 4.5 else "SMALL"
    return "BIG" if latest < 5 else "SMALL"

def get_best_prediction(market_records):
    """সবগুলো ইঞ্জিনের ফলাফল মূল্যায়ন করে সেরা প্রেডিকশন নির্বাচন করে"""
    tiger = calculate_tiger_pro(market_records)
    red = calculate_red_pro(market_records)
    green = calculate_green_pro(market_records)
    
    votes = [tiger, tiger, red, green]
    decision = Counter(votes).most_common(1)[0][0]
    return decision

# =========================================================
# API RESULT FETCHER
# =========================================================
def fetch_latest_results():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    payload = {"pageNumber": 1, "pageSize": 50}
    try:
        res = requests.post(API_URL, json=payload, headers=headers, timeout=5)
        if res.status_code != 200:
            res = requests.get(API_URL, headers=headers, timeout=5)
        data = res.json()

        def extract_list(d):
            if isinstance(d, list) and len(d) > 0 and isinstance(d[0], dict) and ('issueNumber' in d[0] or 'issue' in d[0]):
                return d
            elif isinstance(d, dict):
                for v in d.values():
                    found = extract_list(v)
                    if found:
                        return found
            return None

        issue_list = extract_list(data)
        if issue_list:
            parsed = []
            for item in issue_list:
                issue = str(item.get('issueNumber', item.get('issue', '')))
                num = item.get('number', item.get('result', -1))
                if issue and num != -1:
                    parsed.append({"period": issue, "number": int(num)})
            return parsed
    except Exception:
        pass
    return []

# =========================================================
# HELPER FUNCTIONS (ACCESS CONTROL & REFERRALS)
# =========================================================
def check_channel_membership(user_id: int) -> bool:
    """ইউজার বাধ্যতামূলক চ্যানেলে জয়েন আছে কিনা যাচাই করে"""
    if user_id == OWNER_ID:
        return True
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception:
        pass
    return False

def check_user_access(user_id: int) -> tuple[bool, str]:
    """ইউজারের চ্যানেল সাবস্ক্রিপশন ও রেফারেল যাচাই করে"""
    if user_id == OWNER_ID:
        return True, "OWNER"

    if not check_channel_membership(user_id):
        return False, "NEED_JOIN"

    with db_lock:
        udata = users_db.get(user_id, {})
        referrals = udata.get("referrals", set())

    if len(referrals) < 1:
        return False, "NEED_REFERRAL"

    return True, "ALLOWED"

def format_12hr(hour, minute):
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def is_in_schedule(now, schedules):
    current_minutes = now.hour * 60 + now.minute
    for (sh, sm, eh, em) in schedules:
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
        if start_mins <= current_minutes < end_mins:
            return True
    return False

# =========================================================
# TELEGRAM BOT HANDLERS
# =========================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    text_parts = message.text.strip().split()

    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "channel_id": None,
                "schedules": [],
                "state": "WAITING",
                "target_issue": None,
                "pending_pred": None,
                "last_was_win": True,
                "referrals": set(),
                "referred_by": None
            }

        # রেফারেল কোড চেক
        if len(text_parts) > 1 and text_parts[1].startswith("ref_"):
            try:
                referrer_id = int(text_parts[1].replace("ref_", ""))
                if referrer_id != user_id and referrer_id in users_db:
                    if users_db[user_id]["referred_by"] is None:
                        users_db[user_id]["referred_by"] = referrer_id
                        users_db[referrer_id]["referrals"].add(user_id)
                        try:
                            bot.send_message(
                                referrer_id,
                                f"🎉 <b>নতুন রেফারেল যুক্ত হয়েছে!</b>\nআপনার মোট রেফারেল: <b>{len(users_db[referrer_id]['referrals'])}</b> জন।"
                            )
                        except Exception:
                            pass
            except Exception:
                pass

    # এক্সেস যাচাই
    has_access, reason = check_user_access(user_id)

    if reason == "NEED_JOIN":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join DARK67HACK", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Verify / চেক করুন", callback_data="check_join"))
        bot.send_message(
            user_id,
            "⚠️ <b>বটটি ব্যবহার করার জন্য আপনাকে প্রথমে আমাদের অফিসিয়াল চ্যানেলে যুক্ত হতে হবে।</b>\n\nনিচের বাটনে ক্লিক করে জয়েন করুন এবং ভেরিফাই বাটনে চাপ দিন:",
            reply_markup=markup
        )
        return

    if reason == "NEED_REFERRAL":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        bot.send_message(
            user_id,
            f"⚠️ <b>একটি রেফারেল আবশ্যক!</b>\n\nবটের সার্ভিস ও ফিচার আনলক করতে আপনাকে অন্তত <b>১ জন বন্ধুকে</b> রেফার করতে হবে।\n\n🔗 <b>আপনার রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\nলিংকটি শেয়ার করুন এবং তিনি স্টার্ট দিলে আপনার অ্যাকাউন্ট আনলক হবে।"
        )
        return

    # এক্সেস পেলে মূল মেনু
    welcome_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SYSTEM ONLINE & AUTHORIZED')}</i>\n"
        "────────────────────────\n"
        "স্বাগতম! আপনার অ্যাকাউন্ট সফলভাবে অ্যাক্টিভ হয়েছে।\n\n"
        "⚙️ চ্যানেল যুক্ত এবং সেটিংস কনফিগার করতে <b>/admin88</b> কমান্ড দিন।"
    )
    bot.send_message(user_id, welcome_text)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def handle_verify_join(call):
    user_id = call.message.chat.id
    if check_channel_membership(user_id):
        bot.answer_callback_query(call.id, "✅ চ্যানেল ভেরিফিকেশন সফল!")
        handle_start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!", show_alert=True)

# =========================================================
# /admin88 PANEL & CHANNEL SETUP
# =========================================================
@bot.message_handler(commands=['admin88'])
def handle_admin88(message):
    user_id = message.chat.id
    has_access, reason = check_user_access(user_id)
    if not has_access:
        handle_start(message)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel_step")
    btn_time = types.InlineKeyboardButton("🕒 Schedule Setup Info", callback_data="sched_info")
    markup.add(btn_add, btn_time)

    admin_msg = (
        f"<b>⚙️ {to_vip('ADMIN PANEL')}</b>\n"
        "────────────────────────\n"
        "আপনার চ্যানেল সেটআপ ও সিগন্যাল কন্ট্রোলের জন্য নিচের অপশনটি বেছে নিন:"
    )
    bot.send_message(user_id, admin_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["add_channel_step", "sched_info"])
def handle_admin_callbacks(call):
    user_id = call.message.chat.id

    if call.data == "add_channel_step":
        prompt = (
            "📌 <b>চ্যানেল সেটআপ করার নিয়ম:</b>\n\n"
            "১. প্রথমে এই বটটিকে আপনার চ্যানেলে <b>Administrator</b> হিসেবে যুক্ত করুন (মেসেজ এবং স্টিকার পাঠানোর পারমিশন দিন)।\n"
            "২. অ্যাডমিনশিপ দেওয়ার পর, আপনার চ্যানেলের ID (যেমন: <code>-1001234567890</code>) অথবা ইউজারনেম (যেমন: <code>@mychannel</code>) এখানে লিখে পাঠান:"
        )
        msg = bot.send_message(user_id, prompt)
        bot.register_next_step_handler(msg, process_channel_registration)

    elif call.data == "sched_info":
        info = (
            "🕒 <b>টাইম শিডিউল সেট করার নিয়ম:</b>\n\n"
            "কমান্ড ফরম্যাট: <code>/TM 10:30AM-1:00PM</code>\n"
            "বা <code>/TM 5:12PM-11:00PM</code>\n\n"
            "এই কমান্ড দিলে বট আপনার নির্ধারিত সময়ে চ্যানেলে অটোমেটিক সিগন্যাল শুরু করবে।"
        )
        bot.send_message(user_id, info)

def process_channel_registration(message):
    user_id = message.chat.id
    raw_channel = message.text.strip()

    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "channel_id": None, "schedules": [], "state": "WAITING",
                "target_issue": None, "pending_pred": None, "last_was_win": True,
                "referrals": set(), "referred_by": None
            }
        users_db[user_id]["channel_id"] = raw_channel

    # ইউজারের চাওয়া অনুযায়ী একুরেট রেসপন্স
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅")

# =========================================================
# /TM SCHEDULE COMMAND (NO CHANNEL SPAM)
# =========================================================
@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def handle_time_schedule(message):
    user_id = message.chat.id
    has_access, _ = check_user_access(user_id)
    if not has_access:
        handle_start(message)
        return

    with db_lock:
        udata = users_db.get(user_id)
        if not udata or not udata.get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে <b>/admin88</b> কমান্ড দিয়ে আপনার চ্যানেল যুক্ত করুন।")
            return

    text = message.text.strip().upper()
    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text)

    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)

        # Start Time AM/PM
        if sampm:
            if sampm == 'PM' and sh != 12:
                sh += 12
            if sampm == 'AM' and sh == 12:
                sh = 0
        else:
            if sh < 12 and sh != 0:
                sh += 12

        # End Time AM/PM
        if eampm:
            if eampm == 'PM' and eh != 12:
                eh += 12
            if eampm == 'AM' and eh == 12:
                eh = 0
        else:
            if eh < 12 and eh != 0:
                eh += 12

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]

        time_range_clean = message.text.replace("/TM", "").replace("/tm", "").strip()
        # চ্যানেলে কোনো মেসেজ না দিয়ে শুধুমাত্র ইউজারকে কনফার্মেশন পাঠানো হবে
        bot.send_message(user_id, f"হ্যাঁ, আমরা {time_range_clean} পর্যন্ত সিগন্যাল দিব। 🎯")
    else:
        bot.send_message(user_id, "❌ ফরম্যাট সঠিক নয়! উদাহরণ: <code>/TM 5:12PM-1:00PM</code>")

# =========================================================
# SIGNAL DISPATCHER
# =========================================================
def send_prediction_signal(channel_id: str, issue: str, prediction: str):
    short_issue = str(issue)[-6:]
    if prediction == "BIG":
        digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2))
    else:
        digits = "/".join(random.sample(['0', '1', '2', '3', '4'], 2))

    text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit    ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel_id, text)
    except Exception as e:
        print(f"[Error] Failed to send signal to {channel_id}: {e}")

# =========================================================
# CORE MONITORING & DISPATCH ENGINE (BACKGROUND WORKER)
# =========================================================
def market_monitor_worker():
    global LAST_MORNING_DATE
    while True:
        try:
            results = fetch_latest_results()
            if not results:
                time.sleep(2)
                continue

            curr_issue = results[0]["period"]
            now = datetime.now(BD_TIMEZONE)

            # সকাল ৫টায় মর্নিং স্টিকার চেক
            if now.hour == 5 and now.minute == 0:
                if LAST_MORNING_DATE != now.date():
                    with db_lock:
                        all_channels = [u.get("channel_id") for u in users_db.values() if u.get("channel_id")]
                    for ch in set(all_channels):
                        try:
                            bot.send_sticker(ch, MORNING_STICKER)
                        except Exception:
                            pass
                    LAST_MORNING_DATE = now.date()

            with db_lock:
                active_users = list(users_db.items())

            for user_id, udata in active_users:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])

                if not channel_id or not schedules:
                    continue

                in_sched = is_in_schedule(now, schedules)
                state = udata["state"]

                # ১. শিডিউল অনুযায়ী সেশন শুরু
                if in_sched and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except Exception:
                        pass

                # ২. শিডিউল শেষ হলে সেফ স্টপিং মোডে যাওয়া
                elif not in_sched and state == "RUNNING":
                    udata["state"] = "STOPPING"

                # ৩. ফলাফল যাচাই (Evaluation)
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")

                if target_issue and curr_issue >= target_issue:
                    target_rec = next((r for r in results if r["period"] == target_issue), None)
                    if target_rec:
                        actual_num = target_rec["number"]
                        actual_is_big = (actual_num >= 5)
                        predicted_is_big = (pending_pred == "BIG")
                        is_win = (actual_is_big == predicted_is_big)

                        # স্টিকার প্রদান
                        try:
                            if is_win:
                                bot.send_sticker(channel_id, random.choice(WIN_STICKERS))
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                        except Exception:
                            pass

                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # শিডিউল শেষের সময় উইন হলে সেশন শেষ ও এন্ড স্টিকার প্রদান
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except Exception:
                                pass
                            udata["state"] = "WAITING"

                # ৪. নতুন সিগন্যাল জেনারেট ও পাঠানো (TIGER PRO & Multi-Engine)
                if udata["state"] in ["RUNNING", "STOPPING"] and udata.get("target_issue") is None:
                    # প্রেডিকশন ইঞ্জিন নির্বাচন
                    prediction = get_best_prediction(results)
                    try:
                        next_issue = str(int(curr_issue) + 1)
                    except Exception:
                        next_issue = f"{int(time.time())}"

                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)

        except Exception as e:
            print(f"[Worker Exception]: {e}")

        time.sleep(2)

# =========================================================
# BOT RUNNER
# =========================================================
if __name__ == "__main__":
    print("=" * 65)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} ENGINE SYSTEM ONLINE")
    print("Dedicated to: WinGo 30S Automated Telegram Predictor")
    print(f"Owner ID: {OWNER_ID} | Mandatory Channel: {REQUIRED_CHANNEL}")
    print("=" * 65)

    # ব্যাকগ্রাউন্ড সিগন্যাল ও রেজাল্ট মনিটরিং থ্রেড শুরু
    worker_thread = threading.Thread(target=market_monitor_worker, daemon=True)
    worker_thread.start()

    # মেইন টেলিগ্রাম বট পোলিং
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=15)
        except Exception as err:
            print(f"[Polling Error]: {err}. Reconnecting in 5 seconds...")
            time.sleep(5)
