# -*- coding: utf-8 -*-
"""
DRX-TM WinGo 30-Second Professional Dual-Engine Prediction Telegram Bot
Features:
  - 30-Second Auto Synchronization
  - SQLite Persistent Database Storage (All historical draws saved permanently)
  - Zero Emoji Clean Professional UI
  - In-Place Message Overwrite (Seamless Window Replacement)
  - Engine 1: RED PRO WINNER (Pattern Search + Affinity Resolution)
  - Engine 2: GREEN PRO WINNER (150-Rounds Markov Transition 3-Digit Sniper)
  - Progressive 50-Pages Dynamic Display
API Endpoint: https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json
"""

import time
import json
import sqlite3
import logging
import threading
import requests
from collections import Counter
from datetime import datetime, timedelta
import telebot
from telebot import types

# =========================================================
# CONFIGURATION
# =========================================================
BOT_TOKEN = "8949748635:AAF9w3mFRx2fqcE6AslsrR7AUuNJQzqB-PA"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
MARKET_INTERVAL = 30   # ৩০ সেকেন্ড মার্কেট
TOTAL_PAGES = 50       # ৫০ পেজ (প্রতি পেজে ১০টি করে ৫০০ রেকর্ড)
DB_NAME = "wingo30s_history.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# DATABASE MANAGER (SQLITE PERSISTENT STORAGE)
# =========================================================
def init_database():
    """ডাটাবেজ টেবিল ইনিশিয়ালাইজ করে"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_history (
                period TEXT PRIMARY KEY,
                number INTEGER,
                size TEXT,
                color TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                period TEXT,
                engine TEXT,
                size TEXT,
                num TEXT,
                color TEXT,
                outcome TEXT DEFAULT '--',
                PRIMARY KEY (period, engine)
            )
        """)
        conn.commit()

def db_save_market_records(records):
    """নতুন মার্কেট ডাটা ডাটাবেজে স্থায়ীভাবে সেভ করে"""
    if not records:
        return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR IGNORE INTO market_history (period, number, size, color)
            VALUES (?, ?, ?, ?)
        """, [(r["period"], r["number"], r["size"], r["color"]) for r in records])
        conn.commit()

def db_get_recent_records(limit=500):
    """ডাটাবেজ থেকে সর্বশেষ রেকর্ডগুলো নিয়ে আসে"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT period, number, size, color 
            FROM market_history 
            ORDER BY CAST(period AS INTEGER) DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [{"period": str(r[0]), "number": r[1], "size": r[2], "color": r[3]} for r in rows]

def db_save_prediction(period, engine, size, num, color):
    """প্রেডিকশন ডাটাবেজে রেকর্ড করে"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO predictions (period, engine, size, num, color, outcome)
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT outcome FROM predictions WHERE period=? AND engine=?), '--'))
        """, (period, engine, size, num, color, period, engine))
        conn.commit()

def db_update_outcome(period, engine, outcome):
    """প্রেডিকশনের ফলাফল সেভ করে"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE predictions SET outcome = ? WHERE period = ? AND engine = ?
        """, (outcome, period, engine))
        conn.commit()

def db_get_outcomes(engine):
    """নির্দিষ্ট ইঞ্জিনের ফলাফল লোড করে"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT period, outcome FROM predictions WHERE engine = ?", (engine,))
        return dict(cursor.fetchall())

# =========================================================
# VIP FONT ENGINE (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
# =========================================================
def to_vip(text: str) -> str:
    """টেক্সটকে বোল্ড প্রিমিয়াম ভিআইপি ফন্টে রূপান্তর করে"""
    res = []
    for ch in str(text):
        code = ord(ch)
        if 65 <= code <= 90:     # A-Z -> 𝐀-𝐙
            res.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:  # a-z -> 𝐚-𝐳
            res.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:   # 0-9 -> 𝟎-𝟗
            res.append(chr(0x1D7CE + (code - 48)))
        else:
            res.append(ch)
    return "".join(res)

# =========================================================
# RULES & AFFINITY DEFINITIONS
# =========================================================
VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

GREEN_AFFINITY = {1, 3, 5, 7, 9}
RED_AFFINITY = {0, 2, 4, 6, 8}

def get_color(num: int) -> str:
    if num in VIOLET_NUMBERS:
        return "VIOLET"
    return "RED" if num in RED_NUMBERS else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num in BIG_NUMBERS else "SMALL"

# =========================================================
# STATE MANAGEMENT
# =========================================================
class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_period = ""
        self.market_data = []          # ডাটাবেজ ও মেমোরি সমন্বিত ৫০ পেজের ডাটা

        # RED PRO WINNER স্টোরেজ
        self.pred_red = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_red = {}
        self.win_loss_red = {}

        # GREEN PRO WINNER স্টোরেজ
        self.pred_green = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_green = {}
        self.win_loss_green = {}

        # সক্রিয় চ্যাট লিস্ট: {chat_id: {"message_id": int, "page": int, "mode": "RED"|"GREEN"}}
        self.active_chats = {}

    def reload_from_db(self):
        with self.lock:
            self.market_data = db_get_recent_records(TOTAL_PAGES * 10)
            self.win_loss_red = db_get_outcomes("RED")
            self.win_loss_green = db_get_outcomes("GREEN")

state = BotState()

# =========================================================
# API FETCHER (WINGO 30S JSON ADAPTER)
# =========================================================
def fetch_api_market():
    """30-Second API থেকে ডাটা সংগ্রহ করে প্রসেস করে"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        resp = requests.get(API_URL, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = []

            if isinstance(data, dict):
                # ar-lottery ও অন্যান্য সাধারণ ফরম্যাট হ্যান্ডলার
                if "data" in data and isinstance(data["data"], dict):
                    raw_list = data["data"].get("list", []) or data["data"].get("records", [])
                elif "data" in data and isinstance(data["data"], list):
                    raw_list = data["data"]
                elif "list" in data and isinstance(data["list"], list):
                    raw_list = data["list"]
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                if isinstance(item, dict):
                    p_raw = item.get("issueNumber") or item.get("period") or item.get("issue")
                    n_raw = item.get("number") or item.get("openNumber") or item.get("num")

                    if p_raw is not None and n_raw is not None:
                        period = str(p_raw).strip()
                        try:
                            num = int(str(n_raw).split(",")[-1].strip())
                        except (ValueError, TypeError):
                            continue

                        s_raw = str(item.get("size") or item.get("bigSmall") or "").strip().upper()
                        c_raw = str(item.get("colour") or item.get("color") or "").strip().upper()

                        size = s_raw if s_raw in ["BIG", "SMALL"] else get_size(num)
                        color = c_raw if c_raw in ["RED", "GREEN", "VIOLET"] else get_color(num)

                        formatted.append({
                            "period": period,
                            "number": num,
                            "size": size,
                            "color": color
                        })

            if formatted:
                return formatted
    except Exception as e:
        logger.error(f"API Fetch Error (30S): {e}")
    return []

# =========================================================
# ENGINE 1: RED PRO WINNER
# =========================================================
def calculate_red_pro_prediction(market_records):
    if len(market_records) < 5:
        return {"size": "BIG", "num": "2,8", "color": "RED"}

    t1 = market_records[0]["number"]
    t2 = market_records[1]["number"]

    found_idx = -1
    for i in range(2, len(market_records) - 2):
        curr_pair = (market_records[i]["number"], market_records[i + 1]["number"])
        if curr_pair == (t1, t2) or curr_pair == (t2, t1):
            if i - 1 >= 0 and i + 2 < len(market_records):
                found_idx = i
                break

    if found_idx == -1:
        n_above = (t1 + 3) % 10
        n_below = (t2 + 7) % 10
    else:
        n_above = market_records[found_idx - 1]["number"]
        n_below = market_records[found_idx + 2]["number"]

    pair_nums = {n_above, n_below}

    if pair_nums.issubset(GREEN_AFFINITY) or (9 in pair_nums and 5 in pair_nums) or (3 in pair_nums and 5 in pair_nums) or (9 in pair_nums and 3 in pair_nums):
        pred_color = "GREEN"
    elif pair_nums.issubset(RED_AFFINITY) or (0 in pair_nums and any(x in RED_NUMBERS for x in pair_nums)):
        pred_color = "RED"
    else:
        c_above = get_color(n_above)
        c_below = get_color(n_below)
        pred_color = c_above if c_above == c_below else "GREEN"

    if (9 in pair_nums and 5 in pair_nums) or (9 in pair_nums and 3 in pair_nums):
        pred_size = "BIG"
    elif n_above >= 5 and n_below >= 5:
        pred_size = "BIG"
    elif n_above < 5 and n_below < 5:
        pred_size = "SMALL"
    else:
        avg = (n_above + n_below) / 2.0
        pred_size = "BIG" if avg >= 4.5 else "SMALL"

    return {
        "size": pred_size,
        "num": f"{n_above},{n_below}",
        "color": pred_color
    }

# =========================================================
# ENGINE 2: GREEN PRO WINNER
# =========================================================
def calculate_green_pro_prediction(market_records):
    if len(market_records) < 5:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}

    sample = market_records[:150]
    latest_num = sample[0]["number"]

    transitions = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == latest_num:
            transitions.append(sample[idx]["number"])

    follow_up_candidates = [n for n, _ in Counter(transitions).most_common(2)]
    recent_40 = [r["number"] for r in sample[:40]]
    hot_candidates = [n for n, _ in Counter(recent_40).most_common(3)]
    mirror_candidate = (9 - latest_num)

    predicted_pool = []
    for c in follow_up_candidates + hot_candidates + [mirror_candidate, (latest_num + 3) % 10, (latest_num + 7) % 10]:
        if c not in predicted_pool and 0 <= c <= 9:
            predicted_pool.append(c)
        if len(predicted_pool) == 3:
            break

    target_3_numbers = sorted(predicted_pool)
    num_str = f"{target_3_numbers[0]},{target_3_numbers[1]},{target_3_numbers[2]}"

    sizes_last_10 = [r["size"] for r in sample[:10]]
    big_count = sizes_last_10.count("BIG")
    if big_count >= 7:
        pred_size = "SMALL"
    elif big_count <= 3:
        pred_size = "BIG"
    else:
        big_in_target = sum(1 for n in target_3_numbers if n >= 5)
        pred_size = "BIG" if big_in_target >= 2 else "SMALL"

    colors_last_10 = [r["color"] for r in sample[:10]]
    green_count = colors_last_10.count("GREEN")
    red_count = colors_last_10.count("RED")

    if green_count > red_count:
        pred_color = "GREEN" if (colors_last_10[0] != "GREEN" or green_count >= 6) else "RED"
    else:
        pred_color = "RED" if (colors_last_10[0] != "RED" or red_count >= 6) else "GREEN"

    return {
        "size": pred_size,
        "num": num_str,
        "color": pred_color
    }

# =========================================================
# CLEAN PROFESSIONAL UI BUILDERS
# =========================================================
def get_start_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_red = types.InlineKeyboardButton(to_vip("RED PRO WINNER"), callback_data="launch_RED")
    btn_green = types.InlineKeyboardButton(to_vip("GREEN PRO WINNER"), callback_data="launch_GREEN")
    markup.add(btn_red, btn_green)
    return markup

def get_dashboard_header(mode: str) -> str:
    mode_name = "RED PRO WINNER" if mode == "RED" else "GREEN PRO WINNER"
    return (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(mode_name)} | 30S</b>\n"
        "────────────────────────"
    )

def create_market_markup(page: int = 1, mode: str = "RED"):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. বর্তমান পিরিয়ড
    period_str = state.current_period or "SYNCING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # ২. ৩০ সেকেন্ড টাইমার ও প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % MARKET_INTERVAL
    remaining = MARKET_INTERVAL - elapsed

    total_blocks = 15
    filled_blocks = int((elapsed / MARKET_INTERVAL) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. প্রেডিকশন
    pred = state.pred_red if mode == "RED" else state.pred_green
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. মার্কেট ডাটা টেবিল (প্রতি পেজে ১০টি সারি)
    total_records = len(state.market_data)
    available_pages = max(1, (total_records + 9) // 10)
    page = max(1, min(TOTAL_PAGES, min(page, available_pages)))

    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = state.market_data[start_idx:end_idx]

    records_outcome = state.win_loss_red if mode == "RED" else state.win_loss_green

    for item in records:
        p_full = item["period"]
        p_short = p_full[-4:] if len(p_full) >= 4 else p_full
        num = item["number"]
        actual_size = item["size"]

        outcome_raw = records_outcome.get(p_full, "--")
        outcome = to_vip(outcome_raw) if outcome_raw != "--" else "--"

        b1 = types.InlineKeyboardButton(f"{to_vip(p_short)}", callback_data="none")
        b2 = types.InlineKeyboardButton(f"{to_vip(str(num))}", callback_data="none")
        b3 = types.InlineKeyboardButton(f"{to_vip(actual_size)}", callback_data="none")
        b4 = types.InlineKeyboardButton(f"{outcome}", callback_data="none")
        markup.row(b1, b2, b3, b4)

    # খালি সারি পূরণ (যদি রেকর্ড ১০টির কম থাকে)
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন (৫০ পেজ ক্যাপাসিটি)
    max_nav_pages = min(TOTAL_PAGES, max(available_pages, 1))
    prev_page = page - 1 if page > 1 else max_nav_pages
    next_page = page + 1 if page < max_nav_pages else 1

    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. ইঞ্জিন পরিবর্তন ও রিফ্রেশ
    switch_target = "GREEN" if mode == "RED" else "RED"
    switch_label = "SWITCH TO GREEN PRO" if mode == "RED" else "SWITCH TO RED PRO"
    btn_switch = types.InlineKeyboardButton(to_vip(switch_label), callback_data=f"mode_{switch_target}")
    btn_refresh = types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh")
    markup.row(btn_switch)
    markup.row(btn_refresh)

    return markup

# =========================================================
# REAL-TIME EVALUATOR & BACKGROUND SYNC
# =========================================================
def evaluate_history_outcomes(data):
    """রেজাল্ট মেলানো ও ডাটাবেজে আপডেট করা"""
    for rec in data[:10]:
        p = rec["period"]
        act_n = rec["number"]
        act_s = rec["size"]
        act_c = rec["color"]

        # RED PRO
        if p in state.history_red and state.win_loss_red.get(p, "--") == "--":
            h_red = state.history_red[p]
            pred_nums = [int(x.strip()) for x in h_red.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums:
                res = "JAC"
            elif (h_red.get("size") == act_s) or (h_red.get("color") == act_c):
                res = "WIN"
            else:
                res = "LOSS"
            state.win_loss_red[p] = res
            db_update_outcome(p, "RED", res)

        # GREEN PRO
        if p in state.history_green and state.win_loss_green.get(p, "--") == "--":
            h_green = state.history_green[p]
            pred_nums_g = [int(x.strip()) for x in h_green.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums_g:
                res = "JAC"
            elif (h_green.get("size") == act_s) or (h_green.get("color") == act_c):
                res = "WIN"
            else:
                res = "LOSS"
            state.win_loss_green[p] = res
            db_update_outcome(p, "GREEN", res)

def real_time_market_loop():
    last_fetched_period = ""
    tick_counter = 0

    while True:
        try:
            # ১. প্রতি ৩ সেকেন্ডে API থেকে নতুন ডাটা সংগ্রহ
            data = fetch_api_market()
            if data:
                # ডাটাবেজে স্থায়ীভাবে সেভ করা
                db_save_market_records(data)

                top_record = data[0]
                top_period = top_record["period"]

                if top_period != last_fetched_period:
                    last_fetched_period = top_period

                    # ডাটাবেজ থেকে ৫০ পেজ ডাটা মেমোরিতে রিফ্রেশ
                    state.reload_from_db()

                    try:
                        next_period_num = int(top_period) + 1
                        next_period_str = str(next_period_num).zfill(len(top_period))
                    except Exception:
                        next_period_str = f"{int(time.time() // MARKET_INTERVAL) + 1}"

                    state.current_period = next_period_str

                    # হিস্ট্রি মূল্যায়ন
                    evaluate_history_outcomes(state.market_data)

                    # নতুন প্রেডিকশন: RED PRO
                    pred_r = calculate_red_pro_prediction(state.market_data)
                    state.pred_red = {
                        "period": next_period_str,
                        "size": pred_r["size"],
                        "num": pred_r["num"],
                        "color": pred_r["color"]
                    }
                    state.history_red[next_period_str] = state.pred_red
                    db_save_prediction(next_period_str, "RED", pred_r["size"], pred_r["num"], pred_r["color"])

                    # নতুন প্রেডিকশন: GREEN PRO
                    pred_g = calculate_green_pro_prediction(state.market_data)
                    state.pred_green = {
                        "period": next_period_str,
                        "size": pred_g["size"],
                        "num": pred_g["num"],
                        "color": pred_g["color"]
                    }
                    state.history_green[next_period_str] = state.pred_green
                    db_save_prediction(next_period_str, "GREEN", pred_g["size"], pred_g["num"], pred_g["color"])

            # ২. সক্রিয় চ্যাটে লাইভ মেসেজ আপডেট (টেলিগ্রাম রেট-লিমিট বাঁচাতে ৩-৪ সেকেন্ড পর পর আপডেট)
            tick_counter += 1
            if tick_counter % 1 == 0:
                with state.lock:
                    chats_to_update = list(state.active_chats.items())

                for chat_id, info in chats_to_update:
                    try:
                        markup = create_market_markup(page=info.get("page", 1), mode=info.get("mode", "RED"))
                        bot.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=info["message_id"],
                            reply_markup=markup
                        )
                    except telebot.apihelper.ApiTelegramException as e:
                        if "message is not modified" not in str(e).lower():
                            pass
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Loop error: {e}")

        time.sleep(2.5)

# =========================================================
# BOT COMMAND & CALLBACK HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_start_menu(message):
    chat_id = message.chat.id
    welcome_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SELECT SYSTEM ENGINE')}</i>\n"
        "────────────────────────"
    )
    markup = get_start_markup()
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # ১. লঞ্চ বাটন
    if data.startswith("launch_"):
        chosen_mode = data.split("_")[1]
        header_text = get_dashboard_header(chosen_mode)
        markup = create_market_markup(page=1, mode=chosen_mode)

        try:
            bot.edit_message_text(
                header_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass

        with state.lock:
            state.active_chats[chat_id] = {
                "message_id": call.message.message_id,
                "page": 1,
                "mode": chosen_mode
            }
        bot.answer_callback_query(call.id, text=to_vip(f"{chosen_mode} PRO ACTIVATED"))
        return

    # ২. ইঞ্জিন মোড পরিবর্তন
    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with state.lock:
            curr_page = state.active_chats.get(chat_id, {}).get("page", 1)
            state.active_chats[chat_id] = {
                "message_id": call.message.message_id,
                "page": curr_page,
                "mode": new_mode
            }

        header_text = get_dashboard_header(new_mode)
        markup = create_market_markup(page=curr_page, mode=new_mode)

        try:
            bot.edit_message_text(
                header_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass

        bot.answer_callback_query(call.id, text=to_vip(f"{new_mode} PRO ACTIVATED"))
        return

    # ৩. পেজিনেশন
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                curr_mode = state.active_chats.get(chat_id, {}).get("mode", "RED")
                state.active_chats[chat_id]["page"] = page_num

            markup = create_market_markup(page=page_num, mode=curr_mode)
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {page_num}")
        except Exception:
            bot.answer_callback_query(call.id)

    # ৪. রিফ্রেশ
    elif data == "refresh":
        try:
            state.reload_from_db()
            info = state.active_chats.get(chat_id, {"page": 1, "mode": "RED"})
            markup = create_market_markup(page=info.get("page", 1), mode=info.get("mode", "RED"))
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, text=to_vip("REFRESHED"))
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    init_database()
    state.reload_from_db()

    print("=" * 60)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [30S ONLINE]")
    print(f"Modes: RED PRO WINNER & GREEN PRO WINNER (NO-EMOJI CLEAN UI)")
    print(f"Database: {DB_NAME} | Endpoint: {API_URL}")
    print("=" * 60)

    sync_thread = threading.Thread(target=real_time_market_loop, daemon=True)
    sync_thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Crash: {e}. Restarting in 5s...")
            time.sleep(5)
