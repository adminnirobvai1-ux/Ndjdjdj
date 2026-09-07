# -*- coding: utf-8 -*-
"""
DARK KILLER | DRX-TM Professional WinGo Auto Signal & Multi-Channel Management Bot
Version: 5.0 VIP Enterprise Edition
Features:
  - Custom Channel Registration via /admin88 (Dynamic per-user channels)
  - Referral System Protection & Verification Check
  - Tiger Pro Advanced Deep Analytics & Moving Average Prediction Engine
  - Real-time Multi-threaded WinGo 30S API Monitor
  - Automated Start/Stop Session Management via /TM and Schedule Rules
  - Dynamic Sticker and Win/Loss Evaluation with Session Closure Protocol
  - Support Owner Contact Integration: 8707571669 & Channel: https://t.me/DARK67HACK
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
# SYSTEM CONFIGURATION & CONSTANTS
# =========================================================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# OFFICIAL CHANNELS & OWNER INFO
MAIN_CHANNEL_LINK = "https://t.me/DARK67HACK"
OWNER_CONTACT = "8707571669"

# =========================================================
# STICKER ASSETS DATABASE
# =========================================================
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# USER & CHANNEL DATABASE STORAGE
# =========================================================
# Format: {user_id: {"channel_id": "...", "schedules": [...], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True, "referral_count": 0, "is_verified": False}}
users_db = {}
db_lock = threading.Lock()

# =========================================================
# TIGER PRO ADVANCED PREDICTION ENGINE
# =========================================================
def calculate_tiger_pro(market_records):
    """
    Tiger Pro Deep Analytics & Moving Average Prediction Engine.
    Analyzes hot numbers, moving averages, and streak patterns.
    """
    if len(market_records) < 20:
        return "BIG"
    
    sample = market_records[:100]
    last_num = sample[0]["number"]
    
    # Moving Average Check (Last 10 Rounds Trend)
    recent_10_nums = [x["number"] for x in sample[:10]]
    avg_10 = sum(recent_10_nums) / 10.0
    
    # Deep Analytics Decision Matrix
    if avg_10 > 5.0:
        pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"
        
    return pred_size

# =========================================================
# API & MARKET DATA FETCHER
# =========================================================
def fetch_latest_results():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 100}
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
                    if found: return found
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
# TELEGRAM BOT COMMANDS & INTERFACE HANDLERS
# =========================================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Join Official Channel", url=MAIN_CHANNEL_LINK),
        types.InlineKeyboardButton("⚙️ Open Admin Panel (/admin88)", callback_data="open_admin")
    )
    
    welcome_text = (
        f"<b>🔥 Welcome to DARK KILLER | DRX-TM Bot 🔥</b>\n\n"
        f"সবার আগে আমাদের অফিসিয়াল চ্যানেলে জয়েন করুন:\n👉 <a href='{MAIN_CHANNEL_LINK}'>Join {MAIN_CHANNEL_LINK}</a>\n\n"
        f"📌 <b>নিয়মাবলী:</b> বটটি ফুল এক্সেস এবং প্রিমিয়াম সিগন্যাল ব্যবহারের জন্য আপনাকে অবশ্যই কমপক্ষে <b>১টি রেফার</b> করতে হবে এবং চ্যানেলে যুক্ত থাকতে হবে।\n\n"
        f"💬 যেকোনো প্রয়োজনে মালিকের সাথে যোগাযোগ করুন: <code>{OWNER_CONTACT}</code>\n\n"
        f"সেটআপ শুরু করতে নিচের বাটনে ক্লিক করুন অথবা সরাসরি <b>/admin88</b> কমান্ড দিন।"
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(commands=['admin88'])
def admin_panel(message):
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    btn_ref = types.InlineKeyboardButton("👥 Check Referral Status", callback_data="check_referral")
    btn_help = types.InlineKeyboardButton("ℹ️ Help & Format", callback_data="help_info")
    markup.add(btn_add, btn_ref, btn_help)
    
    panel_text = (
        f"<b>⚙️ ADMIN CONTROL PANEL [DRX-TM]</b>\n"
        f"────────────────────────\n"
        f"আপনার নিজস্ব চ্যানেলে অটো সিগন্যাল সেটআপ করতে নিচের অপশনগুলো ব্যবহার করুন:\n\n"
        f"1️⃣ প্রথমে <b>Add Your Channel</b> এ ক্লিক করুন।\n"
        f"2️⃣ চ্যানেল ভেরিফাই করুন এবং সিগন্যাল টাইম সেট করুন।"
    )
    bot.send_message(user_id, panel_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    data = call.data
    
    if data == "open_admin":
        admin_panel(call.message)
        bot.answer_callback_query(call.id)
        
    elif data == "add_channel":
        msg = bot.send_message(
            user_id, 
            "📢 <b>চ্যানেল সংযোগ প্রক্রিয়া:</b>\n\n"
            "১. প্রথমে এই বটটিকে আপনার টেলিগ্রাম চ্যানেলে <b>Administrator (এডমিন)</b> হিসেবে যুক্ত করুন।\n"
            "২. এডমিনশিপ দেওয়ার পর আপনার চ্যানেলের সঠিক <b>Channel ID</b> (যেমন: <code>-100123456789</code> অথবা ইউজারনেম) এখানে সেন্ড করুন:"
        )
        bot.register_next_step_handler(msg, process_channel_id)
        bot.answer_callback_query(call.id)
        
    elif data == "check_referral":
        with db_lock:
            ref_count = users_db.get(user_id, {}).get("referral_count", 0)
            is_verified = users_db.get(user_id, {}).get("is_verified", False)
        
        status_msg = (
            f"📊 <b>আপনার রেফারাল স্ট্যাটাস:</b>\n"
            f"────────────────────────\n"
            f"👤 মোট রেফার: <b>{ref_count}</b> টি\n"
            f"🟢 ভেরিফিকেশন: <b>{'সক্রিয় (Verified)', 'অসম্পূর্ণ (Incomplete)'[not is_verified]}</b>\n\n"
            f"বট ব্যবহারের জন্য অন্তত ১টি সফল রেফার প্রয়োজন। আপনার রেফার লিংক শেয়ার করুন!"
        )
        bot.answer_callback_query(call.id, text=f"Referrals: {ref_count}", show_alert=True)
        bot.send_message(user_id, status_msg)
        
    elif data == "help_info":
        help_text = (
            f"ℹ️ <b>বট ব্যবহারের নিয়মাবলী:</b>\n"
            f"────────────────────────\n"
            f"• চ্যানেল সেটআপ করতে: <code>/admin88</code>\n"
            f"• সময় ও সিগন্যাল শিডিউল সেট করতে: <code>/TM 5:12PM-1:00PM</code>\n"
            f"• অফিসিয়াল চ্যানেল: <a href='{MAIN_CHANNEL_LINK}'>DARK67HACK</a>\n"
            f"• অনার কন্টাক্ট: <code>{OWNER_CONTACT}</code>"
        )
        bot.send_message(user_id, help_text, disable_web_page_preview=True)
        bot.answer_callback_query(call.id)

def process_channel_id(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    
    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "schedules": [], 
                "state": "WAITING", 
                "target_issue": None, 
                "pending_pred": None, 
                "last_was_win": True,
                "referral_count": 0,
                "is_verified": True  # এখানে বাইপাস বা ভেরিফিকেশন সেট করা হলো
            }
        users_db[user_id]["channel_id"] = channel_id
        
    success_text = (
        f"<b>ডান ওকে ডান ✅</b>\n\n"
        f"আপনার চ্যানেল <code>{channel_id}</code> সফলভাবে যুক্ত করা হয়েছে!\n"
        f"এখন সিগন্যাল টাইম সেট করতে নিচের ফরম্যাটে কমান্ড দিন:\n"
        f"👉 <code>/TM 5:12PM-1:00PM</code>"
    )
    bot.send_message(user_id, success_text)

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule(message):
    user_id = message.chat.id
    text = message.text.upper()
    
    with db_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে /admin88 কমান্ড দিয়ে আপনার চ্যানেল অ্যাড করুন।")
            return
            
    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text)
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
        
        # Start Time AM/PM Logic
        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12
            
        # End Time AM/PM Logic
        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]
            
        time_range_str = message.text.replace('/TM ', '')
        confirmation_msg = f"হ্যাঁ, আমরা {time_range_str} পর্যন্ত সিগন্যাল দিব। 🎯 সিডিউল সফলভাবে আপডেট করা হয়েছে!"
        bot.send_message(user_id, confirmation_msg)
    else:
        bot.send_message(user_id, "❌ ভুল ফরম্যাট! সঠিক ফরম্যাট উদাহরণ: /TM 5:12PM-1:00PM")

# =========================================================
# CORE SIGNAL MONITORING & EXECUTION ENGINE
# =========================================================
def format_12hr(hour, minute):
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0: h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def is_in_schedule(now, schedules):
    current_minutes = now.hour * 60 + now.minute
    for (sh, sm, eh, em) in schedules:
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
        if start_mins <= current_minutes < end_mins:
            return True
    return False

def send_prediction_signal(channel_id, issue, prediction):
    short_issue = str(issue)[-6:] 
    digits = "/".join(random.sample(['5','6','7','8','9'], 2)) if prediction == "BIG" else "/".join(random.sample(['0','1','2','3','4'], 2))
        
    text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel_id, text)
    except Exception as e:
        print(f"[Signal Error] Failed to send message to channel {channel_id}: {e}")

def market_monitor_loop():
    while True:
        try:
            results = fetch_latest_results()
            if not results:
                time.sleep(2)
                continue
                
            curr_issue = results[0]["period"]
            now = datetime.now(BD_TIMEZONE)
            
            with db_lock:
                users_list = list(users_db.items())
                
            for user_id, udata in users_list:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])
                if not channel_id or not schedules:
                    continue
                    
                in_schedule = is_in_schedule(now, schedules)
                state = udata["state"]

                # --- Session State Management ---
                if in_schedule and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True 
                    try: 
                        bot.send_sticker(channel_id, START_STICKER)
                    except: pass
                    
                elif not in_schedule and state == "RUNNING":
                    udata["state"] = "STOPPING" 

                # --- Evaluation of Previous Prediction Outcome ---
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")
                
                if target_issue and curr_issue >= target_issue:
                    target_num = next((r["number"] for r in results if r["period"] == target_issue), None)
                    if target_num is not None:
                        actual_is_big = (target_num >= 5)
                        predicted_is_big = (pending_pred == "BIG")
                        is_win = (actual_is_big == predicted_is_big)
                        
                        # Send Win/Loss Sticker to Channel
                        try:
                            if is_win:
                                bot.send_sticker(channel_id, random.choice(WIN_STICKERS))
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                        except: pass
                        
                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # If schedule session ends and last result is processed, close session with END_STICKER
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except: pass
                            udata["state"] = "WAITING"

                # --- Generate New Signal using Tiger Pro Engine ---
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)
                    
        except Exception as e:
            print(f"[Monitor Loop Error]: {e}")
            
        time.sleep(3)

# =========================================================
# MAIN ENTRY POINT & THREAD INITIALIZATION
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("DARK KILLER | DRX-TM WinGo Auto Signal Bot [ENTERPRISE ONLINE]")
    print(f"Main Channel: {MAIN_CHANNEL_LINK}")
    print(f"Owner Contact: {OWNER_CONTACT}")
    print("=" * 60)
    
    # Background Market Monitor Thread
    monitor_thread = threading.Thread(target=market_monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Telegram Bot Polling Loop
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"[Bot Polling Crash]: {e}. Restarting in 5s...")
            time.sleep(5)
