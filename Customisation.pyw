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

class FilterGamesApp:
    @staticmethod
    def resource_path(relative_path):
        """ Get the absolute path to a resource, accounting for PyInstaller's bundling. """
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.getcwd(), relative_path)
        
    def __init__(self, root):
        self.root = root
        self.root.title("Customisation")
        self.root.geometry("1920x1080")  # Set the initial size (you can adjust as needed)
        self.root.resizable(True, True)  # Enable window resizing
        
        # Set the window icon
        #icon_path = os.path.join(os.getcwd(), 'Potion.ico')  # Adjust path as needed
        #self.iconbitmap(icon_path)  # For .ico files
        #root.iconbitmap('Potion.ico')
        icon_path = self.resource_path('Potion.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)

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
        self.playlists_tab = self.tabview.add("Playlists")
        self.playlists = Playlists(self.playlists_tab)
        
        # Filter Games tab
        self.filter_games_tab = self.tabview.add("Filter Games")
        self.filter_games = FilterGames(self.filter_games_tab)
        
        # Add exe file selector on the right side
        self.exe_selector = ExeFileSelector(self.exe_selector_frame) 
        
        # Bottom frame for Appearance Mode options
        #self.add_appearance_mode_frame()
    
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
            

class ExeFileSelector:
    def __init__(self, parent_frame):
        # Store a reference to the parent frame
        self.parent_frame = parent_frame
        
        # Create a new frame for the .exe radio buttons below the main content
        exe_frame = ctk.CTkFrame(parent_frame, corner_radius=10)  # New frame for exe selection
        exe_frame.grid(row=1, column=1, sticky="nswe", padx=10, pady=10)  # Place below main_content_frame
        
        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)
        
        # Check if the logo image file exists
        logo_path = 'autochanger/Logo.png'
        if os.path.exists(logo_path):
            # Load and create the image (logo)
            max_height = 150

            # Open the image to find its original dimensions
            logo_original = Image.open(logo_path)
            aspect_ratio = logo_original.width / logo_original.height
            calculated_width = int(max_height * aspect_ratio)
                
            logo_image = ctk.CTkImage(
                light_image=logo_original,
                dark_image=logo_original,
                size=(calculated_width, max_height)
            )
        
            # Add the logo label to the exe_frame
            logo_label = ctk.CTkLabel(exe_frame, text="", image=logo_image)
            logo_label.pack(pady=(10, 0))
        else:
            # Use title in its place if not found
            ctk.CTkLabel(exe_frame, text="Select Executable", font=("Arial", 14, "bold")).pack(padx=10, pady=10)

        # Create a scrollable frame inside exe_frame to hold the radio buttons
        scrollable_frame = ctk.CTkScrollableFrame(exe_frame, width=400, height=200, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Find all .exe files in the directory
        self.exe_files = self.find_exe_files()

        # Variable to hold the selected exe file
        self.exe_var = tk.StringVar(value="")

        # Add a radio button for each .exe file found inside the scrollable frame
        for exe in self.exe_files:
            rbutton = ctk.CTkRadioButton(scrollable_frame, text=exe, variable=self.exe_var, value=exe)
            rbutton.pack(anchor="w", padx=20, pady=5)

        # Add a switch to control closing the GUI
        self.close_gui_switch = ctk.CTkSwitch(
            exe_frame,
            text="Close GUI After Running",  # Initial text when the switch is off
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=True),  # Set to 'on' by default
            command=self.update_switch_text  # Call a method to update text when toggled
        )
        self.close_gui_switch.pack(pady=10)

        # Call the update method initially to set the correct label
        self.update_switch_text()


        
        # Add a button to run the selected exe
        run_exe_button = ctk.CTkButton(exe_frame, text="Run Selected Executable", command=self.run_selected_exe)
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

            # Run the batch file
            completed_process = subprocess.run(
                f'cmd.exe /c "{script_path}"',
                shell=True,
                capture_output=True,
                text=True,
                check=False
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
                messagebox.showinfo("Success", "Restore Defaults (Arcades and Consoles) has run.")
                print(f"Script ran successfully:\n{completed_process.stdout.strip()}")

        except FileNotFoundError:
            messagebox.showerror("File Not Found", f"The specified batch file was not found: {script_path}")
        except PermissionError:
            messagebox.showerror("Permission Denied", f"Permission denied while trying to run: {script_path}")
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
        
        ## Replaced with a function to retrieve a lsit form autochnagers. if one not found it uses the list below ##
        # Read excluded playlists from the configuration file
        self.excluded_playlists = self.read_excluded_playlists()
        '''self.excluded_playlists = [
            "arcades40", "arcades60", "arcades80", "arcades120", "arcades150", "arcades220",
            "arcader", "arcades", "consoles", "favorites", "lastplayed", "settings"
        ]'''
        
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
        
        ## Old reference to when the values were hard coded.
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
            with open(os.path.join("autochanger", "customisation.txt"), 'r') as file:
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
    
    def read_excluded_playlists(self):
        try:
            with open(os.path.join("autochanger", "customisation.txt"), 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("excluded ="):
                        excluded_playlists = [item.strip() for item in line.split("=", 1)[1].split(",") if item.strip()]
                        return excluded_playlists
            return [
                "arcades40", "arcades60", "arcades80", "arcades120", "arcades150", "arcades220",
                "arcader", "arcades", "consoles", "favorites", "lastplayed", "settings"
            ]
        except FileNotFoundError:
            return [
                "arcades40", "arcades60", "arcades80", "arcades120", "arcades150", "arcades220",
                "arcader", "arcades", "consoles", "favorites", "lastplayed", "settings"
            ]
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while reading excluded playlists: {str(e)}")
            return []
            
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

class Themes:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()

        # Folders for themes and images
        self.theme_folder = os.path.join(self.base_path, "collections", "zzzSettings", "roms")
        self.image_folder = os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "screenshot")

        # List to hold .bat files and their corresponding images
        self.themes_list = []
        self.current_theme_index = 0

        # Create a frame for displaying the image
        self.display_frame = ctk.CTkFrame(self.parent_tab, fg_color="transparent")
        self.display_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Create a canvas for displaying the theme image
        self.image_canvas = tk.Canvas(self.display_frame, width=400, height=300, bg="#2B2B2B", highlightthickness=0, bd=0)
        self.image_canvas.pack(expand=True, fill="both", padx=10, pady=10)
        self.image_canvas.bind("<Configure>", self.on_canvas_resize)

        ## Keep for reference ##
        # Add navigation buttons
        '''self.previous_button = ctk.CTkButton(self.display_frame, text="Previous", command=self.show_previous_theme)
        self.previous_button.pack(side="left", padx=10, pady=10)

        self.next_button = ctk.CTkButton(self.display_frame, text="Next", command=self.show_next_theme)
        self.next_button.pack(side="right", padx=10, pady=10)

        self.apply_button = ctk.CTkButton(self.display_frame, text="Apply Theme", command=self.run_selected_script)
        self.apply_button.pack(side="bottom", padx=10, pady=10)'''

        ## Keep for reference ##
        # Create individual buttons inside the frame
        '''self.previous_button = ctk.CTkButton(self.display_frame, text="Previous", command=self.show_previous_theme)
        self.previous_button.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.apply_button = ctk.CTkButton(self.display_frame, text="Apply Theme", command=self.run_selected_script, fg_color="green")
        self.apply_button.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.next_button = ctk.CTkButton(self.display_frame, text="Next", command=self.show_next_theme)
        self.next_button.pack(side="left", padx=10, pady=10, fill="x", expand=True)'''

        # Create a frame to act as a segmented button container with the same background color
        self.button_frame = ctk.CTkFrame(self.display_frame, corner_radius=8)
        self.button_frame.pack(padx=5, pady=5, fill="x", expand=False)

        # "Previous" button matching the background
        self.previous_button = ctk.CTkButton(
            self.button_frame, text="Previous", command=self.show_previous_theme, 
            border_width=0, corner_radius=0)
        self.previous_button.grid(row=0, column=0, sticky="ew", padx=(5, 0), pady=5)

        # "Apply Theme" button in green for emphasis
        self.apply_button = ctk.CTkButton(
            self.button_frame, text="Apply Theme", command=self.run_selected_script, 
            fg_color="green", hover_color="darkgreen", border_width=0, corner_radius=0)
        self.apply_button.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # "Next" button matching the background
        self.next_button = ctk.CTkButton(
            self.button_frame, text="Next", command=self.show_next_theme, 
            border_width=0, corner_radius=0)
        self.next_button.grid(row=0, column=2, sticky="ew", padx=(0, 5), pady=5)

        # Configure grid layout to make buttons fill evenly within the frame
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Load the themes (scripts and images)
        self.load_themes()

    def on_canvas_resize(self, event=None):
        """Callback to be called when the canvas is resized."""
        self.show_current_theme()  # Refresh the image on canvas resize

    def load_themes(self):
        """Load .bat files from the theme folder and their corresponding images."""
        if not os.path.isdir(self.theme_folder):
            print(f"Folder does not exist: {self.theme_folder}")
            return

        # List of supported image extensions
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif']

        # Clear existing themes_list to avoid duplicate entries
        self.themes_list = []

        for filename in os.listdir(self.theme_folder):
            if filename.endswith(".bat"):
                theme_name = os.path.splitext(filename)[0]

                image_found = False
                for ext in image_extensions:
                    image_path = os.path.join(self.image_folder, f"{theme_name}{ext}")

                    if os.path.isfile(image_path):
                        self.themes_list.append((filename, image_path))
                        print(f"Loaded theme: {theme_name}, Image path: {image_path}")  # Debugging output
                        image_found = True
                        break  # Exit loop once an image is found
                if not image_found:
                    print(f"Warning: No image found for theme: {theme_name}")  # Debugging output
                    self.themes_list.append((filename, None))  # Append with None if no specific image is found

        if not self.themes_list:
            messagebox.showwarning("Warning", "No themes with matching images found.")
        else:
            # Show the first theme after themes are successfully loaded
            self.current_theme_index = 0
            self.show_current_theme()

    def show_current_theme(self):
        """Display the current theme's image on the canvas."""
        if not self.themes_list:
            return  # No themes to show

        theme_name, image_path = self.themes_list[self.current_theme_index]

        # Check if the theme-specific image exists
        if image_path and os.path.isfile(image_path):
            self.update_image_canvas(image_path)
        else:
            # Try to load a default image if available
            default_image_path = os.path.join(self.image_folder, "default.jpg")
            if os.path.isfile(default_image_path):
                self.update_image_canvas(default_image_path)
            else:
                # If no default image is available, display the theme title as text
                print(f"No image found for theme '{theme_name}', displaying title text instead.")
                self.display_title_text(theme_name)

    def display_title_text(self, title):
        """Display the title text on the canvas in place of an image."""
        self.image_canvas.delete("all")  # Clear the canvas
        self.image_canvas.create_text(
            self.image_canvas.winfo_width() / 2,  # Center X
            self.image_canvas.winfo_height() / 2,  # Center Y
            text=title,
            font=("Arial", 24),
            fill="white"
        )

    def show_previous_theme(self):
        """Show the previous theme's image."""
        if not self.themes_list:
            return

        self.current_theme_index = (self.current_theme_index - 1) % len(self.themes_list)
        print(f"Moved to previous theme index: {self.current_theme_index}")  # Debugging output
        self.show_current_theme()

    def show_next_theme(self):
        """Show the next theme's image."""
        if not self.themes_list:
            return

        self.current_theme_index = (self.current_theme_index + 1) % len(self.themes_list)
        print(f"Moved to next theme index: {self.current_theme_index}")  # Debugging output
        self.show_current_theme()

    def update_image_canvas(self, image_path):
        """Update the canvas with the provided image and overlay a logo."""
        # Open the main theme image
        main_image = Image.open(image_path)

        # Get the width of the canvas
        canvas_width = self.image_canvas.winfo_width()

        if canvas_width <= 0:
            print("Warning: Canvas width is not valid.")
            return  # Exit if canvas width is not valid

        # Get the original dimensions of the main image
        original_width, original_height = main_image.size

        if original_width <= 0 or original_height <= 0:
            print("Warning: Original image dimensions are not valid.")
            return  # Exit if original dimensions are not valid

        # Calculate the new dimensions for the main image
        aspect_ratio = original_height / original_width  # Calculate the aspect ratio
        new_width = canvas_width  # Set new width to canvas width
        new_height = int(new_width * aspect_ratio)  # Calculate new height

        # Ensure new dimensions are greater than zero
        if new_height <= 0:
            print("Warning: New image height is not valid after resizing.")
            return  # Exit if new height is not valid

        # Resize the main image
        main_image = main_image.resize((new_width, new_height), Image.Resampling.LANCZOS)  # Updated for Pillow 10+

        # Determine the theme name and construct the logo path
        theme_name, _ = os.path.splitext(os.path.basename(self.themes_list[self.current_theme_index][0]))
        logo_path = os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "logo", f"{theme_name}.png")
        
        if os.path.isfile(logo_path):
            # Load and resize the logo image
            logo_image = Image.open(logo_path)

            # Resize the logo to be smaller than the main image (e.g., 20% of the main image width)
            logo_width = int(new_width * 0.2)
            logo_aspect_ratio = logo_image.size[1] / logo_image.size[0]
            logo_height = int(logo_width * logo_aspect_ratio)
            logo_image = logo_image.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

            # Paste the logo onto the main image (e.g., bottom-right corner with padding)
            position = (new_width - logo_width - 10, new_height - logo_height - 10)  # Adjust padding as needed
            main_image.paste(logo_image, position, logo_image)  # Use transparency of the logo image if it has an alpha channel
        else:
            print(f"Logo not found at: {logo_path}")  # Debugging output

        # Update the PhotoImage with the combined image
        self.current_image = ImageTk.PhotoImage(main_image)

        # Clear the canvas and display the new image
        self.image_canvas.delete("all")
        self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)

    def run_selected_script(self):
        """Run the selected .bat script."""
        if not self.themes_list:
            return

        script_filename, _ = self.themes_list[self.current_theme_index]
        script_path = os.path.join(self.theme_folder, script_filename)

        if not os.path.isfile(script_path):
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return

        try:
            result = subprocess.run(
                ["cmd.exe", "/c", script_path],
                check=True,
                text=True,
                capture_output=True,
                cwd=self.theme_folder
            )
            # Suppressing the success message due to prior feedback
        except subprocess.CalledProcessError as cpe:
            messagebox.showinfo("Info", f"Script ran, but with issues:\nOutput:\n{cpe.output}")
            
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
        
        ## This works for displaying an external wide screen video. Have commented out for now ##
        # Add a canvas for displaying video
        '''self.video_canvas = tk.Canvas(
            self.parent_tab,
            width=400,
            height=300,
            bg="#2B2B2B",               # Set a black background
            highlightthickness=0,     # Remove white outline (default highlight thickness)
            bd=0                      # Set border width to zero
        )
        self.video_canvas.pack(side="right", padx=10, pady=10)
        
        # Add a Preview button at the bottom of the parent tab
        self.preview_button = ctk.CTkButton(
            self.parent_tab,
            text="Preview Video",
            command=self.preview_video  # Link to preview video method
        )
        self.preview_button.pack(side="bottom", pady=10, padx=10)'''

        # Add the Configure button at the bottom of the parent tab
        self.configure_button = ctk.CTkButton(
            self.parent_tab,
            text="Configure",
            command=self.run_selected_script
        )
        self.configure_button.pack(side="bottom", pady=10, padx=10)
    
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
                pass#messagebox.showinfo("Info", f"Script ran, but with issues:\nOutput:\n")
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
