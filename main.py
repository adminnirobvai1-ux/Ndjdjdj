# -*- coding: utf-8 -*-
"""
WinGo 30S Professional Auto Signal & Telethon Live Stream Controller
Combined Engine: TIGER PRO Analytics + Telethon Userbot Live + Bot Admin Management
"""

import os
import sys
import time
import random
import re
import asyncio
import threading
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter

import telebot
from telebot import types

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import CreateGroupCallRequest, EditGroupCallParticipantRequest
from telethon.tl.types import UpdateGroupCallParticipants

# =========================================================
# ১. কনফিগারেশন ও ক্রেডেনশিয়াল
# =========================================================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"

API_ID = 32054831
API_HASH = "89fc23d0ff6763a53004996fe0c6cab2"
SESSION_STRING = "1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ="

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# =========================================================
# ২. স্টিকার কালেকশন
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
# ৩. গ্লোবাল ডাটাবেস ও অবজেক্ট ইনিশিয়ালাইজেশন
# =========================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
telethon_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

telethon_loop = None
db_lock = threading.Lock()

# স্ট্রাকচার:
# users_db = {
#     chat_id: {
#         "channel_id": "...",
#         "schedules": [(sh, sm, eh, em)],
#         "state": "WAITING" / "RUNNING" / "STOPPING",
#         "target_issue": None,
#         "pending_pred": None,
#         "last_was_win": True,
#         "live_active": False
#     }
# }
users_db = {}

# =========================================================
# ৪. TIGER PRO অ্যানালিটিক্স ইঞ্জিন
# =========================================================
def calculate_tiger_pro(market_records):
    """টাইগার প্রো - ডিপ ট্রেন্ড ও মুভিং এভারেজ অ্যানালাইজার"""
    if len(market_records) < 10:
        return "BIG"
    
    sample = market_records[:100]
    last_num = sample[0]["number"]
    
    recent_10_nums = [x["number"] for x in sample[:10]]
    avg_10 = sum(recent_10_nums) / float(len(recent_10_nums))
    
    if avg_10 > 4.5:
        pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"
        
    return pred_size

# =========================================================
# ৫. লাইভ মার্কেট ডাটা ফেচার
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
    except Exception as e:
        print(f"[Fetch Error] Data retrieve failed: {e}")
    return []

# =========================================================
# ৬. টেলিথন ইউজারবট (অটো লাইভ ও অটো আনমিউট)
# =========================================================
@telethon_client.on(events.Raw)
async def auto_unmute_participants(update):
    """লাইভে কেউ যুক্ত হলে তাকে স্বয়ংক্রিয়ভাবে আনমিউট করবে"""
    if isinstance(update, UpdateGroupCallParticipants):
        for participant in update.participants:
            if getattr(participant, 'muted', False):
                try:
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=update.call,
                        participant=participant.peer,
                        muted=False
                    ))
                    print("[+] Auto-unmuted participant in live stream.")
                except Exception:
                    pass

async def async_start_live(channel_id):
    """চ্যানেলে লাইভ স্ট্রিম তৈরি করার ফাংশন"""
    try:
        try:
            target_peer = int(channel_id)
        except ValueError:
            target_peer = channel_id
            
        entity = await telethon_client.get_entity(target_peer)
        await telethon_client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 DRX-TM Official Live Signals"
        ))
        print(f"[Telethon] Live started successfully on {channel_id}!")
        return True
    except Exception as e:
        print(f"[Telethon Error] Live start failed on {channel_id}: {e}")
        return False

def trigger_start_live(channel_id):
    """সিঙ্ক থ্রেড থেকে অ্যাসিনক্রোনাস টেলিথন লাইভ চালু করা"""
    if telethon_loop and telethon_loop.is_running():
        asyncio.run_coroutine_threadsafe(async_start_live(channel_id), telethon_loop)

def start_telethon_thread():
    """টেলিথন ক্লায়েন্ট চালানোর জন্য ডেডিকেটেড থ্রেড লুপ"""
    global telethon_loop
    telethon_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_loop)
    
    async def runner():
        await telethon_client.start()
        print("[+] Telethon Userbot is Online and Ready.")
        await telethon_client.run_until_disconnected()
        
    telethon_loop.run_until_complete(runner())

# =========================================================
# ৭. টেলিগ্রাম বট হ্যান্ডলার ও অ্যাডমিন প্যানেল
# =========================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "স্বাগতম! চ্যানেল সেটআপ করতে /admin88 কমান্ড দিন।")

@bot.message_handler(commands=['admin88'])
def handle_admin88(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    btn_help = types.InlineKeyboardButton("ℹ️ Help / নিয়মাবলী", callback_data="admin_help")
    markup.add(btn_add, btn_help)
    
    bot.send_message(
        message.chat.id,
        "<b>⚙️ এডমিন কন্ট্রোল প্যানেল</b>\n\n"
        "আপনার চ্যানেলে সিগন্যাল ও অটো-লাইভ সেটআপ করতে নিচের বাটনে চাপুন:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "add_channel":
        msg = bot.send_message(
            call.message.chat.id,
            "<b>ধাপ ১:</b> প্রথমে এই বট এবং আপনার ইউজারবটকে আপনার চ্যানেলে <b>Admin</b> পারমিশন দিন।\n\n"
            "<b>ধাপ ২:</b> আপনার চ্যানেলের ইউজারনেম (যেমন: <code>@channelusername</code>) অথবা চ্যানেল আইডি (যেমন: <code>-100123456789</code>) এখানে লিখে সেন্ড করুন:"
        )
        bot.register_next_step_handler(msg, process_channel_registration)
    elif call.data == "admin_help":
        help_text = (
            "<b>💡 ব্যবহারের নিয়ম:</b>\n"
            "১. চ্যানেল অ্যাড করার পর সময় নির্ধারণ করতে <code>/TM</code> কমান্ড ব্যবহার করুন।\n"
            "২. ফরম্যাট: <code>/TM 10:30AM-1:00PM</code> অথবা <code>/TM 14:00-16:00</code>\n"
            "৩. নির্ধারিত সময়ে অটোমেটিক লাইভ শুরু হবে এবং সিগন্যাল চলবে।"
        )
        bot.send_message(call.message.chat.id, help_text)

def process_channel_registration(message):
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
                "live_active": False
            }
        users_db[user_id]["channel_id"] = channel_id
        
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule(message):
    user_id = message.chat.id
    text = message.text.upper()
    
    with db_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে প্রথমে /admin88 কমান্ড দিয়ে চ্যানেল যুক্ত করুন।")
            return
            
    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text)
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
        
        # Start Time ক্যালকুলেশন
        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12
            
        # End Time ক্যালকুলেশন
        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]
            
        # শুধুমাত্র ব্যবহারকারীকে জানানো হবে, চ্যানেলে মেসেজ যাবে না
        time_display = message.text.replace('/TM ', '').replace('/tm ', '')
        bot.send_message(user_id, f"হ্যাঁ, আমরা {time_display} থেকে সিগন্যাল দিব। 🎯")
    else:
        bot.send_message(user_id, "ভুল ফরম্যাট! সঠিক ফরম্যাট: /TM 10:30AM-1:00PM")

# =========================================================
# ৮. সিগন্যাল ব্রডকাস্ট ও টাইম ভ্যালিডেশন
# =========================================================
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
    if prediction == "BIG":
        digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2))
    else:
        digits = "/".join(random.sample(['0', '1', '2', '3', '4'], 2))
        
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
        print(f"[*] Signal Sent to {channel_id}: Period {short_issue} -> {prediction}")
    except Exception as e:
        print(f"[Error] Failed to send signal to {channel_id}: {e}")

# =========================================================
# ৯. মূল কোর মনিটরিং ও এক্সিকিউশন লুপ
# =========================================================
def market_monitor_loop():
    print("[+] Market Monitoring Engine Activated.")
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

                # ক. সেশন শুরু হওয়া
                if in_schedule and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except Exception as e:
                        print(f"Error sending start sticker: {e}")
                        
                    # স্বয়ংক্রিয় লাইভ স্ট্রিম শুরু
                    if not udata.get("live_active"):
                        trigger_start_live(channel_id)
                        udata["live_active"] = True
                        
                    print(f"[+] Started Session & Triggered Live for: {channel_id}")
                    
                # খ. শিডিউল শেষ হলে সেফ স্টপ স্টেটে যাওয়া
                elif not in_schedule and state == "RUNNING":
                    udata["state"] = "STOPPING"
                    print(f"[-] Session entering STOPPING mode for: {channel_id}")

                # গ. চলমান প্রেডিকশনের ফলাফল মূল্যায়ন
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
                                print(f"[WIN] Result: {target_num} matched with {pending_pred}")
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                                print(f"[LOSS] Result: {target_num} failed for {pending_pred}")
                        except Exception as e:
                            print(f"Sticker dispatch error: {e}")
                        
                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # উইন সম্পন্ন হলে এবং শিডিউল ওভার থাকলে ক্লোজ স্টিকার সেন্ড করে সেশন বন্ধ হবে
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except Exception as e:
                                print(f"End sticker error: {e}")
                            udata["state"] = "WAITING"
                            udata["live_active"] = False
                            print(f"[✓] Session Safely Finished on Win for {channel_id}")

                # ঘ. পরবর্তী রাউন্ডের জন্য TIGER PRO প্রেডিকশন তৈরি
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)
                    
        except Exception as e:
            print(f"[Loop Exception] {e}")
            
        time.sleep(2.5)

# =========================================================
# ১০. সিস্টেম লঞ্চার
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("   DRX-TM TIGER PRO & TELETHON AUTO LIVE SYSTEM ONLINE   ")
    print("=" * 60)
    
    # টেলিথন ক্লায়েন্ট থ্রেড শুরু
    th_userbot = threading.Thread(target=start_telethon_thread, daemon=True)
    th_userbot.start()
    
    # মার্কেট মনিটর ও অটোমেশন থ্রেড শুরু
    th_monitor = threading.Thread(target=market_monitor_loop, daemon=True)
    th_monitor.start()
    
    # টেলিগ্রাম বট লিসেনার
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=10)
        except Exception as e:
            print(f"[Bot Polling Crashed]: {e}. Reconnecting in 5s...")
            time.sleep(5)
