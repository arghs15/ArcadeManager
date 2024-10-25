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

class FilterGamesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arcade Manager")
        self.root.geometry("1920x1080")  # Set the initial size (you can adjust as needed)
        self.root.resizable(True, True)  # Enable window resizing

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

import fileinput

class Playlists:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        self.playlists_path = os.path.join(self.base_path, "collections", "Arcades", "playlists")
        self.excluded_playlists = ["ctrltype", "manufacturer", "genres"]
        self.autochanger_conf_path = os.path.join(self.base_path, "autochanger", "settings5_7.conf")

        self.check_vars = []
        self.check_buttons = []

        # Create a frame for the scrollable checkbox area
        self.scrollable_frame = ctk.CTkFrame(self.parent_tab, corner_radius=10)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.scrollable_checklist = ctk.CTkScrollableFrame(self.scrollable_frame, width=400, height=400)
        self.scrollable_checklist.pack(fill="both", expand=True, padx=10, pady=10)

        # Populate checkboxes based on available playlist files
        self.populate_checkboxes()

        # Create the Create Playlist button
        self.create_playlist_button = ctk.CTkButton(
            self.parent_tab,
            text="Create Playlist",
            command=self.create_playlist,
            fg_color="#4CAF50",
            hover_color="#45A049"
        )
        self.create_playlist_button.pack(side="bottom", pady=10, padx=10)

        # Add additional buttons
        button_frame = ctk.CTkFrame(self.parent_tab)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.ctrltype_button = ctk.CTkButton(
            button_frame,
            text="Control Types",
            command=lambda: self.activate_special_playlist("ctrltype")
        )
        self.ctrltype_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        self.manufacturer_button = ctk.CTkButton(
            button_frame,
            text="Manufacturer",
            command=lambda: self.activate_special_playlist("manufacturer")
        )
        self.manufacturer_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        self.genres_button = ctk.CTkButton(
            button_frame,
            text="Genres",
            command=lambda: self.activate_special_playlist("genres")
        )
        self.genres_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        '''self.reset_button = ctk.CTkButton(
            button_frame,
            text="Reset Playlists",
            fg_color="#D32F2F",
            hover_color="#C62828",
            command=self.reset_playlists
        )
        self.reset_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        '''
        
    def populate_checkboxes(self):
        try:
            for playlist_file in os.listdir(self.playlists_path):
                playlist_name, ext = os.path.splitext(playlist_file)
                if ext == ".txt" and playlist_name.lower() not in self.excluded_playlists:
                    var = tk.BooleanVar()
                    checkbutton = ctk.CTkCheckBox(
                        self.scrollable_checklist,
                        text=playlist_name,
                        variable=var
                    )
                    checkbutton.pack(anchor="w", padx=10, pady=5)
                    self.check_vars.append((playlist_name, var))
        except FileNotFoundError:
            print(f"Playlists folder not found at: {self.playlists_path}")

    def create_playlist(self):
        selected_playlists = [name for name, var in self.check_vars if var.get()]
        self.update_conf_file(selected_playlists)

    def activate_special_playlist(self, playlist_type):
        self.update_conf_file([playlist_type])

    def reset_playlists(self):
        default_playlists = [
            "arcader", "consoles", "favorites", "lastplayed", "old school", "beat em ups",
            "run n gun", "fight club", "shoot em ups", "racer", "sports", "puzzler"
        ]
        self.update_conf_file(default_playlists)

    def update_conf_file(self, playlist_list):
        try:
            with open(self.autochanger_conf_path, 'r') as file:
                lines = file.readlines()

            cycle_playlist_found = False
            first_playlist_found = False

            updated_lines = []
            first_selected_playlist = playlist_list[0] if playlist_list else "default_playlist"

            for line in lines:
                if line.startswith("cyclePlaylist ="):
                    new_line = f"cyclePlaylist = {', '.join(playlist_list)}\n"
                    updated_lines.append(new_line)
                    cycle_playlist_found = True
                elif line.startswith("firstPlaylist ="):
                    new_line = f"firstPlaylist = {first_selected_playlist}\n"
                    updated_lines.append(new_line)
                    first_playlist_found = True
                else:
                    updated_lines.append(line)

            if not cycle_playlist_found:
                updated_lines.append(f"cyclePlaylist = {', '.join(playlist_list)}\n")
            if not first_playlist_found:
                updated_lines.append(f"firstPlaylist = {first_selected_playlist}\n")

            with open(self.autochanger_conf_path, 'w') as file:
                file.writelines(updated_lines)

            messagebox.showinfo("Success", f"Updated Playlist(s): {', '.join(playlist_list)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")


class AdvancedConfigs:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        self.config_folders = ["- Advanced Configs", "- Themes", "- Themes 2nd Screen", "- Bezels Glass & Scanlines"]
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
            "- Bezels Glass & Scanlines": "Bezels & Effects"
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
                messagebox.showinfo("Success", f"'{script_to_run}' executed successfully.\nOutput:\n{result.stdout}")
            except subprocess.CalledProcessError as e:
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
