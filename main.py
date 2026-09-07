# -*- coding: utf-8 -*-
import requests
import time
import sys
import random
import re
import threading
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
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
DB_URL = "https://raw.githubusercontent.com/poke999craft-del/Ififiififi/refs/heads/main/New%20Text%20Document.txt"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
BD_TIMEZONE = timezone(timedelta(hours=6))

# আপনার ইউজারবটের (রিয়েল আইডি) ক্রেডেনশিয়াল
API_ID = 32054831
API_HASH = '89fc23d0ff6763a53004996fe0c6cab2'
SESSION_STRING = '1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ='

# ================= স্টিকার আইডিসমূহ =================
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ" # সেশন শেষের স্টিকার

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ================= ইউজার ও চ্যানেল ডাটাবেস =================
# স্ট্রাকচার: {user_id: {"channel_id": "...", "schedules": [...], "state": "WAITING", "target_issue": None, "pending_pred": None, "last_was_win": True}}
users_db = {}
db_lock = threading.Lock()
LAST_MORNING_STICKER_DATE = None

# ================= ডাটাবেস লোডার ও প্রেডিকশন (আপনার অরিজিনাল কোড) =================
def load_database():
    print("Database লোড হচ্ছে...")
    try:
        res = requests.get(DB_URL, timeout=10)
        db_string = ''.join(filter(str.isdigit, res.text))
        print(f"Database লোড সফল! মোট সংখ্যা: {len(db_string)}")
        return db_string
    except Exception as e:
        print(f"Database লোড করতে সমস্যা হয়েছে: {e}")
        return ""

def run_prediction(seq_str, db_str):
    if len(db_str) == 0 or len(seq_str) < 4:
        return None
    start_len = min(len(seq_str), 9)
    for i in range(start_len, 3, -1):
        srch = seq_str[-i:]
        mtch = []
        for k in range(len(db_str) - i):
            if db_str[k:k+i] == srch:
                mtch.append(db_str[k+i])
        if mtch:
            dom = Counter(mtch).most_common(1)[0][0]
            is_big = int(dom) >= 5
            return "BIG" if is_big else "SMALL"
    return None

def fetch_latest_results():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
    payload = {"pageNumber": 1, "pageSize": 15}
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
                    parsed.append((issue, int(num)))
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

# ================= TELEBOT এডমিন কমান্ডস =================
@bot.message_handler(commands=['admin88'])
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="add_channel")
    markup.add(btn_add)
    bot.send_message(message.chat.id, "<b>⚙️ Admin Panel</b>\nচ্যানেলে সিগন্যাল দেওয়ার জন্য নিচের বাটনে ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "add_channel":
        msg = bot.send_message(call.message.chat.id, "প্রথমে আপনার চ্যানেলে এই বটটিকে Admin দিন।\n\nAdmin দেওয়ার পর আপনার চ্যানেল আইডি (যেমন: -100123...) সেন্ড করুন:")
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
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে /admin88 কমান্ড দিয়ে আপনার চ্যানেল অ্যাড করুন।")
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
            
        # ইউজারের ইনবক্সে মেসেজ যাবে, চ্যানেলে নয়
        bot.send_message(user_id, f"হ্যাঁ, আমরা {message.text.replace('/TM ', '')} থেকে সিগন্যাল দিব। 🎯")

# ================= কোর সিগন্যাল ও মনিটর লুপ =================
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
        print(f"[*] Signal Sent: Period {short_issue} -> {prediction} (Digits: {digits}) to {channel_id}")
    except Exception as e:
        print(f"[Telegram Error] মেসেজ পাঠানো সম্ভব হয়নি: {e}")

def market_monitor_loop(async_loop, db_string):
    global LAST_MORNING_STICKER_DATE
    while True:
        try:
            results = fetch_latest_results()
            if not results:
                time.sleep(2)
                continue
                
            curr_issue, curr_num = results[0]
            now = datetime.now(BD_TIMEZONE)
            
            with db_lock:
                users_list = list(users_db.items())
                
            for user_id, udata in users_list:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])
                if not channel_id or not schedules:
                    continue

                # মর্নিং স্টিকার চেক
                if now.hour == 5 and now.minute == 0:
                    if LAST_MORNING_STICKER_DATE != now.date():
                        try:
                            bot.send_sticker(channel_id, MORNING_STICKER)
                        except: pass
                        LAST_MORNING_STICKER_DATE = now.date()
                    
                in_schedule = is_in_schedule(now, schedules)
                state = udata["state"]

                # --- সিগন্যাল শুরু এবং লাইভ স্টার্ট ---
                if in_schedule and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True 
                    try: bot.send_sticker(channel_id, START_STICKER)
                    except: pass
                    
                    # টেলিথন (Userbot) দিয়ে অটোমেটিক লাইভ শুরু করার কমান্ড পাঠানো
                    asyncio.run_coroutine_threadsafe(start_group_call(channel_id), async_loop)
                    print(f"[+] Session Started for {channel_id} via Auto Schedule!")
                    
                elif not in_schedule and state == "RUNNING":
                    udata["state"] = "STOPPING" # সিগন্যাল বন্ধের প্রক্রিয়া

                # --- রেজাল্ট চেক ও স্টিকার ---
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")
                
                if target_issue and curr_issue >= target_issue:
                    target_num = None
                    for issue, num in results:
                        if issue == target_issue:
                            target_num = num
                            break

                    if target_num is not None:
                        actual_is_big = (target_num >= 5)
                        predicted_is_big = (pending_pred == "BIG")
                        is_win = (actual_is_big == predicted_is_big)
                        
                        try:
                            if is_win:
                                bot.send_sticker(channel_id, random.choice(WIN_STICKERS))
                                print(f"[WIN] Result: {target_num}, Pred: {pending_pred} in {channel_id}")
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                                print(f"[LOSS] Result: {target_num}, Pred: {pending_pred} in {channel_id}")
                        except: pass
                        
                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # উইন হওয়ার পর যদি STOPPING স্টেটে থাকে, তবে সেশন ক্লোজ স্টিকার দিয়ে শেষ করবে
                        if udata["state"] == "STOPPING" and is_win:
                            try: bot.send_sticker(channel_id, END_STICKER)
                            except: pass
                            udata["state"] = "WAITING"
                            print(f"[-] Session Stopped safely! (After a Win) in {channel_id}")

                # --- নতুন প্রেডিকশন (আপনার অরিজিনাল ডাটাবেস লজিক) ---
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    history_nums = [str(r[1]) for r in results[:10]]
                    seq_str = "".join(reversed(history_nums))
                    
                    prediction = run_prediction(seq_str, db_string)
                    if prediction:
                        next_issue = str(int(curr_issue) + 1)
                        udata["pending_pred"] = prediction
                        udata["target_issue"] = next_issue
                        send_prediction_signal(channel_id, next_issue, prediction)
                    
        except Exception as e:
            print(f"Error in main loop: {e}")
            
        time.sleep(3)

# ================= বট স্টার্টার ও থ্রেডিং =================
if __name__ == "__main__":
    db_string = load_database()
    if not db_string:
        print("Database ছাড়া স্ক্রিপ্ট চলতে পারবে না। বন্ধ করা হচ্ছে...")
        sys.exit()

    print("\n[*] Advanced Multi-User Auto Signal + Live Stream Bot Started...")
    print("[+] Bot is waiting for /admin88 Commands...\n")
    
    # টেলিটক (Telebot) পোলের জন্য একটি আলাদা থ্রেড
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    # ইভেন্ট লুপ নিয়ে অরিজিনাল মনিটর থ্রেড রান করানো হলো
    main_loop = asyncio.get_event_loop()
    threading.Thread(target=market_monitor_loop, args=(main_loop, db_string), daemon=True).start()
    
    # টেলিথন (Userbot) ক্লায়েন্ট চালু রাখা হলো
    client.start()
    print("[+] Userbot Active & Waiting to Start Live Streams!")
    client.run_until_disconnected()
