# Homebox Backup GUI

A graphical application for backing up [Homebox](https://github.com/hay-kot/homebox) instances running on Docker with PostgreSQL databases.

## Overview

This tool provides a user-friendly GUI for creating backups of Homebox instances. It connects to your Homebox server via SSH, identifies the relevant Docker containers, and creates a structured backup containing:

- **Database**: PostgreSQL dump of your Homebox database
- **Media**: All attachment/media files
- **Other Files** (optional): Other data volume contents

## Requirements

### Target Server Requirements

This backup tool is designed for Homebox instances with the following setup:

- **Docker**: Homebox running as a Docker container
- **Database**: PostgreSQL database (also running in Docker)
- **SSH Access**: SSH server running and accessible
- **Disk Space**: Sufficient `/tmp` space for creating backup archives

### Client Requirements

- **Python**: 3.7 or higher
- **SSH Keys**: Configured SSH key-based authentication to the Homebox server (recommended)
- **Dependencies**: See [requirements.txt](requirements.txt)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/Homebox-Backup-GUI.git
cd Homebox-Backup-GUI
```

2. Run the setup script:
```bash
./setup.sh
```

This will create a virtual environment using [uv](https://github.com/astral-sh/uv) and install all dependencies.

**Note**: If you don't have `uv` installed, install it first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## SSH Setup

For the best experience, set up SSH key-based authentication to your Homebox server:

1. Generate SSH keys (if you haven't already):
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

2. Copy your public key to the server:
```bash
ssh-copy-id username@your-homebox-server
```

3. Test the connection:
```bash
ssh username@your-homebox-server
```

You should be able to connect without entering a password.

## Usage

### Starting the Application

Simply run:
```bash
./run.sh
```

Or activate the virtual environment manually and run:
```bash
source .venv/bin/activate
python homebox_backup_gui.py
```

### Backup Process

1. **Connect to Server**
   - Enter your server's hostname/IP address (e.g., 10.0.0.4 for LAN hosts)
   - Enter SSH port (default: 22)
   - Enter your SSH username
   - Click "Connect"
   - Your settings will be saved automatically for future sessions

2. **Select Containers**
   - Click "Scan Containers" to discover running Docker containers
   - Select your Homebox container from the dropdown
   - Select your PostgreSQL container from the dropdown
   - The application will attempt to auto-select containers with "homebox" and "postgres" in their names

3. **Configure Backup Options**
   - Media and Database backups are always included
   - Optionally enable "Other Data Volume Files" to backup additional data
   - Choose where to save the backup locally (default: Downloads folder)

4. **Run Backup**
   - Click "Start Backup"
   - Monitor progress in the output window
   - The application will:
     - Create a temporary backup directory on the server
     - Dump the PostgreSQL database
     - Copy media files
     - Copy other files (if enabled)
     - Create a compressed archive
     - Download the archive to your local machine
     - Clean up the temporary directory (archive remains in `/tmp`)

5. **Server Cleanup** (Optional)
   - After downloading, click "Delete Server Backup" to remove the archive from `/tmp` on the server
   - This frees up disk space but can be done manually later if preferred

## Backup Structure

The downloaded backup archive contains:

```
homebox_backup_YYYYMMDD_HHMMSS.tar.gz
├── database/
│   └── homebox_db.sql          # PostgreSQL dump
├── media/
│   └── [attachment files]      # All media/attachment files
└── other-files/                # (Optional) Other data volume contents
    └── [additional files]
```

## Restoring from Backup

To restore a backup:

1. **Extract the archive**:
```bash
tar -xzf homebox_backup_YYYYMMDD_HHMMSS.tar.gz
```

2. **Restore the database**:
```bash
# Copy SQL dump to PostgreSQL container
docker cp database/homebox_db.sql postgres_container:/tmp/

# Restore the database
docker exec postgres_container psql -U homebox -d homebox -f /tmp/homebox_db.sql
```

3. **Restore media files**:
```bash
# Find the data volume path
docker inspect homebox_container --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}'

# Copy media back
sudo cp -r media/* /path/to/volume/attachments/
```

4. **Restore other files** (if applicable):
```bash
sudo cp -r other-files/* /path/to/volume/
```

## Troubleshooting

### Connection Issues

- **"Permission denied (publickey)"**: Ensure SSH keys are properly configured
- **"Connection refused"**: Check that SSH is running on the server and the port is correct
- **Timeout errors**: Verify network connectivity and firewall settings

### Container Detection Issues

- **"No containers found"**: Ensure Docker containers are running: `docker ps`
- **Wrong containers listed**: Manually select the correct containers from the dropdowns

### Backup Issues

- **"Could not determine data volume path"**: The tool may need adjustment for your specific Homebox setup
- **Database backup fails**: Verify PostgreSQL credentials and container access
- **Insufficient disk space**: Check `/tmp` space on the server: `df -h /tmp`

### Download Issues

- **Slow downloads**: Large media libraries may take time to transfer
- **Download fails**: Check network stability and disk space on local machine

## Security Considerations

- This tool uses SSH for secure communication
- SSH key-based authentication is strongly recommended
- Backup archives contain sensitive data - store them securely
- Consider encrypting backup archives for additional security
- The tool temporarily stores backups in `/tmp` - ensure this directory is secure

## Settings

The application automatically saves your settings to `~/.config/homebox-backup/settings.json`. This includes:

- SSH connection details (host, port, username)
- Backup options (include other files)
- Save location preference

Settings are loaded automatically when you start the application.

## Development

### Project Structure

- `homebox_backup_gui.py`: Main application file
- `requirements.txt`: Python dependencies
- `setup.sh`: Setup script for creating virtual environment
- `run.sh`: Convenience script for running the application
- `.gitignore`: Git ignore rules

### Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Add your license here]

## Credits

Created for backing up [Homebox](https://github.com/hay-kot/homebox) instances.

## Changelog

### Version 1.0.0 (Initial Release)

- SSH connection management
- Docker container auto-detection
- PostgreSQL database backup (pg_dump)
- Media files backup
- Optional data volume backup
- Progress tracking and logging
- Local download of backup archives
- Server-side cleanup functionality
