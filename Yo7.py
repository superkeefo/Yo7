import os
import re
import time
import json
import requests
import customtkinter as ctk
from customtkinter import *
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timezone


# Init variables
prefs_ready = False  # CHECK: Set to false after testing
config_file = os.path.join("settings", "config.json")


# GUI initial setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


#Defining the preferences window
def pref_window():
    pref = ctk.CTkToplevel()
    pref.grab_set()
    pref.geometry("500x600")
    pref.title("Preferences")
    pref.after(200, lambda: pref.iconbitmap("Yo7.ico"))
    pref.resizable(False, False)  

    
    #Defining grid for preference window
    pref.grid_columnconfigure((0, 1), weight=1)
    pref.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12), weight=1)


    #Defining preference window elements
    log_entry= ctk.CTkEntry(master=pref, placeholder_text="enter elite dangerous log folder here", font=("Roboto", 15), width=300, height=30)
    log_entry.grid(row=0, column=0, sticky="nw", padx=(20,0), pady=(20,0))


    browse_button = ctk.CTkButton(master=pref, text="browse", font=("Roboto", 15), text_color="Black", width= 220 , height=30)
    browse_button.grid(row=0, column=1, sticky="ne", padx=(10,20), pady=(20,0))

    

    #choice function to declare
    def choice_func(choice_sel):
        if choice_sel == "simple sound alert":
            print("simple")
            #enable volume
            volume_label.configure(text_color="#AAAAAA")
            volume_slider.configure(button_color=("#444444","#444444"), progress_color=("#444444","#444444"), state="normal", hover=True)
            #disable discord
            discord_entry.configure(state="disabled", placeholder_text_color="#444444")
            discord_button.configure(state="disabled", text_color_disabled="#444444" , fg_color="#444444")
        elif choice_sel == "discord notification":
            print("discord")
            #enable discord
            discord_entry.configure(state="normal", placeholder_text_color="#444444")
            discord_button.configure(state="normal", text_color_disabled="#444444" , fg_color="#444444")
            #disable volume
            volume_label.configure(text_color="#444444")
            volume_slider.configure(button_color=("#444444","#444444"), progress_color=("#444444","#444444"), state="disabled", hover=False)
        else:
            print("windows")
            #disable volume
            volume_label.configure(text_color="#444444")
            volume_slider.configure(button_color=("#444444","#444444"), progress_color=("#444444","#444444"), state="disabled", hover=False)
            #disable discord
            discord_entry.configure(state="disabled", placeholder_text_color="#444444")
            discord_button.configure(state="disabled", text_color_disabled="#444444" , fg_color="#444444")      
            

    #Choice for notification 
    choice_label= ctk.CTkLabel(master=pref, text="Which kind of notification", text_color="#AAAAAA" , font=("Roboto", 15))
    choice_label.grid(row=1, column=0, sticky="e", padx=(20,5), pady=(5,0))


    choice_box = ctk.CTkOptionMenu(master=pref, values=["simple sound alert", "discord notification", "windows notification"], 
                                   text_color="Black", font=("Roboto", 15), width=220, height=30, 
                                   #variable=choice_var, 
                                   command=choice_func)
    choice_box.grid(row=1, column=1, sticky="e", padx=(10,20), pady=(5,0))

    #simple sound alert options 
    def slider_value(value):
        volume_label.configure(text="Volume " + str(int(value)) + "%")

    
    volume_slider= ctk.CTkSlider(master=pref, from_=0, to=100, width = 220, command=slider_value)
    volume_slider.set(100) 
    volume_slider.grid(row=2, column=1, sticky="e", padx=(10,20), pady=(5,0))


    volume_label= ctk.CTkLabel(master=pref, text="Volume " + str(int(volume_slider.get())) +"%", text_color="#AAAAAA" , font=("Roboto", 15))
    volume_label.grid(row=2, column=0, sticky="e", padx=(20,5), pady=(5,0))


    #discord notification options
    discord_entry= ctk.CTkEntry(master=pref, placeholder_text="paste discord webhook url here", font=("Roboto", 15), width=300, height=30)
    discord_entry.grid(row=3, column=0, sticky="nw", padx=(20,0), pady=(20,0))


    discord_button = ctk.CTkButton(master=pref, text="test webhook", font=("Roboto", 15), text_color="Black", width= 220 , height=30)
    discord_button.grid(row=3, column=1, sticky="ne", padx=(10,20), pady=(20,0))


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
    dm_switch.grid(row=6, column=1, sticky="nw", padx=(10,5) , pady=(15,0))

    # edchannel options LOCAL
    local_label= ctk.CTkLabel(master=pref, text="Local CMDR messages", text_color="#AAAAAA" , font=("Roboto", 15))
    local_label.grid(row=7, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    local_choice = ctk.StringVar(value="on")
    local_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=local_choice)
    local_switch.grid(row=7, column=1, sticky="nw", padx=(10,5) , pady=(15,0))

    # edchannel options SYSTEM
    system_label= ctk.CTkLabel(master=pref, text="System CMDR messages", text_color="#AAAAAA" , font=("Roboto", 15))
    system_label.grid(row=8, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    system_choice = ctk.StringVar(value="on")
    system_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=system_choice)
    system_switch.grid(row=8, column=1, sticky="nw", padx=(10,5) , pady=(15,0))

    # edchannel options WING
    wing_label= ctk.CTkLabel(master=pref, text="Wing messages", text_color="#AAAAAA" , font=("Roboto", 15))
    wing_label.grid(row=9, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    wing_choice = ctk.StringVar(value="on")
    wing_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=wing_choice)
    wing_switch.grid(row=9, column=1, sticky="nw", padx=(10,5) , pady=(15,0))

    # edchannel options SQUAD
    squad_label= ctk.CTkLabel(master=pref, text="Squad messages", text_color="#AAAAAA" , font=("Roboto", 15))
    squad_label.grid(row=10, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    squad_choice = ctk.StringVar(value="on")
    squad_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=squad_choice)
    squad_switch.grid(row=10, column=1, sticky="nw", padx=(10,5) , pady=(15,0))

    # edchannel options VOICECHAT
    vc_label= ctk.CTkLabel(master=pref, text="Voicechat messages", text_color="#AAAAAA" , font=("Roboto", 15))
    vc_label.grid(row=11, column=0, sticky="e", padx=(20,5), pady=(5,0))
    
    vc_choice = ctk.StringVar(value="on")
    vc_switch= ctk.CTkSwitch(master=pref, text=None , onvalue="on", offvalue="off", variable=vc_choice)
    vc_switch.grid(row=11, column=1, sticky="nw", padx=(10,5) , pady=(15,0))

    #feed saved preferences in here
    choice_func("discord notification")  
    choice_box.set("discord notification")

    #close and save preferences
    def save_config():
        print(dm_choice.get(), int(volume_slider.get()), choice_box.get())
        #pref.destroy() #need to check for correct settings, save settings, and update global variables


    save_button = ctk.CTkButton(master=pref, text="save settings", font=("Roboto", 15), text_color="Black", height=30, command=save_config)
    save_button.grid(row=12, column=0, columnspan=2 , sticky="sew", padx=(20,20), pady=(0,20))



#Defining the main window
root = ctk.CTk()
root.geometry("300x110")
root.title("Yo7")
root.iconbitmap("Yo7.ico")
root.resizable(False, False)


#Denfining main window elements
scan_label = ctk.CTkLabel(master=root, text="scanning inactive", font=("Roboto", 18)) 
scan_label.pack( pady = (20,10))

       
scan_button = ctk.CTkButton(master=root, text="start scanning", height=30, font=("Roboto", 15), text_color="Black")
scan_button.pack( fill = "x", expand=True , pady = 0, padx = (10,2) , side = 'left')


pref_button = ctk.CTkButton(master=root, text="pr", width=30, height=30, font=("Roboto", 15), text_color="Black", command=pref_window)
pref_button.pack( pady = 0, padx = (2,10) , side = 'right' )


#Open preference window if prefs not set
if prefs_ready is False:
    root.after(1000, pref_window())


#Running the main loop
if __name__ == "__main__":
    root.mainloop()

