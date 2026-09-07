# -*- coding: utf-8 -*-
"""
DRX-TM AUTO ENGINE (TA / TOFF / TM FULL CONTROL + AUTO LIVE + TIGER PRO)
"""

import sys
import subprocess

REQUIRED_LIBS = {
    "requests": "requests",
    "telebot": "pyTelegramBotAPI",
    "telethon": "telethon"
}

for import_name, package_name in REQUIRED_LIBS.items():
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

import os
import time
import json
import random
import re
import logging
import threading
import asyncio
from datetime import datetime, timedelta, timezone
from collections import Counter
import requests

import telebot
from telebot import types

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import (
    CreateGroupCallRequest,
    LeaveGroupCallRequest,
    EditGroupCallParticipantRequest,
    JoinGroupCallRequest
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import UpdateGroupCallParticipants, InputGroupCall, DataJSON

# ================= কনফিগারেশন =================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
API_URL_RAW_30S = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

API_ID = 32054831
API_HASH = "89fc23d0ff6763a53004996fe0c6cab2"
SESSION_STRING = "1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ="

START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
telethon_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

global_lock = threading.Lock()
telethon_loop = None

users_db = {}
# Structure: {user_id: {"channel_id": "...", "schedules": [], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True, "active_call": None, "in_live": False}}

# ================= টেলিথন লাইভ ও অটো-আনমিউট ইঞ্জিন =================
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

async def async_start_live(channel_identifier, user_id):
    try:
        try:
            if str(channel_identifier).startswith("-100") or str(channel_identifier).isdigit():
                entity = await telethon_client.get_entity(int(channel_identifier))
            else:
                entity = await telethon_client.get_entity(channel_identifier)
        except Exception:
            try:
                await telethon_client(JoinChannelRequest(channel_identifier))
                entity = await telethon_client.get_entity(channel_identifier)
            except Exception as e:
                logger.error(f"Cannot resolve entity: {e}")
                return

        call_result = await telethon_client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 VIP Signal Room | DRX-TM"
        ))

        input_call = InputGroupCall(id=call_result.call.id, access_hash=call_result.call.access_hash)
        me = await telethon_client.get_me()
        join_as = await telethon_client.get_input_entity(me)

        await telethon_client(JoinGroupCallRequest(
            call=input_call,
            join_as=join_as,
            muted=True,
            video_stopped=True,
            params=DataJSON(data=make_sdp())
        ))

        with global_lock:
            if user_id in users_db:
                users_db[user_id]["in_live"] = True
                users_db[user_id]["active_call"] = input_call

        logger.info(f"[+] Live Stream Activated in {channel_identifier}")
    except Exception as e:
        logger.error(f"[-] Live Stream Failed: {e}")

async def async_leave_live(user_id):
    try:
        with global_lock:
            u_data = users_db.get(user_id, {})
            call_obj = u_data.get("active_call")

        if call_obj:
            await telethon_client(LeaveGroupCallRequest(call=call_obj))

        with global_lock:
            if user_id in users_db:
                users_db[user_id]["in_live"] = False
                users_db[user_id]["active_call"] = None

        logger.info(f"[-] Left Live for user {user_id}")
    except Exception as e:
        logger.error(f"[-] Leave live error: {e}")

@telethon_client.on(events.Raw)
async def auto_unmute_participants(update):
    if isinstance(update, UpdateGroupCallParticipants):
        for participant in update.participants:
            if getattr(participant, 'muted', False) or getattr(participant, 'muted_by_you', False):
                try:
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=update.call,
                        participant=participant.peer,
                        muted=False
                    ))
                except Exception:
                    pass

# ================= TIGER PRO ইঞ্জিন =================
def calculate_tiger_pro(market_records):
    if not market_records:
        return "BIG"
    sample = market_records[:10]
    last_num = sample[0]["number"]
    recent_nums = [x["number"] for x in sample]
    avg = sum(recent_nums) / float(len(recent_nums))

    if avg >= 4.5:
        return "BIG" if recent_nums.count(last_num) < 2 else "SMALL"
    else:
        return "SMALL" if recent_nums.count(last_num) < 2 else "BIG"

def fetch_latest_results_raw():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 15}
    try:
        res = requests.post(API_URL_RAW_30S, json=payload, headers=headers, timeout=5)
        if res.status_code != 200:
            res = requests.get(API_URL_RAW_30S, headers=headers, timeout=5)
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
                issue = str(item.get('issueNumber', item.get('issue', ''))).strip()
                num = item.get('number', item.get('result', -1))
                if issue and num != -1:
                    parsed.append({"period": issue, "number": int(num)})
            return parsed
    except Exception as e:
        logger.error(f"Fetch raw error: {e}")
    return []

# ================= বট কমান্ড ও হ্যান্ডলার =================
@bot.message_handler(commands=["start"])
def send_start(message):
    bot.send_message(message.chat.id, "স্বাগতম! চ্যানেল কনফিগার করতে /admin88 কমান্ড দিন।")

@bot.message_handler(commands=["admin88"])
def admin_panel_cmd(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="btn_add_channel")
    markup.add(btn_add)
    bot.send_message(message.chat.id, "<b>⚙️ ADMIN CONTROL PANEL</b>\n\nচ্যানেল সেটআপ করতে নিচের বাটনে ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "btn_add_channel":
        msg = bot.send_message(call.message.chat.id, "📢 প্রথমে বটটিকে আপনার চ্যানেলে <b>Admin</b> বানান। এরপর চ্যানেলের ইউজারনেম (যেমন: <code>@yourchannel</code>) অথবা আইডি পাঠান:")
        bot.register_next_step_handler(msg, process_channel_registration)
        bot.answer_callback_query(call.id)

def process_channel_registration(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    with global_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "channel_id": channel_id,
                "schedules": [],
                "state": "WAITING",
                "target_issue": None,
                "pending_pred": None,
                "last_was_win": True,
                "active_call": None,
                "in_live": False
            }
        else:
            users_db[user_id]["channel_id"] = channel_id
            
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅\n\nকন্ট্রোল অপশনসমূহ:\n▶️ সরাসরি শুরু করতে: <code>/TA</code>\n⏹ নিরাপদ বন্ধ করতে: <code>/TOFF</code>\n🕒 শিডিউল সেট করতে: <code>/TM 10:30AM-1:00PM</code>")

# ── /TA কমান্ড: সরাসরি লাইভ ও সিগন্যাল শুরু ──
@bot.message_handler(commands=["TA", "ta"])
def trigger_manual_start(message):
    user_id = message.chat.id
    with global_lock:
        udata = users_db.get(user_id)
        if not udata or not udata.get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে /admin88 দিয়ে চ্যানেল অ্যাড করুন।")
            return
        
        channel_id = udata["channel_id"]
        udata["state"] = "RUNNING"
        udata["last_was_win"] = True
        udata["target_issue"] = None
        udata["pending_pred"] = None

    try:
        bot.send_sticker(channel_id, START_STICKER)
    except Exception as e:
        logger.error(f"Failed to send start sticker: {e}")

    if telethon_loop and not udata.get("in_live"):
        asyncio.run_coroutine_threadsafe(async_start_live(channel_id, user_id), telethon_loop)

    bot.send_message(user_id, "✅ <b>সেশন চালু হয়েছে!</b>\nলাইভ স্ট্রিম তৈরি করা হয়েছে এবং সিগন্যাল পাঠানো শুরু হচ্ছে।")

# ── /TOFF কমান্ড: উইন হওয়ার পর লাইভ ও সিগন্যাল অফ ──
@bot.message_handler(commands=["TOFF", "toff"])
def trigger_manual_stop(message):
    user_id = message.chat.id
    with global_lock:
        udata = users_db.get(user_id)
        if not udata or udata.get("state") == "WAITING":
            bot.send_message(user_id, "⚠️ সেশন অলরেডি বন্ধ আছে বা কোনো চ্যানেল সেট করা নেই।")
            return
        udata["state"] = "STOPPING"
        
    bot.send_message(user_id, "🛑 <b>সেশন বন্ধের রিকোয়েস্ট গৃহীত হয়েছে!</b>\nচলতি রাউন্ডটি উইন (WIN) হওয়া মাত্র স্টিকার দিয়ে লাইভ ক্লোজ হবে।")

# ── /TM শিডিউল কমান্ড ──
@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule_handler(message):
    user_id = message.chat.id
    text = message.text.strip().upper()

    with global_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে /admin88 দিয়ে চ্যানেল অ্যাড করুন।")
            return

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

        with global_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]

        start_str = format_12hr(sh, sm)
        end_str = format_12hr(eh, em)
        bot.send_message(user_id, f"হ্যাঁ আমরা <b>{start_str}</b> থেকে <b>{end_str}</b> পর্যন্ত সিগন্যাল দিব এবং লাইভ পরিচালনা করব। 🎯")
    else:
        bot.send_message(user_id, "ভুল ফরম্যাট! সঠিক নিয়ম: <code>/TM 10:30AM-1:00PM</code>")

def format_12hr(hour, minute):
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0: h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def is_in_schedule(now_dt, schedules):
    cur_mins = now_dt.hour * 60 + now_dt.minute
    for (sh, sm, eh, em) in schedules:
        st_mins = sh * 60 + sm
        et_mins = eh * 60 + em
        if st_mins <= cur_mins < et_mins:
            return True
    return False

def send_channel_prediction(channel_id, issue, prediction):
    short_issue = str(issue)[-6:]
    digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2)) if prediction == "BIG" else "/".join(random.sample(['0', '1', '2', '3', '4'], 2))
    signal_text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel_id, signal_text)
    except Exception as e:
        logger.error(f"Signal send error: {e}")

# ================= ব্যাকগ্রাউন্ড সিগন্যাল ও রেজাল্ট মনিটর =================
def channel_signal_and_live_engine():
    while True:
        try:
            results = fetch_latest_results_raw()
            if not results:
                time.sleep(2)
                continue

            curr_issue = results[0]["period"]
            now = datetime.now(BD_TIMEZONE)

            with global_lock:
                sessions = list(users_db.items())

            for user_id, udata in sessions:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])

                if not channel_id:
                    continue

                active_sched = is_in_schedule(now, schedules) if schedules else False
                state = udata["state"]

                # শিডিউলের কারণে অটো-স্টার্ট
                if active_sched and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except Exception: pass

                    if telethon_loop and not udata.get("in_live"):
                        asyncio.run_coroutine_threadsafe(async_start_live(channel_id, user_id), telethon_loop)

                # শিডিউল টাইম পার হলে অটো স্টপিং
                elif schedules and not active_sched and state == "RUNNING":
                    udata["state"] = "STOPPING"

                # রেজাল্ট চেক ও স্টিকার সেন্ডিং
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")

                if target_issue and int(curr_issue) >= int(target_issue):
                    matched = next((r["number"] for r in results if r["period"] == target_issue), None)
                    if matched is not None:
                        actual_size = "BIG" if matched >= 5 else "SMALL"
                        is_win = (actual_size == pending_pred)
                        try:
                            bot.send_sticker(channel_id, random.choice(WIN_STICKERS) if is_win else LOSS_STICKER)
                        except Exception: pass

                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # উইন হওয়ার পর সেশন ক্লোজ করা
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except Exception: pass

                            if telethon_loop and udata.get("in_live"):
                                asyncio.run_coroutine_threadsafe(async_leave_live(user_id), telethon_loop)
                            udata["state"] = "WAITING"

                # নতুন প্রেডিকশন পাঠানো (TIGER PRO)
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_channel_prediction(channel_id, next_issue, prediction)

        except Exception as e:
            logger.error(f"Engine Loop Error: {e}")

        time.sleep(2.5)

# ================= টেলিথন ও বট লঞ্চার =================
def run_telethon_async_loop():
    global telethon_loop
    telethon_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_loop)

    async def start_client():
        await telethon_client.start()
        logger.info("[✓] Telethon Userbot is Connected and Ready.")

    telethon_loop.run_until_complete(start_client())
    telethon_loop.run_forever()

if __name__ == "__main__":
    print("=" * 60)
    print(" DRX-TM HYBRID ENGINE ONLINE ")
    print(" Commands: /admin88 | /TA (Start) | /TOFF (Stop) | /TM ")
    print("=" * 60)

    threading.Thread(target=run_telethon_async_loop, daemon=True).start()
    threading.Thread(target=channel_signal_and_live_engine, daemon=True).start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as err:
            logger.error(f"Bot Polling Crashed: {err}. Restarting in 5s...")
            time.sleep(5)
