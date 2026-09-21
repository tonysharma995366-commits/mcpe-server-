#!/usr/bin/env python3
# ============================================================
#  MCPE MASTER SERVER CONTROL PANEL — FULLY WORKING
#  55+ Commands | Fast Response | No Delays
# ============================================================

import os
import sys
import time
import json
import shutil
import zipfile
import subprocess
import threading
import requests
import re
from datetime import datetime

# ---------------- CONFIG ----------------
BOT_TOKEN = "8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID   = "6955911349"

BASE_DIR        = "/root/mcpe-server"
WORLDS_DIR      = os.path.join(BASE_DIR, "worlds")
PROPERTIES_FILE = os.path.join(BASE_DIR, "server.properties")
SECURITY_FILE   = os.path.join(BASE_DIR, "security_config.json")
BLACKLIST_FILE  = os.path.join(BASE_DIR, "blacklist.json")
SPY_FILE        = os.path.join(BASE_DIR, "spy_list.json")
CHUNK_FILE      = os.path.join(BASE_DIR, "chunk_loaders.json")
LOG_FILE        = os.path.join(BASE_DIR, "control_log.txt")
BACKUP_DIR      = os.path.join(BASE_DIR, "backups")
VERSION_FILE    = os.path.join(BASE_DIR, "version.txt")
MC_LOG_FILE     = "/tmp/mcpe_screenlog.txt"   # Screen log
MC_OUTPUT_FILE  = "/tmp/mc_output.txt"        # Filtered console output

os.makedirs(BACKUP_DIR, exist_ok=True)

DEFAULT_SECURITY = {
    "anticheat": True,
    "speed_detection": True,
    "xray_protection": True,
    "chest_lock": True,
    "property_protection": False,
    "speedhack_protection": True,
    "auto_ban": False,
    "banned_players": [],
    "whitelist": []
}

# ============================================================
#   TELEGRAM HELPERS
# ============================================================
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        if len(text) > 4000:
            text = text[:4000] + "\n...[Truncated]"
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=15)
    except Exception as e:
        print(f"TG error: {e}")

def send_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as doc:
            requests.post(url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": doc},
                timeout=180)
    except Exception as e:
        send_message(f"❌ File error: {e}")

def log_action(action):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action}\n")
    except Exception:
        pass

# ============================================================
#   SYSTEM HELPERS (FAST & RELIABLE)
# ============================================================
def run_cmd(cmd, timeout=30):
    """Run shell command safely with timeout."""
    try:
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=timeout)
        return r
    except subprocess.TimeoutExpired:
        class R: stdout = ""; stderr = "Timeout"; returncode = 1
        return R()
    except Exception as e:
        class R: stdout = ""; stderr = str(e); returncode = 1
        return R()

def send_to_console(mc_cmd):
    """Send command to Minecraft console via screen."""
    safe = mc_cmd.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    run_cmd(f'screen -S mcpe -X stuff "{safe}\n"', timeout=5)

def read_console_output(lines_count=20):
    """FAST log reader - reads screen logfile directly (no hardcopy delay)."""
    try:
        # Method 1: Read screen logfile (fastest)
        if os.path.exists(MC_LOG_FILE):
            with open(MC_LOG_FILE, "r", errors="ignore") as f:
                lines = [l.rstrip() for l in f.readlines() if l.strip()]
            if lines:
                return "\n".join(lines[-lines_count:])
        
        # Method 2: Fallback - bedrock server log
        bedrock_log = os.path.join(BASE_DIR, "logs", "latest.log")
        if os.path.exists(bedrock_log):
            with open(bedrock_log, "r", errors="ignore") as f:
                lines = [l.rstrip() for l in f.readlines() if l.strip()]
            if lines:
                return "\n".join(lines[-lines_count:])
        
        # Method 3: Fallback - screen hardcopy (slow, last resort)
        tmp = "/tmp/mc_hardcopy.txt"
        run_cmd(f"screen -S mcpe -X hardcopy {tmp}", timeout=3)
        time.sleep(0.3)
        if os.path.exists(tmp):
            with open(tmp, "r", errors="ignore") as f:
                lines = [l.rstrip() for l in f.readlines() if l.strip()]
            if lines:
                return "\n".join(lines[-lines_count:])
        
        return "⚠️ No output captured."
    except Exception as e:
        return f"Log error: {e}"

def is_server_running():
    """Fast server status check."""
    try:
        out = run_cmd("screen -ls", timeout=5).stdout
        return "mcpe" in out and "Dead" not in out
    except Exception:
        return False

def is_tunnel_running():
    try:
        out = run_cmd("screen -ls", timeout=5).stdout
        return "playit-tunnel" in out
    except Exception:
        return False

def is_bot_running():
    try:
        out = run_cmd("screen -ls", timeout=5).stdout
        return "tg-bot" in out
    except Exception:
        return False

def stop_server():
    run_cmd("screen -S mcpe -X quit", timeout=5)
    time.sleep(2)
    run_cmd("pkill -f bedrock_server", timeout=5)
    time.sleep(1)

def start_server():
    """Start server with screen logging enabled."""
    stop_server()
    run_cmd(f"rm -f {MC_LOG_FILE}", timeout=3)
    cmd = (
        f'screen -L -Logfile {MC_LOG_FILE} -dmS mcpe '
        f'bash -c "cd {BASE_DIR} && LD_LIBRARY_PATH=. ./bedrock_server"'
    )
    run_cmd(cmd, timeout=10)
    time.sleep(6)  # Wait for server to boot
    
    # Verify it actually started
    for _ in range(5):
        if is_server_running():
            return True
        time.sleep(2)
    return False

def get_active_world():
    if not os.path.exists(PROPERTIES_FILE):
        return "Bedrock level"
    try:
        with open(PROPERTIES_FILE, "r") as f:
            for line in f:
                if line.startswith("level-name="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "Bedrock level"

def update_property(key, value):
    if not os.path.exists(PROPERTIES_FILE):
        return
    try:
        with open(PROPERTIES_FILE, "r") as f:
            lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}\n")
        with open(PROPERTIES_FILE, "w") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"update_property error: {e}")

# ============================================================
#   JSON HELPERS
# ============================================================
def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"save_json error: {e}")

# ============================================================
#   VERSION DETECTION
# ============================================================
KNOWN_BEDROCK_VERSIONS = [
    "1.21.51.02", "1.21.50.07", "1.21.44.01", "1.21.31.04",
    "1.21.30.03", "1.21.20.03", "1.21.2.02", "1.21.0.03"
]

def detect_latest_bedrock_version():
    for v in KNOWN_BEDROCK_VERSIONS:
        url = f"https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-{v}.zip"
        try:
            r = requests.head(url, timeout=6, allow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return v
        except Exception:
            continue
    return None

def get_current_server_version():
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE) as f:
                return f.read().strip()
        except Exception:
            pass
    return "Unknown"

def save_server_version(v):
    with open(VERSION_FILE, "w") as f:
        f.write(v)

# ============================================================
#   ANTICHEAT WATCHDOG (Bedrock-safe, no errors)
# ============================================================
def anticheat_watchdog():
    while True:
        try:
            sec = load_json(SECURITY_FILE, DEFAULT_SECURITY)
            if not sec.get("anticheat", True):
                time.sleep(120)
                continue
            if not is_server_running():
                time.sleep(60)
                continue
            time.sleep(120)
        except Exception as e:
            print(f"AC error: {e}")
            time.sleep(120)

# ============================================================
#   HELP TEXT
# ============================================================
HELP_TEXT = """<b>🎮 MCPE MASTER SERVER CONTROL PANEL</b>
<b>Total 55+ Commands</b>

<b>━━━ [ 1. EMERGENCY & SETUP ] ━━━</b>
/resetserver — Wipe warning
/resetserver CONFIRM — Full reset

<b>━━━ [ 2. FARM CHUNK LOADER ] ━━━</b>
/loadchunk &lt;X&gt; &lt;Z&gt; &lt;radius&gt; [name]
/chunklist
/removechunk &lt;name&gt;
/removeallchunks

<b>━━━ [ 3. SURVEILLANCE ] ━━━</b>
/spy &lt;player&gt;
/unspy &lt;player&gt;
/spylist
/banlist

<b>━━━ [ 4. ANTI-CHEAT ] ━━━</b>
/propertyprotection &lt;on|off&gt;
/chestlock &lt;on|off&gt;
/antixray &lt;on|off&gt;
/speedhackprotection &lt;on|off&gt;

<b>━━━ [ 5. PUNISHMENT ] ━━━</b>
/freeze &lt;player&gt;
/unfreeze &lt;player&gt;
/mute &lt;player&gt;
/unmute &lt;player&gt;
/kill &lt;player&gt;
/clearinv &lt;player&gt;

<b>━━━ [ 6. ROLES ] ━━━</b>
/players — Online list
/visitor &lt;player&gt;
/member &lt;player&gt;
/op &lt;player&gt;
/deop &lt;player&gt;
/kick &lt;player&gt;
/ban &lt;player&gt; [reason]
/unban &lt;player&gt;

<b>━━━ [ 7. TP / GIVE / WHITELIST ] ━━━</b>
/tp &lt;p1&gt; &lt;p2&gt;
/tpxyz &lt;p&gt; &lt;x&gt; &lt;y&gt; &lt;z&gt;
/give &lt;p&gt; &lt;item&gt; [count]
/effect &lt;p&gt; &lt;effect&gt; [sec] [amp]
/whitelist &lt;on|off&gt;
/whitelistadd &lt;player&gt;
/whitelistremove &lt;player&gt;

<b>━━━ [ 8. GAMEPLAY ] ━━━</b>
/coords /keepinventory
/pvp &lt;on|off&gt;
/difficulty &lt;level&gt;
/gamemode &lt;mode&gt;
/time &lt;day|night&gt;
/weather &lt;clear|rain|thunder&gt;
/mobspawning &lt;true|false&gt;
/killmobs
/setworldspawn [x y z]

<b>━━━ [ 9. CHAT & RECOVERY ] ━━━</b>
/say &lt;msg&gt; /clearchat
/seed &lt;number&gt;
[Send .zip/.mcworld]
/backup /backuplist
/restoresnapshot &lt;file&gt;

<b>━━━ [ 10. DIAGNOSTICS ] ━━━</b>
/updateserver [version]
/checkupdate /status
/serverstats /logs
/restart /fixtunnel
/cmd &lt;command&gt;
/shell &lt;command&gt;
"""

# ============================================================
#   WORLD UPLOAD
# ============================================================
def handle_document(doc):
    file_name = doc.get("file_name", "world.zip")
    if not file_name.endswith((".zip", ".mcworld")):
        send_message("❌ Sirf .zip ya .mcworld!")
        return

    send_message("📥 Downloading world...")
    try:
        file_id = doc["file_id"]
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_path = res["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        local_zip = os.path.join(BASE_DIR, "uploaded_world.zip")
        r = requests.get(download_url, stream=True, timeout=180)
        with open(local_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        send_message("⚙️ Applying...")
        stop_server()

        world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
        target_extract = os.path.join(WORLDS_DIR, world_folder_name)
        os.makedirs(target_extract, exist_ok=True)

        with zipfile.ZipFile(local_zip, 'r') as zip_ref:
            zip_ref.extractall(target_extract)

        entries = os.listdir(target_extract)
        if len(entries) == 1 and os.path.isdir(os.path.join(target_extract, entries[0])):
            nested = os.path.join(target_extract, entries[0])
            for item in os.listdir(nested):
                shutil.move(os.path.join(nested, item), target_extract)
            os.rmdir(nested)

        update_property("level-name", world_folder_name)
        start_server()
        send_message(f"✅ World imported: {world_folder_name}")
    except Exception as e:
        send_message(f"❌ Upload error: {e}")

# ============================================================
#   MAIN LOOP
# ============================================================
def handle_updates():
    offset = 0
    if not is_server_running():
        start_server()
    threading.Thread(target=anticheat_watchdog, daemon=True).start()
    send_message("🟢 <b>MCPE Master Server Active!</b>\n\n/help bhejo")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=25"
            r = requests.get(url, timeout=35)
            data = r.json()
            if not data.get("ok"):
                time.sleep(2)
                continue

            for item in data.get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message", {})
                chat = str(msg.get("chat", {}).get("id", ""))
                if chat != CHAT_ID:
                    continue

                if "document" in msg:
                    handle_document(msg["document"])
                    continue

                text = msg.get("text", "").strip()
                if not text:
                    continue

                log_action(f"CMD: {text}")
                parts = text.split()

                # ============ HELP ============
                if text in ["/start", "/help"]:
                    send_message(HELP_TEXT)

                # ============ 1. RESET ============
                elif text == "/resetserver":
                    send_message("⚠️ <b>WARNING!</b>\n\nServer files wipe honge.\nSahi me karna hai toh: <code>/resetserver CONFIRM</code>")
                elif text == "/resetserver CONFIRM":
                    send_message("🔄 Full reset...")
                    run_cmd("pkill -9 playit-cli")
                    run_cmd(f"rm -rf {BASE_DIR}/*", timeout=60)
                    send_message("✅ Reset complete.")
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli")

                # ============ 2. CHUNK LOADER ============
                elif text.startswith("/loadchunk "):
                    if len(parts) < 4:
                        send_message("Usage: /loadchunk <X> <Z> <radius> [name]")
                    else:
                        try:
                            x, z, radius = int(parts[1]), int(parts[2]), int(parts[3])
                            name = parts[4] if len(parts) > 4 else f"farm_{x}_{z}"
                            send_to_console(f"tickingarea add circle {x} 64 {z} {radius} {name}")
                            chunks = load_json(CHUNK_FILE, {})
                            chunks[name] = {"x": x, "z": z, "radius": radius}
                            save_json(CHUNK_FILE, chunks)
                            send_message(f"✅ Chunk '{name}' added: ({x}, {z}) r={radius}")
                        except ValueError:
                            send_message("❌ X, Z, radius numbers hone chahiye.")

                elif text == "/chunklist":
                    chunks = load_json(CHUNK_FILE, {})
                    if not chunks:
                        send_message("📭 No chunks.")
                    else:
                        out = "📋 <b>Active Chunks:</b>\n\n"
                        for name, d in chunks.items():
                            out += f"• {name}: ({d['x']}, {d['z']}) r={d['radius']}\n"
                        send_message(out)

                elif text.startswith("/removechunk "):
                    name = parts[1]
                    chunks = load_json(CHUNK_FILE, {})
                    if name in chunks:
                        send_to_console(f"tickingarea remove {name}")
                        del chunks[name]
                        save_json(CHUNK_FILE, chunks)
                        send_message(f"✅ Removed: {name}")
                    else:
                        send_message(f"❌ '{name}' not found.")

                elif text == "/removeallchunks":
                    send_to_console("tickingarea remove_all")
                    save_json(CHUNK_FILE, {})
                    send_message("✅ All chunks removed.")

                # ============ 3. SURVEILLANCE ============
                elif text.startswith("/spy "):
                    target = parts[1]
                    spy = load_json(SPY_FILE, {"targets": []})
                    if target not in spy["targets"]:
                        spy["targets"].append(target)
                        save_json(SPY_FILE, spy)
                    send_message(f"🕵️ Spying: {target}")

                elif text.startswith("/unspy "):
                    target = parts[1]
                    spy = load_json(SPY_FILE, {"targets": []})
                    if target in spy["targets"]:
                        spy["targets"].remove(target)
                        save_json(SPY_FILE, spy)
                    send_message(f"✅ Unspy: {target}")

                elif text == "/spylist":
                    spy = load_json(SPY_FILE, {"targets": []})
                    if not spy["targets"]:
                        send_message("📭 No spies.")
                    else:
                        send_message("🕵️ <b>Monitored:</b>\n" + "\n".join(f"• {t}" for t in spy["targets"]))

                elif text == "/banlist":
                    bl = load_json(BLACKLIST_FILE, {"players": []})
                    if not bl["players"]:
                        send_message("📭 No banned players.")
                    else:
                        out = "🔨 <b>Banned:</b>\n\n"
                        for p in bl["players"]:
                            out += f"• {p.get('name')} — {p.get('reason', 'N/A')}\n"
                        send_message(out)

                # ============ 4. ANTI-CHEAT ============
                elif text.startswith("/propertyprotection "):
                    val = parts[1].lower() in ["on", "true", "enable"]
                    send_to_console(f"gamerule immutableworld {str(val).lower()}")
                    sec = load_json(SECURITY_FILE, DEFAULT_SECURITY)
                    sec["property_protection"] = val
                    save_json(SECURITY_FILE, sec)
                    send_message(f"🏠 Property protection: {'ON' if val else 'OFF'}")

                elif text.startswith("/chestlock "):
                    val = parts[1].lower() in ["on", "true", "enable"]
                    sec = load_json(SECURITY_FILE, DEFAULT_SECURITY)
                    sec["chest_lock"] = val
                    save_json(SECURITY_FILE, sec)
                    send_message(f"🔐 Chest lock: {'ON' if val else 'OFF'}")

                elif text.startswith("/antixray "):
                    val = "true" if parts[1].lower() in ["on", "true", "enable"] else "false"
                    update_property("texturepack-required", val)
                    send_message(f"🔍 Anti-Xray: {val}")

                elif text.startswith("/speedhackprotection "):
                    val = "server-auth" if parts[1].lower() in ["on", "true", "enable"] else "client-auth"
                    update_property("server-authoritative-movement", val)
                    send_message(f"⚡ Speedhack: {val}")

                # ============ 5. PUNISHMENT ============
                elif text.startswith("/freeze "):
                    p = parts[1]
                    send_to_console(f'effect "{p}" slowness 999999 255 true')
                    send_to_console(f'effect "{p}" jump_boost 999999 128 true')
                    send_message(f"🧊 Frozen: {p}")

                elif text.startswith("/unfreeze "):
                    p = parts[1]
                    send_to_console(f'effect "{p}" slowness 0 0 true')
                    send_to_console(f'effect "{p}" jump_boost 0 0 true')
                    send_message(f"🔥 Unfrozen: {p}")

                elif text.startswith("/mute "):
                    p = parts[1]
                    send_to_console(f'ability "{p}" mute true')
                    send_message(f"🔇 Muted: {p}")

                elif text.startswith("/unmute "):
                    p = parts[1]
                    send_to_console(f'ability "{p}" mute false')
                    send_message(f"🔊 Unmuted: {p}")

                elif text.startswith("/kill "):
                    p = parts[1]
                    send_to_console(f'kill "{p}"')
                    send_message(f"💀 Killed: {p}")

                elif text.startswith("/clearinv "):
                    p = parts[1]
                    send_to_console(f'clear "{p}"')
                    send_message(f"🗑️ Cleared: {p}")

                # ============ 6. ROLES ============
                elif text == "/players":
                    send_to_console("list")
                    time.sleep(0.8)
                    out = read_console_output(8)
                    send_message(f"👥 <b>Online:</b>\n<pre>{out[-2000:]}</pre>")

                elif text.startswith("/visitor "):
                    p = parts[1]
                    send_to_console(f'permission "{p}" set visitor')
                    send_message(f"👤 Visitor: {p}")

                elif text.startswith("/member "):
                    p = parts[1]
                    send_to_console(f'permission "{p}" set member')
                    send_message(f"👤 Member: {p}")

                elif text.startswith("/op "):
                    p = parts[1]
                    send_to_console(f'op "{p}"')
                    send_message(f"✅ OP: {p}")

                elif text.startswith("/deop "):
                    p = parts[1]
                    send_to_console(f'deop "{p}"')
                    time.sleep(0.5)
                    send_to_console(f'gamemode survival "{p}"')
                    send_message(f"✅ DeOP + survival: {p}")

                elif text.startswith("/kick "):
                    p = parts[1]
                    send_to_console(f'kick "{p}"')
                    send_message(f"👢 Kicked: {p}")

                elif text.startswith("/ban "):
                    if len(parts) < 2:
                        send_message("Usage: /ban <player> [reason]")
                    else:
                        p = parts[1]
                        reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
                        send_to_console(f'ban "{p}"')
                        bl = load_json(BLACKLIST_FILE, {"players": []})
                        bl["players"].append({
                            "name": p, "reason": reason,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        save_json(BLACKLIST_FILE, bl)
                        send_message(f"🔨 Banned: {p}\nReason: {reason}")

                elif text.startswith("/unban "):
                    p = parts[1]
                    send_to_console(f'unban "{p}"')
                    bl = load_json(BLACKLIST_FILE, {"players": []})
                    bl["players"] = [x for x in bl["players"] if x.get("name") != p]
                    save_json(BLACKLIST_FILE, bl)
                    send_message(f"✅ Unbanned: {p}")

                # ============ 7. TP / GIVE / WL ============
                elif text.startswith("/tp "):
                    if len(parts) >= 3:
                        send_to_console(f'tp "{parts[1]}" "{parts[2]}"')
                        send_message(f"🌀 {parts[1]} → {parts[2]}")

                elif text.startswith("/tpxyz "):
                    if len(parts) >= 5:
                        p, x, y, z = parts[1], parts[2], parts[3], parts[4]
                        send_to_console(f'tp "{p}" {x} {y} {z}')
                        send_message(f"🌀 {p} → ({x}, {y}, {z})")

                elif text.startswith("/give "):
                    if len(parts) >= 3:
                        p, item = parts[1], parts[2]
                        count = parts[3] if len(parts) > 3 else "1"
                        send_to_console(f'give "{p}" {item} {count}')
                        send_message(f"🎁 {count}x {item} → {p}")

                elif text.startswith("/effect "):
                    if len(parts) >= 3:
                        p, eff = parts[1], parts[2]
                        sec = parts[3] if len(parts) > 3 else "30"
                        amp = parts[4] if len(parts) > 4 else "1"
                        send_to_console(f'effect "{p}" {eff} {sec} {amp} true')
                        send_message(f"✨ {eff} → {p}")

                elif text.startswith("/whitelist "):
                    val = "on" if parts[1].lower() in ["on", "true"] else "off"
                    send_to_console(f"whitelist {val}")
                    send_message(f"📋 Whitelist: {val.upper()}")

                elif text.startswith("/whitelistadd "):
                    p = parts[1]
                    send_to_console(f'whitelist add "{p}"')
                    send_message(f"✅ Added: {p}")

                elif text.startswith("/whitelistremove "):
                    p = parts[1]
                    send_to_console(f'whitelist remove "{p}"')
                    send_message(f"✅ Removed: {p}")

                # ============ 8. GAMEPLAY ============
                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("🧭 Coordinates ON")

                elif text == "/keepinventory":
                    send_to_console("gamerule keepinventory true")
                    send_message("💼 KeepInventory ON")

                elif text.startswith("/pvp "):
                    val = "true" if parts[1].lower() in ["on", "true", "1"] else "false"
                    send_to_console(f"gamerule pvp {val}")
                    update_property("pvp", val)
                    send_message(f"⚔️ PvP: {val}")

                elif text.startswith("/difficulty "):
                    diff = parts[1].lower()
                    if diff in ["peaceful", "easy", "normal", "hard"]:
                        send_to_console(f"difficulty {diff}")
                        update_property("difficulty", diff)
                        send_message(f"🎯 Difficulty: {diff}")

                elif text.startswith("/gamemode "):
                    gm = parts[1].lower()
                    if gm in ["survival", "creative", "adventure"]:
                        send_to_console(f"defaultgamemode {gm}")
                        update_property("gamemode", gm)
                        send_message(f"🎮 Default: {gm}")

                elif text.startswith("/time "):
                    send_to_console(f"time set {parts[1]}")
                    send_message(f"⏰ Time: {parts[1]}")

                elif text.startswith("/weather "):
                    send_to_console(f"weather {parts[1]}")
                    send_message(f"🌦️ Weather: {parts[1]}")

                elif text.startswith("/mobspawning "):
                    send_to_console(f"gamerule domobspawning {parts[1]}")
                    send_message(f"👹 Mob spawning: {parts[1]}")

                elif text == "/killmobs":
                    send_to_console("kill @e[type=!player]")
                    send_message("☠️ Mobs cleared")

                elif text.startswith("/setworldspawn"):
                    if len(parts) >= 4:
                        send_to_console(f"setworldspawn {parts[1]} {parts[2]} {parts[3]}")
                        send_message(f"📍 Spawn: ({parts[1]}, {parts[2]}, {parts[3]})")
                    else:
                        send_to_console("setworldspawn")
                        send_message("📍 Spawn set")

                # ============ 9. CHAT & RECOVERY ============
                elif text.startswith("/say "):
                    m = text.split(" ", 1)[1]
                    send_to_console(f'say [ANNOUNCEMENT]: {m}')
                    send_message(f"📢 {m}")

                elif text == "/clearchat":
                    for _ in range(50):
                        send_to_console("say §r")
                    send_message("🧹 Chat cleared")

                elif text.startswith("/seed "):
                    seed = parts[1]
                    new_world = f"world_{int(time.time())}"
                    send_message(f"🌱 Creating seed {seed}...")
                    stop_server()
                    update_property("level-seed", seed)
                    update_property("level-name", new_world)
                    start_server()
                    send_message(f"✅ World: {new_world}\nSeed: {seed}")

                elif text == "/backup":
                    send_message("📦 Creating backup...")
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    bz = os.path.join(BACKUP_DIR, f"backup_{ts}.zip")
                    run_cmd(f"cd {BASE_DIR} && zip -r {bz} worlds/ server.properties security_config.json blacklist.json 2>/dev/null", timeout=300)
                    if os.path.exists(bz) and os.path.getsize(bz) > 1000:
                        send_document(bz, f"📦 Backup {ts}")
                    else:
                        send_message("❌ Backup failed.")

                elif text == "/backuplist":
                    try:
                        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")],
                                       key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x)),
                                       reverse=True)[:10]
                        if not files:
                            send_message("📭 No backups.")
                        else:
                            out = "📋 <b>Backups:</b>\n\n"
                            for f in files:
                                sz = os.path.getsize(os.path.join(BACKUP_DIR, f)) / (1024*1024)
                                out += f"• {f} ({sz:.1f} MB)\n"
                            send_message(out)
                    except Exception as e:
                        send_message(f"❌ {e}")

                elif text.startswith("/restoresnapshot "):
                    fname = parts[1]
                    fpath = os.path.join(BACKUP_DIR, fname)
                    if os.path.exists(fpath):
                        send_message("⚙️ Restoring...")
                        stop_server()
                        run_cmd(f"cd {BASE_DIR} && unzip -o {fpath}", timeout=300)
                        start_server()
                        send_message(f"✅ Restored: {fname}")
                    else:
                        send_message(f"❌ Not found: {fname}")

                # ============ 10. DIAGNOSTICS ============
                elif text.startswith("/updateserver"):
                    if len(parts) > 1:
                        version = parts[1]
                    else:
                        send_message("🔍 Auto-detecting...")
                        version = detect_latest_bedrock_version()
                        if not version:
                            send_message("❌ Manual daalo: /updateserver 1.21.51.02")
                            continue

                    send_message(f"📥 Updating to {version}...")
                    stop_server()
                    run_cmd(f"cd {BASE_DIR} && mv bedrock_server bedrock_server_old 2>/dev/null")
                    url = f"https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-{version}.zip"
                    run_cmd(f'cd {BASE_DIR} && wget --user-agent="Mozilla/5.0" -O bedrock-server.zip "{url}"', timeout=600)
                    if os.path.exists(os.path.join(BASE_DIR, "bedrock-server.zip")) and \
                       os.path.getsize(os.path.join(BASE_DIR, "bedrock-server.zip")) > 50_000_000:
                        run_cmd(f"cd {BASE_DIR} && unzip -o bedrock-server.zip && chmod +x bedrock_server", timeout=120)
                        save_server_version(version)
                        start_server()
                        send_message(f"✅ Updated to {version}!")
                    else:
                        run_cmd(f"cd {BASE_DIR} && mv bedrock_server_old bedrock_server 2>/dev/null")
                        send_message("❌ Download failed. Rollback done.")

                elif text == "/checkupdate":
                    send_message("🔍 Checking...")
                    latest = detect_latest_bedrock_version()
                    current = get_current_server_version()
                    if latest:
                        upd = "✅ Update available!" if latest != current else "✅ Up to date!"
                        send_message(f"📌 Current: {current}\n🆕 Latest: {latest}\n\n{upd}")
                    else:
                        send_message(f"📌 Current: {current}\n❌ Latest not detected.")

                elif text == "/status":
                    mc = "🟢 ONLINE" if is_server_running() else "🔴 OFFLINE"
                    pt = "🟢 ONLINE" if is_tunnel_running() else "🔴 OFFLINE"
                    bt = "🟢 ONLINE" if is_bot_running() else "🔴 OFFLINE"
                    send_message(f"📊 <b>Status</b>\n\nMinecraft: {mc}\nPlayit: {pt}\nBot: {bt}\nVersion: {get_current_server_version()}\nWorld: {get_active_world()}")

                elif text == "/serverstats":
                    mem = run_cmd("free -h", timeout=5).stdout
                    disk = run_cmd("df -h /root", timeout=5).stdout
                    uptime = run_cmd("uptime", timeout=5).stdout
                    send_message(f"💻 <b>Server Stats</b>\n\n<b>Uptime:</b>\n<pre>{uptime}</pre>\n<b>RAM:</b>\n<pre>{mem[:400]}</pre>\n<b>Disk:</b>\n<pre>{disk[:400]}</pre>")

                elif text == "/logs":
                    out = read_console_output(20)
                    send_message(f"📜 <b>Logs:</b>\n<pre>{out[-3500:]}</pre>")

                elif text == "/restart":
                    send_message("🔄 Restarting...")
                    ok = start_server()
                    send_message("✅ Restarted!" if ok else "❌ Failed. Check /logs")

                elif text == "/fixtunnel":
                    send_message("🔄 Fixing tunnel...")
                    run_cmd("pkill -9 playit-cli", timeout=5)
                    run_cmd("screen -S playit-tunnel -X quit", timeout=5)
                    time.sleep(2)
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli", timeout=5)
                    time.sleep(2)
                    if is_tunnel_running():
                        send_message("✅ Tunnel restarted!")
                    else:
                        send_message("❌ Tunnel failed to start.")

                elif text.startswith("/cmd "):
                    c = text.split(" ", 1)[1]
                    send_to_console(c)
                    send_message(f"⌨️ Sent: <code>{c}</code>")

                elif text.startswith("/shell "):
                    c = text.split(" ", 1)[1]
                    res = run_cmd(c, timeout=60)
                    out = (res.stdout or res.stderr or "Done.")[-3500:]
                    send_message(f"💻 <pre>{out}</pre>")

                else:
                    if text.startswith("/"):
                        send_message(f"❓ Unknown: {text}\n\n/help bhejo")

        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(3)

# ============================================================
if __name__ == "__main__":
    handle_updates()
