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

# আপনার দেওয়া নতুন টেলিগ্রাম বট টোকেন
BOT_TOKEN = os.getenv("BOT_TOKEN", "8765791320:AAFCB4Ls3ASrPW_91m6uZhmIexqRrbk9nY0")
bot = telebot.TeleBot(BOT_TOKEN)

# বাংলাদেশ টাইমজোন
BD_TZ = pytz.timezone("Asia/Dhaka")

# টার্মিনাল ডেটাবেস
terminals = {}
terminal_counter = 1
lock = threading.Lock()

def spawn_sshx():
    """ব্যাকগ্রাউন্ডে ভার্চুয়াল PTY দিয়ে sshx চালু ও লাইভ লিংক রিটার্ন করে"""
    try:
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
    except Exception as e:
        print(f"Spawn error: {e}")
        return None, None, None

    url = None
    buffer = ""
    start_time = time.time()

    # আউটপুট থেকে sshx লিংক বের করা
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
    """আইডি অনুযায়ী নির্দিষ্ট টার্মিনাল বন্ধ করা"""
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
    """টাইম শেষ হলে টার্মিনাল স্বয়ংক্রিয়ভাবে বন্ধ করা"""
    def _runner():
        time.sleep(delay_seconds)
        if kill_terminal(term_id):
            try:
                bot.send_message(
                    chat_id,
                    f"⏰ <b>টার্মিনাল #{term_id} বন্ধ হয়েছে!</b>\n"
                    f"নির্ধারিত সময় ({expire_label}) পার হওয়ায় এটি অফ হয়ে গেছে।",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()

def main_keyboard():
    """বটের ইনলাইন বাটন"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("➕ অ্যাড টার্মিনাল (+১)", callback_data="add_1")
    b2 = types.InlineKeyboardButton("➕ ৫টি অ্যাড করুন (+৫)", callback_data="add_5")
    b3 = types.InlineKeyboardButton("📋 রানিং টার্মিনাল", callback_data="list")
    b4 = types.InlineKeyboardButton("🛑 সব টার্মিনাল বন্ধ", callback_data="kill_all")
    markup.add(b1, b2)
    markup.add(b3, b4)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = (
        "🚀 <b>SSHX মাল্টি-টার্মিনাল প্যানেল</b>\n\n"
        "প্রতিবার <b>[➕ অ্যাড টার্মিনাল (+১)]</b> বাটনে চাপ দিলে ১টি করে নতুন টার্মিনাল তৈরি হবে। এখানে ১০০টিরও বেশি টার্মিনাল একসাথে চালানো যাবে।\n\n"
        "<b>কমান্ডসমূহ:</b>\n"
        "• <code>/add 5</code> - একসাথে ৫টি টার্মিনাল বানাতে\n"
        "• <code>/off 1</code> - ১ নম্বর আইডি টার্মিনাল বন্ধ করতে\n"
        "• <code>/tm 10:00AM-1:00PM</code> - নির্দিষ্ট সময়ে টার্মিনাল অটো-অফ করতে\n"
        "• <code>/list</code> - চালু থাকা সব টার্মিনাল দেখতে"
    )
    bot.reply_to(message, msg, parse_mode="HTML", reply_markup=main_keyboard())

def create_terminals(count, chat_id, expire_seconds=None, expire_label="আনলিমিটেড"):
    global terminal_counter
    with lock:
        current_len = len(terminals)
        if current_len + count > 150:
            bot.send_message(chat_id, f"⚠️ সীমা পূর্ণ! বর্তমানে {current_len}টি চলছে। সর্বোচ্চ ১৫০টি রাখা যাবে।")
            return

    bot.send_message(chat_id, f"⏳ {count}টি টার্মিনাল তৈরি হচ্ছে, দয়া করে কয়েক সেকেন্ড অপেক্ষা করুন...")

    success_count = 0
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

            success_count += 1
            res = (
                f"✅ <b>টার্মিনাল তৈরি সফল!</b>\n\n"
                f"🔹 <b>আইডি (ID):</b> <code>{t_id}</code>\n"
                f"🔗 <b>লিংক:</b> {url}\n"
                f"⏱️ <b>মেয়াদ:</b> {expire_label}\n"
                f"🛑 বন্ধ করতে লিখুন: <code>/off {t_id}</code>"
            )
            bot.send_message(chat_id, res, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard())
        else:
            bot.send_message(chat_id, "⚠️ টার্মিনাল কানেক্ট করতে সমস্যা হয়েছে!")

    if success_count > 1:
        bot.send_message(chat_id, f"🎉 মোট {success_count}টি টার্মিনাল সফলভাবে তৈরি হয়েছে!", reply_markup=main_keyboard())

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
        bot.send_message(call.message.chat.id, "🛑 সব টার্মিনাল বন্ধ করা হয়েছে!", reply_markup=main_keyboard())
    bot.answer_callback_query(call.id)

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
            bot.reply_to(message, "ব্যবহারবিধি: <code>/off 1</code> (আইডি নম্বর দিন)", parse_mode="HTML")
            return

        term_id = int(parts[1])
        if kill_terminal(term_id):
            bot.reply_to(message, f"🛑 <b>টার্মিনাল #{term_id} সফলভাবে বন্ধ করা হয়েছে!</b>", parse_mode="HTML", reply_markup=main_keyboard())
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
            f"🔗 {data['url']}\n"
            f"🛑 বন্ধ: <code>/off {tid}</code>\n\n"
        )
        if len(msg) + len(entry) > 3800:
            bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True)
            msg = ""
        msg += entry

    if msg:
        bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard())

if __name__ == "__main__":
    print("Telegram Terminal Bot চালু হয়েছে...")
    bot.infinity_polling()
