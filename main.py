# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Multi-Market (30S & 5M) Pure Market Viewer Bot
Features:
  - Zero Prediction / Pure Live Market Engine
  - 30-Second (29S) & 5-Minute Live Market Sync
  - Real-time Animated Countdown Timer
  - Period, Number, Size, Color Live Table
  - Referral Lock, Channel Verification & Admin Password Bypass
"""

import time
import threading
import requests
import json
import os

# ================= CONFIGURATION =================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
BOT_USERNAME = "DRX_TM_POD_BOT" 
CHANNEL_USERNAME = "@DARK67HACK"
ADMIN_ID = "8707571669"  # Admin User ID

MARKETS = {
    "30S": {
        "name": "WINGO 30 SEC",
        "api": "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json",
        "interval": 30
    },
    "5M": {
        "name": "WINGO 5 MIN",
        "api": "https://advanced-predict1.ai.studio/apipid.json",
        "interval": 300
    }
}

USER_SESSIONS = {}
LAST_UPDATE_ID = 0
DB_FILE = "users_db.json"

# ================= PREMIUM FONT GENERATOR =================
def to_premium(text):
    mapping = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
    )
    return str(text).translate(mapping)

# ================= NUMBER LOGIC =================
def get_color(num: int) -> str:
    if num in [0, 5]:
        return "VIOLET"
    return "RED" if num in [2, 4, 6, 8] else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num >= 5 else "SMALL"

# ================= DATABASE & REFERRAL LOGIC =================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                db = json.load(f)
                if "__config__" not in db:
                    db["__config__"] = {"bypass_password": None}
                return db
        except Exception:
            pass
    return {"__config__": {"bypass_password": None}}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
    except Exception as e:
        print(f"[-] DB Save Error: {e}")

USERS_DB = load_db()

def check_channel_member(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": CHANNEL_USERNAME, "user_id": user_id}
    try:
        res = requests.get(url, params=params, timeout=3).json()
        if res.get("ok"):
            status = res["result"]["status"]
            return status in ["member", "administrator", "creator"]
    except Exception:
        pass
    return False

def get_user_task_info(user_id):
    user_id = str(user_id)
    current_day = int(time.time() + 21600) // 86400  # UTC+6
    
    if user_id not in USERS_DB:
        USERS_DB[user_id] = {
            "joined_day": current_day,
            "referrals": [],
            "unlocked_days": []
        }
        save_db(USERS_DB)
        
    user_data = USERS_DB[user_id]
    days_active = current_day - user_data.get("joined_day", current_day)
    target_shares = 2 + days_active
    current_referrals = len(user_data.get("referrals", []))
    is_unlocked_today = str(current_day) in user_data.get("unlocked_days", [])
    
    return target_shares, current_referrals, is_unlocked_today, current_day

def send_telegram_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=4)
    except Exception:
        pass

# ================= TASK PROMPT & MENU =================
def send_welcome_task_menu(chat_id, msg_id=None):
    target, current, _, _ = get_user_task_info(chat_id)
    
    text = (
        f"<b>{to_premium('WELCOME TO WINGO LIVE MARKET')}</b>\n\n"
        "আসসালামু আলাইকুম। আশা করি সকলে ভালো আছেন।\n\n"
        "এই 𝐋𝐈𝐕𝐄 𝐌𝐀𝐑𝐊𝐄𝐓 𝐁𝐎𝐓 ব্যবহার করার জন্য আপনাকে নিচের শর্ত পূরণ করতে হবে <b>অথবা</b> এডমিনের দেয়া পাসওয়ার্ড সাবমিট করতে হবে:\n\n"
        f"১. আমাদের অফিশিয়াল চ্যানেলে জয়েন থাকতে হবে।\n"
        f"২. বটটি প্রথমবার আনলক করতে <b>২ জন</b> রিয়েল রেফার করতে হবে। পরবর্তীতে প্রতিদিন <b>১ জন</b> করে রেফার করতে হবে।\n\n"
        "⚠️ <b>সতর্কতা:</b> রেফার করা মেম্বারকে অবশ্যই চ্যানেলে জয়েন থাকতে হবে!\n\n"
        f"🎯 আপনার বর্তমান টার্গেট: <b>{to_premium(str(target))}</b> জন।\n"
        f"👥 লিংকে ক্লিক করেছে: <b>{to_premium(str(current))}</b> জন।\n\n"
        "🔑 <i>আপনার কাছে পাসওয়ার্ড থাকলে সেটি সরাসরি চ্যাটে লিখে সেন্ড করুন।</i>"
    )
    
    channel_link = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    personal_ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"
    share_url = f"https://t.me/share/url?url={personal_ref_link}&text=Join%20Live%20WinGo%20Market%20Terminal"

    keyboard = [
        [{"text": to_premium("JOIN CHANNEL"), "url": channel_link}],
        [{"text": to_premium("SHARE LINK"), "url": share_url}],
        [{"text": to_premium("VERIFY REFERRALS"), "callback_data": "verify_task"}]
    ]

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": keyboard}
    }

    if msg_id:
        payload["message_id"] = msg_id
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
    try:
        res = requests.post(url, json=payload, timeout=4).json()
        if not msg_id and res.get("ok"):
            USER_SESSIONS[str(chat_id)] = {
                "msg_id": res["result"]["message_id"],
                "view": "task",
                "market": None
            }
    except Exception:
        pass

# ================= API DATA & TIMER =================
def fetch_market_history(market_key):
    api_url = MARKETS[market_key]["api"]
    try:
        res = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if res.status_code == 200:
            data = res.json()
            raw_list = []
            
            if isinstance(data, dict):
                for k in ["history", "prediction_history", "data", "list", "records"]:
                    if k in data and isinstance(data[k], list):
                        raw_list = data[k]
                        break
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                if isinstance(item, dict):
                    p_raw = item.get("period")
                    n_raw = item.get("number") if item.get("number") is not None else item.get("actual_number")
                    if p_raw is not None and n_raw is not None:
                        try:
                            num = int(n_raw)
                        except (ValueError, TypeError):
                            continue
                        
                        size = str(item.get("size", "")).strip().upper()
                        color = str(item.get("color", "")).strip().upper()
                        
                        if size not in ["BIG", "SMALL"]:
                            size = get_size(num)
                        if color not in ["RED", "GREEN", "VIOLET"]:
                            color = get_color(num)

                        formatted.append({
                            "period": str(p_raw).strip(),
                            "number": num,
                            "size": size,
                            "color": color
                        })
            return formatted
    except Exception:
        pass
    return []

def get_countdown(interval):
    now = int(time.time())
    return interval - (now % interval)

def get_timer_display(interval):
    sec = get_countdown(interval)
    blocks = int((sec / float(interval)) * 15)
    bar = "▓" * blocks + "░" * (15 - blocks)
    
    if interval >= 60:
        mins = sec // 60
        secs = sec % 60
        return f"⏳ {mins:02d}:{secs:02d} [{bar}]"
    return f"⏳ {sec:02d}S [{bar}]"

# ================= MAIN MENU =================
def build_menu_markup():
    keyboard = [
        [{"text": to_premium("WINGO 30 SEC LIVE"), "callback_data": "open_30S"}],
        [{"text": to_premium("WINGO 5 MIN LIVE"), "callback_data": "open_5M"}]
    ]
    return to_premium("SELECT WINGO MARKET"), keyboard

# ================= PURE MARKET VIEW (NO PREDICTION) =================
def build_market_markup(market_key):
    cfg = MARKETS[market_key]
    interval = cfg["interval"]
    records = fetch_market_history(market_key)
    
    # পিরিয়ড গণনা
    if records:
        top_period = records[0]["period"]
        try:
            current_period = str(int(top_period) + 1).zfill(len(top_period))
        except Exception:
            current_period = str(top_period)
    else:
        current_period = "SYNCING..."

    period_8 = current_period[-8:] if len(current_period) >= 8 else current_period

    keyboard = []
    # ১. পিরিয়ড
    keyboard.append([
        {"text": to_premium(f"PERIOD: {period_8}"), "callback_data": "noop"}
    ])
    # ২. টাইমার
    keyboard.append([
        {"text": get_timer_display(interval), "callback_data": "noop"}
    ])
    # ৩. টেবিল হেডার (নো প্রেডিকশন)
    keyboard.append([
        {"text": to_premium("PERIOD"), "callback_data": "noop"},
        {"text": to_premium("NUM"), "callback_data": "noop"},
        {"text": to_premium("SIZE"), "callback_data": "noop"},
        {"text": to_premium("COLOR"), "callback_data": "noop"}
    ])

    # ৪. পিওর মার্কেট ডাটা (সর্বোচ্চ ১০টি সারি)
    for item in records[:10]:
        p_short = item["period"][-4:] if len(item["period"]) >= 4 else item["period"]
        num = str(item["number"])
        size = item["size"]
        color = item["color"]

        keyboard.append([
            {"text": to_premium(p_short), "callback_data": "noop"},
            {"text": to_premium(num), "callback_data": "noop"},
            {"text": to_premium(size), "callback_data": "noop"},
            {"text": to_premium(color), "callback_data": "noop"}
        ])

    # ৫. ব্যাক টু মেনু বাটন
    keyboard.append([
        {"text": to_premium("🔙 BACK TO MARKETS"), "callback_data": "back_to_menu"}
    ])

    text_title = (
        f"<b>{to_premium('MARKET TERMINAL')}</b>\n"
        f"<b>{to_premium('LIVE:')} {to_premium(cfg['name'])}</b>\n"
        f"<i>{to_premium('PURE LIVE DATA FEED')}</i>\n"
        "────────────────────────"
    )
    return text_title, keyboard

# ================= TELEGRAM HANDLERS =================
def send_main_menu(chat_id, msg_id=None):
    title, markup = build_menu_markup()
    payload = {
        "chat_id": chat_id,
        "text": f"<b>{title}</b>",
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": markup}
    }
    
    if msg_id:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload["message_id"] = msg_id
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        res = requests.post(url, json=payload, timeout=4).json()
        if res.get("ok"):
            save_msg_id = msg_id if msg_id else res["result"]["message_id"]
            USER_SESSIONS[str(chat_id)] = {
                "msg_id": save_msg_id,
                "view": "menu",
                "market": None
            }
    except Exception:
        pass

def switch_view(chat_id, msg_id, view, market_key=None):
    if view == "menu":
        text, markup = build_menu_markup()
        text = f"<b>{text}</b>"
    else:
        text, markup = build_market_markup(market_key)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": markup}
    }
    try:
        requests.post(url, json=payload, timeout=4)
        USER_SESSIONS[str(chat_id)] = {
            "msg_id": msg_id,
            "view": view,
            "market": market_key
        }
    except Exception:
        pass

def live_update_keyboard(chat_id, msg_id, view, market_key):
    if view == "menu":
        return
    _, markup = build_market_markup(market_key)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "reply_markup": {"inline_keyboard": markup}
    }
    try:
        requests.post(url, json=payload, timeout=2)
    except Exception:
        pass

def answer_callback(cb_id, text="", show_alert=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": cb_id, "text": text, "show_alert": show_alert}
    try:
        requests.post(url, json=payload, timeout=2)
    except Exception:
        pass

# ================= REALTIME ENGINE =================
def realtime_sync_engine():
    while True:
        try:
            for chat_id, session in list(USER_SESSIONS.items()):
                if session.get("view") == "market" and session.get("market"):
                    live_update_keyboard(
                        chat_id, 
                        session["msg_id"], 
                        session["view"], 
                        session["market"]
                    )
        except Exception:
            pass
        time.sleep(1)

# ================= MAIN LISTENER =================
def telegram_listener():
    global LAST_UPDATE_ID
    print("[*] Engine Online. Pure Market Display Active (Zero Prediction).")

    while True:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"offset": LAST_UPDATE_ID + 1, "timeout": 2}
        
        try:
            res = requests.get(url, params=params, timeout=4)
            data = res.json()
            
            if data.get("ok"):
                for item in data["result"]:
                    LAST_UPDATE_ID = item["update_id"]

                    if "message" in item and "text" in item["message"]:
                        chat_id = str(item["message"]["chat"]["id"])
                        msg_text = item["message"]["text"].strip()
                        
                        # --- ADMIN PASSWORD SETTING ---
                        if chat_id == ADMIN_ID and msg_text.startswith("/admin "):
                            new_pass = msg_text.split(" ", 1)[1].strip()
                            USERS_DB["__config__"]["bypass_password"] = new_pass
                            save_db(USERS_DB)
                            send_telegram_msg(chat_id, f"✅ <b>Bypass password successfully set to:</b> {new_pass}")
                            continue

                        # --- USER PASSWORD BYPASS ---
                        global_pass = USERS_DB.get("__config__", {}).get("bypass_password")
                        if global_pass and msg_text == global_pass:
                            _, _, _, current_day = get_user_task_info(chat_id)
                            if "unlocked_days" not in USERS_DB[chat_id]:
                                USERS_DB[chat_id]["unlocked_days"] = []
                            if str(current_day) not in USERS_DB[chat_id]["unlocked_days"]:
                                USERS_DB[chat_id]["unlocked_days"].append(str(current_day))
                                save_db(USERS_DB)
                            
                            send_telegram_msg(chat_id, "✅ <b>𝐏𝐀𝐒𝐒𝐖𝐎𝐑𝐃 𝐀𝐂𝐂𝐄𝐏𝐓𝐄𝐃!</b>\nআপনি রেফারাল ছাড়াই মার্কেট বট আনলক করেছেন।")
                            send_main_menu(chat_id)
                            continue

                        # --- REFERRAL TRACKING (/start ...) ---
                        if msg_text.startswith("/start ") and len(msg_text.split()) > 1:
                            referrer_id = msg_text.split()[1].strip()
                            if chat_id not in USERS_DB:
                                get_user_task_info(chat_id)
                                if referrer_id in USERS_DB and referrer_id != chat_id:
                                    if "referrals" not in USERS_DB[referrer_id]:
                                        USERS_DB[referrer_id]["referrals"] = []
                                    if chat_id not in USERS_DB[referrer_id]["referrals"]:
                                        USERS_DB[referrer_id]["referrals"].append(chat_id)
                                        save_db(USERS_DB)
                                        
                        is_member = check_channel_member(chat_id)
                        target, current_refs, is_unlocked, _ = get_user_task_info(chat_id)
                        
                        if is_unlocked and is_member:
                            send_main_menu(chat_id)
                        else:
                            send_welcome_task_menu(chat_id)

                    elif "callback_query" in item:
                        cb = item["callback_query"]
                        cb_id = cb["id"]
                        data = cb.get("data", "")
                        chat_id = str(cb["message"]["chat"]["id"])
                        msg_id = cb["message"]["message_id"]

                        if data == "verify_task":
                            is_member = check_channel_member(chat_id)
                            target, _, is_unlocked, current_day = get_user_task_info(chat_id)
                            
                            if not is_member:
                                answer_callback(cb_id, "Access Denied: You must join the channel first.", show_alert=True)
                            else:
                                raw_referrals = USERS_DB[chat_id].get("referrals", [])
                                valid_referrals = 0
                                
                                for ref_id in raw_referrals:
                                    if check_channel_member(ref_id):
                                        valid_referrals += 1

                                if valid_referrals < target:
                                    remaining = target - valid_referrals
                                    answer_callback(cb_id, f"Access Denied: {remaining} more REAL users must JOIN the channel.", show_alert=True)
                                    send_welcome_task_menu(chat_id, msg_id)
                                else:
                                    if not is_unlocked:
                                        if "unlocked_days" not in USERS_DB[chat_id]:
                                            USERS_DB[chat_id]["unlocked_days"] = []
                                        USERS_DB[chat_id]["unlocked_days"].append(str(current_day))
                                        save_db(USERS_DB)
                                        
                                    answer_callback(cb_id, "Access Granted. Real Referrals Verified! ✅", show_alert=False)
                                    send_main_menu(chat_id, msg_id)
                                
                        elif data == "open_30S":
                            switch_view(chat_id, msg_id, "market", "30S")
                            answer_callback(cb_id)

                        elif data == "open_5M":
                            switch_view(chat_id, msg_id, "market", "5M")
                            answer_callback(cb_id)

                        elif data == "back_to_menu":
                            switch_view(chat_id, msg_id, "menu", None)
                            answer_callback(cb_id)

                        else:
                            answer_callback(cb_id)
                            
        except Exception:
            pass
            
        time.sleep(0.5)

if __name__ == "__main__":
    sync_thread = threading.Thread(target=realtime_sync_engine, daemon=True)
    sync_thread.start()
    telegram_listener()
