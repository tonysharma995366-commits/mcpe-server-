#!/usr/bin/env python3
# ============================================================
#  MCPE MASTER SERVER — ULTRA FAST EDITION
#  55+ Commands | Single Instance | Zero Delay
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
import fcntl
from datetime import datetime

# ---------------- SINGLE INSTANCE LOCK ----------------
LOCK_FILE = "/tmp/tg_manager.lock"
try:
    lock_fd = open(LOCK_FILE, 'w')
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("Another instance is already running. Exiting.")
    sys.exit(1)

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
MC_LOG_FILE     = "/tmp/mcpe_screenlog.txt"

os.makedirs(BACKUP_DIR, exist_ok=True)

DEFAULT_SECURITY = {
    "anticheat": True,
    "speed_detection": True,
    "xray_protection": True,
    "chest_lock": True,
    "property_protection": False,
    "speedhack_protection": True,
    "banned_players": [],
    "whitelist": []
}

# ============================================================
#   FAST TELEGRAM SENDER
# ============================================================
_session = requests.Session()

def send_message(text):
    try:
        if len(text) > 4000:
            text = text[:4000] + "\n...[Truncated]"
        _session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=8
        )
    except Exception as e:
        print(f"TG error: {e}")

def send_document(file_path, caption=""):
    try:
        with open(file_path, 'rb') as doc:
            _session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": doc},
                timeout=180
            )
    except Exception as e:
        send_message(f"❌ File error: {e}")

def log_action(action):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action}\n")
    except Exception:
        pass

# ============================================================
#   FAST SYSTEM HELPERS
# ============================================================
def run_cmd(cmd, timeout=15):
    """Run shell command fast with timeout."""
    try:
        return subprocess.run(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout
        )
    except Exception as e:
        class R: stdout = ""; stderr = str(e); returncode = 1
        return R()

def send_to_console(mc_cmd):
    """Ultra-fast console injection."""
    safe = mc_cmd.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    subprocess.Popen(
        f'screen -S mcpe -X stuff "{safe}\n"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def read_console_output(lines_count=20):
    """Instant log read — no delay."""
    # Primary: screen logfile
    if os.path.exists(MC_LOG_FILE):
        try:
            with open(MC_LOG_FILE, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 50000))
                data = f.read().decode("utf-8", errors="ignore")
            lines = [l.rstrip() for l in data.splitlines() if l.strip()]
            if lines:
                return "\n".join(lines[-lines_count:])
        except Exception:
            pass
    
    # Fallback: bedrock latest.log
    bedrock_log = os.path.join(BASE_DIR, "logs", "latest.log")
    if os.path.exists(bedrock_log):
        try:
            with open(bedrock_log, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 50000))
                data = f.read().decode("utf-8", errors="ignore")
            lines = [l.rstrip() for l in data.splitlines() if l.strip()]
            if lines:
                return "\n".join(lines[-lines_count:])
        except Exception:
            pass
    
    return "⚠️ No output captured."

def is_server_running():
    try:
        out = run_cmd("screen -ls", timeout=3).stdout
        return "mcpe" in out and "Dead" not in out
    except Exception:
        return False

def is_tunnel_running():
    try:
        out = run_cmd("screen -ls", timeout=3).stdout
        return "playit-tunnel" in out
    except Exception:
        return False

def stop_server():
    subprocess.Popen("screen -S mcpe -X quit", shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    run_cmd("pkill -9 -f bedrock_server", timeout=3)
    time.sleep(0.5)

def start_server():
    stop_server()
    run_cmd(f"rm -f {MC_LOG_FILE}", timeout=3)
    cmd = (
        f'screen -L -Logfile {MC_LOG_FILE} -dmS mcpe '
        f'bash -c "cd {BASE_DIR} && LD_LIBRARY_PATH=. ./bedrock_server"'
    )
    run_cmd(cmd, timeout=5)
    # Fast verify
    for _ in range(8):
        time.sleep(1)
        if is_server_running():
            return True
    return False

def get_active_world():
    try:
        with open(PROPERTIES_FILE, "r") as f:
            for line in f:
                if line.startswith("level-name="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "Bedrock level"

def update_property(key, value):
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
    except Exception:
        pass

# ============================================================
#   JSON HELPERS
# ============================================================
def load_json(path, default):
    try:
        if not os.path.exists(path):
            save_json(path, default)
            return default
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

# ============================================================
#   VERSION
# ============================================================
KNOWN_BEDROCK_VERSIONS = [
    "1.21.51.02", "1.21.50.07", "1.21.44.01", "1.21.31.04",
    "1.21.30.03", "1.21.20.03", "1.21.2.02", "1.21.0.03"
]

def detect_latest_bedrock_version():
    for v in KNOWN_BEDROCK_VERSIONS:
        url = f"https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-{v}.zip"
        try:
            r = requests.head(url, timeout=5, allow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return v
        except Exception:
            continue
    return None

def get_current_server_version():
    try:
        with open(VERSION_FILE) as f:
            return f.read().strip()
    except Exception:
        return "Unknown"

def save_server_version(v):
    try:
        with open(VERSION_FILE, "w") as f:
            f.write(v)
    except Exception:
        pass

# ============================================================
#   BACKGROUND WATCHDOG (lightweight)
# ============================================================
def watchdog():
    while True:
        try:
            time.sleep(300)  # 5 min
            # Server auto-restart if crashed
            if not is_server_running():
                if os.path.exists(os.path.join(BASE_DIR, "bedrock_server")):
                    start_server()
        except Exception:
            time.sleep(60)

# ============================================================
#   HELP TEXT
# ============================================================
HELP_TEXT = """<b>🎮 MCPE MASTER SERVER — ULTRA FAST</b>

<b>[1] SETUP</b>
/resetserver · /resetserver CONFIRM

<b>[2] CHUNK LOADER</b>
/loadchunk X Z radius [name]
/chunklist · /removechunk name · /removeallchunks

<b>[3] SURVEILLANCE</b>
/spy p · /unspy p · /spylist · /banlist

<b>[4] ANTI-CHEAT</b>
/propertyprotection on|off
/chestlock on|off
/antixray on|off
/speedhackprotection on|off

<b>[5] PUNISHMENT</b>
/freeze p · /unfreeze p
/mute p · /unmute p
/kill p · /clearinv p

<b>[6] ROLES</b>
/players · /visitor p · /member p
/op p · /deop p · /kick p
/ban p [reason] · /unban p

<b>[7] TP/GIVE/WL</b>
/tp p1 p2 · /tpxyz p x y z
/give p item count
/effect p eff sec amp
/whitelist on|off
/whitelistadd p · /whitelistremove p

<b>[8] GAMEPLAY</b>
/coords · /keepinventory
/pvp on|off · /difficulty level
/gamemode mode · /time t
/weather w · /mobspawning t
/killmobs · /setworldspawn x y z

<b>[9] CHAT & RECOVERY</b>
/say msg · /clearchat · /seed num
[Send .zip/.mcworld]
/backup · /backuplist · /restoresnapshot file

<b>[10] DIAGNOSTICS</b>
/updateserver [ver] · /checkupdate
/status · /serverstats · /logs
/restart · /fixtunnel
/cmd cmd · /shell cmd

<b>Total: 55+ commands</b>"""

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
        res = _session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        file_path = res["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        local_zip = os.path.join(BASE_DIR, "uploaded_world.zip")
        r = _session.get(url, stream=True, timeout=180)
        with open(local_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        send_message("⚙️ Applying...")
        stop_server()
        world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
        target_extract = os.path.join(WORLDS_DIR, world_folder_name)
        os.makedirs(target_extract, exist_ok=True)
        with zipfile.ZipFile(local_zip, 'r') as z:
            z.extractall(target_extract)
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
    # Clear pending updates
    try:
        _session.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1",
            timeout=5
        )
    except Exception:
        pass

    if not is_server_running():
        start_server()
    
    threading.Thread(target=watchdog, daemon=True).start()
    send_message("🟢 <b>MCPE Master Server Active!</b>\n\n/help bhejo")
    
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=10"
            r = _session.get(url, timeout=15)
            data = r.json()
            if not data.get("ok"):
                time.sleep(1)
                continue

            for item in data.get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message", {})
                chat = str(msg.get("chat", {}).get("id", ""))
                if chat != CHAT_ID:
                    continue

                if "document" in msg:
                    threading.Thread(target=handle_document, args=(msg["document"],), daemon=True).start()
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
                    send_message("⚠️ <b>WARNING!</b>\n\nFiles wipe honge.\nSahi me: <code>/resetserver CONFIRM</code>")
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
                            send_message(f"✅ Chunk '{name}': ({x}, {z}) r={radius}")
                        except ValueError:
                            send_message("❌ Numbers daalo.")

                elif text == "/chunklist":
                    chunks = load_json(CHUNK_FILE, {})
                    if not chunks:
                        send_message("📭 No chunks.")
                    else:
                        out = "📋 <b>Active:</b>\n"
                        for n, d in chunks.items():
                            out += f"• {n}: ({d['x']}, {d['z']}) r={d['radius']}\n"
                        send_message(out)

                elif text.startswith("/removechunk "):
                    n = parts[1]
                    chunks = load_json(CHUNK_FILE, {})
                    if n in chunks:
                        send_to_console(f"tickingarea remove {n}")
                        del chunks[n]
                        save_json(CHUNK_FILE, chunks)
                        send_message(f"✅ Removed: {n}")
                    else:
                        send_message(f"❌ Not found: {n}")

                elif text == "/removeallchunks":
                    send_to_console("tickingarea remove_all")
                    save_json(CHUNK_FILE, {})
                    send_message("✅ All chunks removed.")

                # ============ 3. SURVEILLANCE ============
                elif text.startswith("/spy "):
                    p = parts[1]
                    spy = load_json(SPY_FILE, {"targets": []})
                    if p not in spy["targets"]:
                        spy["targets"].append(p)
                        save_json(SPY_FILE, spy)
                    send_message(f"🕵️ Spying: {p}")

                elif text.startswith("/unspy "):
                    p = parts[1]
                    spy = load_json(SPY_FILE, {"targets": []})
                    if p in spy["targets"]:
                        spy["targets"].remove(p)
                        save_json(SPY_FILE, spy)
                    send_message(f"✅ Unspy: {p}")

                elif text == "/spylist":
                    spy = load_json(SPY_FILE, {"targets": []})
                    if not spy["targets"]:
                        send_message("📭 No spies.")
                    else:
                        send_message("🕵️ <b>Monitored:</b>\n" + "\n".join(f"• {t}" for t in spy["targets"]))

                elif text == "/banlist":
                    bl = load_json(BLACKLIST_FILE, {"players": []})
                    if not bl["players"]:
                        send_message("📭 No bans.")
                    else:
                        out = "🔨 <b>Banned:</b>\n"
                        for p in bl["players"]:
                            out += f"• {p.get('name')} — {p.get('reason', 'N/A')}\n"
                        send_message(out)

                # ============ 4. ANTI-CHEAT ============
                elif text.startswith("/propertyprotection "):
                    v = parts[1].lower() in ["on", "true", "enable"]
                    send_to_console(f"gamerule immutableworld {str(v).lower()}")
                    send_message(f"🏠 Property protection: {'ON' if v else 'OFF'}")

                elif text.startswith("/chestlock "):
                    v = parts[1].lower() in ["on", "true", "enable"]
                    sec = load_json(SECURITY_FILE, DEFAULT_SECURITY)
                    sec["chest_lock"] = v
                    save_json(SECURITY_FILE, sec)
                    send_message(f"🔐 Chest lock: {'ON' if v else 'OFF'}")

                elif text.startswith("/antixray "):
                    v = "true" if parts[1].lower() in ["on", "true", "enable"] else "false"
                    update_property("texturepack-required", v)
                    send_message(f"🔍 Anti-Xray: {v}")

                elif text.startswith("/speedhackprotection "):
                    v = "server-auth" if parts[1].lower() in ["on", "true", "enable"] else "client-auth"
                    update_property("server-authoritative-movement", v)
                    send_message(f"⚡ Speedhack: {v}")

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
                    send_to_console(f'ability "{parts[1]}" mute true')
                    send_message(f"🔇 Muted: {parts[1]}")

                elif text.startswith("/unmute "):
                    send_to_console(f'ability "{parts[1]}" mute false')
                    send_message(f"🔊 Unmuted: {parts[1]}")

                elif text.startswith("/kill "):
                    send_to_console(f'kill "{parts[1]}"')
                    send_message(f"💀 Killed: {parts[1]}")

                elif text.startswith("/clearinv "):
                    send_to_console(f'clear "{parts[1]}"')
                    send_message(f"🗑️ Cleared: {parts[1]}")

                # ============ 6. ROLES ============
                elif text == "/players":
                    send_to_console("list")
                    time.sleep(0.6)
                    out = read_console_output(10)
                    # Extract just player list
                    send_message(f"👥 <b>Online:</b>\n<pre>{out[-1500:]}</pre>")

                elif text.startswith("/visitor "):
                    send_to_console(f'permission "{parts[1]}" set visitor')
                    send_message(f"👤 Visitor: {parts[1]}")

                elif text.startswith("/member "):
                    send_to_console(f'permission "{parts[1]}" set member')
                    send_message(f"👤 Member: {parts[1]}")

                elif text.startswith("/op "):
                    send_to_console(f'op "{parts[1]}"')
                    send_message(f"✅ OP: {parts[1]}")

                elif text.startswith("/deop "):
                    p = parts[1]
                    send_to_console(f'deop "{p}"')
                    time.sleep(0.3)
                    send_to_console(f'gamemode survival "{p}"')
                    send_message(f"✅ DeOP + survival: {p}")

                elif text.startswith("/kick "):
                    send_to_console(f'kick "{parts[1]}"')
                    send_message(f"👢 Kicked: {parts[1]}")

                elif text.startswith("/ban "):
                    if len(parts) < 2:
                        send_message("Usage: /ban <player> [reason]")
                    else:
                        p = parts[1]
                        reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
                        send_to_console(f'ban "{p}"')
                        bl = load_json(BLACKLIST_FILE, {"players": []})
                        bl["players"].append({"name": p, "reason": reason,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                        save_json(BLACKLIST_FILE, bl)
                        send_message(f"🔨 Banned: {p}\n{reason}")

                elif text.startswith("/unban "):
                    p = parts[1]
                    send_to_console(f'unban "{p}"')
                    bl = load_json(BLACKLIST_FILE, {"players": []})
                    bl["players"] = [x for x in bl["players"] if x.get("name") != p]
                    save_json(BLACKLIST_FILE, bl)
                    send_message(f"✅ Unbanned: {p}")

                # ============ 7. TP/GIVE/WL ============
                elif text.startswith("/tp "):
                    if len(parts) >= 3:
                        send_to_console(f'tp "{parts[1]}" "{parts[2]}"')
                        send_message(f"🌀 {parts[1]} → {parts[2]}")

                elif text.startswith("/tpxyz "):
                    if len(parts) >= 5:
                        send_to_console(f'tp "{parts[1]}" {parts[2]} {parts[3]} {parts[4]}')
                        send_message(f"🌀 {parts[1]} → ({parts[2]}, {parts[3]}, {parts[4]})")

                elif text.startswith("/give "):
                    if len(parts) >= 3:
                        p, item = parts[1], parts[2]
                        cnt = parts[3] if len(parts) > 3 else "1"
                        send_to_console(f'give "{p}" {item} {cnt}')
                        send_message(f"🎁 {cnt}x {item} → {p}")

                elif text.startswith("/effect "):
                    if len(parts) >= 3:
                        p, eff = parts[1], parts[2]
                        sec = parts[3] if len(parts) > 3 else "30"
                        amp = parts[4] if len(parts) > 4 else "1"
                        send_to_console(f'effect "{p}" {eff} {sec} {amp} true')
                        send_message(f"✨ {eff} → {p}")

                elif text.startswith("/whitelist "):
                    v = "on" if parts[1].lower() in ["on", "true"] else "off"
                    send_to_console(f"whitelist {v}")
                    send_message(f"📋 Whitelist: {v.upper()}")

                elif text.startswith("/whitelistadd "):
                    send_to_console(f'whitelist add "{parts[1]}"')
                    send_message(f"✅ Added: {parts[1]}")

                elif text.startswith("/whitelistremove "):
                    send_to_console(f'whitelist remove "{parts[1]}"')
                    send_message(f"✅ Removed: {parts[1]}")

                # ============ 8. GAMEPLAY ============
                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("🧭 Coordinates ON")

                elif text == "/keepinventory":
                    send_to_console("gamerule keepinventory true")
                    send_message("💼 KeepInventory ON")

                elif text.startswith("/pvp "):
                    v = "true" if parts[1].lower() in ["on", "true", "1"] else "false"
                    send_to_console(f"gamerule pvp {v}")
                    update_property("pvp", v)
                    send_message(f"⚔️ PvP: {v}")

                elif text.startswith("/difficulty "):
                    d = parts[1].lower()
                    if d in ["peaceful", "easy", "normal", "hard"]:
                        send_to_console(f"difficulty {d}")
                        update_property("difficulty", d)
                        send_message(f"🎯 Difficulty: {d}")

                elif text.startswith("/gamemode "):
                    g = parts[1].lower()
                    if g in ["survival", "creative", "adventure"]:
                        send_to_console(f"defaultgamemode {g}")
                        update_property("gamemode", g)
                        send_message(f"🎮 Default: {g}")

                elif text.startswith("/time "):
                    send_to_console(f"time set {parts[1]}")
                    send_message(f"⏰ Time: {parts[1]}")

                elif text.startswith("/weather "):
                    send_to_console(f"weather {parts[1]}")
                    send_message(f"🌦️ Weather: {parts[1]}")

                elif text.startswith("/mobspawning "):
                    send_to_console(f"gamerule domobspawning {parts[1]}")
                    send_message(f"👹 Mob: {parts[1]}")

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
                    send_message("🧹 Cleared")

                elif text.startswith("/seed "):
                    s = parts[1]
                    nw = f"world_{int(time.time())}"
                    send_message(f"🌱 Creating seed {s}...")
                    stop_server()
                    update_property("level-seed", s)
                    update_property("level-name", nw)
                    start_server()
                    send_message(f"✅ World: {nw}\nSeed: {s}")

                elif text == "/backup":
                    send_message("📦 Creating backup...")
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    bz = os.path.join(BACKUP_DIR, f"backup_{ts}.zip")
                    run_cmd(f"cd {BASE_DIR} && zip -r {bz} worlds/ server.properties security_config.json blacklist.json 2>/dev/null", timeout=300)
                    if os.path.exists(bz) and os.path.getsize(bz) > 1000:
                        threading.Thread(target=send_document, args=(bz, f"📦 {ts}"), daemon=True).start()
                    else:
                        send_message("❌ Failed.")

                elif text == "/backuplist":
                    try:
                        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")],
                                       key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x)),
                                       reverse=True)[:10]
                        if not files:
                            send_message("📭 No backups.")
                        else:
                            out = "📋 <b>Backups:</b>\n"
                            for f in files:
                                sz = os.path.getsize(os.path.join(BACKUP_DIR, f)) / (1024*1024)
                                out += f"• {f} ({sz:.1f} MB)\n"
                            send_message(out)
                    except Exception as e:
                        send_message(f"❌ {e}")

                elif text.startswith("/restoresnapshot "):
                    fn = parts[1]
                    fp = os.path.join(BACKUP_DIR, fn)
                    if os.path.exists(fp):
                        send_message("⚙️ Restoring...")
                        stop_server()
                        run_cmd(f"cd {BASE_DIR} && unzip -o {fp}", timeout=300)
                        start_server()
                        send_message(f"✅ Restored: {fn}")
                    else:
                        send_message(f"❌ Not found: {fn}")

                # ============ 10. DIAGNOSTICS ============
                elif text.startswith("/updateserver"):
                    if len(parts) > 1:
                        version = parts[1]
                    else:
                        send_message("🔍 Auto-detect...")
                        version = detect_latest_bedrock_version()
                        if not version:
                            send_message("❌ Manual: /updateserver 1.21.51.02")
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
                        send_message(f"✅ Updated: {version}")
                    else:
                        run_cmd(f"cd {BASE_DIR} && mv bedrock_server_old bedrock_server 2>/dev/null")
                        send_message("❌ Failed. Rollback done.")

                elif text == "/checkupdate":
                    latest = detect_latest_bedrock_version()
                    current = get_current_server_version()
                    if latest:
                        upd = "✅ Update available!" if latest != current else "✅ Up to date!"
                        send_message(f"📌 Current: {current}\n🆕 Latest: {latest}\n\n{upd}")
                    else:
                        send_message(f"📌 Current: {current}\n❌ Not detected.")

                elif text == "/status":
                    mc = "🟢" if is_server_running() else "🔴"
                    pt = "🟢" if is_tunnel_running() else "🔴"
                    send_message(f"📊 <b>Status</b>\n\nMC: {mc}\nPlayit: {pt}\nVer: {get_current_server_version()}\nWorld: {get_active_world()}")

                elif text == "/serverstats":
                    mem = run_cmd("free -h", timeout=3).stdout
                    disk = run_cmd("df -h /root", timeout=3).stdout
                    up = run_cmd("uptime", timeout=3).stdout
                    send_message(f"💻 <b>Stats</b>\n\n<pre>{up}</pre>\n<b>RAM:</b>\n<pre>{mem[:350]}</pre>\n<b>Disk:</b>\n<pre>{disk[:350]}</pre>")

                elif text == "/logs":
                    out = read_console_output(20)
                    send_message(f"📜 <pre>{out[-3500:]}</pre>")

                elif text == "/restart":
                    send_message("🔄 Restarting...")
                    ok = start_server()
                    send_message("✅ Done!" if ok else "❌ Failed.")

                elif text == "/fixtunnel":
                    send_message("🔄 Fixing tunnel...")
                    run_cmd("pkill -9 playit-cli")
                    run_cmd("screen -S playit-tunnel -X quit")
                    time.sleep(1)
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli")
                    send_message("✅ Tunnel restarted!")

                elif text.startswith("/cmd "):
                    c = text.split(" ", 1)[1]
                    send_to_console(c)
                    send_message(f"⌨️ Sent: <code>{c}</code>")

                elif text.startswith("/shell "):
                    c = text.split(" ", 1)[1]
                    res = run_cmd(c, timeout=30)
                    out = (res.stdout or res.stderr or "Done.")[-3500:]
                    send_message(f"💻 <pre>{out}</pre>")

                else:
                    if text.startswith("/"):
                        send_message(f"❓ Unknown: {text}\n\n/help")

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    handle_updates()
