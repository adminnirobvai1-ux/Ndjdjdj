# -*- coding: utf-8 -*-
"""
DRX-TM WinGo 5-Minute Dual-Engine Prediction Telegram Bot
Engines:
  1. 🔴 RED PRO WINNER   : Skip Page 1-2 Sequence Pattern + Enhanced Color/Size Affinity
  2. 🟢 GREEN PRO WINNER : 150-Round Markov Chain & Momentum 3-Digit Sniper Engine
API Endpoint: https://advanced-predict1.ai.studio/apipid.json
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
# RULES & AFFINITY DEFINITIONS
# =========================================================
VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}
BIG_NUMBERS = {5, 6, 7, 8, 9}
SMALL_NUMBERS = {0, 1, 2, 3, 4}

# গ্রিন ও রেড অ্যাফিনিটি (5 গ্রিনের সাথে গ্রিন আচরণ করে, 0 রেডের সাথে রেড আচরণ করে)
GREEN_AFFINITY = {1, 3, 5, 7, 9}
RED_AFFINITY = {0, 2, 4, 6, 8}

def get_color(num: int) -> str:
    if num in VIOLET_NUMBERS:
        return "VIOLET"
    return "RED" if num in RED_NUMBERS else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num in BIG_NUMBERS else "SMALL"

# =========================================================
# STATE MANAGEMENT & DUAL ENGINE STORAGE
# =========================================================
class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_period = ""
        self.market_data = []          # ৫০ পেজের ডাটা (সর্বোচ্চ ৫০০টি)

        # 🔴 RED PRO ডিল
        self.pred_red = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_red = {}          # {period: {"size", "num", "color", "timestamp"}}
        self.win_loss_red = {}         # {period: "JAC" | "WIN" | "LOSS"}

        # 🟢 GREEN PRO ডিল
        self.pred_green = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_green = {}        # {period: {"size", "num", "color", "timestamp"}}
        self.win_loss_green = {}       # {period: "JAC" | "WIN" | "LOSS"}

        # ব্যবহারকারীর চ্যাট স্ট্যাটাস: {chat_id: {"message_id": int, "page": int, "mode": "RED"|"GREEN"}}
        self.active_chats = {}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=24)
        with self.lock:
            for store, hist in [(self.win_loss_red, self.history_red), (self.win_loss_green, self.history_green)]:
                to_del = [p for p, val in hist.items() if val.get("timestamp", datetime.now()) < cutoff]
                for p in to_del:
                    hist.pop(p, None)
                    store.pop(p, None)

state = BotState()

# =========================================================
# API FETCHER (ONLY PURE MARKET: PERIOD, NUM, SIZE, COLOR)
# =========================================================
def fetch_api_market():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = []

            if isinstance(data, dict):
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
                return formatted[:500]
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
    return []

# =========================================================
# ENGINE 1: 🔴 RED PRO WINNER (SEQUENCE PATTERN + AFFINITY)
# =========================================================
def calculate_red_pro_prediction(market_records):
    """
    ১. টপ দুটি সংখ্যা নেওয়া হবে।
    ২. পেজ ১ ও ২ (প্রথম ২০টি রেকর্ড) বাদ দিয়ে পেজ ৩ থেকে পেজ ৫০ পর্যন্ত খোঁজা হবে।
    ৩. ৯ ও ৫ আসলে GREEN এবং BIG; ৯ ও ৩ আসলে GREEN এবং BIG; ৩ ও ৫ আসলে GREEN।
    """
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
        n_above = (t1 + 3) % 10
        n_below = (t2 + 7) % 10
    else:
        n_above = market_records[found_idx - 1]["number"]
        n_below = market_records[found_idx + 2]["number"]

    pair_nums = {n_above, n_below}

    # কাস্টম কালার রেজল্যুশন
    if pair_nums.issubset(GREEN_AFFINITY) or (9 in pair_nums and 5 in pair_nums) or (3 in pair_nums and 5 in pair_nums) or (9 in pair_nums and 3 in pair_nums):
        pred_color = "GREEN"
    elif pair_nums.issubset(RED_AFFINITY) or (0 in pair_nums and any(x in RED_NUMBERS for x in pair_nums)):
        pred_color = "RED"
    else:
        c_above = get_color(n_above)
        c_below = get_color(n_below)
        pred_color = c_above if c_above == c_below else "GREEN"

    # কাস্টম সাইজ রেজল্যুশন
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
# ENGINE 2: 🟢 GREEN PRO WINNER (150-ROUNDS 3-DIGIT HIGH-HIT)
# =========================================================
def calculate_green_pro_prediction(market_records):
    """
    ১. ১৫০টি ড্রয়ের মারকভ ট্রানজিশন ম্যাট্রিক্স (কোন সংখ্যার পর কোন সংখ্যা আসে)।
    ২. ফ্রিকোয়েন্সি মোমেন্টাম এবং হট ট্রেন্ড বিশ্লেষণ।
    ৩. ৩টি হাই-প্রোবাবিলিটি সংখ্যা প্রদান (যে কোনো একটি মিললেই JAC)।
    ৪. গতিশীল বিগ/স্মল এবং কালার ক্যালকুলেশন।
    """
    if len(market_records) < 15:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}

    sample = market_records[:150]
    latest_num = sample[0]["number"]

    # ১. মারকভ চেইন ট্রানজিশন: অতীতে latest_num এর পরে কী এসেছে
    transitions = []
    for idx in range(len(sample) - 1):
        if sample[idx + 1]["number"] == latest_num:
            transitions.append(sample[idx]["number"])

    follow_up_candidates = [n for n, _ in Counter(transitions).most_common(2)]

    # ২. হট ফ্রিকোয়েন্সি (সর্বশেষ ৪০ রাউন্ডের শীর্ষ সংখ্যা)
    recent_40 = [r["number"] for r in sample[:40]]
    hot_candidates = [n for n, _ in Counter(recent_40).most_common(3)]

    # ৩. মিরর / রিভার্সাল সংখ্যা
    mirror_candidate = (9 - latest_num)

    # ৩টি নিশ্চিত ও ইউনিক টার্গেট ডিজিট সাজানো
    predicted_pool = []
    for c in follow_up_candidates + hot_candidates + [mirror_candidate, (latest_num + 3) % 10, (latest_num + 7) % 10]:
        if c not in predicted_pool and 0 <= c <= 9:
            predicted_pool.append(c)
        if len(predicted_pool) == 3:
            break

    target_3_numbers = sorted(predicted_pool)
    num_str = f"{target_3_numbers[0]},{target_3_numbers[1]},{target_3_numbers[2]}"

    # ৪. সাইজ প্রিডিকশন (স্ট্রিক ও মুভিং এভারেজ)
    sizes_last_10 = [r["size"] for r in sample[:10]]
    big_count = sizes_last_10.count("BIG")
    if big_count >= 7:
        pred_size = "SMALL"  # স্ট্রিক রিভার্সাল
    elif big_count <= 3:
        pred_size = "BIG"
    else:
        # টার্গেট ৩টি সংখ্যার আধিক্য অনুসারে
        big_in_target = sum(1 for n in target_3_numbers if n >= 5)
        pred_size = "BIG" if big_in_target >= 2 else "SMALL"

    # ৫. কালার প্রিডিকশন (প্যারিটি ও অল্টারনেশন ডিটেকশন)
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
# UI KEYBOARD DESIGN (DUAL MODE DYNAMIC SWITCH)
# =========================================================
def create_market_markup(page: int = 1, mode: str = "RED"):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. মোড হেডার ব্যাজ
    mode_title = "🔴 RED PRO WINNER" if mode == "RED" else "🟢 GREEN PRO WINNER"
    markup.row(types.InlineKeyboardButton(f"★ {to_vip(mode_title)} ★", callback_data="none"))

    # ২. পিরিয়ড বাটন
    period_str = state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # ৩. ৫ মিনিট টাইমার ও প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % MARKET_INTERVAL
    remaining = MARKET_INTERVAL - elapsed

    total_blocks = 20
    filled_blocks = int((elapsed / MARKET_INTERVAL) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"⏳ {to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৪. প্রেডিকশন ভ্যালু বক্স (মোড অনুযায়ী মান প্রদর্শন)
    pred = state.pred_red if mode == "RED" else state.pred_green
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৫. মার্কেট ডাটা টেবিল (প্রতি পেজে ১০টি সারি)
    page = max(1, min(TOTAL_PAGES, page))
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

    # স্লট পূর্ণ না হলে খালি সারি
    remaining_rows = 10 - len(records)
    for _ in range(remaining_rows):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৬. পেজিনেশন বাটন (১ থেকে ৫০ পেজ)
    prev_page = page - 1 if page > 1 else TOTAL_PAGES
    next_page = page + 1 if page < TOTAL_PAGES else 1
    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৭. দ্রুত মোড পরিবর্তন ও রিফ্রেশ বাটন
    switch_target = "GREEN" if mode == "RED" else "RED"
    switch_label = "🟢 SWITCH TO GREEN PRO" if mode == "RED" else "🔴 SWITCH TO RED PRO"
    btn_switch = types.InlineKeyboardButton(f"{to_vip(switch_label)}", callback_data=f"mode_{switch_target}")
    btn_refresh = types.InlineKeyboardButton(f"{to_vip('REFRESH')}", callback_data="refresh")
    markup.row(btn_switch)
    markup.row(btn_refresh)

    return markup

# =========================================================
# REAL-TIME DUAL EVALUATOR THREAD
# =========================================================
def evaluate_history_outcomes(data):
    for rec in data[:6]:
        p = rec["period"]
        act_n = rec["number"]
        act_s = rec["size"]
        act_c = rec["color"]

        # ১. Evaluate RED PRO
        if p in state.history_red and p not in state.win_loss_red:
            h_red = state.history_red[p]
            pred_nums = [int(x.strip()) for x in h_red.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums:
                state.win_loss_red[p] = "JAC"
            elif (h_red.get("size") == act_s) or (h_red.get("color") == act_c):
                state.win_loss_red[p] = "WIN"
            else:
                state.win_loss_red[p] = "LOSS"

        # ২. Evaluate GREEN PRO (৩ ডিজিট নাম্বার চেক)
        if p in state.history_green and p not in state.win_loss_green:
            h_green = state.history_green[p]
            pred_nums_g = [int(x.strip()) for x in h_green.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums_g:
                state.win_loss_green[p] = "JAC"
            elif (h_green.get("size") == act_s) or (h_green.get("color") == act_c):
                state.win_loss_green[p] = "WIN"
            else:
                state.win_loss_green[p] = "LOSS"

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

                        # অতীত ড্র সমূহের মূল্যায়ন
                        evaluate_history_outcomes(data)

                        # নতুন প্রেডিকশন গণনা: RED PRO
                        pred_r = calculate_red_pro_prediction(state.market_data)
                        state.pred_red = {
                            "period": next_period_str,
                            "size": pred_r["size"],
                            "num": pred_r["num"],
                            "color": pred_r["color"]
                        }
                        state.history_red[next_period_str] = {**state.pred_red, "timestamp": datetime.now()}

                        # নতুন প্রেডিকশন গণনা: GREEN PRO (৩ ডিজিট হাই-হিট)
                        pred_g = calculate_green_pro_prediction(state.market_data)
                        state.pred_green = {
                            "period": next_period_str,
                            "size": pred_g["size"],
                            "num": pred_g["num"],
                            "color": pred_g["color"]
                        }
                        state.history_green[next_period_str] = {**state.pred_green, "timestamp": datetime.now()}

            state.clean_old_records()

            # সক্রিয় সকল চ্যাটে লাইভ রিফ্রেশ
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

        time.sleep(3)

# =========================================================
# BOT COMMAND HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_start_menu(message):
    chat_id = message.chat.id
    welcome_text = (
        f"<b>⚡ {to_vip('DRX-TM WINGO 5-MIN DUAL ENGINE')} ⚡</b>\n\n"
        f"🎯 <b>{to_vip('CHOOSE YOUR PREDICTION ENGINE')}:</b>\n\n"
        f"🔴 <b>{to_vip('RED PRO WINNER')}:</b>\n"
        f"<i>• Skip 2-Page Sequence Pattern Engine</i>\n"
        f"<i>• 9+5/9+3/3+5 Specialized Green & Big Affinity</i>\n\n"
        f"🟢 <b>{to_vip('GREEN PRO WINNER')}:</b>\n"
        f"<i>• 150-Rounds Markov Transition & Momentum</i>\n"
        f"<i>• 3-Digit High-Precision Number Sniper (Any 1 Hit = JAC)</i>\n"
        "────────────────────────"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_red = types.InlineKeyboardButton(f"🔴 {to_vip('LAUNCH RED PRO WINNER')}", callback_data="launch_RED")
    btn_green = types.InlineKeyboardButton(f"🟢 {to_vip('LAUNCH GREEN PRO WINNER')}", callback_data="launch_GREEN")
    markup.add(btn_red, btn_green)

    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # ১. স্টার্ট মেনু থেকে সরাসরি ইঞ্জিন চালু
    if data.startswith("launch_"):
        chosen_mode = data.split("_")[1]
        header_text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<i>{to_vip('WINGO 5-MIN PREDICTION')}</i>\n"
            "────────────────────────"
        )
        markup = create_market_markup(page=1, mode=chosen_mode)
        msg = bot.send_message(chat_id, header_text, reply_markup=markup)

        with state.lock:
            state.active_chats[chat_id] = {"message_id": msg.message_id, "page": 1, "mode": chosen_mode}
        bot.answer_callback_query(call.id, text=f"Activated {chosen_mode} PRO")
        return

    # ২. চলমান টেবিল থেকে ইনস্ট্যান্ট মোড পরিবর্তন
    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with state.lock:
            curr_page = state.active_chats.get(chat_id, {}).get("page", 1)
            state.active_chats[chat_id] = {"message_id": call.message.message_id, "page": curr_page, "mode": new_mode}

        markup = create_market_markup(page=curr_page, mode=new_mode)
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, text=f"Switched to {new_mode} PRO")
        return

    # ৩. পেজ পরিবর্তন (১ থেকে ৫০ পেজ সোয়াইপ)
    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                curr_mode = state.active_chats.get(chat_id, {}).get("mode", "RED")
                state.active_chats[chat_id]["page"] = page_num

            markup = create_market_markup(page=page_num, mode=curr_mode)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {page_num}")
        except Exception:
            bot.answer_callback_query(call.id)

    # ৪. রিফ্রেশ বাটন
    elif data == "refresh":
        try:
            info = state.active_chats.get(chat_id, {"page": 1, "mode": "RED"})
            markup = create_market_markup(page=info.get("page", 1), mode=info.get("mode", "RED"))
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=f"{to_vip('REFRESHED')}")
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [DUAL ENGINE ONLINE]")
    print(f"Modes: RED PRO WINNER & GREEN PRO WINNER")
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
