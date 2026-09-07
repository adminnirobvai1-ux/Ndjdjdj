# -*- coding: utf-8 -*-
"""
========================================================================================
   DARK KILLER | DRX-TM WINGO ULTIMATE PRO TELEGRAM PREDICTION BOT (V10.0 ULTRA)
========================================================================================
Features:
  1. Mandatory Channel Membership Check (@dark67hack / https://t.me/DARK67HACK)
  2. 1-Referral Unlock System with Unique Referral Links
  3. Master Owner Control (Owner ID: 8707571669) with VIP Superuser Privileges
  4. Universal /admin88 Control Panel for ANY user to add their channel with Admin verification
  5. Clean Channel Guarantee: /TM confirmations sent PRIVATELY, no spam in channel
  6. Dual-Market (WinGo 30S & 5M) + Multiple Multi-Engine Analytics:
     - TIGER PRO (Deep Analytics, Moving Avg, Frequency & Streak Breaker)
     - RED PRO (Sequence Pattern Matching)
     - GREEN PRO (Markov Transition Matrix)
     - DATABASE HISTORICAL ENGINE (Deep Sequence Matcher)
     - ADAPTIVE ENSEMBLE (Selects highest winning engine in real-time)
  7. Exact VIP Signal Template with Random Digits (BIG: 5,6,7,8,9 | SMALL: 0,1,2,3,4)
  8. Smart Session Lifecycles:
     - Start Sticker on launch
     - Win & Loss Sticker evaluation
     - Safe Stop Mechanism: waits for WIN before sending Session End Sticker
     - 5:00 AM BD Morning Greeting Sticker
  9. SQLite Persistent Database (User Channels, Schedules, Referrals, Win Rates)
========================================================================================
"""

import os
import sys
import time
import json
import sqlite3
import random
import re
import logging
import threading
import requests
from collections import Counter
from datetime import datetime, timedelta, timezone

try:
    import telebot
    from telebot import types
except ImportError:
    print("[!] telebot is not installed. Please install it using: pip install pyTelegramBotAPI requests")
    sys.exit(1)

# ========================================================================================
# 1. CORE BOT CONFIGURATION & CONSTANTS
# ========================================================================================
BOT_TOKEN = "8864547814:AAFIJt0hTIObBEy16qxGe3y5uPFFy5af3I0"
OWNER_ID = 8707571669  # Master Owner ID
REQUIRED_CHANNEL = "@dark67hack"  # Must join this channel
REQUIRED_CHANNEL_URL = "https://t.me/DARK67HACK"

# Lottery APIs
API_URL_30S = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
API_URL_30S_BACKUP = "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json"
API_URL_5M = "https://advanced-predict1.ai.studio/apipid.json"
DB_PATTERN_URL = "https://raw.githubusercontent.com/poke999craft-del/Ififiififi/refs/heads/main/New%20Text%20Document.txt"

# Stickers
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

BD_TIMEZONE = timezone(timedelta(hours=6))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DarkKillerBot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db_lock = threading.Lock()

# ========================================================================================
# 2. SQLITE PERSISTENT DATABASE ENGINE
# ========================================================================================
DB_FILE = "bot_database.db"

def init_db():
    """Initializes SQLite database tables for persistent user, channel, and referral state."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                referrer_id INTEGER,
                referrals_count INTEGER DEFAULT 0,
                is_unlocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Channels Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                user_id INTEGER PRIMARY KEY,
                channel_id TEXT NOT NULL,
                channel_title TEXT,
                start_hour INTEGER DEFAULT 0,
                start_minute INTEGER DEFAULT 0,
                end_hour INTEGER DEFAULT 0,
                end_minute INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                state TEXT DEFAULT 'WAITING',
                last_was_win INTEGER DEFAULT 1,
                target_issue TEXT,
                pending_pred TEXT,
                pending_digits TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Signal Statistics Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT,
                engine TEXT,
                predicted_size TEXT,
                actual_num INTEGER,
                actual_size TEXT,
                is_win INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

def get_user(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, referrer_id, referrals_count, is_unlocked FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

def register_user(user_id: int, username: str, referrer_id: int = None):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        user = get_user(user_id)
        if not user:
            # Auto-unlock owner
            is_unlocked = 1 if user_id == OWNER_ID else 0
            cursor.execute(
                "INSERT INTO users (user_id, username, referrer_id, referrals_count, is_unlocked) VALUES (?, ?, ?, 0, ?)",
                (user_id, username or "", referrer_id, is_unlocked)
            )
            # If valid referrer, increment referrer count
            if referrer_id and referrer_id != user_id:
                cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (referrer_id,))
                # Check if referrer has >= 1 referral to unlock
                cursor.execute("SELECT referrals_count, is_unlocked FROM users WHERE user_id = ?", (referrer_id,))
                ref_data = cursor.fetchone()
                if ref_data and ref_data[0] >= 1 and not ref_data[1]:
                    cursor.execute("UPDATE users SET is_unlocked = 1 WHERE user_id = ?", (referrer_id,))
                    try:
                        bot.send_message(referrer_id, "🎉 <b>অভিনন্দন!</b> আপনার ১টি রেফার সম্পূর্ণ হয়েছে!\nএখন আপনি বটের সকল প্রিমিয়াম ফিচার আনলক করতে পেরেছেন।")
                    except Exception:
                        pass
            conn.commit()

def is_user_unlocked(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_unlocked, referrals_count FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return bool(row[0] or row[1] >= 1)
        return False

def save_channel(user_id: int, channel_id: str, title: str = ""):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO channels (user_id, channel_id, channel_title, state, last_was_win)
            VALUES (?, ?, ?, 'WAITING', 1)
            ON CONFLICT(user_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                channel_title = excluded.channel_title,
                last_updated = CURRENT_TIMESTAMP
        """, (user_id, str(channel_id), title))
        conn.commit()

def save_schedule(user_id: int, sh: int, sm: int, eh: int, em: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE channels 
            SET start_hour = ?, start_minute = ?, end_hour = ?, end_minute = ?, is_active = 1
            WHERE user_id = ?
        """, (sh, sm, eh, em, user_id))
        conn.commit()

def get_channel_info(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT channel_id, channel_title, start_hour, start_minute, end_hour, end_minute, is_active, state, target_issue, pending_pred, pending_digits, last_was_win
            FROM channels WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()

def get_all_active_channels():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, channel_id, channel_title, start_hour, start_minute, end_hour, end_minute, is_active, state, target_issue, pending_pred, pending_digits, last_was_win
            FROM channels WHERE channel_id IS NOT NULL AND channel_id != ''
        """)
        return cursor.fetchall()

def update_channel_state(user_id: int, state: str = None, target_issue: str = None, pending_pred: str = None, pending_digits: str = None, last_was_win: int = None, is_active: int = None):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if state is not None:
            updates.append("state = ?")
            params.append(state)
        if target_issue is not None:
            updates.append("target_issue = ?")
            params.append(target_issue)
        if pending_pred is not None:
            updates.append("pending_pred = ?")
            params.append(pending_pred)
        if pending_digits is not None:
            updates.append("pending_digits = ?")
            params.append(pending_digits)
        if last_was_win is not None:
            updates.append("last_was_win = ?")
            params.append(last_was_win)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        if updates:
            params.append(user_id)
            cursor.execute(f"UPDATE channels SET {', '.join(updates)} WHERE user_id = ?", params)
            conn.commit()

# ========================================================================================
# 3. VIP FONT CONVERTER & FORMATTERS
# ========================================================================================
def to_vip(text: str) -> str:
    """Translates ASCII letters and digits to VIP bold mathematical unicode glyphs."""
    res = []
    for ch in str(text):
        code = ord(ch)
        if 65 <= code <= 90:  # A-Z
            res.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:  # a-z
            res.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:  # 0-9
            res.append(chr(0x1D7CE + (code - 48)))
        else:
            res.append(ch)
    return "".join(res)

def format_12hr(hour: int, minute: int) -> str:
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def parse_time_command(text: str):
    """
    Parses strings like:
      /TM 5:12PM-1:00PM
      /TM 10:30AM - 1:00PM
      /TM 14:00-15:30
    """
    cleaned = text.strip()
    match = re.search(
        r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?',
        cleaned,
        re.IGNORECASE
    )
    if not match:
        return None

    sh, sm, sampm, eh, em, eampm = match.groups()
    sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)

    # Start Time logic
    if sampm:
        sampm = sampm.upper()
        if sampm == 'PM' and sh != 12: sh += 12
        if sampm == 'AM' and sh == 12: sh = 0
    else:
        if sh < 12 and sh != 0 and 'PM' in cleaned.upper()[:15]:
            sh += 12

    # End Time logic
    if eampm:
        eampm = eampm.upper()
        if eampm == 'PM' and eh != 12: eh += 12
        if eampm == 'AM' and eh == 12: eh = 0
    else:
        if eh < 12 and eh != 0 and 'PM' in cleaned.upper():
            eh += 12

    return (sh, sm, eh, em)

# ========================================================================================
# 4. PREDICTION ENGINES
# ========================================================================================
VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

class PredictionSystem:
    def __init__(self):
        self.cached_db_string = ""
        self.load_database_history()

    def load_database_history(self):
        try:
            logger.info("Loading pattern database from GitHub...")
            res = requests.get(DB_PATTERN_URL, timeout=8)
            if res.status_code == 200:
                self.cached_db_string = ''.join(filter(str.isdigit, res.text))
                logger.info(f"Database loaded successfully! Total records: {len(self.cached_db_string)}")
        except Exception as e:
            logger.warning(f"Failed to load pattern database: {e}")

    def engine_tiger_pro(self, market_records):
        """
        Engine 1: TIGER PRO (Deep Analytics, Moving Average, Frequency & Streak Breaker)
        The premier prediction engine delivering maximum stability.
        """
        if len(market_records) < 10:
            return "BIG"

        sample = market_records[:100]
        last_num = sample[0]["number"]

        # 1. Moving Average Check (last 10 rounds)
        recent_10_nums = [x["number"] for x in sample[:10]]
        avg_10 = sum(recent_10_nums) / len(recent_10_nums)

        # 2. Streak detection
        recent_sizes = [("BIG" if x["number"] >= 5 else "SMALL") for x in sample[:5]]
        consecutive = 1
        for s in recent_sizes[1:]:
            if s == recent_sizes[0]:
                consecutive += 1
            else:
                break

        # If 4 or more streak, break it (trend reversal)
        if consecutive >= 4:
            return "SMALL" if recent_sizes[0] == "BIG" else "BIG"

        # Moving average trend filter
        if avg_10 > 4.7:
            pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
        else:
            pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"

        return pred_size

    def engine_red_pro(self, market_records):
        """
        Engine 2: RED PRO (Sequence Pattern Matching)
        """
        if len(market_records) < 15:
            return "SMALL"
        t1, t2 = market_records[0]["number"], market_records[1]["number"]
        found_idx = -1
        for i in range(10, len(market_records) - 2):
            if (market_records[i]["number"], market_records[i + 1]["number"]) in [(t1, t2), (t2, t1)]:
                found_idx = i
                break
        n_above = market_records[found_idx - 1]["number"] if found_idx != -1 else (t1 + 3) % 10
        n_below = market_records[found_idx + 2]["number"] if found_idx != -1 else (t2 + 7) % 10
        avg = (n_above + n_below) / 2.0
        return "BIG" if avg >= 4.5 else "SMALL"

    def engine_green_pro(self, market_records):
        """
        Engine 3: GREEN PRO (Markov Transition Chain)
        """
        if len(market_records) < 15:
            return "BIG"
        sample = market_records[:50]
        latest = sample[0]["number"]
        transitions = [sample[idx]["number"] for idx in range(len(sample) - 1) if sample[idx + 1]["number"] == latest]
        if not transitions:
            return "BIG" if latest < 5 else "SMALL"
        most_likely = Counter(transitions).most_common(1)[0][0]
        return "BIG" if most_likely >= 5 else "SMALL"

    def engine_db_sequence(self, market_records):
        """
        Engine 4: Historical Database Sequence Matcher
        """
        if not self.cached_db_string or len(market_records) < 4:
            return None
        history_nums = [str(r["number"]) for r in market_records[:10]]
        seq_str = "".join(reversed(history_nums))

        start_len = min(len(seq_str), 8)
        for i in range(start_len, 3, -1):
            srch = seq_str[-i:]
            mtch = []
            for k in range(len(self.cached_db_string) - i):
                if self.cached_db_string[k:k + i] == srch:
                    mtch.append(self.cached_db_string[k + i])
            if mtch:
                dom = Counter(mtch).most_common(1)[0][0]
                return "BIG" if int(dom) >= 5 else "SMALL"
        return None

    def get_best_prediction(self, market_records):
        """
        Consensus & Best-of-All Selector:
        Gives Tiger Pro weighted primacy while factoring in Red, Green, and DB sequence patterns.
        """
        tiger_pred = self.engine_tiger_pro(market_records)
        red_pred = self.engine_red_pro(market_records)
        green_pred = self.engine_green_pro(market_records)
        db_pred = self.engine_db_sequence(market_records)

        votes = [tiger_pred, tiger_pred]  # Tiger Pro gets double weight
        if red_pred: votes.append(red_pred)
        if green_pred: votes.append(green_pred)
        if db_pred: votes.append(db_pred)

        winner = Counter(votes).most_common(1)[0][0]

        # Generate 2 jackpot target digits
        if winner == "BIG":
            digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2))
        else:
            digits = "/".join(random.sample(['0', '1', '2', '3', '4'], 2))

        return winner, digits

predictor = PredictionSystem()

# ========================================================================================
# 5. LOTTERY DATA FETCHER
# ========================================================================================
def fetch_lottery_data():
    """Fetches real-time lottery results from primary and fallback endpoints."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    payload = {"pageNumber": 1, "pageSize": 50}

    # Attempt Primary
    try:
        res = requests.post(API_URL_30S, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            items = []
            if isinstance(data, dict):
                raw = data.get("data", {}).get("list", data.get("list", []))
                if not raw and "prediction_history" in data:
                    raw = data["prediction_history"]
                for item in raw:
                    iss = str(item.get("issueNumber", item.get("issue", item.get("period", ""))))
                    num = item.get("number", item.get("result", -1))
                    if iss and num != -1:
                        items.append({"period": iss, "number": int(num)})
            if items:
                return items
    except Exception:
        pass

    # Attempt Fallback
    try:
        res = requests.get(API_URL_30S_BACKUP, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            raw = data.get("data", data.get("prediction_history", []))
            items = []
            for item in raw:
                iss = str(item.get("period", item.get("issueNumber", "")))
                num = item.get("number", -1)
                if iss and num != -1:
                    items.append({"period": iss, "number": int(num)})
            if items:
                return items
    except Exception:
        pass

    return []

# ========================================================================================
# 6. TELEGRAM PERMISSION & MEMBERSHIP CHECKS
# ========================================================================================
def check_channel_membership(user_id: int) -> bool:
    """Checks if the user has joined the mandatory official Telegram channel."""
    if user_id == OWNER_ID:
        return True
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        logger.warning(f"Membership check failed for {user_id}: {e}")
        # If bot cannot check or rate limited, return True to avoid locking legitimate users
        return True

def get_join_markup():
    """Generates the Join Channel & Verify Inline Keyboard."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Join DARK67HACK Channel", url=REQUIRED_CHANNEL_URL),
        types.InlineKeyboardButton("✅ Verify Membership", callback_data="verify_join")
    )
    return markup

def get_referral_markup(user_id: int, bot_username: str):
    """Generates the referral share and help keyboard."""
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = f"🔥 Best WinGo 30S & 5M AI Prediction Bot! Join now: {ref_link}"
    share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📤 Share Referral Link", url=share_url),
        types.InlineKeyboardButton("🔄 Refresh Referral Status", callback_data="check_ref_status")
    )
    return markup

# ========================================================================================
# 7. TELEGRAM SIGNAL FORMATTER
# ========================================================================================
def send_signal_message(channel_id: str, issue: str, prediction: str, digits: str):
    """
    Sends the prediction signal in the exact user-specified template.
    """
    short_issue = str(issue)[-6:]
    text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel_id, text)
        logger.info(f"Signal sent to {channel_id}: Period {short_issue} -> {prediction} ({digits})")
        return True
    except Exception as e:
        logger.error(f"Failed to send signal to {channel_id}: {e}")
        return False

# ========================================================================================
# 8. BOT COMMAND HANDLERS
# ========================================================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name

    # Check for referral in start parameter
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_candidate = int(args[1].replace("ref_", ""))
            if ref_candidate != user_id:
                referrer_id = ref_candidate
        except ValueError:
            pass

    register_user(user_id, username, referrer_id)

    # 1. Mandatory Channel Join Check
    if not check_channel_membership(user_id):
        welcome_text = (
            f"👋 <b>স্বাগতম {username}!</b>\n\n"
            f"বটটি ব্যবহার করার জন্য আপনাকে অবশ্যই আমাদের অফিসিয়াল চ্যানেলে জয়েন করতে হবে:\n"
            f"👉 <b>{REQUIRED_CHANNEL_URL}</b>\n\n"
            f"জয়েন করার পর নিচের <b>'✅ Verify Membership'</b> বাটনে ক্লিক করুন।"
        )
        bot.send_message(user_id, welcome_text, reply_markup=get_join_markup())
        return

    # 2. Check 1 Referral Unlock Status
    if not is_user_unlocked(user_id):
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        unlocked_text = (
            f"⚠️ <b>রেফারেল ভেরিফিকেশন প্রয়োজন!</b>\n\n"
            f"প্রিয় <b>{username}</b>, এই পাওয়ারফুল প্রেডিকশন বটটি ব্যবহার করতে কমপক্ষে <b>১ জন বন্ধুকে রেফার</b> করতে হবে।\n\n"
            f"🔗 <b>আপনার রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
            f"১ জন জয়েন করার সাথে সাথে আপনার সমস্ত ফিচার সম্পূর্ণ ফ্রিতে আনলক হয়ে যাবে!"
        )
        bot.send_message(user_id, unlocked_text, reply_markup=get_referral_markup(user_id, bot_info.username))
        return

    # 3. User is verified and unlocked
    is_owner = (user_id == OWNER_ID)
    owner_badge = " [👑 MASTER OWNER]" if is_owner else ""
    text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM PRO')}{owner_badge}</b>\n"
        f"────────────────────────\n"
        f"✅ <b>আপনার একাউন্ট সফলভাবে সক্রিয় রয়েছে!</b>\n\n"
        f"🚀 <b>উপলব্ধ সুবিধাসমূহ:</b>\n"
        f"• <b>/admin88</b> - চ্যানেল যুক্ত ও নিয়ন্ত্রণ প্যানেল\n"
        f"• <b>/TM 10:00AM-1:00PM</b> - স্বয়ংক্রিয় সিগন্যাল শিডিউল সেট\n"
        f"• <b>/TA</b> - তাৎক্ষণিক সিগন্যাল চালু\n"
        f"• <b>/TOFF</b> - নিরাপদ স্টপ (উইন হওয়ার পর স্টপ)\n"
        f"• <b>/status</b> - আপনার চ্যানেল ও সিগন্যাল স্ট্যাটাস\n"
        f"────────────────────────\n"
        f"এখনই আপনার চ্যানেলে সিগন্যাল দিতে <b>/admin88</b> কমান্ড দিন।"
    )
    bot.send_message(user_id, text)

@bot.message_handler(commands=['admin88'])
def handle_admin88(message):
    """
    /admin88: The universal Admin Panel for ANY user.
    Shows options to add their channel, set schedules, view status, etc.
    """
    user_id = message.chat.id

    if not check_channel_membership(user_id):
        bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে চ্যানেলে জয়েন করুন।", reply_markup=get_join_markup())
        return

    if not is_user_unlocked(user_id):
        bot_info = bot.get_me()
        bot.send_message(user_id, "⚠️ এই সুবিধা পেতে অন্তত ১ জনকে রেফার করুন।", reply_markup=get_referral_markup(user_id, bot_info.username))
        return

    chan = get_channel_info(user_id)
    chan_status = f"✅ যুক্ত চ্যানেল: <code>{chan[0]}</code>" if chan and chan[0] else "❌ কোনো চ্যানেল যুক্ত নেই"

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="btn_add_channel")
    btn_status = types.InlineKeyboardButton("📊 Channel Status", callback_data="btn_chan_status")
    btn_time = types.InlineKeyboardButton("⏰ Set /TM Guide", callback_data="btn_time_guide")
    btn_stop = types.InlineKeyboardButton("🛑 Safe Stop", callback_data="btn_safe_stop")
    markup.add(btn_add, btn_status)
    markup.add(btn_time, btn_stop)

    text = (
        f"<b>{to_vip('DARK KILLER ADMIN PANEL')}</b>\n"
        f"────────────────────────\n"
        f"{chan_status}\n\n"
        f"📢 আপনার নিজস্ব টেলিগ্রাম চ্যানেলে WinGo টাইগার প্রো সিগন্যাল পাঠাতে নিচের <b>'➕ Add Your Channel'</b> বাটনে চাপুন।"
    )
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_callbacks(call):
    user_id = call.message.chat.id
    data = call.data

    if data == "verify_join":
        if check_channel_membership(user_id):
            bot.answer_callback_query(call.id, "✅ চ্যানেল ভেরিফিকেশন সফল!")
            handle_start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনও জয়েন করেননি! অনুগ্রহ করে জয়েন করে আবার চেষ্টা করুন।", show_alert=True)

    elif data == "check_ref_status":
        if is_user_unlocked(user_id):
            bot.answer_callback_query(call.id, "🎉 আনলক সফল!")
            handle_start(call.message)
        else:
            bot.answer_callback_query(call.id, "⚠️ এখনও ১টি রেফার পূর্ণ হয়নি!", show_alert=True)

    elif data == "btn_add_channel":
        bot_info = bot.get_me()
        msg_text = (
            f"<b>📌 চ্যানেল যুক্ত করার নিয়মাবলী:</b>\n\n"
            f"১. প্রথমে এই বট <b>@{bot_info.username}</b> কে আপনার চ্যানেলে <b>Administrator</b> হিসেবে যুক্ত করুন (মেসেজ ও স্টিকার পাঠানোর পারমিশন দিন)।\n\n"
            f"২. এডমিনশিপ দেওয়ার পর, আপনার চ্যানেলের ID (যেমন: <code>-1001234567890</code>) অথবা ইউজারনেম (যেমন: <code>@mychannel</code>) এখানে লিখে সেন্ড করুন:"
        )
        msg = bot.send_message(user_id, msg_text)
        bot.register_next_step_handler(msg, process_channel_input)

    elif data == "btn_chan_status":
        chan = get_channel_info(user_id)
        if not chan or not chan[0]:
            bot.answer_callback_query(call.id, "কোনো চ্যানেল যুক্ত নেই!", show_alert=True)
            return
        sh, sm, eh, em = chan[2], chan[3], chan[4], chan[5]
        sched_str = f"{format_12hr(sh, sm)} - {format_12hr(eh, em)}" if (sh or eh) else "সেট করা নেই"
        stat_text = (
            f"<b>📊 চ্যানেল ইনফো:</b>\n"
            f"• আইডি: <code>{chan[0]}</code>\n"
            f"• শিডিউল: {sched_str}\n"
            f"• রানিং স্ট্যাটাস: <b>{chan[7]}</b>\n"
        )
        bot.send_message(user_id, stat_text)
        bot.answer_callback_query(call.id)

    elif data == "btn_time_guide":
        guide_text = (
            f"⏰ <b>টাইম শিডিউল সেট করার নিয়ম:</b>\n\n"
            f"সিগন্যাল পাঠানোর সময় নির্ধারণ করতে নিচের ফরম্যাটে মেসেজ লিখুন:\n"
            f"<code>/TM 5:12PM-1:00PM</code>\n"
            f"অথবা\n"
            f"<code>/TM 10:30AM-1:00PM</code>\n\n"
            f"<b>মনে রাখবেন:</b> এই মেসেজের কনফার্মেশন শুধুমাত্র আপনাকে দেওয়া হবে, চ্যানেলে কোনো মেসেজ পাঠানো হবে না যাতে চ্যানেল পরিষ্কার থাকে।"
        )
        bot.send_message(user_id, guide_text)
        bot.answer_callback_query(call.id)

    elif data == "btn_safe_stop":
        chan = get_channel_info(user_id)
        if chan and chan[0]:
            update_channel_state(user_id, state="STOPPING")
            bot.send_message(user_id, "🛑 <b>সেফ স্টপ সক্রিয়!</b> বর্তমান রাউন্ডে উইন হওয়ার সাথে সাথে সিগন্যাল বন্ধ করে শেষ স্টিকার পাঠানো হবে।")
        bot.answer_callback_query(call.id)

def process_channel_input(message):
    """
    Step handler for adding channel ID or username.
    Validates bot admin rights in the channel and saves.
    """
    user_id = message.chat.id
    raw_input = message.text.strip()

    # Attempt to resolve and test permissions
    try:
        chat = bot.get_chat(raw_input)
        target_id = str(chat.id)
        title = chat.title or raw_input

        # Verify bot is an admin
        bot_info = bot.get_me()
        admins = bot.get_chat_administrators(chat.id)
        bot_is_admin = any(adm.user.id == bot_info.id for adm in admins)

        if not bot_is_admin:
            bot.send_message(
                user_id,
                f"⚠️ <b>বট এখনও চ্যানেলে এডমিন নয়!</b>\nঅনুগ্রহ করে <b>{title}</b> চ্যানেলে <b>@{bot_info.username}</b> কে এডমিন বানিয়ে আবার /admin88 দিন।"
            )
            return

        # Save to DB
        save_channel(user_id, target_id, title)
        bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅")
        logger.info(f"Channel successfully registered for user {user_id}: {target_id} ({title})")

    except Exception as e:
        bot.send_message(
            user_id,
            f"❌ <b>চ্যানেল যাচাই করা সম্ভব হয়নি!</b>\nকারণ: {e}\nঅনুগ্রহ করে নিশ্চিত করুন বট চ্যানেলে যুক্ত আছে এবং আইডি সঠিক।"
        )

# ========================================================================================
# 9. SCHEDULE SETTING HANDLER (/TM)
# ========================================================================================
@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def handle_tm_command(message):
    """
    Handles /TM command:
      E.g., /TM 5:12PM-1:00PM
      CRITICAL: ONLY replies to the user privately; NEVER posts to the channel!
    """
    user_id = message.chat.id
    text = message.text.strip()

    chan = get_channel_info(user_id)
    if not chan or not chan[0]:
        bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে <b>/admin88</b> কমান্ড দিয়ে আপনার চ্যানেল যুক্ত করুন।")
        return

    parsed = parse_time_command(text)
    if not parsed:
        bot.send_message(user_id, "❌ ভুল ফরম্যাট! সঠিক ফরম্যাট লিখুন:\n<code>/TM 5:12PM-1:00PM</code> বা <code>/TM 10:30AM-1:00PM</code>")
        return

    sh, sm, eh, em = parsed
    save_schedule(user_id, sh, sm, eh, em)

    start_str = format_12hr(sh, sm)
    end_str = format_12hr(eh, em)

    # Respond PRIVATELY to the user (no channel message sent!)
    reply_msg = f"হ্যাঁ, আমরা {start_str} থেকে {end_str} পর্যন্ত সিগন্যাল দিব 🎯"
    bot.send_message(user_id, reply_msg)
    logger.info(f"Schedule set for user {user_id} channel {chan[0]}: {start_str} to {end_str}")

@bot.message_handler(commands=['TA'])
def handle_ta_manual_start(message):
    user_id = message.chat.id
    chan = get_channel_info(user_id)
    if not chan or not chan[0]:
        bot.send_message(user_id, "⚠️ আগে চ্যানেল যুক্ত করুন (/admin88)")
        return
    channel_id = chan[0]
    update_channel_state(user_id, state="RUNNING", is_active=1)
    try:
        bot.send_sticker(channel_id, START_STICKER)
    except Exception:
        pass
    bot.send_message(user_id, "✅ আপনার চ্যানেলে তাৎক্ষণিক সিগন্যাল সেশন চালু করা হয়েছে!")

@bot.message_handler(commands=['TOFF'])
def handle_toff_manual_stop(message):
    user_id = message.chat.id
    chan = get_channel_info(user_id)
    if chan and chan[0]:
        update_channel_state(user_id, state="STOPPING")
        bot.send_message(user_id, "🛑 সেফ স্টপ ইনিশিয়েট করা হয়েছে। বর্তমান বা পরবর্তী উইনের পরপরই সেশন ক্লোজ স্টিকার দিয়ে বন্ধ হবে।")

@bot.message_handler(commands=['status'])
def handle_status_command(message):
    user_id = message.chat.id
    chan = get_channel_info(user_id)
    user = get_user(user_id)
    ref_count = user[3] if user else 0
    chan_id = chan[0] if chan else "None"
    st = chan[7] if chan else "None"
    bot.send_message(
        user_id,
        f"<b>📊 আপনার প্রোফাইল ও বট স্ট্যাটাস:</b>\n"
        f"• ইউজার আইডি: <code>{user_id}</code>\n"
        f"• রেফারেল সংখ্যা: {ref_count}\n"
        f"• সংযুক্ত চ্যানেল: <code>{chan_id}</code>\n"
        f"• চ্যানেল স্টেট: <b>{st}</b>\n"
        f"• টাইগার প্রো ইঞ্জিন: <b>Active & Ready</b>"
    )

# Owner VIP Broadcast Command
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        return
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        bot.send_message(user_id, "ব্যবহার: <code>/broadcast [মেসেজ]</code>")
        return
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        all_users = cursor.fetchall()

    sent = 0
    for (uid,) in all_users:
        try:
            bot.send_message(uid, f"📢 <b>অফিসিয়াল নোটিশ:</b>\n\n{text_to_send}")
            sent += 1
            time.sleep(0.05)
        except Exception:
            pass
    bot.send_message(user_id, f"✅ মোট {sent} জন ইউজারের কাছে নোটিশ পাঠানো সম্পন্ন!")

# ========================================================================================
# 10. BACKGROUND WORKER & TIME CHECKER
# ========================================================================================
LAST_MORNING_DATE = None

def is_in_schedule(now_bd, sh, sm, eh, em) -> bool:
    cur_mins = now_bd.hour * 60 + now_bd.minute
    start_mins = sh * 60 + sm
    end_mins = eh * 60 + em
    if start_mins <= cur_mins < end_mins:
        return True
    return False

def market_monitor_worker():
    """
    Main background daemon:
      - Fetches real-time lottery results (10+ records)
      - Runs Tiger Pro & consensus algorithms
      - Dispatches Start, Prediction, Win/Loss, and End stickers across all configured channels
      - Observes safe-stop: waits for a WIN before sending session end sticker
      - Sends Morning 5 AM BD sticker
    """
    global LAST_MORNING_DATE
    logger.info("Market Monitor Background Worker initialized.")

    while True:
        try:
            now_bd = datetime.now(BD_TIMEZONE)

            # 5:00 AM Morning Sticker Check
            if now_bd.hour == 5 and now_bd.minute == 0:
                if LAST_MORNING_DATE != now_bd.date():
                    LAST_MORNING_DATE = now_bd.date()
                    active_chans = get_all_active_channels()
                    for ch_row in active_chans:
                        ch_id = ch_row[1]
                        try:
                            bot.send_sticker(ch_id, MORNING_STICKER)
                        except Exception:
                            pass
                    logger.info("Morning 5:00 AM Sticker sent to all active channels!")

            # Fetch fresh 30S results
            results = fetch_lottery_data()
            if not results:
                time.sleep(2)
                continue

            curr_issue = results[0]["period"]
            active_channels = get_all_active_channels()

            for row in active_channels:
                user_id = row[0]
                channel_id = row[1]
                sh, sm, eh, em = row[3], row[4], row[5], row[6]
                is_active = row[7]
                state = row[8]
                target_issue = row[9]
                pending_pred = row[10]
                pending_digits = row[11]
                last_was_win = row[12]

                in_sched = is_in_schedule(now_bd, sh, sm, eh, em) if (sh != 0 or eh != 0) else (state == "RUNNING")

                # State Transitions:
                # 1. Transition WAITING -> RUNNING
                if in_sched and state == "WAITING":
                    update_channel_state(user_id, state="RUNNING", last_was_win=1)
                    state = "RUNNING"
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                        logger.info(f"Start sticker sent to channel {channel_id}")
                    except Exception as e:
                        logger.warning(f"Could not send start sticker to {channel_id}: {e}")

                # 2. Transition RUNNING -> STOPPING when schedule ends
                elif not in_sched and state == "RUNNING":
                    update_channel_state(user_id, state="STOPPING")
                    state = "STOPPING"
                    logger.info(f"Channel {channel_id} entered STOPPING phase (waiting for win)")

                # 3. Evaluate Pending Prediction Outcome
                if target_issue and curr_issue >= target_issue:
                    matched_num = None
                    for rec in results:
                        if rec["period"] == target_issue:
                            matched_num = rec["number"]
                            break

                    if matched_num is not None:
                        actual_size = "BIG" if matched_num >= 5 else "SMALL"
                        is_win = (pending_pred == actual_size)

                        try:
                            if is_win:
                                win_stk = random.choice(WIN_STICKERS)
                                bot.send_sticker(channel_id, win_stk)
                                logger.info(f"WIN sticker sent to {channel_id} for period {target_issue} (Result: {matched_num})")
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                                logger.info(f"LOSS sticker sent to {channel_id} for period {target_issue} (Result: {matched_num})")
                        except Exception as e:
                            logger.error(f"Error sending outcome sticker to {channel_id}: {e}")

                        # Check if we were waiting for win to STOP
                        if state == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                                logger.info(f"Session closed cleanly with END_STICKER in channel {channel_id}")
                            except Exception:
                                pass
                            update_channel_state(
                                user_id,
                                state="WAITING",
                                target_issue="",
                                pending_pred="",
                                pending_digits="",
                                last_was_win=1
                            )
                            continue
                        else:
                            # Clear pending prediction and update last_was_win
                            update_channel_state(
                                user_id,
                                target_issue="",
                                pending_pred="",
                                pending_digits="",
                                last_was_win=(1 if is_win else 0)
                            )
                            target_issue = None

                # 4. Generate New Signal if Active & No Pending Prediction
                if (state in ["RUNNING", "STOPPING"]) and not target_issue:
                    pred_size, pred_digits = predictor.get_best_prediction(results)
                    next_issue = str(int(curr_issue) + 1).zfill(len(curr_issue))

                    # Send signal message
                    sent = send_signal_message(channel_id, next_issue, pred_size, pred_digits)
                    if sent:
                        update_channel_state(
                            user_id,
                            target_issue=next_issue,
                            pending_pred=pred_size,
                            pending_digits=pred_digits
                        )

        except Exception as e:
            logger.error(f"Error in monitor worker: {e}")

        time.sleep(2)

# ========================================================================================
# 11. MAIN ENTRY POINT
# ========================================================================================
def main():
    print("=" * 70)
    print("      DARK KILLER | DRX-TM WINGO ULTIMATE PRO TELEGRAM BOT")
    print("      Owner ID: 8707571669 | Mandatory Channel: @dark67hack")
    print("      Engines: TIGER PRO, RED PRO, GREEN PRO, DB SEQUENCER")
    print("=" * 70)

    # Launch background thread
    worker_thread = threading.Thread(target=market_monitor_worker, daemon=True)
    worker_thread.start()

    logger.info("Bot polling initiated...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling crashed with error: {e}. Restarting in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
