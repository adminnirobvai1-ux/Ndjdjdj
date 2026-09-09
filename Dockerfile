q# syntax=docker/dockerfile:1
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Dhaka

# প্রয়োজনীয় লিনাক্স টুলস, PTY সাপোর্ট ও jq ইনস্টল (কোনো পাইথন নেই)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    bsdutils \
    procps \
    jq \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# sshx সরাসরি ইনস্টল ও পাথ কনফিগার
RUN curl -sSf https://sshx.io/get | sh && \
    cp /root/.local/bin/sshx /usr/local/bin/sshx 2>/dev/null || true

ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /root

# ডকারফাইলের ভেতরেই সম্পূর্ণ টেলিগ্রাম বট ও টার্মিনাল কন্ট্রোলার স্ক্রিপ্ট তৈরি
RUN cat << 'EOF' > /root/entrypoint.sh
#!/usr/bin/env bash

export TZ="Asia/Dhaka"
BOT_TOKEN="${BOT_TOKEN:-8995269165:AAGzs3OBZsa9-f-OETfFjFQN9k0M4QjbZCU}"
API="https://api.telegram.org/bot${BOT_TOKEN}"
DATA_DIR="/tmp/terminals"
mkdir -p "$DATA_DIR"

OFFSET=0

# টেলিগ্রাম মেসেজ পাঠানোর ফাংশন
send_msg() {
    local chat_id="$1"
    local text="$2"
    local markup="$3"

    if [ -n "$markup" ]; then
        curl -s -X POST "$API/sendMessage" \
            --data-urlencode "chat_id=$chat_id" \
            --data-urlencode "text=$text" \
            -d "parse_mode=HTML" \
            --data-urlencode "reply_markup=$markup" > /dev/null
    else
        curl -s -X POST "$API/sendMessage" \
            --data-urlencode "chat_id=$chat_id" \
            --data-urlencode "text=$text" \
            -d "parse_mode=HTML" \
            -d "disable_web_page_preview=true" > /dev/null
    fi
}

# ইনলাইন বাটন
get_keyboard() {
    cat << 'JSON'
{"inline_keyboard":[[{"text":"➕ ১টি টার্মিনাল","callback_data":"add_1"},{"text":"➕ ২টি টার্মিনাল","callback_data":"add_2"}],[{"text":"📋 রানিং লিস্ট","callback_data":"list"},{"text":"❌ সব বন্ধ","callback_data":"kill_all"}]]}
JSON
}

# নির্দিষ্ট আইডি দিয়ে টার্মিনাল কিল করা
kill_term() {
    local id="$1"
    local pid_file="$DATA_DIR/${id}.pid"

    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        pkill -P "$pid" 2>/dev/null || true
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$DATA_DIR/${id}".*
        return 0
    fi
    return 1
}

# টার্মিনাল তৈরি ও লিংক রিটার্ন করার ফাংশন
create_terminal() {
    local chat_id="$1"
    local count="$2"
    local delay_sec="$3"
    local expire_label="$4"

    [ -z "$expire_label" ] && expire_label="আনলিমিটেড"

    send_msg "$chat_id" "⏳ <b>$count</b> টি টার্মিনাল হোস্ট হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন..."

    for ((i=1; i<=count; i++)); do
        local id_file="$DATA_DIR/counter"
        local id=1
        if [ -f "$id_file" ]; then
            id=$(($(cat "$id_file") + 1))
        fi
        echo "$id" > "$id_file"

        local log_file="$DATA_DIR/${id}.log"
        local pid_file="$DATA_DIR/${id}.pid"
        local url_file="$DATA_DIR/${id}.url"
        local exp_file="$DATA_DIR/${id}.exp"

        # ভার্চুয়াল PTY দিয়ে ব্যাকগ্রাউন্ডে sshx চালু
        script -q -c "sshx" "$log_file" > /dev/null 2>&1 &
        local proc_pid=$!
        echo "$proc_pid" > "$pid_file"
        echo "$expire_label" > "$exp_file"

        # আউটপুট লগ থেকে sshx লিংক পড়া
        local term_url=""
        for attempt in {1..30}; do
            term_url=$(grep -oE 'https://sshx\.io/s/[a-zA-Z0-9_-]+' "$log_file" 2>/dev/null | head -n 1)
            [ -n "$term_url" ] && break
            sleep 0.5
        done

        if [ -n "$term_url" ]; then
            echo "$term_url" > "$url_file"
            local msg="✅ <b>টার্মিনাল তৈরি সফল হয়েছে!</b>\n\n🔹 <b>আইডি (ID):</b> <code>${id}</code>\n🔗 <b>লিংক:</b> ${term_url}\n⏱️ <b>মেয়াদ:</b> ${expire_label}\n🛑 বন্ধ করতে লিখুন: <code>/off ${id}</code>"
            send_msg "$chat_id" "$msg"

            # টাইমার শেষ হলে স্বয়ংক্রিয়ভাবে বন্ধ করা
            if [ -n "$delay_sec" ] && [ "$delay_sec" -gt 0 ]; then
                (
                    sleep "$delay_sec"
                    if [ -f "$pid_file" ]; then
                        kill_term "$id"
                        send_msg "$chat_id" "⏰ <b>টার্মিনাল #${id} স্বয়ংক্রিয়ভাবে বন্ধ হয়ে গেছে!</b>\nনির্ধারিত মেয়াদ ($expire_label) পূর্ণ হয়েছে।"
                    fi
                ) &
            fi
        else
            kill_term "$id"
            send_msg "$chat_id" "⚠️ টার্মিনাল #${id} তৈরি করতে ব্যর্থ হয়েছে!"
        fi
    done
}

# সব চলমান টার্মিনাল দেখার তালিকা
show_list() {
    local chat_id="$1"
    local found=0
    local msg="📋 <b>চলমান টার্মিনালগুলোর তালিকা:</b>\n\n"

    for url_file in "$DATA_DIR"/*.url; do
        [ -e "$url_file" ] || continue
        found=1
        local base
        base=$(basename "$url_file" .url)
        local url
        url=$(cat "$url_file")
        local exp="আনলিমিটেড"
        [ -f "$DATA_DIR/${base}.exp" ] && exp=$(cat "$DATA_DIR/${base}.exp")

        msg="${msg}🔹 <b>আইডি:</b> <code>${base}</code>\n🔗 ${url}\n⏱️ মেয়াদ: ${exp}\n🛑 বন্ধ করতে: <code>/off ${base}</code>\n\n"
    done

    if [ "$found" -eq 0 ]; then
        send_msg "$chat_id" "ℹ️ বর্তমানে কোনো সক্রিয় টার্মিনাল নেই।"
    else
        send_msg "$chat_id" "$msg"
    fi
}

echo "=== Telegram Bash Controller চালু হয়েছে ==="

# টেলিগ্রাম API পোলিং লুপ
while true; do
    UPDATES=$(curl -s --max-time 25 "$API/getUpdates?offset=$OFFSET&timeout=20")
    
    OK=$(echo "$UPDATES" | jq -r '.ok' 2>/dev/null)
    if [ "$OK" != "true" ]; then
        sleep 2
        continue
    fi

    COUNT=$(echo "$UPDATES" | jq '.result | length')
    if [ "$COUNT" -gt 0 ]; then
        for ((i=0; i<COUNT; i++)); do
            ITEM=$(echo "$UPDATES" | jq -c ".result[$i]")
            UPDATE_ID=$(echo "$ITEM" | jq -r '.update_id')
            OFFSET=$((UPDATE_ID + 1))

            # বাটন ক্লিকের রেসপন্স হ্যান্ডলার
            CALLBACK=$(echo "$ITEM" | jq -r '.callback_query // empty')
            if [ -n "$CALLBACK" ]; then
                CB_ID=$(echo "$ITEM" | jq -r '.callback_query.id')
                CB_DATA=$(echo "$ITEM" | jq -r '.callback_query.data')
                CHAT_ID=$(echo "$ITEM" | jq -r '.callback_query.message.chat.id')

                curl -s -X POST "$API/answerCallbackQuery" -d "callback_query_id=$CB_ID" > /dev/null

                case "$CB_DATA" in
                    add_1)
                        create_terminal "$CHAT_ID" 1
                        ;;
                    add_2)
                        create_terminal "$CHAT_ID" 2
                        ;;
                    list)
                        show_list "$CHAT_ID"
                        ;;
                    kill_all)
                        for pf in "$DATA_DIR"/*.pid; do
                            [ -e "$pf" ] || continue
                            tid=$(basename "$pf" .pid)
                            kill_term "$tid"
                        done
                        send_msg "$CHAT_ID" "🛑 সব টার্মিনাল বন্ধ করা হয়েছে!"
                        ;;
                esac
                continue
            fi

            # টেক্সট কমান্ড হ্যান্ডলার
            MSG=$(echo "$ITEM" | jq -r '.message.text // empty')
            CHAT_ID=$(echo "$ITEM" | jq -r '.message.chat.id // empty')
            [ -z "$MSG" ] && continue

            # ১. /start কমান্ড
            if [[ "$MSG" == "/start"* ]]; then
                WELCOME="🚀 <b>SSHX মাল্টি-টার্মিনাল প্যানেল</b>\n\nনিচের বাটন চাপুন অথবা সরাসরি কমান্ড পাঠান।\n\n<b>কমান্ডসমূহ:</b>\n• <code>/add 2</code> - ২টি টার্মিনাল চালু করতে\n• <code>/off 1</code> - ১ নম্বর আইডি টার্মিনাল বন্ধ করতে\n• <code>/tm 10:00AM-1:00PM</code> - নির্দিষ্ট সময়ে টার্মিনাল অটো-অফ করতে\n• <code>/list</code> - রানিং টার্মিনালের তালিকা দেখতে"
                send_msg "$CHAT_ID" "$WELCOME" "$(get_keyboard)"

            # ২. /add কমান্ড
            elif [[ "$MSG" == "/add"* ]]; then
                NUM=$(echo "$MSG" | awk '{print $2}')
                [[ ! "$NUM" =~ ^[0-9]+$ ]] && NUM=1
                [ "$NUM" -gt 20 ] && NUM=20
                create_terminal "$CHAT_ID" "$NUM"

            # ৩. /off কমান্ড
            elif [[ "$MSG" == "/off"* ]]; then
                TARGET_ID=$(echo "$MSG" | awk '{print $2}')
                if [ -n "$TARGET_ID" ]; then
                    if kill_term "$TARGET_ID"; then
                        send_msg "$CHAT_ID" "🛑 <b>টার্মিনাল #${TARGET_ID} সফলভাবে বন্ধ করা হয়েছে!</b>"
                    else
                        send_msg "$CHAT_ID" "❌ টার্মিনাল আইডি <code>${TARGET_ID}</code> খুঁজে পাওয়া যায়নি।"
                    fi
                else
                    send_msg "$CHAT_ID" "ব্যবহারবিধি: <code>/off 1</code> (আইডি নম্বর উল্লেখ করুন)"
                fi

            # ৪. /tm বা /TM টাইমার কমান্ড
            elif [[ "$MSG" =~ ^/(tm|TM) ]]; then
                TIME_RANGE=$(echo "$MSG" | sed -E 's/^\/(tm|TM)[[:space:]]*//I')
                
                END_TIME=$(echo "$TIME_RANGE" | awk -F'-' '{print $2}' | xargs)
                [ -z "$END_TIME" ] && END_TIME="$TIME_RANGE"

                TARGET_EPOCH=$(date -d "$END_TIME" +%s 2>/dev/null)
                NOW_EPOCH=$(date +%s)

                if [ -n "$TARGET_EPOCH" ]; then
                    if [ "$TARGET_EPOCH" -le "$NOW_EPOCH" ]; then
                        TARGET_EPOCH=$((TARGET_EPOCH + 86400))
                    fi
                    DIFF_SEC=$((TARGET_EPOCH - NOW_EPOCH))
                    LABEL=$(date -d "@$TARGET_EPOCH" "+%I:%M %p (BD Time)")
                    create_terminal "$CHAT_ID" 1 "$DIFF_SEC" "$LABEL"
                else
                    send_msg "$CHAT_ID" "⚠️ সময় ফরম্যাট সঠিক নয়!\nউদাহরণ: <code>/tm 10:00AM-1:00PM</code>"
                fi

            # ৫. /list কমান্ড
            elif [[ "$MSG" == "/list"* ]]; then
                show_list "$CHAT_ID"
            fi
        done
    fi
    sleep 1
done
EOF

RUN chmod +x /root/entrypoint.sh

# স্বয়ংক্রিয়ভাবে বট স্ক্রিপ্ট রান করা
CMD ["/bin/bash", "/root/entrypoint.sh"]
