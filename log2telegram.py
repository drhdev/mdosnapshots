#!/usr/bin/env python3
# log2telegram.py
# Version: 0.1
# Author: drhdev
# License: GPLv3
#
# Description:
# This script monitors the 'mdosnapshots.log' file for new FINAL_STATUS entries
# and sends them as formatted messages via Telegram. It ensures that only new entries
# are sent and handles log rotation gracefully. Additionally, it implements a retry
# mechanism for sending messages and formats messages using Markdown for better readability.

import os
import sys
import time
import json
import logging
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configuration
LOG_FILE_PATH = "mdosnapshots.log"  # Path to your log file
STATE_FILE_PATH = "log2telegram.json"  # Path to store the state
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Validate Telegram credentials
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables.")
    sys.exit(1)

# Setup logging for the notifier script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log2telegram.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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

class LogHandler(FileSystemEventHandler):
    """
    Handles file system events for the log file.
    """
    def __init__(self, log_file_path, state: LogState):
        super().__init__()
        self.log_file_path = log_file_path
        self.state = state
        self.file = None
        self.open_log_file()

    def open_log_file(self):
        try:
            self.file = open(self.log_file_path, 'r')
            st = os.fstat(self.file.fileno())
            if self.state.inode != st.st_ino:
                # File has been rotated or is new
                self.state.inode = st.st_ino
                self.state.position = 0
                logger.info("Detected new log file or rotation. Resetting position.")
            self.file.seek(self.state.position)
            logger.debug(f"Opened log file at position {self.state.position}")
        except FileNotFoundError:
            logger.error(f"Log file '{self.log_file_path}' not found. Waiting for it to be created.")
            self.file = None
        except Exception as e:
            logger.error(f"Error opening log file: {e}")
            self.file = None

    def on_modified(self, event):
        if event.src_path.endswith(os.path.basename(self.log_file_path)):
            self.process_new_lines()

    def on_created(self, event):
        if event.src_path.endswith(os.path.basename(self.log_file_path)):
            logger.info(f"Log file '{self.log_file_path}' has been created.")
            self.open_log_file()

    def process_new_lines(self):
        if not self.file:
            self.open_log_file()
            if not self.file:
                return

        try:
            while True:
                line = self.file.readline()
                if not line:
                    break  # No new line
                line = line.strip()
                logger.debug(f"Read line: {line}")
                if line.startswith("FINAL_STATUS |"):
                    self.send_telegram_message(line)
            # Update the state with the current file position
            st = os.fstat(self.file.fileno())
            self.state.position = self.file.tell()
            self.state.inode = st.st_ino
            self.state.save_state(self.state.inode, self.state.position)
        except Exception as e:
            logger.error(f"Error processing new lines: {e}")

    def send_telegram_message(self, message, retries=3, delay=5):
        """
        Sends the given message to Telegram with a retry mechanism.
        """
        formatted_message = self.format_message(message)
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

    def format_message(self, raw_message):
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

def main():
    # Initialize log state
    state = LogState(STATE_FILE_PATH)

    # Initialize event handler
    event_handler = LogHandler(LOG_FILE_PATH, state)

    # Initialize observer
    observer = Observer()
    log_dir = os.path.dirname(os.path.abspath(LOG_FILE_PATH)) or '.'
    observer.schedule(event_handler, path=log_dir, recursive=False)
    observer.start()
    logger.info(f"Started monitoring '{LOG_FILE_PATH}' for FINAL_STATUS entries.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping log notifier...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
