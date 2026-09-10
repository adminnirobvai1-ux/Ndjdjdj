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
from telebot.apihelper import ApiTelegramException

# টেলিগ্রাম বট টোকেন
BOT_TOKEN = os.getenv("BOT_TOKEN", "8765791320:AAFCB4Ls3ASrPW_91m6uZhmIexqRrbk9nY0")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# বাংলাদেশ টাইমজোন
BD_TZ = pytz.timezone("Asia/Dhaka")

# টার্মিনাল স্টোরেজ ও লক
terminals = {}
terminal_counter = 1
lock = threading.Lock()

def spawn_sshx():
    """সরাসরি curl কমান্ডের মাধ্যমে ব্যাকগ্রাউন্ডে লাইভ sshx সেশন চালু করে"""
    try:
        master, slave = pty.openpty()
        env = os.environ.copy()
        env["SHELL"] = "/bin/bash"
        env["TERM"] = "xterm-256color"

        # আপনার দেওয়া কমান্ড দিয়ে সাব-প্রসেস রান
        cmd = "curl -sSf https://sshx.io/get | sh -s run"

        proc = subprocess.Popen(
            ["bash", "-c", cmd],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
            preexec_fn=os.setsid,
            env=env
        )
        os.close(slave)
    except Exception as e:
        print(f"Spawn error: {e}")
        return None, None, None

    url = None
    buffer = ""
    start_time = time.time()

    # আউটপুট থেকে আসল হ্যাশ-সহ সম্পূর্ণ sshx লিংক রিড করা (সর্বোচ্চ ২০ সেকেন্ড)
    while time.time() - start_time < 20:
        try:
            chunk = os.read(master, 1024).decode("utf-8", errors="ignore")
            if chunk:
                buffer += chunk

                # সম্পূর্ণ সিক্রেট কি-সহ URL প্যাটার্ন
                match = re.search(r"https://sshx\.io/s/[A-Za-z0-9_-]+#[A-Za-z0-9_-]+", buffer)
                if not match:
                    match = re.search(r"https://sshx\.io/s/[^\s\x1b\r\n]+", buffer)

                if match:
                    url = match.group(0).strip()
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
    """আইডি অনুযায়ী নির্দিষ্ট টার্মিনাল প্রসেস কিল করা"""
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
    """টাইমার শেষ হলে টার্মিনাল স্বয়ংক্রিয়ভাবে বন্ধ করা"""
    def _runner():
        time.sleep(delay_seconds)
        if kill_terminal(term_id):
            try:
                bot.send_message(
                    chat_id,
                    f"⏰ <b>টার্মিনাল #{term_id} বন্ধ করা হয়েছে!</b>\n"
                    f"নির্ধারিত মেয়াদ ({expire_label}) পূর্ণ হয়েছে।",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()

def main_keyboard():
    """বটের প্রধান কন্ট্রোল বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("➕ অ্যাড টার্মিনাল (+১)", callback_data="add_1")
    b2 = types.InlineKeyboardButton("➕ ৫টি অ্যাড করুন (+৫)", callback_data="add_5")
    b3 = types.InlineKeyboardButton("📋 রানিং টার্মিনাল", callback_data="list")
    b4 = types.InlineKeyboardButton("🛑 সব টার্মিনাল বন্ধ", callback_data="kill_all")
    markup.add(b1, b2)
    markup.add(b3, b4)
    return markup

def make_terminal_button(url, term_id):
    """সরাসরি ব্রাউজারে টার্মিনাল খোলার বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_open = types.InlineKeyboardButton("🌐 টার্মিনালে প্রবেশ করুন (Open)", url=url)
    btn_close = types.InlineKeyboardButton(f"🛑 বন্ধ করুন (#{term_id})", callback_data=f"kill_{term_id}")
    markup.add(btn_open, btn_close)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = (
        "🚀 <b>SSHX লাইভ টার্মিনাল কন্ট্রোলার</b>\n\n"
        "প্রতিটি টার্মিনাল ব্যাকগ্রাউন্ডে <code>curl -sSf https://sshx.io/get | sh -s run</code> দিয়ে সরাসরি লাইভ তৈরি হয়।\n\n"
        "<b>কমান্ডসমূহ:</b>\n"
        "• <b>[➕ অ্যাড টার্মিনাল (+১)]</b> - বাটন চেপে ইনস্ট্যান্ট টার্মিনাল খুলুন।\n"
        "• <code>/add 5</code> - একসাথে ৫টি টার্মিনাল তৈরি করতে।\n"
        "• <code>/off 1</code> - ১ নম্বর টার্মিনাল বন্ধ করতে।\n"
        "• <code>/tm 10:00AM-1:00PM</code> - নির্দিষ্ট সময়ে টার্মিনাল অটো-অফ করতে।\n"
        "• <code>/list</code> - চালু থাকা টার্মিনালগুলোর তালিকা দেখতে।"
    )
    bot.reply_to(message, msg, parse_mode="HTML", reply_markup=main_keyboard())

def create_terminals(count, chat_id, expire_seconds=None, expire_label="আনলিমিটেড"):
    global terminal_counter
    with lock:
        current_len = len(terminals)
        if current_len + count > 150:
            bot.send_message(chat_id, f"⚠️ সীমা পূর্ণ! বর্তমানে {current_len}টি চলছে। সর্বোচ্চ ১৫০টি রাখা যাবে।")
            return

    bot.send_message(chat_id, f"⏳ {count}টি টার্মিনাল ব্যাকগ্রাউন্ডে ইনস্টল ও রান হচ্ছে, অপেক্ষা করুন...")

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
                f"⏱️ <b>মেয়াদ:</b> {expire_label}\n"
                f"🛑 বন্ধ করতে কমান্ড: <code>/off {t_id}</code>\n\n"
                f"👇 নিচের বাটনে চাপ দিয়ে সরাসরি টার্মিনাল ব্যবহার করুন:"
            )
            bot.send_message(
                chat_id, 
                res, 
                parse_mode="HTML", 
                reply_markup=make_terminal_button(url, t_id)
            )
        else:
            bot.send_message(chat_id, "⚠️ টার্মিনাল লিঙ্ক জেনারেট হতে ব্যর্থ হয়েছে! পুনরায় চেষ্টা করুন।")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "add_1":
        create_terminals(1, call.message.chat.id)
    elif call.data == "add_5":
        create_terminals(5, call.message.chat.id)
    elif call.data == "list":
        show_list(call.message.chat.id)
    elif call.data == "kill_all":
        with lock:
            all_ids = list(terminals.keys())
        for tid in all_ids:
            kill_terminal(tid)
        bot.send_message(call.message.chat.id, "🛑 সব টার্মিনাল সফলভাবে বন্ধ করা হয়েছে!", reply_markup=main_keyboard())
    elif call.data.startswith("kill_"):
        try:
            tid = int(call.data.replace("kill_", ""))
            if kill_terminal(tid):
                bot.send_message(call.message.chat.id, f"🛑 <b>টার্মিনাল #{tid} বন্ধ করা হয়েছে!</b>", parse_mode="HTML")
            else:
                bot.send_message(call.message.chat.id, f"⚠️ টার্মিনাল #{tid} ইতোমধ্যে বন্ধ রয়েছে।")
        except Exception:
            pass

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

@bot.message_handler(commands=['add'])
def handle_add(message):
    try:
        parts = message.text.strip().split()
        count = int(parts[1]) if len(parts) > 1 else 1
        if count > 100:
            bot.reply_to(message, "⚠️ একসাথে সর্বোচ্চ ১০০টি টার্মিনাল যোগ করা যাবে।")
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
            bot.reply_to(message, f"🛑 <b>টার্মিনাল #{term_id} বন্ধ করা হয়েছে!</b>", parse_mode="HTML")
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
            bot.send_message(chat_id, "ℹ️ বর্তমানে কোনো সক্রিয় টার্মিনাল চালু নেই।", reply_markup=main_keyboard())
            return

        items = list(terminals.items())
        total = len(items)

    msg = f"📋 <b>চলমান টার্মিনালসমূহ (মোট {total}টি):</b>\n\n"
    for tid, data in items:
        exp = data["expire_at"].strftime("%I:%M %p") if data["expire_at"] else "আনলিমিটেড"
        entry = (
            f"🔹 <b>আইডি:</b> <code>{tid}</code> | ⏱️ {exp}\n"
            f"🔗 <a href=\"{data['url']}\">টার্মিনাল লিংক</a>\n"
            f"🛑 বন্ধ: <code>/off {tid}</code>\n\n"
        )
        if len(msg) + len(entry) > 3800:
            bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True)
            msg = ""
        msg += entry

    if msg:
        bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard())

# অটো-রিকানেক্টিং মেইন লুপ
if __name__ == "__main__":
    print("Telegram Terminal Bot চালু হচ্ছে...")
    time.sleep(2)
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10, logger_level=None)
        except ApiTelegramException as e:
            if e.error_code == 409:
                print("অন্য ইনস্ট্যান্স বন্ধের জন্য ১০ সেকেন্ড অপেক্ষা...")
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception as e:
            time.sleep(5)
