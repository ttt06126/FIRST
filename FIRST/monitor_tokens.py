from flask import Flask
import threading
import requests
import time
import logging
import os

# Flask app for health checks
app = Flask(__name__)

@app.route("/health")
def health():
    return "OK", 200

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
        response = requests.get(DEXSCREENER_API_URL, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        # Log the full API response for debugging
        logging.debug(f"API Response: {data}")

        # Handle different response structures
        if isinstance(data, dict):
            if "error" in data:
                logging.error(f"API Error: {data['error']}")
                return []
            elif "data" in data and "profiles" in data["data"]:
                return data["data"]["profiles"]  # Return the list of profiles
            else:
                logging.error("Unexpected API response structure")
                return []
        elif isinstance(data, list):
            # Handle cases where the API returns a list directly
            return data
        else:
            logging.error("Unexpected API response type")
            return []
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
        response = requests.post(url, json=payload, timeout=10)
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

            # Wait before polling again (2 seconds)
            time.sleep(2)  # 2-second interval (30 requests per minute)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(2)  # Wait before retrying

if __name__ == "__main__":
    # Start the Flask app in a separate thread
    port = int(os.getenv("PORT", 5000))  # Use Render's PORT or default to 5000
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port))
    flask_thread.daemon = True
    flask_thread.start()

    # Start the token monitor
    monitor_token_profiles()
