import os
import pty
import subprocess
import re
import time
import threading
from datetime import datetime, timedelta
import pytz
import telebot
from telebot import types

# আপনার দেওয়া টেলিগ্রাম বট টোকেন
BOT_TOKEN = os.getenv("BOT_TOKEN", "8765791320:AAFCB4Ls3ASrPW_91m6uZhmIexqRrbk9nY0")
bot = telebot.TeleBot(BOT_TOKEN)

# বাংলাদেশ টাইমজোন
BD_TZ = pytz.timezone("Asia/Dhaka")

# টার্মিনাল স্টোরেজ
terminals = {}
terminal_counter = 1
lock = threading.Lock()

def spawn_sshx():
    """ভার্চুয়াল টার্মিনাল PTY দিয়ে ব্যাকগ্রাউন্ডে sshx চালু ও লিংক রিড করে"""
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        ["sshx"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        preexec_fn=os.setsid
    )
    os.close(slave)

    url = None
    buffer = ""
    start_time = time.time()

    while time.time() - start_time < 15:
        try:
            chunk = os.read(master, 1024).decode("utf-8", errors="ignore")
            if chunk:
                buffer += chunk
                match = re.search(r"https://sshx\.io/s/[A-Za-z0-9_-]+", buffer)
                if match:
                    url = match.group(0)
                    break
        except Exception:
            break
        time.sleep(0.2)

    if not url:
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:
            pass
        try:
            os.close(master)
        except Exception:
            pass
        return None, None, None

    return proc, master, url

def kill_terminal(term_id):
    """নির্দিষ্ট টার্মিনাল কিল করার ফাংশন"""
    with lock:
        if term_id in terminals:
            info = terminals[term_id]
            try:
                os.killpg(os.getpgid(info["proc"].pid), 9)
            except Exception:
                pass
            try:
                os.close(info["master_fd"])
            except Exception:
                pass
            del terminals[term_id]
            return True
    return False

def schedule_auto_kill(term_id, delay_seconds, chat_id, expire_label):
    """টাইম শেষ হলে স্বয়ংক্রিয়ভাবে টার্মিনাল অফ করা"""
    def _runner():
        time.sleep(delay_seconds)
        if kill_terminal(term_id):
            try:
                bot.send_message(
                    chat_id,
                    f"⏰ <b>টার্মিনাল #{term_id} বন্ধ করা হয়েছে!</b>\n"
                    f"নির্ধারিত সময় ({expire_label}) শেষ হওয়ায় এটি বন্ধ হয়ে গেছে।",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()

def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("➕ ১টি টার্মিনাল", callback_data="add_1")
    b2 = types.InlineKeyboardButton("➕ ২টি টার্মিনাল", callback_data="add_2")
    b3 = types.InlineKeyboardButton("📋 রানিং লিস্ট", callback_data="list")
    b4 = types.InlineKeyboardButton("❌ সব বন্ধ", callback_data="kill_all")
    markup.add(b1, b2)
    markup.add(b3, b4)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = (
        "🚀 <b>SSHX মাল্টি-টার্মিনাল কন্ট্রোল প্যানেল</b>\n\n"
        "নিচের বাটন চেপে বা কমান্ড লিখে টার্মিনাল তৈরি করতে পারেন।\n\n"
        "<b>কমান্ডসমূহ:</b>\n"
        "• <code>/add 3</code> - ৩টি টার্মিনাল একসাথে তৈরি করতে\n"
        "• <code>/off 1</code> - ১ নম্বর আইডি টার্মিনাল বন্ধ করতে\n"
        "• <code>/tm 10:00AM-1:00PM</code> - নির্দিষ্ট সময়ে অটো-অফ করতে\n"
        "• <code>/list</code> - সব চালু টার্মিনাল দেখতে"
    )
    bot.reply_to(message, msg, parse_mode="HTML", reply_markup=main_keyboard())

def create_terminals(count, chat_id, expire_seconds=None, expire_label="আনলিমিটেড"):
    global terminal_counter
    bot.send_message(chat_id, f"⏳ {count}টি টার্মিনাল তৈরি হচ্ছে, দয়া করে একটু অপেক্ষা করুন...")

    for _ in range(count):
        proc, master_fd, url = spawn_sshx()
        if url:
            with lock:
                t_id = terminal_counter
                terminal_counter += 1
                now = datetime.now(BD_TZ)
                expire_at = (now + timedelta(seconds=expire_seconds)) if expire_seconds else None

                terminals[t_id] = {
                    "proc": proc,
                    "pid": proc.pid,
                    "master_fd": master_fd,
                    "url": url,
                    "start_time": now,
                    "expire_at": expire_at
                }

            if expire_seconds:
                schedule_auto_kill(t_id, expire_seconds, chat_id, expire_label)

            res = (
                f"✅ <b>টার্মিনাল তৈরি সফল!</b>\n\n"
                f"🔹 <b>আইডি (ID):</b> <code>{t_id}</code>\n"
                f"🔗 <b>লিংক:</b> {url}\n"
                f"⏱️ <b>মেয়াদ:</b> {expire_label}\n"
                f"🛑 বন্ধ করতে লিখুন: <code>/off {t_id}</code>"
            )
            bot.send_message(chat_id, res, parse_mode="HTML", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, "⚠️ একটি টার্মিনাল তৈরি করতে ব্যর্থ হয়েছে!")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "add_1":
        create_terminals(1, call.message.chat.id)
    elif call.data == "add_2":
        create_terminals(2, call.message.chat.id)
    elif call.data == "list":
        show_list(call.message.chat.id)
    elif call.data == "kill_all":
        with lock:
            all_ids = list(terminals.keys())
        for tid in all_ids:
            kill_terminal(tid)
        bot.send_message(call.message.chat.id, "🛑 সব টার্মিনাল বন্ধ করা হয়েছে!")
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['add'])
def handle_add(message):
    try:
        parts = message.text.strip().split()
        count = int(parts[1]) if len(parts) > 1 else 1
        if count > 20:
            bot.reply_to(message, "⚠️ একসাথে সর্বোচ্চ ২০টি টার্মিনাল তৈরি করতে পারবেন।")
            return
        create_terminals(count, message.chat.id)
    except ValueError:
        bot.reply_to(message, "ব্যবহারবিধি: <code>/add 2</code> (কয়টি বানাবেন লিখুন)", parse_mode="HTML")

@bot.message_handler(commands=['off'])
def handle_off(message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            bot.reply_to(message, "ব্যবহারবিধি: <code>/off 1</code> (টার্মিনাল আইডি দিন)", parse_mode="HTML")
            return

        term_id = int(parts[1])
        if kill_terminal(term_id):
            bot.reply_to(message, f"🛑 <b>টার্মিনাল #{term_id} সফলভাবে বন্ধ করা হয়েছে!</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ টার্মিনাল আইডি <code>{term_id}</code> পাওয়া যায়নি।", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "সঠিক আইডি লিখুন। যেমন: <code>/off 1</code>", parse_mode="HTML")

@bot.message_handler(commands=['tm', 'TM'])
def handle_timer(message):
    text = message.text.replace("/tm", "").replace("/TM", "").strip()
    if not text:
        bot.reply_to(message, "ব্যবহারবিধি: <code>/tm 10:00AM-1:00PM</code> অথবা <code>/tm 30m</code>", parse_mode="HTML")
        return

    now_bd = datetime.now(BD_TZ)
    delay_seconds = 0
    expire_label = ""

    # সময় ফরম্যাট চেক: 10:00AM-1:00PM
    if "-" in text:
        end_str = text.split("-")[1].replace(" ", "").upper()
    else:
        end_str = text.replace(" ", "").upper()

    parsed = False
    for fmt in ("%I:%M%p", "%I:%M %p", "%H:%M"):
        try:
            t = datetime.strptime(end_str, fmt.replace(" ", "")).time()
            target_dt = now_bd.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if target_dt <= now_bd:
                target_dt += timedelta(days=1)
            delay_seconds = int((target_dt - now_bd).total_seconds())
            expire_label = target_dt.strftime("%I:%M %p (BD Time)")
            parsed = True
            break
        except ValueError:
            pass

    # সময়কাল ফরম্যাট চেক: 30m বা 2h
    if not parsed and (text.endswith("m") or text.endswith("h")):
        try:
            val = int(text[:-1])
            delay_seconds = val * 60 if text.endswith("m") else val * 3600
            target_dt = now_bd + timedelta(seconds=delay_seconds)
            expire_label = target_dt.strftime("%I:%M %p (BD Time)")
            parsed = True
        except ValueError:
            pass

    if not parsed:
        bot.reply_to(message, "⚠️ সময়ের ফরম্যাট সঠিক নয়!\nউদাহরণ: <code>/tm 10:00AM-1:00PM</code> অথবা <code>/tm 45m</code>", parse_mode="HTML")
        return

    create_terminals(1, message.chat.id, expire_seconds=delay_seconds, expire_label=expire_label)

@bot.message_handler(commands=['list'])
def handle_list(message):
    show_list(message.chat.id)

def show_list(chat_id):
    with lock:
        if not terminals:
            bot.send_message(chat_id, "ℹ️ বর্তমানে কোনো সক্রিয় টার্মিনাল চালু নেই।")
            return

        msg = "📋 <b>চলমান টার্মিনালগুলোর তালিকা:</b>\n\n"
        now = datetime.now(BD_TZ)
        for tid, data in terminals.items():
            duration = str(now - data["start_time"]).split('.')[0]
            exp = data["expire_at"].strftime("%I:%M %p") if data["expire_at"] else "আনলিমিটেড"
            msg += (
                f"🔹 <b>আইডি:</b> <code>{tid}</code>\n"
                f"🔗 {data['url']}\n"
                f"⏳ চলছে: {duration}\n"
                f"⏱️ অফ হবে: {exp}\n"
                f"🛑 বন্ধ করতে: <code>/off {tid}</code>\n\n"
            )
        bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True)

if __name__ == "__main__":
    print("Telegram Terminal Bot রানিং...")
    bot.infinity_polling()

    url = None
    buffer = ""
    start_time = time.time()

    # sshx লিংক আসা পর্যন্ত সর্বোচ্চ ১৫ সেকেন্ড অপেক্ষা করবে
    while time.time() - start_time < 15:
        try:
            data = os.read(master, 1024).decode("utf-8", errors="ignore")
            buffer += data
            match = re.search(r"https://sshx\.io/s/[A-Za-z0-9_-]+", buffer)
            if match:
                url = match.group(0)
                break
        except Exception:
            break
        time.sleep(0.1)

    if not url:
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:
            pass
        os.close(master)
        return None, None, None

    return proc, master, url

def kill_terminal(term_id):
    """নির্দিষ্ট আইডি টার্মিনাল প্রসেস কিল করা"""
    with lock:
        if term_id in terminals:
            info = terminals[term_id]
            try:
                os.killpg(os.getpgid(info["proc"].pid), 9)
            except Exception:
                pass
            try:
                os.close(info["master_fd"])
            except Exception:
                pass
            del terminals[term_id]
            return True
    return False

def schedule_auto_kill(term_id, delay_seconds, chat_id, expire_time_str):
    """টাইম শেষ হলে টার্মিনাল অফ করার ব্যাকগ্রাউন্ড থ্রেড"""
    def _runner():
        time.sleep(delay_seconds)
        if term_id in terminals:
            kill_terminal(term_id)
            try:
                bot.send_message(
                    chat_id,
                    f"⏰ <b>টার্মিনাল #{term_id} বন্ধ করা হয়েছে!</b>\n"
                    f"নির্ধারিত সময় ({expire_time_str}) পূর্ণ হওয়ায় টার্মিনালটি স্বয়ংক্রিয়ভাবে অফ করা হয়েছে।",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Alert error: {e}")

    t = threading.Thread(target=_runner, daemon=True)
    t.start()

def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("➕ ১টি টার্মিনাল", callback_data="add_1")
    b2 = types.InlineKeyboardButton("➕ ২টি টার্মিনাল", callback_data="add_2")
    b3 = types.InlineKeyboardButton("📋 রানিং লিস্ট", callback_data="list")
    b4 = types.InlineKeyboardButton("❌ সব বন্ধ করুন", callback_data="kill_all")
    markup.add(b1, b2)
    markup.add(b3, b4)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = (
        "🚀 <b>SSHX মাল্টি-টার্মিনাল ম্যানেজার (Python)</b>\n\n"
        "নিচের বাটন বা কমান্ড ব্যবহার করে টার্মিনাল নিয়ন্ত্রণ করুন:\n\n"
        "• বাটন চেপে ১ বা ২টি টার্মিনাল সরাসরি চালু করুন\n"
        "• <code>/add 3</code> — একসাথে ৩টি টার্মিনাল চালু করতে\n"
        "• <code>/off 1</code> — ১ নম্বর আইডি টার্মিনাল বন্ধ করতে\n"
        "• <code>/tm 10:00AM-1:00PM</code> — নির্দিষ্ট সময়ে অটো-অফ টার্মিনাল তৈরি করতে\n"
        "• <code>/list</code> — সক্রিয় সকল টার্মিনালের তালিকা দেখতে"
    )
    bot.reply_to(message, msg, parse_mode="HTML", reply_markup=main_keyboard())

def create_terminals(count, chat_id, expire_seconds=None, expire_label="আনলিমিটেড"):
    global terminal_counter
    bot.send_message(chat_id, f"⏳ {count}টি টার্মিনাল চালু করা হচ্ছে, অপেক্ষা করুন...")

    created_list = []
    for _ in range(count):
        proc, master_fd, url = spawn_sshx()
        if url:
            with lock:
                t_id = terminal_counter
                terminal_counter += 1
                now = datetime.now(BD_TZ)
                expire_at = (now + timedelta(seconds=expire_seconds)) if expire_seconds else None

                terminals[t_id] = {
                    "proc": proc,
                    "pid": proc.pid,
                    "master_fd": master_fd,
                    "url": url,
                    "start_time": now,
                    "expire_at": expire_at
                }

            if expire_seconds:
                schedule_auto_kill(t_id, expire_seconds, chat_id, expire_label)

            created_list.append((t_id, url))
        else:
            bot.send_message(chat_id, "⚠️ একটি টার্মিনাল শুরু করতে ব্যর্থ হয়েছে!")

    if created_list:
        response = "✅ <b>টার্মিনাল তৈরি সফল হয়েছে:</b>\n\n"
        for tid, url in created_list:
            response += (
                f"🔹 <b>আইডি (ID):</b> <code>{tid}</code>\n"
                f"🔗 <b>লিংক:</b> {url}\n"
                f"⏱️ <b>মেয়াদ:</b> {expire_label}\n"
                f"🛑 বন্ধ করতে কমান্ড দিন: <code>/off {tid}</code>\n\n"
            )
        bot.send_message(chat_id, response, parse_mode="HTML", disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "add_1":
        create_terminals(1, call.message.chat.id)
    elif call.data == "add_2":
        create_terminals(2, call.message.chat.id)
    elif call.data == "list":
        show_list(call.message.chat.id)
    elif call.data == "kill_all":
        kill_all_terminals(call.message.chat.id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['add'])
def handle_add(message):
    try:
        parts = message.text.strip().split()
        count = int(parts[1]) if len(parts) > 1 else 1
        if count > 20:
            bot.reply_to(message, "⚠️ একসাথে সর্বোচ্চ ২০টি টার্মিনাল যুক্ত করা যাবে।")
            return
        create_terminals(count, message.chat.id)
    except ValueError:
        bot.reply_to(message, "ব্যবহারবিধি: <code>/add 2</code>", parse_mode="HTML")

@bot.message_handler(commands=['off'])
def handle_off(message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            bot.reply_to(message, "ব্যবহারবিধি: <code>/off 1</code>", parse_mode="HTML")
            return

        term_id = int(parts[1])
        if kill_terminal(term_id):
            bot.reply_to(message, f"🛑 <b>টার্মিনাল #{term_id} সফলভাবে বন্ধ করা হয়েছে!</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ টার্মিনাল আইডি <code>{term_id}</code> পাওয়া যায়নি।", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "সঠিক আইডি লিখুন। যেমন: <code>/off 1</code>", parse_mode="HTML")

@bot.message_handler(commands=['tm', 'TM'])
def handle_timer(message):
    text = message.text.replace("/tm", "").replace("/TM", "").strip()
    if not text:
        bot.reply_to(message, "ব্যবহারবিধি: <code>/tm 10:00AM-1:00PM</code>", parse_mode="HTML")
        return

    now_bd = datetime.now(BD_TZ)
    delay_seconds = 0
    expire_label = ""

    # সময় ফরম্যাট: 10:00AM-1:00PM
    match = re.match(r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)-(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))", text)
    if match:
        end_str = match.group(2).replace(" ", "").upper()
        try:
            end_time = datetime.strptime(end_str, "%I:%M%p").time()
            target_dt = now_bd.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)
            if target_dt <= now_bd:
                target_dt += timedelta(days=1)

            delay_seconds = int((target_dt - now_bd).total_seconds())
            expire_label = target_dt.strftime("%I:%M %p (BD Time)")
        except Exception:
            bot.reply_to(message, "সময়ের ফরম্যাট ভুল! উদাহরণ: <code>/tm 10:00AM-1:00PM</code>", parse_mode="HTML")
            return
    else:
        bot.reply_to(message, "সঠিক ফরম্যাট দিন। উদাহরণ: <code>/tm 10:00AM-1:00PM</code>", parse_mode="HTML")
        return

    create_terminals(1, message.chat.id, expire_seconds=delay_seconds, expire_label=expire_label)

@bot.message_handler(commands=['list'])
def handle_list(message):
    show_list(message.chat.id)

def show_list(chat_id):
    with lock:
        if not terminals:
            bot.send_message(chat_id, "ℹ️ বর্তমানে কোনো সক্রিয় টার্মিনাল নেই।")
            return

        response = "📋 <b>চলমান টার্মিনালগুলোর তালিকা:</b>\n\n"
        now = datetime.now(BD_TZ)
        for tid, data in terminals.items():
            duration = str(now - data["start_time"]).split('.')[0]
            exp = data["expire_at"].strftime("%I:%M %p") if data["expire_at"] else "আনলিমিটেড"
            response += (
                f"🔹 <b>আইডি:</b> <code>{tid}</code>\n"
                f"🔗 {data['url']}\n"
                f"⏳ চলছে: {duration}\n"
                f"⏱️ অটো-অফ: {exp}\n"
                f"🛑 বন্ধ করতে: <code>/off {tid}</code>\n\n"
            )
        bot.send_message(chat_id, response, parse_mode="HTML", disable_web_page_preview=True)

def kill_all_terminals(chat_id):
    with lock:
        tids = list(terminals.keys())
        for tid in tids:
            kill_terminal(tid)
    bot.send_message(chat_id, "🛑 <b>সকল টার্মিনাল বন্ধ করা হয়েছে!</b>", parse_mode="HTML")

if __name__ == "__main__":
    print("Python Telegram Bot চালু হয়েছে...")
    bot.infinity_polling()
