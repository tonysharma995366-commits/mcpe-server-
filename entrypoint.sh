#!/bin/bash
# ============================================================
#  MCPE MASTER SERVER — ULTRA FAST ENTRYPOINT
# ============================================================

set -e

# ---------- VNC / noVNC ----------
vncserver -localhost no -SecurityTypes None -geometry 1024x768 \
    --I-KNOW-THIS-IS-INSECURE 2>/dev/null || true

if [ ! -f /root/self.pem ]; then
    openssl req -new -subj "/C=JP" -x509 -days 365 -nodes \
        -out /root/self.pem -keyout /root/self.pem 2>/dev/null
fi

websockify -D --web=/usr/share/novnc/ --cert=/root/self.pem 6080 localhost:5901 2>/dev/null || true

# ---------- Config ----------
BOT_TOKEN="8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID="6955911349"
SERVER_DIR="/root/mcpe-server"

mkdir -p "$SERVER_DIR"
cd "$SERVER_DIR"

send_tg() {
    curl -s --max-time 5 -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "parse_mode=HTML" \
        --data-urlencode "text=$1" > /dev/null 2>&1
}

# ============================================================
#  KILL ANY EXISTING PROCESSES (Prevent duplicates)
# ============================================================
pkill -9 -f tg_manager.py 2>/dev/null || true
pkill -9 -f bedrock_server 2>/dev/null || true
pkill -9 -f playit-cli 2>/dev/null || true
sleep 2
screen -wipe 2>/dev/null || true

# Clear old Telegram pending updates
curl -s --max-time 5 "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=-1" > /dev/null 2>&1 || true

# ============================================================
#  PLAYIT TUNNEL + CONFIRMATION
# ============================================================
(
    rm -f /tmp/playit_output.log
    /usr/local/bin/playit-cli > /tmp/playit_output.log 2>&1 &
    PLAYIT_PID=$!

    CLAIM_URL=""
    for i in {1..30}; do
        if grep -q "playit.gg/claim/" /tmp/playit_output.log 2>/dev/null; then
            CLAIM_URL=$(grep -o 'https://playit.gg/claim/[a-zA-Z0-9]*' /tmp/playit_output.log | head -n 1)
            break
        fi
        sleep 1
    done

    if [ -n "$CLAIM_URL" ]; then
        send_tg "<b>🎮 Server Ready!</b>

🔗 Claim Playit: $CLAIM_URL

Port: 19132 (UDP)

Done likhkar bhejein."
    fi

    # Fast confirmation loop (1 sec interval)
    LAST_UPDATE_ID=$(curl -s --max-time 5 "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=-1" \
        | grep -o '"update_id":[0-9]*' | tail -n 1 | cut -d: -f2)
    [ -z "$LAST_UPDATE_ID" ] && LAST_UPDATE_ID=0

    CONFIRMED=false
    WAIT_COUNT=0
    while [ "$CONFIRMED" = false ] && [ $WAIT_COUNT -lt 600 ]; do
        UPDATES=$(curl -s --max-time 3 "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=$((LAST_UPDATE_ID + 1))")
        if echo "$UPDATES" | grep -q '"text"'; then
            MSG=$(echo "$UPDATES" | grep -o '"text":"[^"]*"' | tail -n 1 | cut -d'"' -f4 | tr '[:upper:]' '[:lower:]')
            NEW_ID=$(echo "$UPDATES" | grep -o '"update_id":[0-9]*' | tail -n 1 | cut -d: -f2)
            LAST_UPDATE_ID=$NEW_ID
            if [[ "$MSG" =~ ^(done|ok|yes|ready|ho\ gaya|ban\ gaya)$ ]]; then
                CONFIRMED=true
                send_tg "✅ Launching server..."
                break
            fi
        fi
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done

    kill $PLAYIT_PID 2>/dev/null || true
    sleep 2

    # ---------- Download Bedrock ----------
    if [ ! -f "bedrock_server" ]; then
        send_tg "📥 Downloading Bedrock..."
        for V in 1.21.51.02 1.21.50.07 1.21.44.01 1.21.31.04 1.21.30.03; do
            URL="https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-${V}.zip"
            if wget --spider --user-agent="Mozilla/5.0" --timeout=10 "$URL" 2>&1 | grep -q "200 OK"; then
                wget --user-agent="Mozilla/5.0" --timeout=60 -q -O bedrock-server.zip "$URL"
                echo "$V" > version.txt
                break
            fi
        done
        unzip -o -q bedrock-server.zip 2>/dev/null || true
        chmod +x bedrock_server 2>/dev/null || true
    fi

    # ---------- Server Properties ----------
    cat > server.properties << 'EOF'
server-name=Master MCPE Server
gamemode=survival
difficulty=normal
allow-cheats=false
max-players=20
online-mode=true
allow-list=false
white-list=false
server-port=19132
server-portv6=19133
enable-lan-visibility=true
view-distance=10
tick-distance=4
player-idle-timeout=30
max-threads=8
level-name=Bedrock level
default-player-permission-level=member
texturepack-required=true
content-log-file-enabled=true
compression-threshold=1
compression-algorithm=zlib
player-force-server-packs=true
correct-player-movement=true
server-authoritative-movement=server-auth
server-authoritative-block-breaking=true
emit-server-telemetry=false
EOF

    # ---------- Start Services ----------
    screen -dmS playit-tunnel /usr/local/bin/playit-cli
    sleep 2
    screen -dmS tg-bot python3 /root/tg_manager.py
    sleep 2

    send_tg "🟢 <b>Server Online!</b>

/help bhejo commands ke liye."
) &

tail -f /dev/null
