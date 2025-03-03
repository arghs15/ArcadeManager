import customtkinter as ctk
import json
import os
import re
from tkinter import messagebox
from typing import Dict, Optional, Set, List, Tuple
import xml.etree.ElementTree as ET

class MAMEControlConfig(ctk.CTk):
    def __init__(self, preview_only=False):
        super().__init__()

        # Initialize core attributes needed for both modes
        self.visible_control_types = ["BUTTON", "JOYSTICK"]
        self.use_fast_mode = False
        self.use_controls_json = True
        self.use_gamedata_json = True
        self.use_mame_xml = True
        self.default_controls = {}
        self.controls_data = []
        self.available_roms = set()
        self.custom_configs = {}
        self.current_game = None
        self.use_xinput = True
        
        # Skip main window setup if in preview-only mode
        if not preview_only:
            # Configure the window
            self.title("MAME Control Configuration Checker")
            self.geometry("1024x768")
            self.fullscreen = True  # Track fullscreen state
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
            
            # Bind F11 key for fullscreen toggle
            self.bind("<F11>", self.toggle_fullscreen)
            self.bind("<Escape>", self.exit_fullscreen)
            
            self.selected_line = None
            self.highlight_tag = "highlight"
            
            # Set initial fullscreen state
            self.after(100, self.state, 'zoomed')  # Use zoomed for Windows
            
            # Find necessary directories
            self.mame_dir = self.find_mame_directory()
            if not self.mame_dir:
                messagebox.showerror("Error", "Please place this script in the MAME directory!")
                self.quit()
                return

            # Create the interface
            self.create_layout()
            
            # Load all data
            self.load_all_data()
        else:
            # For preview-only mode, just initialize minimal attributes
            self.fullscreen = True
            self.preferred_preview_screen = 2  # Default to second screen
            
            # Hide the main window completely
            self.withdraw()

    def toggle_fast_mode(self):
        """Toggle between full mode and fast mode"""
        self.use_fast_mode = self.fast_mode_toggle.get()
        
        # Update the backward compatibility flags
        if self.use_fast_mode:
            # Fast mode - use only gamedata.json
            self.use_controls_json = False
            self.use_gamedata_json = True
            self.use_mame_xml = False
            messagebox.showinfo("Fast Mode Enabled", 
                            "Fast Mode enabled. Only gamedata.json will be used.\n"
                            "The application will restart to apply this change.")
        else:
            # Normal mode - use controls.json and mame.xml, but NO gamedata.json fallback
            self.use_controls_json = True
            self.use_gamedata_json = False  # Set to False to indicate no fallback
            self.use_mame_xml = True
            messagebox.showinfo("Normal Mode Enabled", 
                            "Normal Mode enabled. Using controls.json and mame.xml only (no gamedata.json).\n"
                            "The application will restart to apply this change.")
        
        # Save settings for next start
        self.save_settings()
        
        # Restart the app to apply changes
        self.restart_application()

    def save_settings(self):
        """Save current settings to a JSON file"""
        settings = {
            "use_fast_mode": self.use_fast_mode
        }
        
        settings_path = os.path.join(self.mame_dir, "control_config_settings.json")
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Load settings from JSON file if it exists"""
        settings_path = os.path.join(self.mame_dir, "control_config_settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    
                # Load the flags
                self.use_fast_mode = settings.get("use_fast_mode", False)
                self.use_controls_json = settings.get("use_controls_json", True)
                self.use_gamedata_json = settings.get("use_gamedata_json", True)
                self.use_mame_xml = settings.get("use_mame_xml", True)
                
                # Load screen preference
                if 'preferred_preview_screen' in settings:
                    self.preferred_preview_screen = settings['preferred_preview_screen']
                    print(f"Loaded preferred screen from settings: {self.preferred_preview_screen}")
                
                # Load visibility settings
                if 'visible_control_types' in settings:
                    self.visible_control_types = settings['visible_control_types']
                    print(f"Loaded visible control types: {self.visible_control_types}")
                
                # Update toggle state
                if hasattr(self, 'fast_mode_toggle'):
                    if self.use_fast_mode:
                        self.fast_mode_toggle.select()
                    else:
                        self.fast_mode_toggle.deselect()

                # Load hide preview buttons setting
                if 'hide_preview_buttons' in settings:
                    self.hide_preview_buttons = settings['hide_preview_buttons']
                    # Update toggle if it exists
                    if hasattr(self, 'hide_buttons_toggle'):
                        if self.hide_preview_buttons:
                            self.hide_buttons_toggle.select()
                        else:
                            self.hide_buttons_toggle.deselect()
                else:
                    self.hide_preview_buttons = False
                    
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.hide_preview_buttons = False
        else:
            # Default setting
            self.hide_preview_buttons = False
        
        # Ensure the visible_control_types is initialized even if no settings file exists
        if not hasattr(self, 'visible_control_types') or self.visible_control_types is None:
            self.visible_control_types = ["BUTTON", "JOYSTICK"]
    
    # 5. Add show/hide methods
    def show_button_frame(self):
        """Show the button frame"""
        if hasattr(self, 'frame_bg'):
            self.frame_bg.place(
                relx=0.5, 
                rely=0.95, 
                anchor="center", 
                width=min(1000, self.preview_window.winfo_width()-20), 
                height=80
            )

    def hide_button_frame(self):
        """Hide the button frame"""
        if hasattr(self, 'frame_bg'):
            self.frame_bg.place_forget()
    
    def restart_application(self):
        """Restart the application to apply new settings"""
        # Get the command used to run this script
        import sys
        script_path = sys.argv[0]
        
        # Close the current instance
        self.destroy()
        
        # Start a new instance
        import subprocess
        subprocess.Popen([sys.executable, script_path])
    
    def convert_mapping(self, mapping: str, to_xinput: bool) -> str:
        """Convert between JOYCODE and XInput mappings"""
        xinput_mappings = {
            'JOYCODE_1_BUTTON1': 'XINPUT_1_A',           # A Button
            'JOYCODE_1_BUTTON2': 'XINPUT_1_B',           # B Button
            'JOYCODE_1_BUTTON3': 'XINPUT_1_X',           # X Button
            'JOYCODE_1_BUTTON4': 'XINPUT_1_Y',           # Y Button
            'JOYCODE_1_BUTTON5': 'XINPUT_1_SHOULDER_L',  # Left Bumper
            'JOYCODE_1_BUTTON6': 'XINPUT_1_SHOULDER_R',  # Right Bumper
            'JOYCODE_1_BUTTON7': 'XINPUT_1_TRIGGER_L',   # Left Trigger
            'JOYCODE_1_BUTTON8': 'XINPUT_1_TRIGGER_R',   # Right Trigger
            'JOYCODE_1_BUTTON9': 'XINPUT_1_THUMB_L',     # Left Stick Button
            'JOYCODE_1_BUTTON10': 'XINPUT_1_THUMB_R',    # Right Stick Button
            'JOYCODE_1_HATUP': 'XINPUT_1_DPAD_UP',       # D-Pad Up
            'JOYCODE_1_HATDOWN': 'XINPUT_1_DPAD_DOWN',   # D-Pad Down
            'JOYCODE_1_HATLEFT': 'XINPUT_1_DPAD_LEFT',   # D-Pad Left
            'JOYCODE_1_HATRIGHT': 'XINPUT_1_DPAD_RIGHT', # D-Pad Right
            'JOYCODE_2_BUTTON1': 'XINPUT_2_A',           # A Button
            'JOYCODE_2_BUTTON2': 'XINPUT_2_B',           # B Button
            'JOYCODE_2_BUTTON3': 'XINPUT_2_X',           # X Button
            'JOYCODE_2_BUTTON4': 'XINPUT_2_Y',           # Y Button
            'JOYCODE_2_BUTTON5': 'XINPUT_2_SHOULDER_L',  # Left Bumper
            'JOYCODE_2_BUTTON6': 'XINPUT_2_SHOULDER_R',  # Right Bumper
            'JOYCODE_2_BUTTON7': 'XINPUT_2_TRIGGER_L',   # Left Trigger
            'JOYCODE_2_BUTTON8': 'XINPUT_2_TRIGGER_R',   # Right Trigger
            'JOYCODE_2_BUTTON9': 'XINPUT_2_THUMB_L',     # Left Stick Button
            'JOYCODE_2_BUTTON10': 'XINPUT_2_THUMB_R',    # Right Stick Button
            'JOYCODE_2_HATUP': 'XINPUT_2_DPAD_UP',       # D-Pad Up
            'JOYCODE_2_HATDOWN': 'XINPUT_2_DPAD_DOWN',   # D-Pad Down
            'JOYCODE_2_HATLEFT': 'XINPUT_2_DPAD_LEFT',   # D-Pad Left
            'JOYCODE_2_HATRIGHT': 'XINPUT_2_DPAD_RIGHT', # D-Pad Right
        }
        joycode_mappings = {v: k for k, v in xinput_mappings.items()}
        
        if to_xinput:
            return xinput_mappings.get(mapping, mapping)
        else:
            return joycode_mappings.get(mapping, mapping)

    def format_control_name(self, control_name: str) -> str:
        """Convert MAME control names to friendly names based on input type"""
        if not self.use_xinput:
            return control_name
            
        # Split control name into parts (e.g., 'P1_BUTTON1' -> ['P1', 'BUTTON1'])
        parts = control_name.split('_')
        if len(parts) < 2:
            return control_name
            
        player_num = parts[0]  # e.g., 'P1'
        control_type = '_'.join(parts[1:])  # Join rest in case of JOYSTICK_UP etc.
        
        # Mapping dictionary for controls based on official XInput mapping
        control_mappings = {
            'BUTTON1': 'A Button',
            'BUTTON2': 'B Button',
            'BUTTON3': 'X Button',
            'BUTTON4': 'Y Button',
            'BUTTON5': 'LB Button',
            'BUTTON6': 'RB Button',
            'BUTTON7': 'LT Button',      # Left Trigger (axis)
            'BUTTON8': 'RT Button',      # Right Trigger (axis)
            'BUTTON9': 'LSB Button',     # Left Stick Button
            'BUTTON10': 'RSB Button',    # Right Stick Button
            'JOYSTICK_UP': 'Left Stick (Up)',
            'JOYSTICK_DOWN': 'Left Stick (Down)',
            'JOYSTICK_LEFT': 'Left Stick (Left)',
            'JOYSTICK_RIGHT': 'Left Stick (Right)',
            'JOYSTICK2_UP': 'Right Stick (Up)',
            'JOYSTICK2_DOWN': 'Right Stick (Down)',
            'JOYSTICK2_LEFT': 'Right Stick (Left)',
            'JOYSTICK2_RIGHT': 'Right Stick (Right)',
        }
        
        # Check if we have a mapping for this control
        if control_type in control_mappings:
            return f"{player_num} {control_mappings[control_type]}"
        
        return control_name
    
    def map_control_to_xinput_config(self, control_name: str) -> Tuple[str, str]:
        """Map MAME control to Xbox controller config field"""
        mapping_dict = {
            'P1_BUTTON1': ('controller A t', 'A Button'),      # A
            'P1_BUTTON2': ('controller B t', 'B Button'),      # B
            'P1_BUTTON3': ('controller X t', 'X Button'),      # X
            'P1_BUTTON4': ('controller Y t', 'Y Button'),      # Y
            'P1_BUTTON5': ('controller LB t', 'Left Bumper'),  # LB
            'P1_BUTTON6': ('controller RB t', 'Right Bumper'), # RB
            'P1_BUTTON7': ('controller LT t', 'Left Trigger'), # LT
            'P1_BUTTON8': ('controller RT t', 'Right Trigger'),# RT
            'P1_BUTTON9': ('controller LSB t', 'L3'),          # Left Stick Button
            'P1_BUTTON10': ('controller RSB t', 'R3'),         # Right Stick Button
            'P1_JOYSTICK_UP': ('controller L-stick t', 'Left Stick Up'),
            'P1_JOYSTICK_DOWN': ('controller L-stick t', 'Left Stick Down'),
            'P1_JOYSTICK_LEFT': ('controller L-stick t', 'Left Stick Left'),
            'P1_JOYSTICK_RIGHT': ('controller L-stick t', 'Left Stick Right'),
        }
        return mapping_dict.get(control_name, (None, None))
    
    def format_mapping_display(self, mapping: str) -> str:
        """Format the mapping string for display"""
        # Handle XInput mappings
        if "XINPUT" in mapping:
            # Convert XINPUT_1_A to "XInput A"
            parts = mapping.split('_')
            if len(parts) >= 3:
                button_part = ' '.join(parts[2:])
                return f"XInput {button_part}"
                
        # Handle JOYCODE mappings
        elif "JOYCODE" in mapping:
            # Special handling for axis/stick controls
            if "YAXIS_UP" in mapping or "DPADUP" in mapping:
                return "Joy Stick Up"
            elif "YAXIS_DOWN" in mapping or "DPADDOWN" in mapping:
                return "Joy Stick Down"
            elif "XAXIS_LEFT" in mapping or "DPADLEFT" in mapping:
                return "Joy Stick Left"
            elif "XAXIS_RIGHT" in mapping or "DPADRIGHT" in mapping:
                return "Joy Stick Right"
            elif "RYAXIS_NEG" in mapping:  # Right stick Y-axis negative
                return "Joy Right Stick Up"
            elif "RYAXIS_POS" in mapping:  # Right stick Y-axis positive
                return "Joy Right Stick Down"
            elif "RXAXIS_NEG" in mapping:  # Right stick X-axis negative
                return "Joy Right Stick Left"
            elif "RXAXIS_POS" in mapping:  # Right stick X-axis positive
                return "Joy Right Stick Right"
            
            # Standard button format for other joystick controls
            parts = mapping.split('_')
            if len(parts) >= 4:
                joy_num = parts[1]
                control_type = parts[2].capitalize()
                
                # Extract button number for BUTTON types
                if control_type == "Button" and len(parts) >= 4:
                    button_num = parts[3]
                    return f"Joy {joy_num} {control_type} {button_num}"
                else:
                    # Generic format for other controls
                    remainder = '_'.join(parts[3:])
                    return f"Joy {joy_num} {control_type} {remainder}"
                    
        return mapping
    
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen state"""
        self.fullscreen = not self.fullscreen
        self.attributes('-fullscreen', self.fullscreen)
        
    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        self.fullscreen = False
        self.attributes('-fullscreen', False)
    
    def find_mame_directory(self) -> Optional[str]:
        """Find the MAME directory containing necessary files"""
        current_dir = os.path.abspath(os.path.dirname(__file__))
        controls_json = os.path.join(current_dir, "controls.json")
        
        if os.path.exists(controls_json):
            print(f"Found MAME directory: {current_dir}")
            return current_dir
            
        print("Error: controls.json not found in:", current_dir)
        return None

    def toggle_xinput(self):
        """Handle toggling between JOYCODE and XInput mappings"""
        self.use_xinput = self.xinput_toggle.get()
        print(f"XInput toggle set to: {self.use_xinput}")
        
        # Refresh the current game display if one is selected
        if self.current_game and self.selected_line is not None:
            # Store the current scroll position
            scroll_pos = self.control_frame._scrollbar.get()
            
            # Create a mock event with coordinates for the selected line
            class MockEvent:
                def __init__(self_mock, line_num):
                    # Calculate position to hit the middle of the line
                    bbox = self.game_list.bbox(f"{line_num}.0")
                    if bbox:
                        self_mock.x = bbox[0] + 5  # A bit to the right of line start
                        self_mock.y = bbox[1] + 5  # A bit below line top
                    else:
                        self_mock.x = 5
                        self_mock.y = line_num * 20  # Approximate line height
            
            # Create the mock event targeting our current line
            mock_event = MockEvent(self.selected_line)
            
            # Force a full refresh of the display
            self.on_game_select(mock_event)
            
            # Restore scroll position
            self.control_frame._scrollbar.set(*scroll_pos)
    
    def create_layout(self):
        """Create the main application layout"""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # Create left panel (game list)
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(2, weight=1)

        # Create stats frame at the top of left panel
        self.stats_frame = ctk.CTkFrame(self.left_panel)
        self.stats_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.stats_frame.grid_columnconfigure(1, weight=1)  # Make middle column expandable

        # Stats label
        self.stats_label = ctk.CTkLabel(self.stats_frame, text="Loading...", 
                                    font=("Arial", 12))
        self.stats_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Unmatched ROMs button
        self.unmatched_button = ctk.CTkButton(
            self.stats_frame,
            text="Show Unmatched ROMs",
            command=self.show_unmatched_roms,
            width=150
        )
        self.unmatched_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        # Generate configs button
        self.generate_configs_button = ctk.CTkButton(
            self.stats_frame,
            text="Generate Info Files",
            command=self.generate_all_configs,
            width=150
        )
        self.generate_configs_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        # Search box
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.filter_games)
        self.search_entry = ctk.CTkEntry(self.left_panel, 
                                    placeholder_text="Search games...",
                                    textvariable=self.search_var)
        self.search_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # Game list with improved styling
        self.game_list = ctk.CTkTextbox(self.left_panel, font=("Arial", 13))
        self.game_list.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        self.game_list._textbox.tag_configure(self.highlight_tag, background="#1a5fb4", foreground="white")
        self.game_list.configure(padx=5, pady=5)
        self.game_list.bind("<Button-1>", self.on_game_select)

        # Create right panel (control display)
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=1)

        # Game title
        self.game_title = ctk.CTkLabel(self.right_panel, 
                                    text="Select a game",
                                    font=("Arial", 20, "bold"))
        self.game_title.grid(row=0, column=0, padx=5, pady=5)

        # Add Preview button next to the game title
        self.preview_button = ctk.CTkButton(
            self.right_panel,
            text="Preview Controls",
            command=self.show_preview,
            width=150
        )
        self.preview_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.hide_buttons_toggle = ctk.CTkSwitch(
            self.right_panel,
            text="Hide Preview Buttons",
            command=self.toggle_hide_preview_buttons
        )
        self.hide_buttons_toggle.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        # Add XInput toggle switch
        self.xinput_toggle = ctk.CTkSwitch(
            self.right_panel,
            text="Use XInput Mappings",
            command=self.toggle_xinput
        )
        self.xinput_toggle.select()  # Set it on by default
        self.xinput_toggle.grid(row=1, column=0, padx=5, pady=5)

        # Add In-Game Mode toggle
        self.ingame_toggle = ctk.CTkSwitch(
            self.right_panel,
            text="In-Game Mode",
            command=self.toggle_ingame_mode
        )
        self.ingame_toggle.grid(row=1, column=1, padx=5, pady=5, sticky="e")
        
        # In create_layout, add this near your other toggles
        self.fast_mode_frame = ctk.CTkFrame(self.right_panel)
        self.fast_mode_frame.grid(row=1, column=2, padx=5, pady=5, sticky="e")

        self.fast_mode_toggle = ctk.CTkSwitch(
            self.fast_mode_frame,
            text="Fast Mode (gamedata.json only)",
            command=self.toggle_fast_mode
        )
        self.fast_mode_toggle.grid(row=0, column=0, padx=5, pady=5)

        # Controls display
        self.control_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.control_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

    def show_preview(self):
        """Show a preview of the control layout for the current game on the second screen"""
        if not self.current_game:
            messagebox.showinfo("No Game Selected", "Please select a game first")
            return
            
        # Create preview directory if it doesn't exist
        preview_dir = os.path.join(self.mame_dir, "preview")
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)

        # Check for a ROM-specific image (PNG or JPG)
        image_extensions = [".png", ".jpg", ".jpeg"]
        image_path = None

        for ext in image_extensions:
            test_path = os.path.join(preview_dir, f"{self.current_game}{ext}")
            if os.path.exists(test_path):
                image_path = test_path
                break

        # Fall back to default image (PNG or JPG)
        if not image_path:
            for ext in image_extensions:
                test_path = os.path.join(preview_dir, f"default{ext}")
                if os.path.exists(test_path):
                    image_path = test_path
                    break

        # If no image found, show a message
        if not image_path:
            messagebox.showinfo(
                "Image Not Found",
                f"No preview image found for {self.current_game}\n"
                f"Place PNG or JPG images in {preview_dir} folder"
            )
            return

        # Get game control data
        game_data = self.get_game_data(self.current_game)
        if not game_data:
            messagebox.showinfo("No Control Data", f"No control data found for {self.current_game}")
            return

        
        # Check for screen preference in settings
        preferred_screen = getattr(self, 'preferred_preview_screen', 2)  # Default to second screen
        
        # We'll use tkinter directly for the window but CustomTkinter for buttons
        import tkinter as tk
        from PIL import Image, ImageTk
        
        # Create our preview window directly
        self.preview_window = tk.Toplevel()
        self.preview_window.title(f"Control Preview: {self.current_game}")
        
        # Hide window initially and prevent flashing
        self.preview_window.withdraw()
        
        # Get information about monitors through direct Windows API if possible
        monitors = []
        try:
            # Try to use Windows API
            import ctypes
            from ctypes import windll
            
            # Define structs needed to get monitor info
            class RECT(ctypes.Structure):
                _fields_ = [
                    ('left', ctypes.c_long),
                    ('top', ctypes.c_long),
                    ('right', ctypes.c_long),
                    ('bottom', ctypes.c_long)
                ]
                
            # Get monitor info
            def callback(monitor, dc, rect, data):
                rect = ctypes.cast(rect, ctypes.POINTER(RECT)).contents
                monitors.append({
                    'left': rect.left,
                    'top': rect.top,
                    'right': rect.right,
                    'bottom': rect.bottom,
                    'width': rect.right - rect.left,
                    'height': rect.bottom - rect.top,
                    'index': len(monitors)  # Add index for selection
                })
                return 1
                
            MonitorEnumProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_ulong,
                ctypes.c_ulong,
                ctypes.POINTER(RECT),
                ctypes.c_double
            )
            
            # Enumerate monitors
            windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
            
            print(f"Found {len(monitors)} monitors")
            for i, mon in enumerate(monitors):
                print(f"Monitor {i+1}: {mon['width']}x{mon['height']} at position {mon['left']},{mon['top']}")
                
        except Exception as e:
            print(f"Error using Windows API for monitor detection: {e}")
            # Create a minimal monitor list with defaults
            monitors = [{'left': 0, 'top': 0, 'width': 1920, 'height': 1080, 'index': 0}]
            
            # Try to detect second monitor using simple method
            full_width = self.winfo_screenwidth()
            if full_width > 2000:  # Assume wide screen means multiple monitors
                monitors.append({
                    'left': 1920, 'top': 0, 
                    'width': full_width - 1920, 'height': self.winfo_screenheight(),
                    'index': 1
                })
                print(f"Detected probable second monitor at x=1920 (simple method)")
        
        # Force at least two monitors for button functionality
        if len(monitors) < 2:
            monitors.append({
                'left': monitors[0]['width'], 
                'top': 0, 
                'width': monitors[0]['width'], 
                'height': monitors[0]['height'],
                'index': 1
            })
            print(f"Added virtual second monitor for button functionality")
        
        # Use selected monitor or fall back to primary
        target_monitor = None
        if 0 <= preferred_screen - 1 < len(monitors):
            target_monitor = monitors[preferred_screen - 1]
            print(f"Using preferred screen {preferred_screen}: {target_monitor}")
        else:
            # Default to first monitor if preferred screen doesn't exist
            target_monitor = monitors[0]
            print(f"Preferred screen {preferred_screen} not available, using monitor 1")
            
        # Position window on selected monitor
        window_x = target_monitor['left']
        window_y = target_monitor['top']
        window_width = target_monitor['width']
        window_height = target_monitor['height']
        
        print(f"Setting window dimensions: {window_width}x{window_height}+{window_x}+{window_y}")
        
        # Configure the preview window
        self.preview_window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
        
        # Make it fullscreen without window decorations
        self.preview_window.overrideredirect(True)
        
        # Update tasks to allow window to process
        self.preview_window.update_idletasks()
        
        # Make the window visible
        self.preview_window.deiconify()
        
        # Ensure it stays on top
        self.preview_window.attributes('-topmost', True)

        # Bind ESC to close the window
        self.preview_window.bind("<Escape>", lambda event: self.preview_window.destroy())

        # Make the window visible
        self.preview_window.deiconify()
        
        # Load and display the image
        try:
            # Load the image
            img = Image.open(image_path)
            print(f"Loaded image: {image_path}, size={img.size}")
            
            # Get window dimensions (use the values we set earlier)
            win_width = window_width
            win_height = window_height
            
            # Resize image to fit window while maintaining aspect ratio
            img_width, img_height = img.size
            
            # Ensure dimensions are positive
            if win_width <= 0:
                win_width = 1024
            if win_height <= 0:
                win_height = 768
            
            # Handle zero-size image
            if img_width <= 0 or img_height <= 0:
                print("Image has invalid dimensions, creating blank image")
                img = Image.new('RGB', (win_width, win_height), color='black')
                img_width, img_height = img.size
            
            # Calculate resize ratio
            ratio = min(win_width/max(img_width, 1), win_height/max(img_height, 1))
            new_width = max(int(img_width * ratio), 1)  # Ensure at least 1 pixel
            new_height = max(int(img_height * ratio), 1)  # Ensure at least 1 pixel
            
            print(f"Resizing image to: {new_width}x{new_height}")
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Create canvas with black background
            canvas = tk.Canvas(self.preview_window, 
                            width=win_width, 
                            height=win_height,
                            bg="black",
                            highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            
            # Center the image
            x = max((win_width - new_width) // 2, 0)
            y = max((win_height - new_height) // 2, 0)
            canvas.create_image(x, y, image=photo, anchor="nw")
            canvas.image = photo  # Keep a reference to prevent garbage collection
            
            # Store canvas and image info for text placement
            self.preview_canvas = canvas
            self.image_x = x
            self.image_y = y
            
            # Add control text overlays - track them for movement
            self.text_items = {}
            
            # Try to load saved positions first (from global file)
            # Try to load saved positions, checking ROM-specific first then global
            positions = self.load_text_positions(self.current_game)
            print(f"Loaded {len(positions)} positions from global file")
            
            # Add player controls as text overlays
            text_y = y + 50  # Start 50px from top of image
            control_count = 0
            
            # Process only Player 1 controls
            for player in game_data.get('players', []):
                if player['number'] != 1:
                    continue
                    
                for label in player.get('labels', []):
                    control_name = label['name']
                    action = label['value']
                    
                    # Only include P1 controls
                    if not control_name.startswith('P1_'):
                        continue
                    
                    print(f"Adding control: {control_name} = {action}")
                    
                    # Position text (use saved positions if available, otherwise spread across the top)
                    if control_name in positions:
                        text_x, text_y = positions[control_name]
                        print(f"Using saved position for {control_name}: {text_x}, {text_y}")
                    else:
                        text_x = x + 100 + (control_count * 150) % (new_width - 200)
                        if text_x + 100 > x + new_width:
                            text_x = x + 100
                            text_y += 40
                        print(f"Using default position for {control_name}: {text_x}, {text_y}")
                    
                    # Check visibility based on control type
                    is_visible = False
                    for control_type in self.visible_control_types:
                        if control_type in control_name:
                            is_visible = True
                            break
                    
                    # Create text with shadow for better visibility
                    shadow = canvas.create_text(text_x+2, text_y+2, text=action, 
                                            font=("Arial", 20, "bold"), fill="black",
                                            anchor="sw", state="" if is_visible else "hidden")
                    text_item = canvas.create_text(text_x, text_y, text=action, 
                                            font=("Arial", 20, "bold"), fill="white",
                                            anchor="sw", state="" if is_visible else "hidden")
                    
                    # Store the text items
                    self.text_items[control_name] = {
                        'text': text_item,
                        'shadow': shadow,
                        'action': action,
                        'x': text_x, 
                        'y': text_y
                    }
                    
                    # Make the text draggable
                    self.make_draggable(canvas, text_item, shadow, control_name)
                    control_count += 1
            
            # Add right-click menu for text removal
            self.create_context_menu(canvas)
            
            # Create a transparent frame for buttons with fixed width
            self.frame_bg = tk.Frame(self.preview_window, bg="black")  # Changed to self.frame_bg

            # Only show if setting allows
            if not hasattr(self, 'hide_preview_buttons') or not self.hide_preview_buttons:
                self.frame_bg.place(relx=0.5, rely=0.95, anchor="center", width=min(1000, window_width-20), height=80)

            # Create ctk frame with default color
            button_frame = ctk.CTkFrame(self.frame_bg)  # Changed from frame_bg to self.frame_bg
            button_frame.pack(expand=True, fill="both")
            self.button_frame = button_frame  # Store reference to button frame

            # Create two rows of buttons using frames
            top_row = ctk.CTkFrame(button_frame)
            top_row.pack(side="top", fill="x", expand=True, pady=2)

            bottom_row = ctk.CTkFrame(button_frame)
            bottom_row.pack(side="bottom", fill="x", expand=True, pady=2)

            # Store row references for the feature buttons
            self.button_row1 = top_row
            self.button_row2 = bottom_row

            # Calculate button width to fit all buttons
            button_width = 90  # Slightly smaller width
            button_padx = 3    # Smaller padding

            # Top row buttons (4 buttons)
            # Close button
            close_button = ctk.CTkButton(
                top_row,
                text="Close",
                command=self.preview_window.destroy,
                width=button_width
            )
            close_button.pack(side="left", padx=button_padx)

            # Reset positions button
            reset_button = ctk.CTkButton(
                top_row,
                text="Reset",
                command=self.reset_text_positions,
                width=button_width
            )
            reset_button.pack(side="left", padx=button_padx)

            # Add save buttons
            global_button = ctk.CTkButton(
                top_row,
                text="Global",
                command=self.save_global_positions,
                width=button_width
            )
            global_button.pack(side="left", padx=button_padx)

            # ROM button
            rom_button = ctk.CTkButton(
                top_row,
                text="ROM",
                command=self.save_rom_positions,
                width=button_width
            )
            rom_button.pack(side="left", padx=button_padx)

            # Bottom row buttons
            # Set initial state for toggle buttons
            self.show_texts = True

            # Add toggle joystick button
            joystick_button = ctk.CTkButton(
                bottom_row,
                text="Joystick",
                command=self.toggle_joystick_controls,
                width=button_width
            )
            joystick_button.pack(side="left", padx=button_padx)

            # Add toggle texts button to bottom row
            def toggle_texts():
                self.toggle_texts_visibility()
                texts_button.configure(text="Hide Texts" if self.show_texts else "Show Texts")
                
            texts_button = ctk.CTkButton(
                bottom_row,
                text="Hide Texts",
                command=toggle_texts,
                width=button_width
            )
            texts_button.pack(side="left", padx=button_padx)

            # Add toggle screen button to bottom row
            def toggle_screen():
                # Cycle to the next available monitor
                current_screen = getattr(self, 'preferred_preview_screen', 2)
                next_screen = (current_screen % len(monitors)) + 1
                
                # Set the preference and print
                self.preferred_preview_screen = next_screen
                print(f"Switching to screen {next_screen}")
                
                # Close and reopen the preview window
                self.preview_window.destroy()
                self.show_preview()
                
            screen_button = ctk.CTkButton(
                bottom_row,
                text=f"Screen {preferred_screen}",
                command=toggle_screen,
                width=button_width
            )
            screen_button.pack(side="left", padx=button_padx)

            # Add the feature functions
            self.add_alignment_guides()
            self.add_show_all_buttons_feature()
        
        except ImportError:
            messagebox.showinfo("Missing Package", "Please install Pillow: pip install pillow")
        except Exception as e:
            messagebox.showerror("Error", f"Error displaying image: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 2. Add the toggle handler method
    def toggle_hide_preview_buttons(self):
        """Toggle whether preview buttons should be hidden"""
        self.hide_preview_buttons = self.hide_buttons_toggle.get()
        
        # Save setting to config file
        self.save_preview_button_setting()
        
        # Update any open preview windows
        if hasattr(self, 'preview_window') and self.preview_window.winfo_exists():
            if self.hide_preview_buttons:
                self.hide_button_frame()
            else:
                self.show_button_frame()

    # 3. Add methods to save and load the setting
    def save_preview_button_setting(self):
        """Save the preview buttons visibility setting"""
        try:
            # Get the settings file path
            settings_path = os.path.join(self.mame_dir, "control_config_settings.json")
            
            # Load existing settings if available
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            
            # Add hide buttons setting
            settings['hide_preview_buttons'] = self.hide_preview_buttons
            
            # Save back to file
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
                
            print(f"Saved hide_preview_buttons setting: {self.hide_preview_buttons}")
        except Exception as e:
            print(f"Error saving setting: {e}")
    
    def save_visibility_settings(self):
        """Save joystick visibility and other display settings"""
        try:
            # Get the settings file path
            settings_path = os.path.join(self.mame_dir, "control_config_settings.json")
            
            # Load existing settings if available
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            
            # Add visibility settings
            settings['visible_control_types'] = self.visible_control_types
            
            # Save back to file
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
                
            print(f"Saved visibility settings: {self.visible_control_types}")
            return True
        except Exception as e:
            print(f"Error saving visibility settings: {e}")
            return False

    def toggle_joystick_controls(self):
        """Toggle joystick controls visibility and save the setting"""
        # Check if joystick is currently visible
        joystick_visible = "JOYSTICK" in self.visible_control_types
        
        if joystick_visible:
            # Remove JOYSTICK from visible types
            self.visible_control_types.remove("JOYSTICK")
        else:
            # Add JOYSTICK to visible types
            self.visible_control_types.append("JOYSTICK")
        
        # Update existing controls
        joystick_visible = not joystick_visible  # New state
        state = "" if joystick_visible else "hidden"
        
        # Update visibility of current controls
        for control_name, data in self.text_items.items():
            if "JOYSTICK" in control_name:
                self.preview_canvas.itemconfigure(data['text'], state=state)
                self.preview_canvas.itemconfigure(data['shadow'], state=state)
        
        # Save the visibility setting
        self.save_visibility_settings()
    
    
    def save_global_positions(self):
        """Save all positions to global file"""
        if hasattr(self, 'showing_all_controls') and self.showing_all_controls:
            return self.save_all_controls_positions()
        
        try:
            # Get all current positions 
            positions = {}
            for name, data in self.text_items.items():
                if 'x' not in data or 'y' not in data:
                    print(f"  Warning: Missing x/y for {name}")
                    continue
                    
                x, y = data['x'], data['y']
                positions[name] = [x, y]  # Use lists instead of tuples
                
            if not positions:
                print("  Warning: No positions to save!")
                messagebox.showinfo("Error", "No valid positions found to save")
                return False
                
            # Create preview directory if it doesn't exist
            preview_dir = os.path.join(self.mame_dir, "preview")
            os.makedirs(preview_dir, exist_ok=True)
            
            # Save to file with explicit path
            filepath = os.path.join(preview_dir, "global_positions.json")
            
            with open(filepath, 'w') as f:
                json.dump(positions, f)
                
            print(f"Saved {len(positions)} global positions to: {filepath}")
            messagebox.showinfo("Success", f"Global positions saved ({len(positions)} items)")
            return True
        except Exception as e:
            print(f"Error saving global positions: {e}")
            messagebox.showerror("Error", f"Could not save positions: {e}")
            return False

    def save_rom_positions(self):
        """Save positions for current ROM"""
        if not self.current_game:
            messagebox.showinfo("Error", "No game selected")
            return False
            
        try:
            # Get all current positions
            positions = {}
            for name, data in self.text_items.items():
                if 'x' not in data or 'y' not in data:
                    print(f"  Warning: Missing x/y for {name}")
                    continue
                    
                x, y = data['x'], data['y']
                positions[name] = [x, y]  # Use lists instead of tuples
                
            if not positions:
                print("  Warning: No positions to save!")
                messagebox.showinfo("Error", "No valid positions found to save")
                return False
                
            # Create preview directory if it doesn't exist  
            preview_dir = os.path.join(self.mame_dir, "preview")
            os.makedirs(preview_dir, exist_ok=True)
            
            # Save to file with explicit path
            filepath = os.path.join(preview_dir, f"{self.current_game}_positions.json")
            
            with open(filepath, 'w') as f:
                json.dump(positions, f)
                
            print(f"Saved {len(positions)} positions for {self.current_game} to: {filepath}")
            messagebox.showinfo("Success", f"Positions saved for {self.current_game}")
            return True
        except Exception as e:
            print(f"Error saving ROM positions: {e}")
            messagebox.showerror("Error", f"Could not save positions: {e}")
            return False
    
    def make_draggable(self, canvas, text_item, shadow_item, control_name):
        """Make text draggable on the canvas with proper coordinate tracking"""
        def on_drag_start(event):
            # Save initial position
            canvas.drag_data = {
                'text': text_item,
                'shadow': shadow_item,
                'control': control_name,
                'x': canvas.canvasx(event.x),
                'y': canvas.canvasy(event.y)
            }
        
        def on_drag_motion(event):
            if hasattr(canvas, 'drag_data'):
                try:
                    control_name = canvas.drag_data['control']
                    
                    # Calculate movement
                    dx = canvas.canvasx(event.x) - canvas.drag_data['x']
                    dy = canvas.canvasy(event.y) - canvas.drag_data['y']
                    
                    # Move the text and shadow
                    canvas.move(canvas.drag_data['text'], dx, dy)
                    canvas.move(canvas.drag_data['shadow'], dx, dy)
                    
                    # Update saved coordinates
                    canvas.drag_data['x'] = canvas.canvasx(event.x)
                    canvas.drag_data['y'] = canvas.canvasy(event.y)
                    
                    # Update stored position with explicit values
                    old_x = self.text_items[control_name]['x']
                    old_y = self.text_items[control_name]['y']
                    new_x = old_x + dx
                    new_y = old_y + dy
                    
                    # Print debugging for buttons
                    if "BUTTON" in control_name:
                        print(f"Dragging {control_name}: ({old_x},{old_y}) -> ({new_x},{new_y})")
                        
                    # Update the dictionary
                    self.text_items[control_name]['x'] = new_x
                    self.text_items[control_name]['y'] = new_y
                except Exception as e:
                    print(f"Error in drag motion: {e}")
                    import traceback
                    traceback.print_exc()
        
        def on_drag_end(event):
            # Clean up
            if hasattr(canvas, 'drag_data'):
                try:
                    # Print final position for debugging
                    x, y = self.text_items[control_name]['x'], self.text_items[control_name]['y']
                    print(f"Final position for {control_name}: x={x}, y={y}")
                except Exception as e:
                    print(f"Error in drag end: {e}")
                finally:
                    delattr(canvas, 'drag_data')
        
        # Bind mouse events to the text
        canvas.tag_bind(text_item, "<ButtonPress-1>", on_drag_start)
        canvas.tag_bind(text_item, "<B1-Motion>", on_drag_motion)
        canvas.tag_bind(text_item, "<ButtonRelease-1>", on_drag_end)

    def create_context_menu(self, canvas):
        """Create right-click menu for text items"""
        from tkinter import Menu
        
        def show_context_menu(event):
            # Find text item under cursor
            items = canvas.find_closest(canvas.canvasx(event.x), canvas.canvasy(event.y))
            if items:
                for control_name, data in self.text_items.items():
                    if data['text'] == items[0] or data['shadow'] == items[0]:
                        self.selected_text = control_name
                        context_menu.post(event.x_root, event.y_root)
                        break
        
        def remove_text():
            if hasattr(self, 'selected_text'):
                control_name = self.selected_text
                if control_name in self.text_items:
                    # Remove text from canvas
                    canvas.delete(self.text_items[control_name]['text'])
                    canvas.delete(self.text_items[control_name]['shadow'])
                    del self.text_items[control_name]
        
        def reset_text():
            if hasattr(self, 'selected_text'):
                self.reset_single_text_position(self.selected_text)
        
        # Create menu
        context_menu = Menu(canvas, tearoff=0)
        context_menu.add_command(label="Remove Text", command=remove_text)
        context_menu.add_command(label="Reset Position", command=reset_text)
        
        # Bind right-click
        canvas.bind("<Button-3>", show_context_menu)

    def save_text_positions_global(self):
        """Save positions globally for all games"""
        if not self.current_game:
            messagebox.showinfo("No Game", "No game is selected")
            return
            
        # Define the global file path
        preview_dir = os.path.join(self.mame_dir, "preview")
        global_file = os.path.join(preview_dir, "global_positions.json")
        
        # Save to this file
        if self.save_positions_to_file(global_file):
            messagebox.showinfo("Success", "Positions saved globally for all games")
    
    def load_text_positions(self, rom_name):
        """Load text positions, with more reliable file path handling"""
        positions = {}
        
        # Create preview directory if it doesn't exist
        preview_dir = os.path.join(self.mame_dir, "preview")
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)
            return positions  # Return empty positions if directory was just created
        
        # First try ROM-specific positions - with explicit path
        rom_positions_file = os.path.join(preview_dir, f"{rom_name}_positions.json")
        if os.path.exists(rom_positions_file):
            try:
                with open(rom_positions_file, 'r') as f:
                    positions = json.load(f)
                print(f"Loaded {len(positions)} ROM-specific positions from: {rom_positions_file}")
                return positions
            except Exception as e:
                print(f"Error loading ROM-specific positions: {e}")
        
        # Fall back to global positions - with explicit path
        global_positions_file = os.path.join(preview_dir, "global_positions.json")
        if os.path.exists(global_positions_file):
            try:
                with open(global_positions_file, 'r') as f:
                    positions = json.load(f)
                print(f"Loaded {len(positions)} positions from global file: {global_positions_file}")
            except Exception as e:
                print(f"Error loading global positions: {e}")
        
        return positions
    
    def reset_text_positions(self):
        """Reset all text positions to default"""
        text_y = self.image_y + 50
        i = 0
        
        for control_name in list(self.text_items.keys()):
            self.reset_single_text_position(control_name, index=i)
            i += 1

    def reset_single_text_position(self, control_name, index=None):
        """Reset a single text to default position"""
        if index is None:
            index = list(self.text_items.keys()).index(control_name)
        
        # Calculate default position (5 items per row)
        text_x = self.image_x + 100 + (index % 5) * 150
        text_y = self.image_y + 50 + (index // 5) * 40
        
        # Move text and shadow
        data = self.text_items[control_name]
        self.preview_canvas.coords(data['text'], text_x, text_y)
        self.preview_canvas.coords(data['shadow'], text_x+2, text_y+2)
        
        # Update stored position
        self.text_items[control_name]['x'] = text_x
        self.text_items[control_name]['y'] = text_y

    def toggle_texts_visibility(self):
        """Toggle visibility of all text items"""
        import tkinter as tk  # Add the import here
        
        self.show_texts = not self.show_texts
        
        # Set visibility state for vanilla tkinter
        state = tk.NORMAL if self.show_texts else tk.HIDDEN
        for data in self.text_items.values():
            self.preview_canvas.itemconfig(data['text'], state=state)
            self.preview_canvas.itemconfig(data['shadow'], state=state)
    
    def load_all_data(self):
        """Load all necessary data sources"""
        # Load settings from file
        self.load_settings()
        
        # Scan ROMs directory (always needed)
        self.scan_roms_directory()
        
        # Load default controls first
        self.load_default_config()  # Add this line
        
        # Load only the enabled data sources
        if not self.use_fast_mode:
            self.load_controls_data()
            if self.use_mame_xml:
                self.load_mame_xml()
        
        if self.use_fast_mode or self.use_gamedata_json:
            self.load_gamedata_json()
        
        # Always load custom configs
        self.load_custom_configs()
        
        # Update UI
        self.update_stats_label()
        self.update_game_list()
        
        # Auto-select first ROM
        self.select_first_rom()

    def select_first_rom(self):
        """Select and display the first available ROM with support for both modes"""
        print("\n=== Auto-selecting first ROM ===")
        
        try:
            # Different approach based on mode
            if self.use_fast_mode:
                print("Using fast mode ROM selection")
                # In fast mode, we might need to use a different data source
                if hasattr(self, 'gamedata_json') and self.gamedata_json:
                    # Get first ROM that exists in both available_roms and gamedata_json
                    available_fast_roms = sorted(
                        rom for rom in self.available_roms 
                        if rom in self.gamedata_json
                    )
                    
                    if available_fast_roms:
                        first_rom = available_fast_roms[0]
                        print(f"Selected first ROM from fast mode: {first_rom}")
                    else:
                        print("No matching ROMs found in fast mode")
                        return
                else:
                    print("No gamedata.json loaded for fast mode")
                    return
            else:
                print("Using normal mode ROM selection")
                # Normal mode - use controls_data
                available_games = sorted(
                    game['romname'] for game in self.controls_data 
                    if game['romname'] in self.available_roms
                )
                
                if available_games:
                    first_rom = available_games[0]
                    print(f"Selected first ROM from normal mode: {first_rom}")
                else:
                    print("No matching ROMs found in normal mode")
                    return
            
            # Check if the game list has content
            list_content = self.game_list.get("1.0", "end-1c")
            if not list_content.strip():
                print("Game list appears to be empty")
                return
            
            # Find the line with our ROM
            lines = list_content.split('\n')
            target_line = None
            
            for i, line in enumerate(lines):
                if first_rom in line:
                    target_line = i + 1  # Lines are 1-indexed in Tkinter
                    print(f"Found ROM on line {target_line}: '{line}'")
                    break
                    
            if target_line is None:
                print(f"Could not find '{first_rom}' in game list")
                return
            
            # Directly highlight and set current_game
            self.highlight_selected_game(target_line)
            self.current_game = first_rom
            
            # Get game data
            game_data = self.get_game_data(first_rom)
            if game_data:
                # Update game title
                self.game_title.configure(text=game_data['gamename'])
                
                # Clear existing display
                for widget in self.control_frame.winfo_children():
                    widget.destroy()
                
                # Force display update by simulating a game selection
                # Create a mock event targeting the line
                class MockEvent:
                    def __init__(self):
                        self.x = 10
                        self.y = target_line * 20
                
                self.on_game_select(MockEvent())
                
                print(f"Auto-selected ROM: {first_rom}")
            else:
                print(f"No game data available for {first_rom}")
                
        except Exception as e:
            print(f"Error in auto-selection: {e}")
            import traceback
            traceback.print_exc()

    def toggle_ingame_mode(self):
        """Toggle between normal and in-game display modes"""
        if self.ingame_toggle.get():
            self.switch_to_ingame_mode()
        else:
            # Create mock event to reuse existing game select logic
            class MockEvent:
                def __init__(self):
                    self.x = 0
                    self.y = 5
            self.on_game_select(MockEvent())
            
    def switch_to_ingame_mode(self):
        """Switch to a simplified, large-format display for in-game reference"""
        if not self.current_game:
            return
            
        # Clear existing display
        for widget in self.control_frame.winfo_children():
            widget.destroy()
            
        # Get the current game's controls
        game_data = next((game for game in self.controls_data if game['romname'] == self.current_game), None)
        if not game_data:
            return
            
        # Get custom controls
        cfg_controls = {}
        if self.current_game in self.custom_configs:
            cfg_controls = self.parse_cfg_controls(self.custom_configs[self.current_game])
            if self.use_xinput:
                cfg_controls = {
                    control: self.convert_mapping(mapping, True)
                    for control, mapping in cfg_controls.items()
                }

        # Configure single column layout
        self.control_frame.grid_columnconfigure(0, weight=1)

        # Create controls display with large font
        controls_frame = ctk.CTkFrame(self.control_frame)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        row = 0
        for player in game_data.get('players', []):
            # Player header
            player_label = ctk.CTkLabel(
                controls_frame,
                text=f"Player {player['number']}",
                font=("Arial", 24, "bold")
            )
            player_label.grid(row=row, column=0, padx=10, pady=(20,10), sticky="w")
            row += 1
            
            # Player controls
            for label in player.get('labels', []):
                control_name = label['name']
                default_action = label['value']
                current_mapping = cfg_controls.get(control_name, "Default")
                
                display_control = self.format_control_name(control_name)
                display_mapping = self.format_mapping_display(current_mapping)
                
                # Create a frame for each control to better organize the information
                control_frame = ctk.CTkFrame(controls_frame)
                control_frame.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
                control_frame.grid_columnconfigure(1, weight=1)  # Make action column expandable
                
                # Control name
                ctk.CTkLabel(
                    control_frame,
                    text=display_control,
                    font=("Arial", 20, "bold"),
                    anchor="w"
                ).grid(row=0, column=0, padx=5, pady=2, sticky="w")

                # Default action
                default_label = ctk.CTkLabel(
                    control_frame,
                    text=f"Action: {default_action}",
                    font=("Arial", 18),
                    text_color="gray75",
                    anchor="w"
                )
                default_label.grid(row=1, column=0, columnspan=2, padx=20, pady=2, sticky="w")
                
                # Current mapping (if different from default)
                if current_mapping != "Default":
                    mapping_label = ctk.CTkLabel(
                        control_frame,
                        text=f"Mapped to: {display_mapping}",
                        font=("Arial", 18),
                        text_color="yellow",
                        anchor="w"
                    )
                    mapping_label.grid(row=2, column=0, columnspan=2, padx=20, pady=2, sticky="w")
                
                row += 1
    
    def load_controls_data(self):
        """Load the controls.json data with variant matching"""
        controls_path = os.path.join(self.mame_dir, "controls.json")
        try:
            print(f"\nLoading controls from: {controls_path}")
            with open(controls_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                base_controls = data.get('games', [])
                
            print(f"Loaded base control data for {len(base_controls)} games")
            
            # Keep original controls data
            self.controls_data = base_controls
            
            # Create variant mapping
            self.control_variants = {}
            for game in base_controls:
                romname = game['romname']
                # Strip region suffixes for variant matching
                base_name = re.sub(r'[jubew]$', '', romname)
                self.control_variants[base_name] = game
                
            # Check for matches
            matched = set()
            for rom in self.available_roms:
                # Direct match
                if any(game['romname'] == rom for game in self.controls_data):
                    matched.add(rom)
                    continue
                
                # Try variant match
                base_name = re.sub(r'[jubew]$', '', rom)
                if base_name in self.control_variants:
                    matched.add(rom)
            
            print(f"\nMatching results:")
            print(f"- Direct or variant matches: {len(matched)}")
            print(f"- Unmatched ROMs: {len(self.available_roms - matched)}")
            
            if len(matched) > 0:
                print("\nSample matches:")
                for rom in list(matched)[:5]:
                    print(f"Found match for: {rom}")
            
        except Exception as e:
            print(f"ERROR loading controls.json: {str(e)}")
            messagebox.showerror("Error", f"Error loading controls.json: {str(e)}")

    def load_gamedata_json(self):
        """Load and parse the gamedata.json file for additional control data"""
        if hasattr(self, 'gamedata_json'):
            # Already loaded
            return self.gamedata_json
            
        self.gamedata_json = {}
        
        # Look for gamedata.json in common locations
        json_paths = [
            os.path.join(self.mame_dir, "gamedata.json"),
            os.path.join(self.mame_dir, "metadata", "gamedata.json"),
            os.path.join(self.mame_dir, "data", "gamedata.json")
        ]
        
        json_path = None
        for path in json_paths:
            if os.path.exists(path):
                json_path = path
                break
        
        if not json_path:
            print("gamedata.json not found")
            return {}
            
        try:
            print(f"Loading gamedata.json from: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Process the data to find both main games and clones
            for rom_name, game_data in data.items():
                self.gamedata_json[rom_name] = game_data
                
                # Also index clones for easier lookup
                if 'clones' in game_data:
                    for clone_name, clone_data in game_data['clones'].items():
                        # Store clone with reference to parent
                        clone_data['parent'] = rom_name
                        self.gamedata_json[clone_name] = clone_data
            
            print(f"Loaded {len(self.gamedata_json)} games from gamedata.json")
            return self.gamedata_json
            
        except Exception as e:
            print(f"Error loading gamedata.json: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_game_data(self, romname):
        """Get control data for a ROM, based on current mode"""
        if self.use_fast_mode:
            # Fast mode - only check gamedata.json
            return self.get_game_data_from_gamedata_only(romname)
        else:
            # Normal mode - check all data sources with original algorithm
            return self.get_game_data_from_all_sources(romname)

    def get_game_data_from_all_sources(self, romname):
        """Get control data from controls.json and mame.xml only (no gamedata.json fallback)"""
        # Try direct match in controls.json
        game_data = next((game for game in self.controls_data if game['romname'] == romname), None)
        if game_data:
            return game_data.copy()
                
        # Try variant match by stripping region code
        base_name = re.sub(r'[jubew]$', '', romname)
        for game in self.controls_data:
            control_base = re.sub(r'[jubew]$', '', game['romname'])
            if base_name == control_base:
                # Copy the data and modify for this ROM
                variant_data = game.copy()
                variant_data['romname'] = romname
                variant_data['gamename'] = f"{game['gamename']} (Variant)"
                return variant_data
        
        # If we have mame.xml data, try to find parent/clone relationships
        if hasattr(self, 'mame_xml_data') and romname in self.mame_xml_data:
            # Check if this ROM is a clone of another ROM
            parent_rom = self.mame_xml_data[romname].get('cloneof')
            if parent_rom:
                # Try to find the parent ROM in controls.json
                parent_data = next((game for game in self.controls_data if game['romname'] == parent_rom), None)
                if parent_data:
                    # Copy the parent data and modify for this ROM
                    clone_data = parent_data.copy()
                    clone_data['romname'] = romname
                    clone_data['gamename'] = f"{self.mame_xml_data[romname]['name']} (Clone)"
                    return clone_data
            
            # Also check the romof relationship
            rom_of = self.mame_xml_data[romname].get('romof')
            if rom_of and rom_of != parent_rom:  # Avoid checking the same ROM twice
                # Try to find the source ROM in controls.json
                source_data = next((game for game in self.controls_data if game['romname'] == rom_of), None)
                if source_data:
                    # Copy the source data and modify for this ROM
                    derived_data = source_data.copy()
                    derived_data['romname'] = romname
                    derived_data['gamename'] = f"{self.mame_xml_data[romname]['name']} (Derived)"
                    return derived_data
        
        # No fallback to gamedata.json - just return None if not found
        return None

    def get_game_data_from_gamedata_only(self, romname):
        """Get control data only from gamedata.json"""
        if not hasattr(self, 'gamedata_json'):
            self.load_gamedata_json()
            
        if romname in self.gamedata_json:
            game_data = self.gamedata_json[romname]
            
            # Simple name defaults
            default_actions = {
                'P1_JOYSTICK_UP': 'Up',
                'P1_JOYSTICK_DOWN': 'Down',
                'P1_JOYSTICK_LEFT': 'Left',
                'P1_JOYSTICK_RIGHT': 'Right',
                'P2_JOYSTICK_UP': 'Up',
                'P2_JOYSTICK_DOWN': 'Down',
                'P2_JOYSTICK_LEFT': 'Left',
                'P2_JOYSTICK_RIGHT': 'Right',
                'P1_BUTTON1': 'A Button',
                'P1_BUTTON2': 'B Button',
                'P1_BUTTON3': 'X Button',
                'P1_BUTTON4': 'Y Button',
                'P1_BUTTON5': 'LB Button',
                'P1_BUTTON6': 'RB Button',
                # Mirror P1 button names for P2
                'P2_BUTTON1': 'A Button',
                'P2_BUTTON2': 'B Button',
                'P2_BUTTON3': 'X Button',
                'P2_BUTTON4': 'Y Button',
                'P2_BUTTON5': 'LB Button',
                'P2_BUTTON6': 'RB Button',
            }
            
            # Basic structure conversion - DEFINE THIS FIRST
            converted_data = {
                'romname': romname,
                'gamename': game_data.get('description', romname),
                'numPlayers': int(game_data.get('playercount', 1)),
                'alternating': game_data.get('alternating', False),
                'mirrored': False,
                'miscDetails': f"Buttons: {game_data.get('buttons', '?')}, Sticks: {game_data.get('sticks', '?')}",
                'players': []
            }
            
            # Find controls (direct or in a clone)
            controls = None
            if 'controls' in game_data:
                controls = game_data['controls']
            elif 'clones' in game_data:
                for clone in game_data['clones'].values():
                    if 'controls' in clone:
                        controls = clone['controls']
                        break
            
            if controls:
                # First pass - collect P1 button names to mirror to P2
                p1_button_names = {}
                for control_name, control_data in controls.items():
                    if control_name.startswith('P1_BUTTON') and 'name' in control_data:
                        button_num = control_name.replace('P1_BUTTON', '')
                        p1_button_names[f'P2_BUTTON{button_num}'] = control_data['name']
                        
                # Process player controls
                p1_controls = []
                p2_controls = []
                
                for control_name, control_data in controls.items():
                    # Add P1 controls
                    if control_name.startswith('P1_'):
                        # Skip non-joystick/button controls
                        if 'JOYSTICK' in control_name or 'BUTTON' in control_name:
                            # Get the friendly name
                            friendly_name = None
                            
                            # First check for explicit name
                            if 'name' in control_data:
                                friendly_name = control_data['name']
                            # Then check for default actions
                            elif control_name in default_actions:
                                friendly_name = default_actions[control_name]
                            # Fallback to control name
                            else:
                                parts = control_name.split('_')
                                if len(parts) > 1:
                                    friendly_name = parts[-1]
                                
                            if friendly_name:
                                p1_controls.append({
                                    'name': control_name,
                                    'value': friendly_name
                                })
                    
                    # Add P2 controls - prioritize matching P1 button names
                    elif control_name.startswith('P2_'):
                        if 'JOYSTICK' in control_name or 'BUTTON' in control_name:
                            friendly_name = None
                            
                            # First check for explicit name
                            if 'name' in control_data:
                                friendly_name = control_data['name']
                            # Then check if we have a matching P1 button name
                            elif control_name in p1_button_names:
                                friendly_name = p1_button_names[control_name]
                            # Then check defaults
                            elif control_name in default_actions:
                                friendly_name = default_actions[control_name]
                            # Fallback to control name
                            else:
                                parts = control_name.split('_')
                                if len(parts) > 1:
                                    friendly_name = parts[-1]
                                
                            if friendly_name:
                                p2_controls.append({
                                    'name': control_name,
                                    'value': friendly_name
                                })
                
                # Also check for special direction mappings (P1_UP, etc.)
                for control_name, control_data in controls.items():
                    if control_name == 'P1_UP' and 'name' in control_data:
                        # Update the joystick control if it exists
                        for control in p1_controls:
                            if control['name'] == 'P1_JOYSTICK_UP':
                                control['value'] = control_data['name']
                    elif control_name == 'P1_DOWN' and 'name' in control_data:
                        for control in p1_controls:
                            if control['name'] == 'P1_JOYSTICK_DOWN':
                                control['value'] = control_data['name']
                    elif control_name == 'P1_LEFT' and 'name' in control_data:
                        for control in p1_controls:
                            if control['name'] == 'P1_JOYSTICK_LEFT':
                                control['value'] = control_data['name']
                    elif control_name == 'P1_RIGHT' and 'name' in control_data:
                        for control in p1_controls:
                            if control['name'] == 'P1_JOYSTICK_RIGHT':
                                control['value'] = control_data['name']
                    # Also handle P2 directional controls the same way
                    elif control_name == 'P2_UP' and 'name' in control_data:
                        for control in p2_controls:
                            if control['name'] == 'P2_JOYSTICK_UP':
                                control['value'] = control_data['name']
                    elif control_name == 'P2_DOWN' and 'name' in control_data:
                        for control in p2_controls:
                            if control['name'] == 'P2_JOYSTICK_DOWN':
                                control['value'] = control_data['name']
                    elif control_name == 'P2_LEFT' and 'name' in control_data:
                        for control in p2_controls:
                            if control['name'] == 'P2_JOYSTICK_LEFT':
                                control['value'] = control_data['name']
                    elif control_name == 'P2_RIGHT' and 'name' in control_data:
                        for control in p2_controls:
                            if control['name'] == 'P2_JOYSTICK_RIGHT':
                                control['value'] = control_data['name']
                
                # Sort controls by name to ensure consistent order (Button 1 before Button 2)
                p1_controls.sort(key=lambda x: x['name'])
                p2_controls.sort(key=lambda x: x['name'])
                            
                # Add player 1 if we have controls
                if p1_controls:
                    converted_data['players'].append({
                        'number': 1,
                        'numButtons': int(game_data.get('buttons', 1)),
                        'labels': p1_controls
                    })

                # Add player 2 if we have controls
                if p2_controls:
                    converted_data['players'].append({
                        'number': 2,
                        'numButtons': int(game_data.get('buttons', 1)),
                        'labels': p2_controls
                    })
                
            # Mark as gamedata source
            converted_data['source'] = 'gamedata.json'
            return converted_data
        
        # Try clone lookup if direct lookup failed
        if hasattr(self, 'mame_xml_data') and romname in self.mame_xml_data:
            # See if it's a clone of another game
            parent_rom = self.mame_xml_data[romname].get('cloneof')
            if parent_rom and parent_rom in self.gamedata_json:
                # Recursive call to get parent data
                parent_data = self.get_game_data_from_gamedata_only(parent_rom)
                if parent_data:
                    # Update with this ROM's info
                    parent_data['romname'] = romname
                    parent_data['gamename'] = f"{self.mame_xml_data[romname]['name']} (Clone)"
                    return parent_data
        
        # Not found
        return None
        
    def scan_roms_directory(self):
        """Scan the roms directory for available games"""
        roms_dir = os.path.join(self.mame_dir, "roms")
        print(f"\nScanning ROMs directory: {roms_dir}")
        
        if not os.path.exists(roms_dir):
            print(f"ERROR: ROMs directory not found: {roms_dir}")
            return

        self.available_roms = set()  # Reset the set
        rom_count = 0

        for filename in os.listdir(roms_dir):
            # Strip common ROM extensions
            base_name = os.path.splitext(filename)[0]
            self.available_roms.add(base_name)
            rom_count += 1
            if rom_count <= 5:  # Print first 5 ROMs as sample
                print(f"Found ROM: {base_name}")
        
        print(f"Total ROMs found: {len(self.available_roms)}")
        if len(self.available_roms) > 0:
            print("Sample of available ROMs:", list(self.available_roms)[:5])
        else:
            print("WARNING: No ROMs were found!")

    def load_custom_configs(self):
        """Load custom configurations from cfg directory"""
        cfg_dir = os.path.join(self.mame_dir, "cfg")
        if not os.path.exists(cfg_dir):
            print(f"Config directory not found: {cfg_dir}")
            return

        for filename in os.listdir(cfg_dir):
            if filename.endswith(".cfg"):
                game_name = filename[:-4]
                full_path = os.path.join(cfg_dir, filename)
                try:
                    # Read as binary first to handle BOM
                    with open(full_path, "rb") as f:
                        content = f.read()
                    # Decode with UTF-8-SIG to handle BOM
                    self.custom_configs[game_name] = content.decode('utf-8-sig')
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

        print(f"Loaded {len(self.custom_configs)} custom configurations")

    def update_stats_label(self):
        """Update the statistics label"""
        # Show current mode
        if self.use_fast_mode:
            mode_text = "Fast Mode (gamedata.json only)"
        else:
            mode_text = "Normal Mode (controls.json + mame.xml only)"
        
        unmatched = len(self.find_unmatched_roms())
        matched = len(self.available_roms) - unmatched
        stats = (
            f"Mode: {mode_text}\n"
            f"Available ROMs: {len(self.available_roms)} ({matched} with controls, {unmatched} without)\n"
            f"Custom configs: {len(self.custom_configs)}"
        )
        self.stats_label.configure(text=stats)
    
    def find_unmatched_roms(self) -> Set[str]:
        """Find ROMs that don't have matching control data"""
        control_roms = {game['romname'] for game in self.controls_data}
        return self.available_roms - control_roms

    def load_mame_xml(self):
        """Load and parse the mame.xml file for ROM metadata including clones"""
        if hasattr(self, 'mame_xml_data'):
            # Already loaded
            return self.mame_xml_data
            
        self.mame_xml_data = {}
        
        # Look for mame.xml in common locations
        xml_paths = [
            os.path.join(self.mame_dir, "mame.xml"),
            os.path.join(self.mame_dir, "metadata", "mame.xml"),
            os.path.join(self.mame_dir, "hash", "mame.xml")
        ]
        
        xml_path = None
        for path in xml_paths:
            if os.path.exists(path):
                xml_path = path
                break
        
        if not xml_path:
            print("mame.xml not found")
            return {}
            
        try:
            print(f"Loading mame.xml from: {xml_path}")
            
            # Simplified approach without progress tracking
            # For large files, this might take a moment
            for event, elem in ET.iterparse(xml_path, events=('end',)):
                # Process both main entries and clones/variants
                if elem.tag == 'machine':
                    rom_name = elem.get('name')
                    if rom_name:
                        # Get description (game name)
                        description = elem.findtext('description')
                        
                        # Store the data if we have at least a name and description
                        if description:
                            # Also capture clone/romof relationships for reference
                            clone_of = elem.get('cloneof')
                            rom_of = elem.get('romof')
                            
                            self.mame_xml_data[rom_name] = {
                                'name': description,
                                'year': elem.findtext('year'),
                                'manufacturer': elem.findtext('manufacturer'),
                                'cloneof': clone_of,
                                'romof': rom_of
                            }
                    
                    # Clear element to save memory
                    elem.clear()
            
            print(f"Loaded {len(self.mame_xml_data)} games from mame.xml")
            return self.mame_xml_data
            
        except Exception as e:
            print(f"Error loading mame.xml: {str(e)}")
            import traceback
            traceback.print_exc()  # Print the full error traceback
            return {}
    
        # Add a helper method to look for game names from other sources
    def get_game_name_from_other_sources(self, rom_name):
        """Try to find a game name for unmatched ROMs from mame.xml or other sources"""
        # Check mame.xml data
        if not hasattr(self, 'mame_xml_data'):
            self.load_mame_xml()
        
        print(f"Looking for ROM name: {rom_name}")
        
        # Check directly for exact match
        if rom_name in self.mame_xml_data:
            print(f"Found exact match for {rom_name}: {self.mame_xml_data[rom_name]['name']}")
            return self.mame_xml_data[rom_name]['name']
        
        # Try alternative approaches for close matches
        for xml_rom, xml_data in self.mame_xml_data.items():
            # Check if this ROM is a direct parent or clone
            if xml_data.get('cloneof') == rom_name or xml_data.get('romof') == rom_name:
                print(f"Found as parent/source of {xml_rom}: {xml_data['name']}")
                return xml_data['name']
            
            # Check if ROM name is a substring with high confidence
            if (rom_name in xml_rom and len(rom_name) >= 3) or (xml_rom in rom_name and len(xml_rom) >= 3):
                # Make sure it's not just a coincidental short string match
                if abs(len(xml_rom) - len(rom_name)) <= 2:
                    print(f"Found close match: {rom_name} ≈ {xml_rom}: {xml_data['name']}")
                    return xml_data['name']
        
        print(f"No match found for {rom_name}")
        return None
    
    def show_unmatched_roms(self):
        """Display ROMs that don't have matching control data"""
        # Load mame.xml data if not already loaded
        if not hasattr(self, 'mame_xml_data'):
            self.load_mame_xml()
        
        # Categorize ROMs using the same get_game_data logic
        unmatched = []
        direct_matches = []
        variant_matches = []
        clone_matches = []  # New category for clone-derived matches

        for rom in sorted(self.available_roms):
            game_data = self.get_game_data(rom)
            if not game_data:
                unmatched.append(rom)
            else:
                # Check if it's a direct match
                if any(game['romname'] == rom for game in self.controls_data):
                    game_name = next((game['gamename'] for game in self.controls_data 
                                    if game['romname'] == rom), "Unknown")
                    direct_matches.append((rom, game_name))
                else:
                    # Check if it's a variant match (region code)
                    try:
                        base_name_matched = False
                        for game in self.controls_data:
                            if re.sub(r'[jubew]$', '', game['romname']) == re.sub(r'[jubew]$', '', rom):
                                variant_matches.append((rom, game['romname'], game['gamename']))
                                base_name_matched = True
                                break
                                
                        # If not a variant match, must be a clone/romof match
                        if not base_name_matched:
                            # Use the game_data's gamename which already has the (Clone) or (Derived) suffix
                            clone_matches.append((rom, game_data['gamename']))
                    except Exception as e:
                        print(f"Error processing {rom}: {str(e)}")
                        # Add to unmatched if there's an error during processing
                        unmatched.append(rom)

        # Get unmatched ROMs with names from mame.xml
        unmatched_with_names = []
        for rom in unmatched:
            game_name = self.get_game_name_from_other_sources(rom)
            if game_name:
                unmatched_with_names.append((rom, game_name))
            else:
                unmatched_with_names.append((rom, "Unknown"))

        # Create new window
        self.unmatched_dialog = ctk.CTkToplevel(self)
        self.unmatched_dialog.title("ROM Control Data Analysis")
        self.unmatched_dialog.geometry("800x600")
        
        # Make it modal
        self.unmatched_dialog.transient(self)
        self.unmatched_dialog.grab_set()
        
        # Create tabs
        tabview = ctk.CTkTabview(self.unmatched_dialog)
        tabview.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Summary tab
        summary_tab = tabview.add("Summary")
        stats_text = (
            f"Total ROMs: {len(self.available_roms)}\n"
            f"Direct matches: {len(direct_matches)}\n"
            f"Variant matches: {len(variant_matches)}\n"
            f"Clone/Parent matches: {len(clone_matches)}\n"
            f"Unmatched ROMs: {len(unmatched)}\n\n"
            f"Control data coverage: {((len(direct_matches) + len(variant_matches) + len(clone_matches)) / len(self.available_roms) * 100):.1f}%"
        )
        stats_label = ctk.CTkLabel(
            summary_tab,
            text=stats_text,
            font=("Arial", 14),
            justify="left"
        )
        stats_label.pack(padx=20, pady=20, anchor="w")
        
        # Unmatched ROMs tab
        unmatched_tab = tabview.add("Unmatched ROMs")
        if unmatched_with_names:
            unmatched_text = ctk.CTkTextbox(unmatched_tab)
            unmatched_text.pack(expand=True, fill="both", padx=10, pady=10)
            
            # Format each entry with ROM name and game name (if available)
            for rom, game_name in sorted(unmatched_with_names):
                if game_name != "Unknown":
                    unmatched_text.insert("end", f"{rom} - {game_name}\n")
                else:
                    unmatched_text.insert("end", f"{rom}\n")
                    
            unmatched_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                unmatched_tab,
                text="No unmatched ROMs found!",
                font=("Arial", 14)
            ).pack(expand=True)
        
        # Direct matches tab 
        direct_tab = tabview.add("Direct Matches")
        if direct_matches:
            direct_text = ctk.CTkTextbox(direct_tab)
            direct_text.pack(expand=True, fill="both", padx=10, pady=10)
            
            # Display both ROM name and game name for direct matches
            for rom, game_name in sorted(direct_matches):
                direct_text.insert("end", f"{rom} - {game_name}\n")
                
            direct_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                direct_tab,
                text="No direct matches found!",
                font=("Arial", 14)
            ).pack(expand=True)
            
        # Variant matches tab
        variants_tab = tabview.add("Variant Matches")
        if variant_matches:
            variants_text = ctk.CTkTextbox(variants_tab)
            variants_text.pack(expand=True, fill="both", padx=10, pady=10)
            for rom, control_rom, game_name in sorted(variant_matches):
                variants_text.insert("end", f"{rom} → {control_rom} - {game_name}\n")
            variants_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                variants_tab,
                text="No variant matches found!",
                font=("Arial", 14)
            ).pack(expand=True)
        
        # Clone matches tab (new)
        clones_tab = tabview.add("Clone Matches")
        if clone_matches:
            clones_text = ctk.CTkTextbox(clones_tab)
            clones_text.pack(expand=True, fill="both", padx=10, pady=10)
            for rom, game_name in sorted(clone_matches):
                clones_text.insert("end", f"{rom} - {game_name}\n")
            clones_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                clones_tab,
                text="No clone matches found!",
                font=("Arial", 14)
            ).pack(expand=True)
        
        # Select Summary tab by default
        tabview.set("Summary")
        
        # Add export button
        def export_analysis():
            try:
                file_path = os.path.join(self.mame_dir, "control_analysis.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("MAME Control Data Analysis\n")
                    f.write("=========================\n\n")
                    f.write(stats_text + "\n\n")
                    
                    f.write("Direct Matches:\n")
                    f.write("===============\n")
                    for rom, game_name in sorted(direct_matches):
                        f.write(f"{rom} - {game_name}\n")
                    f.write("\n")
                    
                    f.write("Variant Matches:\n")
                    f.write("===============\n")
                    for rom, control_rom, game_name in sorted(variant_matches):
                        f.write(f"{rom} → {control_rom} - {game_name}\n")
                    f.write("\n")
                    
                    f.write("Clone Matches:\n")
                    f.write("=============\n")
                    for rom, game_name in sorted(clone_matches):
                        f.write(f"{rom} - {game_name}\n")
                    f.write("\n")
                    
                    f.write("Unmatched ROMs:\n")
                    f.write("==============\n")
                    for rom, game_name in sorted(unmatched_with_names):
                        if game_name != "Unknown":
                            f.write(f"{rom} - {game_name}\n")
                        else:
                            f.write(f"{rom}\n")
                        
                messagebox.showinfo("Export Complete", 
                                f"Analysis exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
        
        export_button = ctk.CTkButton(
            self.unmatched_dialog,
            text="Export Analysis",
            command=export_analysis
        )
        export_button.pack(pady=10)
        
        # Add close button
        close_button = ctk.CTkButton(
            self.unmatched_dialog,
            text="Close",
            command=self.unmatched_dialog.destroy
        )
        close_button.pack(pady=10)
    
    def update_game_list(self):
        """Update the game list to show all available ROMs with visual enhancements"""
        self.game_list.delete("1.0", "end")
        
        # Sort available ROMs
        available_roms = sorted(self.available_roms)
        
        # Add alternating row backgrounds for better readability
        row_count = 0
        
        for romname in available_roms:
            # Get game data including variants
            game_data = self.get_game_data(romname)
            has_config = romname in self.custom_configs
            
            # Build the prefix
            prefix = "* " if has_config else "  "
            if game_data:
                prefix += "+ "
                display_name = f"{romname} - {game_data['gamename']}"
            else:
                prefix += "- "
                display_name = romname
            
            # Insert the line
            line_start = self.game_list.index("end-1c")
            self.game_list.insert("end", f"{prefix}{display_name}\n")
            
            # Apply alternate row background for better readability
            row_count += 1
            
        print(f"\nGame List Update:")
        print(f"Total ROMs: {len(available_roms)}")
        print(f"ROMs with control data: {sum(1 for rom in available_roms if self.get_game_data(rom))}")
        print(f"ROMs with configs: {len(self.custom_configs)}")

    def filter_games(self, *args):
        """Filter the game list based on search text"""
        search_text = self.search_var.get().lower()
        self.game_list.delete("1.0", "end")
        
        # Sort available ROMs
        available_roms = sorted(self.available_roms)
        
        # Reset the selected line when filtering
        self.selected_line = None
        
        # Add alternating row backgrounds for better readability
        row_count = 0
        
        for romname in available_roms:
            # Get game data including variants
            game_data = self.get_game_data(romname)
            
            # Check if ROM matches search
            if (search_text in romname.lower() or 
                (game_data and search_text in game_data['gamename'].lower())):
                
                has_config = romname in self.custom_configs
                
                # Build the prefix
                prefix = "* " if has_config else "  "
                if game_data:
                    prefix += "+ "
                    display_name = f"{romname} - {game_data['gamename']}"
                else:
                    prefix += "- "
                    display_name = romname
                
                # Insert the line
                line_start = self.game_list.index("end-1c")
                self.game_list.insert("end", f"{prefix}{display_name}\n")
                
                # Apply alternate row background for better readability
                row_count += 1

    def highlight_selected_game(self, line_index):
        """Highlight the selected game in the list"""
        # Clear previous highlight if any
        if self.selected_line is not None:
            self.game_list._textbox.tag_remove(self.highlight_tag, f"{self.selected_line}.0", f"{self.selected_line + 1}.0")
        
        # Apply new highlight
        self.selected_line = line_index
        self.game_list._textbox.tag_add(self.highlight_tag, f"{line_index}.0", f"{line_index + 1}.0")
        
        # Ensure the selected item is visible
        self.game_list.see(f"{line_index}.0")

    def parse_cfg_controls(self, cfg_content: str) -> Dict[str, str]:
        """Parse MAME cfg file to extract control mappings"""
        controls = {}
        try:
            import xml.etree.ElementTree as ET
            from io import StringIO
            
            # Parse the XML content
            parser = ET.XMLParser(encoding='utf-8')
            tree = ET.parse(StringIO(cfg_content), parser=parser)
            root = tree.getroot()
            
            # Find all port elements under input
            input_elem = root.find('.//input')
            if input_elem is not None:
                print("Found input element")
                for port in input_elem.findall('port'):
                    control_type = port.get('type')
                    if control_type and control_type.startswith('P') and ('BUTTON' in control_type or 'JOYSTICK' in control_type):
                        # Find the newseq element for the mapping
                        newseq = port.find('.//newseq')
                        if newseq is not None and newseq.text:
                            mapping = newseq.text.strip()
                            controls[control_type] = mapping
                            print(f"Found mapping: {control_type} -> {mapping}")
            else:
                print("No input element found in XML")
                
        except ET.ParseError as e:
            print(f"XML parsing failed with error: {str(e)}")
            print("First 100 chars of content:", repr(cfg_content[:100]))
        except Exception as e:
            print(f"Unexpected error parsing cfg: {str(e)}")
            
        print(f"Found {len(controls)} control mappings")
        if controls:
            print("Sample mappings:")
            for k, v in list(controls.items())[:3]:
                print(f"  {k}: {v}")
                
        return controls

    def load_default_config(self):
        """Load the default MAME control configuration"""
        # Look in the cfg directory
        cfg_dir = os.path.join(self.mame_dir, "cfg")
        default_cfg_path = os.path.join(cfg_dir, "default.cfg")
        
        print(f"Looking for default.cfg at: {default_cfg_path}")
        if os.path.exists(default_cfg_path):
            try:
                print(f"Loading default config from: {default_cfg_path}")
                # Read file content
                with open(default_cfg_path, "rb") as f:
                    content = f.read()
                
                # Parse the default mappings
                self.default_controls = self.parse_default_cfg(content.decode('utf-8-sig'))
                
                # Debug output
                print(f"Loaded {len(self.default_controls)} default control mappings")
                for i, (k, v) in enumerate(list(self.default_controls.items())[:5]):
                    print(f"  Sample {i+1}: {k} -> {v}")
                    
                return True
            except Exception as e:
                print(f"Error loading default config: {e}")
                import traceback
                traceback.print_exc()
                self.default_controls = {}
                return False
        else:
            print("No default.cfg found in cfg directory")
            self.default_controls = {}
            return False

    def parse_default_cfg(self, cfg_content):
        """Special parser just for default.cfg - extract ONLY joystick mappings"""
        controls = {}
        try:
            import xml.etree.ElementTree as ET
            from io import StringIO
            import re
            
            # Parse the XML content
            parser = ET.XMLParser(encoding='utf-8')
            tree = ET.parse(StringIO(cfg_content), parser)
            root = tree.getroot()
            
            # Find the input section
            input_elem = root.find('.//input')
            if input_elem is not None:
                print("Found input element in default.cfg")
                joycode_count = 0
                for port in input_elem.findall('port'):
                    control_type = port.get('type')
                    if control_type:
                        # Find the standard sequence
                        newseq = port.find('./newseq[@type="standard"]')
                        if newseq is not None and newseq.text:
                            full_mapping = newseq.text.strip()
                            
                            # Extract only JOYCODE parts using regex
                            joycode_match = re.search(r'(JOYCODE_\d+_[A-Z0-9_]+)', full_mapping)
                            if joycode_match:
                                joycode = joycode_match.group(1)
                                controls[control_type] = joycode
                                joycode_count += 1
            
            print(f"Parsed {len(controls)} joystick controls from default.cfg (found {joycode_count} JOYCODE entries)")
        except Exception as e:
            print(f"Error parsing default.cfg: {e}")
            import traceback
            traceback.print_exc()
        
        return controls

    def compare_controls(self, game_data: Dict, cfg_controls: Dict) -> List[Tuple[str, str, str, bool]]:
        """Compare controls with game-specific and default mappings"""
        comparisons = []
        
        # Debug output
        has_defaults = hasattr(self, 'default_controls') and self.default_controls
        print(f"Compare controls: ROM={game_data['romname']}, " 
            f"Custom CFG={len(cfg_controls)}, "
            f"Default Controls Available={has_defaults and len(self.default_controls)}, "
            f"XInput={self.use_xinput}")
        
        # Convert default controls to XInput if needed
        default_controls = {}
        if has_defaults:
            for control, mapping in self.default_controls.items():
                if self.use_xinput:
                    default_controls[control] = self.convert_mapping(mapping, True)
                else:
                    default_controls[control] = mapping
        
        # Get default controls from game data
        for player in game_data.get('players', []):
            player_num = player['number']
            for label in player.get('labels', []):
                control_name = label['name']
                default_label = label['value']
                
                # Game-specific cfg has highest priority
                if control_name in cfg_controls:
                    current_mapping = cfg_controls[control_name]
                    is_different = True  # Custom mapping
                # Default.cfg has second priority - already converted to XInput if needed
                elif control_name in default_controls:
                    current_mapping = default_controls[control_name]
                    is_different = False  # Default mapping from default.cfg
                else:
                    current_mapping = "Not mapped"
                    is_different = False
                    
                comparisons.append((control_name, default_label, current_mapping, is_different))
        
        # Debug - print a few samples
        if comparisons:
            print(f"Generated {len(comparisons)} control comparisons. Samples:")
            for i, (name, label, mapping, diff) in enumerate(comparisons[:3]):
                src = "Custom" if diff else ("Default" if mapping != "Not mapped" else "None")
                print(f"  {name}: {label} -> {mapping} ({src})")
        
        return comparisons

    def on_game_select(self, event):
        """Handle game selection and display controls"""
        try:
            # Get the selected game name
            index = self.game_list.index(f"@{event.x},{event.y}")
            
            # Get the line number (starting from 1)
            line_num = int(index.split('.')[0])
            
            # Get the text from this line
            line = self.game_list.get(f"{line_num}.0", f"{line_num}.0 lineend")
            
            # Highlight the selected line
            self.highlight_selected_game(line_num)
            
            # Remove prefix indicators
            if line.startswith("* "):
                line = line[2:]
            if line.startswith("+ ") or line.startswith("- "):
                line = line[2:]
                
            romname = line.split(" - ")[0]
            self.current_game = romname

            # Get game data including variants
            game_data = self.get_game_data(romname)
            
            # Clear existing display
            for widget in self.control_frame.winfo_children():
                widget.destroy()

            if not game_data:
                # Clear display for ROMs without control data
                self.game_title.configure(text=f"No control data: {romname}")
                return

            # Update game title
            self.game_title.configure(text=game_data['gamename'])

            # Configure columns for the controls table
            self.control_frame.grid_columnconfigure(0, weight=2)  # Control name
            self.control_frame.grid_columnconfigure(1, weight=2)  # Default action
            self.control_frame.grid_columnconfigure(2, weight=3)  # Current mapping

            row = 0

            # Basic game info - using a frame for better organization
            info_frame = ctk.CTkFrame(self.control_frame)
            info_frame.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
            info_frame.grid_columnconfigure(0, weight=1)

            # Game info with larger font and better spacing
            info_text = (
                f"ROM: {game_data['romname']}\n\n"
                f"Players: {game_data['numPlayers']}\n"
                f"Alternating: {game_data['alternating']}\n"
                f"Mirrored: {game_data['mirrored']}"
            )
            if game_data.get('miscDetails'):
                info_text += f"\n\nDetails: {game_data['miscDetails']}"

            info_label = ctk.CTkLabel(
                info_frame, 
                text=info_text,
                font=("Arial", 14),
                justify="left",
                anchor="w",
                wraplength=800
            )
            info_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            row += 1

            # Get custom controls if they exist
            cfg_controls = {}
            if romname in self.custom_configs:
                cfg_controls = self.parse_cfg_controls(self.custom_configs[romname])
                
                # Convert mappings if XInput is enabled
                if self.use_xinput:
                    cfg_controls = {
                        control: self.convert_mapping(mapping, True)
                        for control, mapping in cfg_controls.items()
                    }

            # Column headers with consistent styling
            headers = ["Control", "Default Action", "Current Mapping"]
            header_frame = ctk.CTkFrame(self.control_frame)
            header_frame.grid(row=row, column=0, columnspan=3, padx=5, pady=(20,5), sticky="ew")
            
            for col, header in enumerate(headers):
                header_frame.grid_columnconfigure(col, weight=[2,2,3][col])
                header_label = ctk.CTkLabel(
                    header_frame,
                    text=header,
                    font=("Arial", 14, "bold")
                )
                header_label.grid(row=0, column=col, padx=5, pady=5, sticky="ew")
            row += 1

            # Create a frame for the controls list
            controls_frame = ctk.CTkFrame(self.control_frame)
            controls_frame.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
            for col in range(3):
                controls_frame.grid_columnconfigure(col, weight=[2,2,3][col])
            
            # Display control comparisons
            comparisons = self.compare_controls(game_data, cfg_controls)
            control_row = 0
            for control_name, default_label, current_mapping, is_different in comparisons:
                # Control name - now with formatting
                display_control = self.format_control_name(control_name)
                name_label = ctk.CTkLabel(
                    controls_frame,
                    text=display_control,
                    font=("Arial", 12)
                )
                name_label.grid(row=control_row, column=0, padx=5, pady=2, sticky="w")
                
                # Default action
                default_label = ctk.CTkLabel(
                    controls_frame,
                    text=default_label,
                    font=("Arial", 12)
                )
                default_label.grid(row=control_row, column=1, padx=5, pady=2, sticky="w")
                
                # Current mapping
                display_mapping = self.format_mapping_display(current_mapping)
                
                mapping_label = ctk.CTkLabel(
                    controls_frame,
                    text=display_mapping,
                    text_color="yellow" if is_different else None,
                    font=("Arial", 12)
                )
                mapping_label.grid(row=control_row, column=2, padx=5, pady=2, sticky="w")
                
                control_row += 1
            row += 1

            # Display raw custom config if it exists
            if romname in self.custom_configs:
                custom_header = ctk.CTkLabel(
                    self.control_frame,
                    text="RAW CONFIGURATION FILE",
                    font=("Arial", 16, "bold")
                )
                custom_header.grid(row=row, column=0, columnspan=3,
                                padx=5, pady=(20,5), sticky="w")
                row += 1

                custom_text = ctk.CTkTextbox(
                    self.control_frame,
                    height=200,
                    width=200  # The frame will expand this
                )
                custom_text.grid(row=row, column=0, columnspan=3,
                            padx=20, pady=5, sticky="ew")
                custom_text.insert("1.0", self.custom_configs[romname])
                custom_text.configure(state="disabled")

        except Exception as e:
            print(f"Error displaying game: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def create_info_directory(self):
        """Create info directory if it doesn't exist"""
        info_dir = os.path.join(os.path.dirname(__file__), "info")
        if not os.path.exists(info_dir):
            os.makedirs(info_dir)
        return info_dir

    def load_default_template(self):
        """Load the default.conf template"""
        template_path = os.path.join(os.path.dirname(__file__), "info", "default.conf")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading template: {e}")
            return None
    
    def generate_game_config(self, game_data: dict) -> str:
        """Generate config file content for a specific game"""
        template = self.load_default_template()
        if not template:
            return None
            
        # Split template into lines while preserving exact spacing
        template_lines = template.splitlines()
        output_lines = []
        
        # Get the position of the = sign from the template to maintain alignment
        equals_positions = []
        for line in template_lines:
            if '=' in line:
                pos = line.find('=')
                equals_positions.append(pos)
        
        # Get the maximum position to align all equals signs
        max_equals_pos = max(equals_positions) if equals_positions else 0
        
        # Process each line
        for line in template_lines:
            if '=' in line:
                # Split at equals but preserve original spacing
                field_part = line[:line.find('=')].rstrip()
                default_value = line[line.find('=')+1:].strip()
                
                # If it's a tooltip field (ends with 't')
                if field_part.strip().endswith('t'):
                    action_found = False
                    
                    # Look through game controls for a matching action
                    for player in game_data.get('players', []):
                        for label in player.get('labels', []):
                            control_name = label['name']
                            action = label['value']
                            
                            # Map control to config field
                            config_field, _ = self.map_control_to_xinput_config(control_name)
                            
                            if config_field == field_part.strip():
                                # Add the line with proper alignment and the action
                                padding = ' ' * (max_equals_pos - len(field_part))
                                output_lines.append(f"{field_part}{padding}= {action}")
                                action_found = True
                                break
                                
                    if not action_found:
                        # Keep original line with exact spacing
                        output_lines.append(line)
                else:
                    # For non-tooltip fields, keep the original line exactly
                    output_lines.append(line)
            else:
                # For lines without '=', keep them exactly as is
                output_lines.append(line)
        
        return '\n'.join(output_lines)

    def save_game_config(self, romname: str):
        """Save config file for a specific game"""
        # Get game data
        game_data = next((game for game in self.controls_data if game['romname'] == romname), None)
        if not game_data:
            return
            
        # Generate config content
        config_content = self.generate_game_config(game_data)
        if not config_content:
            return
            
        # Save to file
        info_dir = self.create_info_directory()
        config_path = os.path.join(info_dir, f"{romname}.conf")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print(f"Saved config for {romname}")
        except Exception as e:
            print(f"Error saving config for {romname}: {e}")

    def generate_all_configs(self):
        """Generate config files for all available ROMs from any data source"""
        info_dir = self.create_info_directory()
        print(f"Created/Found info directory at: {info_dir}")
        
        # First verify we have the template
        template = self.load_default_template()
        if not template:
            messagebox.showerror("Error", "Could not find default.conf template in info directory!")
            return
        print("Successfully loaded template")
        
        count = 0
        errors = []
        skipped = 0
        
        # Process all ROMs with control data, regardless of source
        roms_to_process = []
        
        # If in normal mode, use controls_data
        if not self.use_fast_mode and self.controls_data:
            # Get available ROMs with control data from controls.json
            for game in self.controls_data:
                if game['romname'] in self.available_roms:
                    roms_to_process.append(game['romname'])
        # If in fast mode or as a fallback, process all available ROMs
        else:
            # We'll check each ROM individually
            roms_to_process = list(self.available_roms)
        
        total_roms = len(roms_to_process)
        print(f"Found {total_roms} ROMs to process")
        
        # Process each ROM
        for rom_name in roms_to_process:
            try:
                # Get game data from appropriate source
                game_data = self.get_game_data(rom_name)
                
                if game_data:
                    config_content = self.generate_game_config(game_data)
                    if config_content:
                        config_path = os.path.join(info_dir, f"{rom_name}.conf")
                        with open(config_path, 'w', encoding='utf-8') as f:
                            f.write(config_content)
                        count += 1
                        if count % 50 == 0:  # Progress update every 50 files
                            print(f"Generated {count}/{total_roms} config files...")
                    else:
                        print(f"Skipping {rom_name}: No config content generated")
                        skipped += 1
                else:
                    print(f"Skipping {rom_name}: No control data found")
                    skipped += 1
            except Exception as e:
                error_msg = f"Error with {rom_name}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        # Final report
        report = f"Generated {count} config files in {info_dir}\n"
        report += f"Skipped {skipped} ROMs\n"
        if errors:
            report += f"\nEncountered {len(errors)} errors:\n"
            report += "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                report += f"\n...and {len(errors) - 5} more errors"
        
        print(report)
        messagebox.showinfo("Config Generation Report", report)

    # Add these methods to your class to enable text alignment

    def add_alignment_guides(self):
        """Add horizontal and vertical alignment guides to the canvas"""
        # Create guide lines (initially hidden)
        self.h_guide = self.preview_canvas.create_line(0, 0, 0, 0, fill="yellow", width=1, dash=(4, 4), state="hidden")
        self.v_guide = self.preview_canvas.create_line(0, 0, 0, 0, fill="yellow", width=1, dash=(4, 4), state="hidden")
        
        # Create snap points for each text item (invisible - just for snapping)
        self.snap_points = {}
        for control_name, data in self.text_items.items():
            text_x, text_y = data['x'], data['y']
            self.snap_points[control_name] = (text_x, text_y)
        
        # Track which item is being dragged
        self.dragged_item = None
        
        # Update draggable method to use guides
        self.update_draggable_for_alignment()
        
        # Add a button to toggle alignment guides (using the bottom row)
        self.alignment_button = ctk.CTkButton(
            self.button_row2,  # Use bottom row frame
            text="Alignment",
            command=self.toggle_alignment_mode,
            width=90  # Match other buttons
        )
        self.alignment_button.pack(side="left", padx=3)
        
        # Set initial alignment mode
        self.alignment_mode = False
        
        print("Alignment guides added")

    def update_draggable_for_alignment(self):
        """Update the drag handlers to use alignment guides"""
        # Store original drag motion method
        self.original_drag_motion = self.preview_canvas.tag_bind

        # Unbind existing motion handlers for all text items
        for control_name, data in self.text_items.items():
            self.preview_canvas.tag_unbind(data['text'], "<B1-Motion>")
            
            # Rebind with alignment-aware version
            self.preview_canvas.tag_bind(data['text'], "<B1-Motion>", 
                                lambda e, name=control_name: self.on_drag_with_alignment(e, name))
            
            # Add binding to start drag
            self.preview_canvas.tag_bind(data['text'], "<ButtonPress-1>", 
                                lambda e, name=control_name: self.on_drag_start_with_alignment(e, name))
            
            # Add binding to end drag
            self.preview_canvas.tag_bind(data['text'], "<ButtonRelease-1>", 
                                lambda e, name=control_name: self.on_drag_end_with_alignment(e, name))

    def on_drag_start_with_alignment(self, event, control_name):
        """Start dragging with alignment guides"""
        # Store which item is being dragged
        self.dragged_item = control_name
        
        # Store initial position
        self.drag_start_x = self.preview_canvas.canvasx(event.x)
        self.drag_start_y = self.preview_canvas.canvasy(event.y)
        
        # If alignment mode is on, show guides
        if self.alignment_mode:
            # Position guides at current item position
            text_x, text_y = self.text_items[control_name]['x'], self.text_items[control_name]['y']
            
            # Set guide lines to span the canvas
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            self.preview_canvas.coords(self.h_guide, 0, text_y, canvas_width, text_y)
            self.preview_canvas.coords(self.v_guide, text_x, 0, text_x, canvas_height)
            
            # Show guides
            self.preview_canvas.itemconfigure(self.h_guide, state="normal")
            self.preview_canvas.itemconfigure(self.v_guide, state="normal")

    def on_drag_with_alignment(self, event, control_name):
        """Handle dragging with alignment guides"""
        if not control_name == self.dragged_item:
            return
        
        # Calculate movement
        new_x = self.preview_canvas.canvasx(event.x)
        new_y = self.preview_canvas.canvasy(event.y)
        
        dx = new_x - self.drag_start_x
        dy = new_y - self.drag_start_y
        
        # Update start position
        self.drag_start_x = new_x
        self.drag_start_y = new_y
        
        # Get current position
        data = self.text_items[control_name]
        old_x, old_y = data['x'], data['y']
        new_x, new_y = old_x + dx, old_y + dy
        
        # Check for snapping if alignment mode is on
        if self.alignment_mode:
            # Snap threshold in pixels
            threshold = 10
            
            # Check for snapping to other items
            snap_x, snap_y = None, None
            for name, (x, y) in self.snap_points.items():
                if name == control_name:
                    continue
                    
                # Check horizontal alignment
                if abs(new_y - y) < threshold:
                    snap_y = y
                    
                # Check vertical alignment
                if abs(new_x - x) < threshold:
                    snap_x = x
            
            # Apply snapping
            if snap_y is not None:
                new_y = snap_y
                # Update horizontal guide
                canvas_width = self.preview_canvas.winfo_width()
                self.preview_canvas.coords(self.h_guide, 0, snap_y, canvas_width, snap_y)
                
            if snap_x is not None:
                new_x = snap_x
                # Update vertical guide
                canvas_height = self.preview_canvas.winfo_height()
                self.preview_canvas.coords(self.v_guide, snap_x, 0, snap_x, canvas_height)
        
        # Move the text and shadow
        self.preview_canvas.move(data['text'], new_x - old_x, new_y - old_y)
        self.preview_canvas.move(data['shadow'], new_x - old_x, new_y - old_y)
        
        # Update stored coordinates
        data['x'] = new_x
        data['y'] = new_y
        
        # Update snap points
        self.snap_points[control_name] = (new_x, new_y)
        
        # Update guides
        if self.alignment_mode:
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            self.preview_canvas.coords(self.h_guide, 0, new_y, canvas_width, new_y)
            self.preview_canvas.coords(self.v_guide, new_x, 0, new_x, canvas_height)

    def on_drag_end_with_alignment(self, event, control_name):
        """End dragging with alignment guides"""
        if not control_name == self.dragged_item:
            return
            
        # Hide guides
        self.preview_canvas.itemconfigure(self.h_guide, state="hidden")
        self.preview_canvas.itemconfigure(self.v_guide, state="hidden")
        
        # Clear dragged item
        self.dragged_item = None

    def toggle_alignment_mode(self):
        """Toggle alignment mode on/off"""
        self.alignment_mode = not self.alignment_mode
        if self.alignment_mode:
            self.alignment_button.configure(text="Alignment ON")
        else:
            self.alignment_button.configure(text="Alignment OFF")
            # Hide guides
            self.preview_canvas.itemconfigure(self.h_guide, state="hidden")
            self.preview_canvas.itemconfigure(self.v_guide, state="hidden")
    
    # Add these methods to implement the "Show All Buttons" feature

    def add_show_all_buttons_feature(self):
        """Add button and functionality to show all possible controls"""
        # Add button to the button frame (using the bottom row)
        self.show_all_button = ctk.CTkButton(
            self.button_row2,  # Use bottom row
            text="Show All",
            command=self.toggle_show_all_controls,
            width=90  # Match other buttons
        )
        self.show_all_button.pack(side="left", padx=3)
        
        # Initialize flag
        self.showing_all_controls = False
        
        # Store original controls when showing all
        self.original_text_items = None
        
        print("Show All Buttons feature added")

    def toggle_show_all_controls(self):
        """Toggle between showing all possible controls and just the game controls"""
        if not self.showing_all_controls:
            # Switch to showing all controls
            self.show_all_possible_controls()
            self.show_all_button.configure(text="Game Only")
            self.showing_all_controls = True
        else:
            # Switch back to game-specific controls
            self.restore_game_controls()
            self.show_all_button.configure(text="Show All")
            self.showing_all_controls = False

    def show_all_possible_controls(self):
        """Show all possible controls for positioning"""
        # Store current controls to restore later
        self.original_text_items = self.text_items.copy()
        
        # Clear existing controls
        for data in self.text_items.values():
            self.preview_canvas.delete(data['text'])
            self.preview_canvas.delete(data['shadow'])
        
        # Define all standard controls
        standard_controls = {
            # Directional controls
            "P1_JOYSTICK_UP": "Up",
            "P1_JOYSTICK_DOWN": "Down",
            "P1_JOYSTICK_LEFT": "Left",
            "P1_JOYSTICK_RIGHT": "Right",
            
            # Buttons 1-10
            "P1_BUTTON1": "A Button",
            "P1_BUTTON2": "B Button",
            "P1_BUTTON3": "X Button",
            "P1_BUTTON4": "Y Button",
            "P1_BUTTON5": "L Button",
            "P1_BUTTON6": "R Button",
            "P1_BUTTON7": "L2 Button",
            "P1_BUTTON8": "R2 Button",
            "P1_BUTTON9": "Select",
            "P1_BUTTON10": "Start",
            
            # Additional controls for completeness
            "P1_COIN": "Insert Coin",
            "P1_START": "1P Start",
        }
        
        # Create new text items dictionary
        self.text_items = {}
        
        # Get image dimensions for positioning
        image_x = self.image_x
        image_y = self.image_y
        
        # Calculate image size safely
        canvas_bbox = self.preview_canvas.bbox(self.preview_canvas.find_withtag("all"))
        if canvas_bbox:
            image_width = canvas_bbox[2] - image_x
            image_height = canvas_bbox[3] - image_y
        else:
            # Use canvas size as fallback
            image_width = self.preview_canvas.winfo_width()
            image_height = self.preview_canvas.winfo_height()
        
        # Load any saved positions
        positions = self.load_text_positions("all_controls")
        if not positions and os.path.exists(os.path.join(self.mame_dir, "preview", "global_positions.json")):
            # Fall back to global positions if all_controls doesn't exist
            positions = self.load_text_positions("global")
        
        # Add all controls as text
        control_count = 0
        for control_name, action in standard_controls.items():
            # Position text (use saved positions if available, otherwise use a grid layout)
            if control_name in positions:
                text_x, text_y = positions[control_name]
            else:
                # Arrange in a grid: 4 columns
                column = control_count % 4
                row = control_count // 4
                
                # Calculate position
                text_x = image_x + 100 + (column * 150)
                text_y = image_y + 50 + (row * 50)
                
            # Check visibility based on control type
            is_visible = True  # Always visible in "show all" mode
            
            # Create text with shadow for better visibility
            shadow = self.preview_canvas.create_text(text_x+2, text_y+2, text=action, 
                                        font=("Arial", 20, "bold"), fill="black",
                                        anchor="sw", state="" if is_visible else "hidden")
            text_item = self.preview_canvas.create_text(text_x, text_y, text=action, 
                                        font=("Arial", 20, "bold"), fill="white",
                                        anchor="sw", state="" if is_visible else "hidden")
            
            # Store the text items
            self.text_items[control_name] = {
                'text': text_item,
                'shadow': shadow,
                'action': action,
                'x': text_x, 
                'y': text_y
            }
            
            # Make the text draggable
            self.make_draggable(self.preview_canvas, text_item, shadow, control_name)
            control_count += 1
        
        # Update snap points for alignment
        self.snap_points = {}
        for control_name, data in self.text_items.items():
            self.snap_points[control_name] = (data['x'], data['y'])
        
        # Re-apply the alignment drag handlers
        self.update_draggable_for_alignment()
        
        # Update alignment mode if it's active
        if hasattr(self, 'alignment_mode') and self.alignment_mode:
            # Force update of alignment button text
            self.alignment_button.configure(text="Align ON")
        
        print(f"Showing all {len(self.text_items)} standard controls")

    def restore_game_controls(self):
        """Restore the game-specific controls"""
        if not self.original_text_items:
            print("No original controls to restore")
            return
        
        # Remove all current controls
        for data in self.text_items.values():
            self.preview_canvas.delete(data['text'])
            self.preview_canvas.delete(data['shadow'])
        
        # Restore original controls
        self.text_items = self.original_text_items
        self.original_text_items = None
        
        # Update alignment snap points
        self.snap_points = {}
        for control_name, data in self.text_items.items():
            self.snap_points[control_name] = (data['x'], data['y'])

        # Re-apply the alignment drag handlers
        self.update_draggable_for_alignment()

        print(f"Restored {len(self.text_items)} game-specific controls")

        # Important: Recreate the text items on the canvas
        for control_name, data in self.text_items.items():
            # Extract coordinates and text
            text_x, text_y = data['x'], data['y']
            action = data['action']
            
            # Check visibility based on control type
            is_visible = False
            for control_type in self.visible_control_types:
                if control_type in control_name:
                    is_visible = True
                    break
            
            # Create text with shadow for better visibility
            shadow = self.preview_canvas.create_text(text_x+2, text_y+2, text=action, 
                                    font=("Arial", 20, "bold"), fill="black",
                                    anchor="sw", state="" if is_visible else "hidden")
            text_item = self.preview_canvas.create_text(text_x, text_y, text=action, 
                                    font=("Arial", 20, "bold"), fill="white",
                                    anchor="sw", state="" if is_visible else "hidden")
            
            # Update the data with new canvas items
            data['text'] = text_item
            data['shadow'] = shadow
            
            # Make the text draggable
            self.make_draggable(self.preview_canvas, text_item, shadow, control_name)
        
        # Clear the original reference
        self.original_text_items = None
        
        # Update alignment guides if that feature is enabled
        if hasattr(self, 'update_draggable_for_alignment'):
            self.update_draggable_for_alignment()
            
        # Update snap points for alignment
        if hasattr(self, 'snap_points'):
            self.snap_points = {}
            for control_name, data in self.text_items.items():
                self.snap_points[control_name] = (data['x'], data['y'])
        
        print(f"Restored {len(self.text_items)} game-specific controls")

    def save_all_controls_positions(self):
        """Save positions for all standard controls"""
        try:
            # Get all current positions
            positions = {}
            for name, data in self.text_items.items():
                if 'x' not in data or 'y' not in data:
                    print(f"  Warning: Missing x/y for {name}")
                    continue
                    
                x, y = data['x'], data['y']
                positions[name] = [x, y]  # Use lists instead of tuples
                
            if not positions:
                print("  Warning: No positions to save!")
                messagebox.showinfo("Error", "No valid positions found to save")
                return False
                
            # Create preview directory if it doesn't exist
            preview_dir = os.path.join(self.mame_dir, "preview")
            os.makedirs(preview_dir, exist_ok=True)
            
            # Save to special file
            filepath = os.path.join(preview_dir, "all_controls_positions.json")
            
            with open(filepath, 'w') as f:
                json.dump(positions, f)
                
            print(f"Saved {len(positions)} positions for all controls to: {filepath}")
            messagebox.showinfo("Success", f"All controls positions saved ({len(positions)} items)")
            return True
        except Exception as e:
            print(f"Error saving all controls positions: {e}")
            messagebox.showerror("Error", f"Could not save positions: {e}")
            return False
    
    def show_preview_standalone(self, rom_name, auto_close=False):
        """Show the preview for a specific ROM without running the main app"""
        print(f"Starting standalone preview for ROM: {rom_name}")
        
        # Set fast mode explicitly for preview-only mode
        self.use_fast_mode = True
        
        # Update related flags for consistency
        self.use_controls_json = False
        self.use_gamedata_json = True
        self.use_mame_xml = False
        
        # Find the MAME directory (already in __init__)
        if not hasattr(self, 'mame_dir') or not self.mame_dir:
            self.mame_dir = self.find_mame_directory()
            if not self.mame_dir:
                print("Error: MAME directory not found!")
                return
        
        # Minimal data loading required for preview
        # We need these for the preview to work
        if not hasattr(self, 'default_controls') or not self.default_controls:
            self.load_default_config()
        
        # Scan ROMs directory if needed
        if not self.available_roms:
            self.scan_roms_directory()
        
        # Load control data for fast mode
        if not self.controls_data:
            self.load_gamedata_json()
        
        # Set the current game
        self.current_game = rom_name
        
        # Load game data
        game_data = self.get_game_data(rom_name)
        if not game_data:
            print(f"Error: No control data found for {rom_name}")
            return
        
        # Start MAME process monitoring only if auto_close is enabled
        if auto_close:
            print("Auto-close enabled - preview will close when MAME exits")
            self.monitor_mame_process(check_interval=0.5)
        else:
            print("Auto-close disabled - preview will stay open until manually closed")
        
        # Show the preview window
        self.show_preview()
        
        # Start mainloop for just this window
        self.mainloop()
        
    def quit_application(self):
        """Properly exit the application when preview window is closed"""
        if hasattr(self, 'preview_window'):
            self.preview_window.destroy()
        self.quit()
        self.destroy()
        import sys
        sys.exit(0)  # Force exit the Python script

    def monitor_mame_process(self, check_interval=2.0):
        """Monitor MAME process and close preview when MAME closes"""
        import threading
        import time
        import subprocess
        import sys
        import os
        
        def check_mame():
            mame_running = True
            while mame_running:
                time.sleep(check_interval)  # Use the specified check interval
                
                # Check if any MAME process is running
                mame_running = False
                try:
                    # Different ways to detect MAME
                    if sys.platform == 'win32':
                        # Windows - check process list
                        output = subprocess.check_output('tasklist /FI "IMAGENAME eq mame*"', shell=True)
                        mame_running = b'mame' in output
                    else:
                        # Linux/Mac - use ps
                        output = subprocess.check_output(['ps', 'aux'])
                        mame_running = b'mame' in output
                except:
                    # Error checking processes, assume MAME still running
                    mame_running = True
                
            # MAME is no longer running - close preview
            print("MAME closed, shutting down preview")
            if hasattr(self, 'preview_window') and self.preview_window:
                self.preview_window.after(100, self.quit_application)
        
        # Start monitoring in a background thread
        monitor_thread = threading.Thread(target=check_mame, daemon=True)
        monitor_thread.start()
    
if __name__ == "__main__":
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='MAME Control Configuration')
    parser.add_argument('--preview-only', action='store_true', help='Show only the preview window')
    parser.add_argument('--game', type=str, help='Specify the ROM name to preview')
    parser.add_argument('--screen', type=int, default=2, help='Screen number to display preview on (default: 2)')
    parser.add_argument('--auto-close', action='store_true', help='Automatically close preview when MAME exits')
    args = parser.parse_args()
    
    if args.preview_only and args.game:
        # Preview-only mode: just show the preview for the specified game
        app = MAMEControlConfig(preview_only=True)
        app.preferred_preview_screen = args.screen
        app.hide_preview_buttons = True  # Always hide buttons in preview-only mode
        app.show_preview_standalone(args.game, auto_close=args.auto_close)
    else:
        # Normal mode: start the full application
        app = MAMEControlConfig()
        app.mainloop()
