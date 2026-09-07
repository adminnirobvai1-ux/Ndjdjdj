# -*- coding: utf-8 -*-
import sys
import subprocess
import os

# ================= 1. প্রয়োজনীয় প্যাকেজ অটো-ইন্সটলার =================
REQUIRED_PACKAGES = ["requests", "pyTelegramBotAPI", "telethon"]

def ensure_dependencies():
    for pkg in REQUIRED_PACKAGES:
        try:
            if pkg == "pyTelegramBotAPI":
                __import__("telebot")
            else:
                __import__(pkg)
        except ImportError:
            print(f"[*] Installing missing package: {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure_dependencies()

import time
import random
import re
import json
import threading
import asyncio
import requests
from datetime import datetime, timedelta, timezone
import telebot
from telebot import types
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import (
    CreateGroupCallRequest,
    JoinGroupCallRequest,
    EditGroupCallParticipantRequest
)
from telethon.tl.types import InputGroupCall, DataJSON
from telethon.tl import functions, types as tl_types

# ================= 2. ক্রেডেনশিয়াল ও কনফিগারেশন =================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
TARGET_CHANNEL = "@dark67hack"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

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
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
telethon_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

telethon_async_loop = None
bot_state = {
    "channel": TARGET_CHANNEL,
    "schedules": [],
    "status": "IDLE",  # IDLE, RUNNING, STOPPING
    "target_period": None,
    "current_pred": None,
    "live_active": False
}
state_lock = threading.Lock()

# ================= 3. লাইভ স্ট্রিম হ্যান্ডলার =================
def create_sdp_payload():
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

async def execute_live_start(channel_ref):
    try:
        try:
            entity = await telethon_client.get_entity(int(channel_ref))
        except ValueError:
            entity = await telethon_client.get_entity(channel_ref)

        full_channel = await telethon_client(functions.channels.GetFullChannelRequest(entity))
        active_call = full_channel.full_chat.call

        if not active_call:
            print(f"[+] Creating fresh Live Call in {channel_ref}...")
            await telethon_client(CreateGroupCallRequest(
                peer=entity,
                random_id=random.randint(100000, 9999999),
                title="🔴 Live Signal Room"
            ))
            await asyncio.sleep(2)
            full_channel = await telethon_client(functions.channels.GetFullChannelRequest(entity))
            active_call = full_channel.full_chat.call

        if active_call:
            call_obj = InputGroupCall(id=active_call.id, access_hash=active_call.access_hash)
            me = await telethon_client.get_me()
            join_peer = await telethon_client.get_input_entity(me)

            await telethon_client(JoinGroupCallRequest(
                call=call_obj,
                join_as=join_peer,
                muted=True,
                video_stopped=True,
                params=DataJSON(data=create_sdp_payload())
            ))
            print(f"[+] Userbot successfully entered Live Stream in {channel_ref} (Silent Mode).")
            with state_lock:
                bot_state["live_active"] = True
            return True
    except Exception as e:
        print(f"[-] Live Stream Error: {e}")
    return False

def trigger_live_stream():
    if telethon_async_loop and telethon_async_loop.is_running():
        asyncio.run_coroutine_threadsafe(execute_live_start(bot_state["channel"]), telethon_async_loop)

# ================= 4. টাইগার প্রো অ্যানালিটিক্স ও হিস্ট্রি =================
def get_tiger_prediction(records):
    if len(records) < 10:
        return "BIG"
    subset = records[:10]
    numbers = [r["number"] for r in subset]
    avg = sum(numbers) / 10.0
    latest = numbers[0]
    
    if avg > 5.0:
        return "BIG" if numbers.count(latest) < 3 else "SMALL"
    else:
        return "SMALL" if numbers.count(latest) < 3 else "BIG"

def fetch_market_data():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    try:
        res = requests.post(API_URL, json={"pageNumber": 1, "pageSize": 10}, headers=headers, timeout=6)
        data = res.json()

        def extract_items(obj):
            if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict) and ('issueNumber' in obj[0] or 'issue' in obj[0]):
                return obj
            elif isinstance(obj, dict):
                for val in obj.values():
                    found = extract_items(val)
                    if found: return found
            return None

        records = extract_items(data)
        if records:
            out = []
            for item in records[:10]:
                period = str(item.get('issueNumber', item.get('issue', '')))
                num = item.get('number', item.get('result', -1))
                if period and num != -1:
                    out.append({"period": period, "number": int(num)})
            return out
    except Exception as e:
        print(f"[-] API Fetch Error: {e}")
    return []

# ================= 5. সিগন্যাল ব্রডকাস্টার =================
def broadcast_signal(channel, period, pred):
    short_period = str(period)[-6:]
    digits = "/".join(random.sample(['5','6','7','8','9'], 2)) if pred == "BIG" else "/".join(random.sample(['0','1','2','3','4'], 2))
    
    msg = f"""🌿🍁🌿 {pred} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_period}
🎯 Action   ➤  BET {pred} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel, msg)
    except Exception as e:
        print(f"[-] Broadcast Error: {e}")

# ================= 6. ব্যাকগ্রাউন্ড মনিটরিং সাইকেল =================
def monitor_engine():
    while True:
        try:
            records = fetch_market_data()
            if not records:
                time.sleep(2)
                continue

            current_issue = records[0]["period"]
            now = datetime.now(BD_TIMEZONE)
            curr_minute = now.hour * 60 + now.minute

            with state_lock:
                status = bot_state["status"]
                target_channel = bot_state["channel"]
                schedules = bot_state["schedules"]

                # শিডিউল যাচাই
                if schedules:
                    active_now = any(s[0] * 60 + s[1] <= curr_minute < s[2] * 60 + s[3] for s in schedules)
                    if active_now and status == "IDLE":
                        bot_state["status"] = "RUNNING"
                        status = "RUNNING"
                        try:
                            bot.send_sticker(target_channel, START_STICKER)
                        except: pass
                        trigger_live_stream()
                    elif not active_now and status == "RUNNING":
                        bot_state["status"] = "STOPPING"
                        status = "STOPPING"

                # ফলাফল চেক
                target_period = bot_state["target_period"]
                pending_pred = bot_state["current_pred"]

                if target_period and current_issue >= target_period:
                    matched = next((r["number"] for r in records if r["period"] == target_period), None)
                    if matched is not None:
                        is_win = ((matched >= 5) == (pending_pred == "BIG"))
                        try:
                            if is_win:
                                bot.send_sticker(target_channel, random.choice(WIN_STICKERS))
                            else:
                                bot.send_sticker(target_channel, LOSS_STICKER)
                        except: pass

                        bot_state["target_period"] = None
                        bot_state["current_pred"] = None

                        if status == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(target_channel, END_STICKER)
                            except: pass
                            bot_state["status"] = "IDLE"

                # নতুন প্রেডিকশন রিলিজ
                if bot_state["status"] in ["RUNNING", "STOPPING"] and bot_state["target_period"] is None:
                    next_pred = get_tiger_prediction(records)
                    next_issue = str(int(current_issue) + 1)
                    bot_state["current_pred"] = next_pred
                    bot_state["target_period"] = next_issue
                    broadcast_signal(target_channel, next_issue, next_pred)

        except Exception as e:
            print(f"[-] Monitor Error: {e}")

        time.sleep(3)

# ================= 7. টেলিগ্রাম বট কমান্ড =================
@bot.message_handler(commands=['ta'])
def handle_ta(message):
    with state_lock:
        bot_state["status"] = "RUNNING"
        target_channel = bot_state["channel"]

    try:
        bot.send_sticker(target_channel, START_STICKER)
    except: pass
    
    # লাইভ স্টার্ট ও সাইলেন্ট জয়েন
    trigger_live_stream()
    bot.reply_to(message, f"✅ <b>{target_channel}</b> চ্যানেলে লাইভ স্ট্রিম ও প্রেডিকশন চালু করা হয়েছে!")

@bot.message_handler(commands=['admin88'])
def handle_admin(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Set Channel", callback_data="btn_channel"))
    bot.reply_to(
        message, 
        f"<b>⚙️ CONTROL PANEL</b>\nবর্তমান চ্যানেল: <code>{bot_state['channel']}</code>\n\nচ্যানেল পরিবর্তন করতে বাটন চাপুন অথবা সময় সেট করতে /TM ফরম্যাটে মেসেজ দিন:",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "btn_channel")
def cb_channel(call):
    msg = bot.send_message(call.message.chat.id, "নতুন চ্যানেলের ID বা Username দিন (যেমন @dark67hack):")
    bot.register_next_step_handler(msg, set_channel_step)

def set_channel_step(message):
    ch = message.text.strip()
    with state_lock:
        bot_state["channel"] = ch
    bot.send_message(message.chat.id, f"✅ চ্যানেল আপডেট হয়েছে: <code>{ch}</code>\nএখন সিগন্যাল সময় সেট করতে লিখুন:\n<code>/TM 10:30AM-1:00PM</code>")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def handle_tm(message):
    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', message.text.upper())
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)

        if sampm == 'PM' and sh != 12: sh += 12
        elif sampm == 'AM' and sh == 12: sh = 0
        elif not sampm and sh < 12 and sh != 0: sh += 12

        if eampm == 'PM' and eh != 12: eh += 12
        elif eampm == 'AM' and eh == 12: eh = 0
        elif not eampm and eh < 12 and eh != 0: eh += 12

        with state_lock:
            bot_state["schedules"] = [(sh, sm, eh, em)]

        clean_time = message.text.replace('/TM', '').strip()
        bot.reply_to(message, f"✅ সময় সেট হয়েছে: <b>{clean_time}</b>\nনির্ধারিত সময়ে বট স্বয়ংক্রিয়ভাবে <b>{bot_state['channel']}</b> চ্যানেলে লাইভ স্টার্ট করবে এবং সিগন্যাল পাঠাবে।")
    else:
        bot.reply_to(message, "ভুল ফরম্যাট! সঠিক ফরম্যাট: <code>/TM 10:30AM-1:00PM</code>")

# ================= 8. টেলিথন ইভেন্ট ও ব্যাকগ্রাউন্ড লুপ =================
def run_telethon_thread():
    global telethon_async_loop
    telethon_async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_async_loop)

    async def telethon_main():
        await telethon_client.start()
        print("[+] Telethon Client Running...")

        # চ্যানেলের লাইভে কোনো ইউজার আসলে অটো আনমিউট
        @telethon_client.on(tl_types.UpdateGroupCallParticipants)
        async def on_user_joined(update):
            for participant in update.participants:
                if getattr(participant, 'muted', False):
                    try:
                        await telethon_client(EditGroupCallParticipantRequest(
                            call=update.call,
                            participant=participant.peer,
                            muted=False
                        ))
                    except: pass

        while True:
            await asyncio.sleep(1)

    telethon_async_loop.run_until_complete(telethon_main())

# ================= 9. স্টার্টার =================
if __name__ == "__main__":
    print(f"[*] Starting Engine for target: {TARGET_CHANNEL}")
    
    # টেলিথন থ্রেড রান
    threading.Thread(target=run_telethon_thread, daemon=True).start()
    
    # প্রেডিকশন মনিটরিং থ্রেড রান
    threading.Thread(target=monitor_engine, daemon=True).start()

    # বট পোলিং
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as err:
            print(f"[Bot Polling Reconnecting]: {err}")
            time.sleep(4)
