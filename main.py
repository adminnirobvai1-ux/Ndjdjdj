import os
import pty
import re
import select
import shutil
import subprocess
import time
import requests

BOT_TOKEN = "8995269165:AAGzs3OBZsa9-f-OETfFjFQN9k0M4QjbZCU"


def get_chat_id():
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
  try:
    res = requests.get(url, timeout=10).json()
    if res.get("result"):
      for update in reversed(res["result"]):
        if "message" in update and "chat" in update["message"]:
          return update["message"]["chat"]["id"]
  except Exception as e:
    print(f"Chat ID আনতে সমস্যা: {e}")
  return None


def send_telegram_message(chat_id, text):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {"chat_id": chat_id, "text": text}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"মেসেজ পাঠাতে সমস্যা: {e}")


def ensure_sshx():
  """sshx ইনস্টল না থাকলে স্বয়ংক্রিয়ভাবে ইনস্টল করে নেয়"""
  if shutil.which("sshx") is None:
    os.system("curl -sSf https://sshx.io/get | sh")
    home_bin = os.path.expanduser("~/.local/bin")
    if home_bin not in os.environ["PATH"]:
      os.environ["PATH"] += os.pathsep + home_bin


def run_sshx_and_notify():
  ensure_sshx()
  sshx_bin = shutil.which("sshx") or "sshx"

  chat_id = get_chat_id()
  while not chat_id:
    print("টেলিগ্রাম চ্যাট আইডি পাওয়া যায়নি! বটে /start দিন...")
    time.sleep(5)
    chat_id = get_chat_id()

  send_telegram_message(chat_id, "🚀 sshx চালু করা হচ্ছে...")

  # sshx-এর জন্য লিনাক্স সিউডো-টার্মিনাল তৈরি
  master, slave = pty.openpty()

  try:
    process = subprocess.Popen(
        [sshx_bin],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        preexec_fn=os.setsid,
    )
    os.close(slave)

    link_pattern = re.compile(r"https://sshx\.io/s/[^\s\x1b\x00-\x1f]+")
    link_sent = False
    output_buffer = ""

    while process.poll() is None:
      r, _, _ = select.select([master], [], [], 0.5)
      if r:
        try:
          data = os.read(master, 1024).decode("utf-8", errors="ignore")
          if not data:
            break
          output_buffer += data

          if not link_sent:
            match = link_pattern.search(output_buffer)
            if match:
              link = match.group(0)
              send_telegram_message(
                  chat_id, f"✅ আপনার sshx টার্মিনাল লিংক:\n{link}"
              )
              link_sent = True
        except OSError:
          break

    process.wait()
    send_telegram_message(chat_id, "⚠️ sshx সেশন বন্ধ হয়ে গেছে।")

  except Exception as e:
    send_telegram_message(chat_id, f"❌ ত্রুটি ঘটেছে: {e}")
  finally:
    try:
      os.close(master)
    except Exception:
      pass


if __name__ == "__main__":
  run_sshx_and_notify()
