# -*- coding: utf-8 -*-
"""
========================================================================================
 DRX-TM MASTER HYBRID SYSTEM (WINGO UI DASHBOARD + AUTO-SIGNAL + AUTO-LIVE STREAM)
 Fixed & Optimized:
   - Supports 10-result API limits flawlessly for TIGER PRO calculations
   - Accurate BD Timezone sync for /TM scheduling
   - Reliable Telethon Group Call (Live) creation and persistent stay
   - Auto-unmute for all live participants
   - Safe stop after WIN sticker with END_STICKER
========================================================================================
"""

import sys
import subprocess

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
            print(f"[!] '{package_name}' পাওয়া যায়নি। ইন্সটল করা হচ্ছে...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                print(f"[✓] {package_name} সফলভাবে ইন্সটল হয়েছে।")
            except Exception as e:
                print(f"[X] প্যাকেজ ইন্সটল ব্যর্থ হয়েছে: {e}")
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
    EditGroupCallParticipantRequest,
    JoinGroupCallRequest
)
from telethon.tl.types import UpdateGroupCallParticipants, InputGroupCall, DataJSON

# =========================================================
# কনফিগারেশন
# =========================================================
BOT_TOKEN = "8995269165:AAGzs3OBZsa9-f-OETfFjFQN9k0M4QjbZCU"

API_URL_5M = "https://advanced-predict1.ai.studio/apipid.json"
API_URL_30S = "https://sh-tim-faruk-vai.ai.studio/api/apipid-tiger-pro.json"
API_URL_RAW_30S = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

MARKET_INTERVAL_5M = 300
MARKET_INTERVAL_30S = 30
TOTAL_PAGES = 50
BD_TIMEZONE = timezone(timedelta(hours=6))

# টেলিথন ক্রেডেনশিয়ালস
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
# ভিআইপি ফন্ট কনভার্টার ইঞ্জিন
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

VIOLET_NUMBERS = {0, 5}
RED_NUMBERS = {2, 4, 6, 8}
GREEN_NUMBERS = {1, 3, 7, 9}

def get_color(num: int) -> str:
    if num in VIOLET_NUMBERS:
        return "VIOLET"
    return "RED" if num in RED_NUMBERS else "GREEN"

def get_size(num: int) -> str:
    return "BIG" if num >= 5 else "SMALL"

# =========================================================
# মার্কেট স্টেট ও ডাটাবেস
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
        self.pred_tiger = {"period": "", "size": "--", "num": "--", "color": "--"}
        self.history_tiger = {}
        self.win_loss_tiger = {}

    def clean_old_records(self):
        cutoff = datetime.now() - timedelta(hours=24)
        for store, hist in [(self.win_loss_red, self.history_red), (self.win_loss_green, self.history_green), (self.win_loss_tiger, self.history_tiger)]:
            to_del = [p for p, val in hist.items() if val.get("timestamp", datetime.now()) < cutoff]
            for p in to_del:
                hist.pop(p, None)
                store.pop(p, None)

state_5m = MarketState(MARKET_INTERVAL_5M)
state_30s = MarketState(MARKET_INTERVAL_30S)
active_chats = {}

users_db = {}

# =========================================================
# TIGER PRO প্রেডিকশন ইঞ্জিন (১০টি ডাটাতেও পারফেক্ট কাজ করবে)
# =========================================================
def calculate_tiger_pro_prediction(market_records):
    if not market_records or len(market_records) < 3:
        return {"size": "BIG", "num": "5,7,9", "color": "GREEN"}

    sample = market_records[:10]
    last_num = sample[0]["number"]

    # ফ্রিকোয়েন্সি
    counts = Counter([x["number"] for x in sample])
    hot_nums = [n for n, c in counts.most_common(2)]

    # মুভিং এভারেজ
    recent_nums = [x["number"] for x in sample]
    avg = sum(recent_nums) / float(len(recent_nums))

    if avg >= 4.5:
        pred_size = "BIG" if recent_nums.count(last_num) < 2 else "SMALL"
    else:
        pred_size = "SMALL" if recent_nums.count(last_num) < 2 else "BIG"

    recent_colors = [x["color"] for x in sample[:5]]
    if len(recent_colors) >= 3 and len(set(recent_colors[:3])) == 1:
        pred_color = "RED" if recent_colors[0] == "GREEN" else "GREEN"
    else:
        color_counts = Counter([x["color"] for x in sample])
        pred_color = color_counts.most_common(1)[0][0]
        if pred_color == "VIOLET":
            pred_color = "GREEN"

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
    return {"size": pred_size, "num": ",".join(map(str, target_nums[:3])), "color": pred_color}

def calculate_red_pro_prediction(market_records):
    if len(market_records) < 3:
        return {"size": "--", "num": "--", "color": "--"}
    t1 = market_records[0]["number"]
    avg = (t1 + 5) / 2.0
    return {"size": "BIG" if avg >= 4.5 else "SMALL", "num": f"{(t1+3)%10},{(t1+7)%10}", "color": get_color(t1)}

def calculate_green_pro_prediction(market_records):
    if len(market_records) < 3:
        return {"size": "BIG", "num": "1,5,9", "color": "GREEN"}
    t1 = market_records[0]["number"]
    return {"size": "SMALL" if t1 >= 5 else "BIG", "num": f"{(9-t1)},{(t1+2)%10}", "color": "GREEN" if t1 % 2 == 1 else "RED"}

# =========================================================
# API ডাটা ফেচার
# =========================================================
def fetch_latest_results_raw():
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    payload = {"pageNumber": 1, "pageSize": 20}
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
                    num_int = int(num)
                    parsed.append({
                        "period": issue,
                        "number": num_int,
                        "size": get_size(num_int),
                        "color": get_color(num_int)
                    })
            return parsed
    except Exception as e:
        logger.error(f"Fetch raw error: {e}")
    return []

# =========================================================
# টেলিথন লাইভ ও অটো-আনমিউট ইঞ্জিন
# =========================================================
def make_sdp():
    s = random.randint(100000000, 4294967295)
    s2 = random.randint(100000000, 4294967295)
    fp = ':'.join(f'{random.randint(0,255):02X}' for _ in range(32))
    pw = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=22))
    uf = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
    cn = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
    ms = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=36))
    return json.dumps({
        "fingerprints": [{"hash": "sha-256", "setup": "actpass", "fingerprint": fp}],
        "pwd": pw, "ufrag": uf, "ssrc": s,
        "ssrc-groups": [{"semantics": "FID", "sources": [s, s2]}],
        "sources": {str(s): {"cname": cn, "msid": f"{ms} {ms}a0"}},
    })

async def async_start_live(channel_identifier, user_id):
    try:
        try:
            entity = await telethon_client.get_entity(int(channel_identifier))
        except Exception:
            entity = await telethon_client.get_entity(channel_identifier)

        call_result = await telethon_client(CreateGroupCallRequest(
            peer=entity,
            random_id=random.randint(100000, 9999999),
            title="🔴 VIP Live Signal Room | DRX-TM"
        ))

        input_call = InputGroupCall(id=call_result.call.id, access_hash=call_result.call.access_hash)
        me = await telethon_client.get_me()
        join_as = await telethon_client.get_input_entity(me)

        # ইউজারবট লাইভে জয়েন করে উপস্থিত থাকবে
        await telethon_client(JoinGroupCallRequest(
            call=input_call,
            join_as=join_as,
            muted=True,
            video_stopped=True,
            params=DataJSON(data=make_sdp())
        ))

        with global_lock:
            if user_id in users_db:
                users_db[user_id]["in_live"] = True
                users_db[user_id]["active_call"] = input_call

        logger.info(f"[+] Live started and Userbot successfully joined in {channel_identifier}")
    except Exception as e:
        logger.error(f"[-] Live stream create/join error: {e}")

async def async_leave_live(user_id):
    try:
        with global_lock:
            u_data = users_db.get(user_id, {})
            call_obj = u_data.get("active_call")

        if call_obj:
            await telethon_client(LeaveGroupCallRequest(call=call_obj))

        with global_lock:
            if user_id in users_db:
                users_db[user_id]["in_live"] = False
                users_db[user_id]["active_call"] = None

        logger.info(f"[-] Left Live Stream for user {user_id}")
    except Exception as e:
        logger.error(f"[-] Leave live error: {e}")

@telethon_client.on(events.Raw)
async def auto_unmute_participants(update):
    if isinstance(update, UpdateGroupCallParticipants):
        for participant in update.participants:
            if getattr(participant, 'muted', False) or getattr(participant, 'muted_by_you', False):
                try:
                    await telethon_client(EditGroupCallParticipantRequest(
                        call=update.call,
                        participant=participant.peer,
                        muted=False
                    ))
                    logger.info("[+] Auto-unmuted a member in Live!")
                except Exception:
                    pass

# =========================================================
# ড্যাশবোর্ড UI হ্যান্ডলার (/start)
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
    period_str = m_state.current_period or "WAITING..."
    markup.row(types.InlineKeyboardButton(f"{to_vip('PERIOD')}: {to_vip(period_str)}", callback_data="none"))
    
    elapsed = int(time.time()) % m_state.interval
    remaining = m_state.interval - elapsed
    progress_bar = "█" * int((elapsed / m_state.interval) * 20) + "▒" * (20 - int((elapsed / m_state.interval) * 20))
    markup.row(types.InlineKeyboardButton(f"{to_vip(str(remaining).zfill(2))}S [{progress_bar}]", callback_data="none"))

    pred = getattr(m_state, f"pred_{mode.lower()}")
    s_val = to_vip(pred['size']) if pred['size'] != "--" else "--"
    n_val = to_vip(pred['num']) if pred['num'] != "--" else "--"
    c_val = to_vip(pred['color']) if pred['color'] != "--" else "--"
    markup.row(
        types.InlineKeyboardButton(s_val, callback_data="none"),
        types.InlineKeyboardButton(n_val, callback_data="none"),
        types.InlineKeyboardButton(c_val, callback_data="none")
    )

    records = m_state.market_data[:10]
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

    markup.row(
        types.InlineKeyboardButton(to_vip('RED PRO'), callback_data="mode_RED"),
        types.InlineKeyboardButton(to_vip('GREEN PRO'), callback_data="mode_GREEN"),
        types.InlineKeyboardButton(to_vip('TIGER PRO'), callback_data="mode_TIGER")
    )
    markup.row(
        types.InlineKeyboardButton(to_vip("REFRESH"), callback_data="refresh"),
        types.InlineKeyboardButton(to_vip("MAIN MENU"), callback_data="menu")
    )
    return markup

@bot.message_handler(commands=["start"])
def send_start_dashboard(message):
    with global_lock:
        active_chats.pop(message.chat.id, None)
    text = f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n<i>{to_vip('SELECT MARKET SYSTEM')}</i>\n────────────────────────"
    bot.send_message(message.chat.id, text, reply_markup=get_start_markup())

# =========================================================
# এডমিন প্যানেল ও টাইম শিডিউল হ্যান্ডলার (/admin88 & /TM)
# =========================================================
@bot.message_handler(commands=["admin88"])
def admin_panel_cmd(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Add Your Channel", callback_data="btn_add_channel")
    btn_status = types.InlineKeyboardButton("📊 Bot Status", callback_data="btn_bot_status")
    markup.add(btn_add, btn_status)
    bot.send_message(message.chat.id, f"<b>⚙️ {to_vip('ADMIN CONTROL PANEL')}</b>\n────────────────────────\nআপনার চ্যানেলে অটো সিগন্যাল ও লাইভ চালাতে নিচের বাটনে ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "none":
        return bot.answer_callback_query(call.id)

    if data == "btn_add_channel":
        msg = bot.send_message(chat_id, "📢 প্রথমে বটটিকে আপনার চ্যানেলে <b>Admin</b> বানান। এরপর চ্যানেলের ইউজারনেম (যেমন: <code>@yourchannel</code>) বা আইডি (যেমন: <code>-100123456789</code>) পাঠান:")
        bot.register_next_step_handler(msg, process_channel_registration)
        return bot.answer_callback_query(call.id)

    elif data == "btn_bot_status":
        with global_lock:
            udata = users_db.get(chat_id, {})
        ch = udata.get("channel_id", "যুক্ত করা হয়নি")
        st = udata.get("state", "WAITING")
        sched = udata.get("schedules", [])
        sched_text = ", ".join([f"{format_12hr(s[0], s[1])}-{format_12hr(s[2], s[3])}" for s in sched]) if sched else "সেট করা হয়নি"
        status_msg = f"<b>📊 {to_vip('STATUS')}</b>\n📡 Channel: <code>{ch}</code>\n⚡ State: <b>{st}</b>\n🕒 Schedule: <b>{sched_text}</b>\n🎙️ In Live: <b>{'YES' if udata.get('in_live') else 'NO'}</b>"
        bot.send_message(chat_id, status_msg)
        return bot.answer_callback_query(call.id)

    if data == "menu":
        with global_lock: active_chats.pop(chat_id, None)
        text = f"<b>{to_vip('DARK KILLER')} | {to_vip('DRX-TM')}</b>\n<i>{to_vip('SELECT MARKET SYSTEM')}</i>\n────────────────────────"
        try: bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=get_start_markup())
        except: pass
        return

    if data.startswith("market_"):
        m_type = data.split("_")[1]
        with global_lock:
            active_chats[chat_id] = {"message_id": call.message.message_id, "market": m_type, "mode": "TIGER", "page": 1}
        header = get_dashboard_header(m_type, "TIGER")
        m_state = state_30s if m_type == "30S" else state_5m
        try:
            bot.edit_message_text(header, chat_id, call.message.message_id, reply_markup=create_market_markup(m_state, "TIGER", 1))
        except: pass
        return bot.answer_callback_query(call.id, text=to_vip(f"{m_type} ACTIVATED"))

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
    bot.send_message(user_id, "<b>ডান ওকে ডান</b> ✅\n\nএখন সিগন্যালের সময় সেট করতে লিখুন: <code>/TM 10:30AM-1:00PM</code>")

@bot.message_handler(regexp=r'(?i)^/TM\s+\d{1,2}:\d{2}.*')
def set_time_schedule_handler(message):
    user_id = message.chat.id
    text = message.text.strip().upper()

    with global_lock:
        if user_id not in users_db or not users_db[user_id].get("channel_id"):
            bot.send_message(user_id, "⚠️ অনুগ্রহ করে আগে <b>/admin88</b> দিয়ে চ্যানেল অ্যাড করুন।")
            return

    match = re.search(r'/TM\s+(\d{1,2}):(\d{2})\s*(AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)?', text)
    if match:
        sh, sm, sampm, eh, em, eampm = match.groups()
        sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)

        if sampm:
            if sampm == 'PM' and sh != 12: sh += 12
            if sampm == 'AM' and sh == 12: sh = 0
        else:
            if sh < 12 and sh != 0: sh += 12

        if eampm:
            if eampm == 'PM' and eh != 12: eh += 12
            if eampm == 'AM' and eh == 12: eh = 0
        else:
            if eh < 12 and eh != 0: eh += 12

        with global_lock:
            users_db[user_id]["schedules"] = [(sh, sm, eh, em)]

        start_str = format_12hr(sh, sm)
        end_str = format_12hr(eh, em)
        bot.send_message(user_id, f"হ্যাঁ আমরা <b>{start_str}</b> থেকে <b>{end_str}</b> পর্যন্ত সিগন্যাল দিব এবং লাইভ পরিচালনা করব। 🎯")
    else:
        bot.send_message(user_id, "ভুল ফরম্যাট! সঠিক নিয়ম: <code>/TM 10:30AM-1:00PM</code>")

def format_12hr(hour, minute):
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0: h12 = 12
    return f"{h12:02d}:{minute:02d} {ampm}"

def is_in_schedule(now_dt, schedules):
    cur_mins = now_dt.hour * 60 + now_dt.minute
    for (sh, sm, eh, em) in schedules:
        st_mins = sh * 60 + sm
        et_mins = eh * 60 + em
        if st_mins <= cur_mins < et_mins:
            return True
    return False

def send_channel_prediction(channel_id, issue, prediction):
    short_issue = str(issue)[-6:]
    digits = "/".join(random.sample(['5', '6', '7', '8', '9'], 2)) if prediction == "BIG" else "/".join(random.sample(['0', '1', '2', '3', '4'], 2))
    signal_text = f"""🌿🍁🌿 {prediction} SIGNAL 🌿🍁🌿
▱▱▱▱▱▱▱▱▱▱▱▱▱▱
💎 Period   ➤  {short_issue}
🎯 Action   ➤  BET {prediction} 🌹
⚡ digit   ➤   {digits}
▱▱▱▱▱▱▱▱▱▱▱▱▱▱"""
    try:
        bot.send_message(channel_id, signal_text)
    except Exception as e:
        logger.error(f"Signal send error: {e}")

# =========================================================
# ব্যাকগ্রাউন্ড সিগন্যাল ও লাইভ মনিটর লুপ
# =========================================================
def channel_signal_and_live_engine():
    while True:
        try:
            results = fetch_latest_results_raw()
            if not results:
                time.sleep(2)
                continue

            curr_issue = results[0]["period"]
            now = datetime.now(BD_TIMEZONE)

            with global_lock:
                sessions = list(users_db.items())

            for user_id, udata in sessions:
                channel_id = udata.get("channel_id")
                schedules = udata.get("schedules", [])

                if not channel_id or not schedules:
                    continue

                active_sched = is_in_schedule(now, schedules)
                state = udata["state"]

                # সেশন শুরু (WAITING -> RUNNING)
                if active_sched and state == "WAITING":
                    udata["state"] = "RUNNING"
                    udata["last_was_win"] = True
                    try:
                        bot.send_sticker(channel_id, START_STICKER)
                    except Exception as e:
                        logger.error(f"Start sticker error: {e}")

                    # টেলিথন দিয়ে লাইভ স্ট্রিম স্টার্ট করা
                    if telethon_loop and not udata.get("in_live"):
                        asyncio.run_coroutine_threadsafe(async_start_live(channel_id, user_id), telethon_loop)

                # সময় পার হলে নিরাপদ স্টপ প্রস্তুতি
                elif not active_sched and state == "RUNNING":
                    udata["state"] = "STOPPING"

                # রেজাল্ট চেক ও স্টিকার
                target_issue = udata.get("target_issue")
                pending_pred = udata.get("pending_pred")

                if target_issue and int(curr_issue) >= int(target_issue):
                    matched = next((r["number"] for r in results if r["period"] == target_issue), None)
                    if matched is not None:
                        is_win = (get_size(matched) == pending_pred)
                        try:
                            bot.send_sticker(channel_id, random.choice(WIN_STICKERS) if is_win else LOSS_STICKER)
                        except Exception: pass

                        udata["last_was_win"] = is_win
                        udata["target_issue"] = None
                        udata["pending_pred"] = None

                        # উইন হওয়ার পর সেশন বন্ধ
                        if udata["state"] == "STOPPING" and is_win:
                            try:
                                bot.send_sticker(channel_id, END_STICKER)
                            except Exception: pass

                            if telethon_loop and udata.get("in_live"):
                                asyncio.run_coroutine_threadsafe(async_leave_live(user_id), telethon_loop)
                            udata["state"] = "WAITING"

                # পরবর্তী সিগন্যাল প্রেরণ (TIGER PRO)
                if (udata["state"] == "RUNNING" or udata["state"] == "STOPPING") and udata.get("target_issue") is None:
                    tiger_res = calculate_tiger_pro_prediction(results)
                    prediction = tiger_res["size"]
                    next_issue = str(int(curr_issue) + 1)
                    udata["pending_pred"] = prediction
                    udata["target_issue"] = next_issue
                    send_channel_prediction(channel_id, next_issue, prediction)

        except Exception as e:
            logger.error(f"Live engine error: {e}")

        time.sleep(2.5)

# =========================================================
# রানার থ্রেডস
# =========================================================
def run_telethon_async_loop():
    global telethon_loop
    telethon_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(telethon_loop)

    async def start_client_session():
        await telethon_client.start()
        logger.info("[✓] Telethon Userbot Connected.")

    telethon_loop.run_until_complete(start_client_session())
    telethon_loop.run_forever()

if __name__ == "__main__":
    print("=" * 65)
    print(f" {to_vip('DRX-TM MASTER SYSTEM ONLINE')} ")
    print(" 1. WinGo UI (/start)")
    print(" 2. Auto-Live & Custom Signals (/admin88)")
    print("=" * 65)

    threading.Thread(target=run_telethon_async_loop, daemon=True).start()
    threading.Thread(target=channel_signal_and_live_engine, daemon=True).start()

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as err:
            logger.error(f"Bot Polling Crashed: {err}. Restarting in 5s...")
            time.sleep(5)
