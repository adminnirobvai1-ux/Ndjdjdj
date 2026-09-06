# -*- coding: utf-8 -*-
"""
DRX-TM WinGo 5-Minute Pure Real-Time Market Viewer
API Endpoint: https://advanced-predict1.ai.studio/apipid.json
Features: 50 Pages Pagination, Real-Time Market Feed, Zero Prediction/Results
"""

import time
import json
import logging
import threading
import requests
from datetime import datetime
import telebot
from telebot import types

# =========================================================
# CONFIGURATION
# =========================================================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
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
# STATE MANAGEMENT
# =========================================================
class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_period = ""
        self.market_data = []          # ৫০ পেজের মার্কেট ডাটা (সর্বোচ্চ ৫০০টি)
        self.active_chats = {}          # {chat_id: {"message_id": int, "page": int}}

state = BotState()

# =========================================================
# API PARSER & FETCHER (UP TO 500 RECORDS)
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
                # ৫০ পেজের জন্য সর্বোচ্চ ৫০০টি লাইভ রেকর্ড নেওয়া হবে
                return formatted[:500]
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
    return []

# =========================================================
# UI KEYBOARD DESIGN (EXACT SAME DESIGN PRESERVED)
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

    # ৩. সর্বশেষ ড্র হওয়া মার্কেট ডাটা বক্স (ডিজাইন সম্পূর্ণ এক)
    latest = state.market_data[0] if state.market_data else None
    s_val = to_vip(latest['size']) if latest else "--"
    n_val = to_vip(str(latest['number'])) if latest else "--"
    c_val = to_vip(latest['color']) if latest else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. মার্কেট ডাটা টেবিল (প্রতি পেজে ১০টি সারি: পিরিয়ড, নম্বর, সাইজ, কালার)
    page = max(1, min(TOTAL_PAGES, page))
    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = state.market_data[start_idx:end_idx]

    for item in records:
        p_full = item["period"]
        p_short = p_full[-4:] if len(p_full) >= 4 else p_full
        num = item["number"]
        actual_size = item["size"]
        actual_color = item["color"]

        b1 = types.InlineKeyboardButton(f"{to_vip(p_short)}", callback_data="none")
        b2 = types.InlineKeyboardButton(f"{to_vip(str(num))}", callback_data="none")
        b3 = types.InlineKeyboardButton(f"{to_vip(actual_size)}", callback_data="none")
        b4 = types.InlineKeyboardButton(f"{to_vip(actual_color)}", callback_data="none")
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
# REAL-TIME BACKGROUND THREAD (PURE MARKET SYNC)
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

            # অ্যাক্টিভ চ্যাটে লাইভ মার্কেট রেন্ডার
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
        f"<i>{to_vip('WINGO 5-MIN MARKET')}</i>\n"
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
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [PURE MARKET ONLINE]")
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
