# mdosnapshots

![License](https://img.shields.io/badge/license-GPL%20v3-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)

mdosnapshots is a versatile Python script designed to manage snapshots for multiple DigitalOcean droplets. It automates the creation, retention, and deletion of snapshots, ensuring your droplets are backed up efficiently and systematically. By leveraging individual YAML configuration files for each droplet, mdosnapshots offers flexibility and scalability, making it an essential tool for developers and system administrators managing multiple DigitalOcean droplets.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Install doctl on Ubuntu 22.04](#1-install-doctl-on-ubuntu-2204)
  - [2. Clone the Repository](#2-clone-the-repository)
  - [3. Set Up a Python Virtual Environment](#3-set-up-a-python-virtual-environment)
  - [4. Install Python Dependencies](#4-install-python-dependencies)
- [Configuration](#configuration)
  - [YAML Configuration Files](#yaml-configuration-files)
  - [Example `config.yaml`](#example-configyaml)
- [Usage](#usage)
  - [Running with Default `config.yaml`](#running-with-default-configyaml)
  - [Running with Multiple YAML Files](#running-with-multiple-yaml-files)
  - [Verbose Mode](#verbose-mode)
- [Logging](#logging)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Manage Multiple Droplets:** Handle snapshots for multiple DigitalOcean droplets, each with its own configuration.
- **Automated Snapshot Creation:** Automatically create snapshots at scheduled intervals.
- **Retention Policy:** Retain a specified number of recent snapshots and delete older ones to manage storage.
- **Retry Mechanism:** Implement retry logic for snapshot deletions to ensure robustness.
- **Flexible Configuration:** Use individual YAML files for each droplet, allowing customized settings.
- **Logging:** Comprehensive logging with options for verbose output to the console.
- **Delay Between Operations:** Introduce delays between managing different droplets to prevent API rate limits.

## Prerequisites

Before using mdosnapshots, ensure you have the following:

- A DigitalOcean account with one or more droplets.
- Access to the terminal on a machine running Ubuntu 22.04.
- Basic knowledge of using the command line and editing configuration files.

## Installation

Follow the steps below to install and set up mdosnapshots on your Ubuntu 22.04 system.

### 1. Install doctl on Ubuntu 22.04

`doctl` is the official command-line tool for managing DigitalOcean resources. mdosnapshots relies on `doctl` to interact with DigitalOcean's API.

#### Step-by-Step Installation:

1. **Update Package List:**

   ```bash
   sudo apt update
   ```

2. **Install Required Dependencies:**

   ```bash
   sudo apt install -y wget apt-transport-https gnupg
   ```

3. **Download and Install doctl:**

   ```bash
   # Download the latest doctl release
   wget https://github.com/digitalocean/doctl/releases/download/v1.94.0/doctl-1.94.0-linux-amd64.tar.gz

   # Extract the downloaded archive
   tar -xzf doctl-1.94.0-linux-amd64.tar.gz

   # Move the doctl binary to /usr/local/bin
   sudo mv doctl /usr/local/bin/

   # Verify the installation
   doctl version
   ```

   *Note:* Replace `v1.94.0` with the latest version number if a newer version is available. You can check the latest release [here](https://github.com/digitalocean/doctl/releases).

4. **Authenticate doctl with Your DigitalOcean Account:**

   Obtain a DigitalOcean API token with the necessary permissions from your [DigitalOcean Control Panel](https://cloud.digitalocean.com/settings/api/tokens). Then, authenticate `doctl`:

   ```bash
   doctl auth init
   ```

   You'll be prompted to enter your API token.

### 2. Clone the Repository

Clone the mdosnapshots repository from GitHub to your local machine:

```bash
git clone https://github.com/drhdev/mdosnapshots.git
cd mdosnapshots
```

### 3. Set Up a Python Virtual Environment

It's recommended to use a virtual environment to manage Python dependencies without affecting your system-wide packages.

1. **Install `venv` if Not Already Installed:**

   ```bash
   sudo apt install -y python3-venv
   ```

2. **Create a Virtual Environment:**

   ```bash
   python3 -m venv venv
   ```

3. **Activate the Virtual Environment:**

   ```bash
   source venv/bin/activate
   ```

   *Note:* Your terminal prompt should now start with `(venv)` indicating the virtual environment is active.

### 4. Install Python Dependencies

With the virtual environment activated, install the required Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

mdosnapshots uses YAML configuration files to manage snapshot settings for each droplet. Each droplet should have its own YAML file containing specific configurations.

### YAML Configuration Files

Each YAML file should define the following keys under the `droplet` section:

- `id`: **(String)** The unique identifier of your DigitalOcean droplet.
- `name`: **(String)** The name of your droplet.
- `api_token`: **(String)** Your DigitalOcean API token with the necessary permissions.
- `retain_last_snapshots`: **(Integer)** The number of recent snapshots to retain. Older snapshots beyond this number will be deleted.
- `delete_retries`: **(Integer)** The number of attempts to delete an old snapshot in case of failures.

#### Directory Structure

It's recommended to store all YAML configuration files in a dedicated directory within the repository for better organization. For example:

```
mdosnapshots/
├── configs/
│   ├── droplet1.yaml
│   ├── droplet2.yaml
│   └── ...
├── mdosnapshots.py
├── README.md
└── ...
```

### Example `config.yaml`

Here's an example of a `config.yaml` file for a single droplet:

```yaml
droplet:
  id: "12345678"
  name: "web-server-1"
  api_token: "your_api_token_1"
  retain_last_snapshots: 3
  delete_retries: 5
```

#### Creating Additional YAML Files

To manage multiple droplets, create separate YAML files for each droplet. For example:

**`droplet2.yaml`:**

```yaml
droplet:
  id: "87654321"
  name: "db-server-1"
  api_token: "your_api_token_2"
  retain_last_snapshots: 5
  delete_retries: 3
```

*Ensure that each YAML file follows the structure shown above and contains valid data.*

## Usage

mdosnapshots can be executed using the Python interpreter. It offers flexibility in specifying which YAML configuration files to use.

### Running with Default `config.yaml`

By default, if no YAML files are specified, DoSnapshots will use `config.yaml`. Ensure that `config.yaml` exists in the script's directory with the correct structure.

**Command:**

```bash
python mdosnapshots.py
```

### Running with Multiple YAML Files

You can specify one or more YAML files to manage multiple droplets. The script will process the droplets in the order the YAML files are provided, introducing a 5-second delay between each to prevent API rate limits.

**Command:**

```bash
python mdosnapshots.py droplet1.yaml droplet2.yaml droplet3.yaml
```

*This command will manage snapshots for `droplet1`, `droplet2`, and `droplet3` sequentially.*

### Running with Specific YAML File (`config.yaml`)

To explicitly run the script with `config.yaml`, use:

```bash
python mdosnapshots.py config.yaml
```

### Verbose Mode

Enable verbose logging to see real-time outputs in the console. This is useful for monitoring the script's progress and debugging.

**Command:**

```bash
python mdosnapshots.py droplet1.yaml droplet2.yaml -v
```

*The `-v` or `--verbose` flag enables detailed logging to the console.*

### Full Example

Assuming you have two YAML configuration files (`droplet1.yaml` and `droplet2.yaml`) in the `configs/` directory:

1. **Navigate to the Script Directory:**

   ```bash
   cd mdosnapshots
   ```

2. **Activate the Virtual Environment:**

   ```bash
   source venv/bin/activate
   ```

3. **Run the Script with YAML Files and Verbose Logging:**

   ```bash
   python mdosnapshots.py configs/droplet1.yaml configs/droplet2.yaml -v
   ```

## Logging

mdosnapshots maintains a log file named `mdosnapshots.log` in the script's directory. This log captures all operations, including snapshot creations, deletions, and any errors encountered.

- **Log Rotation:** The script uses a rotating file handler to prevent the log file from growing indefinitely. Each log file is capped at 5 MB, with up to 5 backup files retained.
- **Verbose Logging:** When the `-v` flag is used, logs are also output to the console for real-time monitoring.

**Example Log Entry:**

```
2024-04-27 10:00:00 - mdosnapshots.py - INFO - Running command: /usr/local/bin/doctl compute snapshot list --resource droplet --format ID,Name,CreatedAt --no-header --access-token abcdef...
2024-04-27 10:00:05 - mdosnapshots.py - INFO - New snapshot created: web-server-1-20240427100000
2024-04-27 10:00:05 - mdosnapshots.py - INFO - Snapshots identified for deletion: ['web-server-1-20240426100000']
2024-04-27 10:00:10 - mdosnapshots.py - INFO - Snapshot deleted: web-server-1-20240426100000
2024-04-27 10:00:10 - mdosnapshots.py - INFO - FINAL_STATUS | SUCCESS | hostname | 2024-04-27 10:00:10 | web-server-1-20240427100000 | 2 snapshots exist
```

## Security Considerations

- **Protect API Tokens:**
  - YAML configuration files contain sensitive API tokens. Ensure these files are stored securely with restricted permissions.
  - **Set File Permissions:**
    ```bash
    chmod 600 configs/*.yaml
    ```
- **Environment Isolation:**
  - Use a virtual environment to manage dependencies and prevent conflicts with system-wide packages.
- **Least Privilege Principle:**
  - Use API tokens with the minimum required permissions to enhance security.
- **Secure Storage:**
  - Avoid committing YAML files with API tokens to version control systems. Consider using environment variables or secret management tools for enhanced security.

## Troubleshooting

**1. `doctl` Not Found Error:**

*Error Message:*
```
ERROR: doctl command not found. Please ensure it is installed and accessible.
```

*Solution:*
- Ensure `doctl` is installed and accessible in your system's PATH.
- Verify the installation by running `doctl version`.
- If not installed, follow the [Installation](#1-install-doctl-on-ubuntu-2204) steps.

**2. YAML File Parsing Errors:**

*Error Message:*
```
ERROR: Error parsing YAML file 'droplet1.yaml': ...
```

*Solution:*
- Check the YAML file for syntax errors.
- Ensure all required fields (`id`, `name`, `api_token`, `retain_last_snapshots`, `delete_retries`) are present under the `droplet` key.
- Use an online YAML validator to verify the structure.

**3. Snapshot Creation Failures:**

*Error Message:*
```
ERROR: Droplet 'web-server-1': Failed to create a new snapshot.
```

*Solution:*
- Verify that the API token has the necessary permissions.
- Ensure the droplet ID and name are correct.
- Check DigitalOcean's status page for any ongoing issues.

**4. Snapshot Deletion Failures:**

*Error Message:*
```
ERROR: Droplet 'web-server-1': Attempt 3 failed to delete snapshot: web-server-1-20240426100000
```

*Solution:*
- Ensure the snapshot ID is correct and the snapshot exists.
- Verify API token permissions.
- Check for any DigitalOcean API rate limits or restrictions.

**5. Log File Not Updating:**

*Solution:*
- Ensure the script has write permissions to the directory where `mdosnapshots.log` is stored.
- Check if the log rotation is causing issues.

## Contributing

Contributions are welcome! If you have suggestions, improvements, or encounter issues, feel free to open an [issue](https://github.com/drhdev/mdosnapshots/issues) or submit a [pull request](https://github.com/drhdev/mdosnapshots/pulls).

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html). You are free to use, modify, and distribute this software under the terms of this license.

---

*Developed by [drhdev](https://github.com/drhdev).*

```
