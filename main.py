# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Dual-Market (30S & 5M) Professional Prediction Telegram Bot
Features:
  - Main Menu for Market Selection (30 Seconds & 5 Minutes)
  - Independent State Management & API Fetching for both markets
  - Zero Emoji Clean Professional UI (VIP Font)
  - Engine 1: RED PRO WINNER (Sequence Pattern)
  - Engine 2: GREEN PRO WINNER (Markov Transition)
  - 50-Pages Dynamic Pagination
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

# APIs & Intervals
API_URL_5M = "https://advanced-predict1.ai.studio/apipid.json"
API_URL_30S = "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json"

MARKET_INTERVAL_5M = 300  # ৫ মিনিট = ৩০০ সেকেন্ড
MARKET_INTERVAL_30S = 30  # ৩০ সেকেন্ড

TOTAL_PAGES = 50          # টোটাল ৫০ পেজ

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
global_lock = threading.Lock()

# =========================================================
# VIP FONT ENGINE (𝐀𝐁𝐂... 𝟎𝟏𝟐...)
# =========================================================
def to_vip(text: str) -> str:
    res = []
    for ch in str(text):
        code = ord(ch)
        if 65 <= code <= 90:
            res.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:
            res.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:
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
# INDEPENDENT MARKET STATE MANAGEMENT
# =========================================================
class MarketState:
    def __init__(self, interval):
        self.interval = interval
        self.current_period = ""
        self.market_data = []

        self.pred_red = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_red = {}
        self.win_loss_red = {}

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

state_5m = MarketState(MARKET_INTERVAL_5M)
state_30s = MarketState(MARKET_INTERVAL_30S)

# Active Chats tracker: {chat_id: {"message_id": int, "market": "30S"|"5M", "mode": "RED"|"GREEN", "page": int}}
active_chats = {}

# =========================================================
# PREDICTION ENGINES (Shared Logic)
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

    return {"size": pred_size, "num": f"{n_above},{n_below}", "color": pred_color}

def calculate_green_pro_prediction(market_records):
    if len(market_records) < 15:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}

    sample = market_records[:150]
    latest_num = sample[0]["number"]

    transitions = [sample[idx]["number"] for idx in range(len(sample) - 1) if sample[idx + 1]["number"] == latest_num]
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
        pred_size = "BIG" if sum(1 for n in target_3_numbers if n >= 5) >= 2 else "SMALL"

    colors_last_10 = [r["color"] for r in sample[:10]]
    green_count, red_count = colors_last_10.count("GREEN"), colors_last_10.count("RED")

    if green_count > red_count:
        pred_color = "GREEN" if (colors_last_10[0] != "GREEN" or green_count >= 6) else "RED"
    else:
        pred_color = "RED" if (colors_last_10[0] != "RED" or red_count >= 6) else "GREEN"

    return {"size": pred_size, "num": num_str, "color": pred_color}

# =========================================================
# DATA FETCHER & OUTCOME EVALUATOR
# =========================================================
def fetch_api_market(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
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
                    p_raw, n_raw = item.get("period"), item.get("number")
                    if p_raw is not None and n_raw is not None:
                        try:
                            num = int(n_raw)
                            s_raw, c_raw = str(item.get("size", "")).strip().upper(), str(item.get("color", "")).strip().upper()
                            formatted.append({
                                "period": str(p_raw).strip(),
                                "number": num,
                                "size": s_raw if s_raw in ["BIG", "SMALL"] else get_size(num),
                                "color": c_raw if c_raw in ["RED", "GREEN", "VIOLET"] else get_color(num)
                            })
                        except:
                            pass
            return formatted[:500]
    except Exception as e:
        pass
    return []

def evaluate_outcomes(data, m_state: MarketState):
    for rec in data[:6]:
        p, act_n, act_s, act_c = rec["period"], rec["number"], rec["size"], rec["color"]
        
        # RED PRO Evaluate
        if p in m_state.history_red and p not in m_state.win_loss_red:
            h = m_state.history_red[p]
            pred_nums = [int(x.strip()) for x in h.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums:
                m_state.win_loss_red[p] = "JAC"
            elif h.get("size") == act_s or h.get("color") == act_c:
                m_state.win_loss_red[p] = "WIN"
            else:
                m_state.win_loss_red[p] = "LOSS"

        # GREEN PRO Evaluate
        if p in m_state.history_green and p not in m_state.win_loss_green:
            h = m_state.history_green[p]
            pred_nums = [int(x.strip()) for x in h.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in pred_nums:
                m_state.win_loss_green[p] = "JAC"
            elif h.get("size") == act_s or h.get("color") == act_c:
                m_state.win_loss_green[p] = "WIN"
            else:
                m_state.win_loss_green[p] = "LOSS"

def market_data_worker(api_url, m_state: MarketState, fetch_delay: int):
    last_period = ""
    while True:
        try:
            data = fetch_api_market(api_url)
            if data:
                with global_lock:
                    m_state.market_data = data
                    top_period = data[0]["period"]

                    if top_period != last_period:
                        last_period = top_period
                        try:
                            next_period_str = str(int(top_period) + 1).zfill(len(top_period))
                        except:
                            next_period_str = f"{int(time.time() // m_state.interval) + 1}"
                        
                        m_state.current_period = next_period_str
                        evaluate_outcomes(data, m_state)

                        # Set New Predictions
                        r_pred = calculate_red_pro_prediction(data)
                        r_pred["period"] = next_period_str
                        m_state.pred_red = r_pred
                        m_state.history_red[next_period_str] = {**r_pred, "timestamp": datetime.now()}

                        g_pred = calculate_green_pro_prediction(data)
                        g_pred["period"] = next_period_str
                        m_state.pred_green = g_pred
                        m_state.history_green[next_period_str] = {**g_pred, "timestamp": datetime.now()}
                        
                    m_state.clean_old_records()
        except Exception:
            pass
        time.sleep(fetch_delay)

# =========================================================
# UI RENDERER & MENUS
# =========================================================
def get_start_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_30s = types.InlineKeyboardButton(to_vip("WINGO 30 SECONDS"), callback_data="market_30S")
    btn_5m = types.InlineKeyboardButton(to_vip("WINGO 5 MINUTES"), callback_data="market_5M")
    markup.add(btn_30s, btn_5m)
    return markup

def get_dashboard_header(market: str, mode: str) -> str:
    market_name = "WINGO 30 SECONDS" if market == "30S" else "WINGO 5 MINUTES"
    mode_name = "RED PRO WINNER" if mode == "RED" else "GREEN PRO WINNER"
    return (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(mode_name)}</b>\n"
        "────────────────────────"
    )

def create_market_markup(m_state: MarketState, mode: str, page: int):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # 1. Period
    period_str = m_state.current_period or "WAITING..."
    markup.row(types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none"))

    # 2. Timer & Progress
    now_ts = int(time.time())
    elapsed = now_ts % m_state.interval
    remaining = m_state.interval - elapsed
    filled = int((elapsed / m_state.interval) * 20)
    progress_bar = "█" * filled + "▒" * (20 - filled)
    markup.row(types.InlineKeyboardButton(f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]", callback_data="none"))

    # 3. Prediction
    pred = m_state.pred_red if mode == "RED" else m_state.pred_green
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"
    markup.row(
        types.InlineKeyboardButton(s_val, callback_data="none"),
        types.InlineKeyboardButton(n_val, callback_data="none"),
        types.InlineKeyboardButton(c_val, callback_data="none")
    )

    # 4. Data Table
    start_idx = (max(1, min(TOTAL_PAGES, page)) - 1) * 10
    records = m_state.market_data[start_idx : start_idx + 10]
    outcomes = m_state.win_loss_red if mode == "RED" else m_state.win_loss_green

    for item in records:
        p_full = item["period"]
        out_raw = outcomes.get(p_full, "--")
        markup.row(
            types.InlineKeyboardButton(to_vip(p_full[-4:] if len(p_full)>=4 else p_full), callback_data="none"),
            types.InlineKeyboardButton(to_vip(str(item["number"])), callback_data="none"),
            types.InlineKeyboardButton(to_vip(item["size"]), callback_data="none"),
            types.InlineKeyboardButton(to_vip(out_raw) if out_raw != "--" else "--", callback_data="none")
        )

    for _ in range(10 - len(records)):
        markup.row(*[types.InlineKeyboardButton("-", callback_data="none")]*4)

    # 5. Pagination
    prev_p = page - 1 if page > 1 else TOTAL_PAGES
    next_p = page + 1 if page < TOTAL_PAGES else 1
    markup.row(
        types.InlineKeyboardButton(to_vip('PREV'), callback_data=f"page_{prev_p}"),
        types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none"),
        types.InlineKeyboardButton(to_vip('NEXT'), callback_data=f"page_{next_p}")
    )

    # 6. Controls
    switch_target = "GREEN" if mode == "RED" else "RED"
    markup.row(types.InlineKeyboardButton(f"{to_vip('SWITCH TO ' + switch_target + ' PRO')}", callback_data=f"mode_{switch_target}"))
    markup.row(
        types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh"),
        types.InlineKeyboardButton(to_vip("MAIN MENU"), callback_data="menu")
    )
    return markup

# =========================================================
# GLOBAL UI UPDATER THREAD (Updates all active chats)
# =========================================================
def ui_updater_loop():
    while True:
        with global_lock:
            chats = list(active_chats.items())
            
        for chat_id, info in chats:
            try:
                msg_id = info["message_id"]
                market, mode, page = info["market"], info["mode"], info["page"]
                m_state = state_30s if market == "30S" else state_5m
                
                markup = create_market_markup(m_state, mode, page)
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                pass # Ignore "message is not modified" errors
            except Exception:
                pass
        time.sleep(2.5) # Update UI every 2.5 seconds to sync timer

# =========================================================
# BOT HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_start_menu(message):
    with global_lock:
        active_chats.pop(message.chat.id, None)
        
    text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SELECT MARKET SYSTEM')}</i>\n"
        "────────────────────────"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_start_markup())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    # Back to Menu
    if data == "menu":
        with global_lock:
            active_chats.pop(chat_id, None)
        text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<i>{to_vip('SELECT MARKET SYSTEM')}</i>\n"
            "────────────────────────"
        )
        try:
            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=get_start_markup())
        except:
            pass
        return

    # Market Launch
    if data.startswith("market_"):
        market_type = data.split("_")[1]
        with global_lock:
            active_chats[chat_id] = {"message_id": call.message.message_id, "market": market_type, "mode": "RED", "page": 1}
            
        header = get_dashboard_header(market_type, "RED")
        m_state = state_30s if market_type == "30S" else state_5m
        markup = create_market_markup(m_state, "RED", 1)
        try:
            bot.edit_message_text(header, chat_id, call.message.message_id, reply_markup=markup)
        except:
            pass
        bot.answer_callback_query(call.id, text=to_vip(f"{market_type} ACTIVATED"))
        return

    # User context block
    with global_lock:
        chat_info = active_chats.get(chat_id)
        
    if not chat_info:
        bot.answer_callback_query(call.id, text="Please /start again")
        return

    market = chat_info["market"]
    mode = chat_info["mode"]
    page = chat_info["page"]
    m_state = state_30s if market == "30S" else state_5m

    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with global_lock:
            active_chats[chat_id]["mode"] = new_mode
            
        header = get_dashboard_header(market, new_mode)
        markup = create_market_markup(m_state, new_mode, page)
        try:
            bot.edit_message_text(header, chat_id, call.message.message_id, reply_markup=markup)
        except:
            pass
        bot.answer_callback_query(call.id, text=to_vip(f"{new_mode} PRO ACTIVATED"))

    elif data.startswith("page_"):
        new_page = int(data.split("_")[1])
        with global_lock:
            active_chats[chat_id]["page"] = new_page
        markup = create_market_markup(m_state, mode, new_page)
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
        except:
            pass
        bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {new_page}")

    elif data == "refresh":
        markup = create_market_markup(m_state, mode, page)
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
        except:
            pass
        bot.answer_callback_query(call.id, text=to_vip("REFRESHED"))

# =========================================================
# RUN BOT & THREADS
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [SYSTEM ONLINE]")
    print("Dual Markets: WinGo 30S & WinGo 5M")
    print("=" * 60)

    # Thread 1: 5-Minute Market API Fetcher
    t1 = threading.Thread(target=market_data_worker, args=(API_URL_5M, state_5m, 4), daemon=True)
    t1.start()

    # Thread 2: 30-Second Market API Fetcher (Faster Polling)
    t2 = threading.Thread(target=market_data_worker, args=(API_URL_30S, state_30s, 2), daemon=True)
    t2.start()

    # Thread 3: Unified Global UI Updater
    t3 = threading.Thread(target=ui_updater_loop, daemon=True)
    t3.start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Crash: {e}. Restarting in 5s...")
            time.sleep(5)
