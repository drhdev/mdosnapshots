#!/usr/bin/env python3
# mdosnapshots.py
# Version: 0.2.3
# Author: drhdev
# License: GPL v3
#
# Description:
# This script manages snapshots for multiple DigitalOcean droplets, including creation, retention, and deletion.
# Configuration is handled via YAML files located in the 'configs' subfolder, allowing individual settings per droplet.

import subprocess
import logging
from logging.handlers import RotatingFileHandler
import datetime
import os
import sys
import yaml
import time
import argparse
from dataclasses import dataclass
from typing import List, Optional

# Constants
CONFIGS_DIR = "configs"
DEFAULT_CONFIG_FILE = os.path.join(CONFIGS_DIR, "config.yaml")
LOG_FILE = "mdosnapshots.log"
DELAY_BETWEEN_DROPLETS = 5  # seconds

@dataclass
class DropletConfig:
    id: str
    name: str
    api_token: str
    retain_last_snapshots: int
    delete_retries: int

class SnapshotManager:
    def __init__(self, config_paths: List[str], verbose: bool = False):
        self.config_paths = config_paths
        self.verbose = verbose
        self.droplets = self.load_configs()
        self.doctl_path = self.get_doctl_path()
        if not self.doctl_path:
            self.error_exit("doctl command not found. Please ensure it is installed and accessible.")
        self.setup_logging()

    def load_configs(self) -> List[DropletConfig]:
        droplets = []
        for path in self.config_paths:
            full_path = os.path.join(CONFIGS_DIR, path)
            if not os.path.exists(full_path):
                self.error_exit(f"Configuration file '{full_path}' does not exist.")
            try:
                with open(full_path, 'r') as f:
                    config = yaml.safe_load(f)
                if 'droplet' not in config:
                    self.error_exit(f"Configuration file '{full_path}' is missing the 'droplet' key.")
                droplet = config['droplet']
                # Validate required fields
                required_fields = ['id', 'name', 'api_token', 'retain_last_snapshots', 'delete_retries']
                for field in required_fields:
                    if field not in droplet:
                        self.error_exit(f"Configuration file '{full_path}' is missing the '{field}' field under 'droplet'.")
                droplets.append(DropletConfig(
                    id=droplet['id'],
                    name=droplet['name'],
                    api_token=droplet['api_token'],
                    retain_last_snapshots=int(droplet['retain_last_snapshots']),
                    delete_retries=int(droplet['delete_retries'])
                ))
            except yaml.YAMLError as e:
                self.error_exit(f"Error parsing YAML file '{full_path}': {e}")
            except ValueError as ve:
                self.error_exit(f"Invalid data type in '{full_path}': {ve}")
        if not droplets:
            self.error_exit("No valid droplet configurations found.")
        return droplets

    def get_doctl_path(self) -> Optional[str]:
        try:
            doctl_paths = subprocess.run("which -a doctl", shell=True, check=True, stdout=subprocess.PIPE).stdout.decode().strip().split('\n')
            for path in doctl_paths:
                if os.path.exists(path):
                    return path
        except subprocess.CalledProcessError:
            pass
        # Fallback
        default_path = "/usr/local/bin/doctl"
        return default_path if os.path.exists(default_path) else None

    def setup_logging(self):
        self.logger = logging.getLogger('mdosnapshots.py')
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        if self.verbose:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def error_exit(self, message: str):
        if hasattr(self, 'logger'):
            self.logger.error(message)
        else:
            print(f"ERROR: {message}", file=sys.stderr)
        sys.exit(1)

    def run_command(self, command: str, api_token: str) -> Optional[str]:
        masked_token = api_token[:6] + '...' + api_token[-6:]
        masked_command = command.replace(api_token, masked_token)
        self.logger.info(f"Executing command: {masked_command}")
        try:
            env = os.environ.copy()
            env["DO_API_TOKEN"] = api_token
            result = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            stdout = result.stdout.decode().strip()
            stderr = result.stderr.decode().strip()
            self.logger.debug(f"Command stdout: {stdout}")
            if stderr:
                self.logger.warning(f"Command stderr: {stderr}")
            return stdout
        except subprocess.CalledProcessError as e:
            stdout = e.stdout.decode().strip() if e.stdout else ""
            stderr = e.stderr.decode().strip() if e.stderr else ""
            self.logger.error(f"Command failed: {stderr}")
            self.logger.debug(f"Failed command output: {stdout}")
            return None

    def get_snapshots(self, droplet: DropletConfig) -> List[dict]:
        command = f"{self.doctl_path} compute snapshot list --resource droplet --format ID,Name,CreatedAt --no-header --access-token {droplet.api_token}"
        snapshots_output = self.run_command(command, droplet.api_token)
        snapshots = []

        if snapshots_output:
            for line in snapshots_output.splitlines():
                parts = line.split(maxsplit=2)
                if len(parts) == 3 and (droplet.id in parts[1] or droplet.name in parts[1]):
                    snapshot_id, snapshot_name, created_at_str = parts
                    try:
                        created_at = datetime.datetime.fromisoformat(created_at_str.replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
                        snapshots.append({"id": snapshot_id, "name": snapshot_name, "created_at": created_at})
                        self.logger.debug(f"Droplet '{droplet.name}': Snapshot found: {snapshot_name} (ID: {snapshot_id}) created at {created_at}")
                    except ValueError as ve:
                        self.logger.error(f"Droplet '{droplet.name}': Invalid date format for snapshot '{snapshot_name}': {created_at_str}")
        else:
            self.logger.error(f"Droplet '{droplet.name}': No snapshots retrieved or an error occurred during retrieval.")

        return snapshots

    def identify_snapshots_to_delete(self, droplet: DropletConfig, snapshots: List[dict], retain: int) -> List[dict]:
        snapshots.sort(key=lambda x: x['created_at'], reverse=True)
        to_delete = snapshots[retain:]
        self.logger.info(f"Droplet '{droplet.name}': Identified {len(to_delete)} snapshot(s) for deletion: {[snap['name'] for snap in to_delete]}")
        return to_delete

    def create_snapshot(self, droplet: DropletConfig) -> Optional[str]:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        snapshot_name = f"{droplet.name}-{timestamp}"
        command = f"{self.doctl_path} compute droplet-action snapshot {droplet.id} --snapshot-name {snapshot_name} --wait --access-token {droplet.api_token}"
        if self.run_command(command, droplet.api_token):
            self.logger.info(f"Droplet '{droplet.name}': New snapshot created: {snapshot_name}")
            return snapshot_name
        else:
            self.logger.error(f"Droplet '{droplet.name}': Failed to create a new snapshot.")
            return None

    def delete_snapshots(self, droplet: DropletConfig, snapshots: List[dict]):
        for snap in snapshots:
            for attempt in range(1, droplet.delete_retries + 1):
                command = f"{self.doctl_path} compute snapshot delete {snap['id']} --force --access-token {droplet.api_token}"
                result = self.run_command(command, droplet.api_token)
                if result is not None:
                    if "404" in result:
                        self.logger.warning(f"Droplet '{droplet.name}': Snapshot not found (likely already deleted): {snap['name']}. Treating as successful deletion.")
                        break
                    else:
                        self.logger.info(f"Droplet '{droplet.name}': Snapshot deleted: {snap['name']}")
                        break
                else:
                    self.logger.error(f"Droplet '{droplet.name}': Attempt {attempt} failed to delete snapshot: {snap['name']}")
                    if attempt < droplet.delete_retries:
                        self.logger.info(f"Droplet '{droplet.name}': Retrying deletion of snapshot '{snap['name']}' after delay...")
                        time.sleep(5)  # Wait before retrying
                    else:
                        self.logger.error(f"Droplet '{droplet.name}': Failed to delete snapshot after {droplet.delete_retries} attempts: {snap['name']}")

    def write_final_status(self, droplet: DropletConfig, snapshot_name: str, total_snapshots: int, status: str):
        hostname = os.uname().nodename
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_status_message = f"FINAL_STATUS | mdosnapshots.py | {droplet.name} | {status.upper()} | {hostname} | {timestamp} | {snapshot_name} | {total_snapshots} snapshots exist"
        self.logger.info(final_status_message)

    def manage_snapshots_for_droplet(self, droplet: DropletConfig):
        self.logger.info(f"--- Managing droplet '{droplet.name}' (ID: {droplet.id}) ---")
        self.logger.info(f"Configuration: Retain last {droplet.retain_last_snapshots} snapshot(s). New snapshots will be named as '{droplet.name}-<timestamp>'.")

        # Retrieve existing snapshots
        snapshots = self.get_snapshots(droplet)

        # Identify snapshots to delete based on retention policy
        to_delete = self.identify_snapshots_to_delete(droplet, snapshots, droplet.retain_last_snapshots)

        # Create a new snapshot
        snapshot_name = self.create_snapshot(droplet)

        # Delete old snapshots
        if to_delete:
            self.delete_snapshots(droplet, to_delete)
        else:
            self.logger.info(f"Droplet '{droplet.name}': No snapshots to delete based on retention policy.")

        # Re-fetch snapshots after creation and deletion to get the updated count
        updated_snapshots = self.get_snapshots(droplet)
        total_snapshots = len(updated_snapshots)

        # Write final status to the log
        if snapshot_name:
            status = "success"
        else:
            status = "failure"
        self.write_final_status(droplet, snapshot_name if snapshot_name else "none", total_snapshots, status)

        self.logger.info(f"--- Completed snapshot management for droplet '{droplet.name}' ---\n")

    def run(self):
        for idx, droplet in enumerate(self.droplets):
            try:
                self.manage_snapshots_for_droplet(droplet)
                if idx < len(self.droplets) - 1:
                    self.logger.info(f"Waiting for {DELAY_BETWEEN_DROPLETS} seconds before processing the next droplet...")
                    time.sleep(DELAY_BETWEEN_DROPLETS)
            except Exception as e:
                self.logger.error(f"An unexpected error occurred for droplet '{droplet.name}': {e}")

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage snapshots for multiple DigitalOcean droplets.")
    parser.add_argument(
        'configs',
        nargs='*',
        help=f"YAML configuration files for droplets located in the '{CONFIGS_DIR}' directory. Defaults to all .yaml files in the directory if not specified."
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging to the console."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    # Check if the configs directory exists
    if not os.path.isdir(CONFIGS_DIR):
        print(f"ERROR: The configuration directory '{CONFIGS_DIR}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if args.configs:
        config_files = args.configs
    else:
        # Get all .yaml files in the configs directory, sorted alphabetically
        config_files = sorted(f for f in os.listdir(CONFIGS_DIR) if f.endswith('.yaml'))
        if not config_files:
            print(f"ERROR: No '.yaml' configuration files found in the '{CONFIGS_DIR}' directory.", file=sys.stderr)
            sys.exit(1)

    # Initialize the SnapshotManager with the provided configuration files
    manager = SnapshotManager(config_paths=config_files, verbose=args.verbose)
    manager.run()

if __name__ == "__main__":
    main()
