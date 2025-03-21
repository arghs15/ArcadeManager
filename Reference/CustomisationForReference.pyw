import os
import sys
import csv
import re
import subprocess
import tkinter as tk
from tkinter import messagebox
from tkinter import Canvas
from PIL import Image, ImageTk
import customtkinter as ctk
import tempfile
import time  # Make sure time is imported
import ctypes
import shutil
import shlex
import cv2
from threading import Thread, Lock
import queue
import ctypes
from tkinter import messagebox, filedialog
import configparser
from typing import List, Optional
import tkinter.font as tkFont
from typing import List
import json
import asyncio
import threading
import keyboard
import time
from inputs import get_gamepad, devices

class FilterGamesApp:
    @staticmethod
    def resource_path(relative_path):
        """Get the absolute path to a resource, works for dev and PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
        
    def __init__(self, root):
        self.root = root
        self.root.title("Customisation")
        self.root.geometry("1920x1080")  # Set the initial size (you can adjust as needed)
        self.root.resizable(True, True)  # Enable window resizing
        
        # Set window icon - handles both development and PyInstaller
        try:
            # First try the bundled path
            icon_path = self.resource_path("Potion.ico")
            
            # For Windows: set both the window icon and taskbar icon
            if os.name == 'nt':  # Windows
                self.root.iconbitmap(default=icon_path)
                # Set taskbar icon
                myappid = 'company.product.subproduct.version'  # arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            else:  # For other operating systems
                icon_img = PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_img)
                
        except Exception as e:
            print(f"Could not load icon: {e}")
            # Continue without icon if there's an error
            pass

        # Center the window on the screen
        self.center_window(1200, 800)
        
        # Bottom frame for Appearance Mode options
        ## Moved here to stop other frames from pushing it out of view
        self.add_appearance_mode_frame()

        # Main container to hold both the tabview and exe selector
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        #self.main_frame.pack_propagate(False)

        # Create the frame for the tabs (Filter Games, Advanced Configs, and Playlists)
        self.tabview_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="transparent")
        self.tabview_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # Create the exe selector frame (on the right side)
        self.exe_selector_frame = ctk.CTkFrame(self.main_frame, width=300, corner_radius=10)
        self.exe_selector_frame.pack(side="right", fill="y", padx=10, pady=(0, 10))  # Adjusted padding

        # Create tab view and initialize the tabs for each class
        self.tabview = ctk.CTkTabview(self.tabview_frame, corner_radius=10, fg_color="transparent")
        self.tabview.pack(expand=True, fill="both")
        
        # Check if the zzzSettings folder exists before adding the Themes tab
        self.zzz_settings_path = os.path.join(os.getcwd(), "collections", "zzzSettings")
        if self.check_zzz_settings_folder():
            self.Themes_games_tab = self.tabview.add("Themes")
            self.Themes_games = Themes(self.Themes_games_tab)

        # Advanced Configurations tab
        self.advanced_configs_tab = self.tabview.add("Advanced Configs")
        self.advanced_configs = AdvancedConfigs(self.advanced_configs_tab)

        # Playlists tab
        # Playlists tab
        self.playlists_tab = self.tabview.add("Playlists")
        self.playlists = Playlists(self.root, self.playlists_tab)  # Pass root here

        # Filter Games tab
        self.filter_games_tab = self.tabview.add("Filter Games")
        self.filter_games = FilterGames(self.filter_games_tab)

        # Controls tab
        ##self.controls_tab = self.tabview.add("Controls")
        ##self.controls = Controls(self.controls_tab)
    
        # Bind cleanup to window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Add exe file selector on the right side
        self.exe_selector = ExeFileSelector(self.exe_selector_frame) 
        
        # Bottom frame for Appearance Mode options
        #self.add_appearance_mode_frame()
    
    def on_closing(self):
        if hasattr(self, 'controls'):
            self.controls.cleanup()
        self.root.destroy()

    def check_zzz_settings_folder(self):
        """Check if the zzzSettings folder exists."""
        if not os.path.isdir(self.zzz_settings_path):
            print(f"Warning: zzzSettings folder not found at: {self.zzz_settings_path}")
            return False
        return True
    
    def add_appearance_mode_frame(self):
        appearance_frame = ctk.CTkFrame(self.root, corner_radius=10)
        appearance_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ctk.CTkLabel(appearance_frame, text="Appearance Mode", font=("Arial", 14, "bold")).pack(side="left", padx=(20, 10), pady=10)

        appearance_mode_optionmenu = ctk.CTkOptionMenu(
            appearance_frame, values=["Dark", "Light", "System"], command=lambda mode: ctk.set_appearance_mode(mode)
        )
        appearance_mode_optionmenu.pack(side="right", padx=10, pady=10)
        
    def center_window(self, width, height):
        # Get the screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate the position for centering the window
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # Set the window geometry with the calculated position
        self.root.geometry(f"{width}x{height}+{x}+{y}") 

    def run_script(self, script_name):
        try:
            script_path = os.path.join(os.getcwd(), script_name)
            if os.path.isfile(script_path):
                subprocess.run(script_path, shell=True)
            else:
                ctk.CTkMessageBox.showerror("Error", f"The script does not exist: {script_name}")
        except Exception as e:
            ctk.CTkMessageBox.showerror("Error", f"Failed to run {script_name}: {str(e)}")

class Controls:
    def __init__(self, parent):
        self.parent = parent
        self.current_control = None
        self.running = True
        self.controller_thread = None
        self.keyboard_thread = None
        self.capture_active = False
        self.capture_lock = threading.Lock()
        self.input_queue = queue.Queue()
        self.show_friendly_names = False  # New flag for name display toggle
        self.status_fade_after_id = None  # For tracking fade timer
        self.status_message_after_id = None  # For tracking message clear timer
        self.stop_event = threading.Event()  # Event object to signal the keyboard thread to stop
        self.config_manager = ConfigManager()  # Add ConfigManager instance

        # Add list of controls to exclude
        self.excluded_controls = [
            "settings", "deadZone", "left", "right", "up", "down", "prevCyclePlaylist", "nextCyclePlaylist", "nextPlaylist", "prevPlaylist" # Example excluded control
            # Add more excluded control names here
        ]

        # Add list of controls to add
        self.controls_add = [
            "" # Example add control
            # Add more added control names here
        ]

        # Append additional excluded controls from config
        self.excluded_controls.extend(self.config_manager.get_exclude_append())

        # Append additional added controls from config
        self.controls_add.extend(self.config_manager.get_controls_add())

        # Add a reverse mapping from friendly names to internal names
        self.reverse_button_map = {
            "joyButton0": "BTN_SOUTH",  # A
            "joyButton1": "BTN_EAST",   # B
            "joyButton2": "BTN_WEST",   # X
            "joyButton3": "BTN_NORTH",  # Y
            "joyButton4": "BTN_TL",     # L1
            "joyButton5": "BTN_TR",     # R1
            "joyButton6": "BTN_START",  # Start
            "joyButton7": "BTN_SELECT", # Select
            "joyButton8": "BTN_THUMBL", # L3
            "joyButton9": "BTN_THUMBR", # R3
            "joyButton10": "ABS_Z",     # L2
            "joyButton11": "ABS_RZ",    # R2
        }
        
        # Initialize controls_config as empty dict - will be populated from config file
        self.controls_config = {}

        self.button_map = {
            "BTN_SOUTH": 0,
            "BTN_EAST": 1,
            "BTN_WEST": 2,
            "BTN_NORTH": 3,
            "BTN_TL": 4,
            "BTN_TR": 5,
            "BTN_SELECT": 7,
            "BTN_START": 6,
            "BTN_THUMBL": 8,
            "BTN_THUMBR": 9,
            "BTN_THUMBL2": 12,  # L3
            "BTN_THUMBR2": 13,  # R3
        }

        self.friendly_names = {
            "BTN_SOUTH": "A",
            "BTN_EAST": "B",
            "BTN_WEST": "X",
            "BTN_NORTH": "Y",
            "BTN_TL": "L1",
            "BTN_TR": "R1",
            "BTN_SELECT": "Select",
            "BTN_START": "Start",
            "BTN_THUMBL": "L3",
            "BTN_THUMBR": "R3",
            "BTN_THUMBL2": "L3",
            "BTN_THUMBR2": "R3",
            "ABS_Z": "L2",
            "ABS_RZ": "R2",
        }

        # Add mapping from friendly names to internal names
        self.friendly_to_internal = {
            "A": "joyButton0",
            "B": "joyButton1",
            "X": "joyButton2",
            "Y": "joyButton3",
            "L1": "joyButton4",
            "R1": "joyButton5",
            "Select": "joyButton7",
            "Start": "joyButton6",
            "L3": "joyButton8",
            "R3": "joyButton9",
            "L2": "joyButton10",
            "R2": "joyButton11",
        }

        self.control_frames = {}
        self.control_entries = {}

        # Load config before creating layout
        self.load_config()
        self.create_layout()
        self.refresh_all_entries()
        self.check_controller()

    ''' hidden controller monitor function
    ## Code to allow R2, and L2 to be used. Keep
    def monitor_controller_input(self):
        """Monitor controller input until a button is pressed or capture is stopped"""
        print("Controller monitoring started")
        try:
            while True:
                with self.capture_lock:
                    if not self.capture_active:
                        print("Controller thread - capture inactive, exiting")
                        return

                try:
                    if not devices.gamepads:
                        time.sleep(0.1)
                        continue

                    events = get_gamepad()
                    for event in events:
                        with self.capture_lock:
                            if not self.capture_active:
                                return

                        # Handle button events
                        if event.ev_type == "Key" and event.state == 1:
                            if event.code in self.button_map:
                                button_num = self.button_map[event.code]
                                button_name = f"joyButton{button_num}"
                                friendly_name = self.friendly_names.get(event.code, button_name)
                                print(f"Controller button pressed: {friendly_name}")
                                with self.capture_lock:
                                    self.capture_active = False
                                self.parent.after(0, self._safe_update_entry, button_name, friendly_name)
                                return

                        # Handle L2 and R2 analog trigger events
                        elif event.ev_type == "Absolute":
                            # Define thresholds to consider analog triggers as "pressed"
                            analog_threshold = 10  # Customize this threshold as needed

                            if event.code == "ABS_Z":  # L2 trigger
                                if event.state > analog_threshold:
                                    button_name = "joyButton10"
                                    friendly_name = self.friendly_names.get(event.code, button_name)
                                    print(f"Controller analog trigger pressed: {friendly_name}")
                                    with self.capture_lock:
                                        self.capture_active = False
                                    self.parent.after(0, self._safe_update_entry, button_name, friendly_name)
                                    return

                            elif event.code == "ABS_RZ":  # R2 trigger
                                if event.state > analog_threshold:
                                    button_name = "joyButton11"
                                    friendly_name = self.friendly_names.get(event.code, button_name)
                                    print(f"Controller analog trigger pressed: {friendly_name}")
                                    with self.capture_lock:
                                        self.capture_active = False
                                    self.parent.after(0, self._safe_update_entry, button_name, friendly_name)
                                    return

                    time.sleep(0.01)
                except Exception as e:
                    print(f"Controller monitoring error: {e}")
                    time.sleep(0.1)
        finally:
            print("Controller monitoring ended")
    '''
    
    def monitor_controller_input(self):
        """Monitor controller input until a button is pressed or capture is stopped"""
        print("Controller monitoring started")
        last_trigger_time = 0
        debounce_interval = 0.5  # Time interval in seconds to debounce trigger events

        try:
            while True:
                with self.capture_lock:
                    if not self.capture_active:
                        print("Controller thread - capture inactive, exiting")
                        return

                try:
                    if not devices.gamepads:
                        time.sleep(0.1)
                        continue

                    events = get_gamepad()
                    current_time = time.time()

                    for event in events:
                        with self.capture_lock:
                            if not self.capture_active:
                                return

                        # Handle button events
                        if event.ev_type == "Key" and event.state == 1:
                            if event.code in self.button_map:
                                button_num = self.button_map[event.code]
                                button_name = f"joyButton{button_num}"
                                friendly_name = self.friendly_names.get(event.code, button_name)
                                print(f"Controller button pressed: {friendly_name}")
                                with self.capture_lock:
                                    self.capture_active = False
                                self.parent.after(0, self._safe_update_entry, button_name, friendly_name)
                                return

                        # Handle L2 and R2 analog trigger events
                        elif event.ev_type == "Absolute":
                            # Define thresholds to consider analog triggers as "pressed"
                            analog_threshold = 10  # Customize this threshold as needed

                            if event.code == "ABS_Z":  # L2 trigger
                                if event.state > analog_threshold and (current_time - last_trigger_time) > debounce_interval:
                                    print("L2 trigger pressed: Reserved for cycle playlist")
                                    self.show_status_message("L2 is reserved for cycle playlist.\nPlease make another selection.")
                                    last_trigger_time = current_time
                                    # Do not exit the loop, keep capture active
                                    continue

                            elif event.code == "ABS_RZ":  # R2 trigger
                                if event.state > analog_threshold and (current_time - last_trigger_time) > debounce_interval:
                                    print("R2 trigger pressed: Reserved for cycle playlist")
                                    self.show_status_message("R2 is reserved for cycle playlist.\nPlease make another selection.")
                                    last_trigger_time = current_time
                                    # Do not exit the loop, keep capture active
                                    continue

                    time.sleep(0.01)
                except Exception as e:
                    print(f"Controller monitoring error: {e}")
                    time.sleep(0.1)
        finally:
            print("Controller monitoring ended")

    ''' Hiden handle keyboard function
    # previous function before removing s, and F1, F2
    def handle_keyboard_input(self):
        """Monitor keyboard input until a key is pressed or capture is stopped."""
        print("Keyboard monitoring started")
        try:
            while not self.stop_event.is_set():
                event = keyboard.read_event(suppress=True)
                if event.event_type == keyboard.KEY_DOWN:
                    key_name = event.name.capitalize()
                    print(f"Got keyboard input: {key_name}")

                    if key_name == "Esc":
                        print("Escape key pressed, canceling capture")
                        self.stop_event.set()  # Signal stop event
                        self.parent.after(0, self.stop_capture)  # Safely stop capture from GUI context
                        return

                    self.stop_event.set()
                    self.parent.after(0, self._safe_update_entry, key_name, key_name)
                    return

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("Keyboard monitoring interrupted")
            self.parent.after(0, self.stop_capture)
            return
        except Exception as e:
            print(f"Keyboard error: {e}")

        print("Keyboard monitoring ended")
    '''

    def handle_keyboard_input(self):
        """Monitor keyboard input until a key is pressed or capture is stopped."""
        print("Keyboard monitoring started")
        try:
            while not self.stop_event.is_set():
                event = keyboard.read_event(suppress=True)
                if event.event_type == keyboard.KEY_DOWN:
                    key_name = event.name.capitalize()
                    print(f"Got keyboard input: {key_name}")

                    if key_name == "Esc":
                        print("Escape key pressed, canceling capture")
                        self.stop_event.set()  # Signal stop event
                        self.parent.after(0, self.stop_capture)  # Safely stop capture from GUI context
                        return

                    if key_name == "S":
                        print("S key pressed: Reserved for settings")
                        self.show_status_message("S is reserved for settings.\nPlease make another selection.")
                        # Do not exit the loop, keep capture active
                        continue

                    if key_name == "F1":
                        print("F1 key pressed: Reserved for prevPlaylist")
                        self.show_status_message("F1 is reserved for prevPlaylist.\nPlease make another selection.")
                        # Do not exit the loop, keep capture active
                        continue

                    if key_name == "F2":
                        print("F2 key pressed: Reserved for nextPlaylist")
                        self.show_status_message("F2 is reserved for nextPlaylist.\nPlease make another selection.")
                        # Do not exit the loop, keep capture active
                        continue

                    self.stop_event.set()
                    self.parent.after(0, self._safe_update_entry, key_name, key_name)
                    return

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("Keyboard monitoring interrupted")
            self.parent.after(0, self.stop_capture)
            return
        except Exception as e:
            print(f"Keyboard error: {e}")

        print("Keyboard monitoring ended")


    def stop_capture(self):
        """Stop all input capture and clean up threads"""
        print("Stopping capture...")

        with self.capture_lock:
            was_active = self.capture_active
            self.capture_active = False

        if was_active:
            if self.controller_thread:
                print("Waiting for controller thread...")
                self.controller_thread.join(timeout=0.5)
                if self.controller_thread.is_alive():
                    print("Warning: Controller thread did not exit cleanly")
                self.controller_thread = None

            if self.keyboard_thread:
                print("Waiting for keyboard thread...")
                self.stop_event.set()
                self.keyboard_thread.join(timeout=0.5)
                self.keyboard_thread = None
                self.stop_event.clear()

        self.cleanup_capture()
        print("Capture stopped")

    def cleanup_capture(self):
        """Clean up after capture is complete"""
        print("Cleanup capture called")
        if self.current_control:
            entry = self.control_entries[self.current_control]
            entry.configure(state="normal")
            # Revert the border color of the entry to indicate capture is complete
            entry.configure(border_color="gray", border_width=1)
        self.current_control = None


    def create_layout(self):
        # Main container for left and right columns
        self.main_container = ctk.CTkFrame(self.parent)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Top frame for status and toggle
        self.top_frame = ctk.CTkFrame(self.main_container)
        self.top_frame.pack(fill="x", padx=5, pady=5)

        self.status_label = ctk.CTkLabel(self.top_frame, text="Controller Status: Checking...")
        self.status_label.pack(side="left", pady=5, padx=5)

        # Add name display toggle switch
        self.name_toggle = ctk.CTkSwitch(
            self.top_frame,
            text="Show Friendly Names",
            command=self.toggle_name_display,
            onvalue=True,
            offvalue=False
        )
        self.name_toggle.pack(side="right", padx=5)
        self.name_toggle.deselect()  # Default to internal names (off)

        # Add information button to display instructions
        self.info_button = ctk.CTkButton(
            self.top_frame,
            text="Info",
            command=self.show_instructions
        )
        self.info_button.pack(side="right", padx=5)

        # Left and right columns for control frames
        self.left_column = ctk.CTkFrame(self.main_container)
        self.left_column.pack(side="left", fill="both", expand=True, padx=5)

        self.right_column = ctk.CTkFrame(self.main_container)
        self.right_column.pack(side="right", fill="both", expand=True, padx=5)

        controls_list = list(self.controls_config.keys())
        mid_point = len(controls_list) // 2

        for control in controls_list[:mid_point]:
            self.create_control_frame(self.left_column, control)

        for control in controls_list[mid_point:]:
            self.create_control_frame(self.right_column, control)

        # Fixed-height status frame above the button frame, outside the main_container
        self.status_frame = ctk.CTkFrame(self.parent, height=35)  # Adjust height as needed
        self.status_frame.pack(fill="x", padx=10, pady=(5, 0))

        # Configure message label inside the fixed-height status frame
        self.message_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            height=25,
            fg_color=("gray85", "gray25"),  # Light/dark mode colors
            corner_radius=8
        )
        self.message_label.pack(fill="x", padx=10, pady=5, ipady=5)

        # Initially hide the status message label, but keep space allocated
        self.message_label.pack_forget()

        # Button frame at the bottom
        self.button_frame = ctk.CTkFrame(self.parent)
        self.button_frame.pack(fill="x", padx=10, pady=5)

        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save Controls",
            command=self.save_config
        )
        self.save_button.pack(side="left", padx=5)

        self.reset_button = ctk.CTkButton(
            self.button_frame,
            text="Reset to Defaults",
            command=self.reset_to_defaults
        )
        self.reset_button.pack(side="left", padx=5)

        # Add clear all button
        self.clear_button = ctk.CTkButton(
            self.button_frame,
            text="Clear All Controls",
            command=self.clear_all_controls
        )
        self.clear_button.pack(side="left", padx=5)

        delete_button = ctk.CTkButton(
            self.button_frame,
            text="Delete Custom Config",
            command=self.delete_config_file
        )
        delete_button.pack(side="left", padx=5)

    def show_instructions(self):
        """Display a pop-up with instructions."""

        # Create a new pop-up window
        info_window = ctk.CTkToplevel(self.parent)
        info_window.title("Instructions")
        info_window.geometry("800x500")

        # Ensure the pop-up stays on top
        info_window.transient(self.parent)  # Set it to be transient to the parent
        info_window.lift()  # Bring it to the front
        info_window.focus_force()  # Give it focus

        # Center the pop-up window on the screen
        window_width = 800
        window_height = 500
        screen_width = info_window.winfo_screenwidth()
        screen_height = info_window.winfo_screenheight()
        x_coordinate = (screen_width // 2) - (window_width // 2)
        y_coordinate = (screen_height // 2) - (window_height // 2)
        info_window.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

        # Add a bold title
        title_label = ctk.CTkLabel(
            info_window, 
            text="Instructions", 
            font=("Arial", 20, "bold")  # Adjust the font size and make it bold
        )
        title_label.pack(pady=(10, 5))  # Add some padding around the title

        # Create a scrollable frame for content
        content_frame = ctk.CTkScrollableFrame(info_window)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Define instruction items with heading and explanation
        instructions = [
            ("Clear a Single Setting:", "Double-click the left mouse button in the text area."),
            ("Clear All Settings:", "Use the 'Clear All' button."),
            ("Capture:", "Click 'Capture' to input a button or keyboard key. * The 'Capture' button must be pressed for each input."),
            ("Cancel Capture:", "Click the 'Capture' button again or press 'ESC' to cancel input."),
            ("Type:", "You can also type directly in the text area, but using the 'Capture' button is recommended."),
            ("Delete Custom Configuration:", "Deletes the controls5.conf file and reverts to using standard controls from controls.conf."),
            ("Reset to Defaults:", "Takes the values from controls.conf and applies them to the GUI."),
            ("Save Controls:", "When you click 'Save Controls,' the controls5.conf file will be created.")
        ]


        # Display instructions with formatted headings
        for heading, explanation in instructions:
            # Heading in bold
            heading_label = ctk.CTkLabel(
                content_frame, 
                text=heading, 
                font=("Arial", 16, "bold")
            )
            heading_label.pack(anchor="w", pady=(5, 0))

            # Explanation in normal font
            explanation_label = ctk.CTkLabel(
                content_frame, 
                text=explanation, 
                font=("Arial", 14)
            )
            explanation_label.pack(anchor="w", padx=10, pady=(0, 5))

    def delete_config_file(self):
        """Delete the controls file specified in the ini file."""
        # Get the controls file path from the ini configuration
        config_file_path = self.config_manager.get_controls_file()
        
        try:
            # Check if the file exists
            if os.path.exists(config_file_path):
                os.remove(config_file_path)
                print(f"{config_file_path} has been deleted.")
                self.show_status_message(f"{config_file_path} has been deleted.")
            else:
                print(f"{config_file_path} does not exist.")
                self.show_status_message(f"{config_file_path} does not exist.")
        except Exception as e:
            print(f"Error deleting {config_file_path}: {e}")
            self.show_status_message(f"Error deleting {config_file_path}: {e}")

    def show_status_message(self, message, duration=2000):
        # Show the status label if it's hidden
        self.message_label.pack(fill="x", padx=10, pady=(0, 10), ipady=5)

        # Update the message
        self.message_label.configure(text=message)

        # Cancel any existing scheduled hide to prevent overlap
        if self.status_message_after_id:
            self.parent.after_cancel(self.status_message_after_id)

        # Schedule the message to be hidden
        self.status_message_after_id = self.parent.after(duration, self.hide_status_message)
    
    def hide_status_message(self):
        self.message_label.pack_forget()

    def toggle_name_display(self):
        """Toggle between friendly and internal names in the GUI"""
        self.show_friendly_names = self.name_toggle.get()
        self.refresh_all_entries()

    def refresh_all_entries(self):
        """Refresh all entry displays based on current name display mode"""
        for key, entry in self.control_entries.items():
            internal_values = self.controls_config[key]
            display_values = []

            for value in internal_values:
                if value.startswith('joyButton') and self.show_friendly_names:
                    # Convert internal name to friendly name
                    button_code = self.reverse_button_map.get(value)
                    if button_code:
                        friendly_name = self.friendly_names.get(button_code, value)
                        display_values.append(friendly_name)
                    else:
                        display_values.append(value)
                else:
                    display_values.append(value)

            entry.delete(0, "end")
            entry.insert(0, ', '.join(display_values))  # Add space after comma for GUI

    def create_control_frame(self, parent, control_name):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=2)

        label = ctk.CTkLabel(frame, text=control_name)
        label.pack(side="left", padx=5)

        entry = ctk.CTkEntry(frame)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        entry.insert(0, ', '.join(self.controls_config[control_name]))  # Add space after comma for GUI

        # Bind the double-click event to clear the entry
        entry.bind("<Double-Button-1>", lambda event, cn=control_name: self.clear_entry(cn))

        capture_button = ctk.CTkButton(
            frame,
            text="Capture",
            width=70,
            command=lambda cn=control_name, e=entry: self.toggle_input_capture(cn, e)
        )
        capture_button.pack(side="right", padx=5)

        self.control_frames[control_name] = frame
        self.control_entries[control_name] = entry
        print(f"Created control frame for: {control_name}")

    def toggle_input_capture(self, control_name, entry):
        """Toggle capturing input for a control"""
        if self.current_control == control_name and self.capture_active:
            print(f"Canceling capture for {control_name}")
            self.stop_capture()
            self.cleanup_capture()
        else:
            self.start_input_capture(control_name, entry)

    def clear_entry(self, control_name):
        """Clear the text in the entry box when it is double-clicked"""
        if control_name in self.control_entries:
            self.parent.after(0, self._safe_clear_entry, control_name)
        else:
            self.show_status_message(f"Control '{control_name}' is not valid", color="#ff6b6b")

    def _safe_clear_entry(self, control_name):
        """Safely clear the entry from the main thread"""
        if control_name in self.control_entries:
            self.control_entries[control_name].delete(0, "end")
            self.controls_config[control_name] = []
            #self.show_status_message(f"Control '{control_name}' has been cleared")

    def _safe_update_entry(self, input_name, friendly_name):
        """Safely update the entry from the main thread"""
        print(f"Safe update called with: {input_name} (friendly: {friendly_name})")
        if self.current_control and input_name:
            entry = self.control_entries[self.current_control]
            entry.configure(state="normal")

            # Store internal name in controls_config
            internal_name = input_name  # Assume input_name is already the internal name for keyboard inputs
            self.controls_config[self.current_control].append(internal_name)

            # Display appropriate name based on toggle
            display_name = friendly_name if self.show_friendly_names else internal_name
            current_display = entry.get().split(', ')
            if current_display == ['']:
                current_display = []
            current_display.append(display_name)

            entry.delete(0, "end")
            entry.insert(0, ', '.join(current_display))  # Add space after comma for GUI

            # Revert the border color of the entry to indicate capture is complete
            entry.configure(border_color="gray", border_width=1)

            self.cleanup_capture()

    def clear_all_controls(self):
        """Clear all control bindings"""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all control bindings?"):
            for key in self.controls_config:
                self.controls_config[key] = []
                if key in self.control_entries:
                    self.parent.after(0, self._safe_clear_entry, key)
            self.show_status_message("All controls have been cleared")

    def start_input_capture(self, control_name, entry):
        """Start capturing input for a control"""
        print(f"Starting capture for {control_name}")

        self.stop_capture()

        self.current_control = control_name
        with self.capture_lock:
            self.capture_active = True

        entry.configure(state="disabled")
        entry.delete(0, "end")
        entry.insert(0, "Press key or controller button...")

        # Change the border color of the entry to indicate capture is active
        entry.configure(border_color="white", border_width=2)

        if not self.controller_thread or not self.controller_thread.is_alive():
            self.controller_thread = threading.Thread(target=self.monitor_controller_input)
            self.controller_thread.daemon = True
            self.controller_thread.start()

        if not self.keyboard_thread or not self.keyboard_thread.is_alive():
            self.stop_event.clear()
            self.keyboard_thread = threading.Thread(target=self.handle_keyboard_input)
            self.keyboard_thread.daemon = True
            self.keyboard_thread.start()

    def cleanup(self):
        """Clean up when closing the application"""
        print("Cleaning up...")
        self.running = False
        self.stop_capture()
        print("Cleanup complete")

    def set_excluded_controls(self, excluded_list):
        """Set the list of controls to exclude"""
        self.excluded_controls = excluded_list
        # Reload config to apply new exclusions
        self.load_config()
        # Recreate layout with new config
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.create_layout()
        self.refresh_all_entries()

    def load_config(self):
        """Load configuration from specified controls file or create it from controls.conf"""
        controls_file = self.config_manager.get_controls_file()
        
        try:
            # First try to load the specified controls file
            self.load_config_from_file(controls_file)
        except FileNotFoundError:
            # If specified file doesn't exist, try to create it from controls.conf
            try:
                self.load_config_from_file("controls.conf")
                # Save the loaded config to the specified file
                #self.save_config()
                print(f"Created {controls_file} from controls.conf")
            except FileNotFoundError:
                print(f"Neither {controls_file} nor controls.conf found. Please create a config file.")
                return
            except Exception as e:
                print(f"Error loading controls.conf: {str(e)}")
                return

    def load_config_from_file(self, filename):
        """Load configuration from specified file"""
        self.controls_config.clear()  # Clear existing config
        
        with open(filename, "r") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                try:
                    parts = line.split('=', 1)
                    if len(parts) != 2:
                        print(f"Warning: Invalid format in line {line_number}: {line}")
                        continue

                    key = parts[0].strip()
                    
                    # Skip if this control is in the excluded list, unless it's in controlsAdd
                    controls_add = self.config_manager.get_controls_add()
                    if key in self.excluded_controls and key not in controls_add:
                        print(f"Skipping excluded control: {key}")
                        continue
                        
                    value = parts[1].strip()
                    self.controls_config[key] = [v.strip() for v in value.split(',')]

                except Exception as e:
                    print(f"Error processing line {line_number}: {line}\nError: {str(e)}")
                    continue

        print(f"Successfully loaded configuration from {filename}")

    def save_config(self):
        """Save configuration to specified controls file"""
        controls_file = self.config_manager.get_controls_file()
        try:
            with open(controls_file, "w") as f:
                # First write excluded controls as comments
                for excluded in self.excluded_controls:
                    #f.write(f"# Excluded: {excluded}\n")
                
                # Then write active controls
                    controls_add = self.config_manager.get_controls_add()
                for key, values in self.controls_config.items():
                    if key not in self.excluded_controls or key in controls_add:
                        f.write(f"{key}={','.join(values)}\n")
            self.show_status_message("Controls saved successfully!")
        except Exception as e:
            self.show_status_message(f"Failed to save controls: {e}", color="#ff6b6b")

    def create_default_config(self):
        """Creates controls5.conf by copying contents from root-level controls.conf if it exists."""
        try:
            with open("controls.conf", "r") as root_conf:
                contents = root_conf.read()

            with open("controls5.conf", "w") as new_conf:
                new_conf.write(contents)
            print("controls5.conf created from root-level controls.conf")

        except FileNotFoundError:
            with open("controls5.conf", "w") as new_conf:
                for key, default_values in self.controls_config.items():
                    new_conf.write(f"{key} = {','.join(default_values)}\n")  # No space after comma for config file
            print("controls5.conf created with internal defaults")

        except Exception as e:
            print(f"Failed to create controls5.conf: {str(e)}")

    def reset_to_defaults(self):
        """Reset control settings to defaults by loading from controls.conf or using internal defaults."""
        try:
            with open("controls.conf", "r") as root_conf:
                contents = root_conf.readlines()

            # Parse and apply values from the root config file
            for line in contents:
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue

                try:
                    # Split on first occurrence of '=' and handle potential spacing
                    parts = line.split('=', 1)
                    if len(parts) != 2:
                        print(f"Warning: Invalid format in line: {line}")
                        continue

                    key = parts[0].strip()
                    value = parts[1].strip()
                    internal_values = [v.strip() for v in value.split(',') if v.strip()]  # Handle potential spaces

                    if key in self.control_entries:
                        # Store internal values in controls_config
                        self.controls_config[key] = internal_values

                        # Convert to friendly names if needed for display
                        display_values = []
                        for val in internal_values:
                            if val.startswith('joyButton') and self.show_friendly_names:
                                button_code = self.reverse_button_map.get(val)
                                if button_code:
                                    friendly_name = self.friendly_names.get(button_code, val)
                                    display_values.append(friendly_name)
                                else:
                                    display_values.append(val)
                            else:
                                display_values.append(val)

                        # Update the entry display
                        self.control_entries[key].delete(0, "end")
                        self.control_entries[key].insert(0, ', '.join(display_values))  # Add space after comma for GUI
                    else:
                        print(f"Warning: Unknown control key: {key}")

                except Exception as e:
                    print(f"Error processing line: {line}\nError: {str(e)}")
                    continue

            print("Settings reset to defaults from controls.conf")
            self.show_status_message("Controls reset to defaults from controls.conf")

        except FileNotFoundError:
            # If controls.conf is not found, use internal defaults
            print("controls.conf not found. Resetting to internal default values.")
            for key, default_values in self.controls_config.items():
                if key in self.control_entries:
                    # Store default values
                    self.controls_config[key] = default_values

                    # Convert to friendly names if needed for display
                    display_values = []
                    for val in default_values:
                        if val.startswith('joyButton') and self.show_friendly_names:
                            button_code = self.reverse_button_map.get(val)
                            if button_code:
                                friendly_name = self.friendly_names.get(button_code, val)
                                display_values.append(friendly_name)
                            else:
                                display_values.append(val)
                        else:
                            display_values.append(val)

                    # Update the entry display
                    self.control_entries[key].delete(0, "end")
                    self.control_entries[key].insert(0, ', '.join(display_values))  # Add space after comma for GUI

            self.show_status_message("Controls reset to internal defaults")

        except Exception as e:
            print(f"Failed to reset controls to defaults: {str(e)}")
            self.show_status_message(f"Failed to reset controls: {str(e)}", color="#ff6b6b")

        ## Commented out for now, so it doesnt auto save, as I want to only create custom control file once users manually saves
        # Save the configuration after resetting
        self.save_config()

    def check_controller(self):
        if not self.running:
            return

        try:
            gamepads = [device for device in devices.gamepads]
            if gamepads:
                controller_name = gamepads[0].name
                self.status_label.configure(
                    text=f"Controller Status: Connected ({controller_name})"
                )
            else:
                self.status_label.configure(text="Controller Status: Not Connected")
        except Exception as e:
            self.status_label.configure(text=f"Controller Status: Error ({str(e)})")

        self.parent.after(1000, self.check_controller)

class ConfigManager:

    def __init__(self):
        self.base_path = os.getcwd()
        self.config_path = os.path.join(self.base_path, "autochanger", "customisation.ini")
        self.config = configparser.ConfigParser()
        self.initialize_config()

    '''cycle_playlist = , and exluded =  can be added manually. I hide them so users dont break it.
    - If the key is missing in the INI file, use the hardcoded default values.
    - If the key exists and has values, use those values from the INI file.
    - If the key exists but has no values (e.g., an empty string), do not use the hardcoded defaults—instead, return an empty list to indicate no values are set.
    Note: For excluded = this means it will return all results if key exists but no values'''
    def initialize_config(self):
        """Initialize the INI file with default values if it doesn't exist."""
        config_exists = os.path.exists(self.config_path)

        # Helper function to determine build type
        def get_build_type():
            shutdown_path = os.path.join(self.base_path, "collections", "zzzShutdown")
            autochanger_path = os.path.join(self.base_path, "- Themes")
            
            if os.path.exists(shutdown_path):
                return 'U'
            elif os.path.exists(autochanger_path):
                return 'S'
            return ''  # Return empty string if neither exists

        if not config_exists:
            # Only create new config file if it doesn't exist
            self.config['Settings'] = {
                'settings_file': '5_7',
                'build_type': get_build_type(),
                'theme_location': '',  # Changed to empty by default
                'custom_roms_path': '',
                'custom_videos_path': '',
                'custom_logos_path': '',
                'show_location_controls': 'False'
            }

            # Add new Controls section with defaults
            self.config['Controls'] = {
                'controls_file': 'controls5.conf',
                'excludeAppend': '',
                'controlsAdd': ''
            }

            self.save_config()
        else:
            # Just read existing config
            self.config.read(self.config_path)
            
            # If Settings section is missing, create it
            if 'Settings' not in self.config:
                self.config['Settings'] = {}
                needs_save = True
            else:
                needs_save = False

            # If Controls section is missing, create it
            if 'Controls' not in self.config:
                self.config['Controls'] = {}
                needs_save = True

            # Check build_type and theme_location
            current_build_type = self.config['Settings'].get('build_type', '')
            current_theme_location = self.config['Settings'].get('theme_location', '')
            
            # Only update build_type if theme_location isn't manually set
            if not current_theme_location:
                detected_build_type = get_build_type()
                if detected_build_type != current_build_type:
                    self.config['Settings']['build_type'] = detected_build_type
                    self.config['Settings']['theme_location'] = ''  # Clear theme_location
                    needs_save = True
                    print(f"Updating build_type to: {detected_build_type}")  # Debug print
                
            # Only add missing keys if they don't exist
            settings_defaults = {
                'theme_location': '',  # Empty by default
                'custom_roms_path': '',
                'custom_videos_path': '',
                'custom_logos_path': '',
                'show_location_controls': 'True'
            }
            
            controls_defaults = {
                'controls_file': 'controls5.conf',
                'excludeAppend': '',
                'controlsAdd': ''
            }
            
            for key, default_value in settings_defaults.items():
                if key not in self.config['Settings']:
                    self.config['Settings'][key] = default_value
                    needs_save = True
            
            for key, default_value in controls_defaults.items():
                if key not in self.config['Controls']:
                    self.config['Controls'][key] = default_value
                    needs_save = True
                    
            # Only save if we added missing keys
            if needs_save:
                self.save_config()

    def check_theme_folder(self):
        """Check if the configured theme folder exists"""
        # First check if there's a manual theme_location set
        theme_location = self.config.get('Settings', 'theme_location', fallback='')
        if theme_location:
            if theme_location == 'custom':
                # For custom paths, check if the custom roms path exists
                custom_paths = self.get_theme_paths()
                return os.path.exists(custom_paths['roms'])
            elif theme_location == 'zzzSettings':
                # Check zzzSettings path
                return os.path.exists(os.path.join(os.getcwd(), "collections", "zzzSettings"))
            elif theme_location == 'zzzShutdown':
                # Check zzzShutdown path
                return os.path.exists(os.path.join(os.getcwd(), "collections", "zzzShutdown"))
            elif theme_location == 'autochanger':
                # Check autochanger path
                return os.path.exists(os.path.join(os.getcwd(), "- Themes"))
        else:
            # Use build_type if no manual theme_location is set
            build_type = self.config.get('Settings', 'build_type', fallback='')
            if build_type == 'U':
                return os.path.exists(os.path.join(os.getcwd(), "collections", "zzzShutdown"))
            elif build_type == 'S':
                return os.path.exists(os.path.join(os.getcwd(), "- Themes"))
        return False

    def get_theme_paths(self):
        """Get the paths for theme-related content based on configuration."""
        theme_location = self.config.get('Settings', 'theme_location', fallback='')
        build_type = self.config.get('Settings', 'build_type', fallback='')

        print(f"Debug - Using theme_location: {theme_location}, build_type: {build_type}")  

        # First handle build_type if no manual theme_location is set
        if not theme_location:
            if build_type == 'U':
                return {
                    'roms': os.path.join(self.base_path, "collections", "zzzShutdown", "roms"),
                    'videos': os.path.join(self.base_path, "collections", "zzzShutdown", "medium_artwork", "video"),
                    'logos': os.path.join(self.base_path, "collections", "zzzShutdown", "medium_artwork", "logos")
                }
            elif build_type == 'S':
                return self.get_default_paths()
            return self.get_default_paths()  # fallback if build_type is empty
            
        # Then handle theme_location if it's set
        if theme_location == 'custom':
            custom_paths = {
                'roms': self.config.get('Settings', 'custom_roms_path', fallback=''),
                'videos': self.config.get('Settings', 'custom_videos_path', fallback=''),
                'logos': self.config.get('Settings', 'custom_logos_path', fallback='')
            }           
            return custom_paths            
        elif theme_location == 'zzzSettings':
            return {
                'roms': os.path.join(self.base_path, "collections", "zzzSettings", "roms"),
                'videos': os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "video"),
                'logos': os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "logos")
            }
        elif theme_location == 'zzzShutdown':
            return {
                'roms': os.path.join(self.base_path, "collections", "zzzShutdown", "roms"),
                'videos': os.path.join(self.base_path, "collections", "zzzShutdown", "medium_artwork", "video"),
                'logos': os.path.join(self.base_path, "collections", "zzzShutdown", "medium_artwork", "logos")
            }
        elif theme_location == 'autochanger':
            return self.get_default_paths()

        # Final fallback
        return self.get_default_paths()

    def get_default_paths(self):
        """Get the default autochanger paths."""
        return {
            'roms': os.path.join(self.base_path, "- Themes"),
            'videos': os.path.join(self.base_path, "autochanger", "themes", "video"),
            'logos': os.path.join(self.base_path, "autochanger", "themes", "logo")
        }

    def update_theme_location(self, location: str):
        """Update the theme location configuration."""
        try:
            if location not in ['autochanger', 'zzzSettings', 'zzzShutdown', 'custom']:
                raise ValueError("Invalid theme location. Must be 'autochanger', 'zzzSettings', 'zzzShutdown',or 'custom'")
            self.config.set('Settings', 'theme_location', location)
            self.save_config()
        except Exception as e:
            print(f"Error updating theme location: {str(e)}")

    def update_custom_paths(self, roms_path: str = None, videos_path: str = None, logos_path: str = None):
        """Update custom paths in the configuration."""
        try:
            if roms_path is not None:
                self.config.set('Settings', 'custom_roms_path', roms_path)
            if videos_path is not None:
                self.config.set('Settings', 'custom_videos_path', videos_path)
            if logos_path is not None:
                self.config.set('Settings', 'custom_logos_path', logos_path)
            self.save_config()
        except Exception as e:
            print(f"Error updating custom paths: {str(e)}")

    def get_playlist_location(self):
        """Get the playlist location setting from INI file"""
        try:
            return self.config.get('Settings', 'build_type', fallback='S')
        except:
            return 'S'  # Default to 'S' if setting not found

    def get_controls_file(self) -> str:
        """Get the controls file name."""
        return self.config.get('Controls', 'controls_file', fallback='controls5.conf')

    def get_exclude_append(self) -> List[str]:
        """Get the list of additional controls to exclude."""
        exclude_str = self.config.get('Controls', 'excludeAppend', fallback='')
        return [item.strip() for item in exclude_str.split(',') if item.strip()]

    def get_controls_add(self) -> List[str]:
        """Get the list of controls to add (ignoring exclude list)."""
        controls_str = self.config.get('Controls', 'controlsAdd', fallback='')
        return [item.strip() for item in controls_str.split(',') if item.strip()]

    def update_controls_file(self, filename: str):
        """Update the controls file name."""
        try:
            self.config.set('Controls', 'controls_file', filename)
            self.save_config()
        except Exception as e:
            print(f"Error updating controls file: {str(e)}")

    def update_exclude_append(self, controls: List[str]):
        """Update the excludeAppend list."""
        try:
            self.config.set('Controls', 'excludeAppend', ', '.join(controls))
            self.save_config()
        except Exception as e:
            print(f"Error updating excludeAppend: {str(e)}")

    def update_controls_add(self, controls: List[str]):
        """Update the controlsAdd list."""
        try:
            self.config.set('Controls', 'controlsAdd', ', '.join(controls))
            self.save_config()
        except Exception as e:
            print(f"Error updating controlsAdd: {str(e)}")

    def toggle_location_controls(self):
        """Toggle the visibility of location control elements"""
        current_value = self.config.getboolean('Settings', 'show_location_controls', fallback=True)
        self.config['Settings']['show_location_controls'] = str(not current_value)
        self.save_config()

    def save_config(self):
        """Save the current configuration to the INI file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def get_settings_file(self) -> str:
        """Get the settings file name."""
        try:
            settings_value = self.config.get('Settings', 'settings_file', fallback='5_7')
            return f"settings{settings_value}.conf"
        except Exception as e:
            print(f"Error reading settings file: {str(e)}")
            return "settings5_7.conf"

    def get_cycle_playlist(self) -> List[str]:
        """Get the cycle playlist configuration based on the specific conditions."""
        try:
            if self.config.has_option('Settings', 'cycle_playlist'):
                playlists = self.config.get('Settings', 'cycle_playlist')
                if playlists:  # Non-empty value in INI
                    return [item.strip() for item in playlists.split(',') if item.strip()]
                else:  # Key exists but is empty
                    return []
            else:
                # Key is missing, use hardcoded default
                return ["arcader", "consoles", "favorites", "lastplayed"]
        except Exception as e:
            print(f"Error reading cycle playlist: {str(e)}")
            return ["arcader", "consoles", "favorites", "lastplayed"]

    def get_excluded_playlists(self) -> List[str]:
        """Get the excluded playlists configuration based on the specific conditions."""
        try:
            if self.config.has_option('Settings', 'excluded'):
                excluded = self.config.get('Settings', 'excluded')
                if excluded:  # Non-empty value in INI
                    return [item.strip() for item in excluded.split(',') if item.strip()]
                else:  # Key exists but is empty
                    return []
            else:
                # Key is missing, use hardcoded default
                return ["arcades40", "arcades60", "arcades80", "arcades120", "arcades150", 
                        "arcades220", "arcader", "arcades", "consoles", "favorites", 
                        "lastplayed", "settings"]
        except Exception as e:
            print(f"Error reading excluded playlists: {str(e)}")
            return ["arcades40", "arcades60", "arcades80", "arcades120", "arcades150", 
                    "arcades220", "arcader", "arcades", "consoles", "favorites", 
                    "lastplayed", "settings"]

    def update_cycle_playlist(self, playlists: List[str]):
        """Update the cycle playlist configuration."""
        try:
            self.config.set('Settings', 'cycle_playlist', ', '.join(playlists))
            self.save_config()
        except Exception as e:
            print(f"Error updating cycle playlist: {str(e)}")

    def update_excluded_playlists(self, playlists: List[str]):
        """Update the excluded playlists configuration."""
        try:
            self.config.set('Settings', 'excluded', ', '.join(playlists))
            self.save_config()
        except Exception as e:
            print(f"Error updating excluded playlists: {str(e)}")

    def update_settings_file(self, settings_value: str):
        """Update the settings file configuration."""
        try:
            self.config.set('Settings', 'settings_file', settings_value)
            self.save_config()
        except Exception as e:
            print(f"Error updating settings file: {str(e)}")      

class ExeFileSelector:
    def __init__(self, parent_frame):
        # Store a reference to the parent frame
        self.parent_frame = parent_frame
        
        # Create a new frame for the .exe radio buttons with fixed size
        self.exe_frame = ctk.CTkFrame(parent_frame, width=300, height=400, corner_radius=10)  # Fixed width and height
        self.exe_frame.grid(row=1, column=1, sticky="nswe", padx=10, pady=10)
        
        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        # Determine the path for the logo
        logo_path = 'autochanger/Logo.png'
        default_logo_path = os.path.join(getattr(sys, '_MEIPASS', '.'), 'Logo.png')
        logo_image_path = logo_path if os.path.exists(logo_path) else default_logo_path

        try:
            # Load the original image
            logo_original = Image.open(logo_image_path)
            
            # Set maximum dimensions
            MAX_WIDTH = 300  # Maximum width in pixels
            MAX_HEIGHT = 150  # Maximum height in pixels
            
            # Calculate scaled dimensions while maintaining aspect ratio
            width_ratio = MAX_WIDTH / logo_original.width
            height_ratio = MAX_HEIGHT / logo_original.height
            scale_ratio = min(width_ratio, height_ratio)
            
            new_width = int(logo_original.width * scale_ratio)
            new_height = int(logo_original.height * scale_ratio)
            
            # Create the CTkImage with the calculated dimensions
            logo_image = ctk.CTkImage(
                light_image=logo_original,
                dark_image=logo_original,
                size=(new_width, new_height)
            )
            
            # Add the logo label to the exe_frame
            logo_label = ctk.CTkLabel(self.exe_frame, text="", image=logo_image)
            logo_label.pack(pady=(10, 0))
            
        except Exception as e:
            # Fallback in case loading the image fails
            title_label = ctk.CTkLabel(self.exe_frame, text="Select Executable", font=("Arial", 14, "bold"))
            title_label.pack(padx=10, pady=10)
            print(f"Error loading logo: {e}")

        # Create a scrollable frame inside exe_frame to hold the radio buttons
        self.scrollable_frame = ctk.CTkScrollableFrame(self.exe_frame, width=300, height=200, corner_radius=10)  # Set fixed width
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Find all .exe files in the directory
        self.exe_files = self.find_exe_files()
        
        # Variable to hold the selected exe file
        self.exe_var = tk.StringVar(value="")
        
        # Add a radio button for each .exe file found inside the scrollable frame
        for exe in self.exe_files:
            rbutton = ctk.CTkRadioButton(self.scrollable_frame, text=exe, variable=self.exe_var, value=exe)
            rbutton.pack(anchor="w", padx=20, pady=5)

        # Add a switch to control closing the GUI
        self.close_gui_switch = ctk.CTkSwitch(
            self.exe_frame,
            text="Close GUI After Running",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=True),
            command=self.update_switch_text
        )
        self.close_gui_switch.pack(pady=10)
        
        # Update switch text initially
        self.update_switch_text()
        
        # Add a button to run the selected exe
        run_exe_button = ctk.CTkButton(self.exe_frame, text="Run Selected Executable", command=self.run_selected_exe)
        run_exe_button.pack(pady=20)
        
        # Call a method to add the batch file dropdown and button frame below this frame
        self.add_batch_file_dropdown(parent_frame)

    def update_switch_text(self):
        if self.close_gui_switch.get():
            # True/default Value - Gui will close on run
            self.close_gui_switch.configure(text="Exit the GUI after execution")
        else:
            # False value - Gui will stay open on run
            self.close_gui_switch.configure(text="Stay in the GUI after execution")

    
    def add_batch_file_dropdown(self, parent_frame):
        # Create a frame for batch file dropdown below the exe frame
        self.batch_file_frame = ctk.CTkFrame(parent_frame, corner_radius=10, fg_color="transparent")
        self.batch_file_frame.grid(row=2, column=1, sticky="nswe", padx=20, pady=(5, 10))

        # Add a title for the reset section
        reset_label = ctk.CTkLabel(self.batch_file_frame, text="Reset Build to Defaults", font=("Arial", 14, "bold"))
        reset_label.pack(pady=(10, 5))

        # Find all batch files in the current directory with "Restore" in their names
        batch_files = self.find_reset_batch_files()

        # Extract clean names for display, but keep original for execution
        display_names = [os.path.splitext(batch_file)[0].replace("- ", "") for batch_file in batch_files]

        # Variable to hold the selected batch file name
        self.selected_batch = tk.StringVar(value=display_names[0])  # Set default to the first script found

        # Create a dropdown (combobox) with cleaned names
        self.dropdown = ctk.CTkComboBox(self.batch_file_frame, values=display_names, variable=self.selected_batch)
        self.dropdown.pack(padx=10, pady=10, fill='x')

        # Add a button to run the selected batch script
        run_batch_button = ctk.CTkButton(
            self.batch_file_frame, text="Run Selected Script", command=self.run_selected_script, hover_color="red"
        )
        run_batch_button.pack(pady=10, padx=10, fill='x')

    def find_reset_batch_files(self):
        """Find all .bat files in the current directory that have 'Restore' in their name."""
        base_path = os.getcwd()
        return [f for f in os.listdir(base_path) if f.endswith('.bat') and "Restore" in f]

    def run_selected_script(self):
        # Get the selected display name and find the corresponding batch file
        selected_display_name = self.selected_batch.get()
        batch_files = self.find_reset_batch_files()

        # Find the batch file that matches the display name (without "- ")
        matching_batch = next(
            (bf for bf in batch_files if os.path.splitext(bf)[0].replace("- ", "") == selected_display_name), None
        )

        if matching_batch:
            self.run_script(matching_batch)
        else:
            messagebox.showerror("File Not Found", f"No matching batch file found for '{selected_display_name}'.")

    def run_script(self, script_name):
        confirm = messagebox.askyesno(
            "Confirmation",
            f"Are you sure you want to run the '{script_name}' script?"
        )

        if not confirm:
            return  # Exit if the user selects "No"

        try:
            script_path = os.path.join(os.getcwd(), script_name)

            # Check if the script exists
            if not os.path.isfile(script_path):
                messagebox.showerror("File Not Found", f"The script does not exist at the path: {script_path}")
                return

            print(f"Attempting to run script at: {script_path}")

            # Create a modal progress window
            progress_window = tk.Toplevel(self.parent_frame)
            progress_window.title("Running Script")
            
            # Make it modal (blocks main window interaction)
            progress_window.grab_set()
            
            # Center the progress window
            window_width = 400
            window_height = 150
            screen_width = progress_window.winfo_screenwidth()
            screen_height = progress_window.winfo_screenheight()
            center_x = int((screen_width - window_width) / 2)
            center_y = int((screen_height - window_height) / 2)
            progress_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
            
            # Make it non-resizable and always on top
            progress_window.resizable(False, False)
            progress_window.transient(self.parent_frame)
            progress_window.attributes('-topmost', True)

            # Add message
            message_label = ctk.CTkLabel(
                progress_window,
                text="Please wait while the restore script runs...\n\nThis window will close automatically when complete.",
                font=("Arial", 12),
                wraplength=350
            )
            message_label.pack(pady=20, padx=20)

            # Add spinning progress indicator
            progress = ctk.CTkProgressBar(progress_window)
            progress.pack(pady=10, padx=20)
            progress.configure(mode='indeterminate')
            progress.start()

            # Function to run the script and close the progress window
            def run_script_thread():
                try:
                    # Run the batch file
                    subprocess.run(
                        f'cmd.exe /c "{script_path}"',
                        shell=True,
                        text=True,
                        check=False
                    )
                    
                    # Schedule the window closure and success message on the main thread
                    progress_window.after(0, lambda: [
                        progress_window.destroy(),
                        messagebox.showinfo("Success", "Restore Defaults (Arcades and Consoles) has completed.")
                    ])
                    
                except Exception as e:
                    # Schedule error handling on the main thread
                    progress_window.after(0, lambda: [
                        progress_window.destroy(),
                        messagebox.showerror("Error", f"An error occurred: {str(e)}")
                    ])

            # Run the script in a separate thread
            thread = Thread(target=run_script_thread)
            thread.daemon = True
            thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred while running {script_name}: {str(e)}")

    def find_exe_files(self):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            current_exe = os.path.basename(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            current_exe = None

        print(f"Base path: {base_path}")
        print(f"Files in directory: {os.listdir(base_path)}")
        return [f for f in os.listdir(base_path) if f.endswith('.exe') and f != current_exe]

    def run_selected_exe(self):
        selected_exe = self.exe_var.get()
        if selected_exe:
            exe_path = os.path.join(os.getcwd(), selected_exe)
            try:
                os.startfile(exe_path)
                if self.close_gui_switch.get():
                    self.parent_frame.winfo_toplevel().destroy()
                time.sleep(1)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run {selected_exe}: {e}")
        else:
            messagebox.showinfo("No Selection", "Please select an executable.")

class FilterGames:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.output_dir = 'collections\\Arcades\\'
        self.output_file = os.path.join(self.output_dir, "include.txt")

        # Control type mapping for dropdown and checkboxes
        self.control_type_mapping = {
            "8 way": "8 way",
            "4 way": "4 way",
            "analog": "analog",
            "trackball": "trackball",
            "twin stick": "twin stick",
            "lightgun": "lightgun",
            "Vertical Games Only": "VERTICAL"
        }

        self.load_custom_dll()
        self.csv_file_path = self.get_csv_file_path()
        
        # Create main UI
        self.create_main_interface()
    
    def create_main_interface(self):
        # Create main container frame with weight distribution
        main_container = ctk.CTkFrame(self.parent_tab)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # Create left sidebar frame (1/3 width)
        sidebar_frame = ctk.CTkFrame(main_container, width=200, corner_radius=10)
        sidebar_frame.pack(side='left', fill='y', padx=10, pady=10)

        # Create right content frame (2/3 width)
        right_frame = ctk.CTkFrame(main_container, corner_radius=10)
        right_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        # Initialize status bar first
        self.status_bar = ctk.CTkLabel(right_frame, text="Ready", anchor='w')
        
        # Create a TabView for Control Types, Buttons, and Vertical Filter
        tabview = ctk.CTkTabview(sidebar_frame, width=200)
        tabview.pack(fill='both', expand=True, padx=10, pady=10)

        # Add Control Types, Buttons, and Vertical tabs
        control_types_tab = tabview.add("Control Types")
        buttons_tab = tabview.add("Buttons")
        vertical_tab = tabview.add("Vertical")

        # Control Types checkboxes
        self.control_type_vars = {}
        control_types = ["8 way", "4 way", "analog", "trackball", "twin stick", "lightgun"]
        control_label = ctk.CTkLabel(control_types_tab, text="Control Types", font=("Arial", 14, "bold"))
        control_label.pack(pady=(10,5))

        for control_type in control_types:
            var = tk.IntVar()
            checkbox = ctk.CTkCheckBox(control_types_tab, text=control_type, variable=var, command=self.update_filtered_list)
            checkbox.pack(padx=20, pady=5, anchor='w')
            self.control_type_vars[control_type] = var

        # Buttons tab content
        self.buttons_var = ctk.StringVar(value="Select number of buttons")
        self.buttons_var.trace('w', lambda *args: self.update_filtered_list())
        button_options = ["Select number of buttons", "0", "1", "2", "3", "4", "5", "6"]
        buttons_label = ctk.CTkLabel(buttons_tab, text="Number of Buttons", font=("Arial", 14, "bold"))
        buttons_label.pack(pady=(10,5))
        buttons_dropdown = ctk.CTkOptionMenu(buttons_tab, variable=self.buttons_var, values=button_options)
        buttons_dropdown.pack(padx=20, pady=5)

        # Players tab content
        self.players_var = ctk.StringVar(value="Select number of players")
        self.players_var.trace('w', lambda *args: self.update_filtered_list())
        player_options = ["Select number of players", "1", "2", "3", "4", "5", "6", "7", "8"]
        players_label = ctk.CTkLabel(buttons_tab, text="Number of Players", font=("Arial", 14, "bold"))
        players_label.pack(pady=(10, 5))
        players_dropdown = ctk.CTkOptionMenu(buttons_tab, variable=self.players_var, values=player_options)
        players_dropdown.pack(padx=20, pady=5)

        # Vertical tab content
        self.vertical_checkbox_var = tk.IntVar()
        vertical_checkbox = ctk.CTkCheckBox(vertical_tab, text="Include only Vertical Games", 
                                          variable=self.vertical_checkbox_var,
                                          command=self.update_filtered_list)
        vertical_checkbox.pack(padx=20, pady=10, anchor='w')

        # Button frame at bottom of sidebar
        button_frame = ctk.CTkFrame(sidebar_frame)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        # Filter, Clear Filters, and Reset buttons
        filter_button = ctk.CTkButton(button_frame, text="Save Filter", command=self.filter_games_from_csv, fg_color="#4CAF50", hover_color="#45A049")
        filter_button.pack(pady=(0, 5), fill='x')

        clear_filters_button = ctk.CTkButton(button_frame, text="Clear Filters", 
                                           command=self.clear_filters)
        clear_filters_button.pack(pady=(0, 5), fill='x')

        # Export button currently commented out, but works
        '''export_button = ctk.CTkButton(button_frame, text="Export List", 
                                 command=self.export_filtered_list,
                                 fg_color="green")
        export_button.pack(pady=(0, 5), fill='x')'''

        show_all_button = ctk.CTkButton(button_frame, text="Reset to Default", 
                                       command=self.show_all_games, fg_color="red")
        show_all_button.pack(fill='x')

        # Create right side games list
        # Add a search entry at the top
        search_frame = ctk.CTkFrame(right_frame)
        search_frame.pack(fill='x', padx=5, pady=5)
        
        search_label = ctk.CTkLabel(search_frame, text="Search Games:")
        search_label.pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.update_filtered_list())
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        search_entry.pack(side='left', fill='x', expand=True, padx=5)

        # Create games list with scrollbar
        list_frame = ctk.CTkFrame(right_frame)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.games_text = ctk.CTkTextbox(list_frame)
        self.games_text.pack(fill='both', expand=True, side='left')

        # Pack status bar last
        self.status_bar.pack(fill='x', padx=5, pady=(5, 0))

        # Initial population of the games list
        self.update_filtered_list()

    def clear_filters(self):
        """Reset all filters to their default states"""
        # Reset control type checkboxes
        for var in self.control_type_vars.values():
            var.set(0)
            
        # Reset dropdowns
        self.buttons_var.set("Select number of buttons")
        self.players_var.set("Select number of players")
        
        # Reset vertical checkbox
        self.vertical_checkbox_var.set(0)
        
        # Clear search box
        self.search_var.set("")
        
        # Update the filtered list
        self.update_filtered_list()
        self.status_bar.configure(text="All filters cleared")

    def update_filtered_list(self, *args):
        try:
            # Clear current display
            self.games_text.delete('1.0', 'end')
            
            # Get search term
            search_term = self.search_var.get().lower()
            
            # Get current filter settings
            selected_ctrltypes = self.get_selected_control_types()
            selected_buttons = self.buttons_var.get().strip()
            selected_players = self.players_var.get().strip()
            vertical_filter = self.vertical_checkbox_var.get()
            
            # Update status to show we're working
            self.status_bar.configure(text="Updating list...")
            
            # Get ROMs in build
            roms_in_build = self.scan_collections_for_roms()
            
            # Read CSV and apply filters
            self.filtered_games = []  # Store filtered games for export
            games_info = []
            with open(self.csv_file_path, newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    rom_name = row.get('ROM Name', '').strip()
                    if rom_name not in roms_in_build:
                        continue
                        
                    description = row.get('Description', '').strip()
                    joystick_input = self.sanitize_csv_cell(row.get('ctrlType'))
                    vertical = row.get('Vertical')
                    buttons = row.get('Buttons', '0')
                    players = row.get('numberPlayers', '1')

                    # Convert buttons and players to integers for comparison
                    buttons = int(buttons) if buttons.isdigit() else float('inf')
                    players = int(players) if players.isdigit() else float('inf')

                    # Apply filters
                    if vertical_filter and (not vertical or vertical.strip().upper() != "VERTICAL"):
                        continue
                    if selected_buttons != "Select number of buttons" and buttons > int(selected_buttons):
                        continue
                    if selected_players != "Select number of players" and players != int(selected_players):
                        continue
                    if selected_ctrltypes:
                        matches_control = False
                        for selected_ctrltype in selected_ctrltypes:
                            mapped_ctrltype = self.control_type_mapping.get(selected_ctrltype)
                            if self.control_type_exists(joystick_input, mapped_ctrltype):
                                matches_control = True
                                break
                        if not matches_control:
                            continue

                    # Apply search filter
                    if search_term and search_term not in description.lower() and search_term not in rom_name.lower():
                        continue

                    # Store the full row data for export
                    self.filtered_games.append(row)

                    # Format the display string
                    if description:
                        display_string = f"{description} ({rom_name})\n"
                    else:
                        display_string = f"{rom_name}\n"

                    games_info.append(display_string)
            
           # Sort and display results
            games_info.sort()
            self.games_text.insert('1.0', f"Matching Games: {len(games_info)}\n\n")
            for game in games_info:
                self.games_text.insert('end', game)
            
            # Update status bar with count
            self.status_bar.configure(text=f"Found {len(games_info)} matching games")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error updating filtered list: {str(e)}")
            self.status_bar.configure(text="Error updating list")

    def export_filtered_list(self):
        """Export the current filtered list to a CSV file"""
        if not hasattr(self, 'filtered_games') or not self.filtered_games:
            messagebox.showinfo("Export", "No games to export")
            return

        try:
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
                initialdir=os.getcwd(),
                initialfile='filtered_games.csv'
            )
            
            if not file_path:  # User cancelled
                return

            # Get the fieldnames from the first row
            fieldnames = self.filtered_games[0].keys()

            # Write to CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.filtered_games)

            self.status_bar.configure(text=f"Exported {len(self.filtered_games)} games to CSV")
            messagebox.showinfo("Export Complete", f"Successfully exported {len(self.filtered_games)} games to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting games: {str(e)}")
            self.status_bar.configure(text="Error exporting games")

    def load_custom_dll(self):
        #import ctypes
        dll_path = os.path.join(os.path.dirname(sys.executable), 'autochanger/python/VCRUNTIME140.dll')
        ctypes.windll.kernel32.SetDllDirectoryW(os.path.dirname(dll_path))
        if os.path.exists(dll_path):
            ctypes.windll.kernel32.LoadLibraryW(dll_path)
        else:
            print("Custom DLL not found. Please check the path.")

    def get_csv_file_path(self):
        # Check for an external CSV in the autochanger folder
        autochanger_csv_path = os.path.join('autochanger', 'META.csv')
        if os.path.exists(autochanger_csv_path):
            return autochanger_csv_path

        # If not found, use the bundled CSV in the executable (from --addfile)
        if getattr(sys, 'frozen', False):  # When running as a bundled executable
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # Return the path to the bundled CSV
        return os.path.join(base_path, 'meta', 'hyperlist', 'META.csv')

    def sanitize_csv_cell(self, cell_content):
        if cell_content:
            return re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', str(cell_content))
        return cell_content

    def get_selected_control_types(self):
        selected_controls = []
        for control_type, var in self.control_type_vars.items():
            if var.get() == 1:
                selected_controls.append(control_type)
        return selected_controls

    def control_type_exists(self, input_field, selected_ctrltype):
        if input_field:
            types_in_field = [t.strip().lower() for t in input_field.split('/')]
            return selected_ctrltype.lower() in types_in_field
        return False

    def check_output_dir(self):
        if not os.path.exists(self.output_dir):
            messagebox.showerror("Error", f"Output directory not found: {self.output_dir}. "
                                          f"Please run the executable from the root of the build.")
            self.parent_tab.quit()
            sys.exit()

    # Method to scan collections for ROMs
    def scan_collections_for_roms(self):
        root_dir = os.getcwd()
        collections_dir = os.path.join(root_dir, 'collections')
        rom_list = []

        for collection_name in os.listdir(collections_dir):
            if "settings" in collection_name.lower() or "zzz" in collection_name.lower():
                continue
            
            collection_path = os.path.join(collections_dir, collection_name)
            settings_path = os.path.join(collection_path, 'settings.conf')
            
            if os.path.isdir(collection_path) and os.path.isfile(settings_path):
                rom_folder = None
                extensions = []

                with open(settings_path, 'r') as settings_file:
                    for line in settings_file:
                        line = line.strip()
                        if line.startswith("#"):
                            continue
                        if line.startswith("list.path"):
                            rom_folder = line.split("=", 1)[1].strip()
                            rom_folder = os.path.join(root_dir, rom_folder)
                        elif line.startswith("list.extensions"):
                            ext_line = line.split("=", 1)[1].strip()
                            extensions = [ext.strip() for ext in ext_line.split(",")]

                if rom_folder and extensions and os.path.isdir(rom_folder):
                    for root, _, files in os.walk(rom_folder):
                        for file in files:
                            if any(file.endswith(ext) for ext in extensions):
                                filename_without_extension = os.path.splitext(file)[0]
                                rom_list.append(filename_without_extension)

        return set(rom_list)  # Return as set to ensure uniqueness

    # Updated filter_games_from_csv method
    def filter_games_from_csv(self):
        self.status_bar.configure(text="Saving filters...")
        self.check_output_dir()
        roms_in_build = self.scan_collections_for_roms()

        try:
            with open(self.csv_file_path, newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    game_count = 0
                    selected_ctrltypes = self.get_selected_control_types()
                    selected_players = self.players_var.get().strip()  # New player selection
                    selected_buttons = self.buttons_var.get().strip()
                    vertical_filter = self.vertical_checkbox_var.get()

                    for row in reader:
                        joystick_input = self.sanitize_csv_cell(row.get('ctrlType'))
                        rom_name = self.sanitize_csv_cell(row.get('ROM Name'))
                        vertical = row.get('Vertical')
                        buttons = row.get('Buttons')
                        players = row.get('numberPlayers')  # Get the Players column

                        buttons = int(buttons) if buttons.isdigit() else float('inf')
                        players = int(players) if players.isdigit() else float('inf')

                        # Check if the ROM is in the current build
                        if rom_name not in roms_in_build:
                            continue

                        # Apply filters
                        if vertical_filter == 1 and (not vertical or vertical.strip().upper() != "VERTICAL"):
                            continue
                        if selected_buttons != "Select number of buttons" and buttons > int(selected_buttons):
                            continue
                        if selected_players != "Select number of players" and players != int(selected_players):
                            continue
                        if selected_ctrltypes:
                            for selected_ctrltype in selected_ctrltypes:
                                mapped_ctrltype = self.control_type_mapping.get(selected_ctrltype)
                                if self.control_type_exists(joystick_input, mapped_ctrltype):
                                    f.write(f"{rom_name}\n")
                                    game_count += 1
                                    break
                        else:
                            f.write(f"{rom_name}\n")
                            game_count += 1

                    # Feedback for users
                    if game_count == 0:
                        messagebox.showinfo("No Games Found", "No games matched the selected filters.")
                        self.status_bar.configure(text="No games matched filters")
                    else:
                        ##Removed message box. status bar no outputs results without having to show, and manually press ok.]
                        #messagebox.showinfo("Success", f"{game_count} games added to {self.output_file}")
                        self.status_bar.configure(text=f"Saved {game_count} games to filter")

        except Exception as e:
            messagebox.showerror("Error", f"Error opening CSV file: {e}")

    def show_all_games(self):
        self.status_bar.configure(text="Resetting to default...")
        try:
            source = "autochanger/include.txt"  # Define the correct source path
            destination = "collections/Arcades/include.txt"  # Define the correct destination path
            
            # Check if the source file exists
            if os.path.exists(source):
                # Copy the file from source to destination
                shutil.copyfile(source, destination)
                print("Success", f"Copied '{source}' to '{destination}'.")
                self.status_bar.configure("Success", f"Copied '{source}' to '{destination}'.")
            else:
                # If source does not exist, delete the file in Arcades if it exists
                if os.path.exists(destination):
                    os.remove(destination)
                    print("Success", f"'{destination}' has been deleted as the source file was not found.")
                    self.status_bar.configure(text=f"Success {destination} has been deleted.")
                else:
                    print("Info", f"No file to delete. '{destination}' does not exist.")
                    self.status_bar.configure(text=f"No include.txt file to delete. {destination} does not exist.")
        
        except Exception as e:
            print("Error", f"Failed to process files: {str(e)}")
            self.status_bar.configure(text=f"Failed to process files: {str(e)}")

class Playlists:
    def __init__(self, root, parent_tab):
        self.root = root
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        self.playlists_path = os.path.join(self.base_path, "collections", "Arcades", "playlists")
        
        # Initialize the configuration manager
        self.config_manager = ConfigManager()
        
        # Get playlist location setting from INI
        self.playlist_location = self.config_manager.get_playlist_location()  # Should return 'S' or 'U'
        
        # Set up paths
        if self.playlist_location == 'S':
            # Original behavior - use settings file from config
            settings_file = self.config_manager.get_settings_file()
            self.settings_file_path = os.path.join(self.base_path, "autochanger", settings_file)
            self.autochanger_conf_path = self.settings_file_path
        else:
            # Use custom settings file
            self.settings_file_path = os.path.join(self.base_path, "collections", "Arcades", "settings.conf")
            self.custom_settings_path = os.path.join(self.base_path, "autochanger", "settingsCustomisation.conf")
            self.autochanger_conf_path = self.custom_settings_path
        
        self.check_vars = []
        self.check_buttons = []
        self.excluded_playlists = self.config_manager.get_excluded_playlists()
        self.manufacturer_playlists = ["atari", "capcom", "cave", "data east", "gunner", "irem", "konami", "midway", "namco", "neogeo", "nintendo", "psikyo", "raizing", "sega", "snk", "taito", "technos", "tecmo", "toaplan", "williams"]
        self.sort_type_playlists = ["ctrltype", "manufacturer", "numberplayers", "year"]
        
        # Create UI elements
        self.create_ui_elements()
        
        # Set up custom settings if needed
        if self.playlist_location == 'U':
            self.setup_custom_settings()
            
        # Initialize the toggle state dictionary
        self.toggle_state = {
            "genres": False,
            "manufacturer": False,
            "sort_type": False
        }
        
        # Populate checkboxes
        self.populate_checkboxes()
        self.update_reset_button_state()

    def create_ui_elements(self):
        """Create all UI elements"""
        # Create a main frame for all content
        self.main_frame = ctk.CTkFrame(self.parent_tab, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create a frame for the scrollable checkbox area
        self.scrollable_checklist = ctk.CTkScrollableFrame(self.main_frame, width=400, height=400)
        self.scrollable_checklist.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        # Create status message label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            height=25,
            fg_color=("gray85", "gray25"),
            corner_radius=8
        )
        self.status_label.pack(fill="x", padx=10, pady=(0, 10), ipady=5)
        self.status_label.pack_forget()  # Hide initially

        # Create button frames
        button_frame = ctk.CTkFrame(self.parent_tab)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        top_button_frame = ctk.CTkFrame(button_frame)
        top_button_frame.pack(fill="x", padx=2, pady=2)

        bottom_button_frame = ctk.CTkFrame(button_frame)
        bottom_button_frame.pack(fill="x", padx=2, pady=2)

        # Create main action buttons
        self.create_playlist_button = ctk.CTkButton(
            top_button_frame,
            text="Create Playlist",
            command=self.create_playlist,
            fg_color="#4CAF50",
            hover_color="#45A049"
        )
        self.create_playlist_button.pack(side="left", fill="x", expand=True, padx=2)

        self.reset_button = ctk.CTkButton(
            top_button_frame,
            text="Reset Playlists",
            fg_color="#D32F2F",
            hover_color="#C62828",
            command=self.reset_playlists,
            state="disabled"
        )
        self.reset_button.pack(side="left", fill="x", expand=True, padx=2)

        # Create category buttons
        self.genres_button = ctk.CTkButton(
            bottom_button_frame,
            text="All Genres",
            command=lambda: self.activate_special_playlist("genres", self.get_genre_playlists()),
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.genres_button.pack(side="left", fill="x", expand=True, padx=2)

        self.manufacturer_button = ctk.CTkButton(
            bottom_button_frame,
            text="All Manufacturer",
            command=lambda: self.activate_special_playlist("manufacturer", self.manufacturer_playlists),
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.manufacturer_button.pack(side="left", fill="x", expand=True, padx=2)

        self.sort_type_button = ctk.CTkButton(
            bottom_button_frame,
            text="All Sort Types",
            command=lambda: self.activate_special_playlist("sort_type", self.sort_type_playlists),
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.sort_type_button.pack(side="left", fill="x", expand=True, padx=2)

    def setup_custom_settings(self):
        """Set up custom settings file and backup if they don't exist"""
        try:
            # Create autochanger directory if it doesn't exist
            autochanger_dir = os.path.join(self.base_path, "autochanger")
            os.makedirs(autochanger_dir, exist_ok=True)
            
            # Check for original settings.conf in Arcades folder
            arcade_settings = os.path.join(self.base_path, "collections", "Arcades", "settings.conf")
            if os.path.exists(arcade_settings):
                # Create settingsCustomisation.conf if it doesn't exist
                if not os.path.exists(self.custom_settings_path):
                    shutil.copy2(arcade_settings, self.custom_settings_path)
                    self.show_status_message("✓ Created settingsCustomisation.conf backup")
            else:
                self.show_status_message("⚠️ Original settings.conf not found in Arcades folder")
                
        except Exception as e:
            self.show_status_message(f"⚠️ Error setting up custom settings: {str(e)}")

    def update_conf_file(self, playlist_list):
        try:
            target_file = self.settings_file_path if self.playlist_location == 'U' else self.autochanger_conf_path
            
            # Get default playlists from INI file
            default_playlists = self.config_manager.get_cycle_playlist()
            
            with open(target_file, 'r') as file:
                lines = file.readlines()

            cycle_playlist_found = False
            updated_lines = []
            
            for line in lines:
                if line.startswith("cyclePlaylist ="):
                    if default_playlists:
                        new_line = f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n"
                    else:
                        new_line = f"cyclePlaylist = {', '.join(playlist_list)}\n"
                    updated_lines.append(new_line)
                    cycle_playlist_found = True
                else:
                    updated_lines.append(line)

            # Add cyclePlaylist if not found
            if not cycle_playlist_found:
                if default_playlists:
                    updated_lines.append(f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n")
                else:
                    updated_lines.append(f"cyclePlaylist = {', '.join(playlist_list)}\n")

            # Write the updated lines back to the file
            with open(target_file, 'w') as file:
                file.writelines(updated_lines)

            self.show_status_message("✓ Playlists updated successfully")
        except Exception as e:
            self.show_status_message(f"⚠️ Error: {str(e)}")
                    
    def read_settings_file_name(self):
        return self.config_manager.get_settings_file()
    
    def read_default_playlists(self):
        return self.config_manager.get_cycle_playlist()
    
    def read_excluded_playlists(self):
        return self.config_manager.get_excluded_playlists()

    def show_temp_message(self, message):
         # Create a temporary window to show a message
        temp_window = tk.Toplevel(self.root)
        temp_window.title("Message")
        
        # Set up the label with the message
        label = tk.Label(temp_window, text=message, wraplength=250)  # Wrap long messages at 250px width
        label.pack(pady=20, padx=20)  # Add padding to the label

        # Calculate width based on message content
        font = tkFont.Font(font=label.cget("font"))
        text_width = font.measure(message) + 40  # Add some padding

        # Limit the minimum and maximum width
        window_width = min(max(text_width, 200), 400)  # Min 200, Max 400
        window_height = 100  # Set a default height; adjust if needed for larger messages
        
        # Center the temporary window relative to the main window
        self.root.update_idletasks()  # Ensure root's dimensions are up-to-date
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()

        # Calculate position for the temp window to be centered
        temp_x = main_x + (main_width // 2) - (window_width // 2)
        temp_y = main_y + (main_height // 2) - (window_height // 2)
        temp_window.geometry(f"{window_width}x{window_height}+{temp_x}+{temp_y}")

        # Auto-close the temporary window after a brief period (e.g., 2 seconds)
        temp_window.after(1000, temp_window.destroy)  # 2000ms = 2 seconds

    def show_status_message(self, message, duration=2000):
        # Show the status label if it's hidden
        self.status_label.pack(fill="x", padx=10, pady=(0, 10), ipady=5)
        
        # Update the message
        self.status_label.configure(text=message)
        
        # Schedule the message to be hidden
        self.root.after(duration, self.hide_status_message)
    
    def hide_status_message(self):
        self.status_label.pack_forget()

    # Gets all playlists not included in manufacturer and sort types
    def get_genre_playlists(self):
        return [name for name, _ in self.check_vars 
            if name not in self.sort_type_playlists and name not in self.manufacturer_playlists]
    
    def toggle_genres(self):
        genre_playlists = self.get_genre_playlists()  # Fetch genre playlists correctly
        if self.genre_switch.get() == "off":
            for genre in genre_playlists:
                if genre not in self.excluded_playlists:
                    self.excluded_playlists.append(genre)
        else:
            for genre in genre_playlists:    
                if genre in self.excluded_playlists:
                    self.excluded_playlists.remove(genre)
                    
        self.refresh_checkboxes()
        self.update_reset_button_state()  # Ensure reset button is enabled or disabled
    
    def toggle_manufacturers(self):
        if self.manufacturer_switch.get() == "off":
            for manufacturer in self.manufacturer_playlists:
                if manufacturer not in self.excluded_playlists:
                    print(f"Adding {manufacturer} to excluded playlists")  # Debugging statement
                    self.excluded_playlists.append(manufacturer)
        else:
            for manufacturer in self.manufacturer_playlists:
                if manufacturer in self.excluded_playlists:
                    print(f"Removing {manufacturer} from excluded playlists")  # Debugging statement
                    self.excluded_playlists.remove(manufacturer)

        self.refresh_checkboxes()
        self.update_reset_button_state()  # Ensure reset button is enabled or disabled
    
    def toggle_sort_types(self):
        print(f"Sort Switch State Before: {self.sort_types_switch.get()}")
        if self.sort_types_switch.get() == "off":
            for sort in self.sort_type_playlists:
                if sort not in self.excluded_playlists:
                    self.excluded_playlists.append(sort)
        else:
            for sort in self.sort_type_playlists:
                if sort in self.excluded_playlists:
                    self.excluded_playlists.remove(sort)
        
        self.refresh_checkboxes()
        self.update_reset_button_state()  # Ensure reset button is enabled or disabled
    
    def refresh_checkboxes(self):
        for widget in self.scrollable_checklist.winfo_children():
            widget.destroy()
        self.populate_checkboxes()

    def populate_checkboxes(self):
        """Populates the initial checkboxes with manufacturer playlists at the end."""
        try:
            all_playlists = []
            manufacturer_playlists = []
            sort_type_playlists = []

            for playlist_file in os.listdir(self.playlists_path):
                playlist_name, ext = os.path.splitext(playlist_file)
                # Normalize the playlist name for comparison
                normalized_name = playlist_name.lower().strip()
                # Normalize the excluded playlists for comparison
                normalized_excluded = [excluded.lower().strip() for excluded in self.excluded_playlists]
                
                # Check if it's a .txt file and not excluded
                if ext == ".txt" and normalized_name not in normalized_excluded:
                    all_playlists.append(playlist_name)
                    
                    # Check if it's a manufacturer playlist
                    if normalized_name in [m.lower() for m in self.manufacturer_playlists]:
                        manufacturer_playlists.append(playlist_name)
                        
                    # Check if it's a sort type playlist
                    if normalized_name in [s.lower() for s in self.sort_type_playlists]:
                        sort_type_playlists.append(playlist_name)
            
            # Remove manufacturer playlists from all_playlists
            for manufacturer_playlist in manufacturer_playlists:
                if manufacturer_playlist in all_playlists:
                    all_playlists.remove(manufacturer_playlist)
            
            # Remove sort type playlists from all_playlists
            for sort_playlist in sort_type_playlists:
                if sort_playlist in all_playlists:
                    all_playlists.remove(sort_playlist)
                
            # Sort playlists to handle numeric prefixes properly
            all_playlists.sort(key=str.lower)
            
            # Append manufacturer and sort type playlists to the end
            all_playlists.extend(manufacturer_playlists)
            all_playlists.extend(sort_type_playlists)

            # Populate checkboxes in the desired order
            for playlist_name in all_playlists:
                var = tk.BooleanVar()
                checkbutton = ctk.CTkCheckBox(self.scrollable_checklist, text=playlist_name, variable=var)
                checkbutton.pack(anchor="w", padx=10, pady=5)
                self.check_vars.append((playlist_name, var))

        except FileNotFoundError:
            print(f"Playlists folder not found at: {self.playlists_path}")
        except Exception as e:
            print("An error occurred:", str(e))

    def add_playlists_to_checklist(self, playlist_names):
        """Adds playlists to the checklist."""
        current_playlists = [name for name, var in self.check_vars]
        
        for playlist in playlist_names:
            if playlist not in current_playlists:
                var = tk.BooleanVar()
                checkbutton = ctk.CTkCheckBox(self.scrollable_checklist, text=playlist, variable=var)
                checkbutton.pack(anchor="w", padx=10, pady=5)
                self.check_vars.append((playlist, var))

    def add_playlists_to_checklist(self, playlist_names):
        """Adds playlists to the checklist."""
        current_playlists = [name for name, var in self.check_vars]
        
        for playlist in playlist_names:
            if playlist not in current_playlists:
                var = tk.BooleanVar()
                checkbutton = ctk.CTkCheckBox(self.scrollable_checklist, text=playlist, variable=var)
                checkbutton.pack(anchor="w", padx=10, pady=5)
                self.check_vars.append((playlist, var))

    def remove_playlists_from_checklist(self, playlist_names):
        """Removes playlists from the checklist."""
        for playlist in playlist_names:
            for name, var in self.check_vars:
                if name == playlist:
                    var.set(False)  # Uncheck the checkbox
                    self.check_vars.remove((name, var))  # Remove from the list
                    break

    def create_playlist(self):
        selected_playlists = [name for name, var in self.check_vars if var.get()]
        self.update_conf_file(selected_playlists)
    
    def activate_special_playlist(self, button_type, playlist_type):
        # Check the toggle state to determine if we select or unselect
        current_state = self.toggle_state[button_type]
        
        for name, var in self.check_vars:
            if name in playlist_type:
                var.set(not current_state)  # Set to True if unselected, False if already selected

        # Toggle the button's state for next click
        self.toggle_state[button_type] = not current_state
               
    def update_reset_button_state(self):
        """Check if backup settings file exists and update reset button state"""
        try:
            # Get current settings filename from config manager
            current_settings = self.config_manager.get_settings_file()
            # Create backup filename
            backup_file = current_settings.replace(".conf", "x.conf")
            # Full path to backup file
            backup_conf_path = os.path.join(self.base_path, "autochanger", backup_file)
            
            # Enable button if backup exists, disable if it doesn't
            if os.path.exists(backup_conf_path):
                self.reset_button.configure(state="normal")
            else:
                self.reset_button.configure(state="disabled")
        except Exception as e:
            print(f"Error checking backup file: {str(e)}")
            self.reset_button.configure(state="disabled")

    def reset_playlists(self):
        """Reset the settings based on playlist location setting"""
        try:
            if self.playlist_location == 'S':
                # Original behavior
                current_settings = self.config_manager.get_settings_file()
                backup_file = current_settings.replace(".conf", "x.conf")
                backup_conf_path = os.path.join(self.base_path, "autochanger", backup_file)
                
                if os.path.exists(backup_conf_path):
                    shutil.copy2(backup_conf_path, self.autochanger_conf_path)
                    self.show_status_message("✓ Playlists have been reset successfully")
                else:
                    self.show_status_message("⚠️ Backup configuration file not found")
            else:
                # For 'U' mode, copy settingsCustomisation.conf to collections/Arcades/settings.conf
                if os.path.exists(self.custom_settings_path):
                    arcade_settings = os.path.join(self.base_path, "collections", "Arcades", "settings.conf")
                    shutil.copy2(self.custom_settings_path, arcade_settings)
                    self.show_status_message("✓ Settings reset to custom defaults")
                else:
                    self.show_status_message("⚠️ settingsCustomisation.conf not found")
        except Exception as e:
            self.show_status_message(f"⚠️ Error during reset: {str(e)}")

class ThemeViewer:
    def __init__(self, video_path=None, image_path=None):
        self.video_path = video_path
        self.image_path = image_path
        self.thumbnail = None
        self.video_cap = None
        self.is_playing = False
        self.lock = Lock()
        
    def extract_thumbnail(self):
        """Extract thumbnail from video file or load PNG"""
        if self.video_path:
            try:
                cap = cv2.VideoCapture(self.video_path)
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    return frame
            except Exception as e:
                print(f"Error extracting video thumbnail: {e}")
                
        if self.image_path:
            try:
                image = cv2.imread(self.image_path)
                if image is not None:
                    return image
            except Exception as e:
                print(f"Error loading PNG: {e}")
                
        return None

    def start_video(self):
        """Start video playback"""
        with self.lock:
            if not self.is_playing and self.video_path:
                try:
                    self.video_cap = cv2.VideoCapture(self.video_path)
                    if self.video_cap.isOpened():
                        self.is_playing = True
                        print(f"Video started successfully: {self.video_path}")
                        return True
                    else:
                        print("Failed to open video file")
                        self.video_cap = None
                except Exception as e:
                    print(f"Error starting video: {e}")
                    self.video_cap = None
            return False

    def stop_video(self):
        """Stop video playback"""
        with self.lock:
            self.is_playing = False
            if self.video_cap:
                try:
                    self.video_cap.release()
                except Exception as e:
                    print(f"Error stopping video: {e}")
                finally:
                    self.video_cap = None

    def get_frame(self):
        """Get next video frame if playing"""
        if not self.is_playing or not self.video_cap:
            return None
            
        try:
            ret, frame = self.video_cap.read()
            if ret:
                return frame
            else:
                # Reset video to start
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video_cap.read()
                return frame if ret else None
        except Exception as e:
            print(f"Error reading frame: {e}")
            return None

class Themes:
    def __init__(self, parent_tab):
        print("Initializing Themes...")
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        
        # Initialize configuration manager
        self.config_manager = ConfigManager()
        self.theme_paths = self.config_manager.get_theme_paths()
        
        # Configuration paths
        self.theme_folder = self.theme_paths['roms']  # Updated to use the roms path from theme_paths
        self.video_folder = self.theme_paths['videos']
        self.logo_folder = self.theme_paths['logos']
        
        # State management
        self.themes_list = []
        self.current_theme_index = 0
        self.current_viewer = None
        self.default_size = (640, 360)
        self.thumbnail_cache = {}
        self.current_frame = None
        self.autoplay_after = None
        self.last_resize_time = 0
        self.resize_delay = 200  # ms
        self.last_frame_time = 0
        self.target_fps = 40
        self.frame_interval = 1000 / self.target_fps  # ms

        self._setup_ui()
        self.load_themes()
        if self.themes_list:
            self.show_initial_theme()  # Changed to directly call show_initial_theme

    def show_status_message(self, message):
        """Utility to display a status message in the theme label."""
        self.theme_label.configure(text=message)
        print(f"Status Update: {message}")
    
    def cancel_autoplay(self):
        """Cancel any scheduled autoplay"""
        if self.autoplay_after:
            try:
                self.parent_tab.after_cancel(self.autoplay_after)
                print("Cancelled scheduled autoplay")
            except Exception as e:
                print(f"Error cancelling autoplay: {e}")
            finally:
                self.autoplay_after = None

    def schedule_autoplay(self):
        """Schedule video autoplay after 2 seconds"""
        self.cancel_autoplay()
        
        if self.current_viewer and self.current_viewer.video_path:
            print("Scheduling autoplay...")
            self.autoplay_after = self.parent_tab.after(250, self.start_autoplay)

    def start_autoplay(self):
        """Start video playback immediately"""
        print("Starting autoplay...")
        if self.current_viewer and self.current_viewer.video_path:
            if not self.current_viewer.is_playing:
                if self.current_viewer.start_video():
                    print("Autoplay started successfully")
                    self.play_video()
                else:
                    print("Failed to start autoplay")
                    self.show_thumbnail()

    def clear_logo_cache(self):
        """Clear all cached logo images"""
        for attr in list(vars(self)):
            if attr.startswith('logo_cache_'):
                delattr(self, attr)

    def show_current_theme(self):
        """Display the current theme and start video if available"""
        print("Showing current theme...")
        if not self.themes_list:
            return

        # Stop any playing video and cancel any pending autoplay
        self.cancel_autoplay()
        if self.current_viewer and self.current_viewer.is_playing:
            self.current_viewer.stop_video()

        theme_name, video_path, png_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Create viewer with both video and image paths
        self.current_viewer = ThemeViewer(video_path, png_path)
        
        # Show thumbnail
        self.show_thumbnail()
        
        # Start video immediately if available
        if video_path:
            print("Starting video immediately...")
            if self.current_viewer.start_video():
                self.play_video()

    def force_initial_display(self):
        """Force the initial theme display"""
        print("Forcing initial display...")  # Debug print
        if self.themes_list:
            self.parent_tab.update_idletasks()
            self.show_initial_theme()

    def show_initial_theme(self):
        """Show the first theme and start video playback"""
        print("Showing initial theme...")
        if not self.themes_list:
            return

        theme_name, video_path, png_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Initialize viewer
        self.current_viewer = ThemeViewer(video_path, png_path)
        
        # Force immediate thumbnail extraction and display
        thumbnail = self.current_viewer.extract_thumbnail()
        if thumbnail is not None:
            print("Thumbnail extracted, displaying...")
            self._display_frame(thumbnail)
            
            # Start video immediately if available
            if video_path:
                print(f"Starting initial video: {video_path}")
                if self.current_viewer.start_video():
                    print("Initial video started, beginning playback...")
                    self.play_video()
        else:
            print("No thumbnail available")
            self._show_no_video_message()

    def schedule_autoplay(self):
        """Schedule immediate video autoplay"""
        self.cancel_autoplay()
        if self.current_viewer and self.current_viewer.video_path:
            print("Scheduling immediate autoplay...")
            self.autoplay_after = self.parent_tab.after(100, self.start_autoplay)

    def play_video(self):
        """Play video with frame timing control"""
        if not self.current_viewer or not self.current_viewer.is_playing:
            return
            
        try:
            current_time = time.time() * 1000
            if current_time - self.last_frame_time >= self.frame_interval:
                frame = self.current_viewer.get_frame()
                if frame is not None:
                    self._display_frame(frame)
                    self.last_frame_time = current_time
                else:
                    print("No frame available, restarting video")
                    self.current_viewer.stop_video()
                    self.current_viewer.start_video()
                    return
            
            # Schedule next frame
            self.parent_tab.after(max(1, int(self.frame_interval)), self.play_video)
            
        except Exception as e:
            print(f"Error during video playback: {e}")
            self.current_viewer.stop_video()
            self.show_thumbnail()

    def load_themes(self):
        """Load themes and their video/image paths"""
        if not os.path.isdir(self.theme_folder):
            messagebox.showerror("Error", f"Theme folder not found: {self.theme_folder}")
            return

        self.themes_list = []
        
        for filename in os.listdir(self.theme_folder):
            if filename.endswith(".bat"):
                theme_name = os.path.splitext(filename)[0]
                video_path = os.path.join(self.video_folder, f"{theme_name}.mp4")
                png_path = os.path.join(self.video_folder, f"{theme_name}.png")
                
                if os.path.isfile(video_path):
                    self.themes_list.append((filename, video_path, png_path if os.path.isfile(png_path) else None))
                elif os.path.isfile(png_path):
                    self.themes_list.append((filename, None, png_path))
                else:
                    self.themes_list.append((filename, None, None))

    def show_current_theme(self):
        """Display the current theme and start video if available"""
        print("Showing current theme...")
        if not self.themes_list:
            return

        # Stop any playing video and cancel any pending autoplay
        self.cancel_autoplay()
        if self.current_viewer and self.current_viewer.is_playing:
            self.current_viewer.stop_video()

        theme_name, video_path, png_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Create viewer with both video and image paths
        self.current_viewer = ThemeViewer(video_path, png_path)
        
        # Show thumbnail
        self.show_thumbnail()
        
        # Start video immediately if available
        if video_path:
            print("Starting video immediately...")
            if self.current_viewer.start_video():
                self.play_video()

    def show_thumbnail(self):
        """Display the current theme's thumbnail"""
        if not self.current_viewer:
            self._show_no_video_message()
            return
            
        # Use cached thumbnail if available
        cache_key = self.current_viewer.video_path or self.current_viewer.image_path
        if cache_key and cache_key in self.thumbnail_cache:
            thumbnail = self.thumbnail_cache[cache_key].copy()  # Create a copy from cache
        else:
            thumbnail = self.current_viewer.extract_thumbnail()
            if thumbnail is not None and cache_key:
                self.thumbnail_cache[cache_key] = thumbnail.copy()
        
        if thumbnail is not None:
            self._display_frame(thumbnail)
        else:
            self._show_no_video_message()

    def _display_frame(self, frame, force_resize=False):
        """Display a frame or thumbnail on the canvas with proper aspect ratio"""
        try:
            current_time = time.time() * 1000
            
            if not force_resize:
                self.current_frame = frame.copy()
            
            # Validate input frame
            if frame is None or frame.size == 0:
                raise ValueError("Invalid frame: frame is None or empty")
                
            # Get current display size
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            # Ensure minimum display dimensions
            canvas_width = max(1, canvas_width)
            canvas_height = max(1, canvas_height)
            
            if canvas_width < 1 or canvas_height < 1:
                canvas_width, canvas_height = self.default_size
            
            # Get original frame dimensions
            frame_height, frame_width = frame.shape[:2]
            
            # Validate frame dimensions
            if frame_width <= 0 or frame_height <= 0:
                raise ValueError(f"Invalid frame dimensions: {frame_width}x{frame_height}")
                
            frame_aspect = frame_width / frame_height
            canvas_aspect = canvas_width / canvas_height
            
            # Calculate new dimensions maintaining aspect ratio
            if canvas_aspect > frame_aspect:
                new_height = max(1, canvas_height)
                new_width = max(1, int(canvas_height * frame_aspect))
            else:
                new_width = max(1, canvas_width)
                new_height = max(1, int(canvas_width / frame_aspect))
            
            # Skip frame if falling behind
            if not force_resize and self.current_viewer and self.current_viewer.is_playing:
                if current_time - self.last_frame_time < self.frame_interval:
                    return
            
            # Validate final dimensions before resize
            if new_width <= 0 or new_height <= 0:
                raise ValueError(f"Invalid resize dimensions: {new_width}x{new_height}")
            
            # Resize frame maintaining aspect ratio
            if new_width * new_height > 1920 * 1080:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            else:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            main_image = Image.fromarray(frame)
            
            # Logo handling (rest of the logo code remains the same)
            try:
                current_theme = os.path.splitext(self.themes_list[self.current_theme_index][0])[0]
                logo_path = os.path.join(self.logo_folder, f"{current_theme}.png")
                
                if os.path.exists(logo_path):
                    # Create a cache key that includes the canvas dimensions
                    cache_key = f'logo_cache_{current_theme}_{new_width}_{new_height}'
                    
                    if not hasattr(self, cache_key):
                        # Load original logo
                        logo_img = Image.open(logo_path)
                        
                        # Calculate logo size based on current frame dimensions
                        logo_max_width = max(1, int(new_width * 0.15))  # 15% of frame width
                        logo_max_height = max(1, int(new_height * 0.15))  # 15% of frame height
                        
                        # Get original logo dimensions
                        logo_w, logo_h = logo_img.size
                        
                        # Calculate scale factor maintaining aspect ratio
                        logo_scale = min(
                            logo_max_width / logo_w,
                            logo_max_height / logo_h
                        )
                        
                        # Calculate new logo dimensions
                        logo_new_size = (
                            max(1, int(logo_w * logo_scale)),
                            max(1, int(logo_h * logo_scale))
                        )
                        
                        # Resize logo
                        resized_logo = logo_img.resize(logo_new_size, Image.Resampling.LANCZOS)
                        
                        # Cache the resized logo
                        setattr(self, cache_key, resized_logo)
                    else:
                        resized_logo = getattr(self, cache_key)
                    
                    # Calculate padding based on frame size
                    padding = max(1, int(min(new_width, new_height) * 0.02))  # 2% of smaller dimension
                    
                    # Calculate position
                    pos_x = new_width - resized_logo.size[0] - padding
                    pos_y = new_height - resized_logo.size[1] - padding
                    
                    # Overlay logo
                    if resized_logo.mode == 'RGBA':
                        main_image.paste(resized_logo, (pos_x, pos_y), resized_logo)
                    else:
                        main_image.paste(resized_logo, (pos_x, pos_y))
                        
            except Exception as e:
                print(f"Error loading or applying logo: {e}")
                
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image=main_image)
            
            # Clear canvas
            self.video_canvas.delete("all")
            
            # Calculate center position
            x = canvas_width // 2
            y = canvas_height // 2
            
            # Create black background to fill canvas
            self.video_canvas.configure(bg="#2B2B2B")
            
            # Display image centered
            self.video_canvas.create_image(
                x, y,
                image=photo,
                anchor="center"
            )
            self.video_canvas.image = photo
            
            self.last_frame_time = current_time
            
        except Exception as e:
            print(f"Error displaying frame: {e}")
            self._show_no_video_message()

    def _setup_ui(self):
        """Initialize and configure UI components"""
        # Main display frame
        self.display_frame = ctk.CTkFrame(self.parent_tab)
        self.display_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Video display
        self.video_canvas = ctk.CTkCanvas(
            self.display_frame,
            width=self.default_size[0],
            height=self.default_size[1],
            bg="#2B2B2B",
            bd="0",
            highlightthickness=0
        )
        self.video_canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Bind resize event
        self.video_canvas.bind('<Configure>', self.handle_resize)
        
        # Theme name and status
        self.status_frame = ctk.CTkFrame(self.display_frame)
        self.status_frame.pack(fill="x", padx=10, pady=5)

        self.theme_label = ctk.CTkLabel(self.status_frame, text="")
        self.theme_label.pack(side="left", padx=5)
        
        # Location selector frame - store as instance variable to control visibility
        self.location_frame = ctk.CTkFrame(self.display_frame)
        self.location_frame.pack(fill="x", padx=10, pady=5)
        
        # Add location selector dropdown
        self.location_var = ctk.StringVar(value=self.config_manager.config.get('Settings', 'theme_location', fallback='autochanger'))
        self.location_dropdown = ctk.CTkOptionMenu(
            self.location_frame,
            values=['autochanger', 'zzzSettings', 'custom'],
            variable=self.location_var,
            command=self.change_location
        )
        self.location_dropdown.pack(side="right", padx=5)
        
        ctk.CTkLabel(self.location_frame, text="Theme Location:").pack(side="right", padx=5)

        # Custom paths configuration button
        self.custom_paths_button = ctk.CTkButton(
            self.location_frame,
            text="Configure Custom Paths",
            command=self.show_custom_paths_dialog
        )
        self.custom_paths_button.pack(side="right", padx=5)
        
        # Navigation frame - always visible
        self.button_frame = ctk.CTkFrame(self.display_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=5, pady=5)  # Always pack this frame

        # Configure grid layout
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.status_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Navigation and control buttons
        buttons = [
            ("Previous", self.show_previous_theme, 0),
            ("Apply Theme", self.run_selected_script, 1, "green", "darkgreen"),
            ("Next", self.show_next_theme, 2)
        ]
        
        for btn_data in buttons:
            if len(btn_data) == 3:
                text, command, col = btn_data
                fg_color = None
                hover_color = None
            else:
                text, command, col, fg_color, hover_color = btn_data
                
            btn = ctk.CTkButton(
                self.button_frame,
                text=text,
                command=command,
                fg_color=fg_color,
                hover_color=hover_color,
                border_width=0
            )
            btn.grid(row=0, column=col, sticky="ew", padx=5, pady=5)
        
        # Check config and show/hide location frame
        self.update_location_frame_visibility()

    def update_location_frame_visibility(self):
        """Update the visibility of the location frame based on config settings"""
        show_location_controls = self.config_manager.config.getboolean('Settings', 'show_location_controls', fallback=True)
        
        if show_location_controls:
            self.location_frame.pack(fill="x", padx=10, pady=5)
        else:
            self.location_frame.pack_forget()

    def show_custom_paths_dialog(self):
        """Show dialog for configuring custom paths"""
        dialog = ctk.CTkToplevel(self.parent_tab)
        dialog.title("Configure Custom Paths")
        dialog.geometry("600x200")
        dialog.transient(self.parent_tab)
        dialog.grab_set()
        
        # Create entry fields for each path
        paths = {
            'ROMs Path': 'custom_roms_path',
            'Videos Path': 'custom_videos_path',
            'Logos Path': 'custom_logos_path'
        }
        
        entries = {}
        
        for i, (label_text, config_key) in enumerate(paths.items()):
            frame = ctk.CTkFrame(dialog)
            frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(frame, text=label_text).pack(side="left", padx=5)
            
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=5, fill="x", expand=True)
            entry.insert(0, self.config_manager.config.get('Settings', config_key, fallback=''))
            
            entries[config_key] = entry
            
            def browse_path(entry_widget):
                path = filedialog.askdirectory()
                if path:
                    entry_widget.delete(0, 'end')
                    entry_widget.insert(0, path)
            
            browse_btn = ctk.CTkButton(
                frame,
                text="Browse",
                command=lambda e=entry: browse_path(e)
            )
            browse_btn.pack(side="right", padx=5)
        
        def save_paths():
            self.config_manager.update_custom_paths(
                roms_path=entries['custom_roms_path'].get(),
                videos_path=entries['custom_videos_path'].get(),
                logos_path=entries['custom_logos_path'].get()
            )
            if self.location_var.get() == 'custom':
                self.change_location('custom')
            dialog.destroy()
        
        # Save button
        ctk.CTkButton(
            dialog,
            text="Save",
            command=save_paths
        ).pack(pady=10)

    def change_location(self, location):
        """Handle location change"""
        # Update configuration
        self.config_manager.update_theme_location(location)
        
        # Update paths
        self.theme_paths = self.config_manager.get_theme_paths()
        self.theme_folder = self.theme_paths['roms']  # Update ROM path
        self.video_folder = self.theme_paths['videos']
        self.logo_folder = self.theme_paths['logos']
        
        # Clear caches
        self.thumbnail_cache.clear()
        self.clear_logo_cache()
        
        # Reload themes and refresh display
        self.load_themes()
        if self.themes_list:
            self.current_theme_index = 0
            self.show_current_theme()
        
        # Update status
        self.show_status_message(f"Changed theme location to: {location}")

    def handle_resize(self, event=None):
        """Handle window resize events"""
        if hasattr(self, 'current_frame') and self.current_frame is not None:
            self._display_frame(self.current_frame, force_resize=True)

    def toggle_video(self):
        """Toggle video playback"""
        if not self.current_viewer:
            return
            
        if not self.current_viewer.is_playing:
            # Start video
            success = self.current_viewer.start_video()
            if success:
                self.play_button.configure(text="Stop Video")
                self.play_video()
            else:
                self.show_thumbnail()
        else:
            # Stop video and show thumbnail
            self.current_viewer.stop_video()
            self.play_button.configure(text="Play Video")
            self.show_thumbnail()

    def initialize_first_theme(self):
        """Initialize and display the first theme"""
        print("Initializing first theme...")
        if not self.themes_list:
            print("No themes available")
            return
            
        theme_name, video_path, png_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Initialize viewer with both video and image paths
        self.current_viewer = ThemeViewer(video_path, png_path)
        self.play_button.configure(state="normal" if video_path else "disabled")
        
        # Force immediate thumbnail display
        print("Forcing thumbnail display...")
        thumbnail = self.current_viewer.extract_thumbnail()
        if thumbnail is not None:
            cache_key = video_path or png_path
            if cache_key:
                self.thumbnail_cache[cache_key] = thumbnail
            
            # Force canvas update and display
            self.parent_tab.update_idletasks()
            self._display_frame(thumbnail)
            
            # Schedule autoplay if video exists
            if video_path:
                print("Scheduling initial autoplay...")
                self.schedule_autoplay()
        else:
            print("No thumbnail available")
            self._show_no_video_message()

    def show_next_theme(self):
        """Navigate to next theme"""
        if self.themes_list:
            self.current_theme_index = (self.current_theme_index + 1) % len(self.themes_list)
            self.show_current_theme()

    def show_previous_theme(self):
        """Navigate to previous theme"""
        if self.themes_list:
            self.current_theme_index = (self.current_theme_index - 1) % len(self.themes_list)
            self.show_current_theme()

    def _show_no_video_message(self):
        """Display message when no video is available"""
        self.video_canvas.delete("all")
        self.video_canvas.create_text(
            self.video_canvas.winfo_width() // 2,
            self.video_canvas.winfo_height() // 2,
            text="No video available",
            fill="white"
        )

    def run_selected_script(self):
        """Execute the selected theme script."""
        if not self.themes_list:
            print("No themes found in themes_list. Exiting function.")
            self.show_status_message("Error: No themes available!")
            return

        # Get the script filename (without extension)
        script_filename, _, _ = self.themes_list[self.current_theme_index]
        script_name_without_extension = os.path.splitext(script_filename)[0]  # Remove extension
        script_path = os.path.join(self.theme_folder, script_filename)

        # Print the selected theme information for debugging
        print(f"Selected script: {script_filename}")
        print(f"Full script path: {script_path}")

        # Check if the script file exists
        print(f"Checking if script exists at path: {script_path}")
        if not os.path.isfile(script_path):
            print(f"Script not found: {script_path}")  # Log the error instead of showing it
            self.show_status_message(f"Error: Script '{script_name_without_extension}' not found.")
            return

        try:
            # Show status message that the script is being executed
            self.show_status_message(f"Applying theme '{script_name_without_extension}'...")

            # Debugging information
            print(f"Executing script: {script_path}")
            print(f"Working directory: {self.theme_folder}")

            # Set up subprocess startup information to hide the command window
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                print(f"StartupInfo flags: {startupinfo.dwFlags}")

            # Run the batch file
            print("Command execution details:", [script_path])
            process = subprocess.run(
                [script_path],
                check=False,  # Do not raise an error for non-zero exit codes
                shell=True,
                text=True,
                capture_output=True,
                cwd=self.theme_folder,
                startupinfo=startupinfo
            )

            # Print process outputs for debugging, regardless of outcome
            print("Process completed with return code:", process.returncode)
            print("Standard output from script:", process.stdout)
            if process.returncode != 0:
                print(f"Non-critical script error: {process.stderr}")

            # Update status message based on script completion
            if process.returncode == 0:
                self.show_status_message(f"Theme: {script_name_without_extension} applied successfully!")
            else:
                self.show_status_message(f"Error: Script '{script_name_without_extension}' encountered an issue.")
            
        except subprocess.CalledProcessError as e:
            print(f"Subprocess error (CalledProcessError): {e}")
            print(f"Return code: {e.returncode}")
            print(f"Standard output: {e.stdout}")
            print(f"Error output: {e.stderr}")
            self.show_status_message(f"Error: {e.stderr}")

        except Exception as e:
            # Log the error without showing it in the GUI
            print(f"Unexpected error while running script: {str(e)}")
            self.show_status_message(f"Unexpected error: {str(e)}")

class AdvancedConfigs:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        self.config_folders = ["- Advanced Configs", "- Themes", "- Themes 2nd Screen", "- Bezels Glass and Scanlines"]
        self.tab_keywords = {
            "Favorites": None,
            "Themes": None,
            "2nd Screen": None,
            "Bezels & Effects": ["Bezel", "SCANLINE", "GLASS EFFECTS"],
            "Overlays": ["OVERLAY"],
            "InigoBeats": ["MUSIC"],
            "Attract": ["Attract", "Scroll"],           
            "Monitor": ["Monitor"],
            "Splash": ["Splash"],
            "Front End": ["FRONT END"],
            "Other": None
        }

        self.folder_to_tab_mapping = {
            "- Themes": "Themes",
            "- Themes 2nd Screen": "2nd Screen",
            "- Bezels Glass and Scanlines": "Bezels & Effects"
        }
        
        self.tab_radio_vars = {}
        self.radio_button_script_mapping = {}
        self.radio_buttons = {}
        self.favorite_buttons = {}
        self.favorites = self.load_favorites()
        
        # Create status label (hidden by default)
        self.status_label = ctk.CTkLabel(
            self.parent_tab,
            text="",
            text_color="green",
            bg_color="transparent",
            corner_radius=8,
            font=("", 14, "bold")
        )

        # Create loading label
        self.loading_label = ctk.CTkLabel(
            self.parent_tab,
            text="Processing...",
            text_color="gray70"
        )
        
        # Create progress bar (hidden by default)
        self.progress_frame = ctk.CTkFrame(self.parent_tab)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="")
        
        # Create the tab view in the parent tab
        self.tabview = ctk.CTkTabview(self.parent_tab)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Flag to track if scripts are currently running
        self.is_running_all = False
        
        # Populate the tabs and scripts dynamically
        self.populate_tabs_and_scripts()

        # Set the initial tab view
        self.set_initial_tab()
    
    def validate_script_exists(self, script_name):
        """Check if a script exists in any of the config folders"""
        for folder in self.config_folders:
            potential_path = os.path.join(self.base_path, folder, script_name)
            if os.path.isfile(potential_path):
                return True
        return False

    def set_initial_tab(self):
        """Set the initial tab to Favorites if it contains values, else Themes."""
        initial_tab = "Favorites" if self.favorites else "Themes"
        self.tabview.set(initial_tab)

    def show_status(self, message, duration=2000, color="green"):
        """Show a status message that automatically fades out"""
        # Configure and show the status label
        self.status_label.configure(text=message, text_color=color)
        self.status_label.pack(side="bottom", pady=10)
        self.parent_tab.update()
        
        # Schedule the fade out effect
        def fade_out(alpha=1.0):
            if alpha <= 0:
                self.status_label.pack_forget()
                return
            
            # Calculate color with alpha
            rgb = [int(int(color[i:i+2], 16) * alpha) for i in (1, 3, 5)] if color.startswith('#') else None
            if rgb:
                color_with_alpha = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                self.status_label.configure(text_color=color_with_alpha)
            
            self.parent_tab.update()
            self.parent_tab.after(50, lambda: fade_out(alpha - 0.1))
        
        # Schedule the start of fade out
        self.parent_tab.after(duration, lambda: fade_out())

    def show_progress(self, show=True):
        """Show or hide the progress bar and label"""
        if show:
            self.progress_frame.pack(side="bottom", fill="x", padx=10, pady=5)
            self.progress_label.pack(pady=(0, 5))
            self.progress_bar.pack(fill="x", padx=10, pady=(0, 5))
        else:
            self.progress_frame.pack_forget()

    async def run_script_async(self, script_path):
        """Run a script and return when it's complete"""
        process = await asyncio.create_subprocess_exec(
            "cmd.exe", "/c", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path)
        )
        
        # Wait for the process to complete
        await process.communicate()
        return True  # Return True as script completed running, regardless of errors

    async def run_all_favorites_async(self):
        """Run all favorite scripts sequentially with progress tracking"""
        if not self.favorites or self.is_running_all:
            return

        self.is_running_all = True
        self.set_gui_state(False)
        
        # Count only existing scripts for progress calculation
        existing_scripts = [script for script in self.favorites if self.validate_script_exists(script)]
        total_scripts = len(existing_scripts)
        
        if total_scripts == 0:
            self.show_status("No valid scripts found in favorites!", color="orange")
            self.is_running_all = False
            self.set_gui_state(True)
            return

        # Show single progress bar
        self.show_progress(True)
        completed = 0
        
        try:
            for script_name in self.favorites:
                script_path = None
                for folder in self.config_folders:
                    potential_path = os.path.join(self.base_path, folder, script_name)
                    if os.path.isfile(potential_path):
                        script_path = potential_path
                        break

                if script_path:
                    # Update progress before running script
                    self.update_progress(completed, total_scripts, script_name)
                    
                    # Run script and wait for it to complete
                    await self.run_script_async(script_path)
                    
                    # Increment progress as script has completed running
                    completed += 1
                    self.update_progress(completed, total_scripts, script_name)

        finally:
            self.is_running_all = False
            self.set_gui_state(True)
            self.show_progress(False)
            self.show_status("All available favorites executed successfully!", color="#2ecc71")

    def run_all_favorites(self):
        """Start the async run_all_favorites operation"""
        asyncio.run(self.run_all_favorites_async())

    def update_progress(self, current, total, script_name):
        """Update progress bar and label"""
        progress = current / total if total > 0 else 0
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Running {current}/{total}: {os.path.splitext(script_name)[0]}")
        self.parent_tab.update()

    def update_favorites_tab(self):
        """Update the contents of the Favorites tab"""
        # Clear existing content in Favorites tab
        for widget in self.tabview.tab("Favorites").winfo_children():
            widget.destroy()

        # Create scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(self.tabview.tab("Favorites"), width=400, height=400)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Add "Run All Favorites" button at the top if there are favorites
        if self.favorites:
            run_all_frame = ctk.CTkFrame(scrollable_frame)
            run_all_frame.pack(fill="x", padx=5, pady=5)
            
            run_all_button = ctk.CTkButton(
                run_all_frame,
                text="Run All Favorites Sequentially",
                command=self.run_all_favorites
            )
            run_all_button.pack(fill="x", padx=5, pady=5)

        # Add favorite scripts
        if not self.favorites:
            ctk.CTkLabel(scrollable_frame, text="No favorites added yet").pack(pady=10)
            return

        self.tab_radio_vars["Favorites"] = tk.IntVar(value=0)
        self.radio_buttons["Favorites"] = []
        self.radio_button_script_mapping["Favorites"] = {}

        for i, script_name in enumerate(self.favorites, 1):
            script_label = os.path.splitext(script_name)[0]
            script_exists = self.validate_script_exists(script_name)
            
            # Create frame for radio button and remove button
            frame = ctk.CTkFrame(scrollable_frame)
            frame.pack(fill="x", padx=5, pady=2)

            # Create radio button with different styling based on existence
            radio_button = ctk.CTkRadioButton(
                frame,
                text=script_label,
                variable=self.tab_radio_vars["Favorites"],
                value=i,
                command=lambda t="Favorites", v=i: self.on_radio_select(t, v),
                state="normal" if script_exists else "disabled",
                text_color="gray50" if not script_exists else None
            )
            radio_button.pack(side="left", padx=5)

            # Add warning icon and text for missing scripts
            if not script_exists:
                warning_frame = ctk.CTkFrame(frame, fg_color="transparent")
                warning_frame.pack(side="left", padx=2)
                
                warning_label = ctk.CTkLabel(
                    warning_frame,
                    text="⚠️ Script not found",
                    text_color="orange"
                )
                warning_label.pack(side="left")

            remove_button = ctk.CTkButton(
                frame,
                text="Remove",
                width=60,
                command=lambda s=script_name, b=radio_button: self.remove_favorite(s, b),
            )
            remove_button.pack(side="right", padx=5)

            if script_exists:
                self.radio_buttons["Favorites"].append(radio_button)
                self.radio_button_script_mapping["Favorites"][i] = script_name
    
    # Video functions are not used atm. Have commented out the preview button for now. Can add back later
    def preview_video(self):
        selected_tab = self.tabview.get()
        selected_index = self.tab_radio_vars[selected_tab].get()

        if selected_index in self.radio_button_script_mapping[selected_tab]:
            script_name = self.radio_button_script_mapping[selected_tab][selected_index]
            theme = os.path.splitext(script_name)[0]

            video_path = os.path.join("collections", "settings", f"{theme}.mp4")

            if not os.path.exists(video_path):
                print(f"Video file for theme '{theme}' not found.")
                return

            # Stop previous video if any
            self.stop_video()
    
            # Open the video file
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                print("Error: Could not open video.")
                return

            # Get the frame rate of the video
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            wait_time = int(1000 / fps)  # Calculate wait time in milliseconds

            # Create a named window for the video
            cv2.namedWindow("Preview Video", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("Preview Video", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            # Loop through frames and display them
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break  # Exit if the video ends

                # Display the frame in the OpenCV window
                cv2.imshow("Preview Video", frame)

                # Wait for the calculated time or until a key is pressed; break on 'q' key press
                if cv2.waitKey(wait_time) & 0xFF == ord('q'):
                    break

            # Release the video capture and close the window
            self.cap.release()
            cv2.destroyAllWindows()

    def stop_video(self):
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            self.cap = None
            self.video_canvas.delete("all")  # Clear the canvas

    def update_video(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Get the canvas dimensions
                canvas_width = self.video_canvas.winfo_width()
                canvas_height = self.video_canvas.winfo_height()
                
                # Get the aspect ratio of the original frame
                original_height, original_width = frame.shape[:2]
                aspect_ratio = original_width / original_height
                
                 # Calculate new dimensions while maintaining aspect ratio
                if canvas_width / canvas_height < aspect_ratio:
                    new_width = canvas_width
                    new_height = int(canvas_width / aspect_ratio)
                else:
                    new_height = canvas_height
                    new_width = int(canvas_height * aspect_ratio)
                    # Resize the frame
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

                # Convert the image from OpenCV's BGR format to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_frame = ImageTk.PhotoImage(Image.fromarray(frame))
                
                # Update the tkinter canvas with the new frame
                self.video_canvas.create_image(
                    (canvas_width - new_width) // 2, (canvas_height - new_height) // 2,
                    anchor=tk.NW, image=self.current_frame
                )

                # Schedule the next frame update
                self.video_canvas.after(33, self.update_video)  # Adjust for smoother playback based on your video FPS

    def categorize_scripts(self):
        script_categories = {tab: {} for tab in self.tab_keywords}

        for folder in self.config_folders:
            folder_path = os.path.join(self.base_path, folder)
            if not os.path.isdir(folder_path):
                print(f"Folder does not exist: {folder_path}")
                continue

            for filename in os.listdir(folder_path):
                if filename.endswith(".bat") or filename.endswith(".cmd"):
                    added_to_tab = False

                    if folder in self.folder_to_tab_mapping:
                        tab_name = self.folder_to_tab_mapping[folder]
                        script_categories[tab_name][len(script_categories[tab_name]) + 1] = filename
                        added_to_tab = True
                    
                    if not added_to_tab:
                        for tab, keywords in self.tab_keywords.items():
                            if keywords:
                                for keyword in keywords:
                                    if keyword.lower() in filename.lower():
                                        script_categories[tab][len(script_categories[tab]) + 1] = filename
                                        added_to_tab = True
                                        break
                            if added_to_tab:
                                break

                    if not added_to_tab:
                        script_categories["Other"][len(script_categories["Other"]) + 1] = filename

        return script_categories

    def load_favorites(self):
        """Load favorites from a JSON file"""
        favorites_path = os.path.join(self.base_path, "autochanger", 'favorites.json')
        try:
            with open(favorites_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_favorites(self):
        """Save favorites to a JSON file"""
        favorites_path = os.path.join(self.base_path, "autochanger", 'favorites.json')
        with open(favorites_path, 'w') as f:
            json.dump(self.favorites, f)

    def toggle_favorite(self, tab_name, script_name, button):
        """Toggle favorite status for a script"""
        if script_name in self.favorites:
            self.favorites.remove(script_name)
            button.configure(text="☆")  # Empty star
        else:
            self.favorites.append(script_name)
            button.configure(text="★")  # Filled star
        
        self.save_favorites()
        self.update_favorites_tab()

    def remove_favorite(self, script_name, button):
        """Remove a script from favorites"""
        if script_name in self.favorites:
            self.favorites.remove(script_name)
            self.save_favorites()
            self.update_favorites_tab()
            
            # Update the star button in the original tab if it exists
            for tab_name in self.favorite_buttons:
                if script_name in self.favorite_buttons[tab_name]:
                    self.favorite_buttons[tab_name][script_name].configure(text="☆")

    def populate_tabs_and_scripts(self):
        script_categories = self.categorize_scripts()

        for tab_name, scripts in script_categories.items():
            if scripts or tab_name == "Favorites":  # Always create Favorites tab
                self.tabview.add(tab_name)
                self.tab_radio_vars[tab_name] = tk.IntVar(value=0)
                self.radio_button_script_mapping[tab_name] = scripts
                self.radio_buttons[tab_name] = []
                self.favorite_buttons[tab_name] = {}

                scrollable_frame = ctk.CTkScrollableFrame(self.tabview.tab(tab_name), width=400, height=400)
                scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

                if tab_name == "Favorites":
                    self.update_favorites_tab()
                else:
                    for i, script_name in scripts.items():
                        script_label = os.path.splitext(script_name)[0]
                        
                        # Create frame for radio button and favorite button
                        frame = ctk.CTkFrame(scrollable_frame)
                        frame.pack(fill="x", padx=5, pady=2)

                        radio_button = ctk.CTkRadioButton(
                            frame,
                            text=script_label,
                            variable=self.tab_radio_vars[tab_name],
                            value=i,
                            command=lambda t=tab_name, v=i: self.on_radio_select(t, v)
                        )
                        radio_button.pack(side="left", padx=5)

                        # Add favorite toggle button
                        favorite_button = ctk.CTkButton(
                            frame,
                            text="★" if script_name in self.favorites else "☆",
                            width=30,
                            command=lambda t=tab_name, s=script_name, b=None: self.toggle_favorite(t, s, b)
                        )
                        favorite_button.pack(side="right", padx=5)
                        
                        # Store the button reference for later updates
                        self.favorite_buttons[tab_name][script_name] = favorite_button
                        favorite_button.configure(command=lambda t=tab_name, s=script_name, b=favorite_button: 
                                               self.toggle_favorite(t, s, b))

                        self.radio_buttons[tab_name].append(radio_button)

    def set_gui_state(self, enabled):
        """Enable or disable all script-related GUI elements without disabling the tabview itself."""
        # Enable/disable all radio buttons without altering the tab appearance
        for tab_buttons in self.radio_buttons.values():
            for button in tab_buttons:
                button.configure(state="normal" if enabled else "disabled")

        # Show/hide loading label for feedback
        if enabled:
            self.loading_label.pack_forget()
        else:
            self.loading_label.pack(side="bottom", pady=5)
        
        # Force GUI update
        self.parent_tab.update()

    def run_script_threaded(self, script_path):
        """Run the script in a separate thread and print output in real-time to VS Code terminal."""
        import threading
        
        def script_worker():
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(
                    ["cmd.exe", "/c", script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(script_path),
                    startupinfo=startupinfo
                )

                # Output real-time stdout and stderr
                for line in process.stdout:
                    print(line, end='')  # Print each line as it's produced

                for line in process.stderr:
                    print(line, end='')  # Print each error line as it's produced

                process.wait()  # Ensure process completes
            finally:
                # Re-enable the GUI in the main thread
                self.parent_tab.after(0, lambda: self.set_gui_state(True))

        # Start the script in a separate thread
        thread = threading.Thread(target=script_worker)
        thread.daemon = True  # Make thread daemon so it doesn't block program exit
        thread.start()

    def on_radio_select(self, tab_name, value):
        """Handler for radio button selection that automatically runs the script"""
        if value in self.radio_button_script_mapping[tab_name]:
            script_to_run = self.radio_button_script_mapping[tab_name][value]

            script_path = None
            for folder in self.config_folders:
                potential_path = os.path.join(self.base_path, folder, script_to_run)
                if os.path.isfile(potential_path):
                    script_path = potential_path
                    break

            if not script_path:
                messagebox.showerror("Error", f"The script does not exist: {script_to_run}")
                return

            # Disable GUI and show loading state
            self.set_gui_state(False)
            
            # Run the script in a separate thread
            self.run_script_threaded(script_path)
                         
# Main application driver
if __name__ == "__main__":
    # Initialize GUI with customtkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = FilterGamesApp(root)
    root.mainloop()
