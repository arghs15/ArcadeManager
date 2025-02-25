import customtkinter as ctk
import json
import os
import re
from tkinter import messagebox
from typing import Dict, Optional, Set, List, Tuple

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
        
        # Set initial fullscreen state
        self.after(100, self.state, 'zoomed')  # Use zoomed for Windows

        # Initialize data structures
        self.controls_data: List = []  # Changed to list for games array
        self.available_roms: Set[str] = set()
        self.custom_configs: Dict = {}
        self.current_game: Optional[str] = None
        # Add after other instance variables
        self.use_xinput = True
        self.current_game = None
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
            'JOYCODE_1_BUTTON11': 'XINPUT_1_START',      # Start Button
            'JOYCODE_1_BUTTON12': 'XINPUT_1_BACK',       # Back/Select Button
            'JOYCODE_1_HATUP': 'XINPUT_1_DPAD_UP',      # D-Pad Up
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
        
        # Mapping dictionary for controls
        control_mappings = {
            'BUTTON1': 'X Button',
            'BUTTON2': 'B Button',
            'BUTTON3': 'Y Button',
            'BUTTON4': 'A Button',
            'BUTTON5': 'LB Button',
            'BUTTON6': 'RB Button',
            'BUTTON7': 'LT Button',
            'BUTTON8': 'RT Button',
            'BUTTON9': 'L3 Button',
            'BUTTON10': 'R3 Button',
            'JOYSTICK_UP': 'Left Stick Up',
            'JOYSTICK_DOWN': 'Left Stick Down',
            'JOYSTICK_LEFT': 'Left Stick Left',
            'JOYSTICK_RIGHT': 'Left Stick Right',
            'JOYSTICK2_UP': 'Right Stick Up',
            'JOYSTICK2_DOWN': 'Right Stick Down',
            'JOYSTICK2_LEFT': 'Right Stick Left',
            'JOYSTICK2_RIGHT': 'Right Stick Right',
        }
        
        # Check if we have a mapping for this control
        if control_type in control_mappings:
            return f"{player_num} {control_mappings[control_type]}"
        
        return control_name
    
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
        if self.current_game:
            # Store the current scroll position
            scroll_pos = self.control_frame._scrollbar.get()
            
            # Create a mock event to pass to on_game_select
            class MockEvent:
                def __init__(self):
                    self.x = 0
                    self.y = 0
            
            # Find the line number for the current game
            content = self.game_list.get("1.0", "end")
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if self.current_game in line:
                    # Create click coordinates that would select this line
                    mock_event = MockEvent()
                    # Get the actual coordinates of the line
                    bbox = self.game_list.bbox(f"{i+1}.0")
                    if bbox:
                        mock_event.x = bbox[0]
                        mock_event.y = bbox[1]
                    # Refresh the display
                    self.on_game_select(mock_event)
                    break
                    
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

        # Game list
        self.game_list = ctk.CTkTextbox(self.left_panel)
        self.game_list.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
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

        # Controls display
        self.control_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.control_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

    def load_all_data(self):
        """Load all necessary data sources"""
        self.load_controls_data()
        self.scan_roms_directory()
        self.load_custom_configs()
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

    def get_game_data(self, romname):
        """Get control data for a ROM, including variant matches"""
        # Direct match first
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
        unmatched = len(self.find_unmatched_roms())
        matched = len(self.available_roms) - unmatched
        stats = (
            f"Total games in controls.dat: {len(self.controls_data)}\n"
            f"Available ROMs: {len(self.available_roms)} ({matched} with controls, {unmatched} without)\n"
            f"Custom configs: {len(self.custom_configs)}"
        )
        self.stats_label.configure(text=stats)
    
    def find_unmatched_roms(self) -> Set[str]:
        """Find ROMs that don't have matching control data"""
        control_roms = {game['romname'] for game in self.controls_data}
        return self.available_roms - control_roms

    def show_unmatched_roms(self):
        """Display ROMs that don't have matching control data"""
        # Categorize ROMs using the same get_game_data logic
        unmatched = []
        direct_matches = []
        variant_matches = []

        for rom in sorted(self.available_roms):
            game_data = self.get_game_data(rom)
            if not game_data:
                unmatched.append(rom)
            else:
                # Check if it's a variant or direct match
                if any(game['romname'] == rom for game in self.controls_data):
                    direct_matches.append(rom)
                else:
                    # Must be a variant match
                    original_game = next(game for game in self.controls_data 
                                    if re.sub(r'[jubew]$', '', game['romname']) == 
                                    re.sub(r'[jubew]$', '', rom))
                    variant_matches.append((rom, original_game['romname']))

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
            f"Unmatched ROMs: {len(unmatched)}\n\n"
            f"Control data coverage: {((len(direct_matches) + len(variant_matches)) / len(self.available_roms) * 100):.1f}%"
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
        if unmatched:
            unmatched_text = ctk.CTkTextbox(unmatched_tab)
            unmatched_text.pack(expand=True, fill="both", padx=10, pady=10)
            unmatched_text.insert("1.0", "\n".join(unmatched))
            unmatched_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                unmatched_tab,
                text="No unmatched ROMs found!",
                font=("Arial", 14)
            ).pack(expand=True)
        
        # Variant matches tab
        variants_tab = tabview.add("Variant Matches")
        if variant_matches:
            variants_text = ctk.CTkTextbox(variants_tab)
            variants_text.pack(expand=True, fill="both", padx=10, pady=10)
            for rom, control_rom in sorted(variant_matches):
                variants_text.insert("end", f"{rom} → {control_rom}\n")
            variants_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                variants_tab,
                text="No variant matches found!",
                font=("Arial", 14)
            ).pack(expand=True)
        
        # Direct matches tab
        direct_tab = tabview.add("Direct Matches")
        if direct_matches:
            direct_text = ctk.CTkTextbox(direct_tab)
            direct_text.pack(expand=True, fill="both", padx=10, pady=10)
            direct_text.insert("1.0", "\n".join(direct_matches))
            direct_text.configure(state="disabled")
        else:
            ctk.CTkLabel(
                direct_tab,
                text="No direct matches found!",
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
                    f.write("\n".join(sorted(direct_matches)) + "\n\n")
                    
                    f.write("Variant Matches:\n")
                    f.write("===============\n")
                    for rom, control_rom in sorted(variant_matches):
                        f.write(f"{rom} → {control_rom}\n")
                    f.write("\n")
                    
                    f.write("Unmatched ROMs:\n")
                    f.write("==============\n")
                    f.write("\n".join(sorted(unmatched)))
                    
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
    
    def update_stats_label(self):
        """Update the statistics label"""
        stats = (
            f"Total games in controls.dat: {len(self.controls_data)}\n"
            f"Available ROMs: {len(self.available_roms)}\n"
            f"Custom configs: {len(self.custom_configs)}"
        )
        self.stats_label.configure(text=stats)

    def update_game_list(self):
        """Update the game list to show all available ROMs"""
        self.game_list.delete("1.0", "end")
        
        # Sort available ROMs
        available_roms = sorted(self.available_roms)
        
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
            
            self.game_list.insert("end", f"{prefix}{display_name}\n")
        
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
                
                self.game_list.insert("end", f"{prefix}{display_name}\n")

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
            line = self.game_list.get(f"{index} linestart", f"{index} lineend")
            
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

    def map_control_to_xinput_config(self, control_name: str) -> Tuple[str, str]:
        """Map MAME control to Xbox controller config field"""
        mapping_dict = {
            'P1_BUTTON1': ('controller X t', 'X Button'),      # Usually mapped to JOYCODE_1_BUTTON3
            'P1_BUTTON2': ('controller B t', 'B Button'),      # Usually mapped to JOYCODE_1_BUTTON2
            'P1_BUTTON3': ('controller Y t', 'Y Button'),      # Usually mapped to JOYCODE_1_BUTTON4
            'P1_BUTTON4': ('controller A t', 'A Button'),      # Usually mapped to JOYCODE_1_BUTTON1
            'P1_BUTTON5': ('controller LB t', 'Left Bumper'),  # Usually mapped to JOYCODE_1_BUTTON5
            'P1_BUTTON6': ('controller RB t', 'Right Bumper'), # Usually mapped to JOYCODE_1_BUTTON6
            'P1_JOYSTICK_UP': ('controller L-stick t', 'Left Stick Up'),
            'P1_JOYSTICK_DOWN': ('controller L-stick t', 'Left Stick Down'),
            'P1_JOYSTICK_LEFT': ('controller L-stick t', 'Left Stick Left'),
            'P1_JOYSTICK_RIGHT': ('controller L-stick t', 'Left Stick Right'),
            'P2_BUTTON1': ('controller R-stick t', 'Right Stick Button 1'),
            'P2_BUTTON2': ('controller R-stick t', 'Right Stick Button 2'),
            'P2_BUTTON3': ('controller R-stick t', 'Right Stick Button 3'),
            'P2_BUTTON4': ('controller R-stick t', 'Right Stick Button 4'),
        }
        return mapping_dict.get(control_name, (None, None))

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
        """Generate config files for all available ROMs"""
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
        
        # Get total available ROMs for progress
        total_roms = len([game for game in self.controls_data if game['romname'] in self.available_roms])
        print(f"Found {total_roms} ROMs to process")
        
        for game in self.controls_data:
            if game['romname'] in self.available_roms:
                try:
                    config_content = self.generate_game_config(game)
                    if config_content:
                        config_path = os.path.join(info_dir, f"{game['romname']}.conf")
                        with open(config_path, 'w', encoding='utf-8') as f:
                            f.write(config_content)
                        count += 1
                        if count % 50 == 0:  # Progress update every 50 files
                            print(f"Generated {count}/{total_roms} config files...")
                    else:
                        print(f"Skipping {game['romname']}: No config content generated")
                        skipped += 1
                except Exception as e:
                    error_msg = f"Error with {game['romname']}: {str(e)}"
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