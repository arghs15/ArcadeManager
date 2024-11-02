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
        exe_frame = ctk.CTkFrame(parent_frame, corner_radius=10)
        exe_frame.grid(row=1, column=1, sticky="nswe", padx=10, pady=10)
        
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
            logo_label = ctk.CTkLabel(exe_frame, text="", image=logo_image)
            logo_label.pack(pady=(10, 0))
            
        except Exception as e:
            # Fallback in case loading the image fails
            title_label = ctk.CTkLabel(exe_frame, text="Select Executable", font=("Arial", 14, "bold"))
            title_label.pack(padx=10, pady=10)
            print(f"Error loading logo: {e}")

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
        # Replace the hardcoded settings file with the dynamic one
        settings_file = self.read_settings_file_name()
        self.autochanger_conf_path = os.path.join(self.base_path, "autochanger", settings_file)
        
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
        # Initialize the toggle state dictionary for each button
        self.toggle_state = {
            "genres": False,       # False means unselected, True means selected
            "manufacturer": False,
            "sort_type": False
        }
        
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

        # Create reset button with disabled state by default
        self.reset_button = ctk.CTkButton(
            button_frame,
            text="Reset Playlists",
            fg_color="#D32F2F",
            hover_color="#C62828",
            command=self.reset_playlists,
            state="disabled"  # Start disabled
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
        
        # Set up buttons with modified commands
        self.genres_button = ctk.CTkButton(
            button_frame,
            text="All Genres",
            command=lambda: self.activate_special_playlist("genres", self.get_genre_playlists())
        )
        self.genres_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        
        self.manufacturer_button = ctk.CTkButton(
            button_frame,
            text="All Manufacturer",
            command=lambda: self.activate_special_playlist("manufacturer", self.manufacturer_playlists)
        )
        self.manufacturer_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        self.sort_type_button = ctk.CTkButton(
            button_frame,
            text="All Sort Types",
            command=lambda: self.activate_special_playlist("sort_type", self.sort_type_playlists)
        )
        self.sort_type_button.pack(side="left", expand=True, fill="x", padx=5, pady=5)

        # Check if backup file exists and enable/disable button accordingly
        self.update_reset_button_state()
                        
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

    def read_settings_file_name(self):
        try:
            with open(os.path.join("autochanger", "customisation.txt"), 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("settingsFile ="):
                        settings_value = line.split("=", 1)[1].strip()
                        # Only use the custom value if it's not empty
                        if settings_value:
                            return f"settings{settings_value}.conf"
            # If no settings line found or empty value, use default
            return "settings5_7.conf"
        except FileNotFoundError:
            return "settings5_7.conf"  # Default if file not found
        except Exception as e:
            print(f"An error occurred while reading settings file name: {str(e)}")
            return "settings5_7.conf"  # Default if any error occurs
               
    def update_reset_button_state(self):
        """Check if backup settings file exists and update reset button state"""
        try:
            # Get current settings filename
            current_settings = self.read_settings_file_name()
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
        """Reset the settings by copying the backup settings file (with 'x' suffix) to the current settings file."""
        try:
            # Get the current settings filename being used (e.g., "settings5_2.conf" or "settings5_7.conf")
            current_settings = self.read_settings_file_name()
            
            # Create the backup filename by adding 'x' (e.g., "settings5_2x.conf" or "settings5_7x.conf")
            backup_file = current_settings.replace(".conf", "x.conf")
            
            # Path to the backup configuration file
            backup_conf_path = os.path.join(self.base_path, "autochanger", backup_file)

            # Check if the backup file exists
            if os.path.exists(backup_conf_path):
                # Copy the backup file to replace the current configuration file
                shutil.copy(backup_conf_path, self.autochanger_conf_path)
                messagebox.showinfo("Success", f"Playlists have been reset using {backup_file}")
            else:
                messagebox.showerror("Error", f"Backup configuration file '{backup_file}' not found.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during reset: {str(e)}")
    
    def read_default_playlists(self):
        try:
            with open(os.path.join("autochanger", "customisation.txt"), 'r') as file:
                found_line = False
                for line in file:
                    line = line.strip()
                    if line.startswith("cyclePlaylist ="):
                        found_line = True
                        default_playlists = [item.strip() for item in line.split("=", 1)[1].split(",") if item.strip()]
                        return default_playlists
                # Only return defaults if line wasn't found at all
                if not found_line:
                    return ["arcader", "consoles", "favorites", "lastplayed"]  # Default if line not found
                return []  # Empty list if line was found but empty
        except FileNotFoundError:
            return ["arcader", "consoles", "favorites", "lastplayed"]  # Default if file not found
        except Exception as e:
            print(f"An error occurred while reading default playlists: {str(e)}")
            return []
    
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
            
            with open(self.autochanger_conf_path, 'r') as file:
                lines = file.readlines()

            cycle_playlist_found = False
            first_playlist_found = False

            updated_lines = []
            first_selected_playlist = playlist_list[0] if playlist_list else ""

            for line in lines:
                if line.startswith("cyclePlaylist ="):
                    if default_playlists:
                        new_line = f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n"
                    else:
                        new_line = f"cyclePlaylist = {', '.join(playlist_list)}\n"
                    updated_lines.append(new_line)
                    cycle_playlist_found = True
                elif line.startswith("firstPlaylist ="):
                    if default_playlists:
                        main_default_playlist = default_playlists[0]
                        new_line = f"firstPlaylist = {main_default_playlist}\n"
                    else:
                        new_line = f"firstPlaylist = {first_selected_playlist}\n"
                    updated_lines.append(new_line)
                    first_playlist_found = True
                else:
                    updated_lines.append(line)

            if not cycle_playlist_found:
                if default_playlists:
                    updated_lines.append(f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n")
                else:
                    updated_lines.append(f"cyclePlaylist = {', '.join(playlist_list)}\n")
            if not first_playlist_found:
                if default_playlists:
                    updated_lines.append(f"firstPlaylist = {default_playlists[0]}\n")
                else:
                    updated_lines.append(f"firstPlaylist = {first_selected_playlist}\n")

            with open(self.autochanger_conf_path, 'w') as file:
                file.writelines(updated_lines)

            messagebox.showinfo("Success", f"Updated Playlist(s): {', '.join(playlist_list)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

'''import os
import cv2
import time
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
from collections import deque
from threading import Thread, Lock, Event
import queue

class RateLimiter:
    def __init__(self, min_interval=0.3):
        self.min_interval = min_interval
        self.last_call = 0
        self.lock = Lock()
        
    def can_proceed(self):
        with self.lock:
            current_time = time.time()
            if current_time - self.last_call >= self.min_interval:
                self.last_call = current_time
                return True
            return False

class VideoManager:
    def __init__(self, video_path, max_frames_cache=30):
        self.video_path = video_path
        self.max_frames_cache = max_frames_cache
        self.frames_cache = deque(maxlen=max_frames_cache)
        self.cap = None
        self.current_frame_index = 0
        self.total_frames = 0
        self.lock = Lock()
        self.is_loading = False
        self.stop_event = Event()
        
        # Initialize video capture in a safe way
        self._safe_init_capture()
        
    def _safe_init_capture(self):
        """Safely initialize video capture"""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            else:
                raise Exception("Failed to open video file")
        except Exception as e:
            print(f"Error initializing video capture: {e}")
            self.cap = None
            
    def preload_frames(self):
        """Preload frames in background"""
        if self.is_loading or self.cap is None:
            return
            
        self.is_loading = True
        try:
            with self.lock:
                while len(self.frames_cache) < self.max_frames_cache and not self.stop_event.is_set():
                    if self.cap is None or not self.cap.isOpened():
                        break
                        
                    ret, frame = self.cap.read()
                    if ret:
                        self.frames_cache.append(frame)
                    else:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        break
        except Exception as e:
            print(f"Error preloading frames: {e}")
        finally:
            self.is_loading = False
            
    def get_frame(self):
        """Get next frame from cache or video"""
        try:
            with self.lock:
                if self.frames_cache:
                    frame = self.frames_cache.popleft()
                    self.current_frame_index += 1
                    # Trigger preload if cache is getting low
                    if len(self.frames_cache) < self.max_frames_cache // 2:
                        Thread(target=self.preload_frames, daemon=True).start()
                    return frame
        except Exception as e:
            print(f"Error getting frame: {e}")
        return None
            
    def release(self):
        """Release resources"""
        self.stop_event.set()
        with self.lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception as e:
                    print(f"Error releasing video capture: {e}")
                self.cap = None
            self.frames_cache.clear()

class Themes:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        
        # Configuration paths
        self.theme_folder = os.path.join(self.base_path, "collections", "zzzSettings", "roms")
        self.video_folder = os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "video")
        
        # State management
        self.themes_list = []
        self.current_theme_index = 0
        self.video_manager = None
        self.is_playing = False
        self.default_size = (640, 480)
        
        # Rate limiter for theme switching
        self.rate_limiter = RateLimiter()
        
        # Video state management
        self.next_video_manager = None
        self.prev_video_manager = None
        self.preload_lock = Lock()
        self.switch_lock = Lock()
        
        self._setup_ui()
        self.parent_tab.after(100, self.load_themes)
        
    def _setup_ui(self):
        """Initialize and configure UI components"""
        # Main display frame
        self.display_frame = ctk.CTkFrame(self.parent_tab)
        self.display_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Video display
        self.video_canvas = ctk.CTkCanvas(
            self.display_frame,
            width=self.default_size[0],
            height=self.default_size[1]
        )
        self.video_canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Bind resize event
        self.video_canvas.bind('<Configure>', self._on_resize)
        
        # Theme name label with loading indicator
        self.status_frame = ctk.CTkFrame(self.display_frame)
        self.status_frame.pack(fill="x", pady=5)
        
        self.theme_label = ctk.CTkLabel(self.status_frame, text="")
        self.theme_label.pack(side="left", padx=5)
        
        self.loading_label = ctk.CTkLabel(self.status_frame, text="")
        self.loading_label.pack(side="right", padx=5)
        
        # Button frame
        self.button_frame = ctk.CTkFrame(self.display_frame)
        self.button_frame.pack(fill="x", padx=5, pady=5)
        
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
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
                border_width=0,
                corner_radius=0
            )
            btn.grid(row=0, column=col, sticky="ew", padx=5, pady=5)

    def _preload_adjacent_videos(self):
        """Preload next and previous videos in background"""
        if not self.themes_list:
            return
            
        def preload_video(index):
            if 0 <= index < len(self.themes_list):
                _, video_path = self.themes_list[index]
                if video_path and os.path.isfile(video_path):
                    return VideoManager(video_path)
            return None

        with self.preload_lock:
            next_idx = (self.current_theme_index + 1) % len(self.themes_list)
            prev_idx = (self.current_theme_index - 1) % len(self.themes_list)
            
            # Preload next video
            if self.next_video_manager is None:
                self.next_video_manager = preload_video(next_idx)
                if self.next_video_manager:
                    Thread(target=self.next_video_manager.preload_frames, daemon=True).start()
            
            # Preload previous video
            if self.prev_video_manager is None:
                self.prev_video_manager = preload_video(prev_idx)
                if self.prev_video_manager:
                    Thread(target=self.prev_video_manager.preload_frames, daemon=True).start()

    def _display_frame(self, frame):
        """Display a frame on the canvas with proper scaling"""
        if frame is None:
            return
            
        try:
            # Get current display size
            canvas_width, canvas_height = self._get_display_size()
            
            # Get frame dimensions
            height, width = frame.shape[:2]
            
            # Calculate scaling
            scale = min(canvas_width/width, canvas_height/height)
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            
            # Resize frame
            frame = cv2.resize(frame, (new_width, new_height))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PhotoImage
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=image)
            
            # Clear canvas and display new frame
            self.video_canvas.delete("all")
            self.video_canvas.create_image(
                canvas_width//2, canvas_height//2,
                image=photo, anchor="center"
            )
            self.video_canvas.image = photo
            
        except Exception as e:
            print(f"Error displaying frame: {e}")

    def show_current_theme(self):
        """Display the current theme's video and update UI"""
        if not self.themes_list:
            return

        try:
            # Ensure clean state before switching
            self._cleanup_video()
            
            theme_name, video_path = self.themes_list[self.current_theme_index]
            display_name = os.path.splitext(theme_name)[0]
            self.theme_label.configure(text=f"Theme: {display_name}")

            if video_path and os.path.isfile(video_path):
                # Use preloaded video manager if available
                if self.next_video_manager and self.next_video_manager.video_path == video_path:
                    self.video_manager = self.next_video_manager
                    self.next_video_manager = None
                elif self.prev_video_manager and self.prev_video_manager.video_path == video_path:
                    self.video_manager = self.prev_video_manager
                    self.prev_video_manager = None
                else:
                    self.video_manager = VideoManager(video_path)
                
                if self.video_manager and self.video_manager.cap and self.video_manager.cap.isOpened():
                    self.is_playing = True
                    Thread(target=self.video_manager.preload_frames, daemon=True).start()
                    self.play_video()
                    
                    # Start preloading adjacent videos
                    Thread(target=self._preload_adjacent_videos, daemon=True).start()
                else:
                    self._show_no_video_message()
            else:
                self._show_no_video_message()
                
        except Exception as e:
            print(f"Error showing theme: {e}")
            self._show_error_message()

    def play_video(self):
        """Play video frame by frame with error handling"""
        if not self.is_playing or self.video_manager is None:
            return
            
        try:
            frame = self.video_manager.get_frame()
            
            if frame is not None:
                self._display_frame(frame)
                self.parent_tab.after(33, self.play_video)
            else:
                # Reset video when it ends
                if self.video_manager and self.video_manager.cap:
                    self.video_manager.current_frame_index = 0
                    Thread(target=self.video_manager.preload_frames, daemon=True).start()
                    self.play_video()
                    
        except Exception as e:
            print(f"Error during video playback: {e}")
            self._cleanup_video()
            self._show_error_message()

    def _cleanup_video(self):
        """Clean up video resources with error handling"""
        self.is_playing = False
        
        try:
            # Clean up current video
            if self.video_manager:
                self.video_manager.release()
                self.video_manager = None
            
            # Clean up preloaded videos
            if self.next_video_manager:
                self.next_video_manager.release()
                self.next_video_manager = None
            
            if self.prev_video_manager:
                self.prev_video_manager.release()
                self.prev_video_manager = None
                
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def _on_resize(self, event):
        """Handle window resize events"""
        if hasattr(self, 'current_frame'):
            self._display_frame(self.current_frame)

    def _get_display_size(self):
        """Get the current display size or return default size"""
        try:
            width = self.video_canvas.winfo_width()
            height = self.video_canvas.winfo_height()
            if width > 1 and height > 1:  # Ensure valid size
                return width, height
        except:
            pass
        return self.default_size

    def load_themes(self):
        """Load .bat files and their corresponding videos"""
        if not os.path.isdir(self.theme_folder):
            messagebox.showerror("Error", f"Theme folder not found: {self.theme_folder}")
            return

        self.themes_list = []
        
        for filename in os.listdir(self.theme_folder):
            if filename.endswith(".bat"):
                theme_name = os.path.splitext(filename)[0]
                video_path = os.path.join(self.video_folder, f"{theme_name}.mp4")
                
                theme_entry = (filename, video_path if os.path.isfile(video_path) else None)
                self.themes_list.append(theme_entry)
        
        if not self.themes_list:
            messagebox.showwarning("Warning", "No themes found.")
            return
            
        self.show_current_theme()

    def show_previous_theme(self):
        """Navigate to previous theme with rate limiting"""
        if not self.rate_limiter.can_proceed():
            return
            
        if self.themes_list:
            with self.switch_lock:
                self.current_theme_index = (self.current_theme_index - 1) % len(self.themes_list)
                self.show_current_theme()

    def show_next_theme(self):
        """Navigate to next theme with rate limiting"""
        if not self.rate_limiter.can_proceed():
            return
            
        if self.themes_list:
            with self.switch_lock:
                self.current_theme_index = (self.current_theme_index + 1) % len(self.themes_list)
                self.show_current_theme()

    def run_selected_script(self):
        """Execute the selected theme script"""
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
            messagebox.showinfo("Success", "Theme applied successfully!")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to apply theme:\n{e.output}")
    
    def _show_error_message(self):
        """Display error message on canvas"""
        try:
            self.video_canvas.delete("all")
            width, height = self._get_display_size()
            self.video_canvas.create_text(
                width // 2,
                height // 2,
                text="Error playing video",
                fill="red",
                font=("Arial", 12)
            )
        except Exception as e:
            print(f"Error showing error message: {e}")
            '''

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
                # Read PNG file directly using cv2
                image = cv2.imread(self.image_path)
                if image is not None:
                    return image
            except Exception as e:
                print(f"Error loading PNG: {e}")
                
        return None

    def start_video(self):
        """Start video playback"""
        with self.lock:
            if not self.is_playing:
                self.video_cap = cv2.VideoCapture(self.video_path)
                self.is_playing = True

    def stop_video(self):
        """Stop video playback"""
        with self.lock:
            self.is_playing = False
            if self.video_cap:
                self.video_cap.release()
                self.video_cap = None

    def get_frame(self):
        """Get next video frame if playing"""
        if not self.is_playing or not self.video_cap:
            return None
            
        ret, frame = self.video_cap.read()
        if ret:
            return frame
        else:
            # Reset video to start
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return None

class Themes:
    def __init__(self, parent_tab):
        print("Initializing Themes...")  # Debug print
        self.parent_tab = parent_tab
        self.base_path = os.getcwd()
        
        # Configuration paths
        self.theme_folder = os.path.join(self.base_path, "collections", "zzzSettings", "roms")
        self.video_folder = os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "video")
        
        # State management
        self.themes_list = []
        self.current_theme_index = 0
        self.current_viewer = None
        self.default_size = (640, 480)
        self.thumbnail_cache = {}
        self.current_frame = None  # Store current frame for resize events
        
        self._setup_ui()
        # Schedule theme loading after UI is fully initialized
        self.parent_tab.after(100, self.delayed_load_themes)
            
    def delayed_load_themes(self):
        """Load themes after ensuring UI is ready"""
        print("Loading themes...")  # Debug print
        self.load_themes()
        # Schedule initial theme display
        self.parent_tab.after(100, self.force_initial_display)

    def force_initial_display(self):
        """Force the initial theme display"""
        print("Forcing initial display...")  # Debug print
        if self.themes_list:
            self.parent_tab.update_idletasks()
            self.show_initial_theme()

    def show_initial_theme(self):
        """Special handling for the first theme display"""
        print("Showing initial theme...")  # Debug print
        if not self.themes_list:
            return

        theme_name, video_path, png_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Initialize viewer
        self.current_viewer = ThemeViewer(video_path, png_path)
        self.play_button.configure(state="normal" if video_path else "disabled")

        # Force immediate thumbnail extraction and display
        thumbnail = self.current_viewer.extract_thumbnail()
        if thumbnail is not None:
            print("Thumbnail extracted, displaying...")  # Debug print
            cache_key = video_path or png_path
            if cache_key:
                self.thumbnail_cache[cache_key] = thumbnail
            
            # Force canvas update and display
            self.parent_tab.update_idletasks()
            self._display_frame(thumbnail)
        else:
            print("No thumbnail available...")  # Debug print
            self._show_no_video_message()

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
        """Display the current theme's thumbnail"""
        print("Showing current theme...")  # Debug print
        if not self.themes_list:
            return

        # Stop any playing video
        if self.current_viewer and self.current_viewer.is_playing:
            self.current_viewer.stop_video()
            self.play_button.configure(text="Play Video")

        theme_name, video_path, png_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Create viewer with both video and image paths
        self.current_viewer = ThemeViewer(video_path, png_path)
        self.play_button.configure(state="normal" if video_path else "disabled")
        
        # Force immediate thumbnail display
        self.show_thumbnail()

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
        """Display a frame or thumbnail on the canvas with logo overlay"""
        try:
            # Store the current frame for resize events
            if not force_resize:
                self.current_frame = frame.copy()
            
            # Get current display size
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width < 1 or canvas_height < 1:
                canvas_width, canvas_height = self.default_size
            
            # Get frame dimensions
            height, width = frame.shape[:2]
            
            # Calculate scaling while maintaining aspect ratio
            scale = min(canvas_width/width, canvas_height/height)
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            
            # Resize frame
            frame = cv2.resize(frame, (new_width, new_height))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert main frame to PIL Image
            main_image = Image.fromarray(frame)
            
            # Try to load and overlay the logo
            try:
                # Get current theme name
                current_theme = os.path.splitext(self.themes_list[self.current_theme_index][0])[0]
                logo_path = os.path.join(self.base_path, "collections", "zzzSettings", "medium_artwork", "logo", f"{current_theme}.png")
                
                if os.path.exists(logo_path):
                    # Load and resize logo
                    logo_img = Image.open(logo_path)
                    
                    # Calculate logo size (e.g., 20% of frame width)
                    logo_max_size = min(new_width, new_height) // 3
                    logo_w, logo_h = logo_img.size
                    logo_scale = min(logo_max_size/logo_w, logo_max_size/logo_h)
                    logo_new_size = (int(logo_w * logo_scale), int(logo_h * logo_scale))
                    logo_img = logo_img.resize(logo_new_size, Image.Resampling.LANCZOS)
                    
                    # Calculate position (bottom right with padding)
                    padding = 10  # pixels from edge
                    pos_x = new_width - logo_new_size[0] - padding
                    pos_y = new_height - logo_new_size[1] - padding
                    
                    # Paste logo onto main image
                    if logo_img.mode == 'RGBA':
                        main_image.paste(logo_img, (pos_x, pos_y), logo_img)
                    else:
                        main_image.paste(logo_img, (pos_x, pos_y))
            except Exception as e:
                print(f"Error loading or applying logo: {e}")
                # Continue without logo if there's an error
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image=main_image)
            
            # Clear canvas
            self.video_canvas.delete("all")
            
            # Calculate centered position
            x = canvas_width // 2
            y = canvas_height // 2
            
            # Display image centered
            self.video_canvas.create_image(
                x, y,
                image=photo,
                anchor="center"
            )
            self.video_canvas.image = photo
            
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
        self.status_frame.pack(fill="x", pady=5)
        
        self.theme_label = ctk.CTkLabel(self.status_frame, text="")
        self.theme_label.pack(side="left", padx=5)
        
        # Play/Stop button
        self.play_button = ctk.CTkButton(
            self.status_frame,
            text="Play Video",
            command=self.toggle_video,
            width=100
        )
        self.play_button.pack(side="right", padx=5)
        
        # Navigation frame
        self.button_frame = ctk.CTkFrame(self.display_frame)
        self.button_frame.pack(fill="x", padx=5, pady=5)
        
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
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
                border_width=0,
                corner_radius=0
            )
            btn.grid(row=0, column=col, sticky="ew", padx=5, pady=5)

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
            self.current_viewer.start_video()
            self.play_button.configure(text="Stop Video")
            self.play_video()
        else:
            # Stop video and show thumbnail
            self.current_viewer.stop_video()
            self.play_button.configure(text="Play Video")
            self.show_thumbnail()

    def initialize_first_theme(self):
        """Initialize and display the first theme"""
        if not self.themes_list:
            return
            
        theme_name, video_path = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        if video_path and os.path.isfile(video_path):
            self.current_viewer = ThemeViewer(video_path)
            # Force canvas update before showing thumbnail
            self.video_canvas.update()
            self.show_thumbnail()
        else:
            self.current_viewer = None
            self._show_no_video_message()

    def play_video(self):
        """Play video if it's active"""
        if not self.current_viewer or not self.current_viewer.is_playing:
            return
            
        frame = self.current_viewer.get_frame()
        if frame is not None:
            self._display_frame(frame)
            self.parent_tab.after(33, self.play_video)
        else:
            # Restart video
            self.play_video()

    def _show_no_video_message(self):
        """Display message when no video is available"""
        self.video_canvas.delete("all")
        self.video_canvas.create_text(
            self.video_canvas.winfo_width() // 2,
            self.video_canvas.winfo_height() // 2,
            text="No video available",
            fill="white"
        )

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

    def run_selected_script(self):
        """Execute the selected theme script."""
        if not self.themes_list:
            print("No themes found in themes_list. Exiting function.")
            return

        # Get the script path
        script_filename, _, _ = self.themes_list[self.current_theme_index]
        script_path = os.path.join(self.theme_folder, script_filename)

        # Print the selected theme information for debugging
        print(f"Selected script: {script_filename}")
        print(f"Full script path: {script_path}")

        # Check if the script file exists
        print(f"Checking if script exists at path: {script_path}")
        if not os.path.isfile(script_path):
            print(f"Script not found: {script_path}")  # Log the error instead of showing it
            return

        try:
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

        except subprocess.CalledProcessError as e:
            print(f"Subprocess error (CalledProcessError): {e}")
            print(f"Return code: {e.returncode}")
            print(f"Standard output: {e.stdout}")
            print(f"Error output: {e.stderr}")
        except Exception as e:
            # Log the error without showing it in the GUI
            print(f"Unexpected error while running script: {str(e)}")

        # Always confirm completion to the user
        messagebox.showinfo("Success", "Theme applied successfully!")


            
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
