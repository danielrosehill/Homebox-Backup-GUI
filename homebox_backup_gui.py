#!/usr/bin/env python3
"""
Homebox Backup GUI
A graphical application for backing up Homebox instances running on Docker with PostgreSQL.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import paramiko
from scp import SCPClient
import os
import threading
import re
import json
from datetime import datetime
from pathlib import Path


class HomeboxBackupGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Homebox Backup Manager")
        self.root.geometry("900x700")

        # Settings file path
        self.settings_file = Path.home() / ".config" / "homebox-backup" / "settings.json"
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # SSH connection
        self.ssh_client = None
        self.remote_backup_path = None

        # Container info
        self.homebox_container = None
        self.postgres_container = None
        self.data_volume_path = None

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the main user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Homebox Backup Manager",
                               font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Connection Frame
        self.setup_connection_frame(main_frame)

        # Container Selection Frame
        self.setup_container_frame(main_frame)

        # Backup Options Frame
        self.setup_backup_options_frame(main_frame)

        # Progress Frame
        self.setup_progress_frame(main_frame)

        # Action Buttons
        self.setup_action_buttons(main_frame)

    def setup_connection_frame(self, parent):
        """Setup SSH connection configuration section."""
        conn_frame = ttk.LabelFrame(parent, text="SSH Connection", padding="10")
        conn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        conn_frame.columnconfigure(1, weight=1)

        # Host
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.host_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.host_var).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # Port
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=10).grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)

        # Username
        ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.username_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.username_var).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_ssh)
        self.connect_btn.grid(row=1, column=2, columnspan=2, pady=2, padx=5)

        # Status
        self.connection_status = ttk.Label(conn_frame, text="Not Connected", foreground="red")
        self.connection_status.grid(row=2, column=0, columnspan=4, pady=5)

    def setup_container_frame(self, parent):
        """Setup container selection section."""
        self.container_frame = ttk.LabelFrame(parent, text="Container Selection", padding="10")
        self.container_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        self.container_frame.columnconfigure(1, weight=1)

        # Initially disabled
        self.set_container_frame_state('disabled')

        # Homebox container
        ttk.Label(self.container_frame, text="Homebox Container:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.homebox_container_var = tk.StringVar()
        self.homebox_combo = ttk.Combobox(self.container_frame, textvariable=self.homebox_container_var, state='readonly')
        self.homebox_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # PostgreSQL container
        ttk.Label(self.container_frame, text="PostgreSQL Container:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.postgres_container_var = tk.StringVar()
        self.postgres_combo = ttk.Combobox(self.container_frame, textvariable=self.postgres_container_var, state='readonly')
        self.postgres_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # Refresh containers button
        self.refresh_btn = ttk.Button(self.container_frame, text="Scan Containers", command=self.scan_containers)
        self.refresh_btn.grid(row=2, column=0, columnspan=2, pady=5)

    def setup_backup_options_frame(self, parent):
        """Setup backup options section."""
        self.options_frame = ttk.LabelFrame(parent, text="Backup Options", padding="10")
        self.options_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        # Initially disabled
        self.set_options_frame_state('disabled')

        # Media (always checked, disabled)
        self.backup_media_var = tk.BooleanVar(value=True)
        media_cb = ttk.Checkbutton(self.options_frame, text="Media Files (always included)",
                                   variable=self.backup_media_var, state='disabled')
        media_cb.grid(row=0, column=0, sticky=tk.W, pady=2)

        # Database (always checked, disabled)
        self.backup_db_var = tk.BooleanVar(value=True)
        db_cb = ttk.Checkbutton(self.options_frame, text="Database (always included)",
                               variable=self.backup_db_var, state='disabled')
        db_cb.grid(row=1, column=0, sticky=tk.W, pady=2)

        # Other files (optional)
        self.backup_other_var = tk.BooleanVar(value=False)
        self.backup_other_var.trace_add('write', lambda *args: self.save_settings())
        self.other_cb = ttk.Checkbutton(self.options_frame, text="Other Data Volume Files (optional)",
                                       variable=self.backup_other_var)
        self.other_cb.grid(row=2, column=0, sticky=tk.W, pady=2)

        # Save location
        ttk.Label(self.options_frame, text="Save Backup To:").grid(row=3, column=0, sticky=tk.W, pady=(10, 2))

        save_frame = ttk.Frame(self.options_frame)
        save_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=2)
        save_frame.columnconfigure(0, weight=1)

        self.save_path_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(save_frame, textvariable=self.save_path_var).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(save_frame, text="Browse...", command=self.browse_save_location).grid(row=0, column=1)

    def setup_progress_frame(self, parent):
        """Setup progress display section."""
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Output text
        self.output_text = scrolledtext.ScrolledText(progress_frame, height=10, state='disabled')
        self.output_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure main_frame row weight for text expansion
        parent.rowconfigure(4, weight=1)

    def setup_action_buttons(self, parent):
        """Setup action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=10)
        button_frame.columnconfigure(0, weight=1)

        # Button container for centering
        btn_container = ttk.Frame(button_frame)
        btn_container.grid(row=0, column=0)

        # Start backup button
        self.backup_btn = ttk.Button(btn_container, text="Start Backup",
                                     command=self.start_backup, state='disabled')
        self.backup_btn.grid(row=0, column=0, padx=5)

        # Delete server backup button
        self.delete_btn = ttk.Button(btn_container, text="Delete Server Backup",
                                     command=self.delete_server_backup, state='disabled')
        self.delete_btn.grid(row=0, column=1, padx=5)

    def set_container_frame_state(self, state):
        """Enable or disable container frame widgets."""
        for child in self.container_frame.winfo_children():
            if isinstance(child, (ttk.Combobox, ttk.Button)):
                child.configure(state=state)

    def set_options_frame_state(self, state):
        """Enable or disable options frame widgets."""
        self.other_cb.configure(state=state)

    def log_output(self, message):
        """Add a message to the output text widget."""
        self.output_text.configure(state='normal')
        self.output_text.insert(tk.END, f"{message}\n")
        self.output_text.see(tk.END)
        self.output_text.configure(state='disabled')

    def connect_ssh(self):
        """Connect to the remote server via SSH."""
        host = self.host_var.get().strip()
        username = self.username_var.get().strip()

        if not host or not username:
            messagebox.showerror("Error", "Please enter both host and username")
            return

        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        self.log_output(f"Connecting to {username}@{host}:{port}...")
        self.connect_btn.configure(state='disabled')

        # Run connection in a thread to avoid freezing GUI
        thread = threading.Thread(target=self._do_ssh_connect, args=(host, port, username))
        thread.daemon = True
        thread.start()

    def _do_ssh_connect(self, host, port, username):
        """Actual SSH connection (runs in thread)."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Try to use SSH keys first
            self.ssh_client.connect(hostname=host, port=port, username=username,
                                   look_for_keys=True, allow_agent=True)

            self.root.after(0, self._connection_success)

        except Exception as e:
            self.root.after(0, lambda: self._connection_failed(str(e)))

    def _connection_success(self):
        """Called when SSH connection succeeds."""
        self.log_output("Connected successfully!")
        self.connection_status.configure(text="Connected", foreground="green")
        self.set_container_frame_state('normal')
        self.connect_btn.configure(state='normal')
        self.save_settings()

    def _connection_failed(self, error):
        """Called when SSH connection fails."""
        self.log_output(f"Connection failed: {error}")
        messagebox.showerror("Connection Error", f"Failed to connect:\n{error}")
        self.connection_status.configure(text="Not Connected", foreground="red")
        self.connect_btn.configure(state='normal')
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

    def scan_containers(self):
        """Scan for Docker containers on the remote server."""
        if not self.ssh_client:
            messagebox.showerror("Error", "Not connected to server")
            return

        self.log_output("Scanning for Docker containers...")
        self.refresh_btn.configure(state='disabled')

        thread = threading.Thread(target=self._do_scan_containers)
        thread.daemon = True
        thread.start()

    def _do_scan_containers(self):
        """Scan for containers (runs in thread)."""
        try:
            # Get list of running containers
            stdin, stdout, stderr = self.ssh_client.exec_command("docker ps --format '{{.ID}}|{{.Names}}|{{.Image}}'")
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            if error:
                self.root.after(0, lambda: self.log_output(f"Warning: {error}"))

            containers = []
            for line in output.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        container_id, name, image = parts
                        containers.append({
                            'id': container_id,
                            'name': name,
                            'image': image,
                            'display': f"{name} ({image})"
                        })

            if not containers:
                self.root.after(0, lambda: messagebox.showwarning("No Containers",
                                                                  "No running Docker containers found"))
                self.root.after(0, lambda: self.refresh_btn.configure(state='normal'))
                return

            self.root.after(0, lambda: self._update_container_lists(containers))

        except Exception as e:
            self.root.after(0, lambda: self.log_output(f"Error scanning containers: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to scan containers:\n{e}"))
            self.root.after(0, lambda: self.refresh_btn.configure(state='normal'))

    def _update_container_lists(self, containers):
        """Update container dropdown lists."""
        self.log_output(f"Found {len(containers)} running containers")

        container_displays = [c['display'] for c in containers]

        # Store container info for later reference
        self.containers_info = containers

        # Update Homebox container list
        self.homebox_combo['values'] = container_displays
        if container_displays:
            # Try to auto-select homebox container
            for i, c in enumerate(containers):
                if 'homebox' in c['name'].lower() or 'homebox' in c['image'].lower():
                    self.homebox_combo.current(i)
                    break
            else:
                self.homebox_combo.current(0)

        # Update PostgreSQL container list
        self.postgres_combo['values'] = container_displays
        if container_displays:
            # Try to auto-select postgres container
            for i, c in enumerate(containers):
                if 'postgres' in c['name'].lower() or 'postgres' in c['image'].lower():
                    self.postgres_combo.current(i)
                    break
            else:
                self.postgres_combo.current(0)

        self.refresh_btn.configure(state='normal')
        self.set_options_frame_state('normal')
        self.backup_btn.configure(state='normal')

    def browse_save_location(self):
        """Browse for save location."""
        directory = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if directory:
            self.save_path_var.set(directory)
            self.save_settings()

    def start_backup(self):
        """Start the backup process."""
        # Validate selections
        if not self.homebox_container_var.get() or not self.postgres_container_var.get():
            messagebox.showerror("Error", "Please select both containers")
            return

        # Get selected containers
        homebox_idx = self.homebox_combo.current()
        postgres_idx = self.postgres_combo.current()

        self.homebox_container = self.containers_info[homebox_idx]
        self.postgres_container = self.containers_info[postgres_idx]

        self.log_output("=" * 50)
        self.log_output("Starting backup process...")
        self.log_output(f"Homebox container: {self.homebox_container['name']}")
        self.log_output(f"PostgreSQL container: {self.postgres_container['name']}")
        self.log_output(f"Include other files: {self.backup_other_var.get()}")

        # Disable buttons
        self.backup_btn.configure(state='disabled')
        self.progress_var.set(0)

        # Run backup in thread
        thread = threading.Thread(target=self._do_backup)
        thread.daemon = True
        thread.start()

    def _do_backup(self):
        """Perform the backup (runs in thread)."""
        try:
            # Step 1: Get data volume path
            self.root.after(0, lambda: self.log_output("Step 1: Finding data volume..."))
            self.root.after(0, lambda: self.progress_var.set(5))

            volume_path = self._get_volume_path()
            if not volume_path:
                raise Exception("Could not determine data volume path")

            self.root.after(0, lambda: self.log_output(f"Data volume path: {volume_path}"))

            # Step 2: Create temporary directory
            self.root.after(0, lambda: self.log_output("Step 2: Creating temporary backup directory..."))
            self.root.after(0, lambda: self.progress_var.set(10))

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"homebox_backup_{timestamp}"
            temp_dir = f"/tmp/{backup_name}"

            self._execute_command(f"mkdir -p {temp_dir}/database {temp_dir}/media")
            if self.backup_other_var.get():
                self._execute_command(f"mkdir -p {temp_dir}/other-files")

            # Step 3: Backup database
            self.root.after(0, lambda: self.log_output("Step 3: Backing up PostgreSQL database..."))
            self.root.after(0, lambda: self.progress_var.set(20))

            self._backup_database(temp_dir)

            # Step 4: Backup media
            self.root.after(0, lambda: self.log_output("Step 4: Backing up media files..."))
            self.root.after(0, lambda: self.progress_var.set(40))

            self._backup_media(volume_path, temp_dir)

            # Step 5: Backup other files (if requested)
            if self.backup_other_var.get():
                self.root.after(0, lambda: self.log_output("Step 5: Backing up other data volume files..."))
                self.root.after(0, lambda: self.progress_var.set(60))
                self._backup_other_files(volume_path, temp_dir)
            else:
                self.root.after(0, lambda: self.progress_var.set(60))

            # Step 6: Create archive
            self.root.after(0, lambda: self.log_output("Step 6: Creating archive..."))
            self.root.after(0, lambda: self.progress_var.set(70))

            archive_path = f"/tmp/{backup_name}.tar.gz"
            self._execute_command(f"cd /tmp && tar -czf {backup_name}.tar.gz {backup_name}")

            # Clean up temp directory
            self._execute_command(f"rm -rf {temp_dir}")

            self.remote_backup_path = archive_path

            # Step 7: Download archive
            self.root.after(0, lambda: self.log_output("Step 7: Downloading backup..."))
            self.root.after(0, lambda: self.progress_var.set(75))

            local_path = os.path.join(self.save_path_var.get(), f"{backup_name}.tar.gz")
            self._download_backup(archive_path, local_path)

            # Done!
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.log_output(f"Backup completed successfully!"))
            self.root.after(0, lambda: self.log_output(f"Saved to: {local_path}"))
            self.root.after(0, lambda: messagebox.showinfo("Success",
                                                          f"Backup completed!\n\nSaved to:\n{local_path}"))

            # Enable delete button
            self.root.after(0, lambda: self.delete_btn.configure(state='normal'))
            self.root.after(0, lambda: self.backup_btn.configure(state='normal'))

        except Exception as e:
            self.root.after(0, lambda: self.log_output(f"ERROR: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Backup Failed", f"Backup failed:\n{e}"))
            self.root.after(0, lambda: self.backup_btn.configure(state='normal'))

    def _execute_command(self, command):
        """Execute a command on the remote server."""
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()

        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if exit_status != 0:
            raise Exception(f"Command failed: {command}\n{error}")

        return output

    def _get_volume_path(self):
        """Get the data volume path for the Homebox container."""
        # Inspect the container to find volume mounts
        container_name = self.homebox_container['name']
        command = f"docker inspect {container_name} --format '{{{{json .Mounts}}}}'"

        output = self._execute_command(command)

        # Parse mounts to find data volume
        # Looking for common Homebox data paths
        if '/data' in output:
            # Extract the source path for /data mount
            # This is a simplified approach - may need refinement
            command = f"docker inspect {container_name} --format '{{{{range .Mounts}}}}{{{{if eq .Destination \"/data\"}}}}{{{{.Source}}}}{{{{end}}}}{{{{end}}}}'"
            volume_path = self._execute_command(command).strip()
            if volume_path:
                return volume_path

        # Fallback: look for any volume
        command = f"docker inspect {container_name} --format '{{{{range .Mounts}}}}{{{{.Source}}}}{{{{end}}}}'"
        volume_path = self._execute_command(command).strip().split('\n')[0]

        return volume_path if volume_path else None

    def _backup_database(self, temp_dir):
        """Backup the PostgreSQL database."""
        container_name = self.postgres_container['name']

        # Get database credentials from Homebox container environment
        # This assumes standard Homebox setup with linked database
        db_name = "homebox"  # Default Homebox database name
        db_user = "homebox"  # Default username

        # Perform pg_dump
        dump_file = f"{temp_dir}/database/homebox_db.sql"
        command = f"docker exec {container_name} pg_dump -U {db_user} {db_name} > {dump_file}"

        self._execute_command(command)
        self.root.after(0, lambda: self.log_output("Database backup completed"))

    def _backup_media(self, volume_path, temp_dir):
        """Backup media files from the data volume."""
        # Copy media directory
        media_src = f"{volume_path}/attachments"
        media_dst = f"{temp_dir}/media/"

        # Check if media directory exists
        check_cmd = f"[ -d {media_src} ] && echo 'exists' || echo 'notfound'"
        result = self._execute_command(check_cmd).strip()

        if result == 'exists':
            self._execute_command(f"cp -r {media_src}/* {media_dst} 2>/dev/null || true")
            self.root.after(0, lambda: self.log_output("Media files backup completed"))
        else:
            self.root.after(0, lambda: self.log_output("No media directory found, skipping..."))

    def _backup_other_files(self, volume_path, temp_dir):
        """Backup other files from the data volume."""
        # Copy everything except media/attachments
        other_dst = f"{temp_dir}/other-files/"

        # List directories in volume
        list_cmd = f"ls -1 {volume_path}"
        dirs = self._execute_command(list_cmd).strip().split('\n')

        for dir_name in dirs:
            if dir_name and dir_name != 'attachments':
                src = f"{volume_path}/{dir_name}"
                self._execute_command(f"cp -r {src} {other_dst} 2>/dev/null || true")

        self.root.after(0, lambda: self.log_output("Other files backup completed"))

    def _download_backup(self, remote_path, local_path):
        """Download the backup archive from the remote server."""
        try:
            with SCPClient(self.ssh_client.get_transport()) as scp:
                scp.get(remote_path, local_path)

            self.root.after(0, lambda: self.log_output(f"Downloaded to: {local_path}"))

        except Exception as e:
            raise Exception(f"Download failed: {e}")

    def delete_server_backup(self):
        """Delete the backup archive from the remote server."""
        if not self.remote_backup_path:
            messagebox.showwarning("No Backup", "No server-side backup to delete")
            return

        response = messagebox.askyesno("Confirm Delete",
                                       "Delete the backup archive from the server?\n\n" +
                                       f"{self.remote_backup_path}")
        if not response:
            return

        try:
            self.log_output(f"Deleting server backup: {self.remote_backup_path}")
            self._execute_command(f"rm -f {self.remote_backup_path}")
            self.log_output("Server backup deleted successfully")
            self.remote_backup_path = None
            self.delete_btn.configure(state='disabled')
            messagebox.showinfo("Success", "Server backup deleted successfully")

        except Exception as e:
            self.log_output(f"Error deleting server backup: {e}")
            messagebox.showerror("Error", f"Failed to delete server backup:\n{e}")

    def load_settings(self):
        """Load settings from the settings file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)

                # Load connection settings
                self.host_var.set(settings.get('host', ''))
                self.port_var.set(settings.get('port', '22'))
                self.username_var.set(settings.get('username', ''))

                # Load backup options
                self.backup_other_var.set(settings.get('backup_other', False))
                self.save_path_var.set(settings.get('save_path', str(Path.home() / "Downloads")))

                self.log_output(f"Settings loaded from {self.settings_file}")
            else:
                self.log_output("No previous settings found - using defaults")
        except Exception as e:
            self.log_output(f"Could not load settings: {e}")

    def save_settings(self):
        """Save current settings to file."""
        try:
            settings = {
                'host': self.host_var.get(),
                'port': self.port_var.get(),
                'username': self.username_var.get(),
                'backup_other': self.backup_other_var.get(),
                'save_path': self.save_path_var.get()
            }

            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)

        except Exception as e:
            self.log_output(f"Could not save settings: {e}")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = HomeboxBackupGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
