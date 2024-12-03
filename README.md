# mdosnapshots - multiple Digitalocean snapshots

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

`mdosnapshots` ("multiple Digitalocean snapshots") is a Python-based tool designed to manage snapshots for multiple DigitalOcean Droplets. It automates the creation, retention, and deletion of snapshots, ensuring your droplets are backed up efficiently. Additionally, it integrates with Telegram to notify you of the snapshot operations' status, providing real-time updates directly to your messaging app.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Setting Up Cronjobs](#setting-up-cronjobs)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automated Snapshot Management**: Schedule regular snapshots for your DigitalOcean Droplets.
- **Retention Policy**: Define how many recent snapshots to retain and automatically delete older ones.
- **Telegram Notifications**: Receive real-time updates on snapshot operations via Telegram.
- **Flexible Configuration**: Manage multiple droplets with individual settings using YAML configuration files.
- **Logging**: Detailed logging with log rotation to monitor operations and troubleshoot issues.

## Prerequisites

- **Python 3.7+**
- **DigitalOcean Account** with Droplets and API Tokens
- **doctl**: DigitalOcean command-line tool installed and configured
- **Telegram Bot**: A Telegram bot token and chat ID for sending notifications

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/drhdev/mdosnapshots.git
   cd mdosnapshots
   ```

2. **Create a Virtual Environment (Optional but Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install `doctl`**

   Follow the official [doctl installation guide](https://docs.digitalocean.com/reference/doctl/how-to/install/) to install `doctl` on your system.

## Configuration

1. **Environment Variables**

   Create a `.env` file in the root directory of the repository based on the provided `env.example`:

   ```bash
   cp env.example .env
   ```

   Edit the `.env` file to include your Telegram Bot Token and Chat ID:

   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

2. **Droplet Configuration**

   Navigate to the `configs` directory and create or edit YAML configuration files for each droplet. Example configurations are provided as `droplet1.yaml` and `droplet2.yaml`.

   ```yaml
   droplet:
     id: "your-digitalocean-droplet-id-1" # e.g. 33345678
     name: "your-digitalocean-droplet-name-1" # e.g. wordpress-ubuntu-s-1vcpu-1gb-nyc2-01
     api_token: "your_digitalocean_api_token_1"
     retain_last_snapshots: 3
     delete_retries: 5
   ```

   - **id**: The unique identifier of your droplet.
   - **name**: The name of your droplet.
   - **api_token**: Your DigitalOcean API token with appropriate permissions.
   - **retain_last_snapshots**: Number of recent snapshots to retain.
   - **delete_retries**: Number of retries for deleting snapshots in case of failure.

## Usage

### Managing Snapshots

To manually run the snapshot management script:

```bash
python mdosnapshots.py -v
```

- **Options**:
  - `-v`, `--verbose`: Enable verbose logging to the console.
  - Specify specific configuration files by listing them as arguments.

Example:

```bash
python mdosnapshots.py droplet1.yaml droplet2.yaml -v
```

### Sending Log Notifications to Telegram

After running the snapshot script, use the log notifier to send the latest status to Telegram:

```bash
python log2telegram.py -v
```

- **Options**:
  - `-v`, `--verbose`: Enable verbose output to the console.
  - `-d`, `--delay`: Delay in seconds between sending multiple Telegram messages (default: 10 seconds).

Example:

```bash
python log2telegram.py --verbose --delay 15
```

## Setting Up Cronjobs

To automate the snapshot management and notification process, set up cronjobs that run both scripts sequentially.

### Example Cronjob

1. **Open the Crontab Editor**

   ```bash
   crontab -e
   ```

2. **Add the Following Cronjob**

   The following example schedules the snapshot process to run daily at 2:00 AM and immediately sends a Telegram notification after snapshots are managed.

   ```cron
   0 2 * * * PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin; cd /path/to/mdosnapshots && /path/to/mdosnapshots/venv/bin/python mdosnapshots.py >> mdosnapshots_cron.log 2>&1 && /path/to/mdosnapshots/venv/bin/python log2telegram.py >> log2telegram_cron.log 2>&1
   ```

   - **Replace `/path/to/mdosnapshots`** with the actual path to your `mdosnapshots` repository.
   - **Replace `/path/to/modsnapshots/venv/bin/python`** with the path to your Python executable, especially if using a virtual environment.
   - **Logging**: The output of each script is appended to separate cron logs for troubleshooting.

3. **Save and Exit**

   Save the crontab file and exit the editor. The cronjob is now scheduled to run automatically.

## Logging

- **Snapshot Manager Log**: `mdosnapshots.log` – Logs detailed information about snapshot operations.
- **Telegram Notifier Log**: `log2telegram.log` – Logs the activities of sending messages to Telegram.
- **Cronjob Logs**: `mdosnapshots_cron.log` & `log2telegram_cron.log` – Capture the output of cron-executed scripts.

Logs are managed with log rotation to prevent uncontrolled growth.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
