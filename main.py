# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Multi-Market Dual-Engine Professional Telegram Bot
Markets:
  - WinGo 30-Second (WinGo 30S)
  - WinGo 5-Minute (WinGo 5M)
Engines:
  - Engine 1: RED PRO WINNER
  - Engine 2: GREEN PRO WINNER
Features:
  - Initial Market Selector (30S / 5M)
  - Seamless In-Place Message Overwrite
  - Zero Emoji Clean VIP UI
  - Real-Time Dynamic Timer & Dual Prediction
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

# মার্কেট কনফিগারেশন
MARKETS_CONFIG = {
    "30S": {
        "title": "WINGO 30 SECONDS",
        "short_title": "WINGO 30S",
        "api_url": "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json",
        "interval": 30
    },
    "5M": {
        "title": "WINGO 5 MINUTES",
        "short_title": "WINGO 5M",
        "api_url": "https://advanced-predict1.ai.studio/apipid.json",
        "interval": 300
    }
}

TOTAL_PAGES = 50

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================================================
# VIP FONT ENGINE (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
# =========================================================
def to_vip(text: str) -> str:
    """টেক্সটকে বোল্ড প্রিমিয়াম ভিআইপি ফন্টে রূপান্তর করে"""
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
# MARKET STATE CLASS
# =========================================================
class SingleMarketState:
    def __init__(self, market_key: str):
        self.market_key = market_key
        self.current_period = ""
        self.market_data = []

        # RED PRO স্টোরেজ
        self.pred_red = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_red = {}
        self.win_loss_red = {}

        # GREEN PRO স্টোরেজ
        self.pred_green = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_green = {}
        self.win_loss_green = {}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=12)
        for store, hist in [(self.win_loss_red, self.history_red), (self.win_loss_green, self.history_green)]:
            to_del = [p for p, val in hist.items() if val.get("timestamp", datetime.now()) < cutoff]
            for p in to_del:
                hist.pop(p, None)
                store.pop(p, None)

class BotState:
    def __init__(self):
        self.lock = threading.Lock()
        self.markets = {
            "30S": SingleMarketState("30S"),
            "5M": SingleMarketState("5M")
        }
        # সক্রিয় চ্যাট লিস্ট: {chat_id: {"message_id": int, "market": "30S"|"5M", "mode": "RED"|"GREEN", "page": int}}
        self.active_chats = {}

state = BotState()

# =========================================================
# API FETCHER (HANDLES 30S AND 5M SCHEMAS)
# =========================================================
def fetch_api_data(market_key: str):
    conf = MARKETS_CONFIG[market_key]
    url = conf["api_url"]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = []

            # 30S API ফরম্যাট হ্যান্ডলিং (data -> list)
            if isinstance(data, dict):
                d_obj = data.get("data")
                if isinstance(d_obj, dict) and "list" in d_obj:
                    raw_list = d_obj["list"]
                elif isinstance(d_obj, list):
                    raw_list = d_obj
                elif "prediction_history" in data:
                    raw_list = data["prediction_history"]
                else:
                    for k in ["records", "rows", "list"]:
                        if k in data and isinstance(data[k], list):
                            raw_list = data[k]
                            break
            elif isinstance(data, list):
                raw_list = data

            formatted = []
            for item in raw_list:
                if isinstance(item, dict):
                    p_raw = item.get("issueNumber") or item.get("period")
                    n_raw = item.get("number")
                    if p_raw is None or n_raw is None:
                        continue

                    period = str(p_raw).strip()
                    try:
                        num = int(n_raw)
                    except (ValueError, TypeError):
                        continue

                    # সাইজ ও কালার নির্ধারণ
                    s_raw = str(item.get("size", "")).strip().upper()
                    c_raw = str(item.get("color", "")).strip().upper()

                    size = s_raw if s_raw in ["BIG", "SMALL"] else get_size(num)

                    if "VIOLET" in c_raw:
                        color = "VIOLET"
                    elif "RED" in c_raw:
                        color = "RED"
                    elif "GREEN" in c_raw:
                        color = "GREEN"
                    else:
                        color = get_color(num)

                    formatted.append({
                        "period": period,
                        "number": num,
                        "size": size,
                        "color": color
                    })

            if formatted:
                return formatted[:500]
    except Exception as e:
        logger.error(f"Fetch Error ({market_key}): {e}")

    return []

# =========================================================
# PREDICTION ENGINES
# =========================================================
def calculate_red_pro_prediction(market_records):
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

def calculate_green_pro_prediction(market_records):
    if len(market_records) < 15:
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
# UI MARKUP GENERATORS (NO EMOJI)
# =========================================================
def get_market_selection_markup():
    """প্রথম স্ক্রিনের মার্কেট সিলেকশন বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_30s = types.InlineKeyboardButton(to_vip("WINGO 30 SECONDS"), callback_data="select_market_30S")
    btn_5m = types.InlineKeyboardButton(to_vip("WINGO 5 MINUTES"), callback_data="select_market_5M")
    markup.add(btn_30s, btn_5m)
    return markup

def get_engine_selection_markup(market_key: str):
    """নির্দিষ্ট মার্কেটের ইঞ্জিন সিলেকশন বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_red = types.InlineKeyboardButton(to_vip("RED PRO WINNER"), callback_data=f"launch_{market_key}_RED")
    btn_green = types.InlineKeyboardButton(to_vip("GREEN PRO WINNER"), callback_data=f"launch_{market_key}_GREEN")
    btn_back = types.InlineKeyboardButton(to_vip("BACK TO MARKETS"), callback_data="menu_markets")
    markup.add(btn_red, btn_green, btn_back)
    return markup

def get_dashboard_header(market_key: str, mode: str) -> str:
    m_conf = MARKETS_CONFIG[market_key]
    mode_name = "RED PRO WINNER" if mode == "RED" else "GREEN PRO WINNER"
    return (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(m_conf['short_title'])}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(mode_name)}</b>\n"
        "────────────────────────"
    )

def create_market_markup(market_key: str = "5M", page: int = 1, mode: str = "RED"):
    m_state = state.markets[market_key]
    interval = MARKETS_CONFIG[market_key]["interval"]

    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. পিরিয়ড বাটন
    period_str = m_state.current_period or "WAITING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # ২. ডাইনামিক টাইমার ও প্রোগ্রেস বার (মার্কেট ভিত্তিক ইন্টারভ্যাল)
    now_ts = int(time.time())
    elapsed = now_ts % interval
    remaining = interval - elapsed

    total_blocks = 20
    filled_blocks = int((elapsed / interval) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. প্রেডিকশন বক্স
    pred = m_state.pred_red if mode == "RED" else m_state.pred_green
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. মার্কেট ডাটা টেবিল (প্রতি পেজে ১০টি)
    page = max(1, min(TOTAL_PAGES, page))
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

    # খালি সারি পূরণ
    for _ in range(10 - len(records)):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন বাটন
    prev_page = page - 1 if page > 1 else TOTAL_PAGES
    next_page = page + 1 if page < TOTAL_PAGES else 1
    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. ইঞ্জিন পরিবর্তন ও মার্কেট পরিবর্তন বাটন
    switch_target = "GREEN" if mode == "RED" else "RED"
    switch_label = f"SWITCH TO {switch_target} PRO"
    btn_switch = types.InlineKeyboardButton(to_vip(switch_label), callback_data=f"mode_{switch_target}")
    btn_change_mkt = types.InlineKeyboardButton(to_vip("CHANGE MARKET"), callback_data="menu_markets")
    btn_refresh = types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh")

    markup.row(btn_switch)
    markup.row(btn_change_mkt, btn_refresh)

    return markup

# =========================================================
# REAL-TIME EVALUATOR & WORKER THREAD
# =========================================================
def evaluate_history_outcomes(m_state, data):
    for rec in data[:6]:
        p = rec["period"]
        act_n = rec["number"]
        act_s = rec["size"]
        act_c = rec["color"]

        # RED PRO মূল্যায়ন
        if p in m_state.history_red and p not in m_state.win_loss_red:
            h_red = m_state.history_red[p]
            pred_nums = [int(x.strip()) for x in h_red.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums:
                m_state.win_loss_red[p] = "JAC"
            elif (h_red.get("size") == act_s) or (h_red.get("color") == act_c):
                m_state.win_loss_red[p] = "WIN"
            else:
                m_state.win_loss_red[p] = "LOSS"

        # GREEN PRO মূল্যায়ন
        if p in m_state.history_green and p not in m_state.win_loss_green:
            h_green = m_state.history_green[p]
            pred_nums_g = [int(x.strip()) for x in h_green.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums_g:
                m_state.win_loss_green[p] = "JAC"
            elif (h_green.get("size") == act_s) or (h_green.get("color") == act_c):
                m_state.win_loss_green[p] = "WIN"
            else:
                m_state.win_loss_green[p] = "LOSS"

def market_worker():
    last_periods = {"30S": "", "5M": ""}

    while True:
        try:
            for m_key in ["30S", "5M"]:
                data = fetch_api_data(m_key)
                if data:
                    with state.lock:
                        m_state = state.markets[m_key]
                        m_state.market_data = data
                        top_record = data[0]
                        top_period = top_record["period"]

                        if top_period != last_periods[m_key]:
                            last_periods[m_key] = top_period

                            try:
                                next_p = str(int(top_period) + 1).zfill(len(top_period))
                            except Exception:
                                interval = MARKETS_CONFIG[m_key]["interval"]
                                next_p = f"{int(time.time() // interval) + 1}"

                            m_state.current_period = next_p

                            # ফলাফল মূল্যায়ন
                            evaluate_history_outcomes(m_state, data)

                            # RED PRO গণনা
                            pr_r = calculate_red_pro_prediction(m_state.market_data)
                            m_state.pred_red = {
                                "period": next_p,
                                "size": pr_r["size"],
                                "num": pr_r["num"],
                                "color": pr_r["color"]
                            }
                            m_state.history_red[next_p] = {**m_state.pred_red, "timestamp": datetime.now()}

                            # GREEN PRO গণনা
                            pr_g = calculate_green_pro_prediction(m_state.market_data)
                            m_state.pred_green = {
                                "period": next_p,
                                "size": pr_g["size"],
                                "num": pr_g["num"],
                                "color": pr_g["color"]
                            }
                            m_state.history_green[next_p] = {**m_state.pred_green, "timestamp": datetime.now()}

                            m_state.clean_old_records()

            # সক্রিয় উইন্ডো অটো-রিফ্রেশ
            with state.lock:
                active_list = list(state.active_chats.items())

            for chat_id, info in active_list:
                try:
                    markup = create_market_markup(
                        market_key=info.get("market", "5M"),
                        page=info.get("page", 1),
                        mode=info.get("mode", "RED")
                    )
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
            logger.error(f"Worker Loop Error: {e}")

        time.sleep(2)

# =========================================================
# BOT COMMANDS & CALLBACK HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_welcome_market_menu(message):
    chat_id = message.chat.id
    welcome_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
        "────────────────────────"
    )
    markup = get_market_selection_markup()
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # ১. মার্কেট সিলেকশন মেনুতে ফিরে যাওয়া
    if data == "menu_markets":
        menu_text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
            "────────────────────────"
        )
        markup = get_market_selection_markup()
        try:
            bot.edit_message_text(menu_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        return

    # ২. মার্কেট সিলেক্ট করা হলে ইঞ্জিন অপশন দেখানো
    if data.startswith("select_market_"):
        chosen_market = data.split("_")[2]
        m_name = MARKETS_CONFIG[chosen_market]["title"]
        engine_text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(m_name)}</b>\n"
            f"<i>{to_vip('SELECT PREDICTION ENGINE')}</i>\n"
            "────────────────────────"
        )
        markup = get_engine_selection_markup(chosen_market)
        try:
            bot.edit_message_text(engine_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id, text=to_vip(f"{chosen_market} SELECTED"))
        return

    # ৩. নির্দিষ্ট মার্কেট ও ইঞ্জিন চালু করা (ইনস্ট্যান্ট ওভাররাইট)
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
                "mode": chosen_mode,
                "page": 1
            }
        bot.answer_callback_query(call.id, text=to_vip(f"{chosen_market} {chosen_mode} ACTIVE"))
        return

    # ৪. ইঞ্জিন পরিবর্তন (RED <-> GREEN)
    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with state.lock:
            info = state.active_chats.get(chat_id, {"market": "5M", "page": 1})
            curr_market = info.get("market", "5M")
            curr_page = info.get("page", 1)
            state.active_chats[chat_id]["mode"] = new_mode

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

        bot.answer_callback_query(call.id, text=to_vip(f"ENGINE: {new_mode} PRO"))
        return

    # ৫. পেজিনেশন (১ থেকে ৫০ পেজ)
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

    # ৬. ম্যানুয়াল রিফ্রেশ বাটন
    elif data == "refresh":
        try:
            info = state.active_chats.get(chat_id, {"market": "5M", "page": 1, "mode": "RED"})
            markup = create_market_markup(
                market_key=info.get("market", "5M"),
                page=info.get("page", 1),
                mode=info.get("mode", "RED")
            )
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, text=to_vip("REFRESHED"))
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# MAIN EXECUTION
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [MULTI-MARKET ONLINE]")
    print("Markets: WinGo 30S & WinGo 5M | Dual Engines Active")
    print("Zero Emoji Clean VIP UI | Threading Engine Started")
    print("=" * 60)

    # ব্যাকগ্রাউন্ড মার্কেট ট্র্যাকার থ্রেড
    t = threading.Thread(target=market_worker, daemon=True)
    t.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling Crash: {e}. Restarting in 5s...")
            time.sleep(5)
