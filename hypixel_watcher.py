import os
import time
import requests

# === CONFIG (read from environment variables) ===
# These are set in Railway (or locally) instead of hard-coding them.

MC_USERNAME = os.environ.get("MC_USERNAME", "YourIGNHere")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "60"))
DISCORD_PING = os.environ.get("DISCORD_PING", "")  # e.g. "<@yourDiscordID>"
HYPIXEL_API_KEY = os.environ.get("HYPIXEL_API_KEY", "")  # from https://developer.hypixel.net/


def get_uuid(username: str) -> str:
    """Get a Minecraft UUID from a username using Mojang API."""
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to get UUID. Status: {resp.status_code}, body: {resp.text}")
    data = resp.json()
    return data["id"]  # UUID without hyphens


def get_hypixel_status(uuid: str) -> bool:
    """
    Returns True if the player is online on Hypixel, False if not.
    Uses the Hypixel /status endpoint (requires API key).
    """
    if not HYPIXEL_API_KEY:
        raise RuntimeError("HYPIXEL_API_KEY is not set. Create one at https://developer.hypixel.net/")

    url = "https://api.hypixel.net/status"  # v2 also exists, but this remains supported
    params = {
        "uuid": uuid,
        "key": HYPIXEL_API_KEY
    }

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to get status. Status: {resp.status_code}, body: {resp.text}")

    data = resp.json()
    if not data.get("success", False):
        raise RuntimeError(f"Hypixel API error: {data}")

    session = data.get("session", {})
    return bool(session.get("online", False))


def send_discord_ping(username: str, online: bool):
    """Send a message to the Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("[ERROR] DISCORD_WEBHOOK_URL is not set.")
        return

    status_text = "just came ONLINE ✅" if online else "just went OFFLINE ❌"
    content = f"{DISCORD_PING} `{username}` {status_text}" if DISCORD_PING else f"`{username}` {status_text}"

    payload = {"content": content}

    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code >= 400:
        print(f"[ERROR] Failed to send Discord webhook: {resp.status_code}, {resp.text}")
    else:
        print("[INFO] Sent Discord ping.")


def main():
    print("[INFO] Starting Hypixel watcher...")

    if not MC_USERNAME or MC_USERNAME == "YourIGNHere":
        print("[ERROR] MC_USERNAME is not set. Set it as an environment variable.")
        return

    try:
        uuid = get_uuid(MC_USERNAME)
        print(f"[INFO] UUID for {MC_USERNAME}: {uuid}")
    except Exception as e:
        print(f"[ERROR] Could not get UUID: {e}")
        return

    last_online = None  # unknown at start

    while True:
        try:
            is_online = get_hypixel_status(uuid)
            print(f"[INFO] {MC_USERNAME} online: {is_online}")

            # Detect OFFLINE -> ONLINE transition
            if last_online is False and is_online is True:
                print("[EVENT] Player just came online! Sending Discord ping.")
                send_discord_ping(MC_USERNAME, True)

            # (Optional) detect ONLINE -> OFFLINE
            # if last_online is True and is_online is False:
            #     print("[EVENT] Player just went offline! Sending Discord ping.")
            #     send_discord_ping(MC_USERNAME, False)

            last_online = is_online

        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
