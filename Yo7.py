import os
import json
import time
import requests
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import hashlib

CONFIG_FILE = "config.json"
LAST_LOG_FILE = "last_log_file.txt"
PROCESSED_MESSAGES_FILE = "processed_messages.json"
LAST_POSITION_FILE = "last_position.json"
LAST_PROCESSED_TIMESTAMP_FILE = "last_processed_timestamp.json"  # New file for storing last processed timestamp
monitoring = False  # Variable to track if monitoring is active
observer = None  # Global observer for `watchdog`
last_sent_time = 0  # Global variable to track last message sent time
last_scanner_on_time = 0  # Track the time when the scanner was turned back on

def load_config():
    """Loads configuration settings from the config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(log_folder, webhook_url):
    """Saves user configuration to a JSON file."""
    config = {"log_folder": log_folder, "webhook_url": webhook_url}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def save_last_log_file(log_file):
    """Saves the last processed log file path."""
    with open(LAST_LOG_FILE, "w") as f:
        f.write(log_file)

def load_last_log_file():
    """Loads the path of the last processed log file."""
    if os.path.exists(LAST_LOG_FILE):
        with open(LAST_LOG_FILE, "r") as f:
            return f.read().strip()
    return None

def load_processed_messages():
    """Loads previously processed messages from a file."""
    if os.path.exists(PROCESSED_MESSAGES_FILE):
        with open(PROCESSED_MESSAGES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_processed_message(message_hash, position):
    """Saves a processed message hash and its file position."""
    processed = load_processed_messages()
    processed[message_hash] = position
    with open(PROCESSED_MESSAGES_FILE, "w") as f:
        json.dump(processed, f)

def get_latest_journal_file(log_folder):
    """Finds the most recent Journal log file."""
    log_files = [f for f in os.listdir(log_folder) if f.startswith("Journal.") and f.endswith(".log")]
    
    if not log_files:
        return None
    
    log_files.sort(key=lambda f: os.path.getmtime(os.path.join(log_folder, f)), reverse=True)
    latest_file = os.path.join(log_folder, log_files[0])
    return latest_file

def load_last_position():
    """Loads the position of the last read line from the log file."""
    if os.path.exists(LAST_POSITION_FILE):
        with open(LAST_POSITION_FILE, "r") as f:
            return int(f.read().strip())
    return 0

def save_last_position(position):
    """Saves the last read position in the log file."""
    with open(LAST_POSITION_FILE, "w") as f:
        f.write(str(position))

def load_last_processed_timestamp():
    """Loads the timestamp of the last processed message."""
    if os.path.exists(LAST_PROCESSED_TIMESTAMP_FILE):
        with open(LAST_PROCESSED_TIMESTAMP_FILE, "r") as f:
            return float(f.read().strip())
    return 0

def save_last_processed_timestamp(timestamp):
    """Saves the timestamp of the last processed message."""
    with open(LAST_PROCESSED_TIMESTAMP_FILE, "w") as f:
        f.write(str(timestamp))

def set_scanner_on_time():
    """Set the time when the scanner is turned on."""
    global last_scanner_on_time
    last_scanner_on_time = time.time()

class LogFileHandler(FileSystemEventHandler):
    """Handles log file updates using watchdog."""
    def __init__(self, log_file, webhook_url):
        self.log_file = log_file
        self.webhook_url = webhook_url
        self.processed_lines = load_processed_messages()
        self.last_processed_timestamp = load_last_processed_timestamp()

    def on_modified(self, event):
        """Triggered when the log file is modified."""
        global last_scanner_on_time
        if event.src_path != self.log_file or not monitoring:
            return
        
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            try:
                data = json.loads(line.strip())
                if data.get("event") == "ReceiveText":
                    message_timestamp = data.get("timestamp")
                    sender = data.get("From", "")
                    message = data.get("Message", "")
                    
                    # Exclude messages and senders that begin with '$'
                    if sender.startswith("$") or message.startswith("$"):
                        continue
                    
                    if not message_timestamp:
                        continue
                    
                    # Convert message timestamp to a float (assuming it's a Unix timestamp)
                    try:
                        message_timestamp = float(message_timestamp)
                    except ValueError:
                        # If it's a datetime string, convert it to a timestamp
                        try:
                            message_timestamp = datetime.strptime(message_timestamp, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                        except ValueError:
                            continue  # Skip if we can't parse the timestamp

                    # Only process messages if the scanner is on and the timestamp is after the scanner was turned on
                    if monitoring and message_timestamp > last_scanner_on_time:
                        message_content = f"**{sender}**: {message}"
                        message_hash = hashlib.sha256(message_content.encode('utf-8')).hexdigest()
                        
                        if message_hash in self.processed_lines:
                            continue
                        
                        send_to_discord(message_content, self.webhook_url)
                        
                        # Update the last processed timestamp and save it
                        self.last_processed_timestamp = message_timestamp
                        save_last_processed_timestamp(self.last_processed_timestamp)
                        self.processed_lines[message_hash] = message_timestamp
                        save_processed_message(message_hash, message_timestamp)
            except json.JSONDecodeError:
                continue

def send_to_discord(message, webhook_url):
    """Sends a message to Discord via a webhook."""
    global last_sent_time
    current_time = time.time()
    if current_time - last_sent_time < 1:
        return  # Enforce cooldown
    
    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        last_sent_time = current_time
    except requests.RequestException as e:
        print(f"Error sending to Discord: {e}")

def start_monitoring(log_folder, webhook_url, status_label):
    global monitoring, observer
    if monitoring:
        return  # Already running

    log_file = get_latest_journal_file(log_folder)
    if not log_file:
        messagebox.showerror("Error", "No log file found in the specified folder!")
        return

    save_last_log_file(log_file)
    status_label.config(text="scanner running", fg="lime green")
    monitoring = True
    set_scanner_on_time()  # Track the time when the scanner starts

    event_handler = LogFileHandler(log_file, webhook_url)
    observer = Observer()
    observer.schedule(event_handler, path=log_folder, recursive=False)
    observer.start()

def start_monitoring_thread(log_folder, webhook_url, status_label):
    """Starts monitoring in a separate thread to avoid blocking the GUI."""
    thread = threading.Thread(target=start_monitoring, args=(log_folder, webhook_url, status_label), daemon=True)
    thread.start()

def stop_monitoring(status_label):
    """Stops file monitoring and message processing."""
    global monitoring, observer
    if observer:
        observer.stop()
        observer.join()
    monitoring = False
    status_label.config(text="scanner stopped", fg="red")

    # Clear processed messages and reset position
    save_processed_message("", 0)  # Clear the processed messages file
    save_last_position(0)  # Reset the position
    save_last_processed_timestamp(0)  # Reset the last processed timestamp

def test_webhook(webhook_url):
    """Sends a test message to the webhook."""
    if not webhook_url:
        messagebox.showerror("Error", "Please enter a webhook URL!")
        return
    send_to_discord("✅ Webhook test successful!", webhook_url)
    messagebox.showinfo("Success", "Test message sent to Discord!")

def setup_gui():
    """GUI for user to enter log file path and webhook URL."""
    config = load_config()

    def save_and_start():
        log_folder = log_folder_entry.get()
        webhook_url = webhook_entry.get()

        if not log_folder or not webhook_url:
            messagebox.showerror("Error", "Please enter valid values.")
            return

        save_config(log_folder, webhook_url)
        start_monitoring_thread(log_folder, webhook_url, status_label)

    def browse_folder():
        folder_selected = filedialog.askdirectory()
        log_folder_entry.delete(0, tk.END)
        log_folder_entry.insert(0, folder_selected)

    def stop_script():
        stop_monitoring(status_label)

    root = tk.Tk()
    root.title("Yo7")
    root.geometry("420x350")
    root.configure(bg="#070707")

    label_style = {"bg": "#070707", "fg": "white", "font": ("Arial", 10,)}
    stat_style = {"bg": "#070707", "fg": "white", "font": ("Arial", 16,)}
    entry_style = {"bg": "#333", "fg": "white", "insertbackground": "white", "width": 50}
    button_style = {"bg": "black", "fg": "white", "activebackground": "white", "activeforeground": "black"}

    tk.Label(root, text="elite dangerous log folder:", **label_style).pack(pady=(30, 0))
    log_folder_entry = tk.Entry(root, **entry_style)
    log_folder_entry.insert(0, config.get("log_folder", ""))
    log_folder_entry.pack()
    tk.Button(root, text="browse", command=browse_folder, **button_style).pack()

    tk.Label(root, text="discord webhook url:", **label_style).pack(pady=(20, 0))
    webhook_entry = tk.Entry(root, **entry_style)
    webhook_entry.insert(0, config.get("webhook_url", ""))
    webhook_entry.pack()
    tk.Button(root, text="test webhook", command=lambda: test_webhook(webhook_entry.get()), **button_style).pack()

    status_label = tk.Label(root, text="click start scanner to begin", **stat_style)
    status_label.pack(pady=(30, 0))

    tk.Button(root, text="start scanner", command=save_and_start, **button_style).pack(pady=(15, 0))
    tk.Button(root, text="stop scanner", command=stop_script, **button_style).pack()

    root.mainloop()

if __name__ == "__main__":
    setup_gui()
