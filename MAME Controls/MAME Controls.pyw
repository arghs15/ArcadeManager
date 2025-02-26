import customtkinter as ctk
import json
import os
import re
from tkinter import messagebox
from typing import Dict, Optional, Set, List, Tuple
import xml.etree.ElementTree as ET

class MAMEControlConfig(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure the window
        self.title("MAME Control Configuration Checker")
        self.geometry("1024x768")
        self.fullscreen = True  # Track fullscreen state
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Bind F11 key for fullscreen toggle
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        
        # Single flag for mode - KEEP THIS
        self.use_fast_mode = False
        
        # For backwards compatibility with existing code - KEEP THESE TOO
        self.use_controls_json = True
        self.use_gamedata_json = True 
        self.use_mame_xml = True
        
        # Set initial fullscreen state
        self.after(100, self.state, 'zoomed')  # Use zoomed for Windows

        # Initialize data structures
        self.controls_data = []  # Changed to list for games array
        self.available_roms = set()
        self.custom_configs = {}
        self.current_game = None
        self.use_xinput = True
        self.selected_line = None
        self.highlight_tag = "highlight"
        
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
                    
                # Load the single flag
                self.use_fast_mode = settings.get("use_fast_mode", False)
                
                # Also load the backward compatibility flags
                self.use_controls_json = settings.get("use_controls_json", True)
                self.use_gamedata_json = settings.get("use_gamedata_json", True)
                self.use_mame_xml = settings.get("use_mame_xml", True)
                
                # Update toggle state
                if hasattr(self, 'fast_mode_toggle'):
                    if self.use_fast_mode:
                        self.fast_mode_toggle.select()
                    else:
                        self.fast_mode_toggle.deselect()
                        
            except Exception as e:
                print(f"Error loading settings: {e}")

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
        if "XINPUT" in mapping:
            # Convert XINPUT_1_A to "XInput A"
            parts = mapping.split('_')
            if len(parts) >= 3:
                button_part = ' '.join(parts[2:])
                return f"XInput {button_part}"
        elif "JOYCODE" in mapping:
            # Convert JOYCODE_1_BUTTON3 to "Joy 1 Button 3"
            parts = mapping.split('_')
            if len(parts) >= 4:
                joy_num = parts[1]
                button_type = parts[2].capitalize()
                button_num = parts[3]
                return f"Joy {joy_num} {button_type} {button_num}"
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
            
            # Refresh the display using the current selection
            self.on_game_select(mock_event)
            
            # Restore scroll position
            self.control_frame._scrollbar.set(*scroll_pos)
    
    def create_layout(self):
        """Create the main application layout"""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
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
        self.control_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

    def load_all_data(self):
        """Load all necessary data sources"""
        # Load settings from file
        self.load_settings()
        
        # Always scan ROM directory
        self.scan_roms_directory()
        
        # Load data sources based on mode
        if self.use_fast_mode:
            # Fast mode - only load gamedata.json
            self.load_gamedata_json()
        else:
            # Normal mode - load all data sources
            self.load_controls_data()
            self.load_gamedata_json()
            self.load_mame_xml()
        
        # Always load custom configs
        self.load_custom_configs()
        
        # Update UI
        self.update_stats_label()
        self.update_game_list()
        
        # Auto-select first ROM
        self.select_first_rom()

    def select_first_rom(self):
        """Select and display the first available ROM"""
        try:
            # Get first available ROM
            available_games = sorted(
                game['romname'] for game in self.controls_data 
                if game['romname'] in self.available_roms
            )
            
            if available_games:
                first_rom = available_games[0]
                # Create a mock event with coordinates at the first line
                class MockEvent:
                    def __init__(self):
                        self.x = 0
                        self.y = 5  # Small y value to hit first line
                
                self.on_game_select(MockEvent())
        except Exception as e:
            print(f"Error auto-selecting first ROM: {str(e)}")

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

    def compare_controls(self, game_data: Dict, cfg_controls: Dict) -> List[Tuple[str, str, str, bool]]:
        """Compare default controls with cfg controls
        Returns list of (control_name, default_label, current_mapping, is_different)"""
        comparisons = []
        
        # Get default controls from game data
        for player in game_data.get('players', []):
            player_num = player['number']
            for label in player.get('labels', []):
                control_name = label['name']
                default_label = label['value']
                current_mapping = cfg_controls.get(control_name, "Not mapped")
                is_different = control_name in cfg_controls  # Consider it different if it's mapped in cfg
                comparisons.append((control_name, default_label, current_mapping, is_different))
        
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

if __name__ == "__main__":
    app = MAMEControlConfig()
    app.mainloop()