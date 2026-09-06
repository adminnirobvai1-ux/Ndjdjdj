# -*- coding: utf-8 -*-
"""
DRX-TM WinGo 5-Minute Real-Time Prediction Telegram Bot
API Endpoint: https://advanced-predict1.ai.studio/apipid.json
Design layout matches Dark Killer ➤ DRX-TM
"""

import time
import logging
import threading
import requests
from datetime import datetime, timedelta
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# =========================================================
# CONFIGURATION
# =========================================================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"  # আপনার টেলিগ্রাম বট টোকেন দিন
API_URL = "https://advanced-predict1.ai.studio/apipid.json"
MARKET_INTERVAL = 300  # ৫ মিনিট = ৩০০ সেকেন্ড
UPDATE_INTERVAL = 5    # টেলিগ্রাম রেট লিমিট এড়াতে ৫ সেকেন্ড পরপর মেসেজ রিফ্রেশ

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# RULES DEFINITION
# =========================================================
RED_NUMBERS = {0, 2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 5, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

def get_color(num: int) -> str:
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
        self.market_data = []          # ১০০টি রেজাল্ট
        self.current_prediction = {
            "period": "",
            "size": "--",
            "num": "--",
            "color": "--"
        }
        self.prediction_history = {}    # {period: {"size", "color", "timestamp"}}
        self.win_loss_records = {}      # {period: "WIN" | "LOSS"}
        self.active_chats = {}          # {chat_id: {"message_id": int, "page": int}}

    def clean_old_records(self):
        """২৪ ঘণ্টার বেশি পুরোনো রেকর্ড মুছে ফেলে"""
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
# API FETCHER (শুধুমাত্র আসল মার্কেট ডাটা নেওয়ার জন্য আপডেটকৃত)
# =========================================================
def fetch_api_market():
    """API-এর prediction_history থেকে শুধুমাত্র লাইভ মার্কেট ডাটা ফিল্টার করে নেয়"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        resp = requests.get(API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            # API এর 'prediction_history' অ্যারে থেকে ডাটা নেওয়া হচ্ছে
            raw_list = []
            if isinstance(data, dict):
                raw_list = data.get("prediction_history", []) or data.get("data", {}).get("list", []) or data.get("data", [])
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                period = str(item.get("period") or item.get("issueNumber") or "")
                num_raw = item.get("number")
                if num_raw is None:
                    num_raw = item.get("openNum", 0)

                try:
                    num = int(num_raw)
                except (ValueError, TypeError):
                    num = 0

                if period:
                    # API-এর প্রেডিকশন সম্পূর্ণ বাদ দিয়ে শুধুমাত্র আসল নম্বর ও সাইজ/কালার নেওয়া হচ্ছে
                    size = str(item.get("size", "")).upper() if item.get("size") else get_size(num)
                    color = str(item.get("color", "")).upper() if item.get("color") else get_color(num)

                    formatted.append({
                        "period": period,
                        "number": num,
                        "size": size,
                        "color": color
                    })
            if formatted:
                return formatted
        else:
            logger.warning(f"API Returned HTTP Status {resp.status_code}")
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
    return []

# =========================================================
# PREDICTION ENGINE (বটের নিজস্ব লজিক)
# =========================================================
def calculate_prediction(market_records):
    if len(market_records) < 25:
        return {"size": "--", "num": "--", "color": "--"}

    t1 = market_records[0]["number"]
    t2 = market_records[1]["number"]

    found_idx = -1
    for i in range(20, len(market_records) - 2):
        curr_pair = (market_records[i]["number"], market_records[i + 1]["number"])
        if curr_pair == (t1, t2) or curr_pair == (t2, t1):
            if i - 1 >= 0 and i + 2 < len(market_records):
                found_idx = i
                break

    if found_idx == -1:
        return {"size": "BIG", "num": f"{t1},{t2}", "color": "RED"}

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
# UI KEYBOARD DESIGN (Dark Killer Layout)
# =========================================================
def create_market_markup(page: int = 1):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. পিরিয়ড বাটন
    period_str = state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"PERIOD: {period_str}", callback_data="none")
    markup.row(btn_period)

    # ২. লাইভ ৫ মিনিট টাইমার ও প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % MARKET_INTERVAL
    remaining = MARKET_INTERVAL - elapsed

    total_blocks = 16
    filled_blocks = int((elapsed / MARKET_INTERVAL) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f" {remaining:02d}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. প্রেডিকশন বক্স
    pred = state.current_prediction
    size_box = f" {pred['size']}" if pred['size'] != "--" else "--"
    num_box = f"NUM: {pred['num']}" if pred['num'] != "--" else "NUM: --"
    color_box = f" {pred['color']}" if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(size_box, callback_data="none")
    btn_num = types.InlineKeyboardButton(num_box, callback_data="none")
    btn_color = types.InlineKeyboardButton(color_box, callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. মার্কেট ডাটা টেবিল (প্রতি পেজে ১০টি সারি)
    page = max(1, min(10, page))
    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = state.market_data[start_idx:end_idx]

    for item in records:
        p_full = item["period"]
        p_short = p_full[-4:] if len(p_full) >= 4 else p_full  # শেষ ৪ সংখ্যা
        num = item["number"]
        actual_size = item["size"]
        outcome = state.win_loss_records.get(p_full, "--")

        b1 = types.InlineKeyboardButton(f"{p_short}", callback_data="none")
        b2 = types.InlineKeyboardButton(f"{num}", callback_data="none")
        b3 = types.InlineKeyboardButton(f"{actual_size}", callback_data="none")
        b4 = types.InlineKeyboardButton(f"{outcome}", callback_data="none")
        markup.row(b1, b2, b3, b4)

    # ডাটা ১০টির কম হলে খালি দাগ দিয়ে ফিল করা
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন বাটন
    prev_page = page - 1 if page > 1 else 10
    next_page = page + 1 if page < 10 else 1
    btn_prev = types.InlineKeyboardButton(" Prev", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"Page {page}/10", callback_data="none")
    btn_next = types.InlineKeyboardButton("Next", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. রিফ্রেশ বাটন
    btn_refresh = types.InlineKeyboardButton(" Refresh", callback_data="refresh")
    markup.row(btn_refresh)

    return markup

# =========================================================
# REAL-TIME BACKGROUND THREAD
# =========================================================
def real_time_market_loop():
    last_fetched_period = ""

    while True:
        try:
            data = fetch_api_market()
            if data:
                with state.lock:
                    state.market_data = data[:100]
                    top_record = data[0]
                    top_period = top_record["period"]

                    # নতুন পিরিয়ড শুরু হলে
                    if top_period != last_fetched_period:
                        last_fetched_period = top_period

                        try:
                            next_period_num = int(top_period) + 1
                            next_period_str = str(next_period_num).zfill(len(top_period))
                        except ValueError:
                            next_period_str = f"{int(time.time() // MARKET_INTERVAL) + 1}"

                        state.current_period = next_period_str

                        # আগের দেওয়া প্রেডিকশনের সাথে রেজাল্ট মিলিয়ে WIN/LOSS নির্ধারণ
                        for rec in data[:5]:
                            p = rec["period"]
                            if p in state.prediction_history and p not in state.win_loss_records:
                                hist = state.prediction_history[p]
                                pred_s = hist.get("size")
                                pred_c = hist.get("color")
                                act_s = rec["size"]
                                act_c = rec["color"]

                                is_win = False
                                if pred_s != "--" and pred_s == act_s:
                                    is_win = True
                                if pred_c != "--" and pred_c == act_c:
                                    is_win = True

                                state.win_loss_records[p] = "WIN" if is_win else "LOSS"

                        # নতুন প্রেডিকশন তৈরি
                        new_pred = calculate_prediction(state.market_data)
                        state.current_prediction = {
                            "period": next_period_str,
                            "size": new_pred["size"],
                            "num": new_pred["num"],
                            "color": new_pred["color"]
                        }

                        # ২৪ ঘণ্টার হিস্ট্রিতে সংরক্ষণ
                        state.prediction_history[next_period_str] = {
                            "size": new_pred["size"],
                            "num": new_pred["num"],
                            "color": new_pred["color"],
                            "timestamp": datetime.now()
                        }

            state.clean_old_records()

            # অ্যাক্টিভ চ্যাট আপডেট
            with state.lock:
                chats_to_update = list(state.active_chats.items())

            dead_chats = []
            for chat_id, info in chats_to_update:
                try:
                    markup = create_market_markup(page=info.get("page", 1))
                    bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=info["message_id"],
                        reply_markup=markup
                    )
                except ApiTelegramException as te:
                    err_msg = str(te).lower()
                    if "message is not modified" in err_msg:
                        continue
                    elif "message to edit not found" in err_msg or "chat not found" in err_msg or "bot was blocked" in err_msg:
                        dead_chats.append(chat_id)
                    elif "flood control exceeded" in err_msg:
                        logger.warning("Telegram Flood Control triggered. Pausing...")
                        time.sleep(10)
                except Exception as e:
                    logger.error(f"Error updating message in chat {chat_id}: {e}")

            if dead_chats:
                with state.lock:
                    for cid in dead_chats:
                        state.active_chats.pop(cid, None)

        except Exception as e:
            logger.error(f"Market loop error: {e}")

        time.sleep(UPDATE_INTERVAL)

# =========================================================
# BOT COMMAND HANDLERS
# =========================================================
@bot.message_handler(commands=["start", "market"])
def send_welcome(message):
    chat_id = message.chat.id
    header_text = (
        "<b>Dark Killer ➤ DRX-TM Bot</b>\n"
        "<i>WinGo 5-Minute Real-Time Market & AI Analysis</i>\n"
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
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return

    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                if chat_id in state.active_chats:
                    state.active_chats[chat_id]["page"] = page_num
            markup = create_market_markup(page=page_num)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=f"Page {page_num}")
        except Exception as e:
            logger.warning(f"Callback page error: {e}")
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass

    elif data == "refresh":
        try:
            page_num = state.active_chats.get(chat_id, {}).get("page", 1)
            markup = create_market_markup(page=page_num)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text="Refreshed ✅")
        except Exception as e:
            logger.warning(f"Callback refresh error: {e}")
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Dark Killer ➤ DRX-TM Bot Starting...")
    print("=" * 60)

    thread = threading.Thread(target=real_time_market_loop, daemon=True)
    thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=15)
        except Exception as e:
            logger.error(f"Bot Polling Crashed: {e}. Restarting in 5s...")
            time.sleep(5)
