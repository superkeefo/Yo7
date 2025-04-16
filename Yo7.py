import os
import re
import time
import json
import requests
import pygame
import customtkinter as ctk
from customtkinter import *
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timezone
from PIL import Image
from winotify import Notification, audio



# Constants
CONFIG_FILE = "config.json"

# Global variables
prefs_ready = False  # CHECK: Set to false after testing
scanning = False
observer = None
start_timestamp = None
latest_log = None


# function for reading save file
def load_config():
    with open(CONFIG_FILE, "r") as pullfile:
       return json.load(pullfile)
    

# Checks if settings exist
if os.path.exists(CONFIG_FILE):
    prefs_ready = True
    # renaming to config_pull for clarity
else:
    prefs_ready = False


# Save settings function
def save_config(config):
    with open(CONFIG_FILE, "w") as savefile:
        json.dump(config, savefile, indent=4)


def find_latest_log():
    config_pull = load_config()
    folder_path = config_pull.get("logfile_name")
    logs = [log for log in os.listdir(folder_path) if re.match(r'(?i)journal\.\d{4}-\d{2}-\d{2}T\d{6}\.01\.log', log)]
    if logs:
        latest_log = max(logs, key=lambda log: re.search(r'\d{4}-\d{2}-\d{2}T\d{6}', log).group())
        return os.path.join(config_pull.get("logfile_name"), latest_log)
    

def scan_pressed():
    global scanning
    if prefs_ready == True and scanning == False:
        start_scanning()
        start_monitoring()
    else:
        stop_scanning()


def start_scanning():
    global scanning, start_timestamp
    scanning = True
    start_timestamp = datetime.now(timezone.utc).isoformat()
    scan_label.configure(text= "scanning")
    scan_button.configure(text= "stop scanning", hover_color="#BB0000")

    

def stop_scanning():
    global scanning
    scanning = False
    scan_label.configure(text= "scanner inactive")
    scan_button.configure(text= "start scanning", hover_color="#106A43")


def send_toast(toastchannel, cmdr, message):
    toast = Notification(app_id="Yo7",
                         title=toastchannel,
                         msg=f"{cmdr}: {message}")
    toast.set_audio(audio.Mail, loop=False)
    toast.show()
    time.sleep(1)
                        

def send_discord(payload):
    config_pull = load_config()
    webhook = config_pull.get("webhook_url")
    requests.post(webhook, json=payload)
    time.sleep(1)
    

def send_alert():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    sound = "Yo7.wav"
    config_pull = load_config()
    pull_vol = config_pull.get("volume")
    push_vol = round(float(pull_vol)/100,1)
    my_sound = pygame.mixer.Sound(sound)
    my_sound.set_volume(push_vol)
    my_sound.play()
    time.sleep(1)
    pygame.mixer.quit()
    pygame.quit() 
    

class LogWatcher(FileSystemEventHandler):
    def __init__(self):
        self.config_pull = load_config()
        self.folder = self.config_pull.get("logfile_name")
        self.latest_log = find_latest_log()
        self.set_latest_log(self.latest_log)
        self.last_position = 0
        self.new_lines()  

    def on_modified(self, event):
        if event.src_path == self.latest_log:
            time.sleep(0.5)
            self.new_lines()
    
    def on_created(self, event):
        if event.src_path.startswith(self.folder):
            time.sleep(0.5)
            new_file= find_latest_log()
            if new_file != self.latest_log:
                self.latest_log = new_file
                self.set_latest_log(self.latest_log)
                self.last_position = 0
                self.new_lines()

    def set_latest_log(self, log_file):
        self.latest_log = log_file

    def new_lines(self):
        global scanning
        if not self.latest_log or not os.path.exists(self.latest_log) or not scanning:
            return
        with open(self.latest_log, "r", encoding="utf-8") as current:
            current.seek(self.last_position)
            new_lines = current.readlines()
            self.last_position = current.tell()
            for line in new_lines:
                match = re.search(r'\{.*\}', line)
                if match:
                    log = json.loads(match.group())
                    timestamp = log.get("timestamp")
                    if timestamp and start_timestamp and timestamp > start_timestamp:
                        event = log.get("event")
                        if event in ("Receivetext", "ReceiveText"):
                            channel = log.get("Channel","Unknown")
                            from_cmdr = log.get("From","Unknown")
                            message = log.get("Message","Unknown")
                            channel_swap = {"player": "DM", "starsystem": "SYSTEM", "local": "LOCAL",
                                            "wing": "WING", "voicechat": "VC", "squadron": "SQUAD"}
                            if from_cmdr.startswith("$") or message.startswith("$"):
                                continue
                            if channel in channel_swap.keys():
                                channel_name = channel_swap[channel]
                            else:
                                channel_name = "Unknown"
                            payload = {"username": "Yo7", "content": f"`{channel_name}`   {from_cmdr} :   {message}"}
                            saved_status = load_config()
                            notify_meth = saved_status.get("notif_type")
                            status = saved_status.get(channel_name)
                    
                            if status == "on" and notify_meth == "simple sound alert":
                                #simple sound alert action
                                send_alert()
                            elif status == "on" and notify_meth == "discord notification":
                                #discord alert action
                                send_discord(payload)
                            elif status == "on" and notify_meth == "windows notification":
                                #windows alert action
                                send_toast(channel_name, from_cmdr, message)
                            else:
                                continue
                                
def start_monitoring():
    global observer 
    if observer:
        observer.stop()
        observer.join()
    config_pull = load_config()
    path = config_pull.get("logfile_name")
    event_handler = LogWatcher()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()

# GUI initial setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


#Defining the preferences window
def pref_window():
    stop_scanning()
    pref = ctk.CTkToplevel()
    pref.grab_set()
    pref.geometry("500x550")
    pref.title("Preferences")
    pref.after(200, lambda: pref.iconbitmap("Yo7.ico"))
    pref.resizable(False, False)


#CHECK: reminds to save or lets discard - need to check prefs_ready on start scan
    def disable_close():
        savealert = CTkToplevel()
        savealert.grab_set()
        savealert.geometry("400x145")
        savealert.title("Whoa there!")
        savealert.after(200, lambda: savealert.iconbitmap("Yo7.ico"))
        savealert.resizable(False, False)
        def closealert():
            savealert.destroy()
        def closewindow():
            pref.destroy()
            closealert()
        alert_label= ctk.CTkLabel(master=savealert,  text="You need to save those settings\n or they'll be lost!", text_color="#AAAAAA" , font=("Roboto", 17))
        alert_label.pack(pady=(30,15))
        discard_btn = ctk.CTkButton(master=savealert, width=150, text="nah it's fine!", text_color="Black", font=("Roboto", 15), command=closewindow)
        discard_btn.pack(side=LEFT, padx=(48,2))
        alert_save= ctk.CTkButton(master=savealert, width=150, text="oh right! whoops!", text_color="Black", font=("Roboto", 15), command=closealert)
        alert_save.pack(side=RIGHT, padx=(2,48))
        
    pref.protocol("WM_DELETE_WINDOW", disable_close)  

    
    #Defining grid for preference window
    pref.grid_columnconfigure((0, 1), weight=1)
    pref.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12), weight=1)


    #Defining preference window elements
    #log_folder = ctk.StringVar() 
    log_entry= ctk.CTkEntry(master=pref, placeholder_text="enter elite dangerous log folder here", font=("Roboto", 15), width=300, height=30)
    log_entry.grid(row=0, column=0, sticky="nw", padx=(20,0), pady=(20,0))


    #clears any previous saved text in log entry field
    def clear():
        log_entry.configure(state=NORMAL) 
        log_entry.delete(0, END)
        log_entry.configure(state=DISABLED)

    #dialog window and insert new entry text
    def browse_folder():
        browsed = filedialog.askdirectory()
        if browsed:
            clear()
            log_entry.configure(state=NORMAL) 
            log_entry.insert(0, browsed)

    
    browse_button = ctk.CTkButton(master=pref, text="browse", font=("Roboto", 15), text_color="Black", width= 220 , height=30, command = browse_folder)
    browse_button.grid(row=0, column=1, sticky="ne", padx=(10,20), pady=(20,0))

    #browse for log file

    disable_color ="#444444"

    #choice function to declare
    def choice_func(choice_sel):
        if choice_sel == "simple sound alert":
            #enable volume
            volume_label.configure(text_color="#AAAAAA")
            volume_slider.configure(button_color=("#2CC985","#2FA572"), progress_color=("gray40","#AAB0B5"), state="normal", hover=True)
            #disable discord
            discord_entry.configure(state="disabled", text_color=disable_color, placeholder_text_color=disable_color)
            discord_button.configure(state="disabled", text_color_disabled="gray10" , fg_color=disable_color)
        elif choice_sel == "discord notification":
            #enable discord
            discord_entry.configure(state="normal", text_color="#DCE4EE" , placeholder_text_color="gray52")
            discord_button.configure(state="normal", fg_color="#2FA572")
            discord_button.focus_set()
            #disable volume
            volume_label.configure(text_color=disable_color)
            volume_slider.configure(button_color=(disable_color,disable_color), progress_color=(disable_color,disable_color), state="disabled", hover=False)
        else:
            #disable volume
            volume_label.configure(text_color=disable_color)
            volume_slider.configure(button_color=(disable_color,disable_color), progress_color=(disable_color,disable_color), state="disabled", hover=False)
            #disable discord
            discord_entry.configure(state="disabled", text_color=disable_color, placeholder_text_color=disable_color)
            discord_button.configure(state="disabled", text_color_disabled=disable_color , fg_color=disable_color)      
            

    #Choice for notification 
    choice_label= ctk.CTkLabel(master=pref, text="Which kind of notification", text_color="#AAAAAA" , font=("Roboto", 15))
    choice_label.grid(row=1, column=0, sticky="e", padx=(20,5), pady=(15,0))


    choice_box = ctk.CTkOptionMenu(master=pref, values=["simple sound alert", "discord notification", "windows notification"], 
                                   text_color="Black", font=("Roboto", 15), width=220, height=30, 
                                   #variable=choice_var, 
                                   command=choice_func)
    choice_box.grid(row=1, column=1, sticky="e", padx=(10,20), pady=(15,0))

    #simple sound alert options 
    def slider_value(value):
        volume_label.configure(text="Volume " + str(int(value)) + "%")

    
    volume_slider= ctk.CTkSlider(master=pref, from_=0, to=100, width = 220, command=slider_value)
    volume_slider.set(100) 
    volume_slider.grid(row=2, column=1, sticky="e", padx=(10,20), pady=(20,0))


    volume_label= ctk.CTkLabel(master=pref, text="Volume " + str(int(volume_slider.get())) +"%", text_color="#AAAAAA" , font=("Roboto", 15))
    volume_label.grid(row=2, column=0, sticky="e", padx=(20,5), pady=(20,0))


    #discord notification options
    discord_entry= ctk.CTkEntry(master=pref, placeholder_text="paste discord webhook url here", font=("Roboto", 15), width=300, height=30)
    discord_entry.grid(row=3, column=0, sticky="nw", padx=(20,0), pady=(15,0))


    def discord_test():
        webhook = discord_entry.get()
        test_message = {"username": "Yo7", "content": f"`TEST` seems to be working"}
        requests.post(webhook, json=test_message)
        

    discord_button = ctk.CTkButton(master=pref, text="test webhook", font=("Roboto", 15), text_color="Black", width= 220 , height=30, command=discord_test)
    discord_button.grid(row=3, column=1, sticky="ne", padx=(10,20), pady=(15,0))


    # windows notification options
    # not sure there is any of these

    # edchannel options
    choice_label= ctk.CTkLabel(master=pref, text="Choose which channels to receive notifications from:", justify="center" , text_color="#AAAAAA" , font=("Roboto", 15))
    choice_label.grid(row=5, column=0 , columnspan=2, sticky="nwe", padx=(20,20), pady=(20,0))


    # edchannel options DM
    dm_label= ctk.CTkLabel(master=pref, text="Direct messages", text_color="#AAAAAA" , font=("Roboto", 15))
    dm_label.grid(row=6, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    dm_choice = ctk.StringVar(value="on")
    dm_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=dm_choice)
    dm_switch.grid(row=6, column=1, sticky="nw", padx=(10,5) , pady=(10,0))

    # edchannel options LOCAL
    local_label= ctk.CTkLabel(master=pref, text="Local CMDR messages", text_color="#AAAAAA" , font=("Roboto", 15))
    local_label.grid(row=7, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    local_choice = ctk.StringVar(value="on")
    local_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=local_choice)
    local_switch.grid(row=7, column=1, sticky="nw", padx=(10,5) , pady=(10,0))

    # edchannel options SYSTEM
    system_label= ctk.CTkLabel(master=pref, text="System CMDR messages", text_color="#AAAAAA" , font=("Roboto", 15))
    system_label.grid(row=8, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    system_choice = ctk.StringVar(value="on")
    system_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=system_choice)
    system_switch.grid(row=8, column=1, sticky="nw", padx=(10,5) , pady=(10,0))

    # edchannel options WING
    wing_label= ctk.CTkLabel(master=pref, text="Wing messages", text_color="#AAAAAA" , font=("Roboto", 15))
    wing_label.grid(row=9, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    wing_choice = ctk.StringVar(value="on")
    wing_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=wing_choice)
    wing_switch.grid(row=9, column=1, sticky="nw", padx=(10,5) , pady=(10,0))

    # edchannel options SQUAD
    squad_label= ctk.CTkLabel(master=pref, text="Squad messages", text_color="#AAAAAA" , font=("Roboto", 15))
    squad_label.grid(row=10, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    squad_choice = ctk.StringVar(value="on")
    squad_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=squad_choice)
    squad_switch.grid(row=10, column=1, sticky="nw", padx=(10,5) , pady=(10,0))

    # edchannel options VOICECHAT
    vc_label= ctk.CTkLabel(master=pref, text="Voicechat messages", text_color="#AAAAAA" , font=("Roboto", 15))
    vc_label.grid(row=11, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    vc_choice = ctk.StringVar(value="on")
    vc_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=vc_choice)
    vc_switch.grid(row=11, column=1, sticky="nw", padx=(10,5) , pady=(10,0))


    #lets the the choice fuction disable based on default value
    if os.path.exists(CONFIG_FILE):
        config_pull = load_config()
        choice = config_pull.get("notif_type")
        choice_func(choice)
        choice_box.set(choice)
        log_entry.insert(0,config_pull.get("logfile_name"))
        volume_slider.set(config_pull.get("volume"))
        slider_value(config_pull.get("volume"))
        if config_pull.get("webhook_url") != "":
            discord_entry.insert(0,config_pull.get("webhook_url"))
        dm_choice.set(config_pull.get("DM"))
        local_choice.set(config_pull.get("LOCAL"))
        system_choice.set(config_pull.get("SYSTEM"))
        wing_choice.set(config_pull.get("WING"))
        squad_choice.set(config_pull.get("SQUAD"))
        vc_choice.set(config_pull.get("VC"))
    else:
        choice_func("simple sound alert")
    

    #close preference and get current preferences for save function
    def save_settings():
        global prefs_ready
        save = {"logfile_name" : log_entry.get(), 
                "notif_type" : choice_box.get(),
                "volume" : int(volume_slider.get()),
                "webhook_url" : discord_entry.get(),
                "DM" : dm_choice.get(),
                "LOCAL" : local_choice.get(),
                "SYSTEM" : system_choice.get(),
                "WING" : wing_choice.get(),
                "SQUAD" : squad_choice.get(),
                "VC" : vc_choice.get()}
        save_config(save)
        prefs_ready = True
        pref.destroy()
        
    

        
    save_button = ctk.CTkButton(master=pref, text="save settings", font=("Roboto", 15), text_color="Black", height=30, command=save_settings)
    save_button.grid(row=12, column=0, columnspan=2 , sticky="sew", padx=(20,20), pady=(15,20))


#Defining the main window
root = ctk.CTk()
root.geometry("300x110")
root.title("Yo7")
root.iconbitmap("Yo7.ico")
root.resizable(False, False)


#Denfining main window elements
scan_label = ctk.CTkLabel(master=root, text="scanner inactive", font=("Roboto", 18)) 
scan_label.pack( pady = (20,10))

       
scan_button = ctk.CTkButton(master=root, text="start scanning", height=30, font=("Roboto", 15), text_color="Black", command=scan_pressed)
scan_button.pack( fill = "x", expand=True , pady = 0, padx = (10,2) , side = 'left')

button_image = ctk.CTkImage(Image.open("cogwheel.png"), size=(15,15))

pref_button = ctk.CTkButton(master=root, image=button_image, text="", width=30, height=30, font=("Roboto", 15), text_color="Black", command=pref_window)
pref_button.pack( pady = 0, padx = (2,10) , side = 'right' )


#Open preference window if prefs not set
if prefs_ready is False:
    root.after(750, pref_window)


#Running the main loop
if __name__ == "__main__":
    root.mainloop()

