# -*- coding: utf-8 -*-
"""
DRX-TM WinGo Multi-Market Professional Telegram Bot
Markets:
  - WinGo 30S: https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json
  - WinGo 5M:  https://advanced-predict1.ai.studio/apipid.json
Features:
  - Exact Same 4-Column Live Table Display for Both 30S & 5M Markets
  - Auto-Discovery Pure Market Parser (Handles 'market', 'history', 'list' keys)
  - Zero Extra Buttons (Single Switch Button Layout Exactly Like 5M)
  - TIGER PRO 2-Digit High-Accuracy Sniper with JAC Outcome
"""

import time
import json
import logging
import threading
import subprocess
import urllib.request
import ssl
import requests
import urllib3
from collections import Counter
from datetime import datetime, timedelta
import telebot
from telebot import types

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# CONFIGURATION
# =========================================================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"

MARKETS_CONFIG = {
    "30S": {
        "title": "WINGO 30 SECONDS",
        "short_title": "WINGO 30S",
        "primary_url": "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json",
        "fallback_url": "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json",
        "interval": 30
    },
    "5M": {
        "title": "WINGO 5 MINUTES",
        "short_title": "WINGO 5M",
        "primary_url": "https://advanced-predict1.ai.studio/apipid.json",
        "fallback_url": "https://advanced-predict1.ai.studio/apipid.json",
        "interval": 300
    }
}

TOTAL_PAGES = 50

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive"
})

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
# RULES & NUMBERS
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
# STATE STORAGE
# =========================================================
class SingleMarketState:
    def __init__(self, market_key: str):
        self.market_key = market_key
        self.current_period = ""
        self.market_data = []

        # RED PRO
        self.pred_red = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_red = {}
        self.win_loss_red = {}

        # GREEN PRO
        self.pred_green = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_green = {}
        self.win_loss_green = {}

        # TIGER PRO (30S এর বিশেষ ২-ডিজিট হাই স্নাইপার)
        self.pred_tiger = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_tiger = {}
        self.win_loss_tiger = {}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=12)
        stores = [
            (self.win_loss_red, self.history_red),
            (self.win_loss_green, self.history_green),
            (self.win_loss_tiger, self.history_tiger)
        ]
        for store, hist in stores:
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
        self.active_chats = {}

state = BotState()

# =========================================================
# ROBUST AUTO-DISCOVERY MARKET PARSER
# =========================================================
def parse_records(raw_list):
    formatted = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue

        # Period / Issue বের করা
        period = None
        for pk in ["issueNumber", "period", "issue", "periodNumber", "issue_number", "stage", "id"]:
            if pk in item and item[pk] is not None:
                period = str(item[pk]).strip()
                break

        # Number বের করা
        num = None
        for nk in ["number", "num", "open_number", "result", "open_result", "actual_number", "winning_number", "digit"]:
            if nk in item and item[nk] is not None:
                try:
                    s = str(item[nk]).strip()
                    num = int(s[-1])
                    break
                except Exception:
                    pass

        if period is None or num is None:
            continue

        # Size বের করা
        size = None
        for sk in ["size", "big_small", "bs", "type"]:
            if sk in item and item[sk]:
                s_val = str(item[sk]).strip().upper()
                if s_val in ["BIG", "SMALL"]:
                    size = s_val
                    break
        if not size:
            size = "BIG" if num >= 5 else "SMALL"

        # Color বের করা
        color = None
        for ck in ["color", "colour", "color_result"]:
            if ck in item and item[ck]:
                c_val = str(item[ck]).strip().lower()
                if "violet" in c_val or "purple" in c_val:
                    color = "VIOLET"
                    break
                elif "red" in c_val:
                    color = "RED"
                    break
                elif "green" in c_val:
                    color = "GREEN"
                    break
        if not color:
            color = "VIOLET" if num in [0, 5] else ("RED" if num in [2, 4, 6, 8] else "GREEN")

        formatted.append({
            "period": period,
            "number": num,
            "size": size,
            "color": color
        })

    # ডিসেন্ডিং সর্ট (সর্বশেষ ড্র সবার শুরুতে থাকবে)
    try:
        formatted.sort(key=lambda x: int(x["period"]) if x["period"].isdigit() else x["period"], reverse=True)
    except Exception:
        pass

    return formatted

def extract_market_from_json(data):
    if not data:
        return []
    if isinstance(data, list):
        return parse_records(data)
    if isinstance(data, dict):
        # ১. শুধুমাত্র মার্কেট কি (Key) অগ্রাধিকার দেওয়া
        for k in ["market", "market_data", "market_history", "history", "data", "list", "records", "rows", "prediction_history", "results"]:
            if k in data:
                val = data[k]
                if isinstance(val, list):
                    res = parse_records(val)
                    if res:
                        return res
                elif isinstance(val, dict):
                    for sub_k in ["market", "market_data", "list", "records", "rows", "history"]:
                        if sub_k in val and isinstance(val[sub_k], list):
                            res = parse_records(val[sub_k])
                            if res:
                                return res

        # ২. ডিকশনারির যেকোনো লিস্ট স্ক্যান
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                res = parse_records(v)
                if res:
                    return res
    return []

def fetch_json_from_url(url: str):
    # মেথড ১: Requests
    try:
        resp = session.get(url, verify=False, timeout=5)
        if resp.status_code == 200:
            return json.loads(resp.content.decode("utf-8-sig", errors="ignore"))
    except Exception:
        pass

    # মেথড ২: Curl
    try:
        cmd = ["curl", "-s", "-k", "-L", "-m", "5", url]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        if res.returncode == 0 and res.stdout.strip():
            raw_text = res.stdout.strip()
            if "{" in raw_text and "}" in raw_text:
                start = raw_text.find("{")
                end = raw_text.rfind("}") + 1
                return json.loads(raw_text[start:end])
    except Exception:
        pass

    return None

def fetch_market_data(market_key: str):
    conf = MARKETS_CONFIG[market_key]

    # প্রথমে প্রাইমারি এপিআই
    data = fetch_json_from_url(conf["primary_url"])
    records = extract_market_from_json(data)
    if records:
        return records

    # মিস হলে ফলব্যাক এপিআই
    if conf.get("fallback_url") and conf["fallback_url"] != conf["primary_url"]:
        fb_data = fetch_json_from_url(conf["fallback_url"])
        fb_records = extract_market_from_json(fb_data)
        if fb_records:
            return fb_records

    return []

# =========================================================
# PREDICTION ENGINES
# =========================================================

# ১. TIGER PRO ENGINE (বিশেষ ২-ডিজিট স্নাইপার + JAC)
def calculate_tiger_pro_prediction(market_records):
    if len(market_records) < 5:
        return {"size": "BIG", "num": "3,7", "color": "GREEN"}

    recent = market_records[:40]
    nums = [r["number"] for r in recent]
    last_num = nums[0]

    freq = Counter(nums)
    hot_top = [n for n, _ in freq.most_common(3)]

    last_seen = {}
    for n in range(10):
        try:
            last_seen[n] = nums.index(n)
        except ValueError:
            last_seen[n] = 99

    gap_sorted = sorted(last_seen.items(), key=lambda x: x[1], reverse=True)
    gap_candidate = gap_sorted[0][0]

    pool = []
    if hot_top and hot_top[0] != last_num:
        pool.append(hot_top[0])
    else:
        pool.append((last_num + 3) % 10)

    if gap_candidate not in pool:
        pool.append(gap_candidate)
    else:
        pool.append((last_num + 7) % 10)

    sniper_digits = sorted(pool[:2])
    num_str = f"{sniper_digits[0]},{sniper_digits[1]}"

    sizes_10 = [r["size"] for r in recent[:10]]
    big_c = sizes_10.count("BIG")
    if big_c >= 7:
        pred_size = "SMALL"
    elif big_c <= 3:
        pred_size = "BIG"
    else:
        pred_size = "BIG" if (sniper_digits[0] >= 5 or sniper_digits[1] >= 5) else "SMALL"

    colors_10 = [r["color"] for r in recent[:10]]
    red_c = colors_10.count("RED")
    green_c = colors_10.count("GREEN")

    if red_c > green_c:
        pred_color = "RED" if red_c >= 6 else "GREEN"
    else:
        pred_color = "GREEN" if green_c >= 6 else "RED"

    return {"size": pred_size, "num": num_str, "color": pred_color}

# ২. RED PRO ENGINE
def calculate_red_pro_prediction(market_records):
    if len(market_records) < 5:
        return {"size": "BIG", "num": "5,8", "color": "RED"}

    t1 = market_records[0]["number"]
    t2 = market_records[1]["number"] if len(market_records) > 1 else (t1 + 3) % 10

    found_idx = -1
    if len(market_records) >= 20:
        for i in range(5, len(market_records) - 2):
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

# ৩. GREEN PRO ENGINE
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

    while len(predicted_pool) < 3:
        for fb in [1, 5, 9, 3, 7, 2, 8]:
            if fb not in predicted_pool:
                predicted_pool.append(fb)
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

    return {"size": pred_size, "num": num_str, "color": pred_color}

# =========================================================
# EVALUATION & STATE MANAGEMENT
# =========================================================
def evaluate_history_outcomes(m_state, data):
    for rec in data[:6]:
        p = rec["period"]
        act_n = rec["number"]
        act_s = rec["size"]
        act_c = rec["color"]

        # TIGER PRO (২ সংখ্যার ১টি মিললেই JAC)
        if p in m_state.history_tiger and p not in m_state.win_loss_tiger:
            h = m_state.history_tiger[p]
            p_nums = [int(x.strip()) for x in h.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in p_nums:
                m_state.win_loss_tiger[p] = "JAC"
            elif (h.get("size") == act_s) or (h.get("color") == act_c):
                m_state.win_loss_tiger[p] = "WIN"
            else:
                m_state.win_loss_tiger[p] = "LOSS"

        # RED PRO
        if p in m_state.history_red and p not in m_state.win_loss_red:
            h = m_state.history_red[p]
            p_nums = [int(x.strip()) for x in h.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in p_nums:
                m_state.win_loss_red[p] = "JAC"
            elif (h.get("size") == act_s) or (h.get("color") == act_c):
                m_state.win_loss_red[p] = "WIN"
            else:
                m_state.win_loss_red[p] = "LOSS"

        # GREEN PRO
        if p in m_state.history_green and p not in m_state.win_loss_green:
            h = m_state.history_green[p]
            p_nums = [int(x.strip()) for x in h.get("num", "").split(",") if x.strip().isdigit()]
            if act_n in p_nums:
                m_state.win_loss_green[p] = "JAC"
            elif (h.get("size") == act_s) or (h.get("color") == act_c):
                m_state.win_loss_green[p] = "WIN"
            else:
                m_state.win_loss_green[p] = "LOSS"

def update_market_state(m_key: str, data: list):
    if not data:
        return

    with state.lock:
        m_state = state.markets[m_key]

        existing_issues = {r["period"] for r in m_state.market_data}
        new_records = [r for r in data if r["period"] not in existing_issues]

        if new_records:
            m_state.market_data = (new_records + m_state.market_data)[:500]
        elif not m_state.market_data:
            m_state.market_data = data[:500]

        top_record = m_state.market_data[0]
        top_period = top_record["period"]

        try:
            next_p = str(int(top_period) + 1).zfill(len(top_period))
        except Exception:
            interval = MARKETS_CONFIG[m_key]["interval"]
            next_p = f"{int(time.time() // interval) + 1}"

        m_state.current_period = next_p
        evaluate_history_outcomes(m_state, m_state.market_data)

        # প্রেডিকশন রানিং
        pr_r = calculate_red_pro_prediction(m_state.market_data)
        m_state.pred_red = {"period": next_p, "size": pr_r["size"], "num": pr_r["num"], "color": pr_r["color"]}
        m_state.history_red[next_p] = {**m_state.pred_red, "timestamp": datetime.now()}

        pr_g = calculate_green_pro_prediction(m_state.market_data)
        m_state.pred_green = {"period": next_p, "size": pr_g["size"], "num": pr_g["num"], "color": pr_g["color"]}
        m_state.history_green[next_p] = {**m_state.pred_green, "timestamp": datetime.now()}

        if m_key == "30S":
            pr_t = calculate_tiger_pro_prediction(m_state.market_data)
            m_state.pred_tiger = {"period": next_p, "size": pr_t["size"], "num": pr_t["num"], "color": pr_t["color"]}
            m_state.history_tiger[next_p] = {**m_state.pred_tiger, "timestamp": datetime.now()}

        m_state.clean_old_records()

# =========================================================
# BACKGROUND WORKERS
# =========================================================
def worker_30s():
    while True:
        try:
            data = fetch_market_data("30S")
            if data:
                update_market_state("30S", data)
        except Exception as e:
            logger.error(f"30S Loop Error: {e}")
        time.sleep(2)

def worker_5m():
    while True:
        try:
            data = fetch_market_data("5M")
            if data:
                update_market_state("5M", data)
        except Exception as e:
            logger.error(f"5M Loop Error: {e}")
        time.sleep(5)

def live_ui_updater():
    while True:
        try:
            with state.lock:
                active_list = list(state.active_chats.items())

            for chat_id, info in active_list:
                try:
                    markup = create_market_markup(
                        market_key=info.get("market", "30S"),
                        page=info.get("page", 1),
                        mode=info.get("mode", "TIGER" if info.get("market") == "30S" else "GREEN")
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
            logger.error(f"UI Updater Error: {e}")
        time.sleep(1)

# =========================================================
# UI BUILDERS
# =========================================================
def get_market_selection_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_30s = types.InlineKeyboardButton(to_vip("WINGO 30 SECONDS"), callback_data="select_market_30S")
    btn_5m = types.InlineKeyboardButton(to_vip("WINGO 5 MINUTES"), callback_data="select_market_5M")
    markup.add(btn_30s, btn_5m)
    return markup

def get_engine_selection_markup(market_key: str):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if market_key == "30S":
        btn_tiger = types.InlineKeyboardButton(to_vip("TIGER PRO WINNER"), callback_data="launch_30S_TIGER")
        btn_red = types.InlineKeyboardButton(to_vip("RED PRO WINNER"), callback_data="launch_30S_RED")
        btn_green = types.InlineKeyboardButton(to_vip("GREEN PRO WINNER"), callback_data="launch_30S_GREEN")
        markup.add(btn_tiger, btn_red, btn_green)
    else:
        btn_red = types.InlineKeyboardButton(to_vip("RED PRO WINNER"), callback_data="launch_5M_RED")
        btn_green = types.InlineKeyboardButton(to_vip("GREEN PRO WINNER"), callback_data="launch_5M_GREEN")
        markup.add(btn_red, btn_green)

    btn_back = types.InlineKeyboardButton(to_vip("BACK TO MARKETS"), callback_data="menu_markets")
    markup.add(btn_back)
    return markup

def get_dashboard_header(market_key: str, mode: str) -> str:
    m_conf = MARKETS_CONFIG[market_key]
    mode_name = f"{mode} PRO WINNER"
    return (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(m_conf['short_title'])}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(mode_name)}</b>\n"
        "────────────────────────"
    )

def create_market_markup(market_key: str = "30S", page: int = 1, mode: str = "TIGER"):
    m_state = state.markets[market_key]
    interval = MARKETS_CONFIG[market_key]["interval"]

    markup = types.InlineKeyboardMarkup(row_width=4)

    # ১. পিরিয়ড বাটন
    period_str = m_state.current_period or "CONNECTING..."
    btn_period = types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none")
    markup.row(btn_period)

    # ২. টাইমার ও প্রোগ্রেস বার
    now_ts = int(time.time())
    elapsed = now_ts % interval
    remaining = interval - elapsed

    total_blocks = 20
    filled_blocks = int((elapsed / interval) * total_blocks)
    progress_bar = "█" * filled_blocks + "▒" * (total_blocks - filled_blocks)
    timer_text = f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]"
    markup.row(types.InlineKeyboardButton(timer_text, callback_data="none"))

    # ৩. প্রেডিকশন
    if mode == "TIGER":
        pred = m_state.pred_tiger
        records_outcome = m_state.win_loss_tiger
    elif mode == "GREEN":
        pred = m_state.pred_green
        records_outcome = m_state.win_loss_green
    else:
        pred = m_state.pred_red
        records_outcome = m_state.win_loss_red

    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"

    btn_size = types.InlineKeyboardButton(f"{s_val}", callback_data="none")
    btn_num = types.InlineKeyboardButton(f"{n_val}", callback_data="none")
    btn_color = types.InlineKeyboardButton(f"{c_val}", callback_data="none")
    markup.row(btn_size, btn_num, btn_color)

    # ৪. মার্কেট ডাটা টেবিল (৫ মিনিটের মতো হুবহু একই ৪-কলাম ফরম্যাট)
    page = max(1, min(TOTAL_PAGES, page))
    start_idx = (page - 1) * 10
    end_idx = start_idx + 10
    records = m_state.market_data[start_idx:end_idx]

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

    for _ in range(10 - len(records)):
        markup.row(
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none"),
            types.InlineKeyboardButton("-", callback_data="none")
        )

    # ৫. পেজিনেশন
    prev_page = page - 1 if page > 1 else TOTAL_PAGES
    next_page = page + 1 if page < TOTAL_PAGES else 1
    btn_prev = types.InlineKeyboardButton(f"{to_vip('PREV')}", callback_data=f"page_{prev_page}")
    btn_curr = types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none")
    btn_next = types.InlineKeyboardButton(f"{to_vip('NEXT')}", callback_data=f"page_{next_page}")
    markup.row(btn_prev, btn_curr, btn_next)

    # ৬. কন্ট্রোল বাটন (৫ মিনিটের মতো সিঙ্গেল বাটন রো - কোনো ডাবল বাটন নেই)
    if market_key == "30S":
        if mode == "TIGER":
            next_mode = "RED"
        elif mode == "RED":
            next_mode = "GREEN"
        else:
            next_mode = "TIGER"
        markup.row(types.InlineKeyboardButton(to_vip(f"SWITCH {next_mode} PRO"), callback_data=f"mode_{next_mode}"))
    else:
        target_mode = "GREEN" if mode == "RED" else "RED"
        markup.row(types.InlineKeyboardButton(to_vip(f"SWITCH {target_mode} PRO"), callback_data=f"mode_{target_mode}"))

    btn_change_mkt = types.InlineKeyboardButton(to_vip("CHANGE MARKET"), callback_data="menu_markets")
    btn_refresh = types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh")
    markup.row(btn_change_mkt, btn_refresh)

    return markup

# =========================================================
# BOT HANDLERS
# =========================================================
@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    welcome_text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
        "────────────────────────"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=get_market_selection_markup())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        bot.answer_callback_query(call.id)
        return

    if data == "menu_markets":
        menu_text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<i>{to_vip('SELECT WIN-GO MARKET')}</i>\n"
            "────────────────────────"
        )
        try:
            bot.edit_message_text(menu_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_market_selection_markup())
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        return

    if data.startswith("select_market_"):
        chosen_market = data.split("_")[2]
        m_name = MARKETS_CONFIG[chosen_market]["title"]
        engine_text = (
            f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
            f"<b>{to_vip('MARKET')}: {to_vip(m_name)}</b>\n"
            f"<i>{to_vip('SELECT PREDICTION ENGINE')}</i>\n"
            "────────────────────────"
        )
        try:
            bot.edit_message_text(engine_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_engine_selection_markup(chosen_market))
        except Exception:
            pass
        bot.answer_callback_query(call.id, text=to_vip(f"{chosen_market} SELECTED"))
        return

    if data.startswith("launch_"):
        parts = data.split("_")
        chosen_market = parts[1]
        chosen_mode = parts[2]

        if not state.markets[chosen_market].market_data:
            fresh_data = fetch_market_data(chosen_market)
            if fresh_data:
                update_market_state(chosen_market, fresh_data)

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

    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with state.lock:
            info = state.active_chats.get(chat_id, {"market": "30S", "page": 1})
            curr_market = info.get("market", "30S")
            curr_page = info.get("page", 1)
            state.active_chats[chat_id]["mode"] = new_mode

        header_text = get_dashboard_header(curr_market, new_mode)
        markup = create_market_markup(market_key=curr_market, page=curr_page, mode=new_mode)

        try:
            bot.edit_message_text(header_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        except Exception:
            pass

        bot.answer_callback_query(call.id, text=to_vip(f"ENGINE: {new_mode} PRO"))
        return

    if data.startswith("page_"):
        try:
            page_num = int(data.split("_")[1])
            with state.lock:
                info = state.active_chats.get(chat_id, {"market": "30S", "mode": "TIGER"})
                curr_market = info.get("market", "30S")
                curr_mode = info.get("mode", "TIGER")
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

    elif data == "refresh":
        try:
            info = state.active_chats.get(chat_id, {"market": "30S", "page": 1, "mode": "TIGER"})
            m_key = info.get("market", "30S")
            fresh_data = fetch_market_data(m_key)
            if fresh_data:
                update_market_state(m_key, fresh_data)

            markup = create_market_markup(
                market_key=m_key,
                page=info.get("page", 1),
                mode=info.get("mode", "TIGER")
            )
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id, text=to_vip("REFRESHED"))
        except Exception:
            bot.answer_callback_query(call.id)

# =========================================================
# RUNTIME STARTUP
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"{to_vip('DARK KILLER')} | {to_vip('DRX-TM')} [ONLINE]")
    print(f"30S Market URL: {MARKETS_CONFIG['30S']['primary_url']}")
    print(f"5M Market URL:  {MARKETS_CONFIG['5M']['primary_url']}")
    print("=" * 60)

    # প্রারম্ভিক ফেচ
    init_30s = fetch_market_data("30S")
    if init_30s:
        update_market_state("30S", init_30s)
        print(f"[SUCCESS] 30S Market Connected: {len(init_30s)} live records loaded.")

    init_5m = fetch_market_data("5M")
    if init_5m:
        update_market_state("5M", init_5m)
        print(f"[SUCCESS] 5M Market Connected: {len(init_5m)} live records loaded.")

    # ওয়ার্কার চালু
    threading.Thread(target=worker_30s, daemon=True).start()
    threading.Thread(target=worker_5m, daemon=True).start()
    threading.Thread(target=live_ui_updater, daemon=True).start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling Crash: {e}. Restarting in 5s...")
            time.sleep(5)
