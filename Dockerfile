FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

RUN apt update -y && apt install --no-install-recommends -y \
    xfce4 tigervnc-standalone-server novnc websockify \
    sudo xterm curl wget git tzdata \
    dbus-x11 x11-utils x11-xserver-utils x11-apps \
    python3 python3-requests python3-pip unzip screen \
    libcurl4 zip ca-certificates jq procps psmisc net-tools \
    && rm -rf /var/lib/apt/lists/*

RUN touch /root/.Xauthority

RUN curl -SsL https://github.com/playit-cloud/playit-agent/releases/download/v0.15.26/playit-linux-amd64 \
    -o /usr/local/bin/playit-cli && \
    chmod +x /usr/local/bin/playit-cli

COPY entrypoint.sh /root/entrypoint.sh
COPY tg_manager.py /root/tg_manager.py
RUN chmod +x /root/entrypoint.sh

WORKDIR /root

EXPOSE 5901 6080 19132/udp 19133/udp

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD screen -ls | grep -q mcpe || exit 1

CMD ["/bin/bash", "/root/entrypoint.sh"]
