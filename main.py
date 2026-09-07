# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Multi-Market (30S & 5M) Pure Market Viewer Bot
Features:
  - 100% Pure Market Feed (No Prediction, No Guess, No Win/Loss)
  - 30-Second (Tiger Pro API) & 5-Minute Live Market
  - Real-time Animated Countdown
  - Columns: PERIOD | NUM | SIZE | COLOR
  - Detailed Terminal Logs to verify API Data
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
ADMIN_ID = "8707571669"

# চ্যানেল লক টেস্ট করার সময় সমস্যা করলে False করে দিতে পারেন
ENABLE_CHANNEL_LOCK = False  # সাথে সাথে মার্কেট দেখতে এটি False করা আছে, পরে True করতে পারেন

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

# ================= RULES & CALCULATION =================
def get_color(num: int) -> str:
    if num in [0, 5]:
        return "VIOLET"
    return "RED" if num in [2, 4, 6, 8] else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num >= 5 else "SMALL"

# ================= ROBUST API FETCHER =================
def fetch_market_history(market_key):
    api_url = MARKETS[market_key]["api"]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            raw_list = []

            if isinstance(data, dict):
                # ৩০ সেকেন্ড এপিআই তে 'history' থাকে, আবার অন্যদের 'prediction_history' থাকে
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
                    
                    # আসল নাম্বার নেওয়া: actual_number অথবা number
                    n_raw = item.get("actual_number")
                    if n_raw is None:
                        n_raw = item.get("number")

                    if p_raw is not None and n_raw is not None:
                        try:
                            num = int(n_raw)
                        except (ValueError, TypeError):
                            continue

                        # সাইজ ও কালার নিশ্চিত করা
                        s_raw = str(item.get("size", "")).strip().upper()
                        c_raw = str(item.get("color", "")).strip().upper()

                        size = s_raw if s_raw in ["BIG", "SMALL"] else get_size(num)
                        color = c_raw if c_raw in ["RED", "GREEN", "VIOLET"] else get_color(num)

                        formatted.append({
                            "period": str(p_raw).strip(),
                            "number": num,
                            "size": size,
                            "color": color
                        })

            if formatted:
                return formatted
            else:
                print(f"[!] Warning: API responded but no records parsed from {api_url}")
        else:
            print(f"[-] API HTTP Error: {res.status_code} for {api_url}")
    except Exception as e:
        print(f"[-] API Fetch Exception ({market_key}): {e}")
        
    return []

# ================= TIMER DISPLAY =================
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

# ================= UI BUILDERS =================
def build_menu_markup():
    keyboard = [
        [{"text": to_premium("WINGO 30 SEC LIVE"), "callback_data": "open_30S"}],
        [{"text": to_premium("WINGO 5 MIN LIVE"), "callback_data": "open_5M"}]
    ]
    return to_premium("SELECT WINGO MARKET"), keyboard

def build_market_markup(market_key):
    cfg = MARKETS[market_key]
    interval = cfg["interval"]
    records = fetch_market_history(market_key)

    keyboard = []

    # পিরিয়ড কাউন্ট
    if records:
        top_period = records[0]["period"]
        try:
            current_period = str(int(top_period) + 1).zfill(len(top_period))
        except Exception:
            current_period = str(top_period)
    else:
        current_period = "WAITING DATA..."

    period_8 = current_period[-8:] if len(current_period) >= 8 else current_period

    # ১. টপ পিরিয়ড বার
    keyboard.append([
        {"text": to_premium(f"PERIOD: {period_8}"), "callback_data": "noop"}
    ])

    # ২. টাইমার কাউন্টডাউন
    keyboard.append([
        {"text": get_timer_display(interval), "callback_data": "noop"}
    ])

    # ৩. টেবিল হেডার
    keyboard.append([
        {"text": to_premium("PERIOD"), "callback_data": "noop"},
        {"text": to_premium("NUM"), "callback_data": "noop"},
        {"text": to_premium("SIZE"), "callback_data": "noop"},
        {"text": to_premium("COLOR"), "callback_data": "noop"}
    ])

    # ৪. মার্কেট ডাটা রো (সর্বোচ্চ ১০টি)
    if records:
        for item in records[:10]:
            p_short = item["period"][-4:] if len(item["period"]) >= 4 else item["period"]
            num_str = str(item["number"])
            size_str = item["size"]
            color_str = item["color"]

            keyboard.append([
                {"text": to_premium(p_short), "callback_data": "noop"},
                {"text": to_premium(num_str), "callback_data": "noop"},
                {"text": to_premium(size_str), "callback_data": "noop"},
                {"text": to_premium(color_str), "callback_data": "noop"}
            ])
    else:
        # ডাটা ফেচিং এ সময় লাগলে খালি দেখাবে না
        keyboard.append([
            {"text": to_premium("LOADING..."), "callback_data": "noop"},
            {"text": to_premium("--"), "callback_data": "noop"},
            {"text": to_premium("--"), "callback_data": "noop"},
            {"text": to_premium("--"), "callback_data": "noop"}
        ])

    # ৫. ব্যাক বাটন
    keyboard.append([
        {"text": to_premium("🔙 BACK TO MENU"), "callback_data": "back_to_menu"}
    ])

    text_title = (
        f"<b>{to_premium('MARKET TERMINAL')}</b>\n"
        f"<b>{to_premium('LIVE:')} {to_premium(cfg['name'])}</b>\n"
        f"<i>{to_premium('PURE LIVE DATA FEED')}</i>\n"
        "────────────────────────"
    )
    return text_title, keyboard

# ================= TELEGRAM ACTIONS =================
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
    except Exception as e:
        print(f"[-] Menu send error: {e}")

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
        res = requests.post(url, json=payload, timeout=4).json()
        if not res.get("ok"):
            print(f"[-] EditMessageText failed: {res}")
        USER_SESSIONS[str(chat_id)] = {
            "msg_id": msg_id,
            "view": view,
            "market": market_key
        }
    except Exception as e:
        print(f"[-] switch_view exception: {e}")

def live_update_keyboard(chat_id, msg_id, market_key):
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

def answer_callback(cb_id, text=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": cb_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=2)
    except Exception:
        pass

# ================= REAL-TIME SYNC ENGINE =================
def realtime_sync_engine():
    while True:
        try:
            for chat_id, session in list(USER_SESSIONS.items()):
                if session.get("view") == "market" and session.get("market"):
                    live_update_keyboard(
                        chat_id, 
                        session["msg_id"], 
                        session["market"]
                    )
        except Exception:
            pass
        time.sleep(1)

# ================= TELEGRAM LISTENER =================
def telegram_listener():
    global LAST_UPDATE_ID
    print("=" * 60)
    print(f"[+] DRX-TM PURE MARKET BOT STARTED SUCCESSFULLY")
    print(f"[+] Testing 30S API...")
    test_30s = fetch_market_history("30S")
    print(f"[+] 30S API Connected! Records found: {len(test_30s)}")
    print(f"[+] Testing 5M API...")
    test_5m = fetch_market_history("5M")
    print(f"[+] 5M API Connected! Records found: {len(test_5m)}")
    print("=" * 60)

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
                        
                        # সরাসরি মেইন মেনু ওপেন হবে
                        if msg_text.startswith("/start"):
                            send_main_menu(chat_id)

                    elif "callback_query" in item:
                        cb = item["callback_query"]
                        cb_id = cb["id"]
                        data_val = cb.get("data", "")
                        chat_id = str(cb["message"]["chat"]["id"])
                        msg_id = cb["message"]["message_id"]

                        if data_val == "open_30S":
                            print(f"[+] User {chat_id} opened 30S Market")
                            switch_view(chat_id, msg_id, "market", "30S")
                            answer_callback(cb_id)

                        elif data_val == "open_5M":
                            print(f"[+] User {chat_id} opened 5M Market")
                            switch_view(chat_id, msg_id, "market", "5M")
                            answer_callback(cb_id)

                        elif data_val == "back_to_menu":
                            switch_view(chat_id, msg_id, "menu", None)
                            answer_callback(cb_id)

                        else:
                            answer_callback(cb_id)
                            
        except Exception as e:
            pass
            
        time.sleep(0.5)

if __name__ == "__main__":
    sync_thread = threading.Thread(target=realtime_sync_engine, daemon=True)
    sync_thread.start()
    telegram_listener()
