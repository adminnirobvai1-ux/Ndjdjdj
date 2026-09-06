# -*- coding: utf-8 -*-
"""
DRX-TM WinGo 5-Minute Real-Time Prediction Telegram Bot
Layout: Original Dark Killer ➤ DRX-TM Clean UI
API: https://advanced-predict1.ai.studio/apipid.json
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
TOTAL_PAGES = 50       # ৫০ পেজ নেভিগেশন

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# RULES DEFINITION (0 & 5 = VIOLET)
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
        self.market_data = []          # ৫০০টি রেকর্ড
        self.current_prediction = {
            "period": "",
            "size": "BIG",
            "num": "--",
            "color": "RED"
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
# API PARSER & FETCHER
# =========================================================
def parse_single_record(item):
    period = ""
    num = None

    if isinstance(item, dict):
        for key in ["issueNumber", "period", "issue", "id", "stage", "expect", "round", "qihao"]:
            if key in item and item[key] is not None:
                period = str(item[key]).strip()
                break

        for key in ["number", "openNum", "num", "code", "result", "openCode", "digit"]:
            if key in item and item[key] is not None:
                raw_val = str(item[key]).strip()
                if "," in raw_val:
                    raw_val = raw_val.split(",")[-1]
                try:
                    num = int(raw_val)
                    break
                except ValueError:
                    continue

    elif isinstance(item, (list, tuple)):
        for el in item:
            s_el = str(el).strip()
            if len(s_el) >= 5 and s_el.isdigit() and not period:
                period = s_el
            elif s_el.isdigit() and 0 <= int(s_el) <= 9 and num is None:
                num = int(s_el)

        if not period and len(item) > 0:
            period = str(item[0]).strip()
        if num is None and len(item) > 1:
            try:
                num = int(str(item[1]).strip().split(",")[-1])
            except (ValueError, IndexError):
                num = 0

    if period and num is not None:
        return {
            "period": period,
            "number": num,
            "size": get_size(num),
            "color": get_color(num)
        }
    return None

def fetch_api_market():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = []

            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict):
                for k in ["data", "list", "result", "rows", "records"]:
                    if k in data:
                        val = data[k]
                        if isinstance(val, list):
                            raw_list = val
                            break
                        elif isinstance(val, dict):
                            for sub_k in ["list", "data", "rows"]:
                                if sub_k in val and isinstance(val[sub_k], list):
                                    raw_list = val[sub_k]
                                    break
                            if raw_list:
                                break

            formatted = []
            for item in raw_list:
                rec = parse_single_record(item)
                if rec:
                    formatted.append(rec)

            if formatted:
                return formatted[:500]
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
    return []

# =========================================================
# PREDICTION ENGINE (SKIP PAGE 1-2, SEARCH PAGE 3-50)
# =========================================================
def calculate_prediction(market_records):
    if len(market_records) < 25:
        return {"size": "BIG", "num": "3,8", "color": "RED"}

    t1 = market_records[0]["number"]
    t2 = market_records[1]["number"]

    found_idx = -1
    # ১ম ও ২য় পেজ (প্রথম ২০টি ডাটা) সম্পূর্ণ বাদ দিয়ে ইন্ডেক্স ২০ থেকে পেজ ৫০ পর্যন্ত সার্চ
    for i in range(20, len(market_records) - 2):
        curr_pair = (market_records[i]["number"], market_records[i + 1]["number"])
        if curr_pair == (t1, t2) or curr_pair == (t2, t1):
            if i - 1 >= 0 and i + 2 < len(market_records):
                found_idx = i
                break

    if found_idx == -1:
        # প্যাটার্ন সরাসরি না পেলে অলটারনেট ভ্যালু
        def_color = "VIOLET" if t1 in VIOLET_NUMBERS else ("RED" if t1 in RED_NUMBERS else "GREEN")
        return {"size": get_size(t1), "num": f"{t1},{t2}", "color": def_color}

    n_above = market_records[found_idx - 1]["number"]
    n_below = market_records[found_idx + 2]["number"]

    c_above = get_color(n_above)
    c_below = get_color(n_below)
    pred_color = c_above if c_above == c_below else c_above

    s_above = get_size(n_above)
    s_below = get_size(n_below)
    pred_size = s_above if s_above == s_below else s_above

    pred_num = f"{n_above},{n_below}"

    return {
        "size": pred_size,
        "num": pred_num,
        "color": pred_color
    }

# =========================================================
# UI KEYBOARD DESIGN (ORIGINAL DARK KILLER)
# =========================================================
def create_market_markup(page: int = 1):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. পিরিয়ড বাটন
    period_str = state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"PERIOD: {period_str}", callback_data="none")
    markup.row(btn_period)

    # ২. লাইভ ৫ মিনিট টাইমার ও ক্লিন প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % MARKET_INTERVAL
    remaining = MARKET_INTERVAL - elapsed

    total_blocks = 15
    filled_blocks = int((elapsed / MARKET_INTERVAL) * total_blocks)
    progress_bar = "■" * filled_blocks + "□" * (total_blocks - filled_blocks)
    timer_text = f"⏳ {remaining:02d}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. তিনটি ক্লিন প্রেডিকশন বক্স: SIZE | NUM | COLOR
    pred = state.current_prediction
    s_val = pred.get('size', 'BIG')
    n_val = pred.get('num', '--')
    c_val = pred.get('color', 'RED')

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

        outcome = state.win_loss_records.get(p_full, "--")

        b1 = types.InlineKeyboardButton(f"{p_short}", callback_data="none")
        b2 = types.InlineKeyboardButton(f"{num}", callback_data="none")
        b3 = types.InlineKeyboardButton(f"{actual_size}", callback_data="none")
        b4 = types.InlineKeyboardButton(f"{outcome}", callback_data="none")
        markup.row(b1, b2, b3, b4)

    # ডাটা ১০টির কম হলে খালি দাগ
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন বাটন (১ থেকে ৫০ পেজ সোয়াইপ)
    prev_page = page - 1 if page > 1 else TOTAL_PAGES
    next_page = page + 1 if page < TOTAL_PAGES else 1
    btn_prev = types.InlineKeyboardButton("◀️ PREV", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"PAGE {page}/{TOTAL_PAGES}", callback_data="none")
    btn_next = types.InlineKeyboardButton("NEXT ▶️", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. রিফ্রেশ বাটন
    btn_refresh = types.InlineKeyboardButton("🔄 REFRESH", callback_data="refresh")
    markup.row(btn_refresh)

    return markup

# =========================================================
# REAL-TIME BACKGROUND THREAD & JAC / WIN LOGIC
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
                        for rec in data[:8]:
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

                                # ১. নম্বর মিলে গেলে ৩ অক্ষরের JAC
                                if act_n in pred_nums:
                                    state.win_loss_records[p] = "JAC"
                                # ২. সাইজ অথবা কালার মিললে WIN
                                elif (pred_s and pred_s == act_s) or (pred_c and pred_c == act_c):
                                    state.win_loss_records[p] = "WIN"
                                # ৩. কোনোটাই না মিললে LOSS
                                else:
                                    state.win_loss_records[p] = "LOSS"

                        # নতুন প্রেডিকশন
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

            # চ্যাটে লাইভ ভিউ ও টাইমার আপডেট
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
        "<b>Dark Killer ➤ DRX-TM Bot</b>\n"
        "<i>WinGo 5-Minute Real-Time Market & Analysis</i>\n"
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

    # ১ থেকে ৫০ পেজ সুইচিং
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                if chat_id in state.active_chats:
                    state.active_chats[chat_id]["page"] = page_num
            markup = create_market_markup(page=page_num)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=f"Page {page_num}")
        except Exception:
            bot.answer_callback_query(call.id)

    elif data == "refresh":
        try:
            page_num = state.active_chats.get(chat_id, {}).get("page", 1)
            markup = create_market_markup(page=page_num)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text="Refreshed ✅")
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Dark Killer ➤ DRX-TM Bot [ONLINE]")
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
