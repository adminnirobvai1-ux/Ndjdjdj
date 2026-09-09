FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# প্রয়োজনীয় প্যাকেজ ও PTY সাপোর্ট ইনস্টল
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    bsdutils \
    procps \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# sshx সরাসরি ইনস্টল ও পাথ সেট
RUN curl -sSf https://sshx.io/get | sh && \
    cp /root/.local/bin/sshx /usr/local/bin/sshx 2>/dev/null || true

ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /root

# 24/7 অটো-রিস্টার্ট লুপ (script কমান্ড দিয়ে ভার্চুয়াল টার্মিনাল প্রদান)
CMD ["bash", "-c", "while true; do echo '=== sshx চালু হচ্ছে ==='; script -q -c 'sshx' /dev/null; echo '=== সেশন ড্রপ করেছে, ৫ সেকেন্ড পর রিস্টার্ট হচ্ছে ==='; sleep 5; done"]
