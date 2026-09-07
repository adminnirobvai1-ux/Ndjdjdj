# -*- coding: utf-8 -*-
"""
DRX-TM ADVANCED PREDICTION & INTEGRATED 24/7 AUTO LIVE ENGINE
Modules Included:
  - Auto dependency installer at runtime
  - Integrated Telethon Userbot Session (Live Stream Creation, Auto Unmute & Persistent Presence)
  - Interactive /admin88 Setup Panel & Quick-Trigger /ta Command
  - Tiger Pro Analytics Engine (Calculated strictly across 10 rounds of WinGo 30S)
  - Dynamic Prediction Broadcaster & Smart Win-Wait-End Sticker Routine
"""

import sys
import subprocess
import os

# ================= 0. প্রয়োজনীয় প্যাকেজ অটো-ইন্সটলার =================
REQUIRED_PACKAGES = ["requests", "pyTelegramBotAPI", "telethon"]

def auto_installer():
    for package in REQUIRED_PACKAGES:
        try:
            if package == "pyTelegramBotAPI":
                __import__("telebot")
            else:
                __import__(package)
        except ImportError:
            print(f"[*] Package '{package}' পাওয়া যায়নি। স্বয়ংক্রিয়ভাবে ইনস্টল হচ্ছে...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

auto_installer()

import time
import random
import re
import json
import threading
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter
import telebot
from telebot import types
from telethon import TelegramClient, events
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

# ================= 1. কনফিগারেশন ও আইডিসমূহ =================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
DEFAULT_CHANNEL = "@dark67hack"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# Telethon Userbot ক্রেডেনশিয়ালস
API_ID = 32054831
API_HASH = "89fc23d0ff6763a53004996fe0c6cab2"
SESSION_STRING = "1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ="

# স্টিকার আইডিসমূহ
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

live_loop_async = None
users_db = {}
db_lock = threading.Lock()

# ডিফল্ট চ্যানেল প্রি-লোড
users_db["default"] = {
    "channel_id": DEFAULT_CHANNEL,
    "schedules": [],
    "state": "WAITING",
    "target_issue": None,
    "pending_pred": None,
    "last_was_win": True,
    "in_live": False
}

# ================= 2. লাইভ স্ট্রিম SDP ও হেল্পার লজিক =================
def make_sdp():
    s = random.randint(100000000, 4294967295)
    s2 = random.randint(100000000, 4294967295)
    fp = ':'.join(f'{random.randint(0,255):02X}' for _ in range(32))
    pw = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=22))
    uf = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
    cn = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
    ms = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=36))
    return json.dumps({
        "fingerprints": [{"hash": "sha-256", "setup": "actpass", "fingerprint": fp}],
        "pwd": pw, "ufrag": uf, "ssrc": s,
        "ssrc-groups": [{"semantics": "FID", "sources": [s, s2]}],
        "sources": {str(s): {"cname": cn, "msid": f"{ms} {ms}a0"}},
    })

async def resolve_channel_entity(channel_target):
    try:
        try:
            return await user_client.get_entity(int(channel_target))
        except ValueError:
            return await user_client.get_entity(channel_target)
    except Exception as e:
        print(f"[-] Channel Resolve Error ({channel_target}): {e}")
        return None

async def start_and_hold_live(channel_target):
    """লাইভ শুরু করা এবং লাইভ কলে চুপচাপ কানেক্টেড থাকা"""
    try:
        entity = await resolve_channel_entity(channel_target)
        if not entity:
            return False

        full = await user_client(functions.channels.GetFullChannelRequest(entity))
        active_call = full.full_chat.call

        if not active_call:
            print(f"[+] Creating Group Call in {channel_target}...")
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

            # জয়েন করা এবং অবস্থান বজায় রাখা
            await user_client(JoinGroupCallRequest(
                call=call_input,
                join_as=join_as,
                muted=True,
                video_stopped=True,
                params=DataJSON(data=make_sdp())
            ))
            print(f"[+] Live Stream active and holding position in {channel_target}!")
            return True
    except Exception as e:
        print(f"[-] Live Start Error for {channel_target}: {e}")
    return False

def trigger_live(channel_target):
    if live_loop_async and live_loop_async.is_running():
        asyncio.run_coroutine_threadsafe(start_and_hold_live(channel_target), live_loop_async)

# ================= 3. টাইগার প্রো ইঞ্জিন (১০টি রাউন্ড বেসড) =================
def calculate_tiger_pro(market_records):
    """১০টি হিস্ট্রি রেজাল্টের ভিত্তিতে সুনির্দিষ্ট মুভিং এভারেজ ও সাইজ নির্ণয়"""
    if len(market_records) < 10:
        return "BIG"

    sample = market_records[:10]
    recent_nums = [x["number"] for x in sample]
    last_num = recent_nums[0]
    
    avg_10 = sum(recent_nums) / 10.0

    if avg_10 > 5.0:
        pred_size = "BIG" if recent_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_nums.count(last_num) < 3 else "BIG"

    return pred_size

# ================= 4. ডেটা ফেচিং লজিক =================
def fetch_latest_results():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 10}
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
            for item in issue_list[:10]:
                issue = str(item.get('issueNumber', item.get('issue', '')))
                num = item.get('number', item.get('result', -1))
                if issue and num != -1:
                    parsed.append({"period": issue, "number": int(num)})
            return parsed
    except Exception as e:
        print(f"[API Fetch Error] {e}")
    return []

# ================= 5. টেলিগ্রাম বট ইন্টারফেস ও কমান্ড =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "স্বাগতম! চ্যানেল সেট করতে <b>/admin88</b> দিন অথবা সিগন্যাল ও লাইভ সরাসরি চালু করতে <b>/ta</b> দিন।")

@bot.message_handler(commands=['ta'])
def manual_start_cmd(message):
    user_id = message.chat.id
    target_channel = DEFAULT_CHANNEL
    with db_lock:
        if user_id in users_db and users_db[user_id].get("channel_id"):
            target_channel = users_db[user_id]["channel_id"]
            users_db[user_id]["state"] = "RUNNING"
            users_db[user_id]["last_was_win"] = True
        else:
            users_db["default"]["state"] = "RUNNING"
            users_db["default"]["last_was_win"] = True

    try:
        bot.send_sticker(target_channel, START_STICKER)
    except: pass
    
    # লাইভ কল চালু ও হোল্ড
    trigger_live(target_channel)
    bot.reply_to(message, f"✅ চ্যানেল <b>{target_channel}</b>-এ লাইভ এবং সিগন্যাল সেশন শুরু করা হয়েছে!")

@bot.message_handler(commands=['admin88'])
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    btn_help = types.InlineKeyboardButton("ℹ️ Help / Info", callback_data="help")
    markup.add(btn_add, btn_help)
    bot.send_message(
        message.chat.id, 
        "<b>⚙️ ADMIN CONTROL PANEL</b>\n\nনিচের বাটন চেপে আপনার চ্যানেল কনফিগার করুন:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "add_channel":
        msg = bot.send_message(
            call.message.chat.id, 
            "📌 প্রথমে বটটিকে আপনার চ্যানেলে <b>Admin</b> পারমিশন দিন।\nএরপর চ্যানেলের ID (যেমন: -100123456789) বা ইউজারনেম পাঠান:"
        )
        bot.register_next_step_handler(msg, process_channel_id)
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "সময় নির্ধারণ করতে /TM কমান্ড ব্যবহার করুন। যেমন:\n/TM 10:30AM-1:00PM\nতাৎক্ষণিক চালাতে /ta দিন।")

def process_channel_id(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {"schedules": [], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True, "in_live": False}
        users_db[user_id]["channel_id"] = channel_id

    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅\nএখন সিগন্যালের সময় সেট করতে লিখুন:\n<code>/TM 10:30AM-1:00PM</code>")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule(message):
    user_id = message.chat.id
    text = message.text.upper()

    with db_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            users_db[user_id] = {"channel_id": DEFAULT_CHANNEL, "schedules": [], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True, "in_live": False}

    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text)
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)

        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12

        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]

        clean_time = message.text.replace('/TM', '').strip()
        bot.send_message(user_id, f"✅ হ্যাঁ, আমরা {clean_time} সময় অনুযায়ী নির্ধারিত চ্যানেলে সিগন্যাল ও লাইভ দিব।")
    else:
        bot.send_message(user_id, "ফরম্যাট ভুল! সঠিক উদাহরণ: /TM 10:30AM-1:00PM")

# ================= 6. প্রেডিকশন ব্রডকাস্ট ও মনিটরিং সাইকেল =================
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
        print(f"[-] Failed to send signal to {channel_id}: {e}")

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

            for user_key, udata in users_list:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])
                if not channel_id:
                    continue

                state = udata["state"]

                # শিডিউল ট্র্যাকিং
                if schedules:
                    in_schedule = is_in_schedule(now, schedules)
                    if in_schedule and state == "WAITING":
                        udata["state"] = "RUNNING"
                        udata["last_was_win"] = True
                        try:
                            bot.send_sticker(channel_id, START_STICKER)
                        except: pass
                        trigger_live(channel_id)
                    elif not in_schedule and state == "RUNNING":
                        udata["state"] = "STOPPING"

                # ফলাফল মূল্যায়ন
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

                        # সেশন সমাপ্তির লজিক (উইনে শেষ হবে)
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except: pass
                            udata["state"] = "WAITING"

                # নতুন প্রেডিকশন প্রদান (টাইগার প্রো ইঞ্জিন)
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)

        except Exception as e:
            print(f"[Monitor Loop Error]: {e}")

        time.sleep(3)

# ================= 7. টেলিথন ইউজারবট ও অটো-আনমিউট থ্রেড =================
def run_telethon_loop():
    global live_loop_async
    live_loop_async = asyncio.new_event_loop()
    asyncio.set_event_loop(live_loop_async)

    async def userbot_task():
        await user_client.start()
        print("[+] Telethon Userbot Connected and Persistent Listener Active.")

        # স্বয়ংক্রিয় আনমিউট হ্যান্ডলার
        @user_client.on(tl_types.UpdateGroupCallParticipants)
        async def auto_unmute_participant(update):
            for p in update.participants:
                if getattr(p, 'muted', False):
                    try:
                        await user_client(EditGroupCallParticipantRequest(
                            call=update.call,
                            participant=p.peer,
                            muted=False
                        ))
                    except: pass

        while True:
            await asyncio.sleep(1)

    live_loop_async.run_until_complete(userbot_task())

# ================= 8. প্রধান রানার =================
if __name__ == "__main__":
    print("=" * 60)
    print("DRX-TM LIVE & PREDICTION SYSTEM ONLINE")
    print(f"Active Channel Target: {DEFAULT_CHANNEL}")
    print("=" * 60)

    # টেলিথন থ্রেড রান
    threading.Thread(target=run_telethon_loop, daemon=True).start()

    # মার্কেট প্রেডিকশন মনিটর থ্রেড রান
    threading.Thread(target=market_monitor_loop, daemon=True).start()

    # টেলিগ্রাম বট পোলিং
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"[Polling Error]: {e}. Restarting...")
            time.sleep(5)
