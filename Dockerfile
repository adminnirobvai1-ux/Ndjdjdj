FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Dhaka
ENV SHELL=/bin/bash
ENV TERM=xterm-256color

# সিস্টেম প্যাকেজ ও পাইথন ইনস্টলেশন
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

# পাইথন লাইব্রেরি ইনস্টল
RUN pip3 install --no-cache-dir pyTelegramBotAPI pytz

WORKDIR /app

# কোড কপি
COPY main.py /app/main.py

# পাইথন বট রান (Unbuffered mode)
CMD ["python3", "-u", "/app/main.py"]
