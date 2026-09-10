FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Dhaka

# curl, bash, procps ও পাইথন ইনস্টল
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    bsdutils \
    procps \
    python3 \
    python3-pip \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# sshx সরাসরি ডকারের ভেতরে ইনস্টল ও সিস্টেম পাথে সেট
RUN curl -sSf https://sshx.io/get | sh && \
    cp /root/.local/bin/sshx /usr/local/bin/sshx 2>/dev/null || true

ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /app

# প্রয়োজনীয় পাইথন লাইব্রেরি ইনস্টল
RUN pip3 install --no-cache-dir pyTelegramBotAPI pytz

# পাইথন কোড কপি
COPY main.py /app/main.py

# পাইথন বট রান করা (unbuffered মোডে যাতে সরাসরি লগ দেখা যায়)
CMD ["python3", "-u", "/app/main.py"]
