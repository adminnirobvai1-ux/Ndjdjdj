# -*- coding: utf-8 -*-
"""
DRX-TM AUTO PREDICTION & INTEGRATED LIVE ENGINE
- Features:
    * Auto dependency package installer on initial run.
    * Integrated Telethon Userbot Session (Creates Live / Stays in Live / Unmutes).
    * Multi-user /admin88 interactive channel registration flow.
    * Custom schedule via /TM without broadcasting to channel.
    * Tiger Pro Deep Analytics Engine (Calculated strictly over 10 rounds).
    * Dynamic Win/Loss stickers and End Session sticker on winning transition.
"""

import sys
import subprocess
import os

# ================= 0. অটো প্যাকেজ ইন্সটলার =================
REQUIRED_PACKAGES = ["requests", "telebot", "telethon"]

def install_and_import():
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[!] Package '{pkg}' missing. Installing automatically...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_and_import()

import time
import random
import re
import threading
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter
import telebot
from telebot import types
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import (
    CreateGroupCallRequest,
    JoinGroupCallRequest,
    EditGroupCallParticipantRequest,
    GetGroupParticipantsRequest,
    LeaveGroupCallRequest
)
from telethon.tl.types import InputGroupCall, DataJSON
from telethon.tl import functions, types as tl_types
from telethon.errors import FloodWaitError

# ================= 1. কনফিগারেশন ও ক্রেডেনশিয়ালস =================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# Telethon Userbot ক্রেডেনশিয়াল
API_ID = 32054831
API_HASH = '89fc23d0ff6763a53004996fe0c6cab2'
SESSION_STRING = '1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ='

# স্টিকার আইডিসমূহ
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

# গ্লোবাল ক্লায়েন্ট ও লকিং
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
users_db = {}
db_lock = threading.Lock()

# ================= 2. TELETHON লাইভ স্ট্রিম হেল্পারস =================
user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
live_loop_async = None

def make_sdp():
    s = random.randint(100000000, 4294967295)
    s2 = random.randint(100000000, 4294967295)
    fp = ':'.join(f'{random.randint(0,255):02X}' for _ in range(32))
    pw = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=22))
    uf = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
    cn = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
    ms = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=36))
    import json
    return json.dumps({
        "fingerprints": [{"hash": "sha-256", "setup": "actpass", "fingerprint": fp}],
        "pwd": pw, "ufrag": uf, "ssrc": s,
        "ssrc-groups": [{"semantics": "FID", "sources": [s, s2]}],
        "sources": {str(s): {"cname": cn, "msid": f"{ms} {ms}a0"}},
    })

async def resolve_target_channel(channel_id):
    try:
        try:
            return await user_client.get_entity(int(channel_id))
        except ValueError:
            return await user_client.get_entity(channel_id)
    except Exception as e:
        print(f"[!] Error resolving channel entity {channel_id}: {e}")
        return None

async def start_channel_live(channel_id):
    """চ্যানেলে লাইভ স্ট্রিম স্টার্ট করা এবং কলে জয়েন করে কানেক্ট থাকা"""
    try:
        entity = await resolve_target_channel(channel_id)
        if not entity:
            return False
            
        # অ্যাক্টিভ কল চেক করা
        full = await user_client(functions.channels.GetFullChannelRequest(entity))
        active_call = full.full_chat.call
        
        if not active_call:
            print(f"[+] Starting new Live Stream in: {channel_id}")
            await user_client(CreateGroupCallRequest(
                peer=entity,
                random_id=random.randint(100000, 9999999),
                title="🔴 Live Signal Room"
            ))
            await asyncio.sleep(2)
            full = await user_client(functions.channels.GetFullChannelRequest(entity))
            active_call = full.full_chat.call

        if active_call:
            call_input = InputGroupCall(id=active_call.id, access_hash=active_call.access_hash)
            me = await user_client.get_me()
            join_as = await user_client.get_input_entity(me)
            
            # লাইভে জয়েন করা
            await user_client(JoinGroupCallRequest(
                call=call_input,
                join_as=join_as,
                muted=True,
                video_stopped=True,
                params=DataJSON(data=make_sdp())
            ))
            print(f"[+] Successfully joined and holding Live Call in {channel_id}")
            return True
    except Exception as e:
        print(f"[-] Live Stream error for {channel_id}: {e}")
    return False

def trigger_start_live(channel_id):
    if live_loop_async and live_loop_async.is_running():
        asyncio.run_coroutine_threadsafe(start_channel_live(channel_id), live_loop_async)

# ================= 3. TIGER PRO ENGINE (10 Results Base) =================
def calculate_tiger_pro(market_records):
    """টাইগার প্রো - ঠিক ১০টি রাউন্ডের ডেটার ভিত্তিতে মুভিং এভারেজ ও সাইজ নির্ধারণ"""
    if len(market_records) < 10:
        return "BIG"
    
    # ঠিক ১০টি ফলাফল সংগ্রহ
    recent_10 = market_records[:10]
    recent_10_nums = [x["number"] for x in recent_10]
    last_num = recent_10_nums[0]
    avg_10 = sum(recent_10_nums) / 10.0
    
    # টাইগার প্রো ট্রেন্ড লজিক
    if avg_10 > 5.0:
        pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"
        
    return pred_size

# ================= 4. API & ডেটা ফেচার =================
def fetch_latest_results():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 10} # শুধুমাত্র ১০টি রেজাল্ট
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
            for item in issue_list[:10]: # ১০টি নিশ্চিত করা
                issue = str(item.get('issueNumber', item.get('issue', '')))
                num = item.get('number', item.get('result', -1))
                if issue and num != -1:
                    parsed.append({"period": issue, "number": int(num)})
            return parsed
    except Exception as e:
        print(f"[API Fetch Error] {e}")
    return []

# ================= 5. বট কমান্ড ও ইন্টারেক্টিভ প্যানেল =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "স্বাগতম! চ্যানেল সেটআপ ও এডমিন অপশনের জন্য /admin88 কমান্ড দিন।")

@bot.message_handler(commands=['admin88'])
def admin_panel(message):
    """যেকোনো ব্যবহারকারীর জন্য ইন্টারেক্টিভ এডমিন প্যানেল"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    btn_help = types.InlineKeyboardButton("ℹ️ Help", callback_data="help")
    markup.add(btn_add, btn_help)
    bot.send_message(
        message.chat.id, 
        "<b>ADMIN CONTROL PANEL</b>\n\nচ্যানেলে অটো সিগন্যাল ও লাইভ চালাতে নিচের অপশন নির্বাচন করুন:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "add_channel":
        msg = bot.send_message(
            call.message.chat.id, 
            "📌 প্রথমে বটটিকে আপনার চ্যানেলে <b>Admin</b> বানান।\nএরপর চ্যানেলের আইডি (যেমন: -100123456789) বা ইউজারনেম পাঠান:"
        )
        bot.register_next_step_handler(msg, process_channel_id)
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "সিগন্যাল সময় সেট করার নিয়ম:\n/TM 10:30AM-1:00PM লিখে মেসেজ দিন।")

def process_channel_id(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {"schedules": [], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True}
        users_db[user_id]["channel_id"] = channel_id
        
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅\nএখন সিগন্যালের সময় সেট করতে লিখুন:\n<code>/TM 10:30AM-1:00PM</code>")

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
        
        # Start Time
        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12
            
        # End Time
        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]
            
        # চ্যানেলে কোনো মেসেজ না দিয়ে কেবল ইউজারকে কনফার্ম করা
        clean_time = message.text.replace('/TM', '').strip()
        bot.send_message(user_id, f"✅ হ্যাঁ, আমরা {clean_time} পর্যন্ত সিগন্যাল দিব।")
    else:
        bot.send_message(user_id, "ভুল ফরম্যাট! সঠিক ফরম্যাট: /TM 10:30AM-1:00PM")

# ================= 6. প্রেডিকশন ব্রডকাস্ট ও মনিটরিং লুপ =================
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
        print(f"[-] Signal Send Failed ({channel_id}): {e}")

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

                # শিডিউলের সময় হলে লাইভ স্টার্ট ও সেশন অন
                if in_schedule and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except: pass
                    # স্বয়ংক্রিয় লাইভ স্ট্রিম চালু
                    trigger_start_live(channel_id)
                    
                elif not in_schedule and state == "RUNNING":
                    udata["state"] = "STOPPING"

                # রেজাল্ট চেক ও স্টিকার সেন্ড
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
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                        except: pass
                        
                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # উইন হওয়ার পর যদি সেশন শেষ হওয়ার কথা থাকে তবে ক্লোজ স্টিকার সেন্ড
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except: pass
                            udata["state"] = "WAITING"

                # নতুন প্রেডিকশন প্রদান (টাইগার প্রো লজিক)
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)
                    
        except Exception as e:
            print(f"[Error in Monitor Loop]: {e}")
            
        time.sleep(3)

# ================= 7. থ্রেড রানার ও মূল ইঞ্জিন =================
def run_telethon_loop():
    global live_loop_async
    live_loop_async = asyncio.new_event_loop()
    asyncio.set_event_loop(live_loop_async)
    
    async def run_userbot():
        await user_client.start()
        print("[+] Telethon Userbot Connected and Waiting for Live calls...")
        
        # অটো আনমিউট ইভেন্ট লিসেনার
        @user_client.on(tl_types.UpdateGroupCallParticipants)
        async def auto_unmute(update):
            for participant in update.participants:
                if getattr(participant, 'muted', False):
                    try:
                        await user_client(EditGroupCallParticipantRequest(
                            call=update.call,
                            participant=participant.peer,
                            muted=False
                        ))
                    except: pass
                    
        while True:
            await asyncio.sleep(1)

    live_loop_async.run_until_complete(run_userbot())

if __name__ == "__main__":
    print("=" * 60)
    print("DRX-TM AUTO LIVE & PREDICTION ENGINE STARTED")
    print("=" * 60)

    # ১. টেলিথন ক্লায়েন্ট থ্রেড
    threading.Thread(target=run_telethon_loop, daemon=True).start()

    # ২. মার্কেট মনিটরিং থ্রেড
    threading.Thread(target=market_monitor_loop, daemon=True).start()

    # ৩. টেলিগ্রাম বট পোলিং
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"[Bot Polling Crashed]: {e}. Restarting in 5s...")
            time.sleep(5)
