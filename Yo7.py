import os
import re
import time
import json
import requests
import tkinter as tk
from tkinter import filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timezone

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def find_latest_log_file(folder_path):
    try:
        log_files = [f for f in os.listdir(folder_path) if re.match(r'(?i)journal\.\d{4}-\d{2}-\d{2}T\d{6}\.01\.log', f)]
        if log_files:
            latest_file = max(log_files, key=lambda f: re.search(r'\d{4}-\d{2}-\d{2}T\d{6}', f).group())
            return os.path.join(folder_path, latest_file)
    except Exception as e:
        print(f"Error finding latest log file: {e}")
    return None

def send_to_discord(webhook_url, message):
    if webhook_url:
        try:
            requests.post(webhook_url, json={"content": message})
        except Exception as e:
            print(f"Error sending to Discord: {e}")

class LogFileMonitor(FileSystemEventHandler):
    def __init__(self, folder_path, app):
        self.folder_path = folder_path
        self.app = app
        self.latest_log_file = find_latest_log_file(self.folder_path)
        self.app.set_latest_log_file(self.latest_log_file)
        self.last_position = 0
        self.process_new_lines()
    
    def on_modified(self, event):
        if event.src_path == self.latest_log_file:
            time.sleep(0.5)
            self.process_new_lines()
    
    def on_created(self, event):
        if event.src_path.startswith(self.folder_path):
            time.sleep(0.5)
            new_file = find_latest_log_file(self.folder_path)
            if new_file != self.latest_log_file:
                self.latest_log_file = new_file
                self.app.set_latest_log_file(self.latest_log_file)
                self.last_position = 0
                self.process_new_lines()

    channel_swap = {"player": "DM", "starsystem": "SYSTEM", "local": "LOCAL", "wing": "WING", "voicechat": "VC", "squadron": "SQUAD"}
    def process_new_lines(self):
        if not self.latest_log_file or not os.path.exists(self.latest_log_file) or not self.app.scanning:
            return
        try:
            with open(self.latest_log_file, "r", encoding="utf-8") as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                for line in new_lines:
                    match = re.search(r'\{.*\}', line)
                    if match:
                        try:
                            log_entry = json.loads(match.group())
                            timestamp = log_entry.get("timestamp")
                            if timestamp and self.app.start_timestamp and timestamp > self.app.start_timestamp:
                                event = log_entry.get("event")
                                if event in ("Receivetext", "ReceiveText"):
                                    channel = log_entry.get("Channel", "Unknown")
                                    from_cmdr = log_entry.get("From", "Unknown")
                                    message = log_entry.get("Message", "Unknown")
                                    if from_cmdr.startswith("$") or message.startswith("$"):
                                        continue
                                    if channel in channel_swap.keys():
                                        channel == channel_swap[channel]
                                    formatted_message = f"{channel} {from_cmdr}: {message}"
                                    send_to_discord(self.app.webhook_url.get(), formatted_message)
                        except json.JSONDecodeError as e:
                            print(f"Error parsing JSON: {e}")
        except Exception as e:
            print(f"Error processing log file: {e}")

class LogMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yo7")
        self.root.iconbitmap('Yo7.ico')
        self.folder_path = tk.StringVar()
        self.latest_log_file = None
        self.event_handler = None
        self.observer = None
        self.scanning = False
        self.start_timestamp = None
        self.webhook_url = tk.StringVar()
        config_data = load_config()
        self.folder_path.set(config_data.get("folder_path", ""))
        self.webhook_url.set(config_data.get("webhook_url", ""))
        tk.Label(root, text="Select Log Folder:").pack()
        tk.Entry(root, textvariable=self.folder_path, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_folder).pack()
        tk.Label(root, text="Discord Webhook URL:").pack()
        tk.Entry(root, textvariable=self.webhook_url, width=50).pack()
        tk.Button(root, text="Start Scan", command=self.start_scan).pack()
        tk.Button(root, text="Stop Scan", command=self.stop_scan).pack()
        self.status_label = tk.Label(root, text="Scanner Off", fg="red")
        self.status_label.pack()
    
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.save_settings()
    
    def start_scan(self):
        if not self.folder_path.get() or not self.webhook_url.get():
            return
        self.scanning = True
        self.start_timestamp = datetime.now(timezone.utc).isoformat()
        self.status_label.config(text="Scanner Running", fg="green")
        self.start_monitoring()
    
    def stop_scan(self):
        self.scanning = False
        self.status_label.config(text="Scanner Off", fg="red")
    
    def start_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.event_handler = LogFileMonitor(self.folder_path.get(), self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.folder_path.get(), recursive=False)
        self.observer.start()
    
    def set_latest_log_file(self, log_file):
        self.latest_log_file = log_file
    
    def save_settings(self):
        save_config({"folder_path": self.folder_path.get(), "webhook_url": self.webhook_url.get()})

if __name__ == "__main__":
    root = tk.Tk()
    app = LogMonitorApp(root)
    root.mainloop()
