# -*- coding: utf-8 -*-
"""
DRX-TM WinGo 5-Minute Real-Time Prediction Telegram Bot
API Endpoint: https://advanced-predict1.ai.studio/apipid.json
Features: 50 Pages Pagination, Skip Page 1-2 Sequence, 0/5 = VIOLET, JAC Jackpot
Note: Reads pure market data from API's 'prediction_history' (Period, Number, Size, Color)
      and calculates bot's own internal predictions and JAC/WIN/LOSS outcomes.
"""

import time
import json
import logging
import threading
import requests
from datetime import datetime, timedelta
import telebot
from telebot import types

# =========================================================
# CONFIGURATION
# =========================================================
BOT_TOKEN = "8949748635:AAF9w3mFRx2fqcE6AslsrR7AUuNJQzqB-PA"
API_URL = "https://advanced-predict1.ai.studio/apipid.json"
MARKET_INTERVAL = 300  # ৫ মিনিট = ৩০০ সেকেন্ড
TOTAL_PAGES = 50       # টোটাল ৫০ পেজ

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# VIP FONT ENGINE (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
# =========================================================
def to_vip(text: str) -> str:
    """টেক্সটকে বোল্ড ভিআইপি ফন্টে রূপান্তর করে"""
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
# RULES DEFINITION (0 ও 5 = VIOLET)
# =========================================================
VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

def get_color(num: int) -> str:
    if num in VIOLET_NUMBERS:
        return "VIOLET"
    return "RED" if num in RED_NUMBERS else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num in BIG_NUMBERS else "SMALL"

# =========================================================
# STATE & 24-HOUR RETENTION
# =========================================================
class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_period = ""
        self.market_data = []          # ৫০ পেজের ডাটা (সর্বোচ্চ ৫০০টি)
        self.current_prediction = {
            "period": "",
            "size": "--",
            "num": "--",
            "color": "--"
        }
        self.prediction_history = {}    # {period: {"size", "num", "color", "timestamp"}}
        self.win_loss_records = {}      # {period: "JAC" | "WIN" | "LOSS"}
        self.active_chats = {}          # {chat_id: {"message_id": int, "page": int}}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=24)
        with self.lock:
            to_remove = [
                p for p, data in self.prediction_history.items()
                if data.get("timestamp", datetime.now()) < cutoff
            ]
            for p in to_remove:
                self.prediction_history.pop(p, None)
                self.win_loss_records.pop(p, None)

state = BotState()

# =========================================================
# EXACT API FETCHER (ONLY PURE MARKET: PERIOD, NUM, SIZE, COLOR)
# =========================================================
def fetch_api_market():
    """
    API রেসপন্সের 'prediction_history' থেকে শুধুমাত্র 
    period, number, size, color রিড করবে। 
    API-এর প্রেডিকশন বা রেজাল্ট সম্পূর্ণ বাদ থাকবে।
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = []

            if isinstance(data, dict):
                # API-এর prediction_history অবজেক্ট লিস্ট নেওয়া হচ্ছে
                raw_list = data.get("prediction_history", [])
                if not raw_list:
                    for k in ["data", "list", "records", "rows"]:
                        if k in data and isinstance(data[k], list):
                            raw_list = data[k]
                            break
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                if isinstance(item, dict):
                    p_raw = item.get("period")
                    n_raw = item.get("number")
                    
                    if p_raw is not None and n_raw is not None:
                        period = str(p_raw).strip()
                        try:
                            num = int(n_raw)
                        except (ValueError, TypeError):
                            continue

                        # সাইজ ও কালার এক্সট্র্যাক্ট বা রুলস অনুযায়ী বের করা
                        s_raw = str(item.get("size", "")).strip().upper()
                        c_raw = str(item.get("color", "")).strip().upper()

                        size = s_raw if s_raw in ["BIG", "SMALL"] else get_size(num)
                        color = c_raw if c_raw in ["RED", "GREEN", "VIOLET"] else get_color(num)

                        formatted.append({
                            "period": period,
                            "number": num,
                            "size": size,
                            "color": color
                        })

            if formatted:
                # ৫০ পেজের জন্য সর্বোচ্চ ৫০০টি লাইভ মার্কেট রেকর্ড
                return formatted[:500]
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
    return []

# =========================================================
# PREDICTION ENGINE (SKIP PAGE 1 & 2, SEARCH PAGE 3-50)
# =========================================================
def calculate_prediction(market_records):
    """
    ১. টপের দুটি সংখ্যা t1, t2 নেওয়া হবে।
    ২. পেজ ১ ও ২ (প্রথম ২০টি রেকর্ড) বাদ দিয়ে পেজ ৩ (ইন্ডেক্স ২০) থেকে পেজ ৫০ পর্যন্ত খোঁজা হবে।
    ৩. সিকোয়েন্স মিললে তার উপরের (i-1) এবং নিচের (i+2) সংখ্যার ভিত্তিতে কালার/সাইজ প্রেডিকশন হবে।
    """
    if len(market_records) < 25:
        return {"size": "--", "num": "--", "color": "--"}

    t1 = market_records[0]["number"]
    t2 = market_records[1]["number"]

    found_idx = -1
    # পেজ ১ এবং পেজ ২ সম্পূর্ণ বাদ (প্রথম ২০টি রেকর্ড বাদ দিয়ে ইন্ডেক্স ২০ থেকে খোঁজা শুরু)
    for i in range(20, len(market_records) - 2):
        curr_pair = (market_records[i]["number"], market_records[i + 1]["number"])
        if curr_pair == (t1, t2) or curr_pair == (t2, t1):
            if i - 1 >= 0 and i + 2 < len(market_records):
                found_idx = i
                break

    if found_idx == -1:
        def_color = "VIOLET" if t1 in VIOLET_NUMBERS else "RED"
        return {"size": "BIG", "num": f"{t1},{t2}", "color": def_color}

    n_above = market_records[found_idx - 1]["number"]
    n_below = market_records[found_idx + 2]["number"]

    c_above = get_color(n_above)
    c_below = get_color(n_below)
    pred_color = c_above if c_above == c_below else "--"

    s_above = get_size(n_above)
    s_below = get_size(n_below)
    pred_size = s_above if s_above == s_below else "--"

    pred_num = f"{n_above},{n_below}"

    return {
        "size": pred_size,
        "num": pred_num,
        "color": pred_color
    }

# =========================================================
# UI KEYBOARD DESIGN (50 PAGES SUPPORT & COMPLETE DESIGN)
# =========================================================
def create_market_markup(page: int = 1):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. পিরিয়ড বাটন
    period_str = state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # ২. ৫ মিনিট টাইমার ও প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % MARKET_INTERVAL
    remaining = MARKET_INTERVAL - elapsed

    total_blocks = 20
    filled_blocks = int((elapsed / MARKET_INTERVAL) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"⏳ {to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. প্রেডিকশন বক্স: শুধু প্রেডিকশন ভ্যালু
    pred = state.current_prediction
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. মার্কেট ডাটা টেবিল (প্রতি পেজে ১০টি সারি)
    page = max(1, min(TOTAL_PAGES, page))
    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = state.market_data[start_idx:end_idx]

    for item in records:
        p_full = item["period"]
        p_short = p_full[-4:] if len(p_full) >= 4 else p_full
        num = item["number"]
        actual_size = item["size"]

        outcome_raw = state.win_loss_records.get(p_full, "--")
        outcome = to_vip(outcome_raw) if outcome_raw != "--" else "--"

        b1 = types.InlineKeyboardButton(f"{to_vip(p_short)}", callback_data="none")
        b2 = types.InlineKeyboardButton(f"{to_vip(str(num))}", callback_data="none")
        b3 = types.InlineKeyboardButton(f"{to_vip(actual_size)}", callback_data="none")
        b4 = types.InlineKeyboardButton(f"{outcome}", callback_data="none")
        markup.row(b1, b2, b3, b4)

    # স্লট পূর্ণ না হলে খালি সারি
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন বাটন (১ থেকে ৫০ পেজ সোয়াইপ)
    prev_page = page - 1 if page > 1 else TOTAL_PAGES
    next_page = page + 1 if page < TOTAL_PAGES else 1
    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. রিফ্রেশ বাটন
    btn_refresh = types.InlineKeyboardButton(f"{to_vip('REFRESH')}", callback_data="refresh")
    markup.row(btn_refresh)

    return markup

# =========================================================
# REAL-TIME BACKGROUND THREAD & 3-LETTER JAC LOGIC
# =========================================================
def real_time_market_loop():
    last_fetched_period = ""

    while True:
        try:
            data = fetch_api_market()
            if data:
                with state.lock:
                    state.market_data = data
                    top_record = data[0]
                    top_period = top_record["period"]

                    if top_period != last_fetched_period:
                        last_fetched_period = top_period

                        try:
                            next_period_num = int(top_period) + 1
                            next_period_str = str(next_period_num).zfill(len(top_period))
                        except Exception:
                            next_period_str = f"{int(time.time() // MARKET_INTERVAL) + 1}"

                        state.current_period = next_period_str

                        # ফলাফল নির্ধারণ (JAC / WIN / LOSS)
                        for rec in data[:5]:
                            p = rec["period"]
                            if p in state.prediction_history and p not in state.win_loss_records:
                                hist = state.prediction_history[p]
                                pred_s = hist.get("size")
                                pred_c = hist.get("color")
                                pred_num_str = hist.get("num", "")
                                
                                act_s = rec["size"]
                                act_c = rec["color"]
                                act_n = rec["number"]

                                pred_nums = []
                                for x in pred_num_str.split(","):
                                    x = x.strip()
                                    if x.isdigit():
                                        pred_nums.append(int(x))

                                # ১. নম্বর মিলে গেলে ৩ অক্ষরের জ্যাকপট 'JAC'
                                if act_n in pred_nums:
                                    state.win_loss_records[p] = "JAC"
                                # ২. সাইজ অথবা কালার মিললে 'WIN' (VIOLET সহ)
                                elif (pred_s != "--" and pred_s == act_s) or (pred_c != "--" and pred_c == act_c):
                                    state.win_loss_records[p] = "WIN"
                                # ৩. কিছুই না মিললে 'LOSS'
                                else:
                                    state.win_loss_records[p] = "LOSS"

                        # নতুন প্রেডিকশন তৈরি
                        new_pred = calculate_prediction(state.market_data)
                        state.current_prediction = {
                            "period": next_period_str,
                            "size": new_pred["size"],
                            "num": new_pred["num"],
                            "color": new_pred["color"]
                        }

                        state.prediction_history[next_period_str] = {
                            "size": new_pred["size"],
                            "num": new_pred["num"],
                            "color": new_pred["color"],
                            "timestamp": datetime.now()
                        }

            state.clean_old_records()

            # সক্রিয় চ্যাট আপডেট
            with state.lock:
                chats_to_update = list(state.active_chats.items())

            for chat_id, info in chats_to_update:
                try:
                    markup = create_market_markup(page=info.get("page", 1))
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

        time.sleep(3)

# =========================================================
# BOT COMMAND HANDLERS
# =========================================================
@bot.message_handler(commands=["start", "market"])
def send_welcome(message):
    chat_id = message.chat.id
    header_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('WINGO 5-MIN PREDICTION')}</i>\n"
        "────────────────────────"
    )
    markup = create_market_markup(page=1)
    msg = bot.send_message(chat_id, header_text, reply_markup=markup)

    with state.lock:
        state.active_chats[chat_id] = {"message_id": msg.message_id, "page": 1}

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # ১ থেকে ৫০ পেজ ব্রাউজিং
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                if chat_id in state.active_chats:
                    state.active_chats[chat_id]["page"] = page_num
            markup = create_market_markup(page=page_num)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {page_num}")
        except Exception:
            bot.answer_callback_query(call.id)

    elif data == "refresh":
        try:
            page_num = state.active_chats.get(chat_id, {}).get("page", 1)
            markup = create_market_markup(page=page_num)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=f"{to_vip('REFRESHED')}")
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [ONLINE]")
    print(f"Total Pages: {TOTAL_PAGES} | Endpoint: {API_URL}")
    print("=" * 60)

    thread = threading.Thread(target=real_time_market_loop, daemon=True)
    thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Crash: {e}. Restarting in 5s...")
            time.sleep(5)
