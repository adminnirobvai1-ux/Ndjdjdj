# Base image
FROM ubuntu:20.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# প্রয়োজনীয় প্যাকেজ ইনস্টল
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    shellinabox \
    git \
    python3 \
    python3-pip \
    curl \
    sudo \
    bash && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# নতুন ইউজার তৈরি ও sudo পারমিশন দেওয়া (root ব্লকিং এড়াতে)
RUN useradd -m -s /bin/bash admin && \
    echo 'admin:admin123' | chpasswd && \
    adduser admin sudo && \
    echo 'admin ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# পোর্ট ডিক্লেয়ারেশন
EXPOSE 4200

# Railway-র $PORT ভ্যারিয়েবল সাপোর্ট এবং SSL ছাড়া সরাসরি রান
CMD ["sh", "-c", "/usr/bin/shellinaboxd -t -p ${PORT:-4200} --no-beep -s /:LOGIN"]
