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

class FilterGamesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Customisation")
        self.root.geometry("1920x1080")  # Set the initial size (you can adjust as needed)
        self.root.resizable(True, True)  # Enable window resizing
        
        # Set the window icon
        #icon_path = os.path.join(os.getcwd(), 'Potion.ico')  # Adjust path as needed
        #self.iconbitmap(icon_path)  # For .ico files
        
        # Center the window on the screen
        self.center_window(1200, 800)

        # Main container to hold both the tabview and exe selector
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create the frame for the tabs (Filter Games, Advanced Configs, and Playlists)
        self.tabview_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="transparent")
        self.tabview_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # Create the exe selector frame (on the right side)
        self.exe_selector_frame = ctk.CTkFrame(self.main_frame, width=300, corner_radius=10)
        self.exe_selector_frame.pack(side="right", fill="y", padx=10, pady=10)

        # Create tab view and initialize the tabs for each class
        self.tabview = ctk.CTkTabview(self.tabview_frame, corner_radius=10, fg_color="transparent")
        self.tabview.pack(expand=True, fill="both")

        # Advanced Configurations tab
        self.advanced_configs_tab = self.tabview.add("Advanced Configs")
        self.advanced_configs = AdvancedConfigs(self.advanced_configs_tab)

        # Playlists tab
        self.playlists_tab = self.tabview.add("Playlists")
        self.playlists = Playlists(self.playlists_tab)
        
        # Filter Games tab
        self.filter_games_tab = self.tabview.add("Filter Games")
        self.filter_games = FilterGames(self.filter_games_tab)
        
        # Add exe file selector on the right side
        self.exe_selector = ExeFileSelector(self.exe_selector_frame) 
        
        # Bottom frame for Appearance Mode options
        self.add_appearance_mode_frame()

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
            
    def add_appearance_mode_frame(self):
        appearance_frame = ctk.CTkFrame(self.root, corner_radius=10)
        appearance_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ctk.CTkLabel(appearance_frame, text="Appearance Mode", font=("Arial", 14, "bold")).pack(side="left", padx=(20, 10), pady=10)

        appearance_mode_optionmenu = ctk.CTkOptionMenu(
            appearance_frame, values=["Light", "Dark", "System"], command=lambda mode: ctk.set_appearance_mode(mode)
        )
        appearance_mode_optionmenu.pack(side="right", padx=10, pady=10)

class ExeFileSelector:
    def __init__(self, parent_frame):
        # Create a new frame for the .exe radio buttons below the main content
        exe_frame = ctk.CTkFrame(parent_frame, corner_radius=10)  # New frame for exe selection
        exe_frame.grid(row=1, column=1, sticky="nswe", padx=10, pady=10)  # Place below main_content_frame

        ctk.CTkLabel(exe_frame, text="Select Executable", font=("Arial", 14, "bold")).pack(padx=10, pady=10)

        # Create a scrollable frame inside exe_frame to hold the radio buttons
        scrollable_frame = ctk.CTkScrollableFrame(exe_frame, width=400, height=200, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Find all .exe files in the directory
        self.exe_files = self.find_exe_files()

        # Variable to hold the selected exe file
        self.exe_var = tk.StringVar(value="")  # Default to no selection

        # Add a radio button for each .exe file found inside the scrollable frame
        for exe in self.exe_files:
            rbutton = ctk.CTkRadioButton(scrollable_frame, text=exe, variable=self.exe_var, value=exe)
            rbutton.pack(anchor="w", padx=20, pady=5)

        # Add a button to run the selected exe
        run_exe_button = ctk.CTkButton(exe_frame, text="Run Selected Executable", command=self.run_selected_exe)
        run_exe_button.pack(pady=20)
        
        # Call a method to add the batch file buttons frame below this frame
        self.add_batch_file_buttons(parent_frame)

    def add_batch_file_buttons(self, parent_frame):
        # Create a frame for batch file buttons below the exe frame
        self.batch_file_frame = ctk.CTkFrame(parent_frame, corner_radius=10, fg_color="transparent")
        self.batch_file_frame.grid(row=2, column=1, sticky="nswe", padx=20, pady=(5, 10))  # Adjust row index

        # Add a title for the reset section
        reset_label = ctk.CTkLabel(self.batch_file_frame, text="Reset Build to Defaults", font=("Arial", 14, "bold"))
        reset_label.pack(pady=(10, 5))  # Padding to separate from buttons

        # Find all batch files in the current directory with "Reset" in their names
        batch_files = self.find_reset_batch_files()

        # Dynamically create a button for each batch file
        for batch_file in batch_files:
            button_text = os.path.splitext(batch_file[2:])[0]  # Remove the first two characters from the name
            
            # Create a button with the modified name
            button = ctk.CTkButton(
                self.batch_file_frame, 
                text=button_text,
                command=lambda bf=batch_file: self.run_script(bf), 
                hover_color="red"
            )
            button.pack(pady=10, padx=10, fill='x')  # Fill horizontally for better spacing

    def find_reset_batch_files(self):
        """Find all .bat files in the current directory that have 'Reset' in their name."""
        base_path = os.getcwd()  # Get the current working directory

        # Debugging: Print the base path and all files in the directory
        print(f"Base path: {base_path}")
        print(f"Files in directory: {os.listdir(base_path)}")

        # Find all .bat files with "Reset" in their name
        return [f for f in os.listdir(base_path) if f.endswith('.bat') and "Restore" in f]

    def run_script(self, script_name):
        confirm = messagebox.askyesno(
            "Confirmation",
            f"Are you sure you want to run the '{script_name}' script?"
        )
        
        if not confirm:
            return  # Exit if the user selects "No"
            
        try:
            # Get the full path to the script
            script_path = os.path.join(os.getcwd(), script_name)
    
            # Check if the script exists
            if not os.path.isfile(script_path):
                messagebox.showerror("File Not Found", f"The script does not exist at the path: {script_path}")
                return
        
            print(f"Attempting to run script at: {script_path}")  # Debug print statement

            # Run the batch file
            completed_process = subprocess.run(
                f'cmd.exe /c "{script_path}"',
                shell=True,
                capture_output=True,  # Capture stdout and stderr
                text=True,  # Decode to text
                check=False  # Don't automatically raise an error if the command fails
            )

            # Check for errors in the execution
            if completed_process.returncode != 0:
                error_message = (
                    f"Failed to run {script_name}.\n\n"
                    f"Return Code: {completed_process.returncode}\n"
                    f"Error Output: {completed_process.stderr.strip()}\n"
                    f"Standard Output: {completed_process.stdout.strip()}"
                )
                messagebox.showerror("Script Execution Error", error_message)
            else:
                #success_message = f"Script '{script_name}' ran successfully:\n{completed_process.stdout.strip()}"
                messagebox.showinfo("Success", "Restore Defaults (Arcades and Consoles) has run" )#, success_message)
                print(f"Script ran successfully:\n{completed_process.stdout.strip()}")

        except FileNotFoundError:
            messagebox.showerror("File Not Found", f"The specified batch file was not found: {script_path}")
        except PermissionError:
            messagebox.showerror("Permission Denied", f"Permission denied while trying to run: {script_path}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred while running {script_name}: {str(e)}")

            
    '''def run_script(self, script_name):
        try:
            script_path = os.path.join(os.getcwd(), script_name)
            if os.path.isfile(script_path):
                subprocess.run(f'cmd.exe /c "{script_path}"', check=True)#check=True,text=True,capture_output=True,
            else:
                messagebox.showerror("Error", f"The script does not exist: {script_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run {script_name}: {str(e)}")'''

    def find_exe_files(self):
        """Finds all .exe files in the current directory."""
        if getattr(sys, 'frozen', False):
            # When running as a PyInstaller executable
            base_path = os.path.dirname(sys.executable)
            current_exe = os.path.basename(sys.executable)  # Get the name of the current executable
        else:
            # When running as a script
            base_path = os.path.dirname(os.path.abspath(__file__))
            current_exe = None  # No current exe if running as a script

        # Debugging: Print the base path and all files in the directory
        print(f"Base path: {base_path}")
        print(f"Files in directory: {os.listdir(base_path)}")

        # Find and return all .exe files in the directory, excluding the current exe
        return [f for f in os.listdir(base_path) if f.endswith('.exe') and f != current_exe]

    def run_selected_exe(self):
        """Runs the selected executable file."""
        if getattr(sys, 'frozen', False):
            # When running as a PyInstaller executable
            base_path = os.path.dirname(sys.executable)
        else:
            # When running as a script
            base_path = os.path.dirname(os.path.abspath(__file__))

        selected_exe = self.exe_var.get()  # Get the selected exe from the radio buttons
        if selected_exe:
            exe_path = os.path.join(base_path, selected_exe)  # Use the correct base path
            try:
                os.startfile(exe_path)  # This will run the .exe file (Windows only)
                root.destroy()  # Close the window after running the .exe
                
                # Adding a short delay before the script ends to allow for cleanup
                time.sleep(1)  # Delay for 1 second
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run {selected_exe}: {e}")
        else:
            messagebox.showinfo("No Selection", "Please select an executable.")

class FilterGames:
    def __init__(self, parent_tab):
        # Store references to parent_tab for creating widgets
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

        # Call methods to create the UI and load necessary settings
        self.create_filter_games_tab()
        self.load_custom_dll()

        # Path to the CSV file
        self.csv_file_path = self.get_csv_file_path()

    def create_filter_games_tab(self):
        # Create a sidebar frame to hold the tab view for control types, buttons, and vertical filter
        sidebar_frame = ctk.CTkFrame(self.parent_tab, width=200, corner_radius=10)
        sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nswe", padx=10, pady=10)

        # Create main content frame for buttons (Filter, Reset, etc.)
        main_content_frame = ctk.CTkFrame(self.parent_tab, corner_radius=10)
        main_content_frame.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)

        # Create a TabView for Control Types, Buttons, and Vertical Filter
        tabview = ctk.CTkTabview(sidebar_frame, width=200)
        tabview.pack(padx=10, pady=10, fill='both', expand=True)

        # Add Control Types, Buttons, and Vertical tabs
        control_types_tab = tabview.add("Control Types")
        buttons_tab = tabview.add("Buttons")
        vertical_tab = tabview.add("Vertical")

        # Control Types checkboxes in the "Control Types" tab
        self.control_type_vars = {}
        control_types = ["8 way", "4 way", "analog", "trackball", "twin stick", "lightgun"]
        ctk.CTkLabel(control_types_tab, text="Control Types", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=20, pady=10)

        for index, control_type in enumerate(control_types, start=1):
            var = tk.IntVar()
            checkbox = ctk.CTkCheckBox(control_types_tab, text=control_type, variable=var)
            checkbox.grid(row=index, column=0, padx=20, pady=5, sticky='w')
            self.control_type_vars[control_type] = var

        # Move Number of Buttons to "Buttons" tab
        self.buttons_var = ctk.StringVar(value="Select number of buttons")
        button_options = ["Select number of buttons", "0", "1", "2", "3", "4", "5", "6"]
        ctk.CTkLabel(buttons_tab, text="Number of Buttons", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=20, pady=10)
        buttons_dropdown = ctk.CTkOptionMenu(buttons_tab, variable=self.buttons_var, values=button_options)
        buttons_dropdown.grid(row=1, column=0, padx=20, pady=5)

        # Move the Vertical filter checkbox to the "Vertical" tab
        self.vertical_checkbox_var = tk.IntVar()
        vertical_checkbox = ctk.CTkCheckBox(vertical_tab, text="Include only Vertical Games", variable=self.vertical_checkbox_var)
        vertical_checkbox.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Add Filter and Show All Games buttons to the main content frame
        filter_button = ctk.CTkButton(main_content_frame, text="Filter Games", command=self.filter_games_from_csv)
        filter_button.pack(pady=20)

        show_all_button = ctk.CTkButton(main_content_frame, text="Reset to Default", command=self.show_all_games, fg_color="red")
        show_all_button.pack(pady=10)

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
        autochanger_csv_path = os.path.join('autochanger', 'MAMEx.csv')
        if os.path.exists(autochanger_csv_path):
            return autochanger_csv_path

        # If not found, use the bundled CSV in the executable (from --addfile)
        if getattr(sys, 'frozen', False):  # When running as a bundled executable
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # Return the path to the bundled CSV
        return os.path.join(base_path, 'meta', 'hyperlist', 'MAMEx.csv')

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

    def filter_games_from_csv(self):
        self.check_output_dir()

        try:
            with open(self.csv_file_path, newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    game_count = 0

                    selected_ctrltypes = self.get_selected_control_types()
                    selected_buttons = self.buttons_var.get().strip()
                    vertical_filter = self.vertical_checkbox_var.get()

                    for row in reader:
                        joystick_input = self.sanitize_csv_cell(row.get('ctrlType'))
                        rom_name = self.sanitize_csv_cell(row.get('ROM Name'))
                        vertical = row.get('Vertical')
                        buttons = row.get('Buttons')

                        buttons = int(buttons) if buttons.isdigit() else float('inf')

                        if vertical_filter == 1 and (not vertical or vertical.strip().upper() != "VERTICAL"):
                            continue

                        if selected_buttons != "Select number of buttons" and buttons > int(selected_buttons):
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

                    if game_count == 0:
                        messagebox.showinfo("No Games Found", "No games matched the selected filters.")
                    else:
                        messagebox.showinfo("Success", f"{game_count} games added to {self.output_file}")

        except Exception as e:
            messagebox.showerror("Error", f"Error opening CSV file: {e}")

    def show_all_games(self):
        try:
            source = "autochanger/include.txt"  # Define the correct source path
            destination = "collections/Arcades/include.txt"  # Define the correct destination path
            
            # Check if the source file exists
            if os.path.exists(source):
                # Copy the file from source to destination
                shutil.copyfile(source, destination)
                messagebox.showinfo("Success", f"Copied '{source}' to '{destination}'.")
            else:
                # If source does not exist, delete the file in Arcades if it exists
                if os.path.exists(destination):
                    os.remove(destination)
                    messagebox.showinfo("Success", f"'{destination}' has been deleted as the source file was not found.")
                else:
                    messagebox.showinfo("Info", f"No file to delete. '{destination}' does not exist.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process files: {str(e)}")

class Playlists:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        self.playlists_path = os.path.join(self.base_path, "collections", "Arcades", "playlists")
        self.autochanger_conf_path = os.path.join(self.base_path, "autochanger", "settings5_7.conf")
        
        self.check_vars = []
        self.check_buttons = []
        self.excluded_playlists = [
            "arcades40", "arcades60", "arcades80", "arcades120", "arcades150", "arcades220",
            "arcader", "arcades", "consoles", "favorites", "lastplayed", "settings"
        ]
        
        # Playlists associated with each toggle
        #self.genre_playlists = ["beat em ups", "fight club", "old school", "puzzler", "racer", "run n gun", "shoot em ups", "sports", "trackball", "twinsticks", "vector"]
        self.manufacturer_playlists = ["atari", "capcom", "cave", "data east", "gunner", "irem", "konami", "midway", "namco", "neogeo", "nintendo", "psikyo", "raizing", "sega", "snk", "taito", "technos", "tecmo", "toaplan", "williams"]  # Example, can expand later
        self.sort_type_playlists = ["ctrltype", "manufacturer", "numberplayers", "year"]  # Example, can expand later
        
        # Create a main frame for all content
        self.main_frame = ctk.CTkFrame(self.parent_tab, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        
        #Come back top this. No idea why sort is not working.Manu and genre work fine
        '''
        # Create a frame for switches and place it at the top
        self.switch_frame = ctk.CTkFrame(self.main_frame)
        self.switch_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Add CTkSwitch widgets in the switch frame
        self.genre_switch = ctk.CTkSwitch(self.switch_frame, text="Genres", command=self.toggle_genres, onvalue="on", offvalue="off")
        self.genre_switch.select()  # Default to 'on'
        self.genre_switch.pack(side="left", padx=5, pady=5)

        self.manufacturer_switch = ctk.CTkSwitch(self.switch_frame, text="Manufacturers", command=self.toggle_manufacturers, onvalue="on", offvalue="off")
        self.manufacturer_switch.select()  # Default to 'on'
        self.manufacturer_switch.pack(side="left", padx=5, pady=5)

        self.sort_types_switch = ctk.CTkSwitch(self.switch_frame, text="Sort Types", command=self.toggle_sort_types, onvalue="on", offvalue="off")
        self.sort_types_switch.select()  # Default to 'on'
        self.sort_types_switch.pack(side="left", padx=5, pady=5)
        '''
        
        # Create a frame for the scrollable checkbox area below the switches
        self.scrollable_checklist = ctk.CTkScrollableFrame(self.main_frame, width=400, height=400)
        self.scrollable_checklist.pack(fill="both", expand=True, padx=10, pady=10)

        # Populate checkboxes based on available playlist files
        self.populate_checkboxes()

        # Create a frame for the buttons
        button_frame = ctk.CTkFrame(self.parent_tab)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # Create playlist buttons
        self.create_playlist_button = ctk.CTkButton(
            button_frame,
            text="Create Playlist",
            command=self.create_playlist,
            fg_color="#4CAF50",
            hover_color="#45A049"
        )
        self.create_playlist_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        self.reset_button = ctk.CTkButton(
            button_frame,
            text="Reset Playlists",
            fg_color="#D32F2F",
            hover_color="#C62828",
            command=self.reset_playlists
        )
        self.reset_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        '''
        self.genres_button = ctk.CTkButton(
            button_frame,
            text="All Genres",
            command=lambda: self.activate_special_playlist("beat em ups, fight club, old school, puzzler, racer, run n gun, shoot em ups, sports, trackball, twinsticks, vector")
        )
        self.genres_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        '''
        self.genres_button = ctk.CTkButton(
            button_frame,
            text="All Genres",
            command=lambda: self.activate_special_playlist(",".join(self.get_genre_playlists()))
        )
        self.genres_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        
        self.manufacturer_button = ctk.CTkButton(
            button_frame,
            text="All Manufacturer",
            command=lambda: self.activate_special_playlist(",".join(self.manufacturer_playlists))
        )
        self.manufacturer_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        self.sort_type_button = ctk.CTkButton(
            button_frame,
            text="All Sort Types",
            command=lambda: self.activate_special_playlist(",".join(self.sort_type_playlists))
        )
        self.sort_type_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

    # Define toggle functions and other methods as before...
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
    
    def refresh_checkboxes(self):
        for widget in self.scrollable_checklist.winfo_children():
            widget.destroy()
        self.populate_checkboxes()

    def populate_checkboxes(self):
        """Populates the initial checkboxes with manufacturer playlists at the end."""
        try:
            all_playlists = []  # To store all found playlists
            manufacturer_playlists = []  # To store only manufacturer playlists
            sort_type_playlists = []  # To store only sort type playlists

            # Debugging: Print the path we're checking
            #print("Checking playlists in:", self.playlists_path)
            
            # Debugging: Print the sort type playlists to check if they're defined
            #print("Sort Type Playlists:", self.sort_type_playlists)
        
            # Iterate through the files in the playlists directory
            for playlist_file in os.listdir(self.playlists_path):
                playlist_name, ext = os.path.splitext(playlist_file)
                # Check if it's a .txt file and not excluded
                if ext == ".txt" and playlist_name.lower() not in self.excluded_playlists:
                    all_playlists.append(playlist_name)  # Add to all_playlists
                    
                    # Check if it's a manufacturer playlist
                    if playlist_name.lower() in [m.lower() for m in self.manufacturer_playlists]:
                        manufacturer_playlists.append(playlist_name)  # Separate manufacturer playlists
                        
                        # Check if it's a sort type playlist
                    if playlist_name.lower() in [s.lower() for s in self.sort_type_playlists]:
                        sort_type_playlists.append(playlist_name)  # Separate sort type playlists
            
            # Debugging: Print found playlists
            print("Found Playlists:", all_playlists)
            print("Manufacturer Playlists:", manufacturer_playlists)
            print("Sort Type Playlists:", sort_type_playlists)
            
            # Remove manufacturer playlists from all_playlists
            for manufacturer_playlist in manufacturer_playlists:
                if manufacturer_playlist in all_playlists:
                    all_playlists.remove(manufacturer_playlist)
            
            # Remove sort type playlists from all_playlists
            for sort_playlist in sort_type_playlists:
                if sort_playlist in all_playlists:
                    all_playlists.remove(sort_playlist)
                
            # Append manufacturer playlists to the end
            all_playlists.extend(manufacturer_playlists)
            
            # Append sort type playlists to the end
            all_playlists.extend(sort_type_playlists)  # Add sort playlists after manufacturer playlists
        
            # Debugging: Print the final order of playlists
            print("Final Playlist Order:", all_playlists)

            # Populate checkboxes in the desired order
            for playlist_name in all_playlists:
                var = tk.BooleanVar()
                checkbutton = ctk.CTkCheckBox(self.scrollable_checklist, text=playlist_name, variable=var)
                checkbutton.pack(anchor="w", padx=10, pady=5)
                self.check_vars.append((playlist_name, var))

        except FileNotFoundError:
            print(f"Playlists folder not found at: {self.playlists_path}")
        except Exception as e:
            # Catch all exceptions to understand any issues
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
    
    def activate_special_playlist(self, playlist_type):
        playlists_to_check = [playlist.strip() for playlist in playlist_type.split(",")]
        for name, var in self.check_vars:
            if name in playlists_to_check:
                var.set(not var.get())  # Toggle the checkbox state
               
    def reset_playlists(self):
        """Reset the settings by copying 'settings5_7x.conf' to 'settings5_7.conf'."""
        # Path to the backup configuration file
        backup_conf_path = os.path.join(self.base_path, "autochanger", "settings5_7x.conf")

        try:
            # Check if the backup file exists
            if os.path.exists(backup_conf_path):
                # Copy the backup file to replace the original configuration file
                shutil.copy(backup_conf_path, self.autochanger_conf_path)
                messagebox.showinfo("Success", "Playlists have been reset to default.")
            else:
                messagebox.showerror("Error", "Backup configuration file 'settings5_7x.conf' not found.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during reset: {str(e)}")
    
    def read_default_playlists(self):
        try:
            with open(os.path.join("autochanger", "default_playlists.txt"), 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("cyclePlaylist ="):
                        default_playlists = [item.strip() for item in line.split("=", 1)[1].split(",") if item.strip()]
                        return default_playlists
            return ["arcader", "consoles", "favorites", "lastplayed"]
        # surpressing the error, as it's not really an error - we use hardcoded values if not found
        except FileNotFoundError:
            return ["arcader", "consoles", "favorites", "lastplayed"]
            #messagebox.showerror("Error", "Default playlists file not found.")
            #return []
        except Exception as e:
            print(f"An error occurred while reading default playlists: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while reading default playlists: {str(e)}")
            return[]
                 
    def update_conf_file(self, playlist_list):
        try:
            default_playlists = self.read_default_playlists()
            if not default_playlists:
                default_playlists = ["arcades, lastplayed"]  # Fallback if reading file fails
            
            # The main playlist for firstPlaylist should only be the first entry from default_playlists
            main_default_playlist = default_playlists[0]
                
            with open(self.autochanger_conf_path, 'r') as file:
                lines = file.readlines()

            cycle_playlist_found = False
            first_playlist_found = False

            updated_lines = []
            first_selected_playlist = playlist_list[0] if playlist_list else default_playlists[0]

            for line in lines:
                if line.startswith("cyclePlaylist ="):
                    new_line = f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n"
                    updated_lines.append(new_line)
                    cycle_playlist_found = True
                elif line.startswith("firstPlaylist ="):
                    new_line = f"firstPlaylist = {main_default_playlist}\n"
                    updated_lines.append(new_line)
                    first_playlist_found = True
                else:
                    updated_lines.append(line)

            if not cycle_playlist_found:
                updated_lines.append(f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n")
            if not first_playlist_found:
                updated_lines.append(f"firstPlaylist = {first_selected_playlist}, {default_playlists[0]}\n")

            with open(self.autochanger_conf_path, 'w') as file:
                file.writelines(updated_lines)

            messagebox.showinfo("Success", f"Updated Playlist(s): {', '.join(playlist_list)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

class AdvancedConfigs:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        self.config_folders = ["- Advanced Configs", "- Themes", "- Themes 2nd Screen", "- Bezels Glass and Scanlines"]
        self.tab_keywords = {
            "Themes": None,  # For direct folder mapping
            "2nd Screen": None,  # For direct folder mapping
            "Bezels & Effects": ["Bezel", "SCANLINE", "GLASS EFFECTS"],  # Updated to use keywords too
            "Overlays": ["OVERLAY"],  # Updated to use keywords too
            "InigoBeats": ["MUSIC"],
            "Attract": ["Attract", "Scroll"],           
            "Monitor": ["Monitor"],
            "Splash": ["Splash"],
            "Front End": ["FRONT END"],
            "Other": None
        }

        # Map folders to tabs for direct mapping
        self.folder_to_tab_mapping = {
            "- Themes": "Themes",
            "- Themes 2nd Screen": "2nd Screen",
            "- Bezels Glass and Scanlines": "Bezels & Effects"
        }

        self.tab_radio_vars = {}
        self.radio_button_script_mapping = {}

        # Create the tab view in the parent tab
        self.tabview = ctk.CTkTabview(self.parent_tab)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Populate the tabs and scripts dynamically
        self.populate_tabs_and_scripts()

        # Add the Configure button at the bottom of the parent tab
        self.configure_button = ctk.CTkButton(
            self.parent_tab,
            text="Configure",
            command=self.run_selected_script
        )
        self.configure_button.pack(side="bottom", pady=10, padx=10)

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

                    # Step 1: Direct folder mapping
                    if folder in self.folder_to_tab_mapping:
                        tab_name = self.folder_to_tab_mapping[folder]
                        script_categories[tab_name][len(script_categories[tab_name]) + 1] = filename
                        added_to_tab = True
                    
                    # Step 2: Keyword matching (if not already categorized by folder)
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

                    # Step 3: Default to "Other" tab if not matched to any tab yet
                    if not added_to_tab:
                        script_categories["Other"][len(script_categories["Other"]) + 1] = filename

        return script_categories

    def populate_tabs_and_scripts(self):
        script_categories = self.categorize_scripts()

        for tab_name, scripts in script_categories.items():
            if scripts:
                self.tabview.add(tab_name)
                self.tab_radio_vars[tab_name] = tk.IntVar(value=0)
                self.radio_button_script_mapping[tab_name] = scripts

                scrollable_frame = ctk.CTkScrollableFrame(self.tabview.tab(tab_name), width=400, height=400)
                scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

                for i, script_name in scripts.items():
                    script_label = os.path.splitext(script_name)[0]
                    ctk.CTkRadioButton(
                        scrollable_frame,
                        text=script_label,
                        variable=self.tab_radio_vars[tab_name],
                        value=i
                    ).pack(anchor="w", padx=20, pady=5)

    def run_selected_script(self):
        selected_tab = self.tabview.get()
        selected_value = self.tab_radio_vars[selected_tab].get()

        if selected_value in self.radio_button_script_mapping[selected_tab]:
            script_to_run = self.radio_button_script_mapping[selected_tab][selected_value]

            script_path = None
            for folder in self.config_folders:
                potential_path = os.path.join(self.base_path, folder, script_to_run)
                if os.path.isfile(potential_path):
                    script_path = potential_path
                    break

            if not script_path:
                messagebox.showerror("Error", f"The script does not exist: {script_to_run}")
                return

            try:
                result = subprocess.run(
                    ["cmd.exe", "/c", script_path],
                    check=True,
                    text=True,
                    capture_output=True,
                    cwd=os.path.dirname(script_path)
                )
                #Surpress success because errors are not tru, and confuse users
                #messagebox.showinfo("Success", f"'{script_to_run}' executed successfully.\nOutput:\n{result.stdout}")
            except subprocess.CalledProcessError as cpe:
                messagebox.showinfo("Info", f"Script ran, but with issues:\nOutput:\n{e.output}")
        else:
            messagebox.showwarning("Warning", "No script is mapped to the selected option.")
                         

# Main application driver
if __name__ == "__main__":
    # Initialize GUI with customtkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = FilterGamesApp(root)
    root.mainloop()
