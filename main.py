# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Multi-Market (30S & 5M) Professional Dual-Engine Telegram Bot
Features:
  - Zero Emoji Clean Professional VIP UI
  - Dual Independent Markets: WinGo 30-Second & WinGo 5-Minute
  - Dedicated API Parsers (supports 'actual_number' & 'number')
  - Engine 1: RED PRO WINNER (Adaptive Sequence & Affinity)
  - Engine 2: GREEN PRO WINNER (Markov Chain & 3-Digit Sniper)
  - In-Place Window Overwrite & Real-Time Sync
"""

import time
import json
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
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
TOTAL_PAGES = 50

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

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
class MarketState:
    def __init__(self, key: str, config: dict):
        self.key = key
        self.name = config["name"]
        self.api_url = config["api"]
        self.interval = config["interval"]

        self.current_period = ""
        self.market_data = []
        self.last_fetched_period = ""

        # RED PRO WINNER স্টোরেজ
        self.pred_red = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_red = {}
        self.win_loss_red = {}

        # GREEN PRO WINNER স্টোরেজ
        self.pred_green = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_green = {}
        self.win_loss_green = {}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=24)
        for store, hist in [(self.win_loss_red, self.history_red), (self.win_loss_green, self.history_green)]:
            to_del = [p for p, val in hist.items() if val.get("timestamp", datetime.now()) < cutoff]
            for p in to_del:
                hist.pop(p, None)
                store.pop(p, None)

class GlobalBotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.markets = {
            "30S": MarketState("30S", MARKETS["30S"]),
            "5M": MarketState("5M", MARKETS["5M"])
        }
        # {chat_id: {"message_id": int, "market": "30S"|"5M", "mode": "RED"|"GREEN", "page": int}}
        self.active_chats = {}

state = GlobalBotState()

# =========================================================
# ROBUST API FETCHER (HANDLES BOTH 30S & 5M DATA SCHEMAS)
# =========================================================
def fetch_api_market(api_url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(api_url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = []
            root_period = None

            if isinstance(data, dict):
                root_period = data.get("period")
                for k in ["history", "prediction_history", "data", "list", "records", "rows"]:
                    if k in data and isinstance(data[k], list):
                        raw_list = data[k]
                        break
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                if isinstance(item, dict):
                    p_raw = item.get("period")

                    # টাইগার প্রো এপিআই-তে actual_number থাকে, অন্যগুলোতে number
                    n_raw = item.get("actual_number")
                    if n_raw is None:
                        n_raw = item.get("number")

                    if p_raw is not None and n_raw is not None:
                        period = str(p_raw).strip()
                        try:
                            num = int(n_raw)
                        except (ValueError, TypeError):
                            continue

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
                return formatted[:500], str(root_period).strip() if root_period else None
    except Exception as e:
        logger.error(f"API Fetch Error ({api_url}): {e}")
    return [], None

# =========================================================
# PREDICTION ENGINES (ADAPTIVE FOR 10 TO 500 RECORDS)
# =========================================================
def calculate_red_pro_prediction(market_records):
    """RED PRO WINNER: হিস্ট্রি ছোট বা বড় উভয় ক্ষেত্রে উপযুক্ত"""
    if len(market_records) < 2:
        return {"size": "BIG", "num": "5,8", "color": "RED"}

    t1 = market_records[0]["number"]
    t2 = market_records[1]["number"]

    found_idx = -1
    # রেকর্ড সংখ্যা ২০ এর বেশি হলে ২য় পেজ স্কিপ করবে, কম থাকলে ১ম পেজ থেকেই প্যাটার্ন খুঁজবে
    start_search = 20 if len(market_records) >= 25 else 2
    for i in range(start_search, len(market_records) - 1):
        curr_pair = (market_records[i]["number"], market_records[i + 1]["number"])
        if curr_pair == (t1, t2) or curr_pair == (t2, t1):
            found_idx = i
            break

    if found_idx == -1:
        n_above = (t1 + 3) % 10
        n_below = (t2 + 7) % 10
    else:
        n_above = market_records[found_idx - 1]["number"] if found_idx - 1 >= 0 else (t1 + 4) % 10
        n_below = market_records[found_idx + 1]["number"] if found_idx + 1 < len(market_records) else (t2 + 6) % 10

    pair_nums = {n_above, n_below}

    # কাস্টম কালার
    if pair_nums.issubset(GREEN_AFFINITY) or (9 in pair_nums and 5 in pair_nums) or (3 in pair_nums and 5 in pair_nums) or (9 in pair_nums and 3 in pair_nums):
        pred_color = "GREEN"
    elif pair_nums.issubset(RED_AFFINITY) or (0 in pair_nums and any(x in RED_NUMBERS for x in pair_nums)):
        pred_color = "RED"
    else:
        c_above = get_color(n_above)
        c_below = get_color(n_below)
        pred_color = c_above if c_above == c_below else "GREEN"

    # কাস্টম সাইজ
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

def calculate_green_pro_prediction(market_records):
    """GREEN PRO WINNER: ৩ ডিজিট স্নাইপার ও ট্রেন্ড মূল্যায়ন"""
    if len(market_records) < 2:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}

    sample = market_records[:150]
    latest_num = sample[0]["number"]

    transitions = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == latest_num:
            transitions.append(sample[idx]["number"])

    follow_up_candidates = [n for n, _ in Counter(transitions).most_common(2)]
    recent_nums = [r["number"] for r in sample[:40]]
    hot_candidates = [n for n, _ in Counter(recent_nums).most_common(3)]
    mirror_candidate = (9 - latest_num)

    predicted_pool = []
    for c in follow_up_candidates + hot_candidates + [mirror_candidate, (latest_num + 3) % 10, (latest_num + 7) % 10]:
        if c not in predicted_pool and 0 <= c <= 9:
            predicted_pool.append(c)
        if len(predicted_pool) == 3:
            break

    target_3_numbers = sorted(predicted_pool)
    num_str = f"{target_3_numbers[0]},{target_3_numbers[1]},{target_3_numbers[2]}"

    # সাইজ ডিটারমিনেশন
    sizes = [r["size"] for r in sample[:10]]
    big_count = sizes.count("BIG")
    if big_count >= 7:
        pred_size = "SMALL"
    elif big_count <= 3:
        pred_size = "BIG"
    else:
        big_in_target = sum(1 for n in target_3_numbers if n >= 5)
        pred_size = "BIG" if big_in_target >= 2 else "SMALL"

    # কালার ডিটারমিনেশন
    colors = [r["color"] for r in sample[:10]]
    green_count = colors.count("GREEN")
    red_count = colors.count("RED")

    if green_count > red_count:
        pred_color = "GREEN" if (colors[0] != "GREEN" or green_count >= 6) else "RED"
    else:
        pred_color = "RED" if (colors[0] != "RED" or red_count >= 6) else "GREEN"

    return {
        "size": pred_size,
        "num": num_str,
        "color": pred_color
    }

def evaluate_history_outcomes(m_state: MarketState, data):
    for rec in data[:6]:
        p = rec["period"]
        act_n = rec["number"]
        act_s = rec["size"]
        act_c = rec["color"]

        # RED PRO মূল্যায়ন
        if p in m_state.history_red and p not in m_state.win_loss_red:
            h_red = m_state.history_red[p]
            pred_nums = [int(x.strip()) for x in h_red.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums:
                m_state.win_loss_red[p] = "JAC"
            elif (h_red.get("size") == act_s) or (h_red.get("color") == act_c):
                m_state.win_loss_red[p] = "WIN"
            else:
                m_state.win_loss_red[p] = "LOSS"

        # GREEN PRO মূল্যায়ন
        if p in m_state.history_green and p not in m_state.win_loss_green:
            h_green = m_state.history_green[p]
            pred_nums_g = [int(x.strip()) for x in h_green.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums_g:
                m_state.win_loss_green[p] = "JAC"
            elif (h_green.get("size") == act_s) or (h_green.get("color") == act_c):
                m_state.win_loss_green[p] = "WIN"
            else:
                m_state.win_loss_green[p] = "LOSS"

# =========================================================
# UI MARKUPS
# =========================================================
def get_start_market_markup():
    """প্রথম স্ক্রিন: ২টি মার্কেট বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_30s = types.InlineKeyboardButton(to_vip("WINGO 30 SEC"), callback_data="select_market_30S")
    btn_5m = types.InlineKeyboardButton(to_vip("WINGO 5 MIN"), callback_data="select_market_5M")
    markup.add(btn_30s, btn_5m)
    return markup

def get_engine_selection_markup(market_key: str):
    """মার্কেট সিলেক্ট করার পর ২টি ইঞ্জিন বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_red = types.InlineKeyboardButton(to_vip("RED PRO WINNER"), callback_data=f"launch_{market_key}_RED")
    btn_green = types.InlineKeyboardButton(to_vip("GREEN PRO WINNER"), callback_data=f"launch_{market_key}_GREEN")
    btn_back = types.InlineKeyboardButton(to_vip("BACK TO MARKETS"), callback_data="back_markets")
    markup.add(btn_red, btn_green, btn_back)
    return markup

def get_dashboard_header(market_key: str, mode: str) -> str:
    market_name = MARKETS[market_key]["name"]
    mode_name = "RED PRO WINNER" if mode == "RED" else "GREEN PRO WINNER"
    return (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(mode_name)}</b>\n"
        "────────────────────────"
    )

def create_market_markup(market_key: str = "5M", page: int = 1, mode: str = "RED"):
    """লাইভ মার্কেট টেবিল ও ড্যাশবোর্ড"""
    m_state = state.markets[market_key]
    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. পিরিয়ড বাটন
    period_str = m_state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # ২. টাইমার ও অ্যানিমেটেড প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % m_state.interval
    remaining = m_state.interval - elapsed

    total_blocks = 20
    filled_blocks = int((elapsed / m_state.interval) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. প্রেডিকশন ভ্যালু
    pred = m_state.pred_red if mode == "RED" else m_state.pred_green
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. টেবিল ডাটা (১০টি রো)
    total_records = len(m_state.market_data)
    available_pages = max(1, (total_records + 9) // 10)
    page = max(1, min(available_pages, page))

    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = m_state.market_data[start_idx:end_idx]

    records_outcome = m_state.win_loss_red if mode == "RED" else m_state.win_loss_green

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

    # খালি থাকলে ড্যাশ পূরণ
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন
    prev_page = page - 1 if page > 1 else available_pages
    next_page = page + 1 if page < available_pages else 1
    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(available_pages))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. ইঞ্জিন ও মার্কেট পরিবর্তনের বাটন
    switch_engine_target = "GREEN" if mode == "RED" else "RED"
    btn_switch_engine = types.InlineKeyboardButton(to_vip(f"SWITCH TO {switch_engine_target} PRO"), callback_data=f"mode_{switch_engine_target}")

    switch_market_target = "5M" if market_key == "30S" else "30S"
    btn_switch_market = types.InlineKeyboardButton(to_vip(f"SWITCH TO {MARKETS[switch_market_target]['name']}"), callback_data=f"switchmarket_{switch_market_target}")

    btn_back_main = types.InlineKeyboardButton(to_vip("MAIN MENU"), callback_data="back_markets")

    markup.row(btn_switch_engine)
    markup.row(btn_switch_market)
    markup.row(btn_back_main)

    return markup

# =========================================================
# DUAL WORKER LOOPS
# =========================================================
def market_processing_worker(market_key: str):
    """নির্দিষ্ট মার্কেটের ডেটা ফেচিং ও প্রেডিকশন হ্যান্ডলার"""
    m_state = state.markets[market_key]
    sleep_time = 1.5 if market_key == "30S" else 3.0

    while True:
        try:
            data, root_p = fetch_api_market(m_state.api_url)
            if data:
                with state.lock:
                    m_state.market_data = data
                    top_record = data[0]
                    top_period = root_p if root_p else top_record["period"]

                    if top_period != m_state.last_fetched_period:
                        m_state.last_fetched_period = top_period

                        try:
                            next_period_num = int(top_period) + 1
                            next_period_str = str(next_period_num).zfill(len(top_period))
                        except Exception:
                            next_period_str = f"{int(time.time() // m_state.interval) + 1}"

                        m_state.current_period = next_period_str

                        # ফলাফল নির্ধারণ
                        evaluate_history_outcomes(m_state, data)

                        # RED PRO প্রেডিকশন
                        pred_r = calculate_red_pro_prediction(m_state.market_data)
                        m_state.pred_red = {
                            "period": next_period_str,
                            "size": pred_r["size"],
                            "num": pred_r["num"],
                            "color": pred_r["color"]
                        }
                        m_state.history_red[next_period_str] = {**m_state.pred_red, "timestamp": datetime.now()}

                        # GREEN PRO প্রেডিকশন
                        pred_g = calculate_green_pro_prediction(m_state.market_data)
                        m_state.pred_green = {
                            "period": next_period_str,
                            "size": pred_g["size"],
                            "num": pred_g["num"],
                            "color": pred_g["color"]
                        }
                        m_state.history_green[next_period_str] = {**m_state.pred_green, "timestamp": datetime.now()}

            m_state.clean_old_records()
        except Exception as e:
            logger.error(f"Error in {market_key} worker: {e}")

        time.sleep(sleep_time)

def real_time_ui_broadcaster():
    """লাইভ টাইমার ও টেবিল আপডেট ডিসপ্যাচার"""
    while True:
        try:
            with state.lock:
                chats_snapshot = list(state.active_chats.items())

            for chat_id, info in chats_snapshot:
                try:
                    m_key = info.get("market", "5M")
                    p_num = info.get("page", 1)
                    e_mode = info.get("mode", "RED")

                    markup = create_market_markup(market_key=m_key, page=p_num, mode=e_mode)
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
            logger.error(f"Broadcaster error: {e}")

        time.sleep(2)

# =========================================================
# BOT COMMANDS & HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_start_menu(message):
    chat_id = message.chat.id
    welcome_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SELECT WINGO MARKET')}</i>\n"
        "────────────────────────"
    )
    markup = get_start_market_markup()
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # ১. ব্যাক টু মার্কেট মেনু
    if data == "back_markets":
        welcome_text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<i>{to_vip('SELECT WINGO MARKET')}</i>\n"
            "────────────────────────"
        )
        try:
            bot.edit_message_text(
                welcome_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=get_start_market_markup()
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        return

    # ২. মার্কেট বাছাই (30S বা 5M)
    if data.startswith("select_market_"):
        selected_market = data.split("_")[2]
        market_name = MARKETS[selected_market]["name"]
        text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
            f"<i>{to_vip('CHOOSE PREDICTION ENGINE')}</i>\n"
            "────────────────────────"
        )
        try:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=get_engine_selection_markup(selected_market)
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id, text=to_vip(f"{market_name} SELECTED"))
        return

    # ৩. ড্যাশবোর্ড লঞ্চ
    if data.startswith("launch_"):
        parts = data.split("_")
        chosen_market = parts[1]
        chosen_mode = parts[2]

        header_text = get_dashboard_header(chosen_market, chosen_mode)
        markup = create_market_markup(market_key=chosen_market, page=1, mode=chosen_mode)

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
                "market": chosen_market,
                "page": 1,
                "mode": chosen_mode
            }
        bot.answer_callback_query(call.id, text=to_vip(f"{chosen_mode} ACTIVATED"))
        return

    # ৪. ইঞ্জিন পরিবর্তন
    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with state.lock:
            info = state.active_chats.get(chat_id, {"market": "5M", "page": 1, "mode": "RED"})
            curr_market = info.get("market", "5M")
            curr_page = info.get("page", 1)
            state.active_chats[chat_id] = {
                "message_id": call.message.message_id,
                "market": curr_market,
                "page": curr_page,
                "mode": new_mode
            }

        header_text = get_dashboard_header(curr_market, new_mode)
        markup = create_market_markup(market_key=curr_market, page=curr_page, mode=new_mode)

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

    # ৫. মার্কেট পরিবর্তন
    if data.startswith("switchmarket_"):
        new_market = data.split("_")[1]
        with state.lock:
            info = state.active_chats.get(chat_id, {"market": "5M", "page": 1, "mode": "RED"})
            curr_mode = info.get("mode", "RED")
            state.active_chats[chat_id] = {
                "message_id": call.message.message_id,
                "market": new_market,
                "page": 1,
                "mode": curr_mode
            }

        header_text = get_dashboard_header(new_market, curr_mode)
        markup = create_market_markup(market_key=new_market, page=1, mode=curr_mode)

        try:
            bot.edit_message_text(
                header_text,
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception:
            pass

        bot.answer_callback_query(call.id, text=to_vip(f"{MARKETS[new_market]['name']} LOADED"))
        return

    # ৬. পেজিনেশন
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                info = state.active_chats.get(chat_id, {"market": "5M", "mode": "RED"})
                curr_market = info.get("market", "5M")
                curr_mode = info.get("mode", "RED")
                state.active_chats[chat_id]["page"] = page_num

            markup = create_market_markup(market_key=curr_market, page=page_num, mode=curr_mode)
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {page_num}")
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# MAIN ENTRY
# =========================================================
if __name__ == "__main__":
    print("=" * 65)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [SYSTEM ONLINE]")
    print(f"Loaded Markets: WINGO 30 SEC & WINGO 5 MIN")
    print(f"Endpoints:")
    print(f" - 30S: {MARKETS['30S']['api']}")
    print(f" - 5M:  {MARKETS['5M']['api']}")
    print("=" * 65)

    # ৩০ সেকেন্ড থ্রেড
    t_30s = threading.Thread(target=market_processing_worker, args=("30S",), daemon=True)
    t_30s.start()

    # ৫ মিনিট থ্রেড
    t_5m = threading.Thread(target=market_processing_worker, args=("5M",), daemon=True)
    t_5m.start()

    # ইউআই লাইভ আপডেট ব্রডকাস্টার
    t_ui = threading.Thread(target=real_time_ui_broadcaster, daemon=True)
    t_ui.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Crash detected: {e}. Restarting in 5s...")
            time.sleep(5)
