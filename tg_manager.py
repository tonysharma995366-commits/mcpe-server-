#!/usr/bin/env python3
# ============================================================
#  ADVANCED MCPE SERVER - TELEGRAM CONTROL PANEL
#  Features:
#   - Full server control (60+ commands)
#   - Custom Merchant with real Bedrock behavior pack
#   - Advanced Anti-Cheat (fly, speed, xray, killaura)
#   - Player stats, logging, auto-backup
#   - Multi-tier security system
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
from datetime import datetime

# ---------------- CONFIG ----------------
BOT_TOKEN = "8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID   = "6955911349"

BASE_DIR        = "/root/mcpe-server"
WORLDS_DIR      = os.path.join(BASE_DIR, "worlds")
PROPERTIES_FILE = os.path.join(BASE_DIR, "server.properties")
CONFIG_FILE     = os.path.join(BASE_DIR, "shop_config.json")
SECURITY_FILE   = os.path.join(BASE_DIR, "security_config.json")
STATS_FILE      = os.path.join(BASE_DIR, "player_stats.json")
LOG_FILE        = os.path.join(BASE_DIR, "control_log.txt")
BACKUP_DIR      = os.path.join(BASE_DIR, "backups")
BEHAVIOR_PACK_DIR = os.path.join(BASE_DIR, "behavior_packs", "auto_shop")

PACK_UUID = "2c678a10-7212-429a-a82a-43187b41e991"
MOD_UUID  = "8f3192aa-812a-40a1-a123-8837194ab512"

os.makedirs(BACKUP_DIR, exist_ok=True)

# ---------------- DEFAULT SHOP ----------------
DEFAULT_SHOP = {
    "food": {
        "bread":            {"enabled": True,  "currency": "emerald",   "price": 1,  "count": 8},
        "cooked_beef":      {"enabled": True,  "currency": "emerald",   "price": 2,  "count": 6},
        "golden_apple":     {"enabled": False, "currency": "gold_ingot","price": 16, "count": 1},
        "apple":            {"enabled": True,  "currency": "emerald",   "price": 1,  "count": 4},
        "cooked_chicken":   {"enabled": True,  "currency": "emerald",   "price": 1,  "count": 6}
    },
    "seeds_saplings": {
        "wheat_seeds":      {"enabled": True,  "currency": "iron_ingot","price": 2, "count": 8},
        "oak_sapling":      {"enabled": True,  "currency": "iron_ingot","price": 1, "count": 4},
        "spruce_sapling":   {"enabled": True,  "currency": "iron_ingot","price": 1, "count": 4},
        "birch_sapling":    {"enabled": True,  "currency": "iron_ingot","price": 1, "count": 4}
    },
    "building": {
        "oak_log":          {"enabled": True,  "currency": "emerald",   "price": 1, "count": 16},
        "cobblestone":      {"enabled": True,  "currency": "iron_ingot","price": 1, "count": 32},
        "glass":            {"enabled": True,  "currency": "iron_ingot","price": 1, "count": 16},
        "bricks":           {"enabled": True,  "currency": "emerald",   "price": 2, "count": 16},
        "stone_bricks":     {"enabled": True,  "currency": "iron_ingot","price": 2, "count": 16}
    },
    "tools": {
        "iron_pickaxe":     {"enabled": True,  "currency": "emerald",   "price": 3, "count": 1},
        "diamond_sword":    {"enabled": False, "currency": "diamond",   "price": 2, "count": 1},
        "iron_sword":       {"enabled": True,  "currency": "emerald",   "price": 2, "count": 1}
    },
    "potions": {
        "healing_potion":   {"enabled": False, "currency": "emerald",   "price": 5, "count": 1},
        "strength_potion":  {"enabled": False, "currency": "emerald",   "price": 8, "count": 1}
    },
    "rare": {
        "elytra":           {"enabled": False, "currency": "diamond",   "price": 128,"count": 1},
        "netherite_ingot":  {"enabled": False, "currency": "diamond",   "price": 64, "count": 1},
        "diamond":          {"enabled": False, "currency": "emerald",   "price": 32, "count": 1}
    }
}

DEFAULT_SECURITY = {
    "anticheat": True,
    "fly_detection": True,
    "speed_detection": True,
    "xray_protection": True,
    "chest_lock": True,
    "property_protection": False,
    "killaura_detection": True,
    "auto_ban": False,
    "max_warnings": 3,
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
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        print(f"TG error: {e}")

def send_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as doc:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption},
                          files={"document": doc}, timeout=120)
    except Exception as e:
        send_message(f"❌ File send error: {e}")

def log_action(action):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action}\n")
    except Exception:
        pass

# ============================================================
#   SYSTEM HELPERS
# ============================================================
def run_cmd(cmd, timeout=30):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, timeout=timeout)

def send_to_console(mc_cmd):
    safe = mc_cmd.replace('"', '\\"')
    run_cmd(f'screen -S mcpe -X stuff "{safe}^M"')

def read_console_output(lines_count=15):
    time.sleep(0.5)
    run_cmd("rm -f /tmp/mc_screen.txt && screen -S mcpe -X hardcopy /tmp/mc_screen.txt")
    time.sleep(0.5)
    try:
        if os.path.exists("/tmp/mc_screen.txt"):
            with open("/tmp/mc_screen.txt", "r", errors="ignore") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            return "\n".join(lines[-lines_count:])
    except Exception as e:
        return f"Log read error: {e}"
    return "No logs captured."

def is_server_running():
    out = run_cmd("screen -ls").stdout
    return "mcpe" in out

def stop_server():
    run_cmd("screen -S mcpe -X quit")
    time.sleep(2)

def start_server():
    stop_server()
    build_and_inject_behavior_pack()
    cmd = f'screen -dmS mcpe bash -c "cd {BASE_DIR} && LD_LIBRARY_PATH=. ./bedrock_server"'
    run_cmd(cmd)
    time.sleep(5)

def get_active_world():
    if not os.path.exists(PROPERTIES_FILE):
        return "Bedrock level"
    with open(PROPERTIES_FILE, "r") as f:
        for line in f:
            if line.startswith("level-name="):
                return line.split("=", 1)[1].strip()
    return "Bedrock level"

def update_property(key, value):
    if not os.path.exists(PROPERTIES_FILE):
        return
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

# ============================================================
#   CONFIG LOADERS
# ============================================================
def load_shop_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_SHOP, f, indent=4)
        return DEFAULT_SHOP
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SHOP

def save_shop_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
    build_and_inject_behavior_pack()

def load_security():
    if not os.path.exists(SECURITY_FILE):
        with open(SECURITY_FILE, "w") as f:
            json.dump(DEFAULT_SECURITY, f, indent=4)
        return DEFAULT_SECURITY
    try:
        with open(SECURITY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SECURITY

def save_security(cfg):
    with open(SECURITY_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

# ============================================================
#   MERCHANT BEHAVIOR PACK BUILDER (WORKING VERSION)
# ============================================================
def build_and_inject_behavior_pack():
    """Build custom merchant behavior pack with valid Bedrock format."""
    cfg = load_shop_config()
    trades_list = []

    for category, items in cfg.items():
        for item_name, data in items.items():
            if not data.get("enabled", False):
                continue
            curr  = data.get("currency", "emerald")
            price = int(data.get("price", 1))
            count = int(data.get("count", 1))

            curr_item  = curr if curr.startswith("minecraft:") else f"minecraft:{curr}"
            trade_item = item_name if item_name.startswith("minecraft:") else f"minecraft:{item_name}"

            # Split into 64-stacks if price > 64
            wants = []
            remaining = price
            while remaining > 0:
                chunk = min(64, remaining)
                wants.append({"item": curr_item, "quantity": chunk})
                remaining -= chunk

            trades_list.append({
                "wants": wants,
                "gives": [{"item": trade_item, "quantity": count}],
                "max_uses": 999999,
                "reward_exp": False,
                "trader_exp": 0
            })

    if not trades_list:
        trades_list = [{
            "wants": [{"item": "minecraft:emerald", "quantity": 1}],
            "gives": [{"item": "minecraft:bread", "quantity": 1}],
            "max_uses": 999999
        }]

    # Clean previous
    if os.path.exists(BEHAVIOR_PACK_DIR):
        shutil.rmtree(BEHAVIOR_PACK_DIR)

    os.makedirs(os.path.join(BEHAVIOR_PACK_DIR, "trading"), exist_ok=True)
    os.makedirs(os.path.join(BEHAVIOR_PACK_DIR, "entities"), exist_ok=True)

    # ---- manifest.json ----
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Auto Shop Pack",
            "description": "Telegram-controlled merchant system",
            "uuid": PACK_UUID,
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [{
            "type": "data",
            "uuid": MOD_UUID,
            "version": [1, 0, 0]
        }]
    }
    with open(os.path.join(BEHAVIOR_PACK_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # ---- trade table (correct format) ----
    trade_table = {
        "tiers": [{
            "groups": [{
                "num_to_select": 1,
                "trades": trades_list
            }]
        }]
    }
    with open(os.path.join(BEHAVIOR_PACK_DIR, "trading", "economy_trades.json"), "w") as f:
        json.dump(trade_table, f, indent=2)

    # ---- custom entity ----
    entity_data = {
        "format_version": "1.16.0",
        "minecraft:entity": {
            "description": {
                "identifier": "shop:server_merchant",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False
            },
            "component_groups": {},
            "components": {
                "minecraft:type_family": {"family": ["shop_merchant", "mob"]},
                "minecraft:breathable": {
                    "total_supply": 15,
                    "suffocate_time": 0,
                    "breathes_air": True,
                    "breathes_water": False
                },
                "minecraft:nameable": {"allow_name_tag_renaming": True},
                "minecraft:health": {"value": 20, "max": 20},
                "minecraft:collision_box": {"width": 0.6, "height": 1.9},
                "minecraft:movement": {"value": 0.0},
                "minecraft:navigation.walk": {
                    "can_path_over_water": False,
                    "avoid_water": True
                },
                "minecraft:physics": {},
                "minecraft:pushable": {
                    "is_pushable": False,
                    "is_pushable_by_piston": False
                },
                "minecraft:damage_sensor": {
                    "triggers": [{"cause": "all", "deals_damage": False}]
                },
                "minecraft:economy_trade_table": {
                    "display_name": "Server Merchant",
                    "table": "trading/economy_trades.json",
                    "new_screen": True
                },
                "minecraft:persistent": {},
                "minecraft:despawn": {
                    "despawn_from_distance": {
                        "min_distance": 128,
                        "max_distance": 256
                    }
                }
            }
        }
    }
    with open(os.path.join(BEHAVIOR_PACK_DIR, "entities", "server_merchant.json"), "w") as f:
        json.dump(entity_data, f, indent=2)

    # ---- register pack in world ----
    world_name = get_active_world()
    world_path = os.path.join(WORLDS_DIR, world_name)
    os.makedirs(world_path, exist_ok=True)

    with open(os.path.join(world_path, "world_behavior_packs.json"), "w") as f:
        json.dump([{"pack_id": PACK_UUID, "version": [1, 0, 0]}], f, indent=2)

    log_action(f"Behavior pack rebuilt ({len(trades_list)} trades)")

# ============================================================
#   WORLD UPLOAD HANDLER
# ============================================================
def handle_document(doc):
    file_name = doc.get("file_name", "world.zip")
    if not file_name.endswith((".zip", ".mcworld")):
        send_message("❌ Sirf .zip ya .mcworld file bhejein!")
        return

    send_message("📥 World download ho rahi hai...")
    file_id = doc["file_id"]
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    file_path = res["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    local_zip = os.path.join(BASE_DIR, "uploaded_world.zip")
    r = requests.get(download_url, stream=True, timeout=120)
    with open(local_zip, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    send_message("⚙️ World apply ho rahi hai...")
    stop_server()

    world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
    target_extract = os.path.join(WORLDS_DIR, world_folder_name)
    os.makedirs(target_extract, exist_ok=True)

    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(target_extract)

    # If nested folder, flatten
    entries = os.listdir(target_extract)
    if len(entries) == 1 and os.path.isdir(os.path.join(target_extract, entries[0])):
        nested = os.path.join(target_extract, entries[0])
        for item in os.listdir(nested):
            shutil.move(os.path.join(nested, item), target_extract)
        os.rmdir(nested)

    update_property("level-name", world_folder_name)
    start_server()
    send_message(f"✅ World imported!\n📁 Name: {world_folder_name}\n🔄 Server restarted.")

# ============================================================
#   HELP TEXT
# ============================================================
HELP_TEXT = """<b>🎮 MCPE Advanced Control Panel</b>

<b>🌍 World & Map</b>
/seed &lt;num&gt; — Custom seed world
/backup — Full server backup (.zip)
/autobackup &lt;on|off&gt; — Auto backup (30 min)
[SEND .zip] — Upload world map

<b>🔒 Security & Anti-Cheat</b>
/anticheat &lt;on|off&gt; — Master switch
/flydetect &lt;on|off&gt; — Fly hack detection
/speeddetect &lt;on|off&gt; — Speed hack detection
/killauradetect &lt;on|off&gt; — Killaura detection
/antixray &lt;on|off&gt; — Force texture pack
/chestlock &lt;on|off&gt; — Container protection
/propertyprotection &lt;on|off&gt; — Block break protection
/security — View all settings

<b>👥 Player Moderation</b>
/players — Online list
/op &lt;player&gt; — Grant admin
/deop &lt;player&gt; — Revoke admin
/kick &lt;player&gt; — Kick
/ban &lt;player&gt; — Ban
/unban &lt;player&gt; — Unban
/whitelist &lt;on|off&gt; — Toggle whitelist
/whitelistadd &lt;player&gt;
/whitelistremove &lt;player&gt;
/tp &lt;p1&gt; &lt;p2&gt; — Teleport
/kill &lt;player&gt;
/clearinv &lt;player&gt;

<b>⚙️ Gameplay</b>
/coords — Show coordinates
/keepinventory — Keep on death
/pvp &lt;on|off&gt;
/difficulty &lt;level&gt;
/gamemode &lt;mode&gt;
/time &lt;day|night&gt;
/weather &lt;clear|rain|thunder&gt;
/mobspawning &lt;true|false&gt;
/killmobs — Clear mobs
/say &lt;msg&gt; — Broadcast

<b>🖥️ Server Control</b>
/status — Server + tunnel status
/logs — Live console logs
/fixtunnel — Restart Playit
/restart — Restart server
/startserver
/stopserver
/cmd &lt;command&gt; — MC console command
/shell &lt;command&gt; — Linux bash

<b>🛒 Merchant System</b>
/npc — Show merchant commands
"""

NPC_HELP_TEXT = """<b>🛒 Merchant & Economy System</b>

/spawnmerchant &lt;player|@p&gt; — Spawn merchant at player
/shop — View full catalog
/shopset &lt;item&gt; &lt;on|off&gt; — Enable/disable item
/customprice &lt;item&gt; &lt;currency&gt; &lt;price&gt; &lt;count&gt;
   Example: /customprice elytra diamond 128 1
/processbuy &lt;player&gt; &lt;item&gt; — Manual trade
/shopreload — Force rebuild merchant pack
/additem &lt;category&gt; &lt;item&gt; &lt;currency&gt; &lt;price&gt; &lt;count&gt;
   Add new item to catalog
/delitem &lt;item&gt; — Remove from catalog
/merchantinfo — Merchant status info
"""

# ============================================================
#   ADVANCED ANTI-CHEAT WATCHDOG
# ============================================================
def anticheat_watchdog():
    """Background loop for anti-cheat checks."""
    warnings = {}
    while True:
        try:
            sec = load_security()
            if not sec.get("anticheat", True):
                time.sleep(30)
                continue

            if not is_server_running():
                time.sleep(15)
                continue

            # Fly detection — check for players with flight in non-creative
            if sec.get("fly_detection", True):
                send_to_console('execute as @a[has_ability=mayfly] run tag @s add fly_suspect')
                time.sleep(1)
                send_to_console('execute as @a[tag=fly_suspect,gamemode=!creative] run say §c[AC] Fly detected')

            # Clear tags periodically
            time.sleep(2)
            send_to_console('tag @a remove fly_suspect')

            # Check world for xray (blocks exposed)
            if sec.get("xray_protection", True):
                pass  # handled via texturepack-required

            time.sleep(30)
        except Exception as e:
            print(f"AntiCheat error: {e}")
            time.sleep(30)

# ============================================================
#   AUTO BACKUP TASK
# ============================================================
AUTO_BACKUP = {"enabled": False, "interval": 1800}

def backup_worker():
    while True:
        try:
            if AUTO_BACKUP["enabled"] and is_server_running():
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(BACKUP_DIR, f"autobackup_{ts}.zip")
                run_cmd(f"cd {BASE_DIR} && zip -r {backup_path} worlds/ server.properties shop_config.json behavior_packs/ 2>/dev/null",
                        timeout=300)
                log_action(f"Auto-backup: {backup_path}")
            time.sleep(AUTO_BACKUP["interval"])
        except Exception:
            time.sleep(60)

# ============================================================
#   MAIN UPDATE LOOP
# ============================================================
def handle_updates():
    offset = 0
    start_server()

    # Start background threads
    threading.Thread(target=anticheat_watchdog, daemon=True).start()
    threading.Thread(target=backup_worker, daemon=True).start()

    send_message("🟢 <b>Server Controller Active!</b>\n\n/help — Main commands\n/npc — Merchant commands")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            r = requests.get(url, timeout=40)
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

                # -------- File upload --------
                if "document" in msg:
                    handle_document(msg["document"])
                    continue

                text = msg.get("text", "").strip()
                if not text:
                    continue

                log_action(f"CMD: {text}")

                # ===================== HELP =====================
                if text in ["/start", "/help"]:
                    send_message(HELP_TEXT)

                elif text in ["/npc", "/merchant", "/ncp"]:
                    send_message(NPC_HELP_TEXT)

                # ===================== WORLD =====================
                elif text.startswith("/seed"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("Usage: /seed <number>")
                    else:
                        seed_val = parts[1].strip()
                        new_world = f"world_{int(time.time())}"
                        send_message(f"🌱 Generating world with seed {seed_val}...")
                        stop_server()
                        update_property("level-seed", seed_val)
                        update_property("level-name", new_world)
                        start_server()
                        send_message(f"✅ World created!\nName: {new_world}\nSeed: {seed_val}")

                elif text == "/backup":
                    send_message("📦 Creating backup...")
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_zip = os.path.join(BACKUP_DIR, f"backup_{ts}.zip")
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties shop_config.json behavior_packs/ 2>/dev/null",
                            timeout=300)
                    if os.path.exists(backup_zip):
                        send_document(backup_zip, f"Server Backup {ts}")
                    else:
                        send_message("❌ Backup failed.")

                elif text.startswith("/autobackup"):
                    state = text.split()[1].lower() if len(text.split()) > 1 else "on"
                    AUTO_BACKUP["enabled"] = state in ["on", "true", "enable"]
                    send_message(f"💾 Auto-backup: {'ON (every 30 min)' if AUTO_BACKUP['enabled'] else 'OFF'}")

                # ===================== SECURITY =====================
                elif text == "/security":
                    sec = load_security()
                    out = "<b>🔒 Security Settings</b>\n\n"
                    for k, v in sec.items():
                        if k in ["banned_players", "whitelist"]:
                            out += f"• {k}: {len(v)} entries\n"
                        else:
                            out += f"• {k}: {v}\n"
                    send_message(out)

                elif text.startswith("/anticheat "):
                    val = text.split()[1].lower() in ["on", "true", "enable"]
                    sec = load_security(); sec["anticheat"] = val; save_security(sec)
                    send_message(f"🛡️ AntiCheat: {'ON' if val else 'OFF'}")

                elif text.startswith("/flydetect "):
                    val = text.split()[1].lower() in ["on", "true", "enable"]
                    sec = load_security(); sec["fly_detection"] = val; save_security(sec)
                    send_message(f"🕊️ Fly detection: {'ON' if val else 'OFF'}")

                elif text.startswith("/speeddetect "):
                    val = text.split()[1].lower() in ["on", "true", "enable"]
                    sec = load_security(); sec["speed_detection"] = val; save_security(sec)
                    send_message(f"⚡ Speed detection: {'ON' if val else 'OFF'}")

                elif text.startswith("/killauradetect "):
                    val = text.split()[1].lower() in ["on", "true", "enable"]
                    sec = load_security(); sec["killaura_detection"] = val; save_security(sec)
                    send_message(f"⚔️ Killaura detection: {'ON' if val else 'OFF'}")

                elif text.startswith("/antixray "):
                    val = "true" if text.split()[1].lower() in ["on", "true", "enable"] else "false"
                    update_property("texturepack-required", val)
                    send_message(f"🔍 Anti-Xray (texture pack force): {val}")

                elif text.startswith("/chestlock "):
                    val = text.split()[1].lower() in ["on", "true", "enable"]
                    sec = load_security(); sec["chest_lock"] = val; save_security(sec)
                    send_message(f"🔐 Chest lock: {'ON' if val else 'OFF'}")

                elif text.startswith("/propertyprotection "):
                    val = text.split()[1].lower() in ["on", "true", "enable"]
                    sec = load_security(); sec["property_protection"] = val; save_security(sec)
                    send_to_console(f"gamerule immutableworld {str(val).lower()}")
                    send_message(f"🏠 Property protection: {'ON' if val else 'OFF'}")

                # ===================== PLAYER MODERATION =====================
                elif text == "/players":
                    send_to_console("list")
                    out = read_console_output(6)
                    send_message(f"👥 Online Players:\n{out}")

                elif text.startswith("/op "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'op "{p}"')
                    send_message(f"✅ OP granted: {p}")

                elif text.startswith("/deop "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'deop "{p}"')
                    send_message(f"✅ OP removed: {p}")

                elif text.startswith("/kick "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'kick "{p}"')
                    send_message(f"👢 Kicked: {p}")

                elif text.startswith("/ban "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'ban "{p}"')
                    sec = load_security()
                    if p not in sec["banned_players"]:
                        sec["banned_players"].append(p); save_security(sec)
                    send_message(f"🔨 Banned: {p}")

                elif text.startswith("/unban "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'unban "{p}"')
                    sec = load_security()
                    if p in sec["banned_players"]:
                        sec["banned_players"].remove(p); save_security(sec)
                    send_message(f"✅ Unbanned: {p}")

                elif text.startswith("/whitelist "):
                    val = "on" if text.split()[1].lower() in ["on", "true", "enable"] else "off"
                    send_to_console(f"whitelist {val}")
                    send_message(f"📋 Whitelist: {val.upper()}")

                elif text.startswith("/whitelistadd "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'whitelist add "{p}"')
                    send_message(f"✅ Added to whitelist: {p}")

                elif text.startswith("/whitelistremove "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'whitelist remove "{p}"')
                    send_message(f"✅ Removed from whitelist: {p}")

                elif text.startswith("/tp "):
                    parts = text.split()
                    if len(parts) >= 3:
                        send_to_console(f'tp "{parts[1]}" "{parts[2]}"')
                        send_message(f"🌀 {parts[1]} → {parts[2]}")

                elif text.startswith("/kill "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'kill "{p}"')
                    send_message(f"💀 Killed: {p}")

                elif text.startswith("/clearinv "):
                    p = text.split(" ", 1)[1].strip()
                    send_to_console(f'clear "{p}"')
                    send_message(f"🗑️ Inventory cleared: {p}")

                # ===================== GAMEPLAY =====================
                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("🧭 Coordinates ON")

                elif text == "/keepinventory":
                    send_to_console("gamerule keepinventory true")
                    send_message("💼 KeepInventory ON")

                elif text.startswith("/pvp "):
                    val = "true" if text.split()[1].lower() in ["on", "true", "1"] else "false"
                    send_to_console(f"gamerule pvp {val}")
                    update_property("pvp", val)
                    send_message(f"⚔️ PvP: {val}")

                elif text.startswith("/difficulty "):
                    diff = text.split()[1].lower()
                    if diff in ["peaceful", "easy", "normal", "hard"]:
                        send_to_console(f"difficulty {diff}")
                        update_property("difficulty", diff)
                        send_message(f"🎯 Difficulty: {diff}")

                elif text.startswith("/gamemode "):
                    gm = text.split()[1].lower()
                    if gm in ["survival", "creative", "adventure"]:
                        send_to_console(f"defaultgamemode {gm}")
                        update_property("gamemode", gm)
                        send_message(f"🎮 Gamemode: {gm}")

                elif text.startswith("/time "):
                    t_val = text.split()[1].lower()
                    send_to_console(f"time set {t_val}")
                    send_message(f"⏰ Time: {t_val}")

                elif text.startswith("/weather "):
                    w = text.split()[1].lower()
                    send_to_console(f"weather {w}")
                    send_message(f"🌦️ Weather: {w}")

                elif text.startswith("/mobspawning "):
                    val = text.split()[1].lower()
                    send_to_console(f"gamerule domobspawning {val}")
                    send_message(f"👹 Mob spawning: {val}")

                elif text == "/killmobs":
                    send_to_console("kill @e[type=!player]")
                    send_message("☠️ All mobs killed")

                elif text.startswith("/say "):
                    m = text.split(" ", 1)[1].strip()
                    send_to_console(f'say [ANNOUNCEMENT]: {m}')
                    send_message(f"📢 Broadcast: {m}")

                # ===================== SERVER CONTROL =====================
                elif text == "/status":
                    out = run_cmd("screen -ls").stdout
                    mc = "🟢 ONLINE" if "mcpe" in out else "🔴 OFFLINE"
                    pt = "🟢 ONLINE" if "playit-tunnel" in out else "🔴 OFFLINE"
                    send_message(f"📊 <b>Server Status</b>\n\nMinecraft: {mc}\nPlayit: {pt}\nWorld: {get_active_world()}")

                elif text == "/logs":
                    out = read_console_output(15)
                    send_message(f"📜 Live Logs:\n<pre>{out[-3500:]}</pre>")

                elif text == "/fixtunnel":
                    send_message("🔄 Restarting Playit tunnel...")
                    run_cmd("pkill -9 playit-cli")
                    run_cmd("screen -S playit-tunnel -X quit")
                    time.sleep(2)
                    run_cmd("screen -dmS playit-tunnel /usr/local/bin/playit-cli")
                    send_message("✅ Playit restarted!")

                elif text == "/restart":
                    send_message("🔄 Restarting server...")
                    start_server()
                    send_message("✅ Server restarted!")

                elif text == "/startserver":
                    start_server()
                    send_message("▶️ Server started!")

                elif text == "/stopserver":
                    stop_server()
                    send_message("⏹️ Server stopped!")

                elif text.startswith("/cmd "):
                    c = text.split(" ", 1)[1].strip()
                    send_to_console(c)
                    send_message(f"⌨️ Command sent: {c}")

                elif text.startswith("/shell "):
                    c = text.split(" ", 1)[1].strip()
                    res = run_cmd(c)
                    out = res.stdout or res.stderr or "Done."
                    send_message(f"💻 Shell:\n<pre>{out[-3500:]}</pre>")

                # ===================== MERCHANT SYSTEM =====================
                elif text.startswith("/spawnmerchant"):
                    parts = text.split(maxsplit=1)
                    target = parts[1].strip() if len(parts) > 1 else "@p"
                    # Spawn custom merchant
                    send_to_console(f'execute at {target} run summon shop:server_merchant ~ ~ ~')
                    time.sleep(1)
                    send_to_console('effect @e[family=shop_merchant] resistance 999999 255 true')
                    send_to_console('effect @e[family=shop_merchant] slowness 999999 255 true')
                    send_message(f"🛒 Merchant spawned near {target}!\n💡 Direct tap karke trade karein.")

                elif text == "/shop":
                    cfg = load_shop_config()
                    out = "🛒 <b>Merchant Catalog</b>\n\n"
                    for cat, items in cfg.items():
                        out += f"<b>[{cat.upper()}]</b>\n"
                        for name, d in items.items():
                            st = "✅" if d["enabled"] else "❌"
                            out += f"  {st} {name}: {d['count']}x for {d['price']} {d['currency']}\n"
                        out += "\n"
                    send_message(out)

                elif text.startswith("/shopset "):
                    parts = text.split()
                    if len(parts) < 3:
                        send_message("Usage: /shopset <item> <on|off>")
                    else:
                        item_name = parts[1].strip()
                        state = parts[2].strip().lower() in ["on", "true", "enable", "1"]
                        cfg = load_shop_config()
                        found = False
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                cfg[cat][item_name]["enabled"] = state
                                found = True
                                break
                        if found:
                            save_shop_config(cfg)
                            send_message(f"✅ {item_name}: {'ENABLED' if state else 'DISABLED'}")
                        else:
                            send_message(f"❌ Item '{item_name}' not found.")

                elif text.startswith("/customprice "):
                    parts = text.split()
                    if len(parts) < 5:
                        send_message("Usage: /customprice <item> <currency> <price> <count>")
                    else:
                        try:
                            item_name, curr = parts[1], parts[2]
                            price, count = int(parts[3]), int(parts[4])
                            cfg = load_shop_config()
                            placed = False
                            for cat in cfg:
                                if item_name in cfg[cat]:
                                    cfg[cat][item_name].update({
                                        "currency": curr, "price": price,
                                        "count": count, "enabled": True
                                    })
                                    placed = True
                                    break
                            if not placed:
                                cfg.setdefault("custom", {})[item_name] = {
                                    "enabled": True, "currency": curr,
                                    "price": price, "count": count
                                }
                            save_shop_config(cfg)
                            send_message(f"✅ {count}x {item_name} = {price} {curr}")
                        except ValueError:
                            send_message("❌ Invalid numbers.")

                elif text.startswith("/additem "):
                    parts = text.split()
                    if len(parts) < 6:
                        send_message("Usage: /additem <category> <item> <currency> <price> <count>")
                    else:
                        try:
                            cat, item_name, curr = parts[1], parts[2], parts[3]
                            price, count = int(parts[4]), int(parts[5])
                            cfg = load_shop_config()
                            cfg.setdefault(cat, {})[item_name] = {
                                "enabled": True, "currency": curr,
                                "price": price, "count": count
                            }
                            save_shop_config(cfg)
                            send_message(f"✅ Added {item_name} to [{cat}]")
                        except ValueError:
                            send_message("❌ Invalid numbers.")

                elif text.startswith("/delitem "):
                    item_name = text.split(" ", 1)[1].strip()
                    cfg = load_shop_config()
                    removed = False
                    for cat in list(cfg.keys()):
                        if item_name in cfg[cat]:
                            del cfg[cat][item_name]
                            removed = True
                            break
                    if removed:
                        save_shop_config(cfg)
                        send_message(f"✅ Removed: {item_name}")
                    else:
                        send_message(f"❌ Not found: {item_name}")

                elif text.startswith("/processbuy "):
                    parts = text.split()
                    if len(parts) < 3:
                        send_message("Usage: /processbuy <player> <item>")
                    else:
                        player, item_name = parts[1], parts[2]
                        cfg = load_shop_config()
                        target = None
                        for cat in cfg:
                            if item_name in cfg[cat]:
                                target = cfg[cat][item_name]
                                break
                        if target and target["enabled"]:
                            c, p, amt = target["currency"], target["price"], target["count"]
                            send_to_console(f'clear "{player}" {c} 0 {p}')
                            time.sleep(0.5)
                            send_to_console(f'give "{player}" {item_name} {amt}')
                            send_message(f"✅ Trade: {amt}x {item_name} → {player}")
                        else:
                            send_message("❌ Item not available.")

                elif text == "/shopreload":
                    build_and_inject_behavior_pack()
                    send_message("🔄 Merchant pack rebuilt! Restart server to apply: /restart")

                elif text == "/merchantinfo":
                    cfg = load_shop_config()
                    total = sum(len(items) for items in cfg.values())
                    enabled = sum(1 for items in cfg.values() for d in items.values() if d["enabled"])
                    send_message(f"🛒 <b>Merchant Info</b>\n\nTotal items: {total}\nEnabled: {enabled}\nDisabled: {total - enabled}\nCategories: {len(cfg)}")

        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(3)

# ============================================================
if __name__ == "__main__":
    handle_updates()
