# -*- coding: utf-8 -*-
"""
========================================================================================
 DRX-TM ALL-IN-ONE MASTER ENGINE (WINGO UI DASHBOARD + AUTO-SIGNAL + LIVE STREAMING)
 
 1. Core Front-End (/start):
    - Dual Markets: WinGo 30 Seconds & WinGo 5 Minutes
    - Engine 1: RED PRO WINNER (Sequence Pattern)
    - Engine 2: GREEN PRO WINNER (Markov Transition)
    - Engine 3: TIGER PRO (Deep Analytics, Moving Avg & Streak Breaker)
    - Zero Emoji Clean Professional VIP Font UI
    - 50-Pages Dynamic Pagination with Jackpot History Tracking
    - Live Background Auto-Refreshing Timer Bar

 2. Extra Automation System (/admin88 & Auto Live):
    - Auto Package Dependency Installer
    - /admin88 Channel Configuration System
    - Private /TM Time Schedule Handler (Zero Spam in Channel)
    - Auto Group Call / Live Stream Creation & 24/7 Presence (Telethon)
    - Live Call Auto-Unmute for All Joining Participants
    - Win/Loss Sticker Broadcaster
    - Safe Session Closing: Guaranteed END_STICKER after a final WIN
========================================================================================
"""

import sys
import subprocess

# =========================================================
# ১. স্বয়ংক্রিয় প্যাকেজ ইন্সটলার (Auto Package Installer)
# =========================================================
REQUIRED_LIBS = {
    "requests": "requests",
    "telebot": "pyTelegramBotAPI",
    "telethon": "telethon"
}

def auto_install_packages():
    for import_name, package_name in REQUIRED_LIBS.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"[!] '{package_name}' পাওয়া যায়নি। ইন্সটল করা হচ্ছে...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                print(f"[✓] {package_name} সফলভাবে ইন্সটল হয়েছে।")
            except Exception as e:
                print(f"[X] প্যাকেজ ইন্সটল ব্যর্থ হয়েছে: {e}")
                sys.exit(1)

auto_install_packages()

import os
import time
import json
import random
import re
import logging
import threading
import asyncio
from datetime import datetime, timedelta, timezone
from collections import Counter
import requests

import telebot
from telebot import types

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.phone import (
    CreateGroupCallRequest,
    LeaveGroupCallRequest,
    EditGroupCallParticipantRequest
)
from telethon.tl.types import UpdateGroupCallParticipants, InputGroupCall

# =========================================================
# ২. মূল কনফিগারেশন এবং ক্রেডেনশিয়ালস
# =========================================================
BOT_TOKEN = "8995269165:AAGzs3OBZsa9-f-OETfFjFQN9k0M4QjbZCU"

# APIs & Intervals
API_URL_5M = "https://advanced-predict1.ai.studio/apipid.json"
API_URL_30S = "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json"
API_URL_RAW_30S = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

MARKET_INTERVAL_5M = 300
MARKET_INTERVAL_30S = 30
TOTAL_PAGES = 50
BD_TIMEZONE = timezone(timedelta(hours=6))

# টেলিথন ক্রেডেনশিয়ালস
API_ID = 32054831
API_HASH = "89fc23d0ff6763a53004996fe0c6cab2"
SESSION_STRING = "1BVtsOMMBuz49a2_210in_8j3mmQYJ1OBm2w2niDhPuTm83mfeVuXoXO_UhiWNxMvEGPhaKgwHJfDvPY8YgA_OuB0jT91aNvQy-2SV49fwWZqeqgtjra0MubJ7M0EElD1nQ2gDVCmnuKNEzJ57lKkQ8pSLf99qgvO1r6xUB1J-vj-OAfJYFLHPjb34fyOos-HjzagA6CibhLy_tEp-gzFQyF74uXI5ftt40-JrZG8CbqPVvnI8sDG-hpj_7lBlrdudzZ_gZ7Fj6tKcz_TA_EI3BeTqSzthrAMeZhkbSovmzGLBTatRFMc58RVvycts5PRaM-c17-jly3-xKix1r0gcykDA_cFJQQ="

# স্টিকার আইডিসমূহ
START_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"
WIN_STICKERS = [
    "CAACAgUAAxkBAAICympgV_mYbYJ5o_ltYTUUBv7mKTr5AALSHAACQlWYVEhO4I8eBRYYPQQ",
    "CAACAgUAAxkBAAIC2GpgXkSXM2Nm8xUq97L6CewvEjVuAALUHgACWhiJVBClJA3AM_g7PQQ"
]
LOSS_STICKER = "CAACAgUAAxkBAAICzGpgWC6gUjMbKd5TvjfoCeqHPrrtAAJOGQACxAuZVNxk4HDx8tskPQQ"
MORNING_STICKER = "CAACAgUAAxkBAAIC0GpgWErTJk46Z_CfSizMZsi2vIU0AAKaFwACE0qZVBcum6ql5maTPQQ"
END_STICKER = "CAACAgUAAxkBAAICx2pgV34mvhrXYdFo074GfPCT3DxpAAIGHAACCWOZVJ54JyHk0pq6PQQ"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
telethon_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

global_lock = threading.Lock()
telethon_loop = None

# =========================================================
# ৩. ভিআইপি ফন্ট কনভার্টার ইঞ্জিন (VIP Font Engine)
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
# ৪. রুলস ও রঙ ক্যাটাগরি
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
# ৫. মার্কেট স্টেট ম্যানেজমেন্ট (ড্যাশবোর্ড UI এর জন্য)
# =========================================================
class MarketState:
    def __init__(self, interval):
        self.interval = interval
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

        # TIGER PRO
        self.pred_tiger = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_tiger = {}
        self.win_loss_tiger = {}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=24)
        storages = [
            (self.win_loss_red, self.history_red),
            (self.win_loss_green, self.history_green),
            (self.win_loss_tiger, self.history_tiger)
        ]
        for store, hist in storages:
            to_del = [p for p, val in hist.items() if val.get("timestamp", datetime.now()) < cutoff]
            for p in to_del:
                hist.pop(p, None)
                store.pop(p, None)

state_5m = MarketState(MARKET_INTERVAL_5M)
state_30s = MarketState(MARKET_INTERVAL_30S)
active_chats = {}

# এডমিন ও চ্যানেল সিগন্যাল ডাটাবেস
users_db = {}
# Structure:
# {
#   user_id: {
#       "channel_id": "...",
#       "schedules": [(sh, sm, eh, em)],
#       "state": "WAITING",          # WAITING, RUNNING, STOPPING
#       "target_issue": None,
#       "pending_pred": None,
#       "last_was_win": True,
#       "active_call": None,
#       "in_live": False
#   }
# }

# =========================================================
# ৬. তিনটি মূল প্রেডিকশন ইঞ্জিন
# =========================================================
def calculate_red_pro_prediction(market_records):
    """Engine 1: Sequence Pattern Matching"""
    if len(market_records) < 25:
        return {"size": "--", "num": "--", "color": "--"}
    t1, t2 = market_records[0]["number"], market_records[1]["number"]
    found_idx = -1
    for i in range(20, len(market_records) - 2):
        if (market_records[i]["number"], market_records[i + 1]["number"]) in [(t1, t2), (t2, t1)]:
            found_idx = i
            break
    n_above = market_records[found_idx - 1]["number"] if found_idx != -1 else (t1 + 3) % 10
    n_below = market_records[found_idx + 2]["number"] if found_idx != -1 else (t2 + 7) % 10
    pair_nums = {n_above, n_below}

    if pair_nums.issubset(GREEN_AFFINITY) or (9 in pair_nums and 5 in pair_nums):
        pred_color = "GREEN"
    elif pair_nums.issubset(RED_AFFINITY) or (0 in pair_nums and any(x in RED_NUMBERS for x in pair_nums)):
        pred_color = "RED"
    else:
        pred_color = "GREEN" if get_color(n_above) != get_color(n_below) else get_color(n_above)

    avg = (n_above + n_below) / 2.0
    pred_size = "BIG" if avg >= 4.5 else "SMALL"
    return {"size": pred_size, "num": f"{n_above},{n_below}", "color": pred_color}

def calculate_green_pro_prediction(market_records):
    """Engine 2: Markov Transition Chain"""
    if len(market_records) < 15:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}
    sample = market_records[:100]
    latest = sample[0]["number"]
    
    transitions = [sample[idx]["number"] for idx in range(len(sample)-1) if sample[idx+1]["number"] == latest]
    cands = [n for n, _ in Counter(transitions).most_common(2)] + [9 - latest]
    pool = list(set([c for c in cands if 0 <= c <= 9] + [(latest + 3) % 10, (latest + 7) % 10]))[:3]
    
    pool.sort()
    num_str = ",".join(map(str, pool))
    pred_size = "BIG" if sum(1 for n in pool if n >= 5) >= 2 else "SMALL"
    
    green_c = [r["color"] for r in sample[:10]].count("GREEN")
    pred_color = "GREEN" if green_c >= 5 else "RED"
    return {"size": pred_size, "num": num_str, "color": pred_color}

def calculate_tiger_pro_prediction(market_records):
    """Engine 3: TIGER PRO - Deep Analytics, Moving Average & Trend Breaker"""
    if len(market_records) < 20:
        return {"size": "SMALL", "num": "2,4,6", "color": "RED"}

    sample = market_records[:100]
    last_num = sample[0]["number"]

    # 1. Frequency (Hot Numbers)
    counts = Counter([x["number"] for x in sample])
    hot_nums = [n for n, c in counts.most_common(2)]

    # 2. Moving Average for Size Trend
    recent_10_nums = [x["number"] for x in sample[:10]]
    avg_10 = sum(recent_10_nums) / 10.0
    if avg_10 > 5.0:
        pred_size = "BIG" if recent_10_nums.count(last_num) < 3 else "SMALL"
    else:
        pred_size = "SMALL" if recent_10_nums.count(last_num) < 3 else "BIG"

    # 3. Streak Breaker (Color Logic)
    recent_colors = [x["color"] for x in sample[:5]]
    if len(set(recent_colors)) == 1:
        pred_color = "RED" if recent_colors[0] == "GREEN" else "GREEN"
    else:
        color_counts = Counter([x["color"] for x in sample[:15]])
        pred_color = color_counts.most_common(1)[0][0]
        if pred_color == "VIOLET":
            pred_color = "GREEN"

    # 4. Target Numbers for Jackpot
    predicted_pool = set(hot_nums)
    if pred_size == "BIG":
        predicted_pool.update([7, 9] if pred_color == "GREEN" else [6, 8])
    else:
        predicted_pool.update([1, 3] if pred_color == "GREEN" else [2, 4])

    target_nums = list(predicted_pool)[:3]
    while len(target_nums) < 3:
        new_val = (last_num + len(target_nums) + 2) % 10
        if new_val not in target_nums:
            target_nums.append(new_val)
            
    target_nums.sort()
    num_str = ",".join(map(str, target_nums[:3]))

    return {"size": pred_size, "num": num_str, "color": pred_color}

# =========================================================
# ৭. আউটকাম এবং ডাটা ফেচার
# =========================================================
def evaluate_outcomes(data, m_state: MarketState):
    for rec in data[:6]:
        p, act_n, act_s, act_c = rec["period"], rec["number"], rec["size"], rec["color"]
        
        engines = [
            (m_state.history_red, m_state.win_loss_red),
            (m_state.history_green, m_state.win_loss_green),
            (m_state.history_tiger, m_state.win_loss_tiger)
        ]
        
        for history_store, win_loss_store in engines:
            if p in history_store and p not in win_loss_store:
                h = history_store[p]
                pred_nums = [int(x.strip()) for x in h.get("num", "").split(",") if x.strip().isdigit()]
                if act_n in pred_nums:
                    win_loss_store[p] = "JAC"
                elif h.get("size") == act_s or h.get("color") == act_c:
                    win_loss_store[p] = "WIN"
                else:
                    win_loss_store[p] = "LOSS"

def fetch_api_market(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            raw_list = data.get("prediction_history", data.get("data", data))
            
            formatted = []
            for item in (raw_list if isinstance(raw_list, list) else []):
                if isinstance(item, dict) and item.get("period") is not None and item.get("number") is not None:
                    try:
                        num = int(item["number"])
                        s_raw = str(item.get("size", "")).strip().upper()
                        c_raw = str(item.get("color", "")).strip().upper()
                        formatted.append({
                            "period": str(item["period"]).strip(),
                            "number": num,
                            "size": s_raw if s_raw in ["BIG", "SMALL"] else get_size(num),
                            "color": c_raw if c_raw in ["RED", "GREEN", "VIOLET"] else get_color(num)
                        })
                    except: pass
            return formatted[:500]
    except: pass
    return []

def fetch_latest_results_raw():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 50}
    try:
        res = requests.post(API_URL_RAW_30S, json=payload, headers=headers, timeout=5)
        if res.status_code != 200:
            res = requests.get(API_URL_RAW_30S, headers=headers, timeout=5)
        data = res.json()
        
        def extract_list(d):
            if isinstance(d, list) and len(d) > 0 and isinstance(d[0], dict) and ('issueNumber' in d[0] or 'issue' in d[0]):
                return d
            elif isinstance(d, dict):
                for v in d.values():
                    found = extract_list(v)
                    if found: return found
            return None
            
        issue_list = extract_list(data)
        if issue_list:
            parsed = []
            for item in issue_list:
                issue = str(item.get('issueNumber', item.get('issue', ''))).strip()
                num = item.get('number', item.get('result', -1))
                if issue and num != -1:
                    parsed.append({"period": issue, "number": int(num)})
            return parsed
    except Exception:
        pass
    return []

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

                        # Set Predictions for all 3 Engines
                        preds = [
                            (calculate_red_pro_prediction, "red"),
                            (calculate_green_pro_prediction, "green"),
                            (calculate_tiger_pro_prediction, "tiger")
                        ]
                        
                        for calc_func, prefix in preds:
                            pred_result = calc_func(data)
                            pred_result["period"] = next_period_str
                            setattr(m_state, f"pred_{prefix}", pred_result)
                            getattr(m_state, f"history_{prefix}")[next_period_str] = {**pred_result, "timestamp": datetime.now()}
                            
                    m_state.clean_old_records()
        except Exception:
            pass
        time.sleep(fetch_delay)

# =========================================================
# ৮. ইউআই রেন্ডারার ও ড্যাশবোর্ড মেনু (UI Renderer)
# =========================================================
def get_start_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(to_vip("WINGO 30 SECONDS"), callback_data="market_30S"),
        types.InlineKeyboardButton(to_vip("WINGO 5 MINUTES"), callback_data="market_5M")
    )
    return markup

def get_dashboard_header(market: str, mode: str) -> str:
    market_name = "WINGO 30 SECONDS" if market == "30S" else "WINGO 5 MINUTES"
    return (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<b>{to_vip('MARKET')}: {to_vip(market_name)}</b>\n"
        f"<b>{to_vip('ENGINE')}: {to_vip(mode + ' PRO')}</b>\n"
        "────────────────────────"
    )

def create_market_markup(m_state: MarketState, mode: str, page: int):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # 1. Period & Timer
    period_str = m_state.current_period or "WAITING..."
    markup.row(types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none"))
    
    elapsed = int(time.time()) % m_state.interval
    remaining = m_state.interval - elapsed
    progress_bar = "█" * int((elapsed / m_state.interval) * 20) + "▒" * (20 - int((elapsed / m_state.interval) * 20))
    markup.row(types.InlineKeyboardButton(f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]", callback_data="none"))

    # 2. Prediction Display
    pred = getattr(m_state, f"pred_{mode.lower()}")
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"
    markup.row(
        types.InlineKeyboardButton(s_val, callback_data="none"),
        types.InlineKeyboardButton(n_val, callback_data="none"),
        types.InlineKeyboardButton(c_val, callback_data="none")
    )

    # 3. Market Data Table (10 rows)
    start_idx = (max(1, min(TOTAL_PAGES, page)) - 1) * 10
    records = m_state.market_data[start_idx : start_idx + 10]
    outcomes = getattr(m_state, f"win_loss_{mode.lower()}")

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

    # 4. Pagination
    prev_p = page - 1 if page > 1 else TOTAL_PAGES
    next_p = page + 1 if page < TOTAL_PAGES else 1
    markup.row(
        types.InlineKeyboardButton(to_vip('PREV'), callback_data=f"page_{prev_p}"),
        types.InlineKeyboardButton(f"{to_vip('PAGE')} {to_vip(str(page))}/{to_vip(str(TOTAL_PAGES))}", callback_data="none"),
        types.InlineKeyboardButton(to_vip('NEXT'), callback_data=f"page_{next_p}")
    )

    # 5. Engine Selection Row
    markup.row(
        types.InlineKeyboardButton(to_vip('RED PRO'), callback_data="mode_RED"),
        types.InlineKeyboardButton(to_vip('GREEN PRO'), callback_data="mode_GREEN"),
        types.InlineKeyboardButton(to_vip('TIGER PRO'), callback_data="mode_TIGER")
    )

    # 6. Controls Row
    markup.row(
        types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh"),
        types.InlineKeyboardButton(to_vip("MAIN MENU"), callback_data="menu")
    )
    return markup

def ui_updater_loop():
    """ড্যাশবোর্ডের টাইমার ও টেবিল অটোমেটিক আপডেট রাখার থ্রেড"""
    while True:
        with global_lock:
            chats = list(active_chats.items())
            
        for chat_id, info in chats:
            try:
                msg_id, market, mode, page = info["message_id"], info["market"], info["mode"], info["page"]
                m_state = state_30s if market == "30S" else state_5m
                markup = create_market_markup(m_state, mode, page)
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=markup)
            except telebot.apihelper.ApiTelegramException: pass
            except Exception: pass
        time.sleep(2.5)

# =========================================================
# ৯. টেলিথন লাইভ স্ট্রিম ও অটো-আনমিউট ইঞ্জিন (Telethon Userbot)
# =========================================================
async def async_start_live(channel_identifier, user_id):
    """চ্যানেলে লাইভ স্ট্রিম তৈরি করা এবং অবস্থান নেওয়া"""
    try:
        try:
            entity = await telethon_client.get_entity(int(channel_identifier))
        except (ValueError, TypeError):
            entity = await telethon_client.get_entity(channel_identifier)

        call_result = await telethon_client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 VIP Live Signal Room | DRX-TM"
        ))
        
        with global_lock:
            if user_id in users_db:
                users_db[user_id]["in_live"] = True
                users_db[user_id]["active_call"] = call_result
                
        logger.info(f"[+] Live Stream Activated in {channel_identifier}")
    except Exception as e:
        logger.error(f"[-] Failed to start live in {channel_identifier}: {e}")

async def async_leave_live(user_id):
    """লাইভ থেকে লিভ নেওয়া"""
    try:
        with global_lock:
            u_data = users_db.get(user_id, {})
            call_obj = u_data.get("active_call")
            
        if call_obj:
            input_call = InputGroupCall(id=call_obj.id, access_hash=call_obj.access_hash)
            await telethon_client(LeaveGroupCallRequest(call=input_call))
            
        with global_lock:
            if user_id in users_db:
                users_db[user_id]["in_live"] = False
                users_db[user_id]["active_call"] = None
                
        logger.info(f"[-] Left Live Stream for user {user_id}")
    except Exception as e:
        logger.error(f"[-] Leave Live Error: {e}")

@telethon_client.on(events.Raw)
async def auto_unmute_participants(update):
    """লাইভ কলে কোনো মেম্বার ঢুকলে স্বয়ংক্রিয়ভাবে স্পিকিং পারমিশন (আনমিউট) দিবে"""
    if isinstance(update, UpdateGroupCallParticipants):
        for participant in update.participants:
            if getattr(participant, 'muted', False) or getattr(participant, 'muted_by_you', False):
                try:
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=update.call,
                        participant=participant.peer,
                        muted=False
                    ))
                    logger.info("[+] Auto-unmuted participant in Live!")
                except Exception as e:
                    logger.debug(f"Unmute Error: {e}")

# =========================================================
# ১০. বট কমান্ডস ও হ্যান্ডলারস (/start & /admin88)
# =========================================================
@bot.message_handler(commands=["start"])
def send_start_dashboard(message):
    """স্বাভাবিক ক্ষেত্রে /start দিলে WinGo 30S & 5M ড্যাশবোর্ড লোড হবে"""
    with global_lock:
        active_chats.pop(message.chat.id, None)
    text = (
        f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n"
        f"<i>{to_vip('SELECT MARKET SYSTEM')}</i>\n"
        "────────────────────────"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_start_markup())

@bot.message_handler(commands=["admin88"])
def admin_panel_cmd(message):
    """এক্সট্রা এডমিন প্যানেল যা দিয়ে চ্যানেল ও টাইম সেট হবে"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="btn_add_channel")
    btn_status = types.InlineKeyboardButton("📊 Bot Status", callback_data="btn_bot_status")
    markup.add(btn_add, btn_status)
    
    panel_text = (
        f"<b>⚙️ {to_vip('ADMIN CONTROL PANEL')}</b>\n"
        "────────────────────────\n"
        "আপনার চ্যানেলে অটো-সিগন্যাল ও লাইভ স্ট্রিম সেটআপ করতে নিচের বাটনে ক্লিক করুন:"
    )
    bot.send_message(message.chat.id, panel_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        return bot.answer_callback_query(call.id)

    # ── এডমিন বাটন অ্যাকশন ──
    if data == "btn_add_channel":
        guide = (
            "📢 <b>চ্যানেল যুক্ত করার ধাপসমূহ:</b>\n\n"
            "১. প্রথমে এই বটটিকে আপনার চ্যানেলে <b>Administrator</b> হিসেবে অ্যাড করুন।\n"
            "২. অ্যাডমিনশিপ দেওয়ার পর, চ্যানেলের ID (যেমন: <code>-100123456789</code>) "
            "বা ইউজারনেম (যেমন: <code>@yourchannel</code>) এখানে লিখে সেন্ড করুন:"
        )
        msg = bot.send_message(chat_id, guide)
        bot.register_next_step_handler(msg, process_channel_registration)
        return bot.answer_callback_query(call.id)

    elif data == "btn_bot_status":
        with global_lock:
            udata = users_db.get(chat_id, {})
        ch = udata.get("channel_id", "যুক্ত করা হয়নি")
        st = udata.get("state", "WAITING")
        sched = udata.get("schedules", [])
        sched_text = ", ".join([f"{format_12hr(s[0], s[1])}-{format_12hr(s[2], s[3])}" for s in sched]) if sched else "সেট করা হয়নি"
        
        status_msg = (
            f"<b>📊 {to_vip('STATUS')}</b>\n"
            f"📡 Channel: <code>{ch}</code>\n"
            f"⚡ State: <b>{st}</b>\n"
            f"🕒 Schedule: <b>{sched_text}</b>\n"
            f"🎙️ In Live: <b>{'YES' if udata.get('in_live') else 'NO'}</b>"
        )
        bot.send_message(chat_id, status_msg)
        return bot.answer_callback_query(call.id)

    # ── ড্যাশবোর্ড বাটন অ্যাকশন ──
    if data == "menu":
        with global_lock: active_chats.pop(chat_id, None)
        text = f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n<i>{to_vip('SELECT MARKET SYSTEM')}</i>\n────────────────────────"
        try: bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=get_start_markup())
        except: pass
        return

    if data.startswith("market_"):
        market_type = data.split("_")[1]
        with global_lock: 
            active_chats[chat_id] = {"message_id": call.message.message_id, "market": market_type, "mode": "TIGER", "page": 1}
        header = get_dashboard_header(market_type, "TIGER")
        m_state = state_30s if market_type == "30S" else state_5m
        try: 
            bot.edit_message_text(header, chat_id, call.message.message_id, reply_markup=create_market_markup(m_state, "TIGER", 1))
        except: pass
        return bot.answer_callback_query(call.id, text=to_vip(f"{market_type} ACTIVATED"))

    with global_lock: chat_info = active_chats.get(chat_id)
    if not chat_info: return bot.answer_callback_query(call.id, text="Please /start again")

    market, mode, page = chat_info["market"], chat_info["mode"], chat_info["page"]
    m_state = state_30s if market == "30S" else state_5m

    if data.startswith("mode_"):
        new_mode = data.split("_")[1]
        with global_lock: active_chats[chat_id]["mode"] = new_mode
        try: 
            bot.edit_message_text(get_dashboard_header(market, new_mode), chat_id, call.message.message_id, reply_markup=create_market_markup(m_state, new_mode, page))
        except: pass
        bot.answer_callback_query(call.id, text=to_vip(f"{new_mode} PRO ACTIVATED"))

    elif data.startswith("page_"):
        new_page = int(data.split("_")[1])
        with global_lock: active_chats[chat_id]["page"] = new_page
        try: 
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=create_market_markup(m_state, mode, new_page))
        except: pass
        bot.answer_callback_query(call.id, text=f"{to_vip('PAGE')} {new_page}")

    elif data == "refresh":
        try: 
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=create_market_markup(m_state, mode, page))
        except: pass
        bot.answer_callback_query(call.id, text=to_vip("REFRESHED"))

def process_channel_registration(message):
    channel_id = message.text.strip()
    user_id = message.chat.id
    
    with global_lock:
        if user_id not in users_db:
            users_db[user_id] = {
                "channel_id": channel_id,
                "schedules": [],
                "state": "WAITING",
                "target_issue": None,
                "pending_pred": None,
                "last_was_win": True,
                "active_call": None,
                "in_live": False
            }
        else:
            users_db[user_id]["channel_id"] = channel_id
            
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅\n\nএখন সিগন্যালের সময় সেট করতে <code>/TM শুরু-শেষ</code> লিখে মেসেজ দিন।\nউদাহরণ: <code>/TM 10:30AM-1:00PM</code>")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule_handler(message):
    user_id = message.chat.id
    text = message.text.strip().upper()
    
    with global_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে <b>/admin88</b> দিয়ে আপনার চ্যানেল অ্যাড করুন।")
            return
            
    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text)
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
        
        # Start Time Parsing
        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12
            
        # End Time Parsing
        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with global_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]
            
        start_str = format_12hr(sh, sm)
        end_str = format_12hr(eh, em)
        
        # শুধুমাত্র ইউজারকে রিপ্লাই দিবে, চ্যানেলে কোনো মেসেজ যাবে না
        bot.send_message(user_id, f"হ্যাঁ আমরা <b>{start_str}</b> থেকে <b>{end_str}</b> পর্যন্ত সিগন্যাল দিব এবং লাইভ পরিচালনা করব। 🎯")
    else:
        bot.send_message(user_id, "ভুল ফরম্যাট! সঠিক নিয়ম: <code>/TM 10:30AM-1:00PM</code>")

# =========================================================
# ১১. চ্যানেল সিগন্যাল ও ফলাফল ফরম্যাট
# =========================================================
def format_12hr(hour, minute):
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0: h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def is_in_schedule(now_dt, schedules):
    current_minutes = now_dt.hour * 60 + now_dt.minute
    for (sh, sm, eh, em) in schedules:
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
        if start_mins <= current_minutes < end_mins:
            return True
    return False

def send_channel_prediction(channel_id, issue, prediction):
    short_issue = str(issue)[-6:]
    if prediction == "BIG":
        digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2))
    else:
        digits = "/".join(random.sample(['0', '1', '2', '3', '4'], 2))
        
    signal_text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel_id, signal_text)
        logger.info(f"[*] Signal sent to {channel_id}: {short_issue} -> {prediction}")
    except Exception as e:
        logger.error(f"Error sending signal: {e}")

# =========================================================
# ১২. কোর ব্যাকগ্রাউন্ড মনিটরিং ও লাইভ কন্ট্রোলার লুপ
# =========================================================
def channel_signal_and_live_engine():
    last_morning_date = None
    while True:
        try:
            results = fetch_latest_results_raw()
            if not results:
                time.sleep(2)
                continue
                
            curr_issue = results[0]["period"]
            now = datetime.now(BD_TIMEZONE)
            
            # প্রতিদিন সকাল ৫:০০ টার স্টিকার
            if now.hour == 5 and now.minute == 0:
                if last_morning_date != now.date():
                    with global_lock:
                        all_users = list(users_db.items())
                    for uid, udata in all_users:
                        ch = udata.get("channel_id")
                        if ch:
                            try: bot.send_sticker(ch, MORNING_STICKER)
                            except: pass
                    last_morning_date = now.date()

            with global_lock:
                sessions = list(users_db.items())

            for user_id, udata in sessions:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])
                
                if not channel_id or not schedules:
                    continue

                active_schedule = is_in_schedule(now, schedules)
                state = udata["state"]

                # সেশন শুরু লজিক (WAITING -> RUNNING)
                if active_schedule and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except Exception as e:
                        logger.error(f"Error sending start sticker: {e}")
                    
                    # টেলিথনে স্বয়ংক্রিয় লাইভ স্টার্ট
                    if telethon_loop and not udata.get("in_live"):
                        asyncio.run_coroutine_threadsafe(
                            async_start_live(channel_id, user_id),
                            telethon_loop
                        )

                # শিডিউল শেষ হলে নিরাপদ বন্ধের প্রস্তুতি (RUNNING -> STOPPING)
                elif not active_schedule and state == "RUNNING":
                    udata["state"] = "STOPPING"
                    logger.info(f"Schedule finished for {channel_id}. Waiting for a WIN before shutdown.")

                # ফলাফল যাচাই ও স্টিকার সেন্ডিং
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")

                if target_issue and curr_issue >= target_issue:
                    matched = next((r["number"] for r in results if r["period"] == target_issue), None)
                    if matched is not None:
                        actual_size = "BIG" if matched >= 5 else "SMALL"
                        is_win = (actual_size == pending_pred)

                        try:
                            if is_win:
                                bot.send_sticker(channel_id, random.choice(WIN_STICKERS))
                            else:
                                bot.send_sticker(channel_id, LOSS_STICKER)
                        except Exception as e:
                            logger.error(f"Sticker error: {e}")

                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # সেশন শেষ: উইন হওয়ার পরপরই END_STICKER দিয়ে লাইভ ক্লোজ করবে
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                                logger.info(f"[CLOSED] Session closed with WIN for {channel_id}")
                            except Exception as e:
                                logger.error(f"End sticker error: {e}")

                            # লাইভ থেকে লিভ নেওয়া
                            if telethon_loop and udata.get("in_live"):
                                asyncio.run_coroutine_threadsafe(
                                    async_leave_live(user_id),
                                    telethon_loop
                                )
                            udata["state"] = "WAITING"

                # নতুন প্রেডিকশন পাঠানো (TIGER PRO লজিক অনুযায়ী)
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    tiger_res = calculate_tiger_pro_prediction(results)
                    prediction = tiger_res["size"]
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_channel_prediction(channel_id, next_issue, prediction)

        except Exception as e:
            logger.error(f"Loop error: {e}")

        time.sleep(2.5)

# =========================================================
# ১৩. থ্রেডস ও মেইন রানার (System Boot)
# =========================================================
def run_telethon_async_loop():
    global telethon_loop
    telethon_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_loop)
    
    async def start_client_session():
        await telethon_client.start()
        logger.info("[✓] Telethon Userbot Connected for Live Streams.")
        
    telethon_loop.run_until_complete(start_client_session())
    telethon_loop.run_forever()

if __name__ == "__main__":
    print("=" * 65)
    print(f" {to_vip('DRX-TM MASTER HYBRID SYSTEM ONLINE')} ")
    print(" 1. Interactive Wingo Dashboard (/start) Active")
    print(" 2. Auto-Live & Schedule Channel Signals (/admin88) Active")
    print("=" * 65)

    # ১. টেলিথন লাইভ ইউজারবট থ্রেড
    threading.Thread(target=run_telethon_async_loop, daemon=True).start()

    # ২. WinGo 5M & 30S মার্কেট ডাটা ফেচার থ্রেড
    threading.Thread(target=market_data_worker, args=(API_URL_5M, state_5m, 4), daemon=True).start()
    threading.Thread(target=market_data_worker, args=(API_URL_30S, state_30s, 2), daemon=True).start()

    # ৩. UI ড্যাশবোর্ড অটো-আপডেটার থ্রেড (টাইমার ও পেজ রিফ্রেশ)
    threading.Thread(target=ui_updater_loop, daemon=True).start()

    # ৪. চ্যানেল সিগন্যাল ও লাইভ মনিটর থ্রেড
    threading.Thread(target=channel_signal_and_live_engine, daemon=True).start()

    # ৫. মূল টেলিগ্রাম বট লং-পোলিং
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as err:
            logger.error(f"Bot Polling Crashed: {err}. Restarting in 5s...")
            time.sleep(5)
