#!/bin/bash
# ============================================================
#  MCPE ADVANCED SERVER - ENTRYPOINT
#  VNC + noVNC + Playit + Auto Setup
# ============================================================

set -e

# ---------- VNC / noVNC Setup ----------
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
BEDROCK_VERSION="1.26.45.1"
BEDROCK_URL="https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-${BEDROCK_VERSION}.zip"

mkdir -p "$SERVER_DIR"
cd "$SERVER_DIR"

# ---------- Telegram Helper ----------
send_tg() {
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "parse_mode=HTML" \
        --data-urlencode "text=$1" > /dev/null 2>&1
}

# ============================================================
#  BACKGROUND TASK: Playit Tunnel + Telegram Confirmation
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

🔗 <b>Claim Playit Tunnel:</b>
$CLAIM_URL

📡 <b>Protocol:</b> Minecraft Bedrock (UDP)
🔌 <b>Port:</b> 19132

✅ Claim karne ke baad bot ko <code>done</code> likhkar bhejein."
    else
        send_tg "⏳ Playit tunnel active. Server launch pending..."
    fi

    # Wait for user confirmation
    LAST_UPDATE_ID=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" \
        | grep -o '"update_id":[0-9]*' | tail -n 1 | cut -d: -f2)
    [ -z "$LAST_UPDATE_ID" ] && LAST_UPDATE_ID=0

    CONFIRMED=false
    WAIT_COUNT=0
    while [ "$CONFIRMED" = false ] && [ $WAIT_COUNT -lt 300 ]; do
        UPDATES=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=$((LAST_UPDATE_ID + 1))")
        if echo "$UPDATES" | grep -q '"text"'; then
            MSG=$(echo "$UPDATES" | grep -o '"text":"[^"]*"' | tail -n 1 | cut -d'"' -f4 | tr '[:upper:]' '[:lower:]')
            NEW_ID=$(echo "$UPDATES" | grep -o '"update_id":[0-9]*' | tail -n 1 | cut -d: -f2)
            LAST_UPDATE_ID=$NEW_ID

            if [[ "$MSG" =~ ^(done|ok|yes|ready|ho\ gaya|ban\ gaya)$ ]]; then
                CONFIRMED=true
                send_tg "✅ Confirmation received! Launching Bedrock ${BEDROCK_VERSION}..."
                break
            fi
        fi
        sleep 3
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done

    kill $PLAYIT_PID 2>/dev/null || true
    sleep 2

    # ---------- Download & Setup Bedrock Server ----------
    if [ ! -f "bedrock-server.zip" ]; then
        send_tg "📥 Downloading Bedrock Server ${BEDROCK_VERSION}..."
        wget --user-agent="Mozilla/5.0" -q -O bedrock-server.zip "$BEDROCK_URL" || {
            send_tg "❌ Download failed! Retry manually."
            exit 1
        }
    fi

    unzip -o -q bedrock-server.zip
    chmod +x bedrock_server

    # ---------- Server Properties (Advanced Security) ----------
    cat > server.properties << 'EOF'
server-name=Advanced MCPE Server
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
level-seed=
default-player-permission-level=member
texturepack-required=true
content-log-file-enabled=true
compression-threshold=1
compression-algorithm=zlib
player-force-server-packs=true
correct-player-movement=true
server-authoritative-movement=server-auth
player-position-acceptance-threshold=0.5
player-movement-action-direction-threshold=0.85
server-authoritative-block-breaking=true
server-authoritative-block-breaking-pick-range-scalar=1.5
disable-custom-skins=false
emit-server-telemetry=false
EOF

    # ---------- Start Services ----------
    screen -dmS playit-tunnel /usr/local/bin/playit-cli
    sleep 3
    screen -dmS tg-bot python3 /root/tg_manager.py

    send_tg "🟢 <b>Server Online!</b>

Minecraft server aur Telegram bot dono active hain.
📖 Sabhi commands dekhne ke liye: <code>/help</code>
🛒 Merchant system ke liye: <code>/npc</code>"
) &

# Keep container alive
tail -f /dev/null
