import requests
import time
import logging
import os

# Replace with your Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# DexScreener API endpoint
DEXSCREENER_API_URL = "https://api.dexscreener.com/token-profiles/latest/v1"

# Store last known state of token profiles
last_state = {}

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_token_profiles():
    """Fetch the latest token profiles from DexScreener."""
    try:
        response = requests.get(DEXSCREENER_API_URL)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        return data.get("data", {}).get("profiles", [])  # Extract the list of profiles
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching token profiles: {e}")
        return []

def check_for_updates(new_profiles):
    """Compare new profiles with the last known state to detect updates."""
    updated_tokens = []
    for profile in new_profiles:
        token_address = profile.get("address")
        if token_address in last_state:
            # Compare specific fields (e.g., description, website, socials)
            last_profile = last_state[token_address]
            if (profile.get("info", {}).get("description") != last_profile.get("info", {}).get("description") or
                profile.get("info", {}).get("website") != last_profile.get("info", {}).get("website") or
                profile.get("info", {}).get("socials") != last_profile.get("info", {}).get("socials")):
                updated_tokens.append(profile)
        else:
            # First time seeing this token
            pass
        # Update last known state
        last_state[token_address] = profile
    return updated_tokens

def send_telegram_notification(message):
    """Send a notification via Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Notification sent: {message}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Telegram notification: {e}")

def monitor_token_profiles():
    """Monitor token profiles for updates."""
    logging.info("Starting token profile monitor...")
    while True:
        try:
            # Fetch the latest token profiles
            new_profiles = fetch_token_profiles()
            if not new_profiles:
                logging.warning("No profiles found in the API response.")
                continue

            # Check for updates
            updated_tokens = check_for_updates(new_profiles)
            if updated_tokens:
                for token in updated_tokens:
                    token_name = token.get("name")
                    token_symbol = token.get("symbol")
                    token_address = token.get("address")
                    message = (
                        f"🚀 Token updated: {token_name} ({token_symbol})\n"
                        f"Address: {token_address}\n"
                        f"Description: {token.get('info', {}).get('description')}\n"
                        f"Website: {token.get('info', {}).get('website')}\n"
                        f"Socials: {token.get('info', {}).get('socials')}"
                    )
                    send_telegram_notification(message)

            # Wait before polling again (1 second)
            time.sleep(1)  # 1-second interval (60 requests per minute)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(1)  # Wait before retrying

if __name__ == "__main__":
    monitor_token_profiles()
