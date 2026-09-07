# -*- coding: utf-8 -*-
import time
import random
import re
import threading
import requests
import asyncio
from datetime import datetime, timedelta, timezone
from collections import Counter

import telebot
from telebot import types
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import CreateGroupCallRequest, EditGroupCallParticipantRequest
from telethon.tl.types import UpdateGroupCallParticipants

# ================= কনফিগারেশন =================
# আপনার সিগন্যাল বটের টোকেন
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"

# আপনার ইউজারবটের (রিয়েল আইডি) ক্রেডেনশিয়াল
API_ID = 32054831
API_HASH = '89fc23d0ff6763a53004996fe0c6cab2'
SESSION_STRING = '1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ='

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# ================= স্টিকার আইডিসমূহ =================
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ================= ইউজার ও চ্যানেল ডাটাবেস =================
users_db = {}
db_lock = threading.Lock()

# ================= TIGER PRO ENGINE =================
def calculate_tiger_pro(market_records):
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

# ================= API ডাটা ফেচার =================
def fetch_latest_results():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 100}
    try:
        res = requests.post(API_URL, json=payload, headers=headers, timeout=5)
        if res.status_code != 200:
            res = requests.get(API_URL, headers=headers, timeout=5)
        data = res.json()
        
        def extract_list(d):
            if isinstance(d, list) and len(d)>0 and isinstance(d[0], dict) and ('issueNumber' in d[0] or 'issue' in d[0]):
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

# ================= TELETHON (Userbot) ফাংশনস =================
async def start_group_call(channel_id):
    """অটোমেটিক চ্যানেলে লাইভ স্টার্ট করার ফাংশন"""
    try:
        try:
            entity = await client.get_entity(int(channel_id))
        except ValueError:
            entity = await client.get_entity(channel_id)
            
        await client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 Live Signal Room"
        ))
        print(f"[+] Successfully started Live Stream in {channel_id}")
    except Exception as e:
        print(f"[-] Live Stream Error (Already running or issue): {e}")

@client.on(events.Raw)
async def auto_unmute_handler(update):
    """লাইভে কেউ জয়েন করলেই অটোমেটিক আনমিউট করবে"""
    if isinstance(update, UpdateGroupCallParticipants):
        for participant in update.participants:
            if participant.muted:
                try:
                    await client(EditGroupCallParticipantRequest(
                        call=update.call,
                        participant=participant.peer,
                        muted=False
                    ))
                    print("[+] এক ইউজারকে অটো আনমিউট করা হয়েছে!")
                except Exception as e:
                    pass

# ================= TELEBOT কমান্ডস =================
@bot.message_handler(commands=['admin88'])
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    markup.add(btn_add)
    bot.send_message(message.chat.id, "<b>⚙️ Admin Panel</b>\nচ্যানেল সেটআপ করতে নিচের বাটনে ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "add_channel":
        msg = bot.send_message(call.message.chat.id, "প্রথমে বট এবং আপনার রিয়েল আইডিকে চ্যানেলে Admin দিন।\nএরপর চ্যানেলের ID (যেমন: -100123...) দিন:")
        bot.register_next_step_handler(msg, process_channel_id)

def process_channel_id(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    with db_lock:
        if user_id not in users_db:
            users_db[user_id] = {"schedules": [], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True}
        users_db[user_id]["channel_id"] = channel_id
    bot.send_message(user_id, "<b>ডান ওকে ডান ✅</b>", parse_mode="HTML")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule(message):
    user_id = message.chat.id
    text = message.text.upper()
    with db_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ আগে /admin88 দিয়ে চ্যানেল অ্যাড করুন।")
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

        with db_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]
            
        bot.send_message(user_id, f"হ্যাঁ, আমরা {message.text.replace('/TM ', '')} থেকে সিগন্যাল দিব। 🎯")

# ================= কোর সিগন্যাল ও মনিটর লুপ =================
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
    except: pass

def market_monitor_loop(async_loop):
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

                # --- সিগন্যাল শুরু এবং লাইভ স্টার্ট ---
                if in_schedule and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True 
                    try: bot.send_sticker(channel_id, START_STICKER)
                    except: pass
                    
                    # টেলিথন (Userbot) দিয়ে লাইভ শুরু করার কমান্ড
                    asyncio.run_coroutine_threadsafe(start_group_call(channel_id), async_loop)
                    
                elif not in_schedule and state == "RUNNING":
                    udata["state"] = "STOPPING"

                # --- রেজাল্ট চেক ও স্টিকার ---
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")
                
                if target_issue and curr_issue >= target_issue:
                    target_num = next((r["number"] for r in results if r["period"] == target_issue), None)
                    if target_num is not None:
                        actual_is_big = (target_num >= 5)
                        predicted_is_big = (pending_pred == "BIG")
                        is_win = (actual_is_big == predicted_is_big)
                        
                        try:
                            if is_win: bot.send_sticker(channel_id, random.choice(WIN_STICKERS))
                            else: bot.send_sticker(channel_id, LOSS_STICKER)
                        except: pass
                        
                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        if udata["state"] == "STOPPING" and is_win:
                            try: bot.send_sticker(channel_id, END_STICKER)
                            except: pass
                            udata["state"] = "WAITING"

                # --- নতুন সিগন্যাল (TIGER PRO) ---
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    prediction = calculate_tiger_pro(results)
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_prediction_signal(channel_id, next_issue, prediction)
                    
        except Exception as e:
            pass
            
        time.sleep(3)

# ================= বট স্টার্টার =================
if __name__ == "__main__":
    print("[*] Tiger Pro Auto Signal + Live Stream Bot Started...")
    
    # টেলিটক (Telebot) পোলের জন্য একটি আলাদা থ্রেড তৈরি করা হলো
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    # ইভেন্ট লুপ নিয়ে মনিটর থ্রেড রান করানো হলো
    main_loop = asyncio.get_event_loop()
    threading.Thread(target=market_monitor_loop, args=(main_loop,), daemon=True).start()
    
    # টেলিথন (Userbot) ক্লায়েন্ট চালু রাখা হলো
    client.start()
    print("[+] Userbot Active & Waiting to Start Live Streams!")
    client.run_until_disconnected()
