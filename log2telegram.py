#!/usr/bin/env python3
# log2telegram.py
# Version: 0.1.1
# Author: drhdev
# License: GPLv3
#
# Description:
# This script checks the 'mdosnapshots.log' file for new FINAL_STATUS entries,
# sends them as formatted messages via Telegram, and then exits. It ensures
# that only new entries are sent by tracking the last read position and inode.

import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

from logging.handlers import RotatingFileHandler

# Load environment variables from .env if present
load_dotenv()

# Configuration
LOG_FILE_PATH = "mdosnapshots.log"  # Path to your log file
STATE_FILE_PATH = "log_notifier_state.json"  # Path to store the state
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Validate Telegram credentials
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables.")
    sys.exit(1)

# Set up logging
log_filename = 'log2telegram.log'
logger = logging.getLogger('log2telegram.py')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(log_filename, maxBytes=5*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class LogState:
    """
    Manages the state of the log file to track the last read position and inode.
    """
    def __init__(self, state_file):
        self.state_file = state_file
        self.inode = None
        self.position = 0
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.inode = data.get("inode")
                    self.position = data.get("position", 0)
                logger.debug(f"Loaded state: inode={self.inode}, position={self.position}")
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
        else:
            logger.debug("No existing state file found. Starting fresh.")

    def save_state(self, inode, position):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({"inode": inode, "position": position}, f)
            logger.debug(f"Saved state: inode={inode}, position={position}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

def send_telegram_message(message, retries=3, delay=5):
    """
    Sends the given message to Telegram with a retry mechanism.
    """
    formatted_message = format_message(message)
    for attempt in range(1, retries + 1):
        try:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": formatted_message,
                "parse_mode": "Markdown"  # Using Markdown for better formatting
            }
            response = requests.post(TELEGRAM_API_URL, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Sent Telegram message: {formatted_message}")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Exception occurred while sending Telegram message: {e}")
        if attempt < retries:
            logger.info(f"Retrying in {delay} seconds... (Attempt {attempt}/{retries})")
            time.sleep(delay)
    logger.error(f"Failed to send Telegram message after {retries} attempts.")
    return False

def format_message(raw_message):
    """
    Formats the raw FINAL_STATUS log entry into a Markdown message for Telegram.
    Example Input:
        FINAL_STATUS | mdosnapshots.py | example.com | SUCCESS | hostname | 2024-12-02 13:32:34 | example.com-20241202133213 | 3 snapshots exist
    Example Output:
        *FINAL_STATUS*
        *Script:* `mdosnapshots.py`
        *Droplet:* `example.com`
        *Status:* `SUCCESS`
        *Hostname:* `hostname`
        *Timestamp:* `2024-12-02 13:32:34`
        *Snapshot:* `example.com-20241202133213`
        *Total Snapshots:* `3 snapshots exist`
    """
    parts = raw_message.split(" | ")
    if len(parts) != 8:
        logger.warning(f"Unexpected FINAL_STATUS format: {raw_message}")
        return raw_message  # Return as is if format is unexpected

    _, script_name, droplet_name, status, hostname, timestamp, snapshot_name, snapshot_info = parts

    formatted_message = (
        f"*FINAL_STATUS*\n"
        f"*Script:* `{script_name}`\n"
        f"*Droplet:* `{droplet_name}`\n"
        f"*Status:* `{status}`\n"
        f"*Hostname:* `{hostname}`\n"
        f"*Timestamp:* `{timestamp}`\n"
        f"*Snapshot:* `{snapshot_name}`\n"
        f"*Total Snapshots:* `{snapshot_info}`"
    )
    return formatted_message

def process_log(state: LogState):
    """
    Processes the log file for new FINAL_STATUS entries and sends them via Telegram.
    """
    if not os.path.exists(LOG_FILE_PATH):
        logger.error(f"Log file '{LOG_FILE_PATH}' does not exist.")
        return

    try:
        with open(LOG_FILE_PATH, 'r') as f:
            st = os.fstat(f.fileno())
            current_inode = st.st_ino
            if state.inode != current_inode:
                # Log file has been rotated or is new
                logger.info("Detected new log file or rotation. Resetting position.")
                state.position = 0
                state.inode = current_inode

            f.seek(state.position)
            lines = f.readlines()
            if not lines:
                logger.info("No new lines to process.")
                return

            logger.info(f"Processing {len(lines)} new line(s).")
            for line in lines:
                line = line.strip()
                if line.startswith("FINAL_STATUS |"):
                    success = send_telegram_message(line)
                    if not success:
                        logger.error(f"Failed to send Telegram message for line: {line}")

            # Update the state with the current file position
            state.position = f.tell()
            state.inode = current_inode
            state.save_state(state.inode, state.position)

    except Exception as e:
        logger.error(f"Error processing log file: {e}")

def main():
    # Initialize log state
    state = LogState(STATE_FILE_PATH)

    # Process the log file
    process_log(state)

if __name__ == "__main__":
    main()
