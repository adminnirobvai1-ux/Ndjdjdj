# Base image
FROM ubuntu:20.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# প্রয়োজনীয় প্যাকেজ ও টুলস ইনস্টল
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    shellinabox \
    git \
    python3 \
    python3-pip \
    curl \
    nano \
    sudo \
    bash && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# পোর্ট এক্সপোজ
EXPOSE 4200

# সরাসরি রুট শেল চালু করার কমান্ড (লগইন বা সেশন ক্র্যাশ হবে না)
CMD ["sh", "-c", "/usr/bin/shellinaboxd -t -p ${PORT:-4200} --no-beep -s /:root:root:/root:/bin/bash"]
