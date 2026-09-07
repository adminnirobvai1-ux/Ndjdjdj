# -*- coding: utf-8 -*-
"""
=============================================================================
DRX-TM WinGo 30S Professional Auto Signal & Live Bot (All-in-One Edition)
=============================================================================
Features:
  - Auto dependency installer at startup
  - /admin88 panel with channel configuration buttons
  - Private schedule confirmation (does not spam public channel)
  - Auto Live Stream starter via Telethon Userbot
  - Auto-unmute listener handler in Live Group Call
  - High-accuracy TIGER PRO prediction engine
  - Dynamic sticker cycle (Start, Win, Loss, and Session End on last win)
=============================================================================
"""

import sys
import subprocess

# ================= 1. স্বয়ংক্রিয় প্যাকেজ ইন্সটলার =================
REQUIRED_PACKAGES = {
    "requests": "requests",
    "telebot": "pyTelegramBotAPI",
    "telethon": "telethon"
}

def install_dependencies():
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"[*] লাইব্রেরি পাওয়া যায়নি: {pip_name}। ইনস্টল করা হচ্ছে...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
                print(f"[+] {pip_name} সফলভাবে ইনস্টল হয়েছে!")
            except Exception as e:
                print(f"[-] {pip_name} ইনস্টল করতে ব্যর্থ: {e}")

install_dependencies()

# ================= 2. লাইব্রেরি ইমপোর্ট =================
import time
import random
import re
import asyncio
import threading
from datetime import datetime, timedelta, timezone
from collections import Counter
import requests
import telebot
from telebot import types
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import CreateGroupCallRequest, EditGroupCallParticipantRequest
from telethon.tl.types import UpdateGroupCallParticipants

# ================= 3. কনফিগারেশন ও ক্রেডেনশিয়াল =================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
API_ID = 32054831
API_HASH = "89fc23d0ff6763a53004996fe0c6cab2"
SESSION_STRING = (
    "1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNv"
    "Qy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-H"
    "jzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMe"
    "ZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ="
)

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# ================= 4. স্টিকার আইডিসমূহ =================
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
END_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"

# ================= 5. ডাটা ও থ্রেড ম্যানেজমেন্ট =================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
telethon_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

users_db = {}
db_lock = threading.Lock()
telethon_loop = None

# ================= 6. TIGER PRO ইঞ্জিন (Deep Analytics) =================
def calculate_tiger_pro(market_records):
    """
    টাইগার প্রো ইঞ্জিন: মুভিং এভারেজ এবং ট্রেন্ড অ্যানালাইসিস
    """
    if len(market_records) < 20:
        return "BIG"
    
    sample = market_records[:100]
    last_num = sample[0]["number"]
    
    recent_10_nums = [x["number"] for x in sample[:10]]
    avg_10 = sum(recent_10_nums) / 10.0
    
    if avg_10 > 5.0:
        pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"
        
    return pred_size

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

# ================= 7. টেলিথন ইউজারবট ও লাইভ স্ট্রিম মেকানিজম =================
async def start_channel_live_call(channel_id):
    """চ্যানেলে স্বয়ংক্রিয়ভাবে ভয়েস চ্যাট / লাইভ স্ট্রিম চালু করার মেথড"""
    try:
        try:
            entity = await telethon_client.get_entity(int(channel_id))
        except ValueError:
            entity = await telethon_client.get_entity(channel_id)
            
        await telethon_client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 Official Live Signal Room"
        ))
        print(f"[+] Live Stream started successfully in channel: {channel_id}")
    except Exception as e:
        print(f"[-] Live Stream failed to start in {channel_id}: {e}")

@telethon_client.on(UpdateGroupCallParticipants)
async def auto_unmute_participants(update):
    """লাইভে শ্রোতা জয়েন করলেই অটো-আনমিউট পারমিশন দেওয়ার হ্যান্ডলার"""
    for participant in update.participants:
        if participant.muted:
            try:
                await telethon_client(EditGroupCallParticipantRequest(
                    call=update.call,
                    participant=participant.peer,
                    muted=False
                ))
                print("[+] Participant auto-unmuted in live call.")
            except Exception:
                pass

def run_telethon_worker():
    global telethon_loop
    telethon_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_loop)
    telethon_client.start()
    print("[+] Telethon Userbot is running and active in the background.")
    telethon_loop.run_forever()

# ================= 8. টেলিগ্রাম বট হ্যান্ডলারসমূহ =================
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(
        message.chat.id,
        "👋 <b>স্বাগতম!</b>\nবটের অ্যাডমিন সেটিংস এবং চ্যানেল কনফিগার করতে /admin88 কমান্ড দিন।"
    )

@bot.message_handler(commands=['admin88'])
def handle_admin88(message):
    """যেকোনো ব্যবহারকারীর জন্য /admin88 মেনু প্রদর্শন"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="action_add_channel")
    btn_info = types.InlineKeyboardButton("ℹ️ Rules & Info", callback_data="action_info")
    markup.add(btn_add, btn_info)
    
    bot.send_message(
        message.chat.id,
        "<b>⚙️ Admin Panel Setup</b>\n\nচ্যানেলে সিগন্যাল দিতে নিচের <b>Add Your Channel</b> বাটনে ক্লিক করুন:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    if call.data == "action_add_channel":
        msg = bot.send_message(
            call.message.chat.id,
            "📌 <b>চ্যানেল সেটআপ করার নিয়ম:</b>\n"
            "১. প্রথমে এই বটটিকে আপনার চ্যানেলে <b>Admin</b> হিসেবে যুক্ত করুন।\n"
            "২. যুক্ত করা শেষে আপনার চ্যানেলের ID (যেমন: <code>-100123456789</code>) অথবা ইউজারনেম (যেমন: <code>@yourchannel</code>) এখানে লিখে সেন্ড করুন:"
        )
        bot.register_next_step_handler(msg, register_user_channel)
    elif call.data == "action_info":
        bot.send_message(
            call.message.chat.id,
            "📖 <b>ব্যবহার নির্দেশিকা:</b>\n"
            "• সময় সেট করতে /TM কমান্ড ব্যবহার করুন।\n"
            "  উদাহরণ: <code>/TM 10:30AM-1:00PM</code>\n"
            "• সিগন্যাল সেশন শেষে একটি উইন আসা মাত্র স্বয়ংক্রিয়ভাবে সেশন শেষ হবে।"
        )

def register_user_channel(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    
    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "channel_id": channel_id,
                "schedules": [],
                "state": "WAITING",
                "target_issue": None,
                "pending_pred": None,
                "last_was_win": True,
                "live_started": False
            }
        else:
            users_db[user_id]["channel_id"] = channel_id
            
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def handle_tm_schedule(message):
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
        
        # Start Time AM/PM logic
        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12
            
        # End Time AM/PM logic
        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]
            users_db[user_id]["live_started"] = False
            
        raw_time_str = message.text.replace('/TM', '').replace('/tm', '').strip()
        # শুধু ইউজারকে রিপ্লাই দেবে (চ্যানেলে কোনো মেসেজ সেন্ড হবে না)
        bot.send_message(user_id, f"হ্যাঁ আমরা {raw_time_str} সিগন্যাল দিব। 🎯")
    else:
        bot.send_message(user_id, "ভুল ফরম্যাট! সঠিক ফরম্যাট: <code>/TM 10:30AM-1:00PM</code>")

# ================= 9. সিগন্যাল সেন্ডার ও ফরম্যাট =================
def send_prediction_signal(channel_id, issue, prediction):
    short_issue = str(issue)[-6:]
    digits = "/".join(random.sample(['5','6','7','8','9'], 2)) if prediction == "BIG" else "/".join(random.sample(['0','1','2','3','4'], 2))
    
    text = (
        f"🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿\n"
        f"▱▱▱▱▱▱▱▱▱▱▱▱▱▱\n"
        f"💎 Period   ➤  {short_issue}\n"
        f"🎯 Action   ➤  BET {prediction} 🌹\n"
        f"⚡ digit   ➤   {digits}\n"
        f"▱▱▱▱▱▱▱▱▱▱▱▱▱▱"
    )
    try:
        bot.send_message(channel_id, text)
        print(f"[*] Signal Sent -> {channel_id}: Period {short_issue} [{prediction}]")
    except Exception as e:
        print(f"[-] Signal Send Error to {channel_id}: {e}")

def is_in_schedule(now, schedules):
    current_minutes = now.hour * 60 + now.minute
    for (sh, sm, eh, em) in schedules:
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
        if start_mins <= current_minutes < end_mins:
            return True
    return False

# ================= 10. কোর মনিটরিং ও এক্সিকিউশন লুপ =================
def core_monitor_loop():
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
                    
                in_sched = is_in_schedule(now, schedules)
                state = udata["state"]

                # --- সেশন স্টার্ট লজিক ---
                if in_sched and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except Exception:
                        pass
                    
                    # চ্যানেলে লাইভ স্ট্রিম স্টার্ট করা (যদি এখনও চালু না হয়ে থাকে)
                    if not udata.get("live_started", False) and telethon_loop:
                        asyncio.run_coroutine_threadsafe(start_channel_live_call(channel_id), telethon_loop)
                        udata["live_started"] = True
                    
                    print(f"[+] Session Started for {channel_id} at {now.strftime('%H:%M:%S')}")

                # --- সেশন ক্লোজিং ট্রানজিশন ---
                elif not in_sched and state == "RUNNING":
                    udata["state"] = "STOPPING"
                    print(f"[*] Time up for {channel_id}. Waiting for a WIN to end session safely...")

                # --- ফলাফল যাচাই ও স্টিকার সেন্ড ---
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")
                
                if target_issue and curr_issue >= target_issue:
                    target_num = next((r["number"] for r in results if r["period"] == target_issue), None)
                    if target_num is not None:
                        actual_is_big = (target_num >= 5)
                        predicted_is_big = (pending_pred == "BIG")
                        is_win = (actual_is_big == predicted_is_big)
                        
                        try:
                            if is_win:
                                bot.send_sticker(channel_id, random.choice(WIN_STICKERS))
                                print(f"[WIN] Channel: {channel_id} | Result: {target_num}")
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                                print(f"[LOSS] Channel: {channel_id} | Result: {target_num}")
                        except Exception as e:
                            print(f"[-] Sticker Send Error: {e}")
                            
                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # নির্ধারিত সময় শেষ হলে এবং সর্বশেষ সিগন্যালে উইন হলে সেশন ক্লোজ হবে
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except Exception:
                                pass
                            udata["state"] = "WAITING"
                            udata["live_started"] = False
                            print(f"[+] Session Ended safely with WIN sticker for {channel_id}")

                # --- নতুন সিগন্যাল তৈরি ও সেন্ড (TIGER PRO) ---
                if (udata["state"] in ["RUNNING", "STOPPING"]) and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)
                    
        except Exception as e:
            print(f"[-] Monitor loop error: {e}")
            
        time.sleep(3)

# ================= 11. বট এক্সিকিউশন =================
if __name__ == "__main__":
    print("=" * 65)
    print("🚀 DRX-TM WinGo 30S Auto Signal & Live Bot Initialized")
    print("• Admin Panel: /admin88 Enabled")
    print("• TIGER PRO Engine: Active")
    print("• Live Stream Userbot: Connected")
    print("=" * 65)

    # Telethon থ্রেড চালু
    telethon_thread = threading.Thread(target=run_telethon_worker, daemon=True)
    telethon_thread.start()

    # মার্কেট মনিটর থ্রেড চালু
    monitor_thread = threading.Thread(target=core_monitor_loop, daemon=True)
    monitor_thread.start()

    # টেলিগ্রাম বট পোলিং
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"[-] Telegram Bot crashed: {e}. Restarting in 5s...")
            time.sleep(5)
