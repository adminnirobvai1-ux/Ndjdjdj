# -*- coding: utf-8 -*-
"""
=============================================================================
 DRX-TM VIP AUTOMATED SIGNAL BOT + TELETHON USERBOT LIVE STREAM SYSTEM
=============================================================================
 Features:
   1. Automatic Package Installer (pip auto-installer)
   2. Interactive Admin Panel (/admin88) with Channel Setup & /TM Time Parser
   3. Tiger Pro Deep Analytics Prediction Engine (WinGo 30S)
   4. Telethon Userbot Integration for Automated Channel Live/Voice Calls
   5. Auto-Unmute Engine for Live Call Participants
   6. Session Cycle Manager with Start, Win, Loss, Morning, and End Stickers
=============================================================================
"""

import sys
import os
import subprocess

# =========================================================
# ১. স্বয়ংক্রিয় প্যাকেজ ইন্সটলার (AUTO PACKAGE INSTALLER)
# =========================================================
REQUIRED_PACKAGES = {
    "requests": "requests",
    "telebot": "pyTelegramBotAPI",
    "telethon": "telethon"
}

def auto_install_packages():
    print("[*] Checking and installing required packages...")
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"[+] Installing {pip_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

auto_install_packages()

import time
import random
import re
import json
import asyncio
import threading
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter
import requests
import telebot
from telebot import types
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import CreateGroupCallRequest, EditGroupCallParticipantRequest, DiscardGroupCallRequest
from telethon.tl.types import UpdateGroupCallParticipants, InputGroupCall

# =========================================================
# ২. কনফিগারেশন ও গ্লোবাল ক্রেডেনশিয়ালস
# =========================================================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
API_ID = 32054831
API_HASH = "89fc23d0ff6763a53004996fe0c6cab2"
SESSION_STRING = "1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ="

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# =========================================================
# ৩. স্টিকার কনফিগারেশন
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
# ৪. গ্লোবাল অবজেক্টস ও স্টেট ম্যানেজমেন্ট
# =========================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
telethon_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

db_lock = threading.Lock()
users_db = {}
active_group_calls = {}  # {channel_id: call_handle}
last_morning_sticker_date = None

# =========================================================
# ৫. কাস্টম ভিআইপি ফন্ট ইঞ্জিন (VIP FONT GENERATOR)
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
# ৬. টাইগার প্রো (TIGER PRO) প্রেডিকশন ইঞ্জিন
# =========================================================
def calculate_tiger_pro(market_records):
    """
    Tiger Pro Deep Analytics Engine:
    - Moving Average (১০ রাউন্ডের ট্রেন্ড)
    - Frequency Analysis (হট নাম্বার ট্র্যাকিং)
    - Streak Breaker (একটানা একই কালার/সাইজ কমানো)
    """
    if len(market_records) < 15:
        return "BIG"

    sample = market_records[:100]
    last_num = sample[0]["number"]

    # ১০ রাউন্ডের মুভিং এভারেজ
    recent_10 = [x["number"] for x in sample[:10]]
    avg_10 = sum(recent_10) / 10.0

    # ফ্রিকোয়েন্সি কাউন্ট
    big_count = sum(1 for x in recent_10 if x >= 5)
    small_count = 10 - big_count

    # স্ট্রিক চেইনিং ডিটেকশন
    if big_count >= 7:
        return "SMALL"
    elif small_count >= 7:
        return "BIG"

    if avg_10 >= 4.8:
        return "BIG" if recent_10.count(last_num) < 3 else "SMALL"
    else:
        return "SMALL" if recent_10.count(last_num) < 3 else "BIG"

# =========================================================
# ৭. এপিআই ডাটা ফেচার (DATA FETCHING ENGINE)
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
        logger.error(f"Data Fetch Error: {e}")
    return []

# =========================================================
# ৮. সময় ও শিডিউল হেলপার্স
# =========================================================
def format_12hr(hour, minute):
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def parse_time_string(text):
    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text, re.IGNORECASE)
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)

        if sampm:
            sampm = sampm.upper()
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12

        if eampm:
            eampm = eampm.upper()
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        return (sh, sm, eh, em)
    return None

def is_in_schedule(now, schedules):
    current_minutes = now.hour * 60 + now.minute
    for (sh, sm, eh, em) in schedules:
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
        if start_mins <= current_minutes < end_mins:
            return True
    return False

# =========================================================
# ৯. টেলিগ্রাম বট কন্ট্রোল ও হ্যান্ডলার্স (TELEBOT HANDLERS)
# =========================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('VIP SIGNAL SYSTEM')}</b>\n\n"
        f"স্বাগতম! বট সেটআপ করতে এবং সিগন্যাল রান করতে <b>/admin88</b> কমান্ড দিন।"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['admin88'])
def handle_admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    btn_time = types.InlineKeyboardButton("🕒 Set Signal Time", callback_data="set_time_info")
    btn_status = types.InlineKeyboardButton("📊 System Status", callback_data="sys_status")
    btn_help = types.InlineKeyboardButton("ℹ️ Help", callback_data="help_info")
    markup.add(btn_add, btn_time)
    markup.add(btn_status, btn_help)

    panel_text = (
        f"<b>⚙️ {to_vip('ADMIN PANEL')}</b>\n"
        f"────────────────────────\n"
        f"আপনার চ্যানেল অ্যাড করতে এবং সময় সেটআপ করতে নিচের বাটনগুলো ব্যবহার করুন:"
    )
    bot.send_message(message.chat.id, panel_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id

    if call.data == "add_channel":
        msg = bot.send_message(
            chat_id,
            "<b>১.</b> প্রথমে এই বটটিকে আপনার চ্যানেলে Admin হিসেবে অ্যাড করুন।\n"
            "<b>২.</b> আপনার চ্যানেলের Username (যেমন: `@channelname`) অথবা ID (যেমন: `-100123456789`) এখানে পাঠান:"
        )
        bot.register_next_step_handler(msg, process_channel_input)

    elif call.data == "set_time_info":
        info_msg = (
            "<b>🕒 সিগন্যাল সময় সেট করার নিয়ম:</b>\n\n"
            "ফরম্যাট: <code>/TM 10:30AM-1:00PM</code> অথবা <code>/TM 02:00PM-05:00PM</code>\n\n"
            "এখনই এই ফরম্যাটে মেসেজ সেন্ড করুন।"
        )
        bot.send_message(chat_id, info_msg)

    elif call.data == "sys_status":
        with db_lock:
            udata = users_db.get(chat_id, {})
        chan = udata.get("channel_id", "Not Set")
        sched = udata.get("schedules", [])
        st = udata.get("state", "WAITING")

        sched_str = "None"
        if sched:
            sh, sm, eh, em = sched[0]
            sched_str = f"{format_12hr(sh, sm)} - {format_12hr(eh, em)}"

        status_text = (
            f"<b>📊 {to_vip('SYSTEM STATUS')}</b>\n"
            f"────────────────────────\n"
            f"<b>Channel ID:</b> {chan}\n"
            f"<b>Schedule:</b> {sched_str}\n"
            f"<b>Engine State:</b> {st}\n"
        )
        bot.send_message(chat_id, status_text)

    elif call.data == "help_info":
        help_text = (
            "<b>ℹ️ সাহায্য নির্দেশিকা:</b>\n"
            "1. /admin88 ব্যবহার করে চ্যানেল সেট করুন।\n"
            "2. /TM দিয়ে সময় যুক্ত করুন।\n"
            "3. বট নির্ধারিত সময়ে চ্যানেলে লাইভ স্ট্রিম চালু করবে এবং প্রেডিকশন মেসেজ দেওয়া শুরু করবে।"
        )
        bot.send_message(chat_id, help_text)

    bot.answer_callback_query(call.id)

def process_channel_input(message):
    channel_input = message.text.strip()
    user_id = message.chat.id

    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "channel_id": channel_input,
                "schedules": [],
                "state": "WAITING",
                "target_issue": None,
                "pending_pred": None,
                "last_was_win": True,
                "live_active": False
            }
        else:
            users_db[user_id]["channel_id"] = channel_input

    bot.send_message(user_id, "<b>ডান ওকে ডান ✅</b>")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def handle_time_command(message):
    user_id = message.chat.id
    text = message.text.strip().upper()

    with db_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ আগে /admin88 দিয়ে আপনার চ্যানেল অ্যাড করুন।")
            return

    new_sched = parse_time_string(text)
    if new_sched:
        sh, sm, eh, em = new_sched
        start_str = format_12hr(sh, sm)
        end_str = format_12hr(eh, em)

        with db_lock:
            users_db[user_id]["schedules"] = [new_sched]

        # চ্যানেলে পোস্ট হবে না, ইউজারকে সরাসরি প্রাইভেটে কনফার্ম করবে
        reply_msg = f"হ্যাঁ, আমরা {start_str} থেকে {end_str} পর্যন্ত সিগন্যাল দিব।"
        bot.send_message(user_id, reply_msg)
    else:
        bot.send_message(user_id, "❌ ভুল ফরম্যাট! উদাহরণ: /TM 10:30AM-1:00PM")

# =========================================================
# ১০. TELETHON USERBOT LIVE CALL ENGINE
# =========================================================
async def start_channel_live(channel_id):
    """চ্যানেলে লাইভ স্ট্রিমিং/ভয়েস কল শুরু করার জন্য"""
    try:
        try:
            entity = await telethon_client.get_entity(int(channel_id))
        except ValueError:
            entity = await telethon_client.get_entity(channel_id)

        call_result = await telethon_client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 DRX-TM LIVE SIGNAL ROOM"
        ))
        logger.info(f"[+] Live Stream Started on {channel_id}")
        return call_result
    except Exception as e:
        logger.error(f"[-] Failed to start live call on {channel_id}: {e}")
        return None

@telethon_client.on(events.Raw)
async def auto_unmute_participants(update):
    """লাইভে কেউ যুক্ত হলে সাথে সাথে Auto Unmute করা"""
    if isinstance(update, UpdateGroupCallParticipants):
        for participant in update.participants:
            if participant.muted:
                try:
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=update.call,
                        participant=participant.peer,
                        muted=False
                    ))
                    logger.info("[+] Auto-Unmuted participant in Live Call!")
                except Exception as e:
                    pass

# =========================================================
# ১১. সিগন্যাল ও সেশন এক্সিকিউশন মনিটর (MAIN SIGNAL LOOP)
# =========================================================
def send_prediction_signal(channel_id, issue, prediction):
    short_issue = str(issue)[-6:]
    if prediction == "BIG":
        digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2))
    else:
        digits = "/".join(random.sample(['0', '1', '2', '3', '4'], 2))

    signal_text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""

    try:
        bot.send_message(channel_id, signal_text)
        logger.info(f"[*] Signal Sent to {channel_id}: {short_issue} -> {prediction}")
    except Exception as e:
        logger.error(f"Failed to send signal to {channel_id}: {e}")

def signal_execution_loop():
    global last_morning_sticker_date

    while True:
        try:
            now = datetime.now(BD_TIMEZONE)

            # সকাল ৫টা স্টিকার চেক
            if now.hour == 5 and now.minute == 0:
                if last_morning_sticker_date != now.date():
                    with db_lock:
                        for udata in users_db.values():
                            chan = udata.get("channel_id")
                            if chan:
                                try: bot.send_sticker(chan, MORNING_STICKER)
                                except: pass
                    last_morning_sticker_date = now.date()

            results = fetch_latest_results()
            if not results:
                time.sleep(2)
                continue

            curr_issue = results[0]["period"]

            with db_lock:
                users_list = list(users_db.items())

            for user_id, udata in users_list:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])

                if not channel_id or not schedules:
                    continue

                in_sched = is_in_schedule(now, schedules)
                state = udata.get("state", "WAITING")

                # --- ১. সেশন শুরু ---
                if in_sched and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except: pass

                    # লাইভ স্ট্রিম অটো শুরু
                    if not udata.get("live_active"):
                        asyncio.run_coroutine_threadsafe(
                            start_channel_live(channel_id),
                            telethon_client.loop
                        )
                        udata["live_active"] = True

                # --- ২. সেশন বন্ধের সময় পার হওয়া (STOPPING State) ---
                elif not in_sched and state == "RUNNING":
                    udata["state"] = "STOPPING"

                # --- ৩. ফলাফল মূল্যায়ন (Win/Loss Validation) ---
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

                        # নির্ধারিত সময় পার হওয়ার পর উইন এলে সেশন শেষ করবে
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except: pass
                            udata["state"] = "WAITING"
                            udata["live_active"] = False

                # --- ৪. নতুন প্রেডিকশন প্রদান (Tiger Pro Engine) ---
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)

                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue

                    send_prediction_signal(channel_id, next_issue, prediction)

        except Exception as e:
            logger.error(f"Error in signal execution loop: {e}")

        time.sleep(2)

# =========================================================
# ১২. মাল্টি-থ্রেডেড রানার ও বট স্টার্টআপ
# =========================================================
def run_telebot():
    while True:
        try:
            logger.info("[+] Telebot Polling Started...")
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Telebot Crash: {e}. Restarting in 5s...")
            time.sleep(5)

def run_telethon():
    logger.info("[+] Telethon Userbot Starting...")
    telethon_client.start()
    telethon_client.run_until_disconnected()

if __name__ == "__main__":
    print("=" * 70)
    print(f" {to_vip('DRX-TM AUTOMATED LIVE SIGNAL & PREDICTION SYSTEM')} ")
    print(" Engine: Tiger Pro Deep Analytics | Multi-Threaded System")
    print("=" * 70)

    # ১. মার্কেট ও সিগন্যাল থ্রেড চালু
    signal_thread = threading.Thread(target=signal_execution_loop, daemon=True)
    signal_thread.start()

    # ২. টেলিবট থ্রেড চালু
    telebot_thread = threading.Thread(target=run_telebot, daemon=True)
    telebot_thread.start()

    # ৩. টেলিথন ইউজারবট মেইন থ্রেডে চালু
    run_telethon()
