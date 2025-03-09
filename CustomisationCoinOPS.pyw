import builtins
import os
import platform
import random
import sys
import csv
import re
import subprocess
import tkinter as tk
from tkinter import PhotoImage, messagebox, filedialog, Canvas
from tkinter import ttk
import traceback
from PIL import Image, ImageTk
import customtkinter as ctk
import time
import ctypes
import shutil
import cv2
from threading import Thread, Lock
import threading
import queue
import configparser
import tkinter.font as tkFont
import json
import asyncio
import keyboard
from inputs import get_gamepad, devices
import fnmatch
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import queue
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import psutil
import builtins
from datetime import datetime
from ctypes import wintypes

# Global debug flag - set to False for production, True for debugging
DEBUG_MODE = False

def disable_logging():
    def null_print(*args, **kwargs): pass
    null_print._disabled = True
    builtins.print = null_print
    sys.stdout = type('NullWriter', (), {'write': lambda s,t: None, 'flush': lambda s: None})()

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip timing measurements if not in debug mode
        if not DEBUG_MODE:
            return func(*args, **kwargs)
        
        # Only perform timing if in debug mode
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # Memory in MB
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        duration = end_time - start_time
        memory_used = memory_after - memory_before
        
        message = f"[TIMING] {func.__name__} took {duration:.3f} seconds | Memory change: {memory_used:.1f}MB"
        print(message)
        
        # Only attempt to store timing data if we have an instance
        if args and len(args) > 0:
            instance = args[0]
            if hasattr(instance, 'timing_data'):
                instance.timing_data.append({
                    "function": func.__name__,
                    "duration": duration,
                    "memory_change": memory_used,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                })
            if hasattr(instance, 'timing_messages'):
                instance.timing_messages.append(message)
                
        return result
    return wrapper

# Early initialization - check config to disable logging if needed
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autochanger", "customisation.ini")
if os.path.exists(config_path):
    config.read(config_path)
    if not config.get('Settings', 'log_level', fallback='ALL').upper() == 'ALL':
        disable_logging()

# Check if the script is running in a bundled environment
if not getattr(sys, 'frozen', False):
    # Change the working directory to the directory where the script is located
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

class PathManager:
    # Initialize the class attribute to store our cached path
    _cached_base_path = None

    @staticmethod
    def get_parent_directory(path):
        # Get the parent directory of a given path
        return os.path.dirname(os.path.dirname(path))

    @staticmethod
    def get_directory(path):
        # Get the directory of a given path
        return os.path.dirname(path)

    @staticmethod
    def get_base_path():
        # Check if we've already cached the base path
        if PathManager._cached_base_path is not None:
            return PathManager._cached_base_path
        
        # Calculate the base path if not cached
        if sys.platform == 'win32':
            # Windows implementation...
            hModule = ctypes.windll.kernel32.GetModuleHandleW(None)
            exe = ctypes.create_unicode_buffer(260)  # MAX_PATH
            ctypes.windll.kernel32.GetModuleFileNameW(hModule, exe, 260)
            base_path = PathManager.get_directory(exe.value)
            
        elif sys.platform == 'darwin':
            # macOS implementation...
            exepath = psutil.Process(os.getpid()).exe()
            sPath = PathManager.get_directory(exepath)
            rootPos = sPath.find("/Customisation.app/Contents/MacOS")
            if rootPos != -1:
                sPath = sPath[:rootPos]
            base_path = sPath
            
        else:
            # Linux implementation...
            exepath = f"/proc/{os.getpid()}/exe"
            try:
                realpath = os.readlink(exepath)
                base_path = PathManager.get_directory(realpath)
            except OSError:
                print(f"Error reading the executable path: {exepath}")
                base_path = None
        
        # Cache the result in the class attribute
        PathManager._cached_base_path = base_path
        return base_path

    @staticmethod
    def get_resource_path(relative_path):
        """Get absolute path to resource, works for dev and PyInstaller"""
        return os.path.join(PathManager.get_base_path(), relative_path)

class LogManager:
    def __init__(self, config_manager=None):
        self.original_print = builtins.print
        self.log_enabled = True  # Default to enabled
        self.log_level = "ALL"   # Default to all logging
        self.config_manager = config_manager
        
        # Initialize based on config if provided
        if config_manager:
            self.update_from_config()

    def update_from_config(self):
        """Update logging settings from config"""
        try:
            # Get logging settings from config
            self.log_level = self.config_manager.get_setting('Settings', 'log_level', 'ALL').upper()
            print(f"Log level set to: {self.log_level}")  # Debug print
        except Exception as e:
            print(f"Error updating log config: {e}")  # More specific error handling
            self.log_level = "ALL"

    def write_error_details(self, f, timestamp, error):
        """Write detailed error information to log file"""
        if not self.log_enabled or self.log_level == "NONE":
            return
            
        f.write(f"[{timestamp}] [ERROR] Error message: {str(error)}\n")
        f.write(f"[{timestamp}] [ERROR] Error type: {type(error).__name__}\n")
        f.write(f"[{timestamp}] [ERROR] Stack trace:\n")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                f.write(f"[{timestamp}] [ERROR] {line}\n")
        f.write(f"[{timestamp}] [ERROR] ------------------\n")

    def should_log_level(self, level):
        """Determine if this log level should be logged based on settings"""
        if self.log_level == "NONE":
            return False
                
        if self.log_level == "ALL":
            return True
                
        # Define app log level hierarchy (higher number = more severe)
        app_level_hierarchy = {
            "DEBUG": 0,
            "INFO": 1,
            "WARNING": 2,
            "ERROR": 3,
            "CRITICAL": 4,
            "NONE": 5
        }
        
        # Get numeric values for comparison
        try:
            current_level = app_level_hierarchy.get(self.log_level, 0)  # Default to DEBUG if unknown
            msg_level = app_level_hierarchy.get(level, 0)  # Default to DEBUG if unknown
            
            # Higher or equal level messages should be logged
            return msg_level >= current_level

        except Exception as e:
            print(f"Error checking log level: {e}")
            return True  # Default to logging on error

    def get_current_exe_log_level(self):
        """Get current log level from settings.conf"""
        try:
            settings_conf_path = os.path.join(self.config_manager.base_path, "settings.conf")
            if os.path.exists(settings_conf_path):
                with open(settings_conf_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.lower().startswith('log='):
                            return line.strip().split('=')[1].upper()  # Normalize case
            return "ALL"  # Default if not found
        except Exception as e:
            print(f"Error reading executable log level: {e}")
            return "ALL"
    
    def update_app_logging_setting(self, setting, value):
        """Update application logging setting"""
        try:
            self.config_manager.set_setting('Settings', setting, value)
            self.log_level = value  # Update current instance
            print(f"Application log level updated to: {value}")
        except Exception as e:
            print(f"Error updating application log setting: {e}")

    def update_exe_logging_setting(self, value):
        """Update executable logging setting"""
        try:
            settings_conf_path = os.path.join(self.config_manager.base_path, "settings.conf")
            if os.path.exists(settings_conf_path):
                # Read current settings
                with open(settings_conf_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Find and update Log= line
                log_line_found = False
                for i, line in enumerate(lines):
                    if line.startswith('log='):
                        lines[i] = f'log={value}\n'
                        log_line_found = True
                        break
                
                # Add Log= line if not found
                if not log_line_found:
                    lines.append(f'Log={value}\n')
                
                # Write back to file
                with open(settings_conf_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                print(f"CoinOPS log level updated to: {value}")
        except Exception as e:
            print(f"Error updating CoinOPS log setting: {e}")

    def custom_print(self, *args, **kwargs):
        # Always do original print if it's not a log-only message
        if not kwargs.pop('log_only', False):
            self.original_print(*args, **kwargs)
        
        if not self.log_enabled or self.log_level == "NONE":
            return
            
        message = " ".join(str(arg) for arg in args)
        try:
            log_file = os.path.join(PathManager.get_base_path(), "autochanger", "application.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Don't modify if message already has timestamp and level
                if "[20" in message and any(f"] [{level}]" in message for level in ["INFO", "ERROR", "WARNING", "DEBUG", "CRITICAL"]):
                    if self.should_log_level(message.split('] [')[1].split(']')[0]):
                        f.write(f"{message}\n")
                    return
                
                # Determine message level
                level = "INFO"  # default
                msg_lower = message.lower()
                
                if any(err in msg_lower for err in ["error", "exception", "failed", "could not"]):
                    level = "ERROR"
                elif any(warn in msg_lower for warn in ["warning", "warn", "deprecated"]):
                    level = "WARNING"
                elif any(crit in msg_lower for crit in ["critical", "fatal", "crash"]):
                    level = "CRITICAL"
                elif any(debug in msg_lower for debug in ["debug", "trace", "diagnostic"]):
                    level = "DEBUG"
                
                if self.should_log_level(level):
                    f.write(f"[{timestamp}] [{level}] {message}\n")
                    
        except Exception as e:
            self.original_print(f"Error writing to log: {e}")

def initialize_logging(config_manager=None):
    """Initialize the logging system"""
    log_manager = LogManager(config_manager)
    builtins.print = log_manager.custom_print
    return log_manager

# Check if the script is running in a bundled environment
if not getattr(sys, 'frozen', False):
    # Change the working directory to the directory where the script is located
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

class CreateToolTip:
    """
    Create a tooltip for a given customtkinter widget with improved reliability
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.hide_id = None
        
        # Bind to the CTk button's internal label widget
        if hasattr(self.widget, '_text_label'):
            self.widget._text_label.bind('<Enter>', self.enter)
            self.widget._text_label.bind('<Leave>', self.leave)
            
        # Also bind to the button itself
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.hide)  # Hide on click
        
        # Bind to the root window focus changes
        try:
            root = self.get_root()
            if root:
                root.bind('<FocusOut>', lambda e: self.hide())
                root.bind('<Configure>', lambda e: self.check_position())
        except:
            pass
            
        self.id = None
        self.tw = None
        
        # Automatic cleanup after 3 seconds as failsafe
        self.auto_hide_id = None

    def get_root(self):
        """Get the root window of this widget"""
        widget = self.widget
        while widget.master:
            widget = widget.master
        return widget

    def enter(self, event=None):
        """Schedule showing the tooltip"""
        # Cancel any pending hide operation
        if self.hide_id:
            try:
                self.widget.after_cancel(self.hide_id)
                self.hide_id = None
            except:
                pass
        
        self.schedule()

    def leave(self, event=None):
        """Schedule hiding the tooltip with a small delay"""
        self.unschedule()
        # Use a short delay before hiding to prevent flickering
        # when moving between button and text label
        self.hide_id = self.widget.after(100, self.hide)

    def schedule(self):
        """Schedule showing of tooltip"""
        self.unschedule()
        self.id = self.widget.after(500, self.show)

    def unschedule(self):
        """Unschedule showing of tooltip"""
        id_ = self.id
        self.id = None
        if id_:
            try:
                self.widget.after_cancel(id_)
            except:
                pass

    def show(self):
        """Show the tooltip"""
        # Don't show if a tooltip is already visible
        if self.tw:
            return
            
        try:
            # Get widget position
            x = self.widget.winfo_rootx() + self.widget.winfo_width()//2
            y = self.widget.winfo_rooty() + self.widget.winfo_height()

            # Creates a toplevel window
            self.tw = tk.Toplevel(self.widget)
            # Remove the window decorations
            self.tw.wm_overrideredirect(True)
            
            # Create tooltip content with dark theme
            frame = tk.Frame(self.tw, background="#2B2B2B", borderwidth=1, relief="solid")
            frame.pack(ipadx=5, ipady=2)
            
            label = tk.Label(frame, 
                            text=self.text,
                            justify='left',
                            background="#2B2B2B",
                            foreground="white",
                            wraplength=250,
                            font=("Arial", "10", "normal"))
            label.pack(padx=3, pady=2)

            # Position tooltip centered below the button
            tw_width = label.winfo_reqwidth() + 10  # Add padding
            tw_height = label.winfo_reqheight() + 6  # Add padding
            
            x = x - tw_width//2  # Center horizontally
            y = y + 5  # Add small gap below button
            
            # Adjust if tooltip would go off screen
            screen_width = self.widget.winfo_screenwidth()
            screen_height = self.widget.winfo_screenheight()
            
            if x < 0:
                x = 0
            elif x + tw_width > screen_width:
                x = screen_width - tw_width
                
            if y + tw_height > screen_height:
                y = self.widget.winfo_rooty() - tw_height - 5  # Show above widget
            
            self.tw.wm_geometry(f"+{x}+{y}")
            
            # Raise tooltip above other windows
            self.tw.lift()
            self.tw.attributes('-topmost', True)
            
            # Set auto-hide as a failsafe
            self.auto_hide_id = self.widget.after(3000, self.hide)
            
        except Exception as e:
            print(f"Error showing tooltip: {e}")
            self.hide()

    def check_position(self):
        """Check if mouse is still over widget, hide if not"""
        if not self.tw:
            return
            
        try:
            # Get current mouse position
            root = self.get_root()
            mouse_x = root.winfo_pointerx()
            mouse_y = root.winfo_pointery()
            
            # Get widget position
            widget_x1 = self.widget.winfo_rootx()
            widget_y1 = self.widget.winfo_rooty()
            widget_x2 = widget_x1 + self.widget.winfo_width()
            widget_y2 = widget_y1 + self.widget.winfo_height()
            
            # Hide tooltip if mouse is outside widget (with a small margin)
            if (mouse_x < widget_x1 - 5 or mouse_x > widget_x2 + 5 or
                mouse_y < widget_y1 - 5 or mouse_y > widget_y2 + 5):
                self.hide()
        except:
            # If any error occurs, hide the tooltip
            self.hide()

    def hide(self, event=None):
        """Hide the tooltip"""
        # Cancel any auto-hide timer
        if self.auto_hide_id:
            try:
                self.widget.after_cancel(self.auto_hide_id)
                self.auto_hide_id = None
            except:
                pass
                
        # Destroy tooltip window
        tw = self.tw
        self.tw = None
        if tw:
            try:
                tw.destroy()
            except:
                pass

class SplashScreen:
    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Store parent reference for force closing
        self.parent = parent
        
        # Add taskbar icon and allow closing from taskbar
        self.root.withdraw()  # Hide window temporarily
        self.root.iconbitmap(default="") if os.name == 'nt' else None  # Show in taskbar
        self.root.protocol("WM_DELETE_WINDOW", self.force_close)
        self.root.deiconify()  # Show window again

        # Get DPI scale factor - simplified for CustomTkinter compatibility
        if hasattr(ctk, 'get_scaling'):
            # Use CustomTkinter's scaling if available
            self.dpi_scale = ctk.get_scaling()
        else:
            # Fallback to manual detection
            try:
                from ctypes import windll
                self.dpi_scale = windll.shcore.GetScaleFactorForDevice(0) / 100
            except Exception:
                print("Failed to get DPI scale, using default")
                self.dpi_scale = 1.0

        # Set dark grey background
        self.root.configure(bg='#2b2b2b')

        # Add right-click menu for force close
        self.create_context_menu()

        # Bind right-click event
        self.root.bind('<Button-3>', self.show_context_menu)
        
        # Add timeout mechanism (reduced from 60 to 30 seconds)
        self.timeout_id = self.root.after(30000, self.handle_timeout)

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate splash dimensions based on screen size and DPI
        base_width = int(min(screen_width * 0.8, 1200))
        base_height = int(min(screen_height * 0.8, 800))
        
        # Apply DPI scaling
        splash_width = int(base_width * self.dpi_scale)
        splash_height = int(base_height * self.dpi_scale)

        # Calculate position
        x = (screen_width - splash_width) // 2
        y = (screen_height - splash_height) // 2

        # Configure root grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create main frame with grid
        self.frame = tk.Frame(self.root, bg='#2b2b2b')
        self.frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure frame grid
        self.frame.grid_rowconfigure(0, weight=1)  # Image/text area
        self.frame.grid_rowconfigure(1, weight=0)  # Progress bar
        self.frame.grid_rowconfigure(2, weight=0)  # Status label
        self.frame.grid_columnconfigure(0, weight=1)

        # Set initial geometry
        self.root.geometry(f"{splash_width}x{splash_height}+{x}+{y}")

        # Try to load splash image with optimized path lookup
        self.load_splash_image(splash_width, splash_height)

        # Progress bar with custom style
        self.setup_progress_bar(splash_width)

        # Status label with DPI-aware font size
        self.setup_status_label()

    def load_splash_image(self, width, height):
        """Improved image loading with better error handling"""
        # Paths for splash image lookup
        possible_paths = [
            PathManager.get_resource_path("Helper.png"),
            PathManager.get_resource_path("Helper.jpg"),
        ]

        # Try to load image
        for splash_path in possible_paths:
            try:
                if os.path.exists(splash_path):
                    print(f"Found splash image at: {splash_path}")
                    image = Image.open(splash_path)
                    
                    # Use full frame width and height above progress bar
                    img_width = width
                    img_height = int(height * 0.9)  # Leave 10% for progress bar and status
                    
                    # Maintain aspect ratio while filling the space
                    aspect_ratio = image.width / image.height
                    target_ratio = img_width / img_height
                    
                    if target_ratio > aspect_ratio:
                        # Image is taller than space, will fill height
                        new_height = img_height
                        new_width = int(img_height * aspect_ratio)
                    else:
                        # Image is wider than space, will fill width
                        new_width = img_width
                        new_height = int(img_width / aspect_ratio)
                    
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    
                    self.image_label = tk.Label(self.frame, image=photo, bg='#2b2b2b')
                    self.image_label.image = photo
                    # Remove padding to allow full-frame coverage
                    self.image_label.grid(row=0, column=0, sticky="nsew")
                    
                    return  # Successfully loaded image
            except Exception as e:
                print(f"Failed to load splash image from {splash_path}: {e}")
                continue

        # Fallback to text if no image is loaded
        print("\nNo splash image found. Using text fallback.")
        # Scale font size based on DPI
        font_size = int(48 * self.dpi_scale)
        label = tk.Label(
            self.frame,
            text="Loading Application...",
            font=("Helvetica", font_size),
            bg='#2b2b2b',
            fg='white'
        )
        label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def setup_progress_bar(self, width):
        """Configure and set up the progress bar"""
        style = ttk.Style()
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor='#2b2b2b',
            background='#007acc',
            darkcolor='#007acc',
            lightcolor='#007acc'
        )

        progress_width = int(width * 0.95)
        
        self.progress = ttk.Progressbar(
            self.frame,
            mode='indeterminate',
            length=progress_width,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.progress.start()

    def setup_status_label(self):
        """Set up the status label with proper DPI scaling"""
        status_font_size = int(20 * self.dpi_scale)
        self.status_label = tk.Label(
            self.frame,
            text="Initializing...",
            font=("Helvetica", status_font_size),
            bg='#2b2b2b',
            fg='white'
        )
        self.status_label.grid(row=2, column=0, sticky="ew", pady=5)

    def create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(
            label="Force Close Application", 
            command=self.force_close,
            background='#2b2b2b',
            foreground='white',
            activebackground='#ff0000',
            activeforeground='white'
        )

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def handle_timeout(self):
        """Handle splash screen timeout with improved messaging"""
        print("Splash screen timed out after 30 seconds")
        error_msg = ("Application initialization is taking longer than expected.\n"
                    "This might indicate a problem with the startup process.\n"
                    "Would you like to force close the application?")
                    
        if messagebox.askyesno("Startup Taking Too Long", error_msg):
            self.force_close()
        else:
            # Reset timeout for another 15 seconds, shorter than initial timeout
            self.timeout_id = self.root.after(15000, self.handle_timeout)
    
    def force_close(self):
        """Force close the entire application with enhanced cleanup"""
        print("Force closing application...")
        try:
            # Cancel timeout if it exists
            if hasattr(self, 'timeout_id') and self.timeout_id:
                self.root.after_cancel(self.timeout_id)
                self.timeout_id = None
            
            # Stop the progress bar if running
            if hasattr(self, 'progress'):
                try:
                    self.progress.stop()
                except:
                    pass
            
            # Destroy splash screen
            self.root.destroy()
            
            # Force close parent application
            if self.parent:
                try:
                    self.parent.quit()
                    self.parent.destroy()
                except:
                    pass
                    
            # As a last resort if normal close fails
            import os
            import sys
            os._exit(1)
            
        except Exception as e:
            print(f"Error during force close: {e}")
            # If all else fails
            import os
            os._exit(1)

    def update_status(self, text):
        """Update status text with error checking"""
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.config(text=text)
                self.root.update_idletasks()
                print(f"Status update: {text}")
        except Exception as e:
            print(f"Error updating status: {e}")

    def close(self):
        """Normal close of splash screen with improved cleanup"""
        try:
            # Cancel timeout if it exists
            if hasattr(self, 'timeout_id') and self.timeout_id:
                self.root.after_cancel(self.timeout_id)
                self.timeout_id = None
            
            # Stop the progress bar if running
            if hasattr(self, 'progress'):
                try:
                    self.progress.stop()
                except:
                    pass
                    
            # Lower topmost flag before destroying
            self.root.attributes('-topmost', False)
            
            # Destroy the window
            self.root.destroy()
        except Exception as e:
            print(f"Error closing splash screen: {e}")

class FilterGamesApp:
    def __init__(self, root):
        # Initialize with PathManager
        self.base_path = PathManager.get_base_path()
        
        # Add window state tracking
        self._popup_active = False

        # Initialize timing data first
        self.timing_data = []
        self.tab_load_times = []
        self.start_time = time.time()

        # Initialize config_manager without passing base_path
        self.config_manager = ConfigManager()

        # Get the base_path from config_manager if needed elsewhere
        self.base_path = self.config_manager.base_path

        self.root = root
        
        # Configure root window properties first
        self.root.attributes('-alpha', 0.0)  # Start invisible but maintain geometry
        self.root.attributes('-topmost', False)  # Explicitly ensure window isn't topmost
        
        # Window state setup with more adaptive defaults
        self._window_state = {
            'width_percentage': 0.75,  # Slightly smaller default
            'height_percentage': 0.75,  # Slightly smaller default
            'min_width': 800,    # Reduced minimum width
            'min_height': 600,   # Reduced minimum height
            'is_fullscreen': False
        }

        # Get the script name for the title
        script_name = os.path.splitext(os.path.basename(__file__))[0]
        if script_name == 'noname':
            self.root.title("")
        else:
            self.root.title(script_name)

        # Store original geometry
        self.original_geometry = None

        # Create and show splash screen
        self.splash = SplashScreen(root)
        self.splash.update_status("Initializing application...")

        # Start loading the application
        self.root.after(100, self.initialize_app)
        
        # Ensure main window isn't topmost after a delay
        self.root.after(200, lambda: self.root.attributes('-topmost', False))

    @staticmethod
    def resource_path(relative_path):
        """Get absolute path to resource, works for dev and PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    def _handle_focus(self):
        """Handle window focus events"""
        if not self._popup_active:
            self.root.attributes('-alpha', 1.0)
            self.root.focus_force()

    def show_popup(self, popup_window):
        """Standardized method to show popups"""
        self._popup_active = True
        popup_window.transient(self.root)
        # Only set topmost temporarily
        popup_window.attributes('-topmost', True)
        popup_window.focus_force()

        popup_window.after(100, lambda: popup_window.attributes('-topmost', False))
        
        def on_popup_close():
            self._popup_active = False
            popup_window.withdraw()
            self.root.after(50, lambda: self.root.attributes('-alpha', 1.0))
            self.root.after(100, popup_window.destroy)
        
        popup_window.protocol("WM_DELETE_WINDOW", on_popup_close)
        return on_popup_close

    def finish_loading(self):
        """Close splash screen and show main window"""
        self.splash.close()
        
        # Explicitly ensure window isn't topmost
        self.root.attributes('-topmost', False)
        
        # Make window visible with a slight delay
        self.root.after(50, lambda: self.root.attributes('-alpha', 1.0))
        
        # Get fullscreen preference
        fullscreen_mode = self.config_manager.get_fullscreen_preference()
        
        # Add appearance frame after main UI is set up
        self.add_appearance_mode_frame(fullscreen=fullscreen_mode)
        
        # Handle fullscreen if needed
        if fullscreen_mode:
            self._window_state['is_fullscreen'] = True
            self.handle_fullscreen()
            
        # Final ensure of non-topmost state
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

    def initialize_app(self):
        """Initialize the main application with loading status updates"""
        try:
            # Configure root grid before adding any widgets
            self.root.grid_rowconfigure(0, weight=1)  # Main content
            self.root.grid_rowconfigure(1, weight=0)  # Appearance frame
            self.root.grid_columnconfigure(0, weight=1)

            self.splash.update_status("Detecting screen configuration...")
            self.detect_screen_configuration()

            self.splash.update_status("Setting up window configurations...")
            self._calculate_and_set_window_size()
            
            # Window Configuration
            self.splash.update_status("Setting up window configurations...")
            self._calculate_and_set_window_size()
            
            # UI Setup
            self.splash.update_status("Setting up user interface...")
            self.setup_main_ui()
            
            self.splash.update_status("Launch complete!")
            self.root.after(1000, self.finish_loading)

        except Exception as e:
            print(f"Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            self.splash.update_status(f"Error: {str(e)}")

    def check_for_extreme_screen_size(self):
        """Check for extremely unusual screen configurations and adjust if needed"""
        try:
            # Get actual window size after rendering
            actual_width = self.root.winfo_width()
            actual_height = self.root.winfo_height()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Check if window is larger than screen
            if actual_width > screen_width or actual_height > screen_height:
                print(f"Warning: Window size ({actual_width}x{actual_height}) exceeds screen size ({screen_width}x{screen_height})")
                
                # Force a more conservative size
                new_width = min(800, int(screen_width * 0.7))
                new_height = min(600, int(screen_height * 0.7))
                x = (screen_width - new_width) // 2
                y = (screen_height - new_height) // 2
                
                geometry_string = f"{new_width}x{new_height}+{x}+{y}"
                self.root.geometry(geometry_string)
                self.original_geometry = geometry_string
                
                print(f"Adjusted window size to {new_width}x{new_height}")
                
                # Schedule another check after window stabilizes
                self.root.after(1000, self.check_for_extreme_screen_size)
                
        except Exception as e:
            print(f"Error in screen size safety check: {e}")
    
    def finish_loading(self):
        """Close splash screen and show main window"""
        self.splash.close()
        
        # Explicitly ensure window isn't topmost
        self.root.attributes('-topmost', False)
        
        # Make window visible with a slight delay
        self.root.after(50, lambda: self.root.attributes('-alpha', 1.0))
        
        # Get fullscreen preference
        fullscreen_mode = self.config_manager.get_fullscreen_preference()
        
        # Add appearance frame after main UI is set up
        self.add_appearance_mode_frame(fullscreen=fullscreen_mode)
        
        # Handle fullscreen if needed
        if fullscreen_mode:
            self._window_state['is_fullscreen'] = True
            self.handle_fullscreen()
        
        # Check for extreme screen sizes after window is visible
        self.root.after(500, self.check_for_extreme_screen_size)
        
        # Final ensure of non-topmost state
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
    
    def detect_screen_configuration(self):
        """Detect screen configuration and adjust window parameters accordingly"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Detect if we're on a vertical screen
        is_vertical = screen_height > screen_width
        
        # Detect if we're on a small screen (below typical desktop resolution)
        is_small_screen = screen_width < 1280 or screen_height < 768
        
        # Log screen configuration
        print(f"Screen configuration: {screen_width}x{screen_height} " + 
            f"({'Vertical' if is_vertical else 'Horizontal'}, " +
            f"{'Small' if is_small_screen else 'Normal'} screen)")
        
        # Adjust window state based on screen configuration
        if is_vertical:
            # For vertical screens, use a higher percentage of height but less width
            self._window_state['width_percentage'] = 0.85
            self._window_state['height_percentage'] = 0.7
            self._window_state['min_width'] = min(700, int(screen_width * 0.85))
            self._window_state['min_height'] = min(600, int(screen_height * 0.7))
            
            # Schedule exe frame auto-handling after UI is fully loaded
            self.root.after(1500, self._handle_exe_frame_for_vertical_screen)
        
        if is_small_screen:
            # For small screens, use more conservative dimensions
            self._window_state['width_percentage'] = 0.7
            self._window_state['height_percentage'] = 0.7
            self._window_state['min_width'] = min(600, int(screen_width * 0.7))
            self._window_state['min_height'] = min(500, int(screen_height * 0.7))
            
        # Ensure aspect ratio isn't too extreme
        max_aspect_ratio = 1.8  # Maximum width/height or height/width ratio
        if is_vertical:
            if screen_height / screen_width > max_aspect_ratio:
                self._window_state['height_percentage'] = 0.6  # Reduce height percentage further
        else:
            if screen_width / screen_height > max_aspect_ratio:
                self._window_state['width_percentage'] = 0.7  # Reduce width percentage
                
    def _show_vertical_screen_notification(self):
        """Show a notification about vertical screen adaptations with option to not show again"""
        # First check if notification is disabled in config
        try:
            if hasattr(self, 'config_manager'):
                show_notification = self.config_manager.get_setting('Settings', 'show_vertical_screen_notification', default=True)
                if not show_notification:
                    return  # Don't show if user disabled it
        except:
            pass  # If there's any error, proceed with showing the notification
            
        try:
            # Create popup window
            popup = ctk.CTkToplevel(self.root)
            popup.title("Vertical Screen Detected")
            
            # Make it appear on top but not system-wide topmost
            popup.attributes('-topmost', True)
            popup.after(100, lambda: popup.attributes('-topmost', False))
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate appropriate size - smaller for vertical screens
            # Make it narrower but still tall enough for content
            popup_width = min(400, int(screen_width * 0.8))
            popup_height = 330  # Increased to accommodate checkbox
            
            # Ensure it doesn't exceed screen bounds
            popup_width = min(popup_width, screen_width - 40)
            popup_height = min(popup_height, screen_height - 100)
            
            # Configure grid with appropriate weights
            popup.grid_columnconfigure(0, weight=1)
            popup.grid_rowconfigure(0, weight=0)  # Header
            popup.grid_rowconfigure(1, weight=1)  # Content
            popup.grid_rowconfigure(2, weight=0)  # Checkbox
            popup.grid_rowconfigure(3, weight=0)  # Button
            
            # Add header with appropriately sized font
            header_font_size = max(14, min(16, int(popup_width / 25)))
            header = ctk.CTkLabel(
                popup, 
                text="Vertical Screen Mode", 
                font=("Arial", header_font_size, "bold")
            )
            header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="ew")
            
            # Add content with more condensed text and smaller font for vertical screens
            content_font_size = max(10, min(12, int(popup_width / 35)))
            content = ctk.CTkLabel(
                popup,
                text=(
                    "Your screen is in vertical orientation.\n\n"
                    "The Exe Selector panel has been\n"
                    "automatically hidden.\n\n"
                    "You can show it by clicking the '>'\n"
                    "button on the right edge,\n"
                    "or pop it out to a separate window\n"
                    "with the '□' button."
                ),
                font=("Arial", content_font_size),
                justify="center",
                wraplength=popup_width - 50  # Ensure text wraps properly
            )
            content.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
            
            # Add "Do not show again" checkbox
            do_not_show_var = ctk.BooleanVar()
            do_not_show_checkbox = ctk.CTkCheckBox(
                popup,
                text="Do not show this message again",
                variable=do_not_show_var,
                font=("Arial", content_font_size - 1)
            )
            do_not_show_checkbox.grid(row=2, column=0, pady=(5, 5), padx=15, sticky="ew")
            
            # Handle close with checkbox value
            def on_close():
                if do_not_show_var.get() and hasattr(self, 'config_manager'):
                    try:
                        # Update config to not show notification again
                        self.config_manager.config.set('Settings', 'show_vertical_screen_notification', 'False')
                        self.config_manager.save_config()
                    except Exception as e:
                        print(f"Error saving notification preference: {e}")
                popup.destroy()
            
            # Add close button
            close_button = ctk.CTkButton(
                popup,
                text="Got it",
                command=on_close,
                width=80,
                height=30,
                font=("Arial", content_font_size)
            )
            close_button.grid(row=3, column=0, pady=(5, 15))
            
            # Set initial size
            popup.geometry(f"{popup_width}x{popup_height}")
            
            # Center the popup after it's been created and sized
            popup.update_idletasks()
            actual_width = popup.winfo_width()
            actual_height = popup.winfo_height()
            x = (screen_width // 2) - (actual_width // 2)
            y = (screen_height // 2) - (actual_height // 2)
            popup.geometry(f"+{x}+{y}")
            
            # Ensure it gets focus
            popup.focus_force()
            
            # Add auto-close after 15 seconds
            auto_close_id = popup.after(15000, on_close)
            
            # Override window close button
            popup.protocol("WM_DELETE_WINDOW", on_close)
            
        except Exception as e:
            print(f"Error showing vertical screen notification: {e}")
    
    def _handle_exe_frame_for_vertical_screen(self):
        """Auto-hide exe frame on vertical screens and show a notification"""
        if hasattr(self, 'exe_frame_controller'):
            # Auto-hide the exe frame
            self.exe_frame_controller.hide_exe_frame()
            
            # Create a notification popup
            self._show_vertical_screen_notification()
    
    def _calculate_and_set_window_size(self):
        """Calculate window size based on screen size and constraints, with better vertical screen support"""
        try:
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Determine if we're on a vertical screen
            is_vertical = screen_height > screen_width
            
            # Adjust minimum dimensions based on screen orientation
            if is_vertical:
                min_width = min(self._window_state['min_width'], int(screen_width * 0.9))
                min_height = min(self._window_state['min_height'], int(screen_height * 0.8))
            else:
                min_width = self._window_state['min_width']
                min_height = self._window_state['min_height']
            
            # Calculate size based on percentages with orientation-aware minimums
            width = max(min_width, int(screen_width * self._window_state['width_percentage']))
            height = max(min_height, int(screen_height * self._window_state['height_percentage']))
            
            # Ensure window isn't larger than screen (with some margin)
            width = min(width, screen_width - 20)  # 20px margin
            height = min(height, screen_height - 50)  # 50px margin for taskbar
            
            # Calculate centered position
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            
            # Store dimensions
            self._window_state['width'] = width
            self._window_state['height'] = height
            
            if not self._window_state['is_fullscreen']:
                geometry_string = f"{width}x{height}+{x}+{y}"
                self.root.geometry(geometry_string)
                self.original_geometry = geometry_string
                
        except Exception as e:
            print(f"Error calculating window size: {e}")
            # Use more conservative fallback dimensions
            self.root.geometry("1000x700+100+100")

    def handle_fullscreen(self):
        """Enhanced fullscreen handling with scaling awareness"""
        try:
            if self._window_state['is_fullscreen']:
                # Store current geometry if not already stored
                if not self.original_geometry:
                    self.original_geometry = self.root.geometry()
                
                # Adjust column weights for better fullscreen distribution
                # This ensures exe frame doesn't get pushed off screen
                self.main_frame.grid_columnconfigure(0, weight=4)  # More space for tabs
                self.main_frame.grid_columnconfigure(1, weight=1)  # Maintain exe frame visibility
                
                # Set fullscreen
                self.root.attributes('-fullscreen', True)
                
            else:
                # Restore original geometry
                self.root.attributes('-fullscreen', False)
                if self.original_geometry:
                    self.root.geometry(self.original_geometry)
                    
                # Reset to normal weight distribution
                self.main_frame.grid_columnconfigure(0, weight=4)
                self.main_frame.grid_columnconfigure(1, weight=1)
        except Exception as e:
            print(f"Error handling fullscreen: {e}")
            self.root.attributes('-fullscreen', False)
    
    def add_resize_observer(self):
        """Add window resize handling"""
        self.root.bind('<Configure>', self.on_window_resize)

    def on_window_resize(self, event):
        """Enhanced resize handling for proper scaling"""
        if event.widget == self.root and not self._window_state['is_fullscreen']:
            # Update window dimensions
            self._window_state['width'] = event.width
            self._window_state['height'] = event.height
            
            # Store the new geometry
            self.original_geometry = self.root.geometry()

            # Trigger a frame update to ensure proper layout
            self.root.update_idletasks()

    def setup_main_ui(self):
        """Setup all UI components with proper vertical expansion and frame control"""
        overall_start = time.time()
        self.tab_load_times = []
        
        # Set window icon and AppUserModelID FIRST, before any other UI setup
        try:
            icon_path = self.resource_path("icon.ico")
            if os.name == 'nt':  # Windows
                # Set AppUserModelID before any UI operations
                myappid = 'coinops.filtergames.app.v1'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                # Then set the icon
                self.root.iconbitmap(default=icon_path)
            elif os.name == 'posix':  # macOS or Linux
                if 'darwin' in os.uname().sysname.lower():  # Check if it's macOS
                    icns_path = os.path.join(PathManager.get_base_path() + "Customisation.app/Contents/Resources" + "icon.ico")
                    self.root.iconphoto(True, PhotoImage(file=icns_path))
                else:  # Linux
                    icon_img = PhotoImage(file=icon_path)
                    self.root.iconphoto(True, icon_img)
        except Exception as e:
            print(f"Could not load icon: {e}")
        
        # Now continue with the rest of the UI setup
        self.root.resizable(True, True)
        self.playlist_location = self.config_manager.get_playlist_location()

        # Configure root window grid - main content and appearance frame
        self.root.grid_rowconfigure(0, weight=1)  # Main content
        self.root.grid_rowconfigure(1, weight=0)  # Appearance frame
        self.root.grid_columnconfigure(0, weight=1)
                    
        # Create main container
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        
        # Configure main_frame grid with extra column for toggle buttons
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)  # Main content area
        self.main_frame.grid_columnconfigure(1, minsize=300, weight=0)  # Exe selector (fixed width)
        self.main_frame.grid_columnconfigure(2, minsize=34, weight=0)  # Toggle buttons (fixed width, never changes)
        
        # Create tabview frame with proper scaling
        self.tabview_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="transparent")
        self.tabview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        # Configure tabview_frame grid
        self.tabview_frame.grid_rowconfigure(0, weight=1)
        self.tabview_frame.grid_columnconfigure(0, weight=1)
        
        # Create exe selector frame that maintains visibility
        self.exe_selector_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.exe_selector_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Configure exe_selector_frame grid
        self.exe_selector_frame.grid_rowconfigure(0, weight=1)
        self.exe_selector_frame.grid_columnconfigure(0, weight=1)
        
        # Create exe file selector
        self.exe_selector = ExeFileSelector(self.exe_selector_frame, self.config_manager)
        
        # Create exe frame controller (after exe selector is created)
        self.exe_frame_controller = ExeFrameController(self, self.main_frame, self.exe_selector_frame, self.exe_selector)
        
        # Create tabview that will adjust its size
        self.tabview = ctk.CTkTabview(self.tabview_frame, corner_radius=10, fg_color="transparent")
        self.tabview.grid(row=0, column=0, sticky="nsew")
        
        # Add tabs
        # MultiPath Themes tab
        if self.config_manager.determine_tab_visibility('multi_path_themes'):
            # Get theme paths and validate
            theme_paths = self.config_manager.get_theme_paths_multi()
            if theme_paths.get('roms'):  # Only create tab if we have ROM paths
                tab_start = time.time()
                self.multi_path_themes_tab = self.tabview.add("Themes")
                self.multi_path_themes = MultiPathThemes(self.multi_path_themes_tab)
                tab_end = time.time()
                duration = tab_end - tab_start
                self.tab_load_times.append(("Themes", duration))
                print(f"MultiPathThemes loaded in {duration:.3f} seconds")
            else:
                print("No ROM paths configured - Themes tab will not be displayed")

        # Advanced Configurations tab
        if self.config_manager.determine_tab_visibility('advanced_configs'):
            tab_start = time.time()
            self.advanced_configs_tab = self.tabview.add("Advanced Configs")
            self.advanced_configs = AdvancedConfigs(self.advanced_configs_tab)
            tab_end = time.time()
            duration = tab_end - tab_start
            self.tab_load_times.append(("Advanced Configs", duration))
            print(f"AdvancedConfigs loaded in {duration:.3f} seconds")
            
        # Playlists tab
        if self.config_manager.determine_tab_visibility('playlists'):
            tab_start = time.time()
            self.playlists_tab = self.tabview.add("Arcade Playlists")
            self.playlists = Playlists(self.root, self.playlists_tab)
            tab_end = time.time()
            duration = tab_end - tab_start
            self.tab_load_times.append(("Playlists", duration))
            print(f"Playlists loaded in {duration:.3f} seconds")

        # Filter Games tab
        if self.config_manager.determine_tab_visibility('filter_games'):
            tab_start = time.time()
            self.filter_games_tab = self.tabview.add("Filter Arcades")
            self.filter_games = FilterGames(self.filter_games_tab)
            tab_end = time.time()
            duration = tab_end - tab_start
            self.tab_load_times.append(("Filter Arcades", duration))
            print(f"FilterGames loaded in {duration:.3f} seconds")

        # Controls tab
        if self.config_manager.determine_tab_visibility('controls'):
            tab_start = time.time()
            self.controls_tab = self.tabview.add("Controls")
            self.controls = Controls(self.controls_tab)
            tab_end = time.time()
            duration = tab_end - tab_start
            self.tab_load_times.append(("Controls", duration))
            print(f"Controls loaded in {duration:.3f} seconds")

        # Manage Games tab
        if self.config_manager.determine_tab_visibility('view_games'):
            tab_start = time.time()
            self.view_games_tab = self.tabview.add("Manage Games")
            self.view_games = ViewRoms(self.view_games_tab, self.config_manager, self)
            tab_end = time.time()
            duration = tab_end - tab_start
            self.tab_load_times.append(("Manage Games", duration))
            print(f"ViewRoms loaded in {duration:.3f} seconds")

        # Bind cleanup to window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Add exe file selector on the right side
        self.exe_selector = ExeFileSelector(self.exe_selector_frame, self.config_manager)

        # Add resize observer
        self.add_resize_observer()

    def _on_window_configure(self, event):
        """Track window size changes when not in fullscreen"""
        if not self._window_state['is_fullscreen'] and event.widget == self.root:
            # Store actual pixel dimensions
            self._window_state['width'] = event.width
            self._window_state['height'] = event.height
            
            # Update percentages based on screen size
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self._window_state['width_percentage'] = event.width / screen_width
            self._window_state['height_percentage'] = event.height / screen_height

    def add_appearance_mode_frame(self, fullscreen=False):
        """Add appearance mode frame using grid layout"""
        # Check if the frame already exists
        if hasattr(self, "appearance_frame"):
            return  # Do nothing if the frame already exists

        # Create frame
        self.appearance_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.appearance_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        # Create a grid layout inside appearance frame
        self.appearance_frame.grid_columnconfigure(1, weight=0)  # Fullscreen toggle
        self.appearance_frame.grid_columnconfigure(2, weight=1)  # Flexible space
        self.appearance_frame.grid_columnconfigure(3, weight=0)  # Scale
        self.appearance_frame.grid_columnconfigure(4, weight=0)  # Appearance mode
        self.appearance_frame.grid_columnconfigure(5, weight=0)  # Close button

        # Add fullscreen toggle
        fullscreen_switch = ctk.CTkSwitch(
            self.appearance_frame,
            text="Start in Fullscreen",
            command=lambda: self.set_fullscreen_preference(fullscreen_switch.get())
        )
        fullscreen_switch.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        if self.config_manager.get_fullscreen_preference():
            fullscreen_switch.select()
        else:
            fullscreen_switch.deselect()

        # Add scaling factor dropdown
        scaling_optionmenu = ctk.CTkOptionMenu(
            self.appearance_frame,
            values=["80%", "90%", "100%", "110%", "120%", "130%", "140%", "150%"],
            command=self.change_scaling_event
        )
        scaling_optionmenu.grid(row=0, column=3, padx=5, pady=10, sticky="e")

        # Add appearance mode dropdown
        current_mode = self.config_manager.get_appearance_mode()
        appearance_mode_optionmenu = ctk.CTkOptionMenu(
            self.appearance_frame,
            values=["Dark", "Light", "System"],
            command=lambda mode: self.set_appearance_mode(mode)
        )
        appearance_mode_optionmenu.grid(row=0, column=4, padx=5, pady=10, sticky="e")
        appearance_mode_optionmenu.set(current_mode)

        # Add close button
        close_button = ctk.CTkButton(
            self.appearance_frame,
            text="Close",
            font=("Arial", 14, "bold"),
            fg_color="red",
            hover_color="darkred",
            command=self.close_app
        )
        close_button.grid(row=0, column=5, padx=(5, 10), pady=10, sticky="e")

        # Set default scaling based on screen properties
        current_scale = self.get_recommended_scaling()
        scaling_optionmenu.set(f"{int(current_scale * 100)}%")

    def get_recommended_scaling(self):
        """Calculate recommended scaling based on screen resolution and DPI"""
        try:
            # Get screen DPI
            from ctypes import windll
            dpi = windll.user32.GetDpiForSystem() / 96.0
        except:
            dpi = 1.0
            
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Base scaling on screen size and DPI
        base_scale = min(screen_width / 1920, screen_height / 1080)  # 1080p as reference
        recommended_scale = base_scale * dpi
        
        # Round to nearest 10%
        rounded_scale = round(recommended_scale * 10) / 10
        
        # Clamp between 0.8 and 1.5
        return max(0.8, min(1.5, rounded_scale))

    def change_scaling_event(self, new_scaling_str: str):
        """Handle scaling change"""
        try:
            # Convert percentage string to float (e.g., "120%" -> 1.2)
            new_scaling = float(new_scaling_str.strip('%')) / 100
            
            # Update CustomTkinter's widget scaling
            ctk.set_widget_scaling(new_scaling)
            
            # Recalculate window size
            self._calculate_and_set_window_size()
            
            # Store the scaling preference
            if hasattr(self, 'config_manager'):
                self.config_manager.config.set('Settings', 'ui_scale', str(new_scaling))
                self.config_manager.save_config()
                
        except Exception as e:
            print(f"Error changing scaling: {e}")

    def set_appearance_mode(self, mode: str):
        """Set and save the appearance mode."""
        ctk.set_appearance_mode(mode)  # Apply the mode immediately
        self.config_manager.set_appearance_mode(mode)  # Save to config

    def set_fullscreen_preference(self, fullscreen: bool):
        """Set and save fullscreen preference."""
        self.config_manager.set_fullscreen_preference(fullscreen)
        self._window_state['is_fullscreen'] = fullscreen
        
        if fullscreen:
            # Store current window dimensions before going fullscreen
            self._previous_geometry = self.root.geometry()
            self.root.attributes("-fullscreen", True)
        else:
            self.root.attributes("-fullscreen", False)
            # Allow time for window manager and recalculate size
            self.root.after(100, self._calculate_and_set_window_size)

    def close_app(self):
        """Closes the application."""
        self.root.destroy()

    def on_closing(self):
        try:
            # Clean up exe frame controller if it exists
            if hasattr(self, 'exe_frame_controller'):
                self.exe_frame_controller.cleanup()
                
            # Clean up controls if they exist
            if hasattr(self, 'controls'):
                self.controls.cleanup()

            # Clean up advanced configs if it exists
            if hasattr(self, 'advanced_configs'):
                self.advanced_configs.cleanup()

            # Destroy the root window
            self.root.destroy()
        except Exception as e:
            print(f"Error during application closing: {e}")
            # Ensure window is destroyed even if there's an error
            try:
                self.root.destroy()
            except:
                pass

    def check_zzz_settings_folder(self):
        """Check if at least one of the required themes folders exists."""
        # Check if any of the paths exist
        if os.path.isdir(self.zzz_auto_path):
            print(f"Found themes folder: {self.zzz_auto_path}")
            return True
        elif os.path.isdir(self.zzz_set_path):
            print(f"Found zzzSettings folder: {self.zzz_set_path}")
            return True
        elif os.path.isdir(self.zzz_shutdwn_path):
            print(f"Found zzzShutdown folder: {self.zzz_shutdwn_path}")
            return True
        
        # If none of the paths exist, return False
        print(f"Warning: No themes folders found. Will remove Themes tab")
        return False

class ConfigManager:
    # Document all possible settings as class attributes
    CONFIG_FILE_VERSION = "3.1.0"  # Current configuration file version
    CONFIG_VERSION_KEY = "config_version"

    AVAILABLE_SETTINGS = {
        'Settings': {
            'settings_file': {
                'default': '5_7',
                'description': 'Settings file version to use',
                'type': str,
                'hidden': True
            },
            'multi_roms_path': {
                'default': '',
                'description': 'Comma-separated paths for multi ROMs',
                'type': List[str],
                'hidden': True
            },
            'multi_videos_path': {
                'default': '',
                'description': 'Comma-separated paths for multi videos',
                'type': List[str],
                'hidden': True
            },
            'multi_logos_path': {
                'default': '',
                'description': 'Comma-separated paths for multi logos',
                'type': List[str],
                'hidden': True
            },
            'theme_location': {
                'default': 'autochanger',
                'description': 'Location of theme files',
                'type': str,
                'hidden': True
            },
            'custom_roms_path': {
                'default': '',
                'description': 'Custom path for ROM files',
                'type': str,
                'hidden': True
            },
            'custom_videos_path': {
                'default': '',
                'description': 'Custom path for video files',
                'type': str,
                'hidden': True
            },
            'custom_logos_path': {
                'default': '',
                'description': 'Custom path for logo files',
                'type': str,
                'hidden': True
            },
            'show_location_controls': {
                'default': 'False',
                'description': 'Show location control options',
                'type': bool,
                'hidden': True
            },
            'cycle_playlist': {
                'default': '',
                'description': 'Comma-separated list of playlists to cycle through',
                'type': List[str],
                'hidden': True
            },
            'excluded': {
                'default': '',
                'description': 'Comma-separated list of items to exclude',
                'type': List[str],
                'hidden': True
            },
            'show_move_artwork_instructions': {
                'default': 'True',
                'description': 'Show Move Artwork instructions',
                'type': bool,
                'hidden': True
            },
            'show_move_roms_instructions': {
                'default': 'True',
                'description': 'Show Move ROMs instructions',
                'type': bool,
                'hidden': True
            },
            'close_gui_after_running': {
                'default': 'True',
                'description': 'Close GUI after running executable',
                'type': bool,
                'hidden': False
            },
            'additional_theme_folders': {
                'default': [],  # Changed default from '' to []
                'description': 'Comma-separated list of additional theme folder paths',
                'type': List[str],
                'hidden': False
            },
            'additional_sub_tabs': {
                'default': [],  # Changed default from '' to []
                'description': 'Comma-separated list of additional sub-tabs in format "FolderName|TabName"',
                'type': List[str],
                'hidden': False
            },
            'additional_collection_excludes': {
                'default': [],
                'description': 'Additional collection patterns to exclude from ROM scanning',
                'type': List[str],
                'hidden': False
            },
            'additional_rom_excludes': {
                'default': [],
                'description': 'Additional ROM patterns to exclude from ROM scanning',
                'type': List[str],
                'hidden': False
            },
            'fullscreen': {
                'default': 'False',
                'description': 'Start application in fullscreen mode.',
                'type': bool,
                'hidden': False
            },
            'enable_logging': {
                'default': 'False',
                'description': 'Enable or disable logging',
                'type': bool,
                'hidden': False
            },
            'log_level': {
                'default': 'NONE',
                'description': 'Logging level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL, ALL)',
                'type': str,
                'hidden': False
            },
            'appearance_mode': {
                'default': 'Dark',  # Default to Dark mode
                'description': 'Appearance mode of the application (Dark, Light, System)',
                'type': str,
                'hidden': False
            },
            'lazy_loading': {
                'default': 'True',
                'description': 'Enable or disable logging',
                'type': bool,
                'hidden': False
            },
            'ignored_executables': {
                'default': ['customisation', 'unins'],  # Default as a list
                'description': 'Comma-separated list of executables to ignore',
                'type': List[str],
                'hidden': False
            },
            'ignore_collections': {
                'default': [''],  # Default as a list, not a string
                'description': 'Comma-separated list of collections to ignore',
                'type': List[str],
                'hidden': False
            },
            'layout_paths': {
                'default': ['layouts/Arcades/collections'],
                'description': 'Comma-separated list of layout collection paths',
                'type': List[str],
                'hidden': False
            },
            'default_executable': {
                'default': '',
                'description': 'Default executable to select when opening the app',
                'type': str,
                'hidden': False
            },
            'show_console_single_collection': {
                'default': False,
                'description': 'Whether to show the Console Single Collection tab',
                'type': bool,
                'hidden': False
            },
            'show_vertical_screen_notification': {
                'default': 'True',
                'description': 'Show vertical screen mode notification',
                'type': bool,
                'hidden': False
            }
        },
        'Controls': {
            'controls_file': {
                'default': 'controls5.conf',
                'description': 'Controls configuration file',
                'type': str,
                'hidden': True
            },
            'excludeAppend': {
                'default': '',
                'description': 'Additional exclusions for controls',
                'type': str,
                'hidden': True
            },
            'controlsAdd': {
                'default': '',
                'description': 'Additional control configurations',
                'type': str,
                'hidden': True
            }
        },
        'Tabs': {
            'multi_path_themes_tab': {
                'default': 'always',  # 'auto', 'always', or 'never'
                'description': 'Visibility of Themes Games tab',
                'type': str,
                'hidden': True
            },
            'advanced_configs_tab': {
                'default': 'always',  # 'auto', 'always', or 'never'
                'description': 'Visibility of Advanced Configs tab',
                'type': str,
                'hidden': True
            },
            'playlists_tab': {
                'default': 'always',  # 'auto', 'always', or 'never'
                'description': 'Visibility of Playlists tab',
                'type': str,
                'hidden': True
            },
            'filter_games_tab': {
                'default': 'always',  # 'auto', 'always', or 'never'
                'description': 'Visibility of Filter Games tab',
                'type': str,
                'hidden': True
            },
            'controls_tab': {
                'default': 'never',  # 'auto', 'always', or 'never'
                'description': 'Visibility of Controls tab',
                'type': str,
                'hidden': True
            },
            'view_games_tab': {
                'default': 'never',  # 'auto', 'always', or 'never'
                'description': 'Visibility of All Games tab',
                'type': str,
                'hidden': True
            },
            'theme_manager': {
                'default': 'never',  # 'auto', 'always', or 'never'
                'description': 'Visibility of All Games tab',
                'type': str,
                'hidden': True
            },
        },
        'ButtonVisibility': {
            'show_move_artwork_button': { # removes all artwork for missing roms
                'default': 'always',  # 'always', 'never'
                'description': 'Controls visibility of Move Artwork button',
                'type': str,
                'hidden': True  # Changed from True
            },
            'show_move_roms_button': { # Allows a user to select roms to remove from a text fileView Log
                'default': 'always',  # 'always', 'never'
                'description': 'Controls visibility of Move ROMs button',
                'type': str,
                'hidden': True  # Changed from True
            },
            'show_remove_random_roms_button': { # Allows user to choose percentage of roms to remove. Used for me to slim down a build for testing.
                'default': 'never',  # 'always', 'never'
                'description': 'Controls visibility of Move ROMs button',
                'type': str,
                'hidden': True  # Changed from True
            },
            'remove_games_button': { # Checklist of roms user can manually choose to remove
                'default': 'always',  # 'always', 'never'
                'description': 'Controls visibility of Remove Games button',
                'type': str,
                'hidden': True  # Changed from True
            },
            'show_log_viewer_button': {  # Added new button visibility state
                'default': 'never',  # 'always', 'never'
                'description': 'Controls visibility of Log Viewer button',
                'type': str,
                'hidden': True
            },
            'create_playlist_button': {
                'default': 'always',  # 'always', 'never'
                'description': '',
                'type': str,
                'hidden': True
            },
            'export_collections_button': {
                'default': 'always',  # 'always', 'never'
                'description': 'Controls visibility of Log Viewer button',
                'type': str,
                'hidden': True
            },
        }
    }

    BUILD_TYPE_PATHS = {
        'D': {  # Dynamic build type
            'roms': "- Themes",  # Relative to `self.base_path`
            'videos': os.path.join("autochanger", "themes", "video"),
            'logos': os.path.join("autochanger", "themes", "logo")
        },
        'U': {  # User build type
            'roms': os.path.join("collections", "zzzShutdown", "roms"),
            'videos': os.path.join("collections", "zzzShutdown", "medium_artwork", "video"),
            'logos': os.path.join("collections", "zzzShutdown", "medium_artwork", "logo")
        },
        'S': {  # Settings build type
            'roms': os.path.join("collections", "zzzSettings", "roms"),
            'videos': os.path.join("collections", "zzzSettings", "medium_artwork", "video"),
            'logos': os.path.join("collections", "zzzSettings", "medium_artwork", "logo")
        }
    }

    # Add class-level cache for build type
    _cached_build_type = None
    _build_type_lock = threading.Lock()

    @classmethod
    def _determine_build_type(cls, base_path: str) -> str:
        """
        Determine build type based on directory structure.
        Thread-safe, cached implementation.
        """
        print("\n=== Build Type Detection Start ===")
        
        # Check if we already have a cached build type
        if cls._cached_build_type is not None:
            print(f"✓ Using cached build type: {cls._cached_build_type}")
            return cls._cached_build_type

        print("No cached build type found, determining build type...")
        
        # Use a lock to prevent multiple threads from determining build type simultaneously
        with cls._build_type_lock:
            print("Acquired lock for build type detection")
            
            # Double-check pattern in case another thread set it while we were waiting
            if cls._cached_build_type is not None:
                print(f"✓ Another thread set build type while waiting: {cls._cached_build_type}")
                return cls._cached_build_type

            # Check each build type's paths
            print("\nChecking paths for each build type:")
            for build_type, relative_paths in cls.BUILD_TYPE_PATHS.items():
                print(f"\nChecking build type '{build_type}':")
                valid_paths = True
                
                # Check each path for this build type
                for path_type, rel_path in relative_paths.items():
                    abs_path = os.path.join(base_path, rel_path)
                    exists = os.path.exists(abs_path)
                    print(f"  {path_type}: {abs_path}")
                    print(f"    → {'✓ Exists' if exists else '✗ Not found'}")
                    valid_paths = valid_paths and exists
                
                if valid_paths:
                    print(f"\n✓ Found valid build type: {build_type}")
                    cls._cached_build_type = build_type
                    return build_type

            # Default to 'S' if no valid paths found
            print("\n⚠ No valid build type found, defaulting to 'S'")
            cls._cached_build_type = 'S'
            return 'S'
    
    def __init__(self, debug=True):
        self.debug = debug
        self.base_path = PathManager.get_base_path()
        print(f"Base path: {self.base_path}")

        # Normalize the path
        self.base_path = os.path.normpath(self.base_path)
        print(f"Base path (normalized): {self.base_path}")
        
        # Set config path using the determined base_path
        self.config_path = os.path.join(self.base_path, "autochanger", "customisation.ini")
        print(f"Config path: {self.config_path}")

        # Create autochanger directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        self.config = configparser.ConfigParser()

        # Initialize class if needed
        print("\nChecking build type cache...")
        if ConfigManager._cached_build_type is None:
            print("Cache empty, determining build type...")
            ConfigManager._determine_build_type(self.base_path)
        else:
            print(f"Using cached build type: {ConfigManager._cached_build_type}")
        
        # Store instance build type from class cache
        self._build_type = ConfigManager._cached_build_type
        print(f"Instance build type set to: {self._build_type}")
        
        # Initialize other caches
        self._theme_paths = None
        self._tab_visibility_cache = {}
        self._button_visibility_cache = {}
        self._paths_cache = {}

        print("\nInitializing configuration...")
        self.init_log()
        self.initialize_config()
        self.version_check()

        print("\nInitializing caches...")
        # Initialize button visibility cache
        button_settings = self.AVAILABLE_SETTINGS.get('ButtonVisibility', {})
        for button_name in button_settings:
            self._button_visibility_cache[button_name] = self.determine_button_visibility(button_name)

        # Pre-compute tab visibility
        for tab in ['controls', 'view_games', 'themes_games', 'advanced_configs', 
                'playlists', 'filter_games', 'multi_path_themes_tab']:
            self._tab_visibility_cache[tab] = self.determine_tab_visibility(tab)
        
        print("=== ConfigManager Initialization Complete ===\n")
        print(f"✓ Using cached build type: {self._build_type}")
        
        # Print final state of button visibility cache
        print("\nFinal Button Visibility Cache:")
        for button_name, is_visible in self._button_visibility_cache.items():
            print(f"  {button_name}: {'visible' if is_visible else 'hidden'}")
    
    def init_log(self):
        """Initialize/clear the log file on app startup"""
        try:
            # Use autochanger folder directly
            log_folder = os.path.join(self.base_path, "autochanger")
            os.makedirs(log_folder, exist_ok=True)
            
            # Store log file in autochanger folder
            self.log_file = os.path.join(log_folder, "application.log")
            
            # Clear/create the log file
            with open(self.log_file, 'w', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] [INFO] Log initialized\n")
                f.write(f"[{timestamp}] [INFO] Application starting up\n")
                
            # Add another test log entry
            self.add_to_log("ConfigManager initialized successfully")
                
        except Exception as e:
            print(f"Error initializing log: {e}")

    def add_to_log(self, message: str, level: str = "INFO"):
        """Add a message to the log file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] [{level.upper()}] {message}\n"
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_message)

            if self.debug:
                print(formatted_message.strip())
                
        except Exception as e:
            print(f"Error writing to log: {e}")
    
    def get_fullscreen_preference(self) -> bool:
        """Retrieve the fullscreen preference."""
        return self.get_setting('Settings', 'fullscreen', False)

    def set_fullscreen_preference(self, fullscreen: bool):
        """Update the fullscreen preference."""
        self.set_setting('Settings', 'fullscreen', str(fullscreen).lower())

    def get_appearance_mode(self) -> str:
        """Retrieve the saved appearance mode."""
        return self.get_setting('Settings', 'appearance_mode', 'Dark')

    def set_appearance_mode(self, mode: str):
        """Update and save the appearance mode."""
        if mode not in ['Dark', 'Light', 'System']:
            raise ValueError("Invalid appearance mode. Must be 'Dark', 'Light', or 'System'.")
        self.set_setting('Settings', 'appearance_mode', mode)

    def version_check(self):
        """
        Check and handle configuration file version compatibility.
        Preserves legacy versions "528" and "529".
        """
        try:
            # Use the class constant for version
            current_version = ConfigManager.CONFIG_FILE_VERSION
            
            # If config file doesn't exist, create it with current version
            if not os.path.exists(self.config_path):
                self._log("Config file not found. Will create with current version.")
                self._reset_config_to_defaults()
                self.config['DEFAULT'][ConfigManager.CONFIG_VERSION_KEY] = current_version
                self.save_config()
                return

            # Read existing config
            self.config.read(self.config_path)

            # Ensure DEFAULT section exists
            if 'DEFAULT' not in self.config:
                self.config['DEFAULT'] = {}

            # Check for version key specifically in DEFAULT section
            config_version = self.config.get('DEFAULT', ConfigManager.CONFIG_VERSION_KEY, fallback=None)
            print(f"Version in config file: {config_version}")

            # Preserve "528" and "529" versions, reset if it's any other version mismatch
            if config_version is None or (config_version not in ['528', '529'] and config_version != current_version):
                self._log(f"Config version mismatch. Config: {config_version}, Current: {current_version}")
                
                # Preserve old config
                old_config = dict(self.config)
                self._reset_config_to_defaults()
                
                # Set the new version unless it's "528" or "529"
                if config_version in ['528', '529']:
                    self.config['DEFAULT'][ConfigManager.CONFIG_VERSION_KEY] = config_version
                else:
                    self.config['DEFAULT'][ConfigManager.CONFIG_VERSION_KEY] = current_version
                
                # Restore non-hidden settings from the old config
                for section in old_config.sections():
                    if section != 'DEFAULT':
                        for key, value in old_config[section].items():
                            if section not in self.config or key not in self.config[section]:
                                try:
                                    setting_type = self.AVAILABLE_SETTINGS.get(section, {}).get(key, {}).get('type', str)
                                    if setting_type == bool:
                                        value = str(value).lower() in ['true', '1', 'yes']
                                    elif setting_type == List[str]:
                                        value = ','.join(value) if isinstance(value, list) else value
                                    self.config[section][key] = str(value)
                                except Exception as e:
                                    print(f"Could not restore setting {section}.{key}: {e}")
                
                self.save_config()

        except Exception as e:
            self._log(f"Error during version check: {e}")
            self._reset_config_to_defaults()

    def determine_button_visibility(self, button_name):
        """
        Determine whether a button should be visible based on configuration and context.
        """
        try:
            # Check cache first
            if button_name in self._button_visibility_cache:
                return self._button_visibility_cache[button_name]

            # Get the default value from AVAILABLE_SETTINGS
            default_value = self.AVAILABLE_SETTINGS['ButtonVisibility'].get(button_name, {}).get('default', 'never')

            # First check ButtonVisibility section in INI
            if 'ButtonVisibility' in self.config and button_name in self.config['ButtonVisibility']:
                visibility = self.config['ButtonVisibility'][button_name]
            # Then check Settings section in INI (for backward compatibility)
            elif 'Settings' in self.config and button_name in self.config['Settings']:
                visibility = self.config['Settings'][button_name]
            else:
                visibility = default_value

            print(f"Button {button_name} visibility from config: {visibility}")
            
            # Convert visibility setting to boolean
            is_visible = visibility.lower() == 'always'
            
            # Cache the result
            self._button_visibility_cache[button_name] = is_visible
            return is_visible

        except Exception as e:
            print(f"Error determining button visibility for {button_name}: {e}")
            return False

    def update_button_visibility(self, button_name, visibility):
        """Update button visibility setting."""
        try:
            if visibility not in ['always', 'never']:
                raise ValueError("Invalid visibility mode. Must be 'always' or 'never'")
            self.set_setting('ButtonVisibility', button_name, visibility)
            # Update the cache
            self._button_visibility_cache[button_name] = (visibility == 'always')
        except Exception as e:
            print(f"Error updating button visibility for {button_name}: {e}")
    
    def _reset_config_to_defaults(self):
        """
        Reset configuration to hardcoded defaults for all non-hidden settings.
        """
        # Create a new config parser
        new_config = configparser.ConfigParser()

        # Populate sections and settings with their hardcoded defaults
        for section, settings in self.AVAILABLE_SETTINGS.items():
            new_config[section] = {}
            for key, setting_info in settings.items():
                if not setting_info.get('hidden', False):
                    # Use the hardcoded default value, converting to string
                    default_value = setting_info['default']

                    # Special handling for different types
                    if setting_info['type'] == bool:
                        # Convert boolean to lowercase string
                        default_value = str(default_value).lower()
                    elif setting_info['type'] == List[str]:
                        # Convert list to comma-separated string
                        default_value = ','.join(default_value) if default_value else ''
                    else:
                        default_value = str(default_value)

                    new_config[section][key] = default_value

        # Ensure DEFAULT section exists with version
        new_config['DEFAULT'] = {
            ConfigManager.CONFIG_VERSION_KEY: ConfigManager.CONFIG_FILE_VERSION
        }

        # Update the current config
        self.config = new_config

        self._log("Configuration reset to hardcoded defaults.")
        self.save_config()

    def save_config(self):
        """
        Write configuration to file, but only if changes have been made.
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        # Check if the current configuration differs from the existing file
        if os.path.exists(self.config_path):
            existing_config = configparser.ConfigParser()
            existing_config.read(self.config_path)

            if self._configs_are_identical(existing_config, self.config):
                # No changes, so no need to write
                return

        # Write config to file if there are changes
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def _configs_are_identical(self, config1, config2):
        """
        Compare two ConfigParser configurations for equality.
        
        :param config1: First configuration to compare
        :param config2: Second configuration to compare
        :return: True if configurations are identical, False otherwise
        """
        # Compare sections
        if set(config1.sections()) != set(config2.sections()):
            return False

        # Compare values in each section
        for section in config1.sections():
            if section not in config2:
                return False
            
            if set(config1[section].keys()) != set(config2[section].keys()):
                return False
            
            for key in config1[section]:
                val1 = str(config1[section][key]).strip()
                val2 = str(config2[section][key]).strip()
                if val1 != val2:
                    return False

        return True

    def initialize_config(self):
        """Initialize the INI file with only visible settings if it doesn't exist."""
        if not os.path.exists(self.config_path):
            self._log("Config file not found. Initializing with default visible settings.")
            self._initialize_default_config()
            self.save_config()  # Save immediately to create the file
        else:
            self.config.read(self.config_path)

    def _initialize_default_config(self):
        """Initialize the INI file with only visible (non-hidden) default settings."""
        print("\n=== Initializing Default Configuration ===")
        
        # Add base sections
        for section in ['Settings', 'Controls', 'Tabs', 'ButtonVisibility']:
            if section not in self.config:
                print(f"Creating section: {section}")
                self.config[section] = {}

        # Initialize settings from AVAILABLE_SETTINGS
        for section, settings in self.AVAILABLE_SETTINGS.items():
            if section not in self.config:
                self.config[section] = {}
                
            for key, setting_info in settings.items():
                if not setting_info.get('hidden', False):
                    default_value = str(setting_info['default'])
                    self.config[section][key] = default_value
                    print(f"Adding setting: [{section}] {key} = {default_value}")

        print("=== Default Configuration Initialization Complete ===\n")

    def verify_button_visibility_settings(self):
        """Verify that non-hidden button visibility settings are properly written to the INI file."""
        print("\n=== Verifying Button Visibility Settings ===")
        
        if 'ButtonVisibility' not in self.config:
            print("❌ ButtonVisibility section missing from config")
            return False
            
        all_correct = True
        button_settings = self.AVAILABLE_SETTINGS.get('ButtonVisibility', {})
        
        for button_name, button_info in button_settings.items():
            if not button_info.get('hidden', False):
                if button_name in self.config['ButtonVisibility']:
                    stored_value = self.config['ButtonVisibility'][button_name]
                    expected_value = button_info['default']
                    if stored_value == expected_value:
                        print(f"✓ {button_name}: stored={stored_value}")
                    else:
                        print(f"❌ Value mismatch for {button_name}: stored={stored_value}, expected={expected_value}")
                        all_correct = False
                else:
                    print(f"❌ Missing setting for {button_name}")
                    all_correct = False
        
        print(f"\nVerification {'succeeded' if all_correct else 'failed'}")
        return all_correct
    
    def determine_tab_visibility(self, tab_name):
        """
        Determine whether a tab is visible based on config and environment checks.
        """
        try:
            # Get the tab visibility setting
            setting_key = f'{tab_name}_tab'
            visibility = self.get_setting('Tabs', setting_key, 'auto')

            # Check cache first
            if tab_name in self._tab_visibility_cache:
                return self._tab_visibility_cache[tab_name]

            if visibility == 'always':
                self._tab_visibility_cache[tab_name] = True
                return True
            elif visibility == 'never':
                self._tab_visibility_cache[tab_name] = False
                return False

            # Auto mode: use context-specific logic
            result = False
            if visibility == 'auto':
                if tab_name in ['controls', 'view_games']:
                    result = self.get_playlist_location() == 'U'
                elif tab_name == 'themes_games':
                    themes_paths = [
                        os.path.join(PathManager.get_base_path(), "autochanger", "themes"),
                        os.path.join(PathManager.get_base_path(), "collections", "zzzSettings"),
                        os.path.join(PathManager.get_base_path(), "collections", "zzzShutdown")
                    ]
                    result = any(os.path.exists(path) for path in themes_paths)
                else:
                    # Other tabs like advanced_configs, playlists, filter_games => always visible
                    result = True

            self._tab_visibility_cache[tab_name] = result
            return result

        except Exception as e:
            print(f"ERROR determining tab visibility for {tab_name}: {e}")
            return False

    def update_tab_visibility(self, tab_name, visibility):
        """Update tab visibility setting."""
        try:
            if visibility not in ['auto', 'always', 'never']:
                raise ValueError("Invalid visibility mode. Must be 'auto', 'always', or 'never'")
            setting_key = f'{tab_name}_tab'
            self.set_setting('Tabs', setting_key, visibility)
            # Update the cache
            self._tab_visibility_cache[tab_name] = self.determine_tab_visibility(tab_name)
        except Exception as e:
            print(f"Error updating tab visibility for {tab_name}: {e}")

    def get_setting(self, section, key, default=None):
        """Retrieve a setting value, using the default if not present."""
        if section in self.config and key in self.config[section]:
            value = self.config[section][key]
            setting_type = self.AVAILABLE_SETTINGS.get(section, {}).get(key, {}).get('type', str)
            
            # Handle List[str] type specifically
            if setting_type == List[str]:
                # Split by comma and handle whitespace
                if value:
                    # Split by comma, strip whitespace from each item, and filter out empty strings
                    return [item.strip() for item in value.split(',') if item.strip()]
                return []
                
            if setting_type == bool:
                return value.lower() == 'true'
            
            return setting_type(value)

        # Return default directly if not present in config
        if section in self.AVAILABLE_SETTINGS and key in self.AVAILABLE_SETTINGS[section]:
            return self.AVAILABLE_SETTINGS[section][key].get('default', default)

        return default

    def set_setting(self, section, key, value):
        """Set a setting in the config file"""
        # Make sure section exists
        if section not in self.config:
            self.config[section] = {}
        
        # Set the value
        self.config[section][key] = str(value)
        
        try:
            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            print(f"Setting saved: [{section}] {key} = {value}")
        except Exception as e:
            print(f"Error saving setting: {e}")
    
    def setting_exists(self, section, key):
        """Check if a setting exists in the configuration."""
        return section in self.config and key in self.config[section]

    def _log(self, message, section=None):
        """Centralized logging method."""
        if self.debug:
            if section:
                print(f"=== {section} ===")
            print(message)

    @classmethod
    def get_available_settings(cls) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get documentation of all available settings, including hidden ones.
        Returns a dictionary of all possible settings and their metadata.
        """
        return cls.AVAILABLE_SETTINGS

    def get_build_type(self) -> str:
        """Get the cached build type."""
        print(f"Getting build type: {self._build_type}")
        return self._build_type

    def get_theme_paths(self):
        """Get theme paths with caching."""
        if self._theme_paths is not None:
            return self._theme_paths

        theme_location = self.get_setting('Settings', 'theme_location', 'autochanger')
        self._log("Resolving Theme Paths", section="Theme Path Resolution")
        self._log(f"Theme location: {theme_location}")

        if theme_location == 'custom':
            paths = self._get_custom_paths()
            if paths:
                self._theme_paths = paths
                return paths

        # Fallback to dynamic
        paths = self._get_dynamic_paths()
        self._theme_paths = paths
        return paths

    def get_theme_paths_multi(self):
        """
        Return arrays of paths for ROMs, videos, and logos.
        1) Read user-defined (INI) paths and filter out any that don't actually exist.
        2) If after filtering none are valid, fall back to the hardcoded defaults.
        """

        # 1) User-defined (INI) paths
        ini_roms = self.get_setting('Settings', 'multi_roms_path', [])
        ini_videos = self.get_setting('Settings', 'multi_videos_path', [])
        ini_logos = self.get_setting('Settings', 'multi_logos_path', [])

        # 2) Hardcoded defaults
        default_roms = [
            "- Themes",
            "collections/zzzShutdown/roms",
            "collections/zzzSettings/roms"
        ]
        default_videos = [
            "autochanger/themes/video",
            "collections/zzzShutdown/medium_artwork/video",
            "collections/zzzSettings/medium_artwork/video"
        ]
        default_logos = [
            "autochanger/themes/logo",
            "collections/zzzShutdown/medium_artwork/logo",
            "collections/zzzSettings/medium_artwork/logo"
        ]

        # Helper: filter list for only those paths that exist on disk
        def filter_existing_paths(paths: List[str]) -> List[str]:
            existing = []
            for p in paths:
                p_stripped = p.strip()
                if not p_stripped:
                    continue
                abs_path = os.path.join(self.base_path, p_stripped)
                if os.path.exists(abs_path):
                    existing.append(p_stripped)
            return existing

        # Filter the user-defined paths
        valid_roms = filter_existing_paths(ini_roms)
        valid_videos = filter_existing_paths(ini_videos)
        valid_logos = filter_existing_paths(ini_logos)

        # If user-defined paths ended up empty, revert to defaults
        if not valid_roms:
            valid_roms = filter_existing_paths(default_roms)
        if not valid_videos:
            valid_videos = filter_existing_paths(default_videos)
        if not valid_logos:
            valid_logos = filter_existing_paths(default_logos)

        return {
            'roms': valid_roms,
            'videos': valid_videos,
            'logos': valid_logos
        }

    def get_ignore_list(self):
        """
        Return a list of ROMs to ignore.
        """
        return ['']

    def update_custom_paths(self, roms_path, videos_path, logos_path):
        """
        Update the custom paths in the configuration. (Implementation placeholder)
        """
        pass

    def update_theme_location(self, location: str):
        """
        Update the theme location in the configuration.
        """
        try:
            if location not in ['autochanger', 'zzzSettings', 'custom']:
                raise ValueError("Invalid theme location. Must be 'autochanger', 'zzzSettings', or 'custom'")
            self.config.set('Settings', 'theme_location', location)
            self.save_config()
        except Exception as e:
            print(f"Error updating theme location: {str(e)}")

    def _get_dynamic_paths(self):
        """Get paths based on build type with caching."""
        build_type = self._build_type or self._determine_build_type()
        if build_type in self._paths_cache:
            return self._paths_cache[build_type]

        paths = self._get_absolute_paths(self.BUILD_TYPE_PATHS[build_type])
        if self._validate_paths(paths):
            self._paths_cache[build_type] = paths
            return paths

        self._log("✗ Dynamic paths invalid, falling back to default")
        return self.BUILD_TYPE_PATHS['S']

    def _get_custom_paths(self):
        """
        Resolve custom paths from the configuration. 
        Fallback to None if any path is invalid.
        """
        paths = {
            'roms': self.get_setting('Settings', 'custom_roms_path', ''),
            'videos': self.get_setting('Settings', 'custom_videos_path', ''),
            'logos': self.get_setting('Settings', 'custom_logos_path', '')
        }
        if self._validate_paths(paths):
            self._log("✓ Using custom paths")
            return paths
        
        self._log("✗ Custom paths invalid, falling back to defaults")
        return None

    def _get_absolute_paths(self, relative_paths):
        """Convert relative paths to absolute paths using correct path joining."""
        absolute_paths = {}
        for key, rel_path in relative_paths.items():
            # Handle special case for "- Themes" path
            if rel_path == "- Themes":
                absolute_paths[key] = os.path.join(self.base_path, "- Themes")
            else:
                absolute_paths[key] = os.path.join(self.base_path, rel_path)
                
            # Print path for debugging
            print(f"Converting path for {key}:")
            print(f"  Relative: {rel_path}")
            print(f"  Absolute: {absolute_paths[key]}")
            print(f"  Exists: {os.path.exists(absolute_paths[key])}")
            
        return absolute_paths

    def _validate_paths(self, paths):
        """Validate that all paths exist on disk with detailed logging."""
        all_valid = True
        for path_type, path in paths.items():
            exists = os.path.exists(path)
            print(f"Validating {path_type} path:")
            print(f"  Path: {path}")
            print(f"  Exists: {exists}")
            if not exists:
                all_valid = False
        return all_valid

    def get_default_paths(self):
        """Get the default autochanger paths."""
        return {
            'roms': os.path.join(self.base_path, "- Themes"),
            'videos': os.path.join(self.base_path, "autochanger", "themes", "video"),
            'logos': os.path.join(self.base_path, "autochanger", "themes", "logo")
        }

    def get_playlist_location(self) -> str:
        """Get the playlist location based on cached build type."""
        print(f"Getting playlist location (build type): {self._build_type}")
        return self._build_type
    
    @classmethod
    def reset_build_type_cache(cls):
        """Reset the build type cache (useful for testing or when paths change)."""
        print("\n=== Resetting Build Type Cache ===")
        with cls._build_type_lock:
            print("Previous cached build type:", cls._cached_build_type)
            cls._cached_build_type = None
            print("Cache reset complete")

    def get_exclude_append(self) -> List[str]:
        """Get the list of additional controls to exclude."""
        return self.get_setting('Controls', 'excludeAppend', [])

    def get_exclude_append(self) -> List[str]:
        """Get the list of additional controls to exclude."""
        return self.get_setting('Controls', 'excludeAppend', [])

    def get_controls_add(self) -> List[str]:
        """Get the list of controls to add (ignoring exclude list)."""
        return self.get_setting('Controls', 'controlsAdd', [])

    def update_controls_file(self, filename: str):
        """Update the controls file name."""
        self.set_setting('Controls', 'controls_file', filename)

    def update_exclude_append(self, controls: List[str]):
        """Update the excludeAppend list."""
        self.set_setting('Controls', 'excludeAppend', ', '.join(controls))

    def update_controls_add(self, controls: List[str]):
        """Update the controlsAdd list."""
        try:
            self.config.set('Controls', 'controlsAdd', ', '.join(controls))
            self.save_config()
        except Exception as e:
            print(f"Error updating controlsAdd: {str(e)}")

    def get_controls_file(self) -> str:
        """Get the controls file name."""
        return self.get_setting('Controls', 'controls_file', 'controls5.conf')

    def toggle_location_controls(self):
        """Toggle the visibility of location control elements."""
        current_value = self.get_setting('Settings', 'show_location_controls', False)
        self.set_setting('Settings', 'show_location_controls', not current_value)

    def get_settings_file(self) -> str:
        """Get the settings file name."""
        settings_value = self.get_setting('Settings', 'settings_file', '5_7')
        return f"settings{settings_value}.conf"

    def get_cycle_playlist(self) -> List[str]:
        """Get the cycle playlist configuration based on build conditions."""
        try:
            # If the playlist location is 'U', return only specific playlists
            if self._build_type == 'U':
                print("Playlist Location is 'U', returning default playlists")
                return ["all", "favorites", "lastplayed"]  # Only these playlists for 'U'

            # For 'S' and 'D', check if the 'cycle_playlist' option exists in the config
            if self.config.has_option('Settings', 'cycle_playlist'):
                playlists = self.config.get('Settings', 'cycle_playlist')
                if playlists:  # Non-empty value in INI
                    parsed_playlists = [item.strip() for item in playlists.split(',') if item.strip()]
                    print(f"Parsed playlists from config: {parsed_playlists}")
                    return parsed_playlists
                else:
                    print("Cycle playlist key exists but is empty")
                    return []
            else:
                # If the 'cycle_playlist' key is missing, use a default playlist list
                print("Cycle playlist key is missing, using default")
                return ["arcader", "consoles", "favorites", "lastplayed"]

        except Exception as e:
            print(f"Error reading cycle playlist: {str(e)}")
            import traceback
            traceback.print_exc()
            return ["arcader", "consoles", "favorites", "lastplayed"]  # Default in case of error

    def get_excluded_playlists(self) -> List[str]:
        """Get the excluded playlists configuration based on the specific conditions."""
        try:
            if self.config.has_option('Settings', 'excluded'):
                excluded = self.config.get('Settings', 'excluded')
                if excluded:  # Non-empty value in INI
                    return [item.strip() for item in excluded.split(',') if item.strip()]
                else:  
                    return []
            else:
                # Key is missing, use hardcoded default
                return [
                    "arcades40", "arcades60", "arcades80", "arcades120", "arcades150", 
                    "arcades220", "arcader", "arcades", "consoles", "favorites", 
                    "lastplayed", "settings" "zSettings"
                ]
        except Exception as e:
            print(f"Error reading excluded playlists: {str(e)}")
            return [
                "arcades40", "arcades60", "arcades80", "arcades120", "arcades150", 
                "arcades220", "arcader", "arcades", "consoles", "favorites", 
                "lastplayed", "settings" "zSettings"
            ]

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

class ExeFrameController:
    """Controls the visibility and position of the exe selector frame"""
    
    def __init__(self, app, main_frame, exe_selector_frame, exe_selector):
        self.app = app
        self.main_frame = main_frame
        self.exe_selector_frame = exe_selector_frame
        self.exe_selector = exe_selector
        
        # State tracking
        self.is_visible = True
        self.is_popped_out = False
        self.popup_window = None
        
        # Create the toggle button frame at the edge of main content
        self.toggle_button_frame = ctk.CTkFrame(main_frame, width=34, corner_radius=10)
        self.toggle_button_frame.grid(row=0, column=2, sticky="ns", pady=10)
        
        # Configure the toggle frame to expand vertically
        self.toggle_button_frame.grid_rowconfigure(0, weight=1)  # Top padding
        self.toggle_button_frame.grid_rowconfigure(1, weight=0)  # Toggle button
        self.toggle_button_frame.grid_rowconfigure(2, weight=0)  # Popout button
        self.toggle_button_frame.grid_rowconfigure(3, weight=1)  # Bottom padding
        self.toggle_button_frame.grid_columnconfigure(0, weight=1)
        
        # Create toggle button (using text initially, could be replaced with an icon)
        self.toggle_button = ctk.CTkButton(
            self.toggle_button_frame, 
            text="<", 
            width=30,
            height=30,
            corner_radius=5,
            command=self.toggle_exe_frame
        )
        self.toggle_button.grid(row=1, column=0, padx=2, pady=2)
        
        # Create pop-out button
        '''self.popout_button = ctk.CTkButton(
            self.toggle_button_frame, 
            text="□", 
            width=30,
            height=30,
            corner_radius=5,
            command=self.toggle_popout
        )
        self.popout_button.grid(row=2, column=0, padx=2, pady=2)'''
        
        # Add tooltips to buttons
        try:
            self.toggle_tooltip = CreateToolTip(self.toggle_button, "Show/Hide Exe Selector")
            self.popout_tooltip = CreateToolTip(self.popout_button, "Pop Out to Separate Window")
        except Exception as e:
            print(f"Could not create tooltips: {e}")

        # Also add periodic position check to detect when tooltips should be hidden
        self._add_tooltip_check()       
        
        # Detect vertical screen on init
        self._check_for_vertical_screen()
    
    def _add_tooltip_check(self):
        """Set up periodic checking of tooltip positions"""
        
        def check_tooltips():
            """Check if tooltips should be hidden based on mouse position"""
            if hasattr(self, 'toggle_tooltip') and self.toggle_tooltip:
                self.toggle_tooltip.check_position()
                
            if hasattr(self, 'popout_tooltip') and self.popout_tooltip:
                self.popout_tooltip.check_position()
                
            # Re-schedule the check if controller still exists
            if hasattr(self, 'app') and self.app:
                self.app.root.after(500, check_tooltips)
        
        # Start the periodic check
        self.app.root.after(1000, check_tooltips)
    
    def _check_for_vertical_screen(self):
        """Check if we're on a vertical screen and auto-hide if needed"""
        screen_width = self.app.root.winfo_screenwidth()
        screen_height = self.app.root.winfo_screenheight()
        
        # If vertical screen (height > width), auto-hide exe frame
        if screen_height > screen_width:
            # Delay the hide operation to ensure UI is fully built
            self.app.root.after(500, self.hide_exe_frame)
    
    def toggle_exe_frame(self):
        """Toggle the visibility of the exe selector frame"""
        if self.is_visible:
            self.hide_exe_frame()
        else:
            self.show_exe_frame()
    
    def hide_exe_frame(self):
        """Hide the exe selector frame"""
        if self.is_popped_out:
            # Just minimize the popup window
            self.popup_window.iconify()
        else:
            # Update toggle button first
            self.toggle_button.configure(text=">")
            
            # Hide the frame in the main window
            self.exe_selector_frame.grid_remove()
            
            # Update state
            self.is_visible = False
            
            # Use helper method to update layout
            self._update_layout()
    
    def show_exe_frame(self):
        """Show the exe selector frame"""
        if self.is_popped_out:
            # Restore the popup window
            self.popup_window.deiconify()
            self.popup_window.lift()
        else:
            # Update toggle button first
            self.toggle_button.configure(text="<")
            
            # Update state
            self.is_visible = True
            
            # Restore column configuration and show frame
            self.main_frame.grid_columnconfigure(1, minsize=300, weight=0)
            self.exe_selector_frame.grid()
            
            # Use helper method to update layout
            self._update_layout()
    
    def _update_layout(self):
        """Helper method to ensure proper layout when toggling exe frame visibility"""
        try:
            # Get references to key UI components
            tabview_frame = self.app.tabview_frame
            
            # Update frame configuration based on visibility
            if not self.is_visible and not self.is_popped_out:
                # When exe frame is hidden, maximize tabview frame
                self.main_frame.grid_columnconfigure(1, minsize=0, weight=0)
                tabview_frame.grid(padx=(0, 0), pady=10)
            else:
                # When exe frame is visible, restore original layout
                self.main_frame.grid_columnconfigure(1, minsize=300, weight=0)
                tabview_frame.grid(padx=(0, 10), pady=10)
            
            # Force update
            self.app.root.update_idletasks()
        except Exception as e:
            print(f"Error updating layout: {e}")
    
    def toggle_popout(self):
        """Toggle between embedded and popped-out states"""
        if self.is_popped_out:
            self.pop_in()
        else:
            self.pop_out()
    
    def pop_out(self):
        """Move the exe selector to a separate window"""
        if self.is_popped_out:
            return
        
        # Create a new toplevel window
        self.popup_window = ctk.CTkToplevel(self.app.root)
        self.popup_window.title("Exe Selector")
        self.popup_window.geometry("300x600")
        self.popup_window.minsize(250, 400)
        
        # Configure the popup window grid
        self.popup_window.grid_rowconfigure(0, weight=1)
        self.popup_window.grid_columnconfigure(0, weight=1)
        
        # Remove exe_selector from main window
        self.exe_selector_frame.grid_remove()
        
        # Reparent the exe_selector to the popup window
        # (We need to re-create it since direct reparenting isn't supported)
        new_frame = ctk.CTkFrame(self.popup_window, corner_radius=10)
        new_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure new frame grid
        new_frame.grid_rowconfigure(0, weight=1)
        new_frame.grid_columnconfigure(0, weight=1)
        
        # Create a new ExeFileSelector in the popup window
        new_exe_selector = ExeFileSelector(new_frame, self.app.config_manager)
        
        # Store references
        self.popped_out_frame = new_frame
        self.popped_out_selector = new_exe_selector
        
        # Update main window layout
        self.main_frame.grid_columnconfigure(1, minsize=0, weight=0)
        
        # Update button text
        self.popout_button.configure(text="⧉")
        
        # Handle popup window close
        self.popup_window.protocol("WM_DELETE_WINDOW", self.pop_in)
        
        # Update state
        self.is_popped_out = True
        self.is_visible = True
        
        # Update layout
        self._update_layout()
    
    def pop_in(self):
        """Move the exe selector back to the main window"""
        if not self.is_popped_out:
            return
        
        # Destroy the popup window
        self.popup_window.destroy()
        self.popup_window = None
        self.popped_out_frame = None
        self.popped_out_selector = None
        
        # Show the original exe selector frame
        self.exe_selector_frame.grid()
        
        # Restore original column configuration
        self.main_frame.grid_columnconfigure(1, minsize=300, weight=0)
        
        # Update button text
        self.popout_button.configure(text="□")
        
        # Update state
        self.is_popped_out = False
        self.is_visible = True
        
        # Update toggle button
        self.toggle_button.configure(text="<")
        
        # Update layout
        self._update_layout()
    
    def cleanup(self):
        """Clean up resources when app is closing"""
        # Clean up tooltips
        if hasattr(self, 'toggle_tooltip') and self.toggle_tooltip:
            try:
                self.toggle_tooltip.hide()
            except:
                pass
            
        if hasattr(self, 'popout_tooltip') and self.popout_tooltip:
            try:
                self.popout_tooltip.hide()
            except:
                pass
        
        # Clean up popup window
        if self.popup_window:
            try:
                self.popup_window.destroy()
            except:
                pass
                
        # Clear references to prevent memory leaks
        self.toggle_tooltip = None
        self.popout_tooltip = None
        self.popup_window = None

class ExeFileSelector:
    def __init__(self, parent_frame, config_manager):
        self.parent_frame = parent_frame
        self.config_manager = config_manager
        self.base_path = self.config_manager.base_path

        print("\nInitializing ExeFileSelector...")

        # Get settings
        close_gui_after_running = self.config_manager.get_setting('Settings', 'close_gui_after_running', True)
        self.default_exe = self.config_manager.get_setting('Settings', 'default_executable', '')
        print(f"Loaded default_executable from config: {self.default_exe}")

        # Create the exe frame inside parent frame
        self.exe_frame = ctk.CTkFrame(parent_frame, corner_radius=10)
        self.exe_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure the exe_frame grid
        self.exe_frame.grid_rowconfigure(0, weight=0)  # Logo row
        self.exe_frame.grid_rowconfigure(0, weight=1)  # Scrollable frame
        self.exe_frame.grid_rowconfigure(2, weight=0)  # Switch row
        self.exe_frame.grid_columnconfigure(0, weight=1)

        # Modified logo loading section
        try:
            print("\nLogo loading debug:")
            
            # Try multiple possible logo locations relative to base_path
            possible_paths = [
                os.path.join(self.base_path, 'autochanger', 'Logo.png'),
                os.path.join(self.base_path, 'Logo.png'),
                os.path.join(self.base_path, 'assets', 'Logo.png')
            ]

            if sys.platform == 'darwin':
                # For macOS
                possible_paths = [
                    os.path.join(self.base_path, "Customisation.app/Contents/Resources", "Logo.png")
                ]
            
            logo_found = None
            for path in possible_paths:
                print(f"Checking path: {path}")
                if os.path.exists(path):
                    logo_found = path
                    print(f"Found logo at: {logo_found}")
                    break
                    
            if not logo_found:
                raise FileNotFoundError("Logo file not found in any of the expected locations")

            # Load and process the logo
            logo_original = Image.open(logo_found)
            print(f"Logo loaded successfully! Dimensions: {logo_original.width}x{logo_original.height}")
            
            # Calculate scaled dimensions
            MAX_WIDTH = 300
            MAX_HEIGHT = 150
            width_ratio = MAX_WIDTH / logo_original.width
            height_ratio = MAX_HEIGHT / logo_original.height
            scale_ratio = min(width_ratio, height_ratio)
            new_width = int(logo_original.width * scale_ratio)
            new_height = int(logo_original.height * scale_ratio)
            
            # Create and display the logo
            logo_image = ctk.CTkImage(
                light_image=logo_original,
                dark_image=logo_original,
                size=(new_width, new_height)
            )
            
            # Create and display the logo using grid
            logo_label = ctk.CTkLabel(self.exe_frame, text="", image=logo_image)
            logo_label.grid(row=0, column=0, pady=(10, 0))
            
            # Store reference
            self.logo_image = logo_image
            
        except Exception as e:
            print(f"Error loading logo: {str(e)}")
            print(f"Full error traceback:", traceback.format_exc())
            title_label = ctk.CTkLabel(self.exe_frame, text="Select Executable", font=("Arial", 14, "bold"))
            title_label.grid(row=0, column=0, padx=10, pady=10)

       # Create a scrollable frame inside exe_frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.exe_frame, width=300, height=200, corner_radius=10)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Bind mousewheel to scrollable frame
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", self._on_mousewheel)
        self.scrollable_frame.bind("<Button-5>", self._on_mousewheel)
        
        # Find all .exe files
        self.exe_files = self.find_exe_files()
        print(f"Found executables: {self.exe_files}")
        
        # Set the default exe if it exists in exe_files, otherwise use first exe
        initial_exe = self.default_exe if self.default_exe in self.exe_files else (self.exe_files[0] if self.exe_files else "")
        print(f"Setting initial executable to: {initial_exe}")
        self.exe_var = tk.StringVar(value=initial_exe)
        
        # Dictionary to store labels and frames
        self.exe_labels = {}
        
        # Add clickable items for each exe
        for i, exe in enumerate(self.exe_files):
            # Remove the .exe extension for display
            display_name = os.path.splitext(exe)[0]
            
            # Create a frame to hold the label for better hover effects
            item_frame = ctk.CTkFrame(
                self.scrollable_frame,
                fg_color="transparent",
                corner_radius=5
            )
            item_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            item_frame.grid_columnconfigure(0, weight=1)
            
            # Create the label
            exe_label = ctk.CTkLabel(
                item_frame,
                text=display_name,
                cursor="hand2",
                anchor="w",
                padx=15,
                pady=8,
                width=300  # Add a width that extends beyond most names
            )
            exe_label.grid(row=0, column=0, sticky="ew")
            
            # Bind events for hover effect and click
            item_frame.bind("<Button-1>", lambda e, ex=exe: self.on_exe_click(ex))
            exe_label.bind("<Button-1>", lambda e, ex=exe: self.on_exe_click(ex))
            
            self.exe_labels[exe] = (item_frame, exe_label)
            
        # Update selection indicator for initial_exe
        if initial_exe and initial_exe in self.exe_labels:
            self.update_selection_indicator(initial_exe)

        # Create the switch using grid
        self.close_gui_var = tk.BooleanVar(value=close_gui_after_running)
        self.close_gui_switch = ctk.CTkSwitch(
            self.exe_frame,
            text="Close GUI After Running",
            onvalue=True,
            offvalue=False,
            variable=self.close_gui_var,
            command=self.update_switch_text
        )
        self.close_gui_switch.grid(row=2, column=0, pady=10, padx=10, sticky="w")
        
        # Update switch text initially
        self.update_switch_text()
        
        # Add a separator between exe selection and batch file sections
        separator = ctk.CTkFrame(parent_frame, height=2, fg_color="gray70")
        separator.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        # Add batch file section - convert to use grid throughout
        self.add_batch_file_dropdown(parent_frame)

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        # Different handling for different platforms
        if event.num == 4 or event.num == 5:
            # Linux behavior
            direction = 1 if event.num == 4 else -1
        else:
            # Windows behavior
            direction = event.delta // 120
        
        # Scroll the canvas inside the scrollable frame
        # For CTkScrollableFrame, we need to access its internal canvas
        self.scrollable_frame._parent_canvas.yview_scroll(-direction, "units")
    
    def on_exe_click(self, exe):
        """Handle click on an exe item"""
        self.exe_var.set(exe)
        self.update_selection_indicator(exe)
        
        # Automatically save this as the default/last used
        self.default_exe = exe
        self.config_manager.config.setdefault('Settings', {})['default_executable'] = exe
        self.config_manager.save_config()
        
        # Run the executable
        self.run_selected_exe()
        
    def update_selection_indicator(self, selected_exe):
        """Update the visual indicator of the selected exe"""
        # Find the frame of the selected exe
        if selected_exe in self.exe_labels:
            frame, _ = self.exe_labels[selected_exe]
            frame.configure(fg_color="#3B8ED0")  # Highlight color
            
            # Reset other frames
            for exe, (other_frame, _) in self.exe_labels.items():
                if exe != selected_exe:
                    other_frame.configure(fg_color="transparent")
    
    def update_switch_text(self):
        # Update the visual text based on the current switch state
        if self.close_gui_var.get():
            self.close_gui_switch.configure(text="Exit the GUI after execution")
        else:
            self.close_gui_switch.configure(text="Stay in the GUI after execution")
        
        # Save the current switch state to the configuration
        self.config_manager.config['Settings']['close_gui_after_running'] = str(self.close_gui_var.get()).lower()
        self.config_manager.save_config()

    def find_exe_files(self):
        """Find executable files with cross-platform support, ignoring specified executables."""
        # Get the executable extension based on platform
        if sys.platform.startswith('win'):
            exe_extension = '.exe'
        elif sys.platform == 'darwin':
            exe_extension = '.app'
        else:
            exe_extension = ''

        exe_dir = self.base_path
        
        print(f"Searching for executables in: {exe_dir}")
        
        # Get the list of ignored executables from the config
        ignored_terms = self.config_manager.get_setting('Settings', 'ignored_executables')
        
        # Add 'Customisation' to ignored terms if not already present
        if 'Customisation' not in ignored_terms:
            ignored_terms.append('Customisation')
        
        executables = []
        for f in os.listdir(exe_dir):
            if f.endswith(exe_extension):
                # Convert filename to lowercase for case-insensitive comparison
                filename_lower = f.lower()
                
                # Check if any ignored term appears in the filename
                should_ignore = any(
                    ignore_term.lower() in filename_lower 
                    for ignore_term in ignored_terms
                )
                
                if not should_ignore and not filename_lower.startswith('customisation'):
                    executables.append(f)
        
        print(f"Found executables: {executables}, Ignored terms:", ignored_terms)
        return executables
    
    def run_selected_exe(self):
        selected_exe = self.exe_var.get()
        if not selected_exe:
            messagebox.showinfo("No Selection", "Please select an executable.")
            return
        
        exe_path = os.path.join(PathManager.get_base_path(), selected_exe)
        try:
            # 1) Remove topmost if we want the EXE to appear on top
            #    (only if 'stay in the GUI' is toggled off, for example)
            if not self.close_gui_switch.get():
                # “Stay in the GUI”
                parent_window = self.parent_frame.winfo_toplevel()
                parent_window.attributes('-topmost', False)
                parent_window.lift()  # or parent_window.lower() if you prefer
            
            # 2) Launch the EXE
            os.startfile(exe_path)
            
            # 3) If user selected “close GUI after running,” just destroy
            if self.close_gui_switch.get():
                self.parent_frame.winfo_toplevel().destroy()

            # Optionally do a small sleep to give Windows time to reorder windows
            time.sleep(0.5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to run {selected_exe}: {e}")

    def add_batch_file_dropdown(self, parent_frame):
        # Create a frame for batch file dropdown below the separator
        self.batch_file_frame = ctk.CTkFrame(parent_frame, corner_radius=10)
        self.batch_file_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Configure the batch_file_frame grid
        self.batch_file_frame.grid_rowconfigure(0, weight=0)  # Title row
        self.batch_file_frame.grid_rowconfigure(1, weight=1)  # Script list row
        self.batch_file_frame.grid_columnconfigure(0, weight=1)

        # Add a title for the reset section using grid
        reset_label = ctk.CTkLabel(self.batch_file_frame, text="Reset Build to Defaults", font=("Arial", 14, "bold"))
        reset_label.grid(row=0, column=0, padx=10, pady=(10, 5))

        # Get batch files and ensure it's a list
        batch_files = self.find_reset_batch_files()
        print(f"Found batch files: {batch_files}")
        
        # If no scripts found, display message
        if not batch_files:
            no_scripts_label = ctk.CTkLabel(
                self.batch_file_frame,
                text="No reset scripts found",
                text_color="gray60"
            )
            no_scripts_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
            return
        
        # Create a scrollable frame for script items
        self.scripts_frame = ctk.CTkScrollableFrame(self.batch_file_frame, height=100, corner_radius=5)
        self.scripts_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.scripts_frame.grid_columnconfigure(0, weight=1)
        
        # Bind mousewheel to scrollable frame
        self.scripts_frame.bind("<MouseWheel>", self._on_scripts_mousewheel)
        self.scripts_frame.bind("<Button-4>", self._on_scripts_mousewheel)
        self.scripts_frame.bind("<Button-5>", self._on_scripts_mousewheel)
        
        # Variable to track selected script
        self.script_var = tk.StringVar(value=batch_files[0] if batch_files else "")
        print(f"Initial script selection: {self.script_var.get()}")
        
        # Clear any existing script_labels from previous runs
        self.script_labels = {}
        
        # Add clickable items for each script
        for i, script in enumerate(batch_files):
            # Remove extension and "- " for display
            display_name = os.path.splitext(script)[0].replace("- ", "")
            print(f"Creating script item {i}: {display_name}")
            
            # Create a frame with fixed width and explicit background
            script_frame = ctk.CTkFrame(
                self.scripts_frame,
                fg_color="transparent",
                corner_radius=5
            )
            script_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            script_frame.grid_columnconfigure(0, weight=1)
            
            # Create the label
            script_label = ctk.CTkLabel(
                script_frame,
                text=display_name,
                cursor="hand2",
                anchor="w",
                padx=15,
                pady=8
            )
            script_label.grid(row=0, column=0, sticky="ew")
            
            # Store the reference
            self.script_labels[script] = (script_frame, script_label)
            
            # Use a function to create a proper closure to capture the script variable correctly
            def make_bindings(script_frame, script_name):
                script_frame.bind("<Button-1>", lambda e, s=script_name: self.on_script_click(s))
                
                # Get the label for this frame
                label = script_frame.winfo_children()[0]
                label.bind("<Button-1>", lambda e, s=script_name: self.on_script_click(s))
            
            # Call the function to properly bind events
            make_bindings(script_frame, script)
            
        # Highlight the first script initially
        if batch_files:
            print(f"Setting initial highlight to: {batch_files[0]}")
            self.update_script_highlight(batch_files[0])

    def _on_scripts_mousewheel(self, event):
        """Handle mousewheel scrolling for scripts frame"""
        # Different handling for different platforms
        if hasattr(event, 'num') and (event.num == 4 or event.num == 5):
            # Linux behavior
            direction = 1 if event.num == 4 else -1
        else:
            # Windows behavior
            direction = event.delta // 120
        
        # Scroll the canvas inside the scrollable frame
        self.scripts_frame._parent_canvas.yview_scroll(-direction, "units")
    
    def on_script_click(self, script):
        """Handle click on a script item"""
        print(f"Script clicked: {script}")
        
        # Update the selected script
        self.script_var.set(script)
        
        # Update highlighting
        self.update_script_highlight(script)
        
        # Ask for confirmation before running
        confirm = messagebox.askyesno(
            "Confirmation",
            f"Are you sure you want to run the '{script}' script?"
        )
        
        if confirm:
            print(f"  - running script: {script}")
            self.run_script(script)

    def update_script_highlight(self, selected_script):
        """Update the visual indicator for scripts"""
        print(f"Setting script highlight: {selected_script}")
        
        # First reset all scripts to transparent
        for s, (frame, _) in self.script_labels.items():
            if s == selected_script:
                print(f"  - highlighting: {s}")
                frame.configure(fg_color="#B22222")  # Red
            else:
                print(f"  - clearing: {s}")
                frame.configure(fg_color="transparent")
    
    def find_reset_batch_files(self):
        """Find reset scripts with cross-platform support"""
        # Define script extensions based on platform
        if sys.platform.startswith('win'):
            extensions = ['.bat', '.cmd']
        else:
            extensions = ['.sh']
            
        base_path = self.base_path
        files = []
        
        for ext in extensions:
            files.extend([
                f for f in os.listdir(base_path) 
                if f.endswith(ext) and "Restore" in f
            ])
            
        print(f"Found reset scripts: {files}")
        return files if files else []

    def run_script(self, script_name):
        """Run scripts with cross-platform support"""
        confirm = messagebox.askyesno(
            "Confirmation",
            f"Are you sure you want to run the '{script_name}' script?"
        )

        if not confirm:
            return

        try:
            script_path = os.path.join(self.base_path, script_name)

            # Check if the script exists
            if not os.path.isfile(script_path):
                messagebox.showerror("File Not Found", f"Script not found: {script_path}")
                return

            print(f"Running script: {script_path}")

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
                    if sys.platform.startswith('win'):
                        # Windows
                        subprocess.run(
                            f'cmd.exe /c "{script_path}"',
                            shell=True,
                            text=True,
                            check=False
                        )
                    else:
                        # Linux/MacOS
                        os.chmod(script_path, 0o755)  # Make executable
                        subprocess.run(
                            ['/bin/bash', script_path],
                            shell=False,
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

"""
This class is used to manage playing videos for MultiThemes class.
"""
class ThemeViewer:
    def __init__(self, video_path=None, image_path=None):
        self.video_path = video_path
        self.image_path = image_path
        self.thumbnail = None
        self.video_cap = None
        self.is_playing = False
        self.lock = Lock()
        
    def extract_thumbnail(self):
        """Extract thumbnail from video file or load PNG with fallback handling"""
        # Try video first
        if self.video_path:
            try:
                cap = cv2.VideoCapture(self.video_path)
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    return frame
            except Exception as e:
                print(f"Error extracting video thumbnail: {e}")
        
        # Try specific image if provided (but not logo)
        if self.image_path and not any(folder in self.image_path for folder in ['logos', 'Logos']):
            try:
                image = cv2.imread(self.image_path)
                if image is not None:
                    return image
            except Exception as e:
                print(f"Error loading specific image: {e}")
        
        # Try fallback image
        fallback_path = os.path.join("assets", "images", "theme_fallback.png")
        if not os.path.exists(fallback_path):
            fallback_path = os.path.join("assets", "images", "theme_fallback.jpg")
        
        if os.path.exists(fallback_path):
            try:
                fallback_image = cv2.imread(fallback_path)
                if fallback_image is not None:
                    return fallback_image
            except Exception as e:
                print(f"Error loading fallback image: {e}")
        
        return None

    def start_video(self):
        """Start video playback"""
        with self.lock:
            if not self.is_playing and self.video_path:
                try:
                    self.video_cap = cv2.VideoCapture(self.video_path)
                    if self.video_cap.isOpened():
                        self.is_playing = True
                        #print(f"Video started successfully: {self.video_path}")
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
            
class MultiPathThemes:
    def __init__(self, parent_tab):
        #print("Initializing MultiPathThemes...")
        self.parent_tab = parent_tab
        self.base_path = PathManager.get_base_path()

        # Initialize configuration manager
        self.config_manager = ConfigManager()
        self.theme_paths = self.config_manager.get_theme_paths_multi()
        self.ignore_list = self.config_manager.get_ignore_list()

        # Validate that we have required paths
        if not self.theme_paths.get('roms'):
            print("No ROM paths configured")
            self.rom_folders = []
        else:
            self.rom_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['roms']]

        if not self.theme_paths.get('videos'):
            print("No video paths configured")
            self.video_folders = []
        else:
            self.video_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['videos']]
            
        if not self.theme_paths.get('logos'):
            print("No logo paths configured")
            self.logo_folders = []
        else:
            self.logo_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['logos']]

        # Resolve relative paths to absolute paths
        #self.rom_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['roms']]
        #self.video_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['videos']]
        #self.logo_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['logos']]

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
        self.current_rom_folder_index = 0  # Track the current ROM folder index

        self._setup_ui()
        self.load_themes()
        
        # If we have themes, show initial theme and update button visibility
        if self.themes_list:
            # Force button visibility update before showing initial theme
            self.update_exclude_button()
            self.show_initial_theme()
            # Update UI to ensure changes are applied
            self.parent_tab.update_idletasks()

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
        self.config_manager.add_to_log("Starting autoplay...")
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

    def get_build_type(self, rom_folder):
        """Determine build type from ROM folder path"""
        if 'zzzSettings' in rom_folder:
            return 'S'
        elif 'zzzShutdown' in rom_folder:
            return 'U'
        return 'D'
    
    def exclude_current_theme(self):
        """Add current theme to exclude.txt for its build type and refresh display"""
        if not self.themes_list:
            return

        current_theme = self.themes_list[self.current_theme_index]
        theme_name = os.path.splitext(current_theme[0])[0]  # Remove extension
        rom_folder = current_theme[3]  # Get ROM folder from theme tuple
        build_type = self.get_build_type(rom_folder)

        # Get the base path and construct collections path
        collections_path = os.path.join(self.base_path, 'collections')
        
        # Determine exclude directory path based on build type
        if build_type == 'S':
            exclude_dir = os.path.join(collections_path, 'zzzSettings')
        elif build_type == 'U':
            exclude_dir = os.path.join(collections_path, 'zzzShutdown')
        else:
            return  # Don't proceed for build type D

        # Ensure the exclude directory exists
        os.makedirs(exclude_dir, exist_ok=True)
        
        # Create full path to exclude.txt
        exclude_file = os.path.join(exclude_dir, 'exclude.txt')
        
        try:
            # Read existing excludes
            existing_excludes = []
            if os.path.exists(exclude_file):
                with open(exclude_file, 'r', encoding='utf-8') as f:
                    existing_excludes = [line.strip() for line in f if line.strip()]

            # Add new theme if not already excluded
            if theme_name not in existing_excludes:
                # Add the new theme to the list
                existing_excludes.append(theme_name)
                
                # Write all themes back to file, each on its own line
                with open(exclude_file, 'w', encoding='utf-8') as f:
                    for theme in existing_excludes:
                        f.write(f"{theme}\n")
                
                self.show_status_message(f"Added '{theme_name}' to exclude list")
                print(f"Added {theme_name} to {exclude_file}")
                
                # Update ignore list in config manager
                if f"{theme_name}.bat" not in self.ignore_list:
                    self.ignore_list.append(f"{theme_name}.bat")
                
                # Store current index
                current_index = self.current_theme_index
                
                # Reload themes list
                self.load_themes()
                
                # Adjust index if necessary
                if current_index >= len(self.themes_list):
                    self.current_theme_index = len(self.themes_list) - 1
                else:
                    self.current_theme_index = current_index
                
                # Show current theme at adjusted index
                if self.themes_list:
                    self.show_current_theme()
                else:
                    self._show_no_video_message()
                    self.show_status_message("No more themes available")
            else:
                self.show_status_message(f"'{theme_name}' is already in exclude list")

        except Exception as e:
            print(f"Error updating exclude file: {e}")
            print(f"Attempted to write to: {exclude_file}")
            print(f"Collections path: {collections_path}")
            print(f"Exclude directory: {exclude_dir}")
            self.show_status_message("Error updating exclude list")

    
    def _setup_exclude_context_menu(self):
        """Setup context menu for exclude button with tooltip"""
        self.exclude_menu = tk.Menu(self.parent_tab, tearoff=0)
        self.exclude_menu.add_command(label="Reset excludes", command=self.reset_excludes)
        self.exclude_menu.add_command(label="Show excluded themes", command=self.show_excluded_themes)

        # Bind right-click to Exclude button
        if 'Exclude' in self.buttons:
            exclude_button = self.buttons['Exclude']
            exclude_button.bind('<Button-3>', self.show_exclude_menu)
            
            # Add tooltip with more visible styling 
            CreateToolTip(exclude_button, 
                        "• Left-click to exclude current theme\n• Right-click to manage excluded themes")
            
    def show_exclude_menu(self, event):
        """Show the context menu on right-click"""
        try:
            self.exclude_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.exclude_menu.grab_release()

    def reset_excludes(self):
        """Reset all excludes except 'shutdown'"""
        collections_path = os.path.join(self.base_path, 'collections')
        
        # Handle Settings excludes
        settings_exclude = os.path.join(collections_path, 'zzzSettings', 'exclude.txt')
        if os.path.exists(settings_exclude):
            try:
                with open(settings_exclude, 'w', encoding='utf-8') as f:
                    f.write("")  # Clear file
                print(f"Reset Settings excludes")
            except Exception as e:
                print(f"Error resetting Settings excludes: {e}")
        
        # Handle Shutdown excludes - preserve 'shutdown' entry
        shutdown_exclude = os.path.join(collections_path, 'zzzShutdown', 'exclude.txt')
        if os.path.exists(shutdown_exclude):
            try:
                with open(shutdown_exclude, 'w', encoding='utf-8') as f:
                    f.write("shutdown\n")  # Keep only shutdown
                print(f"Reset Shutdown excludes (kept 'shutdown')")
            except Exception as e:
                print(f"Error resetting Shutdown excludes: {e}")
        
        # Reset ignore list except for shutdown.bat
        self.ignore_list = ['shutdown.bat'] if 'shutdown.bat' in self.ignore_list else []
        
        # Reload themes to show previously excluded items
        self.load_themes()
        self.show_current_theme()
        
        self.show_status_message("Excludes reset (kept 'shutdown')")

    def show_excluded_themes(self):
        """Show a dialog with currently excluded themes"""
        dialog = ctk.CTkToplevel(self.parent_tab)
        dialog.title("Excluded Themes")
        dialog.transient(self.parent_tab)
        dialog.grab_set()
        
        # Get screen width and height
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        
        # Calculate dimensions - making the dialog proportional to screen size
        dialog_width = min(int(screen_width * 0.3), 500)  # 30% of screen width, max 500px
        dialog_height = min(int(screen_height * 0.4), 400)  # 40% of screen height, max 400px
        
        # Calculate position to center
        position_x = (screen_width - dialog_width) // 2
        position_y = (screen_height - dialog_height) // 2
        
        # Set size and position
        dialog.geometry(f"{dialog_width}x{dialog_height}+{position_x}+{position_y}")
        
        # Create scrollable frame
        frame = ctk.CTkScrollableFrame(dialog)
        frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        excluded_themes = self.load_excluded_themes()
        
        if not excluded_themes:
            ctk.CTkLabel(frame, text="No themes are currently excluded").pack(pady=10)
            return
        
        # Add checkboxes for each excluded theme, excluding "shutdown"
        vars = {}
        for theme in sorted(excluded_themes):
            if theme.lower() != "shutdown":  # Explicitly exclude "shutdown" theme
                var = tk.BooleanVar()
                vars[theme] = var
                ctk.CTkCheckBox(frame, text=theme, variable=var).pack(anchor="w", pady=2)
        
        def restore_selected():
            restored = []
            for theme, var in vars.items():
                if var.get():
                    restored.append(theme)
            
            if restored:
                # Remove selected themes from exclude files
                self.remove_from_excludes(restored)
                # Reload themes
                self.load_themes()
                self.show_current_theme()
                dialog.destroy()
                self.show_status_message(f"Restored {len(restored)} themes")
        
        # Button at the bottom
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(button_frame, 
                    text="Restore Selected", 
                    command=restore_selected).pack(pady=10)

    def remove_from_excludes(self, themes_to_remove):
        """Remove specified themes from exclude files"""
        collections_path = os.path.join(self.base_path, 'collections')
        
        # Handle both Settings and Shutdown exclude files
        for folder in ['zzzSettings', 'zzzShutdown']:
            exclude_file = os.path.join(collections_path, folder, 'exclude.txt')
            if os.path.exists(exclude_file):
                try:
                    # Read existing excludes
                    with open(exclude_file, 'r', encoding='utf-8') as f:
                        excludes = [line.strip() for line in f if line.strip()]
                    
                    # Remove selected themes (keep 'shutdown' if in Shutdown folder)
                    new_excludes = []
                    for theme in excludes:
                        if theme == 'shutdown' and folder == 'zzzShutdown':
                            new_excludes.append(theme)
                        elif theme not in themes_to_remove:
                            new_excludes.append(theme)
                    
                    # Write back remaining excludes
                    with open(exclude_file, 'w', encoding='utf-8') as f:
                        for theme in new_excludes:
                            f.write(f"{theme}\n")
                    
                except Exception as e:
                    print(f"Error updating {folder} exclude file: {e}")
        
        # Update ignore list
        self.ignore_list = [item for item in self.ignore_list 
                        if item == 'shutdown.bat' or 
                        os.path.splitext(item)[0] not in themes_to_remove]
    
    def show_current_theme(self):
        """Display the current theme and start video if available"""
        print("Showing current theme...")
        if not self.themes_list:
            return

        # Stop any playing video and cancel any pending autoplay
        self.cancel_autoplay()
        if self.current_viewer and self.current_viewer.is_playing:
            self.current_viewer.stop_video()

        theme_name, video_path, png_path, rom_folder = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Create viewer with both video and image paths
        self.current_viewer = ThemeViewer(video_path, png_path)

        # Update exclude button visibility for new theme
        self.update_exclude_button()

        # Show thumbnail
        self.show_thumbnail()

        # Start video immediately if available
        if video_path:
            print("Starting video immediately...")
            if self.current_viewer.start_video():
                self.play_video()

    def force_initial_display(self):
        """Force the initial theme display"""
        print("Forcing initial display...")
        if self.themes_list:
            self.parent_tab.update_idletasks()
            self.show_initial_theme()

    def show_initial_theme(self):
        """Show the first theme and start video playback"""
        if not self.themes_list:
            return

        theme_name, video_path, png_path, rom_folder = self.themes_list[self.current_theme_index]
        display_name = os.path.splitext(theme_name)[0]
        self.theme_label.configure(text=f"Theme: {display_name}")

        # Initialize viewer
        self.current_viewer = ThemeViewer(video_path, png_path)

        # Make sure exclude button visibility is correct before showing anything
        self.update_exclude_button()

        # Force immediate thumbnail extraction and display
        thumbnail = self.current_viewer.extract_thumbnail()
        
        # Ensure the canvas is properly sized before displaying anything
        self.parent_tab.update_idletasks()
        
        if thumbnail is not None:
            self._display_frame(thumbnail)
            # Start video immediately if available
            if video_path:
                if self.current_viewer.start_video():
                    self.play_video()
        else:
            # Force canvas update before showing message
            self.video_canvas.update_idletasks()
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

    def _show_no_video_message(self):
        """Display message when no video or image is available"""
        self.video_canvas.delete("all")
        
        # Get canvas size, use minimum dimensions if not yet properly sized
        canvas_width = max(640, self.video_canvas.winfo_width())
        canvas_height = max(360, self.video_canvas.winfo_height())
        
        # Create a dark gray rectangle as background
        self.video_canvas.create_rectangle(
            0, 0, canvas_width, canvas_height,
            fill="#2B2B2B"
        )
        
        # Calculate center position
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Add "No video available" text
        self.video_canvas.create_text(
            center_x,
            center_y,
            text="No video available",
            fill="white",
            font=("Arial", 14),
            anchor="center"
        )
        
        # Get current theme name and build type for helper text
        if self.themes_list and len(self.themes_list) > self.current_theme_index:
            theme_name = os.path.splitext(self.themes_list[self.current_theme_index][0])[0]
            _, _, _, rom_folder = self.themes_list[self.current_theme_index]
            
            # Determine build type from folder path
            build_type = None
            if 'zzzSettings' in rom_folder:
                build_type = 'S'
            elif 'zzzShutdown' in rom_folder:
                build_type = 'U'
            else:
                build_type = 'D'
            
            # Get the correct video path from BUILD_TYPE_PATHS
            if build_type in self.config_manager.BUILD_TYPE_PATHS:
                video_path = self.config_manager.BUILD_TYPE_PATHS[build_type]['videos']
                helper_text = f"Place {theme_name}.mp4 in {video_path}"
            else:
                helper_text = "Video folder not configured"
        else:
            helper_text = "Video folder not configured"

        # Add helper text about video location
        self.video_canvas.create_text(
            center_x,
            center_y + 30,
            text=helper_text,
            fill="#808080",
            font=("Arial", 10),
            anchor="center"
        )

    def load_excluded_themes(self):
        """Load excluded themes from exclude.txt files in collections folder"""
        excluded_themes = set()
        
        collections_path = os.path.join(self.base_path, 'collections')
        
        # Check zzzSettings/exclude.txt
        settings_exclude = os.path.join(collections_path, 'zzzSettings', 'exclude.txt')
        if os.path.exists(settings_exclude):
            try:
                with open(settings_exclude, 'r', encoding='utf-8') as f:
                    excluded_themes.update(line.strip() for line in f if line.strip())
            except Exception as e:
                print(f"Error reading settings exclude file: {e}")
        
        # Check zzzShutdown/exclude.txt
        shutdown_exclude = os.path.join(collections_path, 'zzzShutdown', 'exclude.txt')
        if os.path.exists(shutdown_exclude):
            try:
                with open(shutdown_exclude, 'r', encoding='utf-8') as f:
                    excluded_themes.update(line.strip() for line in f if line.strip())
            except Exception as e:
                print(f"Error reading shutdown exclude file: {e}")
        
        return excluded_themes
    
    def load_themes(self):
        """Load themes and their video/image paths with exclude file checking"""
        self.themes_list = []
        
        # Load excluded themes first
        excluded_themes = self.load_excluded_themes()
        print(f"Loaded excluded themes: {excluded_themes}")

        # Look for fallback image
        fallback_path = None
        potential_fallback_paths = [
            os.path.join("assets", "images", "theme_fallback.png"),
            os.path.join("assets", "images", "theme_fallback.jpg")
        ]
        
        for path in potential_fallback_paths:
            if os.path.isfile(path):
                fallback_path = path
                break

        for rom_folder in self.rom_folders:
            if not os.path.isdir(rom_folder):
                print("Error", f"ROM folder not found: {rom_folder}")
                continue

            # Determine build type for current folder
            build_type = self.get_build_type(rom_folder)

            for filename in os.listdir(rom_folder):
                if (filename.endswith(".bat") or filename.endswith(".sh")):
                    theme_name = os.path.splitext(filename)[0]
                    
                    # Skip if theme is in excluded list or ignore list
                    if (theme_name in excluded_themes or 
                        filename in self.ignore_list or
                        theme_name.lower() == "shutdown"):  # Explicitly exclude "shutdown" theme
                        print(f"Skipping excluded theme: {theme_name}")
                        continue

                    video_path = None
                    png_path = None

                    # Look for video
                    for video_folder in self.video_folders:
                        video_path = os.path.join(video_folder, f"{theme_name}.mp4")
                        if os.path.isfile(video_path):
                            break
                        video_path = None

                    # Look for theme-specific PNG in video folders only
                    if video_path is None:
                        for video_folder in self.video_folders:
                            png_path = os.path.join(video_folder, f"{theme_name}.png")
                            if os.path.isfile(png_path):
                                break
                            png_path = None

                    # Add to themes list with appropriate fallback
                    if video_path and os.path.isfile(video_path):
                        self.themes_list.append((filename, video_path, None, rom_folder))
                    elif png_path and os.path.isfile(png_path):
                        self.themes_list.append((filename, None, png_path, rom_folder))
                    elif fallback_path:
                        self.themes_list.append((filename, None, fallback_path, rom_folder))
                    else:
                        self.themes_list.append((filename, None, None, rom_folder))

        print(f"Loaded {len(self.themes_list)} themes after excluding {len(excluded_themes)} themes")

    def show_thumbnail(self):
        """Display the current theme's thumbnail"""
        if not self.current_viewer:
            self._show_no_video_message()
            return

        # Use cached thumbnail if available
        cache_key = self.current_viewer.video_path or self.current_viewer.image_path
        if cache_key and cache_key in self.thumbnail_cache:
            thumbnail = self.thumbnail_cache[cache_key].copy()
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
                logo_path = None

                for logo_folder in self.logo_folders:
                    logo_path = os.path.join(logo_folder, f"{current_theme}.png")
                    if os.path.exists(logo_path):
                        break

                if logo_path and os.path.exists(logo_path):
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

    def get_current_build_type(self):
        """Get build type for current theme"""
        if not self.themes_list or self.current_theme_index >= len(self.themes_list):
            return None
            
        _, _, _, rom_folder = self.themes_list[self.current_theme_index]
        
        if 'zzzSettings' in rom_folder:
            return 'S'
        elif 'zzzShutdown' in rom_folder:
            return 'U'
        return 'D'
    
    def update_exclude_button(self):
        """Update exclude button visibility and layout based on current build type"""
        build_type = self.get_current_build_type()
        
        if 'Exclude' in self.buttons:
            if build_type in ['S', 'U']:
                # For S and U build types, show all buttons in normal positions
                self.buttons['Exclude'].grid(row=0, column=2)
                self.buttons['Next'].grid(row=0, column=3)
                if 'Jump Category' in self.buttons:
                    self.buttons['Jump Category'].grid(row=0, column=4)
            else:
                # For build type D, hide Exclude and shift other buttons left
                self.buttons['Exclude'].grid_remove()
                self.buttons['Next'].grid(row=0, column=2)  # Move Next to Exclude's position
                if 'Jump Category' in self.buttons:
                    self.buttons['Jump Category'].grid(row=0, column=3)  # Move Jump Category left

            # Reconfigure grid weights based on visible buttons
            for i in range(5):  # Reset all column weights
                self.button_frame.grid_columnconfigure(i, weight=0)
            
            # Set weights only for columns that have visible buttons
            if build_type in ['S', 'U']:
                visible_columns = 4 if 'Jump Category' not in self.buttons else 5
            else:
                visible_columns = 3 if 'Jump Category' not in self.buttons else 4
                
            # Set equal weights for visible columns
            for i in range(visible_columns):
                self.button_frame.grid_columnconfigure(i, weight=1)

    def _setup_ui(self):
        # Main display frame
        self.display_frame = ctk.CTkFrame(self.parent_tab)
        self.display_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Video canvas
        self.video_canvas = ctk.CTkCanvas(
            self.display_frame,
            bg="#2B2B2B",
            bd=0,
            highlightthickness=0,
            width=640,
            height=360
        )
        self.video_canvas.pack(expand=True, fill="both", padx=10, pady=10)
        self.video_canvas.bind('<Configure>', self.handle_resize)

        # Theme label (hidden but kept for reference)
        self.theme_label = ctk.CTkLabel(self.display_frame, text="")
        self.theme_label.pack_forget()

        # Button frame
        self.button_frame = ctk.CTkFrame(self.display_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=5, pady=5)

        # Define base buttons with smaller width
        button_width = 100  # Reduced button width
        base_buttons = [
            ("Previous", self.show_previous_theme, None, None, 0),
            ("Apply Theme", self.run_selected_script, "green", "darkgreen", 1),
            ("Exclude", self.exclude_current_theme, "red", "darkred", 2),  # Changed to column 2
            ("Next", self.show_next_theme, None, None, 3)  # Changed to column 3
        ]

        # Check if Jump Category button should be added
        roms_list = self.config_manager.get_theme_paths_multi().get('roms', [])
        if len(roms_list) > 1:
            base_buttons.append(("Jump Category", self.jump_to_start, None, None, 4))

        # Create buttons
        self.buttons = {}
        for text, command, fg_color, hover_color, column in base_buttons:
            btn = ctk.CTkButton(
                self.button_frame,
                text=text,
                command=command,
                fg_color=fg_color,
                hover_color=hover_color,
                border_width=0,
                width=button_width
            )
            btn.grid(row=0, column=column, sticky="ew", padx=5)
            self.buttons[text] = btn

        # Initially hide Exclude button (will be shown based on build type)
        if 'Exclude' in self.buttons:
            self.buttons['Exclude'].grid_remove()

        # Set up the context menu and tooltip for Exclude button
        self._setup_exclude_context_menu()  # Add this line here

        # Location frame
        self.location_frame = ctk.CTkFrame(self.display_frame)
        self.location_frame.pack(fill="x", padx=10, pady=5)
        self.update_location_frame_visibility()
        
    def _update_button_layout(self, event=None):
        """Update button layout proportionally based on frame size"""
        frame_width = self.button_frame.winfo_width()
        if frame_width > 0:
            # Calculate proportional padding (1% of frame width)
            padding = int(frame_width * 0.01)
            
            # Update padding for all buttons
            for btn in self.buttons.values():
                btn.grid_configure(padx=padding, pady=padding)

        # Maintain button visibility
        roms_list = self.config_manager.get_theme_paths_multi().get('roms', [])
        should_show_jump = len(roms_list) > 1
        
        if 'Jump Category' in self.buttons:
            if should_show_jump:
                self.buttons['Jump Category'].grid()
                self.button_frame.grid_columnconfigure(3, weight=1)
            else:
                self.buttons['Jump Category'].grid_remove()
                self.button_frame.grid_columnconfigure(3, weight=0)

    def _adjust_button_weights(self, columns):
        """Adjust the button frame column weights dynamically."""
        for col in range(4):  # Reset all columns
            self.button_frame.grid_columnconfigure(col, weight=0)
        for col in range(columns):  # Adjust the active columns
            self.button_frame.grid_columnconfigure(col, weight=1)

    def update_location_frame_visibility(self):
        """Update the visibility of the location frame based on config settings"""
        show_location_controls = self.config_manager.config.getboolean('Settings', 'show_location_controls', fallback=False)
        #print(f"show_location_controls value: {show_location_controls}")  # Debug

        if show_location_controls:
            self.location_frame.pack(fill="x", padx=10, pady=5)
            #print("Location frame is visible")  # Debug
        else:
            self.location_frame.pack_forget()
            #print("Location frame is hidden")  # Debug

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
        self.theme_paths = self.config_manager.get_theme_paths_multi()
        self.rom_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['roms']]
        self.video_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['videos']]
        self.logo_folders = [os.path.join(self.base_path, path) for path in self.theme_paths['logos']]

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
        elif self.current_viewer is None or (self.current_viewer.video_path is None and self.current_viewer.image_path is None):
            # If no content to display, refresh the no video message
            self._show_no_video_message()

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

        theme_name, video_path, png_path, rom_folder = self.themes_list[self.current_theme_index]
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

    def run_selected_script(self):
        """Execute the selected theme script with cross-platform support."""
        if not self.themes_list:
            print("No themes found in themes_list. Exiting function.")
            self.show_status_message("Error: No themes available!")
            return

        # Get script info from themes list
        script_filename, _, _, rom_folder = self.themes_list[self.current_theme_index]
        script_name_without_extension = os.path.splitext(script_filename)[0]
        
        # Construct absolute path using rom_folder
        script_path = os.path.abspath(os.path.join(rom_folder, script_filename))
        working_dir = os.path.dirname(script_path)
        
        # Log attempt
        self.config_manager.add_to_log(f"Attempting to run theme script: {script_name_without_extension}")
        print(f"Selected script: {script_filename}")
        print(f"Full script path: {script_path}")
        print(f"Working directory: {working_dir}")

        # Verify script exists
        if not os.path.isfile(script_path):
            error_msg = f"Script not found: {script_path}"
            print(error_msg)
            self.show_status_message(f"Error: Script '{script_name_without_extension}' not found.")
            self.config_manager.add_to_log(error_msg, "ERROR")
            return

        try:
            self.show_status_message(f"Applying theme '{script_name_without_extension}'...")

            # Platform-specific command setup
            if sys.platform == 'win32':
                # Windows: Use cmd.exe with proper escaping
                command = [
                    "cmd.exe",
                    "/c",
                    script_path
                ]
                # Windows-specific startup info
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            elif sys.platform == 'darwin':
                # macOS: Make script executable and run
                os.chmod(script_path, 0o755)  # Add execute permission
                if script_filename.endswith('.command') or script_filename.endswith('.sh'):
                    command = ["/bin/bash", script_path]
                else:
                    command = [script_path]
                startupinfo = None
            else:
                # Linux/Unix: Make script executable and run
                os.chmod(script_path, 0o755)  # Add execute permission
                if script_filename.endswith('.sh'):
                    command = ["/bin/bash", script_path]
                else:
                    command = [script_path]
                startupinfo = None

            print("Command execution details:", command)
            
            # Environment setup for cross-platform compatibility
            env = os.environ.copy()
            if sys.platform != 'win32':
                # Add script directory to PATH for Unix-like systems
                env['PATH'] = f"{working_dir}:{env.get('PATH', '')}"

            # Execute the script
            process = subprocess.run(
                command,
                check=False,
                shell=False,
                text=True,
                capture_output=True,
                cwd=working_dir,
                env=env,
                startupinfo=startupinfo
            )

            # Handle process output
            print("Process completed with return code:", process.returncode)
            if process.stdout:
                print("Standard output:", process.stdout)
            if process.stderr:
                print("Standard error:", process.stderr)

            # Handle return code
            if process.returncode != 0:
                error_msg = f"Script execution returned code {process.returncode}: {process.stderr}"
                print(error_msg)
                self.config_manager.add_to_log(error_msg, "WARNING")
                # Still show success if the script ran but had non-zero exit code
                self.show_status_message(f"Theme: {script_name_without_extension} applied!")
            else:
                self.show_status_message(f"Theme: {script_name_without_extension} applied successfully!")

        except Exception as e:
            error_msg = f"Critical error while executing script: {str(e)}"
            print(error_msg)
            self.show_status_message(f"Error: Could not apply theme '{script_name_without_extension}'.")
            self.config_manager.add_to_log(error_msg, "ERROR")

    def jump_to_start(self):
        """Jump to the start of each ROM folder for quick navigation"""
        print("Jumping to the start of each ROM folder...")
        self.cycle_rom_folders()

    def cycle_rom_folders(self):
        """Cycle through the ROM folders and display the first theme in each folder"""
        print("Cycling through ROM folders...")
        if not self.rom_folders:
            print("No ROM folders available")
            return

        # Move to the next ROM folder
        self.current_rom_folder_index = (self.current_rom_folder_index + 1) % len(self.rom_folders)
        current_rom_folder = self.rom_folders[self.current_rom_folder_index]
        print(f"Moved to next ROM folder: {current_rom_folder}")

        # Find the first theme in the current ROM folder
        first_theme_found = False
        for theme_index, (theme_name, video_path, png_path, rom_folder) in enumerate(self.themes_list):
            if rom_folder == current_rom_folder:
                self.current_theme_index = theme_index
                self.show_current_theme()
                first_theme_found = True
                break

        if not first_theme_found:
            print(f"No themes found in folder: {current_rom_folder}")

class ThemeManager:
    def __init__(self, parent_frame, config_manager=None):
        """
        Initialize the Theme Manager
        
        Args:
            parent_frame (CTkFrame): CustomTkinter frame to contain the UI elements
            config_manager: Configuration manager instance
        """
        self.parent = parent_frame
        self.config_manager = config_manager
        
        # Use PathManager to get the base path
        self.root_folder = PathManager.get_base_path()
        
        # Get layout paths from config and ensure proper formatting
        layout_paths = self.config_manager.get_setting('Settings', 'layout_paths')
        
        # Handle different possible formats of layout_paths
        if isinstance(layout_paths, str):
            # If it's a single string, convert to list
            self.layout_paths = [layout_paths]
        elif isinstance(layout_paths, (list, tuple)):
            # If it's already a list or tuple, use it
            self.layout_paths = layout_paths
        else:
            # Default fallback
            self.layout_paths = ['layouts/Arcades/collections']
            
        # Convert layout paths to full paths using PathManager
        self.layout_paths = [PathManager.get_resource_path(path) for path in self.layout_paths]
        
        print(f"Initialized layout paths: {self.layout_paths}")  # Debug print
        
        # Convert layout paths to full paths using PathManager
        self.layout_paths = [PathManager.get_resource_path(path) for path in self.layout_paths]
        
        # Theme folder remains the same
        self.themes_folder = PathManager.get_resource_path("- Themes Console")
        
        # Theme mappings (batch file name to layout file name)
        self.theme_mappings = {
            "Future Theme.bat": "layout - Future Room",
            "Nostalgic Night Theme.bat": "layout - Nostelgic Nights",
            "Zen Theme.bat": "layout - Zen Room",
            "TV Theme.bat": "layout - TV Legends",
            "Spin Theme.bat": "layout - Bottom Spin",
            "Retro Theme.bat": "layout - Retro Room",
            "Poster Theme.bat": "layout - Large Poster Cascade",
            "Future Theme.bat": "layout - Future Room",
        }
        
        # List of basic layout files that all collections have
        self.basic_layouts = {
            "layout.xml",
            "layout - 0.xml",
            "layout - 1.xml",
            "layout - 2.xml",
            "layout - 5.xml"
        }
        
        # List of collections to ignore
        self.ignore_collections = self.config_manager.get_setting('Settings', 'ignore_collections', [])
        
        # Variables to track selected collection and theme
        self.selected_collection = tk.StringVar()
        self.selected_theme = tk.StringVar()
        
        # Dictionary to store collection to path mapping
        self.collection_paths = {}
        
        self.setup_ui()
    
    def get_collections(self):
        """
        Get list of collections that have more than the basic layout files or fewer,
        from all configured layout paths, excluding ignored collections
        """
        collections = []
        # Reset collection paths dictionary
        self.collection_paths = {}
        print("Layout paths:", self.layout_paths)
        # Normalize ignored collections (strip spaces and convert to lowercase)
        normalized_ignore = [name.strip().lower() for name in self.ignore_collections]
        
        # Iterate through each layout path
        for layout_path in self.layout_paths:
            layout_folder = Path(layout_path)
            
            if not layout_folder.exists():
                continue
                
            for collection_folder in layout_folder.iterdir():
                # Skip if not a directory
                if not collection_folder.is_dir():
                    continue
                    
                # Skip if collection is in ignore list
                if collection_folder.name.strip().lower() in normalized_ignore:
                    continue
                    
                # Check for layout folder
                layout_folder = collection_folder / "layout"
                if not layout_folder.is_dir():
                    continue
                
                # Get all XML files in the layout folder
                layout_files = {f.name for f in layout_folder.iterdir() if f.is_file() and f.suffix.lower() == '.xml'}
                
                # If the collection has more files than the basic layouts, include it
                if len(layout_files) > len(self.basic_layouts):
                    collections.append(collection_folder.name)
                    # Store the path for this collection
                    self.collection_paths[collection_folder.name] = collection_folder
        
        return sorted(collections)

    def get_themes(self):
        """Get list of all theme batch files"""
        themes = []
        themes_folder = Path(self.themes_folder)
        if themes_folder.exists():
            themes = [f.name for f in themes_folder.iterdir() 
                    if f.is_file() and f.name.endswith('.bat')]
        return sorted(themes)
    
    def setup_ui(self):
        """Setup the UI with two scrollable lists (collections and themes) and an Apply button"""
        # Create main frame
        self.frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Add a title label
        title_label = ctk.CTkLabel(
            self.frame,
            text="Apply Layout to a Single Collection",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Create a container for the two lists
        lists_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        lists_frame.pack(fill="both", expand=True, pady=10)

        # Left side: Collections list
        collections_frame = ctk.CTkFrame(lists_frame, fg_color="transparent")
        collections_frame.pack(side="left", fill="both", expand=True, padx=10)

        ctk.CTkLabel(
            collections_frame,
            text="Collections",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 10))

        self.collections_scrollable = ctk.CTkScrollableFrame(collections_frame, width=200, height=300)
        self.collections_scrollable.pack(fill="both", expand=True)

        # Populate collections list with radio buttons
        for collection in self.get_collections():
            radio_button = ctk.CTkRadioButton(
                self.collections_scrollable,
                text=collection,
                variable=self.selected_collection,
                value=collection
            )
            radio_button.pack(anchor="w", pady=2)

        # Right side: Themes list
        themes_frame = ctk.CTkFrame(lists_frame, fg_color="transparent")
        themes_frame.pack(side="right", fill="both", expand=True, padx=10)

        ctk.CTkLabel(
            themes_frame,
            text="Themes",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 10))

        self.themes_scrollable = ctk.CTkScrollableFrame(themes_frame, width=200, height=300)
        self.themes_scrollable.pack(fill="both", expand=True)

        # Populate themes list with radio buttons
        for theme in self.get_themes():
            radio_button = ctk.CTkRadioButton(
                self.themes_scrollable,
                text=theme,
                variable=self.selected_theme,
                value=theme
            )
            radio_button.pack(anchor="w", pady=2)

        # Apply button
        apply_button = ctk.CTkButton(
            self.frame,
            text="Apply Theme",
            command=self.apply_theme,
            width=120,
            fg_color="green",
            font=("Arial", 12)
        )
        apply_button.pack(pady=10)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.frame,
            text="",
            font=("Arial", 12),
            text_color="gray70"
        )
        self.status_label.pack(pady=5)
    
    def apply_theme(self):
        """Apply the selected theme to the selected collection"""
        collection = self.selected_collection.get()
        theme_bat = self.selected_theme.get()
        
        # Check if a collection and theme are selected
        if not collection or not theme_bat:
            self.status_label.configure(text="Please select both a collection and theme", text_color="red")
            return
        
        # Get the corresponding layout name for the theme
        layout_name = self.theme_mappings.get(theme_bat)
        
        # If the theme is not in the mappings, generate the layout name dynamically
        if not layout_name:
            # Remove "Theme" and ".bat" from the batch file name
            layout_name = "layout - " + theme_bat.replace(" Theme.bat", "")
        
        try:
            # Get the correct path for this collection
            collection_path = self.collection_paths.get(collection)
            if not collection_path:
                self.status_label.configure(text=f"Could not find path for collection: {collection}", text_color="red")
                return
                
            # Construct the source and destination paths using the correct collection path
            source_path = collection_path / "layout" / f"{layout_name}.xml"
            dest_path = collection_path / "layout" / "layout.xml"
            
            # Ensure the source file exists
            if not source_path.exists():
                self.status_label.configure(text=f"Source layout file not found: {source_path}", text_color="red")
                return
                
            # Create the destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(str(source_path), str(dest_path))
            self.status_label.configure(text=f"Successfully applied {layout_name} to {collection}", text_color="green")
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")
            print(f"Error applying theme: {e}")

"""
These Classes are used in the Advanced Configs tab
"""

@dataclass
class ScriptMetadata:
    name: str
    path: Path
    size: int
    modified: float
    last_accessed: float
    
@dataclass
class VirtualScrollState:
    start_index: int = 0
    visible_items: int = 20
    total_items: int = 0

"""
3. Add this new MetadataCache class:
"""
class MetadataCache:
    def __init__(self, cache_duration: timedelta = timedelta(minutes=5)):
        self._cache: Dict[str, ScriptMetadata] = {}
        self._cache_duration = cache_duration
        self._last_refresh = datetime.now()
        self._lock = threading.Lock()

    def get(self, script_name: str) -> Optional[ScriptMetadata]:
        with self._lock:
            return self._cache.get(script_name)

    def set(self, script_name: str, metadata: ScriptMetadata):
        with self._lock:
            self._cache[script_name] = metadata

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._last_refresh = datetime.now()

    def is_stale(self) -> bool:
        return datetime.now() - self._last_refresh > self._cache_duration

"""
4. Add this BackgroundWorker class:
"""
class BackgroundWorker:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = queue.Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def _process_queue(self):
        while self.running:
            try:
                task, callback = self.task_queue.get(timeout=1)
                future = self.executor.submit(task)
                future.add_done_callback(callback)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")

    def submit_task(self, task, callback):
        self.task_queue.put((task, callback))

    def shutdown(self):
        self.running = False
        self.executor.shutdown(wait=True)

class AdvancedConfigs:
    def __init__(self, parent_tab):
        # First, set the parent_tab
        self.parent_tab = parent_tab
        self.favorites_display_name = "Starred"
        
        # Get base path once from ConfigManager since it's already using PathManager
        self.config_manager = ConfigManager()
        self.base_path = self.config_manager.base_path
        print(f"Using base path: {self.base_path}")
        
        # Get lazy loading setting - default to True if not specified
        self.use_lazy_loading = self.config_manager.get_setting('Settings', 'lazy_loading', True)
        print(f"Debug: Lazy loading is: {self.use_lazy_loading}")

        # Initialize support classes
        self.background_worker = BackgroundWorker()
        self.virtual_scroll_state = VirtualScrollState()
        
        # Add loading overlay
        self.loading_overlay = self._create_loading_overlay()

        # Track which tabs exist
        self._tab_inited = {}
        self._categories = {}
        self.all_scripts_map = {}
        self._themes_tabview = None

        # First, get all folders from the base path that start with "- Themes"
        base_path = Path(self.base_path)
        theme_folders = [
            f.name for f in base_path.iterdir() 
            if f.is_dir() and f.name.startswith("- Themes")
        ]
        print(f"\nDebug: Found theme folders: {theme_folders}")
        
        # Add non-theme base folders
        self.base_config_folders = [
            "- Advanced Configs",
            "- Bezels Glass and Scanlines",
            "- Mods"
        ] + theme_folders  # Add all detected theme folders
        
        print(f"\nDebug: Final base_config_folders: {self.base_config_folders}")

        # Get additional folders from config - ensure it's a list
        additional_folders = self.config_manager.get_setting('Settings', 'additional_theme_folders', [])
        if isinstance(additional_folders, str):
            additional_folders = [additional_folders] if additional_folders else []
        
        # Combine base and additional folders
        all_folders = self.base_config_folders + additional_folders
        
        # Convert all folders to Path objects
        self.config_folders_all = [Path(self.base_path, folder) for folder in all_folders]
        
        # Filter existing folders
        self.config_folders = [folder for folder in self.config_folders_all if folder.is_dir()]
        print(f"\nDebug: Final config_folders: {[f.name for f in self.config_folders]}")
        
        # Set up path for favorites
        self.favorites_path = Path(self.base_path) / "autochanger" / "favorites.json"

        # Initialize potential_sub_tabs based on theme folders
        self.potential_sub_tabs = []
        for folder in theme_folders:
            if folder.startswith("- Themes "):  # Has a suffix after "- Themes "
                tab_name = folder.replace("- Themes ", "")
                self.potential_sub_tabs.append((folder, tab_name))
        
        # Add any additional sub-tabs from config
        additional_sub_tabs_raw = self.config_manager.get_setting('Settings', 'additional_sub_tabs', [])
        if isinstance(additional_sub_tabs_raw, str):
            additional_sub_tabs_raw = [additional_sub_tabs_raw] if additional_sub_tabs_raw else []
        
        for sub_tab in additional_sub_tabs_raw:
            try:
                folder, tab_name = sub_tab.split('|')
                if (folder.strip(), tab_name.strip()) not in self.potential_sub_tabs:
                    self.potential_sub_tabs.append((folder.strip(), tab_name.strip()))
            except ValueError:
                print(f"Warning: Invalid sub-tab format: {sub_tab}. Expected format: 'FolderName|TabName'")
        
        print(f"\nDebug: Potential sub-tabs: {self.potential_sub_tabs}")
        
        # Initialize remaining components
        self._init_tab_configs()
        self.tab_radio_vars = {}
        self.radio_button_script_mapping = {}
        self.radio_buttons = {}
        self.favorite_buttons = {}
        self.is_running_all = False
        
        # Load favorites and init GUI
        self.favorites = self._load_favorites()
        self._init_gui_elements()

    def _create_loading_overlay(self):
        overlay = ctk.CTkFrame(self.parent_tab)
        spinner = ctk.CTkProgressBar(overlay)
        spinner.pack(pady=20)
        spinner.configure(mode="indeterminate")
        label = ctk.CTkLabel(overlay, text="Loading...")
        label.pack(pady=10)
        return overlay

    def show_loading(self, show: bool = True):
        if show:
            self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
            self.loading_overlay.lift()
            for widget in self.loading_overlay.winfo_children():
                if isinstance(widget, ctk.CTkProgressBar):
                    widget.start()
        else:
            for widget in self.loading_overlay.winfo_children():
                if isinstance(widget, ctk.CTkProgressBar):
                    widget.stop()
            self.loading_overlay.place_forget()

    def _get_theme_folders(self):
        """
        Get all theme folders and organize them into base and sub-folders.
        Returns tuple of (base_folder, sub_folders_dict)
        """
        theme_folders = []
        
        print("\nDebug: Searching for theme folders in:", self.base_path)
        
        # Get dynamic theme folders
        base_path = Path(self.base_path)
        for folder in base_path.iterdir():
            if folder.is_dir() and folder.name.startswith("- Themes"):
                theme_folders.append(folder)
                print(f"Debug: Found theme folder: {folder.name}")
        
        # Get additional tabs from config
        additional_sub_tabs_raw = self.config_manager.get_setting('Settings', 'additional_sub_tabs', [])
        if isinstance(additional_sub_tabs_raw, str):
            additional_sub_tabs_raw = [additional_sub_tabs_raw] if additional_sub_tabs_raw else []
        
        print(f"Debug: Additional sub-tabs from config: {additional_sub_tabs_raw}")
        
        # Add folders from additional sub-tabs
        for sub_tab in additional_sub_tabs_raw:
            try:
                folder_name, tab_name = sub_tab.split('|')
                folder_path = base_path / folder_name.strip()
                if folder_path.is_dir() and folder_path not in theme_folders:
                    theme_folders.append(folder_path)
                    print(f"Debug: Added additional theme folder: {folder_path}")
            except ValueError:
                print(f"Warning: Invalid sub-tab format: {sub_tab}. Expected format: 'FolderName|TabName'")
        
        if not theme_folders:
            print("Debug: No theme folders found!")
            return None, {}
        
        # Sort for consistent ordering
        theme_folders.sort(key=lambda x: x.name)
        print(f"\nDebug: All theme folders (sorted): {[f.name for f in theme_folders]}")
        
        # First, try to find "- Themes" as base
        base_folder = next((f for f in theme_folders if f.name == "- Themes"), None)
        
        # If not found, try "- Themes Arcade"
        if not base_folder:
            base_folder = next((f for f in theme_folders if f.name == "- Themes Arcade"), None)
        
        # If still no base folder, use the first theme folder
        if not base_folder and theme_folders:
            base_folder = theme_folders[0]
            print(f"Debug: No standard base folder found, using: {base_folder.name}")
        
        print(f"Debug: Selected base folder: {base_folder.name if base_folder else 'None'}")
        
        # Create dictionary of sub-folders with cleaned names
        sub_folders = {}
        for folder in theme_folders:
            if folder != base_folder:
                # Check if this folder is from additional_sub_tabs
                folder_name = folder.name
                for sub_tab in additional_sub_tabs_raw:
                    try:
                        config_folder, config_tab = sub_tab.split('|')
                        if folder_name == config_folder.strip():
                            # Use the configured tab name instead of the folder name
                            sub_folders[folder] = config_tab.strip()
                            print(f"Debug: Using configured name for {folder_name} -> {config_tab.strip()}")
                            break
                    except ValueError:
                        continue
                else:  # No match in additional_sub_tabs
                    # Extract the part after "- Themes "
                    if folder_name.startswith("- Themes "):
                        sub_name = folder_name.replace("- Themes ", "")
                        if sub_name:  # Only add if we have a name
                            sub_folders[folder] = sub_name
                            print(f"Debug: Added sub-folder: {folder_name} -> {sub_name}")
        
        print(f"\nDebug: Found {len(sub_folders)} sub-folders")
        return base_folder, sub_folders
    
    def _init_tab_configs(self):
        """Initialize tab configurations with optimized data structures"""
        self.tab_keywords = {
            "Favorites": frozenset(),
            "Themes": frozenset(),  # Keep Themes in keywords
            "Bezels & Effects": frozenset(["Bezel", "SCANLINE", "GLASS EFFECTS"]),
            "Overlays": frozenset(["OVERLAY"]),
            "InigoBeats": frozenset(["MUSIC"]),
            "Attract": frozenset(["Attract", "Scroll"]),
            "Monitor": frozenset(["Monitor"]),
            "Splash": frozenset(["Splash"]),
            "Front End": frozenset(["FRONT END"]),
            "Other": frozenset()
        }
        
        # Get theme folders
        base_folder, sub_folders = self._get_theme_folders()
        
        # Update the folder_to_tab_mapping based on discovered folders
        self.folder_to_tab_mapping = {
            "- Bezels Glass and Scanlines": "Bezels & Effects"
        }
        
        # Add base theme folder mapping
        if base_folder:
            self.folder_to_tab_mapping[base_folder.name] = "Themes"
        
        # Add sub-folder mappings
        for folder, tab_name in sub_folders.items():
            self.folder_to_tab_mapping[folder.name] = tab_name

    def _init_gui_elements(self):
        """Initialize GUI elements with fresh scan"""
        self.status_label = ctk.CTkLabel(
            self.parent_tab,
            text="",
            text_color="green",
            bg_color="transparent",
            corner_radius=8,
            font=("", 14, "bold")
        )
        
        self.loading_label = ctk.CTkLabel(
            self.parent_tab,
            text="Processing...",
            text_color="gray70"
        )
        
        self.progress_frame = ctk.CTkFrame(self.parent_tab)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="")
        self.progress_bar.set(0)

        self.tabview = ctk.CTkTabview(self.parent_tab)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Do initial script scan
        self._async_populate_tabs()

    @lru_cache(maxsize=250)  # was 128; 250 is the new max size
    def _get_script_path(self, script_name: str) -> Optional[Path]:
        """Cached function to find script path"""
        for folder in self.config_folders:
            script_path = folder / script_name
            if script_path.is_file():
                return script_path
        return None

    def _load_favorites(self) -> List[str]:
        """Load favorites with error handling"""
        try:
            return json.loads(self.favorites_path.read_text()) if self.favorites_path.exists() else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_favorites(self):
        """Save favorites with error handling"""
        try:
            self.favorites_path.parent.mkdir(parents=True, exist_ok=True)
            self.favorites_path.write_text(json.dumps(self.favorites))
        except OSError:
            pass  # Handle saving error gracefully

    async def _scan_folder(self, folder: Path) -> Dict[int, str]:
        """Modified scan folder with better debug output"""
        if not folder.is_dir():
            print(f"Not a directory: {folder}")
            return {}

        print(f"\nScanning folder: {folder}")
        scripts = {}
        script_count = 0

        # Get script extensions based on platform
        if sys.platform.startswith('win'):
            script_extensions = ('.bat', '.cmd')
        else:
            script_extensions = ('.sh',)

        try:
            files = list(folder.iterdir())
            print(f"Found {len(files)} total files")
        except Exception as e:
            print(f"Error listing directory {folder}: {e}")
            return {}

        async def process_file(file_path):
            nonlocal script_count
            try:
                if file_path.is_file() and file_path.suffix.lower() in script_extensions:
                    script_count += 1
                    print(f"Found script: {file_path.name}")
                    return script_count, file_path.name
            except OSError as e:
                print(f"Error processing file {file_path}: {e}")
            return None

        tasks = [process_file(f) for f in files]
        results = await asyncio.gather(*tasks)
        
        scripts = {idx: name for result in results if result for idx, name in [result]}
        print(f"Found {len(scripts)} scripts in {folder}")
        return scripts

    async def _categorize_scripts_async(self) -> Dict[str, Any]:
        """Categorize scripts asynchronously with sorting"""
        tasks = [self._scan_folder(folder) for folder in self.config_folders]
        folder_results = await asyncio.gather(*tasks)

        # Create categories dictionary
        script_categories = {tab: {} for tab in self.tab_keywords}

        # Categorize and sort scripts from folder scan results
        for folder_scripts in folder_results:
            # Convert values to list and sort alphabetically
            sorted_scripts = sorted(folder_scripts.values(), key=lambda x: x.lower())
            # Reassign indices after sorting
            for idx, script_name in enumerate(sorted_scripts, 1):
                self._categorize_script(script_name, script_categories)

        # Sort themes separately
        themes_data = {}
        for folder, sub_tab_name in self.potential_sub_tabs:
            folder_path = Path(self.base_path, folder)
            if not folder_path.is_dir():
                continue

            sub_tab_scripts_dict = await self._scan_folder(folder_path)
            if sub_tab_scripts_dict:
                # Sort scripts alphabetically
                sorted_scripts = sorted(sub_tab_scripts_dict.values(), key=lambda x: x.lower())
                # Create new dictionary with sorted scripts
                themes_data[sub_tab_name] = {i+1: script for i, script in enumerate(sorted_scripts)}

        script_categories["Themes"] = themes_data
        return script_categories


    def _categorize_script(self, script_name: str, categories: Dict[str, Dict[int, str]]):
        """Categorize a single script"""
        # Ignore theme scripts - they're handled separately by the themes tab
        script_path = self._get_script_path(script_name)
        if script_path:
            for folder in self.config_folders:
                if isinstance(folder, Path) and folder.name.startswith("- Themes"):
                    if str(script_path).startswith(str(folder)):
                        return  # Skip theme scripts entirely

        # Try to match script to a specific category first
        script_name_lower = script_name.lower()
        for tab, keywords in self.tab_keywords.items():
            if tab in ["Themes", "Favorites", "Other"]:  # Skip special categories
                continue
            if keywords and any(keyword.lower() in script_name_lower for keyword in keywords):
                idx = len(categories[tab]) + 1
                categories[tab][idx] = script_name
                print(f"Debug: Categorized {script_name} into {tab}")
                return

        # If no specific category matched and it's not a theme script, put it in Other
        idx = len(categories["Other"]) + 1
        categories["Other"][idx] = script_name
        print(f"Debug: Categorized {script_name} into Other")

    def _async_populate_tabs(self):
        """Kick off the async scanning and create tabs."""
        async def populate():
            try:
                self.show_loading(True)
                script_categories = await self._categorize_scripts_async()
                self._categories = script_categories
                self.parent_tab.after(0, lambda: self._create_tabs(script_categories))
            finally:
                self.show_loading(False)

        asyncio.run(populate())

    def _clear_current_tab_content(self, tab_name):
        """Clear the existing content of the current tab"""
        tab_frame = self.tabview.tab(tab_name)
        for widget in tab_frame.winfo_children():
            widget.destroy()

    def _clear_themes_tab_content(self):
        """Clear the existing content of the Themes tab and its sub-tabs"""
        themes_tab = self.tabview.tab("Themes")
        for widget in themes_tab.winfo_children():
            widget.destroy()
        self._themes_tabview = None

    def _create_tabs(self, script_categories, restore_tab=None):
        """Create tabs and optionally restore the previously selected tab"""
        print("\nDebug: Creating tabs...")

        # 1) Favorites Tab
        if "Favorites" not in self._tab_inited:
            self.tabview.add(self.favorites_display_name)
            self._tab_inited["Favorites"] = False

        # Build Favorites immediately
        self.update_favorites_tab()
        self._tab_inited["Favorites"] = True

        # 2) Themes Tab - always create if we have any theme folders
        base_folder, sub_folders = self._get_theme_folders()
        if base_folder or sub_folders:
            print("Debug: Found theme folders, adding Themes tab")
            if "Themes" not in self._tab_inited:
                self.tabview.add("Themes")
                self._tab_inited["Themes"] = False
                # If not using lazy loading, initialize immediately
                if not self.use_lazy_loading:
                    self._lazy_init_tab("Themes")
                    self._tab_inited["Themes"] = True

        # 3) Other script categories
        for tab_name, scripts in script_categories.items():
            if not scripts or tab_name in ("Favorites", "Themes"):
                continue

            if tab_name not in self._tab_inited:
                self.tabview.add(tab_name)
                self._tab_inited[tab_name] = False
                # If not using lazy loading, initialize immediately
                if not self.use_lazy_loading:
                    self._lazy_init_tab(tab_name)
                    self._tab_inited[tab_name] = True

        # 4) Bind to detect tab changes - only if using lazy loading
        if self.use_lazy_loading:
            self.tabview.configure(command=self._on_tab_changed)

        # 5) Restore previous tab or set initial tab
        if restore_tab and restore_tab in self._tab_inited:
            self.tabview.set(restore_tab)
            if not self._tab_inited[restore_tab] and self.use_lazy_loading:
                self._lazy_init_tab(restore_tab)
        else:
            self.set_initial_tab()

    def _clear_tabs(self):
        """Destroy any existing tabs in the Tabview for rebuild"""
        # Store existing tabs that aren't Favorites
        existing_tabs = [tab for tab in self.tabview._tab_dict.keys() 
                        if tab != "Favorites"]
        
        # Remove non-Favorites tabs
        for tab_name in existing_tabs:
            self.tabview.delete(tab_name)
            if tab_name in self._tab_inited:
                del self._tab_inited[tab_name]

        # Reset the Themes sub-tabview
        self._themes_tabview = None

    def _on_tab_changed(self):
        """Handle tab changes - only used when lazy loading is enabled"""
        if not self.use_lazy_loading:
            return
            
        # Get the name of the currently selected tab from CTkTabview
        current_tab_name = self.tabview.get()
        
        # Check if it's already initialized in your dictionary
        if not self._tab_inited.get(current_tab_name, True):
            self._lazy_init_tab(current_tab_name)
            self._tab_inited[current_tab_name] = True

    def _lazy_init_tab(self, tab_name: str):
        """Actually build out the tab's content once, on first click."""
        if tab_name == "Themes":
            script_dict = self._categories.get("Themes", {})
            self._create_themes_tab(script_dict)
        elif tab_name == "Favorites":
            # Already built in _create_tabs() if you call update_favorites_tab()
            pass
        else:
            script_dict = self._categories.get(tab_name, {})
            self._create_regular_tab(tab_name, script_dict)

    def _create_themes_tab(self, scripts: dict[int, str]):
        """Build the 'Themes' tab content with dynamically created sub-tabs"""
        themes_tab = self.tabview.tab("Themes")

        if self._themes_tabview is not None:
            return

        self._themes_tabview = ctk.CTkTabview(themes_tab)
        self._themes_tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Add the original sub-tabs (e.g., "Arcades", "Consoles", etc.)
        base_folder, sub_folders = self._get_theme_folders()
        
        # Process base folder first if it exists
        if base_folder:
            script_list = self._get_scripts_from_folder(base_folder)
            if script_list:
                self._create_theme_sub_tab(self._themes_tabview, "Arcades", script_list)
        
        # Process sub-folders
        for folder, tab_name in sub_folders.items():
            script_list = self._get_scripts_from_folder(folder)
            if script_list:
                self._create_theme_sub_tab(self._themes_tabview, tab_name, script_list)

        # Check if we should show Console Single Collection tab based on config setting
        show_csc = self.config_manager.get_setting('Settings', 'show_console_single_collection', True)
        
        # Also check build type - get the current build type that was determined
        build_type = ConfigManager._cached_build_type  # Using the cached value
        
        # Show if explicitly enabled in config OR if build type is "U"
        if show_csc or build_type == "U":
            print(f"Debug: Showing Console Single Collection tab (show_csc={show_csc}, build_type={build_type})")
            # Add the new sub-tab: "Console Single Collection" after all original sub-tabs
            self._themes_tabview.add("Console Single Collection")
            console_single_collection_tab = self._themes_tabview.tab("Console Single Collection")

            # Initialize and add the ThemeManager UI to the new sub-tab
            self.theme_manager = ThemeManager(console_single_collection_tab, self.config_manager)
            self.theme_manager.frame.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            print(f"Debug: Not showing Console Single Collection tab (show_csc={show_csc}, build_type={build_type})")

    def _get_scripts_from_folder(self, folder: Path) -> list[str]:
        """Get list of scripts from a folder with appropriate extensions"""
        if not folder.is_dir():
            print(f"Debug: Folder not found or not a directory: {folder}")
            return []
            
        # Get appropriate extensions based on platform
        if sys.platform.startswith('win'):
            extensions = ('.bat', '.cmd')
        else:
            extensions = ('.sh',)
        
        try:
            # Get all script files
            script_list = [
                f.name for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in extensions
            ]
            
            # Sort alphabetically
            sorted_scripts = sorted(script_list, key=str.lower)
            print(f"Debug: Found {len(sorted_scripts)} scripts in {folder}")
            return sorted_scripts
        except Exception as e:
            print(f"Debug: Error reading folder {folder}: {e}")
            return []

    def _create_theme_sub_tab(self, themes_tabview, sub_tab_name: str, scripts: list[str]):
        """Create a single theme sub-tab with radio buttons, etc."""
        print(f"\nDebug: Creating theme sub-tab: {sub_tab_name}")
        
        # Validate inputs
        if not scripts:
            print(f"Debug: No scripts provided for sub-tab {sub_tab_name}")
            return
        
        if not themes_tabview:
            print("Debug: No themes_tabview provided")
            return
            
        try:
            # Add the tab to the tabview
            print(f"Debug: Adding tab {sub_tab_name} to themes_tabview")
            themes_tabview.add(sub_tab_name)
            
            # Initialize the radio variable
            if sub_tab_name not in self.tab_radio_vars:
                self.tab_radio_vars[sub_tab_name] = tk.IntVar(value=0)
            
            # Create script mapping
            sub_tab_scripts = {i+1: s for i, s in enumerate(scripts)}
            self.radio_button_script_mapping[sub_tab_name] = sub_tab_scripts
            
            # Initialize button lists if needed
            if sub_tab_name not in self.radio_buttons:
                self.radio_buttons[sub_tab_name] = []
            if sub_tab_name not in self.favorite_buttons:
                self.favorite_buttons[sub_tab_name] = {}

            # Create outer frame to properly contain the scrollable frame
            outer_frame = ctk.CTkFrame(themes_tabview.tab(sub_tab_name), fg_color="transparent")
            outer_frame.pack(fill="both", expand=True, padx=5, pady=5)

            # Create scrollable frame with explicit size and proper containment
            scrollable_frame = ctk.CTkScrollableFrame(
                outer_frame,
                width=380,
                height=400,
                fg_color="transparent"
            )
            scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

            # Set up scrolling using shared method
            self._setup_scrolling(scrollable_frame)

            # Create a frame to hold all the buttons
            buttons_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            buttons_frame.pack(fill="both", expand=True)

            # Create the script buttons
            for i, script_name in sub_tab_scripts.items():
                frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
                frame.pack(fill="x", padx=5, pady=2)

                script_label = Path(script_name).stem
                script_exists = bool(self._get_script_path(script_name))

                radio_button = ctk.CTkRadioButton(
                    frame,
                    text=script_label,
                    variable=self.tab_radio_vars[sub_tab_name],
                    value=i,
                    command=lambda t=sub_tab_name, v=i: self.on_radio_select(t, v),
                    state="normal" if script_exists else "disabled",
                    text_color="gray50" if not script_exists else None
                )
                radio_button.pack(side="left", padx=5)

                if not script_exists:
                    warning_frame = ctk.CTkFrame(frame, fg_color="transparent")
                    warning_frame.pack(side="left", padx=2)
                    warning_label = ctk.CTkLabel(
                        warning_frame,
                        text="⚠️ Script not found",
                        text_color="orange"
                    )
                    warning_label.pack(side="left")

                is_favorite = script_name in self.favorites
                star_text = "★ Starred" if is_favorite else "☆ Add to Starred"
                
                favorite_button = ctk.CTkButton(
                    frame,
                    text=star_text,
                    width=100,
                    command=lambda s=script_name: self.toggle_favorite(sub_tab_name, s)
                )
                favorite_button.pack(side="right", padx=5)

                if script_exists:
                    self.radio_buttons[sub_tab_name].append(radio_button)
                    self.favorite_buttons[sub_tab_name][script_name] = favorite_button

            # Store the frame for cleanup
            themes_tabview.tab(sub_tab_name)._scrollable_frame = scrollable_frame
            
            print(f"Debug: Successfully completed sub-tab creation for {sub_tab_name}")
        except Exception as e:
            print(f"Debug: Error in _create_theme_sub_tab for {sub_tab_name}: {e}")

    def _setup_scrolling(self, scrollable_frame):
        """Set up mousewheel scrolling for a scrollable frame"""
        def _on_mousewheel(event):
            if not scrollable_frame.winfo_exists():
                return
                
            if event.delta:
                delta = -1 * (event.delta/120)
            else:
                if event.num == 4:
                    delta = -1
                else:
                    delta = 1
                    
            scrollable_frame._parent_canvas.yview_scroll(int(delta), "units")

        # Bind mouse wheel to the scrollable frame and its children
        scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        scrollable_frame.bind_all("<Button-4>", _on_mousewheel, add="+")
        scrollable_frame.bind_all("<Button-5>", _on_mousewheel, add="+")
    
    def _create_regular_tab(self, tab_name: str, scripts: dict[int, str]):
        """Create a normal tab with alphabetically sorted scripts"""
        print(f"\nDebug: Creating regular tab: {tab_name}")
        print(f"Debug: Number of scripts: {len(scripts)}")
        
        tab_frame = self.tabview.tab(tab_name)
        
        # Clear any existing content
        for widget in tab_frame.winfo_children():
            widget.destroy()

        self.tab_radio_vars[tab_name] = tk.IntVar(value=0)
        
        # Sort scripts by name
        sorted_scripts = sorted(scripts.values(), key=lambda x: x.lower())
        sorted_scripts_dict = {i+1: script for i, script in enumerate(sorted_scripts, 1)}
        
        print(f"Debug: Sorted scripts for {tab_name}: {len(sorted_scripts_dict)}")
        
        self.radio_button_script_mapping[tab_name] = sorted_scripts_dict
        self.radio_buttons[tab_name] = []
        self.favorite_buttons[tab_name] = {}

        # Create outer frame to properly contain the scrollable frame
        outer_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        outer_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create scrollable frame with explicit size and proper containment
        scrollable_frame = ctk.CTkScrollableFrame(
            outer_frame,
            width=380,
            height=400,
            fg_color="transparent"
        )
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Set up scrolling using shared method
        self._setup_scrolling(scrollable_frame)

        # Create a frame to hold all the buttons
        buttons_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        buttons_frame.pack(fill="both", expand=True)

        # Create the script buttons
        for i, script_name in sorted_scripts_dict.items():
            frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
            frame.pack(fill="x", padx=5, pady=2)

            script_label = Path(script_name).stem
            script_exists = bool(self._get_script_path(script_name))

            radio_button = ctk.CTkRadioButton(
                frame,
                text=script_label,
                variable=self.tab_radio_vars[tab_name],
                value=i,
                command=lambda t=tab_name, v=i: self.on_radio_select(t, v),
                state="normal" if script_exists else "disabled",
                text_color="gray50" if not script_exists else None
            )
            radio_button.pack(side="left", padx=5)

            if not script_exists:
                warning_frame = ctk.CTkFrame(frame, fg_color="transparent")
                warning_frame.pack(side="left", padx=2)
                warning_label = ctk.CTkLabel(
                    warning_frame,
                    text="⚠️ Script not found",
                    text_color="orange"
                )
                warning_label.pack(side="left")

            is_favorite = script_name in self.favorites
            star_text = "★ Starred" if is_favorite else "☆ Add to Starred"
            
            favorite_button = ctk.CTkButton(
                frame,
                text=star_text,
                width=100,
                command=lambda s=script_name: self.toggle_favorite(tab_name, s)
            )
            favorite_button.pack(side="right", padx=5)

            if script_exists:
                self.radio_buttons[tab_name].append(radio_button)
                self.favorite_buttons[tab_name][script_name] = favorite_button
        
        # Store the frame for cleanup
        tab_frame._scrollable_frame = scrollable_frame

    def _create_script_buttons(self, parent_frame, tab_name: str, scripts: Dict[int, str]):
        """Create script buttons with virtual scrolling"""
        for widget in parent_frame.winfo_children():
            widget.destroy()

        start = self.virtual_scroll_state.start_index
        end = start + self.virtual_scroll_state.visible_items

        visible_scripts = {
            k: v for k, v in scripts.items()
            if isinstance(k, int) and start <= k <= end
        }

        for i, script_name in visible_scripts.items():
            self._create_single_script_buttons(parent_frame, tab_name, i, script_name)

        # Store tab_name on the frame and bind scroll
        parent_frame.tab_name = tab_name  # Add this line
        if not hasattr(parent_frame, '_scroll_bound'):
            parent_frame.bind_all("<MouseWheel>",
                                lambda e: self._handle_scroll(e, parent_frame, scripts))
            parent_frame._scroll_bound = True

    def _create_single_script_buttons(self, parent_frame, tab_name: str, index: int, script_name: str):
        frame = ctk.CTkFrame(parent_frame)
        frame.pack(fill="x", padx=5, pady=2)

        script_label = Path(script_name).stem
        script_exists = bool(self._get_script_path(script_name))

        radio_button = ctk.CTkRadioButton(
            frame,
            text=script_label,
            variable=self.tab_radio_vars[tab_name],
            value=index,
            command=lambda t=tab_name, v=index: self.on_radio_select(t, v),
            state="normal" if script_exists else "disabled",
            text_color="gray50" if not script_exists else None
        )
        radio_button.pack(side="left", padx=5)

        if not script_exists:
            warning_frame = ctk.CTkFrame(frame, fg_color="transparent")
            warning_frame.pack(side="left", padx=2)
            warning_label = ctk.CTkLabel(
                warning_frame,
                text="⚠️ Script not found",
                text_color="orange"
            )
            warning_label.pack(side="left")

        if tab_name == self.favorites_display_name:
            remove_button = ctk.CTkButton(
                frame,
                text="Remove from Starred",
                width=120,
                command=lambda s=script_name: self.remove_favorite(s, radio_button)
            )
            remove_button.pack(side="right", padx=5)
        else:
            is_favorite = script_name in self.favorites
            star_text = "★ Starred" if is_favorite else "☆ Add to Starred"
            
            favorite_button = ctk.CTkButton(
                frame,
                text=star_text,
                width=100,
                command=lambda s=script_name: self.toggle_favorite(tab_name, s)
            )
            favorite_button.pack(side="right", padx=5)

            # Store button reference
            if tab_name not in self.favorite_buttons:
                self.favorite_buttons[tab_name] = {}
            self.favorite_buttons[tab_name][script_name] = favorite_button

    def _handle_scroll(self, event, frame, scripts):
        """Handle scrolling for virtual list"""
        if not scripts:
            return

        # Calculate new start index
        delta = -1 if event.delta > 0 else 1
        new_start = max(0, min(
            self.virtual_scroll_state.start_index + delta,
            len(scripts) - self.virtual_scroll_state.visible_items
        ))

        # Update if changed
        if new_start != self.virtual_scroll_state.start_index:
            self.virtual_scroll_state.start_index = new_start
            self._create_script_buttons(frame, frame.tab_name, scripts)


    def cleanup(self):
        """Enhanced cleanup method"""
        try:
            # Stop background worker
            if hasattr(self, 'background_worker'):
                self.background_worker.shutdown()
            
            # Remove scroll bindings and destroy frames
            if hasattr(self, 'tabview'):
                for tab_name in self.tabview._tab_dict:
                    tab_frame = self.tabview.tab(tab_name)
                    if hasattr(tab_frame, '_scrollable_frame'):
                        tab_frame._scrollable_frame.unbind_all("<MouseWheel>")
                        tab_frame._scrollable_frame.unbind_all("<Button-4>")
                        tab_frame._scrollable_frame.unbind_all("<Button-5>")

            # Clear other resources
            if hasattr(self, '_categories'):
                self._categories.clear()
            if hasattr(self, '_tab_inited'):
                self._tab_inited.clear()

            # Clear GUI elements
            if hasattr(self, 'loading_overlay'):
                self.loading_overlay.destroy()

            # Clear any remaining widgets
            for widget in self.parent_tab.winfo_children():
                widget.destroy()

        except Exception as e:
            print(f"Error during cleanup: {e}")
            
    def _init_tab_configs(self):
        """Initialize tab configurations with optimized data structures"""
        self.tab_keywords = {
            "Favorites": frozenset(),
            "Themes": frozenset(),
            "Bezels & Effects": frozenset(["Bezel", "SCANLINE", "GLASS EFFECTS"]),
            "Overlays": frozenset(["OVERLAY"]),
            "InigoBeats": frozenset(["MUSIC"]),
            "Attract": frozenset(["Attract", "Scroll"]),
            "Monitor": frozenset(["Monitor", "MONITOR"]),  # Added uppercase variant
            "Splash": frozenset(["Splash"]),
            "Front End": frozenset(["FRONT END"]),
            "Other": frozenset()
        }

    def run_script_threaded(self, script_path: Path):
        """Modified to use background worker"""
        def script_task():
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(
                    ["cmd.exe", "/c", str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=script_path.parent,
                    startupinfo=startupinfo
                )
                stdout, stderr = process.communicate()
                return stdout, stderr, process.returncode
            except Exception as e:
                return None, str(e), -1

        def script_complete(future):
            try:
                stdout, stderr, returncode = future.result()
                if returncode != 0:
                    self.show_status(f"Script error: {stderr}", color="red")
                else:
                    self.show_status("Script completed successfully")
            finally:
                self.set_gui_state(True)

        self.set_gui_state(False)
        self.background_worker.submit_task(script_task, script_complete)

    def update_favorites_tab(self):
        """Update favorites tab with optimized GUI updates"""
        tab = self.tabview.tab(self.favorites_display_name)  # Changed from "Favorites"
        for widget in tab.winfo_children():
            widget.destroy()

        scrollable_frame = ctk.CTkScrollableFrame(tab, width=400, height=400)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        if self.favorites:
            run_all_frame = ctk.CTkFrame(scrollable_frame)
            run_all_frame.pack(fill="x", padx=5, pady=5)
            
            run_all_button = ctk.CTkButton(
                run_all_frame,
                text="Run All Favorites Sequentially",
                command=self.run_all_favorites
            )
            run_all_button.pack(fill="x", padx=5, pady=5)

        if not self.favorites:
            ctk.CTkLabel(scrollable_frame, text="No favorites added yet").pack(pady=10)
            return

        self.tab_radio_vars["Favorites"] = tk.IntVar(value=0)
        self.radio_buttons["Favorites"] = []
        self.radio_button_script_mapping["Favorites"] = {}

        for i, script_name in enumerate(self.favorites, 1):
            script_label = Path(script_name).stem
            script_exists = bool(self._get_script_path(script_name))
            
            frame = ctk.CTkFrame(scrollable_frame)
            frame.pack(fill="x", padx=5, pady=2)

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
                command=lambda s=script_name, b=radio_button: 
                    self.remove_favorite(s, b)
            )
            remove_button.pack(side="right", padx=5)

            if script_exists:
                self.radio_buttons["Favorites"].append(radio_button)
                self.radio_button_script_mapping["Favorites"][i] = script_name

    def run_script_threaded(self, script_path: Path):
        """Run script using background worker with platform support"""
        def script_task():
            try:
                script_path_str = str(script_path.resolve())
                cwd = script_path.parent.resolve()

                if sys.platform.startswith('win'):
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    # For Windows, directly execute the batch file
                    process = subprocess.Popen(
                        [script_path_str],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=cwd,
                        startupinfo=startupinfo,
                        shell=True  # Add shell=True for Windows
                    )
                else:
                    # Make script executable on Unix-like systems
                    os.chmod(script_path_str, 0o755)
                    process = subprocess.Popen(
                        ["/bin/bash", script_path_str],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=cwd
                    )
                
                stdout, stderr = process.communicate()
                print(f"Script output: {stdout}")
                print(f"Script error (if any): {stderr}")
                if process.returncode != 0:
                    print(f"Script exited with code: {process.returncode}")
                    
                return stdout, stderr, process.returncode

            except Exception as e:
                print(f"Error executing script: {e}")
                return None, str(e), -1

        def script_complete(future):
            try:
                stdout, stderr, returncode = future.result()
                # Always show success message to user regardless of errors
                self.show_status("Script completed successfully")
            finally:
                self.set_gui_state(True)

        self.set_gui_state(False)
        self.background_worker.submit_task(script_task, script_complete)

    async def run_script_async(self, script_path: Path) -> bool:
        """Run script asynchronously with platform support"""
        try:
            script_path_str = str(script_path.resolve())
            cwd = script_path.parent.resolve()

            if sys.platform.startswith('win'):
                process = await asyncio.create_subprocess_exec(
                    script_path_str,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    shell=True  # Add shell=True for Windows
                )
            else:
                # Make script executable on Unix-like systems
                os.chmod(script_path_str, 0o755)
                process = await asyncio.create_subprocess_exec(
                    "/bin/bash",
                    script_path_str,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
            
            stdout, stderr = await process.communicate()
            return True
            
        except Exception as e:
            print(f"Error running script: {e}")
            return False

    def set_gui_state(self, enabled: bool):
        """Update GUI state with minimal redraws"""
        for buttons in self.radio_buttons.values():
            for button in buttons:
                button.configure(state="normal" if enabled else "disabled")

        # Only show processing message when disabled
        if enabled:
            self.loading_label.pack_forget()
            # Show success message once processing is complete
            self.show_status("Script completed successfully")
        else:
            # Show started message in green instead of gray processing
            self.show_status("Script started...", duration=None)
        
        self.parent_tab.update_idletasks()

    def show_status(self, message: str, duration: int = 2000, color: str = "green"):
        """Show status with optimized animation"""
        # Hide any existing loading label first
        self.loading_label.pack_forget()
        
        # Configure and show the status
        self.status_label.configure(text=message, text_color=color)
        self.status_label.pack(side="bottom", pady=10)
        
        # Only do fade out if duration is specified
        if duration is not None:
            def fade_out(alpha: float = 1.0):
                if alpha <= 0:
                    self.status_label.pack_forget()
                    return
                
                if color.startswith('#'):
                    rgb = [int(int(color[i:i+2], 16) * alpha) for i in (1, 3, 5)]
                    color_with_alpha = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                    self.status_label.configure(text_color=color_with_alpha)
                
                self.parent_tab.after(50, lambda: fade_out(alpha - 0.1))
            
            self.parent_tab.after(duration, lambda: fade_out())

    def toggle_favorite(self, tab_name: str, script_name: str):
        """Toggle favorite status and update all relevant buttons"""
        is_now_favorite = script_name not in self.favorites
        
        if is_now_favorite:
            self.favorites.append(script_name)
            new_state = "★ Starred"
            #status_msg = f"Added '{Path(script_name).stem}' to Starred tab"
        else:
            self.favorites.remove(script_name)
            new_state = "☆ Add to Starred"
            #status_msg = f"Removed '{Path(script_name).stem}' from Starred tab"

        # Update all instances of this script's star button
        for tab_buttons in self.favorite_buttons.values():
            if script_name in tab_buttons:
                tab_buttons[script_name].configure(text=new_state)

        self._save_favorites()
        self.update_favorites_tab()
        #self.show_status(status_msg, duration=2000, color="#2ecc71")

    def remove_favorite(self, script_name: str, button: ctk.CTkRadioButton):
        """Remove from favorites and update buttons"""
        if script_name in self.favorites:
            self.favorites.remove(script_name)
            
            # Update all star buttons for this script
            for tab_buttons in self.favorite_buttons.values():
                if script_name in tab_buttons:
                    tab_buttons[script_name].configure(text="☆ Add to Starred")
            
            self._save_favorites()
            self.update_favorites_tab()
            #self.show_status(f"Removed '{Path(script_name).stem}' from Starred tab", 
                            #duration=2000, color="#2ecc71")

    def on_radio_select(self, tab_name: str, value: int):
        """Handle radio selection with optimized script execution"""
        if value not in self.radio_button_script_mapping[tab_name]:
            return

        script_name = self.radio_button_script_mapping[tab_name][value]
        script_path = self._get_script_path(script_name)

        if not script_path:
            messagebox.showerror("Error", f"Script not found: {script_name}")
            return

        self.set_gui_state(False)
        self.run_script_threaded(script_path)

    async def run_all_favorites_async(self):
        """Run all favorite scripts sequentially with progress tracking"""
        if not self.favorites or self.is_running_all:
            return

        self.is_running_all = True
        self.set_gui_state(False)
        
        # Filter to existing scripts
        existing_scripts = [
            script for script in self.favorites 
            if self._get_script_path(script)
        ]
        total_scripts = len(existing_scripts)
        
        if total_scripts == 0:
            self.show_status("No valid scripts found in favorites!", color="orange")
            self.is_running_all = False
            self.set_gui_state(True)
            return

        self.show_progress(True)
        completed = 0
        
        try:
            for script_name in existing_scripts:
                script_path = self._get_script_path(script_name)
                if script_path:
                    # Update progress before running script
                    self.update_progress(completed, total_scripts, script_name)
                    
                    # Run script and wait for completion
                    await self.run_script_async(script_path)
                    
                    # Update progress after script completion
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

    def show_progress(self, show: bool = True):
        """Show or hide the progress bar and label"""
        if show:
            self.progress_frame.pack(side="bottom", fill="x", padx=10, pady=5)
            self.progress_label.pack(pady=(0, 5))
            self.progress_bar.pack(fill="x", padx=10, pady=(0, 5))
        else:
            self.progress_frame.pack_forget()

    def update_progress(self, current: int, total: int, script_name: str):
        """Update progress bar and label"""
        progress = current / total if total > 0 else 0
        self.progress_bar.set(progress)
        self.progress_label.configure(
            text=f"Running {current}/{total}: {Path(script_name).stem}"
        )
        self.parent_tab.update_idletasks()

    def set_initial_tab(self):
        """Pick your initial tab if you want to open Favorites or Themes first."""
        if not self._tab_inited:
            return
        
        # 1) If you want Favorites first
        if self.favorites and "Favorites" in self._tab_inited:
            self.tabview.set(self.favorites_display_name)  # Changed from "Favorites"
            if not self._tab_inited["Favorites"]:
                self._lazy_init_tab("Favorites")
            return

        # 2) If you want Themes second
        if "Themes" in self._tab_inited:
            self.tabview.set("Themes")
            if not self._tab_inited["Themes"]:
                self._lazy_init_tab("Themes")
            return
        
        # 3) Otherwise just pick the first key
        try:
            first_tab = next(iter(self._tab_inited.keys()))
            self.tabview.set(first_tab)
            if not self._tab_inited[first_tab]:
                self._lazy_init_tab(first_tab)
        except (StopIteration, ValueError):
            pass

class FilterGames:
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        # Fix path separators for cross-platform compatibility
        self.output_dir = os.path.join('collections', 'Arcades')
        self.include_output_file = os.path.join(self.output_dir, "include.txt")
        self.exclude_output_file = os.path.join(self.output_dir, "exclude.txt")
        self.playlist_location = 'U'

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

        # Load DLL and CSV with proper path handling
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
        self.buttons_var.trace_add('write', lambda *args: self.update_filtered_list())
        button_options = ["Select number of buttons", "0", "1", "2", "3", "4", "5", "6"]
        buttons_label = ctk.CTkLabel(buttons_tab, text="Number of Buttons", font=("Arial", 14, "bold"))
        buttons_label.pack(pady=(10,5))
        buttons_dropdown = ctk.CTkOptionMenu(buttons_tab, variable=self.buttons_var, values=button_options)
        buttons_dropdown.pack(padx=20, pady=5)

        # Players tab content
        self.players_var = ctk.StringVar(value="Select number of players")
        self.players_var.trace_add('write', lambda *args: self.update_filtered_list())
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

        # Toggle button frame
        toggle_frame = ctk.CTkFrame(sidebar_frame)
        toggle_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        # Toggle button
        self.toggle_var = tk.StringVar(value="Switch to Exclude Options")
        toggle_button = ctk.CTkButton(toggle_frame, textvariable=self.toggle_var, command=self.toggle_mode)
        toggle_button.pack(pady=(0, 5), fill='x')

        # Include Games frame
        self.include_frame = ctk.CTkFrame(sidebar_frame)
        self.include_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        # Include Games buttons
        filter_button = ctk.CTkButton(self.include_frame, text="Save Filter", command=self.filter_games_from_csv, fg_color="#4CAF50", hover_color="#45A049")
        filter_button.pack(pady=(0, 5), fill='x')

        clear_filters_button = ctk.CTkButton(self.include_frame, text="Clear Filters",
                                           command=self.clear_filters)
        clear_filters_button.pack(pady=(0, 5), fill='x')

        show_all_button = ctk.CTkButton(self.include_frame, text="Reset to Default",
                                       command=self.show_all_games, fg_color="red")
        show_all_button.pack(fill='x')

        # Exclude Games frame
        self.exclude_frame = ctk.CTkFrame(sidebar_frame)

        # Exclude Games buttons
        exclude_button = ctk.CTkButton(self.exclude_frame, text="Exclude Games",
                                           command=self.exclude_games_from_csv, fg_color="#4CAF50", hover_color="#45A049")
        exclude_button.pack(pady=(0, 5), fill='x')

        clear_filters_button = ctk.CTkButton(self.exclude_frame, text="Clear Filters",
                                           command=self.clear_filters)
        clear_filters_button.pack(pady=(0, 5), fill='x')

        reset_exclude_button = ctk.CTkButton(self.exclude_frame, text="Reset Exclude to Default",
                                              command=self.reset_exclude_to_default, fg_color="red")
        reset_exclude_button.pack(pady=(0, 5), fill='x')

        # Initially show the Include Games frame
        self.include_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        # Create right side games list
        # Add a search entry at the top
        search_frame = ctk.CTkFrame(right_frame)
        search_frame.pack(fill='x', padx=5, pady=5)

        search_label = ctk.CTkLabel(search_frame, text="Search Games:")
        search_label.pack(side='left', padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *args: self.update_filtered_list())
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

    def toggle_mode(self):
        if self.toggle_var.get() == "Switch to Exclude Options":
            self.toggle_var.set("Switch to Include Options")
            self.include_frame.pack_forget()
            self.exclude_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        else:
            self.toggle_var.set("Switch to Exclude Options")
            self.exclude_frame.pack_forget()
            self.include_frame.pack(side='bottom', fill='x', padx=10, pady=10)

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

            # Read existing exclude file to check for duplicates
            existing_excludes = set()
            if os.path.exists(self.exclude_output_file):
                with open(self.exclude_output_file, 'r', encoding='utf-8') as f:
                    existing_excludes = set(line.strip() for line in f if line.strip())

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

                    # Check if the ROM is in the exclude list
                    if rom_name in existing_excludes:
                        continue

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
                initialdir=PathManager.get_base_path(),
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
        """Load custom DLL with cross-platform path handling"""
        if sys.platform.startswith('win'):  # Only load DLL on Windows
            dll_path = os.path.join(os.path.dirname(sys.argv[0]), 'autochanger', 'python', 'VCRUNTIME140.dll')
            print(f"Checking DLL path: {dll_path}")
            ctypes.windll.kernel32.SetDllDirectoryW(os.path.dirname(dll_path))
            if os.path.exists(dll_path):
                ctypes.windll.kernel32.LoadLibraryW(dll_path)
                print("Custom DLL loaded successfully.")
            else:
                print("Custom DLL not found.")

    def get_csv_file_path(self):
        """Get CSV file path with cross-platform compatibility"""
        # Check for external CSV in autochanger folder
        autochanger_csv_path = os.path.join('autochanger', 'META.csv')
        if os.path.exists(autochanger_csv_path):
            return os.path.abspath(autochanger_csv_path)

        # If not found, use bundled CSV
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

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
        """Check and create output directory if needed"""
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir, exist_ok=True)
                print(f"Created output directory: {self.output_dir}")
            except Exception as e:
                messagebox.showerror("Error", 
                    f"Could not create output directory: {self.output_dir}\nError: {str(e)}")
                self.parent_tab.quit()
                sys.exit()

    # Method to scan collections for ROMs
    def scan_collections_for_roms(self):
        """Scan collections with cross-platform path handling"""
        root_dir = PathManager.get_base_path()
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

                with open(settings_path, 'r', encoding='utf-8') as settings_file:
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

        return set(rom_list)

    # Updated filter_games_from_csv method
    def filter_games_from_csv(self):
        self.status_bar.configure(text="Saving filters...")
        self.check_output_dir()
        roms_in_build = self.scan_collections_for_roms()

        try:
            # Read existing exclude file to check for duplicates
            existing_excludes = set()
            if os.path.exists(self.exclude_output_file):
                with open(self.exclude_output_file, 'r', encoding='utf-8') as f:
                    existing_excludes = set(line.strip() for line in f if line.strip())

            with open(self.csv_file_path, newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                with open(self.include_output_file, 'w', encoding='utf-8') as f:
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

                        # Check if the ROM is in the exclude list
                        if rom_name in existing_excludes:
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
                        self.status_bar.configure(text=f"Saved {game_count} games to filter")

        except Exception as e:
            messagebox.showerror("Error", f"Error opening CSV file: {e}")


    def exclude_games_from_csv(self):
        self.status_bar.configure(text="Excluding games...")
        self.check_output_dir()
        roms_in_build = self.scan_collections_for_roms()

        try:
            # Read existing exclude file to check for duplicates
            existing_excludes = set()
            if os.path.exists(self.exclude_output_file):
                with open(self.exclude_output_file, 'r', encoding='utf-8') as f:
                    existing_excludes = set(line.strip() for line in f if line.strip())

            with open(self.csv_file_path, newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                with open(self.exclude_output_file, 'a', encoding='utf-8') as f:
                    game_count = 0
                    already_excluded_count = 0
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
                                    if rom_name not in existing_excludes:
                                        f.write(f"{rom_name}\n")
                                        game_count += 1
                                    else:
                                        already_excluded_count += 1
                                    break
                        else:
                            if rom_name not in existing_excludes:
                                f.write(f"{rom_name}\n")
                                game_count += 1
                            else:
                                already_excluded_count += 1

                    # Feedback for users
                    if game_count == 0 and already_excluded_count == 0:
                        messagebox.showinfo("No Games Found", "No games matched the selected filters.")
                        self.status_bar.configure(text="No games matched filters")
                    else:
                        feedback_message = f"Excluded {game_count} games from filter."
                        if already_excluded_count > 0:
                            feedback_message += f" {already_excluded_count} games were already excluded."
                        self.status_bar.configure(text=feedback_message)

        except Exception as e:
            messagebox.showerror("Error", f"Error opening CSV file: {e}")

    def reset_exclude_to_default(self):
        self.status_bar.configure(text="Resetting exclude to default...")
        try:
            if os.path.exists(self.exclude_output_file):
                os.remove(self.exclude_output_file)
                self.status_bar.configure(text=f"Exclude file deleted successfully.")
            else:
                self.status_bar.configure(text=f"Exclude file does not exist.")

        except Exception as e:
            messagebox.showerror("Error", f"Error resetting exclude to default: {e}")
            self.status_bar.configure(text=f"Error resetting exclude to default: {e}")

    def show_all_games(self):
        """Reset to default with proper path handling"""
        self.status_bar.configure(text="Resetting to default...")
        try:
            source = os.path.join("autochanger", "include.txt")
            destination = os.path.join("collections", "Arcades", "include.txt")

            if os.path.exists(source):
                # Ensure destination directory exists
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copyfile(source, destination)
                print(f"Success: Copied '{source}' to '{destination}'.")
                self.status_bar.configure(text=f"Successfully reset to default games list.")
            else:
                if os.path.exists(destination):
                    os.remove(destination)
                    print(f"Success: '{destination}' has been deleted.")
                    self.status_bar.configure(text="Successfully removed custom games list.")
                else:
                    print(f"Info: No file to delete. '{destination}' does not exist.")
                    self.status_bar.configure(text="No custom games list found.")

        except Exception as e:
            print(f"Error: Failed to process files: {str(e)}")
            self.status_bar.configure(text=f"Failed to process files: {str(e)}")

class Playlists:
    def __init__(self, root, parent_tab):
        self.root = root
        self.parent_tab = parent_tab
        self.base_path = PathManager.get_base_path()
        self.playlists_path = os.path.join(self.base_path, "collections", "Arcades", "playlists")
        
        # Initialize the configuration manager
        self.config_manager = ConfigManager()
        
        # Get playlist location setting from INI
        self.playlist_location = self.config_manager.get_playlist_location()  # Should return 'S', 'D', or 'U'
        
        # Set up paths
        if self.playlist_location == 'U':
            # Use Universe settings file
            self.settings_file_path = os.path.join(self.base_path, "collections", "Arcades", "settings.conf")
            self.custom_settings_path = os.path.join(self.base_path, "autochanger", "settingsCustomisation.conf")
            self.autochanger_conf_path = self.custom_settings_path
        else:
            # Original behavior - use settings file from config
            settings_file = self.config_manager.get_settings_file()
            self.settings_file_path = os.path.join(self.base_path, "autochanger", settings_file)
            self.autochanger_conf_path = self.settings_file_path     
        
        self.check_vars = []
        self.check_buttons = []
        self.excluded_playlists = self.config_manager.get_excluded_playlists()
        self.manufacturer_playlists = ["atari", "capcom", "cave", "data east", "irem", "konami", "midway", "namco", "neogeo", "nintendo", "psikyo", "raizing", "sega", "snk", "taito", "technos", "tecmo", "toaplan", "williams"]
        self.sort_type_playlists = ["ctrltype", "manufacturer", "numberplayers", "year"]
        
        # Define playlists to exclude from genres
        self.excluded_from_genres = ["vertical", "horizontal"]  # Add your playlists here

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
            text="Show Selected Playlists",
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
            
            # Use self.get_cycle_playlist() instead of self.config_manager.get_cycle_playlist()
            if self.playlist_location == 'U':
                default_playlists = ["all", "favorites", "lastplayed"]
            else:
                default_playlists = self.config_manager.get_cycle_playlist()
            
            with open(target_file, 'r') as file:
                lines = file.readlines()

            cycle_playlist_found = False
            updated_lines = []
            
            for line in lines:
                if line.startswith("cyclePlaylist ="):
                    # Combine default playlists with selected playlists
                    new_line = f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n"
                    updated_lines.append(new_line)
                    cycle_playlist_found = True
                else:
                    updated_lines.append(line)

            # Add cyclePlaylist if not found
            if not cycle_playlist_found:
                new_line = f"cyclePlaylist = {', '.join(default_playlists)}, {', '.join(playlist_list)}\n"
                updated_lines.append(new_line)

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
            if name not in self.sort_type_playlists and name not in self.manufacturer_playlists and name not in self.excluded_from_genres]

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
        """Check if backup settings file exists and update reset button state."""
        try:
            if self.playlist_location == 'U':
                # For 'U' location, always enable the reset defaults button
                self.reset_button.configure(state="normal")
            else:
                # For 'S' and 'D', check if backup exists
                current_settings = self.config_manager.get_settings_file()
                backup_file = current_settings.replace(".conf", "x.conf")
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
        """Reset the settings based on playlist location setting."""
        try:
            if self.playlist_location == 'U':
                # For 'U' mode, update CyclePlaylist with a hardcoded value
                try:
                    hardcoded_cycle_playlist = (
                        "all,favorites,lastplayed,01 old school,02 beat em up,03 run n gun, "
                        "04 fight club,05 shoot n up,06 racer,year,manufacturer,ctrltype,numberplayers"
                    )
                    settings_file_path = os.path.join(self.base_path, "collections", "Arcades", "settings.conf")
                    
                    if os.path.exists(settings_file_path):
                        # Update CyclePlaylist in settings.conf
                        self.update_cycle_playlist_value(settings_file_path, hardcoded_cycle_playlist)
                        self.show_status_message("✓ CyclePlaylist successfully reset to custom value")
                    else:
                        self.show_status_message("⚠️ settings.conf not found in collections/Arcades")
                except Exception as e:
                    self.show_status_message(f"⚠️ Error during reset for U: {str(e)}")
            else:
                # Common behavior for 'S' and 'D' modes
                current_settings = self.config_manager.get_settings_file()
                backup_file = current_settings.replace(".conf", "x.conf")
                backup_conf_path = os.path.join(self.base_path, "autochanger", backup_file)
                
                if os.path.exists(backup_conf_path):
                    shutil.copy2(backup_conf_path, self.autochanger_conf_path)
                    self.show_status_message("✓ Playlists have been reset successfully")
                else:
                    self.show_status_message("⚠️ Backup configuration file not found")
        except Exception as e:
            self.show_status_message(f"⚠️ Error during reset: {str(e)}")

    def update_cycle_playlist_value(self, file_path, new_value):
        """Update the cyclePlaylist value in the configuration file."""
        try:
            updated_lines = []
            found = False

            with open(file_path, "r") as file:
                for line in file:
                    if line.strip().startswith("cyclePlaylist ="):
                        updated_lines.append(f"cyclePlaylist = {new_value}\n")
                        found = True
                    else:
                        updated_lines.append(line)

            # If CyclePlaylist was not found, add it to the file
            if not found:
                updated_lines.append(f"cyclePlaylist = {new_value}\n")

            # Write the updated configuration back to the file
            with open(file_path, "w") as file:
                file.writelines(updated_lines)
        except Exception as e:
            raise Exception(f"Failed to update cyclePlaylist: {str(e)}")
        
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
                                self.parent.after(0, self._safe_update_entry, button_name, friendly_name, "controller")

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

    def handle_keyboard_input(self):
        """Monitor keyboard input until a key is pressed or capture is stopped."""
        print("Keyboard monitoring started")
        
        # List of keys to exclude from capture (lowercase for comparison)
        excluded_keys = ['pause', 'next', 'prev', 'volumeup', 'volumedown', 's', 'f1', 'f2', 
                        'numpad 8', 'numpad 2', 'numpad 4', 'numpad 6',',','.','[',']',"'"]
        
        try:
            while not self.stop_event.is_set():
                event = keyboard.read_event(suppress=True)
                if event.event_type == keyboard.KEY_DOWN:
                    # Keep comparison lowercase, but display in uppercase
                    key_name_lower = event.name.lower()
                    key_name_display = event.name.capitalize()
                    print(f"Got keyboard input: {key_name_display}")

                    # Check if the key is in the excluded list
                    if key_name_lower in excluded_keys:
                        print(f"{key_name_display} key pressed: Excluded from capture")
                        self.show_status_message(f"{key_name_display} key is excluded.\nPlease make another selection.")
                        continue

                    # Escape key handler
                    if key_name_lower == "esc":
                        print("Escape key pressed, canceling capture")
                        self.stop_event.set()  # Signal stop event
                        self.parent.after(0, self.stop_capture)  # Safely stop capture from GUI context
                        return

                    # If not an excluded or reserved key, proceed with capture
                    self.stop_event.set()
                    self.parent.after(0, self._safe_update_entry, key_name_display, key_name_display, "keyboard")
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
            text="Show Xinput Friendly Names",
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
            ("Save Controls:", "When you click 'Save Controls,' the controls5.conf file will be created."),
            ("Excluded Controls:", "Certain buttons and keys are not allowed as they are locked in for other controls that should not be changed. A prompt will show, asking you to try another selection.")
        ]

        # Add each instruction item to the scrollable frame
        for heading, explanation in instructions:
            heading_label = ctk.CTkLabel(
                content_frame,
                text=heading,
                font=("Arial", 16, "bold"),
                wraplength=750,  # Set the wrap length to ensure text fits within the frame
                anchor="w"  # Align text to the left
            )
            heading_label.pack(anchor="w", pady=(5, 0))

            explanation_label = ctk.CTkLabel(
                content_frame,
                text=explanation,
                font=("Arial", 14),
                wraplength=750,  # Set the wrap length to ensure text fits within the frame
                anchor="w",  # Align text to the left
                justify="left"  # Ensure text is left-justified
            )
            explanation_label.pack(anchor="w", pady=(0, 10))

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
        """Refresh all entry displays based on current name display mode."""
        for key, entry in self.control_entries.items():
            internal_values = self.controls_config[key]
            display_values = []

            for value in internal_values:
                # If it's "joyButton###", we assume it's from a controller
                if value.startswith("joyButton"):
                    if self.show_friendly_names:
                        # Convert from internal "joyButtonN" to short label A/B/X/Y, etc.
                        button_code = self.reverse_button_map.get(value)  # e.g. "BTN_SOUTH"
                        if button_code:
                            # e.g. "A", "B", "X", etc.
                            friendly_label = self.friendly_names.get(button_code, value)
                            display_values.append(f"🎮{friendly_label}")  # Controller icon prefix
                        else:
                            # fallback if not in reverse_button_map
                            display_values.append(f"🎮{value}")  # Controller icon prefix
                    else:
                        # Not showing friendly names → display e.g. "joyButton0"
                        display_values.append(f"🎮{value}")  # Controller icon prefix

                else:
                    # Otherwise assume it's a keyboard input - no prefix
                    display_values.append(value)

            # Now update the GUI Entry
            entry.delete(0, "end")
            entry.insert(0, ', '.join(display_values))


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
        #print(f"Created control frame for: {control_name}")

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

    def _safe_update_entry(self, input_name, friendly_name, device_type=None):
        """
        Called via self.parent.after(...).
        device_type can be "keyboard", "controller", or None.
        Uses '🎮' for controller inputs to distinguish them.
        """
        print(f"_safe_update_entry called with input_name={input_name}, "
            f"friendly_name={friendly_name}, device_type={device_type}, "
            f"show_friendly_names={self.show_friendly_names}")

        if self.current_control and input_name:
            entry = self.control_entries[self.current_control]
            entry.configure(state="normal")

            # Store the internal name in controls_config (for saving)
            internal_name = input_name
            self.controls_config[self.current_control].append(internal_name)

            # Determine display name:
            # For controller inputs, add 🎮 prefix
            # For keyboard inputs, just show the key name
            if device_type == "keyboard":
                display_name = friendly_name  # No prefix for keyboard
            elif device_type == "controller":
                if self.show_friendly_names:
                    display_name = f"🎮{friendly_name}"   # Controller icon prefix
                else:
                    display_name = f"🎮{internal_name}"   # Controller icon prefix
            else:
                # Fallback if device_type is somehow None or unknown
                if self.show_friendly_names:
                    display_name = friendly_name
                else:
                    display_name = internal_name

            # Grab current text from the Entry and split by comma
            current_display = entry.get().split(', ')
            if current_display == ['']:
                current_display = []

            # Append the new display name
            current_display.append(display_name)

            # Update the Entry widget
            entry.delete(0, "end")
            entry.insert(0, ', '.join(current_display))

            # Revert the Entry border color to indicate capture is complete
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
        """Load configuration from specified file with cross-platform path handling"""
        self.controls_config.clear()
        
        # Get the absolute path using ConfigManager's base path
        config_path = os.path.join(self.config_manager.base_path, filename)
        print(f"Loading controls from: {config_path}")
        
        try:
            with open(config_path, "r", encoding='utf-8') as f:
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
                            continue
                            
                        value = parts[1].strip()
                        self.controls_config[key] = [v.strip() for v in value.split(',')]

                    except Exception as e:
                        print(f"Error processing line {line_number}: {line}\nError: {str(e)}")
                        continue

            print(f"Successfully loaded configuration from {config_path}")
        except FileNotFoundError:
            print(f"Config file not found: {config_path}")
            raise
        except Exception as e:
            print(f"Error loading config file: {e}")
            raise

    def save_config(self):
        """Save configuration to specified controls file using cross-platform paths"""
        controls_file = self.config_manager.get_controls_file()
        config_path = os.path.join(self.config_manager.base_path, controls_file)
        
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, "w", encoding='utf-8') as f:
                controls_add = self.config_manager.get_controls_add()
                for key, values in self.controls_config.items():
                    if key not in self.excluded_controls or key in controls_add:
                        f.write(f"{key}={','.join(values)}\n")
            self.show_status_message("Controls saved successfully!")
            print(f"Controls saved to: {config_path}")
        except Exception as e:
            error_msg = f"Failed to save controls: {e}"
            print(error_msg)
            self.show_status_message(error_msg)

    def create_default_config(self):
        """Creates controls5.conf by copying from root-level controls.conf with cross-platform paths"""
        try:
            # Get paths using ConfigManager's base path
            root_conf_path = os.path.join(self.config_manager.base_path, "controls.conf")
            new_conf_path = os.path.join(self.config_manager.base_path, "controls5.conf")
            
            print(f"Creating default config:")
            print(f"Source: {root_conf_path}")
            print(f"Destination: {new_conf_path}")

            if os.path.exists(root_conf_path):
                with open(root_conf_path, "r", encoding='utf-8') as root_conf:
                    contents = root_conf.read()

                # Ensure the directory exists
                os.makedirs(os.path.dirname(new_conf_path), exist_ok=True)
                
                with open(new_conf_path, "w", encoding='utf-8') as new_conf:
                    new_conf.write(contents)
                print("controls5.conf created from root-level controls.conf")
            else:
                print("controls.conf not found, creating with defaults")
                with open(new_conf_path, "w", encoding='utf-8') as new_conf:
                    for key, default_values in self.controls_config.items():
                        new_conf.write(f"{key}={','.join(default_values)}\n")
                print("controls5.conf created with internal defaults")

        except Exception as e:
            print(f"Failed to create controls5.conf: {str(e)}")

    def reset_to_defaults(self):
        """Reset control settings to defaults using cross-platform paths"""
        try:
            # Get the path to controls.conf using ConfigManager's base path
            root_conf_path = os.path.join(self.config_manager.base_path, "controls.conf")
            print(f"Loading defaults from: {root_conf_path}")
            
            with open(root_conf_path, "r", encoding='utf-8') as root_conf:
                contents = root_conf.readlines()

            # Parse and apply values from the root config file
            for line in contents:
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue

                try:
                    parts = line.split('=', 1)
                    if len(parts) != 2:
                        print(f"Warning: Invalid format in line: {line}")
                        continue

                    key = parts[0].strip()
                    value = parts[1].strip()
                    internal_values = [v.strip() for v in value.split(',') if v.strip()]

                    if key in self.control_entries:
                        self.controls_config[key] = internal_values
                        display_values = []
                        for val in internal_values:
                            if val.startswith('joyButton') and self.show_friendly_names:
                                button_code = self.reverse_button_map.get(val)
                                if button_code:
                                    friendly_name = self.friendly_names.get(button_code, val)
                                    display_values.append(f"🎮{friendly_name}")
                                else:
                                    display_values.append(f"🎮{val}")
                            else:
                                display_values.append(val)

                        # Update the entry display
                        self.control_entries[key].delete(0, "end")
                        self.control_entries[key].insert(0, ', '.join(display_values))
                except Exception as e:
                    print(f"Error processing line: {line}\nError: {str(e)}")
                    continue

            print("Settings reset to defaults from controls.conf")
            self.show_status_message("Controls reset to defaults from controls.conf")

        except FileNotFoundError:
            print(f"controls.conf not found at {root_conf_path}. Using internal defaults.")
            self.reset_to_internal_defaults()
        except Exception as e:
            error_msg = f"Failed to reset controls to defaults: {str(e)}"
            print(error_msg)
            self.show_status_message(error_msg)

    def reset_to_internal_defaults(self):
        """Reset to internal defaults when controls.conf is not found"""
        for key, default_values in self.controls_config.items():
            if key in self.control_entries:
                self.controls_config[key] = default_values
                display_values = []
                for val in default_values:
                    if val.startswith('joyButton') and self.show_friendly_names:
                        button_code = self.reverse_button_map.get(val)
                        if button_code:
                            friendly_name = self.friendly_names.get(button_code, val)
                            display_values.append(f"🎮{friendly_name}")
                        else:
                            display_values.append(f"🎮{val}")
                    else:
                        display_values.append(val)

                self.control_entries[key].delete(0, "end")
                self.control_entries[key].insert(0, ', '.join(display_values))

        self.show_status_message("Controls reset to internal defaults")

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

class ViewRoms:
    def __init__(self, parent_tab, config_manager, main_app):
        # Define font settings at the top of the class
        self.list_font = ("Arial", 14)  # Changed from 12 to 14
        self.label_font = ("Arial", 12)   # Added for labels
        self.button_font = ("Arial", 12)  # Added for buttons
        self.config_manager = config_manager
        self.rom_list = []  # Ensure this is initialized
        self.rom_descriptions = {}  # Make sure this is initialized
        self.parent_tab = parent_tab
        self.main_app = main_app  # Store reference to main app
        # Add this line with your other initializations
        self.buttons = {}

        # Main container
        main_container = ctk.CTkFrame(self.parent_tab)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # Filter controls frame
        filter_frame = ctk.CTkFrame(main_container)
        filter_frame.pack(fill='x', padx=5, pady=5)

        # Collection dropdown with custom font
        collection_label = ctk.CTkLabel(filter_frame, text="Collection:", font=self.label_font)
        collection_label.pack(side='left', padx=5)

        self.collection_var = tk.StringVar(value="All Collections")
        self.collection_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.collection_var,
            values=["All Collections"],
            command=self.handle_collection_change,
            font=self.button_font  # Added font for dropdown
        )
        self.collection_dropdown.pack(side='left', padx=5)

        # Search frame with custom fonts
        search_frame = ctk.CTkFrame(main_container)
        search_frame.pack(fill='x', padx=5, pady=5)

        search_label = ctk.CTkLabel(search_frame, text="Search ROMs:", font=self.label_font)
        search_label.pack(side='left', padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.filter_roms)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, font=self.button_font)
        search_entry.pack(side='left', fill='x', expand=True, padx=5)

        # Button frame with custom fonts
        # Button frame with custom fonts
        self.button_frame = ctk.CTkFrame(search_frame)  # Use self.button_frame instead of button_frame
        self.button_frame.pack(side='right', padx=5)
        
        # Sort toggle with custom font
        self.sort_var = tk.StringVar(value="Name")
        self.sort_toggle = ctk.CTkSegmentedButton(
            self.button_frame,
            values=["Name", "Collection"],
            variable=self.sort_var,
            command=self.handle_sort_change,
            font=self.button_font  # Added font for toggle
        )
        self.sort_toggle.pack(side='right', padx=(0, 5))

        # Clear filters button with custom font
        clear_button = ctk.CTkButton(
            self.button_frame,
            text="Clear All",
            command=self.clear_filters,
            width=70,
            font=self.button_font  # Added font for button
        )
        clear_button.pack(side='right', padx=5)

        # ROM list frame
        list_frame = ctk.CTkFrame(main_container)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # ROM listbox with custom font
        self.rom_listbox = ctk.CTkTextbox(
            list_frame,
            font=self.list_font  # Using the custom list font
        )
        self.rom_listbox.pack(fill='both', expand=True, side='left')

        # Status bar with custom font
        self.status_bar = ctk.CTkLabel(
            main_container,
            text="Ready",
            anchor='w',
            font=self.label_font  # Added font for status bar
        )
        self.status_bar.pack(fill='x', padx=5, pady=(5, 0))

        # Store collections data
        self.rom_list = []
        self.rom_collections = {}
        self.rom_descriptions = {}
        self.rom_file_names = {}  # Store actual file names

        # Populate ROM list and collection dropdown
        self.load_initial_data()

        # Pack buttons based on visibility setting
        self.update_button_visibility()

        # Then when you're setting up your UI, call your button creation
        self.create_buttons()

    def create_buttons(self):
        button_configs = {
            'show_move_artwork_button': {
                'text': "Move Artwork",
                'command': lambda: self.show_instructions_popup('show_move_artwork_button')
            },
            'show_move_roms_button': {
                'text': "Move ROMs From TXT",
                'command': lambda: self.show_instructions_popup('show_move_roms_button')
            },
            'show_remove_random_roms_button': {
                'text': "Remove Random ROMs",
                'command': self.remove_random_roms
            },
            'remove_games_button': {
                'text': "Remove Games",
                'command': self.select_games_to_remove
            },
            'create_playlist_button': {
                'text': "Create Playlist",
                'command': self.create_playlist
            },
            'export_collections_button': {
                'text': "Export Collections",
                'command': self.export_collections_data
            }
        }

        for button_name, config in button_configs.items():
            # Debug prints
            #print(f"\nChecking button {button_name}")
            visibility = self.config_manager.determine_button_visibility(button_name)
            #print(f"Visibility value returned: {visibility}")

            if visibility:  # Will be True only when visibility is 'always'
                #print(f"Creating button {button_name}")
                self.buttons[button_name] = ctk.CTkButton(
                    self.button_frame,
                    text=config['text'],
                    command=config['command'],
                    width=100,
                    font=self.button_font
                )
                self.buttons[button_name].pack(side='right', padx=5)

    def create_playlist(self):
        """Open a window to select games to add to a new playlist"""
        try:
            # Get the selected collection
            selected_collection = self.collection_var.get()
            if selected_collection == "All Collections":
                messagebox.showerror("Error", "Please select a specific collection.")
                return

            # Pre-filter ROMs and get their base names
            filtered_roms = []
            for full_rom in self.rom_list:
                if f"({selected_collection})" in full_rom:
                    # Get the actual ROM name (without collection)
                    base_rom = full_rom.rsplit(' (', 1)[0]  # This only removes the collection name
                    # Get the description for display
                    # First try with just the game name (before any parentheses)
                    simple_name = base_rom.split(" (")[0]
                    desc = self.rom_descriptions.get(simple_name)
                    if desc is None:
                        # If no description found in CSV, use the full ROM name including all parenthetical info
                        desc = base_rom
                    filtered_roms.append((base_rom, desc, full_rom))
            
            filtered_roms.sort(key=lambda x: x[1].lower())

            # Create window
            select_window = tk.Toplevel(self.parent_tab)
            select_window.title(f"Create Playlist - {selected_collection}")
            select_window.configure(bg='#2c2c2c')

            # Window sizing
            screen_width = select_window.winfo_screenwidth()
            screen_height = select_window.winfo_screenheight()
            window_width = int(screen_width * 0.4)
            window_height = int(screen_height * 0.6)
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            select_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # Main container - set dark background color
            main_frame = ctk.CTkFrame(select_window, fg_color='#2c2c2c')
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)

            # Add playlist name input
            name_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            name_frame.pack(fill='x', padx=5, pady=5)

            name_label = ctk.CTkLabel(name_frame, text="Playlist Name:", font=self.label_font)
            name_label.pack(side='left', padx=5)

            playlist_name_var = tk.StringVar()
            name_entry = ctk.CTkEntry(name_frame, textvariable=playlist_name_var, font=self.button_font)
            name_entry.pack(side='left', fill='x', expand=True, padx=5)

            # Add search functionality
            search_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            search_frame.pack(fill='x', padx=5, pady=5)

            search_label = ctk.CTkLabel(search_frame, text="Search:", font=self.label_font)
            search_label.pack(side='left', padx=5)

            search_var = tk.StringVar()
            search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, font=self.button_font)
            search_entry.pack(side='left', fill='x', expand=True, padx=5)

            # Create list frame with fixed height and dark background
            list_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            list_frame.pack(fill='both', expand=True, padx=5, pady=5)

            # Use a Treeview for game selection
            tree = ttk.Treeview(list_frame, selectmode='none', show='tree')
            tree.pack(side='left', fill='both', expand=True)

            # Configure Treeview style for dark theme
            style = ttk.Style()
            style.map('Treeview', background=[('selected', '#2c2c2c')])
            style.configure("Treeview", 
                        background="#2c2c2c", 
                        foreground="white", 
                        fieldbackground="#2c2c2c",
                        font=('TkDefaultFont', 12))
            style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
            style.configure("Treeview.Heading", 
                        background="#2c2c2c", 
                        foreground="white",
                        font=('TkDefaultFont', 12))
            
            tree.tag_configure('custom', font=('TkDefaultFont', 12))
            tree.tag_configure('checked', background='#2d5a27')
            tree.tag_configure('unchecked', background='#2c2c2c')

            # Add scrollbar
            scrollbar = ctk.CTkScrollbar(list_frame, command=tree.yview)
            scrollbar.pack(side='right', fill='y')
            tree.configure(yscrollcommand=scrollbar.set)

            # Tracking dictionaries
            checked_items = {}
            item_to_rom = {}
            desc_to_display = {}

            def toggle_check(event):
                item = tree.identify_row(event.y)
                if item:
                    checked_items[item] = not checked_items.get(item, False)
                    if checked_items[item]:
                        tree.item(item, text="☒ " + desc_to_display[item], tags=('custom', 'checked'))
                    else:
                        tree.item(item, text="☐ " + desc_to_display[item], tags=('custom', 'unchecked'))

            tree.bind('<Button-1>', toggle_check)

            def update_list(search_text=''):
                tree.delete(*tree.get_children())
                search_text = search_text.lower()
                
                visible_items = [
                    (base_rom, desc, full_rom) for base_rom, desc, full_rom in filtered_roms
                    if search_text in desc.lower() or search_text in base_rom.lower()
                ]

                for rom_name, desc, full_rom in visible_items:
                    item = tree.insert('', 'end', text="☐ " + desc, tags=('custom', 'unchecked'))
                    checked_items[item] = False
                    desc_to_display[item] = desc
                    # Store the actual ROM name for the playlist file
                    item_to_rom[item] = rom_name

            search_after_id = None
            def on_search(*args):
                nonlocal search_after_id
                if search_after_id:
                    select_window.after_cancel(search_after_id)
                search_after_id = select_window.after(150, lambda: update_list(search_var.get()))

            search_var.trace_add('write', on_search)

            # Button frame
            button_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            button_frame.pack(fill='x', pady=5)

            def select_all():
                for item in tree.get_children():
                    checked_items[item] = True
                    tree.item(item, text="☒ " + desc_to_display[item], tags=('custom', 'checked'))

            def select_none():
                for item in tree.get_children():
                    checked_items[item] = False
                    tree.item(item, text="☐ " + desc_to_display[item], tags=('custom', 'unchecked'))

            select_all_btn = ctk.CTkButton(
                button_frame,
                text="Select All",
                command=select_all,
                font=self.button_font
            )
            select_all_btn.pack(side='left', padx=5)

            select_none_btn = ctk.CTkButton(
                button_frame,
                text="Select None",
                command=select_none,
                font=self.button_font
            )
            select_none_btn.pack(side='left', padx=5)

            on_close = self.main_app.show_popup(select_window)

            def create_playlist_file():
                playlist_name = playlist_name_var.get().strip()
                if not playlist_name:
                    messagebox.showerror("Error", "Please enter a playlist name.")
                    return
                    
                selected_items = [item for item, checked in checked_items.items() if checked]
                if not selected_items:
                    messagebox.showinfo("No Selection", "No games were selected.")
                    return

                # Create playlists directory if it doesn't exist
                collection_path = os.path.join(PathManager.get_base_path(), 'collections', selected_collection)
                playlists_dir = os.path.join(collection_path, 'playlists')
                os.makedirs(playlists_dir, exist_ok=True)

                # Create playlist file
                playlist_file = os.path.join(playlists_dir, f"{playlist_name}.txt")
                
                # Check if file already exists
                if os.path.exists(playlist_file):
                    if not messagebox.askyesno("File Exists", 
                        f"A playlist named '{playlist_name}' already exists. Do you want to overwrite it?"):
                        return

                # Write selected ROMs to playlist file
                with open(playlist_file, 'w', encoding='utf-8') as f:
                    selected_roms = [item_to_rom[item] for item in selected_items]
                    for rom in selected_roms:
                        f.write(f"{rom}\n")

                # Update settings.conf
                settings_file = os.path.join(collection_path, 'settings.conf')
                cycle_playlist_line = None
                new_lines = []
                
                if os.path.exists(settings_file):
                    # Read existing settings file
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Look for cyclePlaylist line
                    for line in lines:
                        if line.strip().startswith('cyclePlaylist'):
                            cycle_playlist_line = line.strip()
                            # Update the line with new playlist
                            current_playlists = cycle_playlist_line.split('=')[1].strip()
                            if current_playlists:
                                new_line = f"{cycle_playlist_line},{playlist_name}\n"
                            else:
                                new_line = f"{cycle_playlist_line}{playlist_name}\n"
                            new_lines.append(new_line)
                        else:
                            new_lines.append(line)
                    
                    # If cyclePlaylist wasn't found, add it
                    if cycle_playlist_line is None:
                        new_lines.append(f"cyclePlaylist = all,favorites,{playlist_name}\n")
                else:
                    # Create new settings file with cyclePlaylist
                    new_lines = [f"cyclePlaylist = all,favorites,{playlist_name}\n"]

                # Write updated settings file
                with open(settings_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)

                messagebox.showinfo("Success", 
                    f"Playlist '{playlist_name}' created successfully!\n\nNote: You will need to restart the application for the playlist to be visible in the Playlists tab.")
                if on_close:
                    on_close()

            def cancel():
                if on_close:
                    on_close()

            create_btn = ctk.CTkButton(
                button_frame,
                text="Create Playlist",
                command=create_playlist_file,
                font=self.button_font,
                fg_color='#4CAF50',
                hover_color='#45a049'
            )
            create_btn.pack(side='right', padx=5)

            cancel_btn = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=cancel,
                font=self.button_font,
                fg_color='#f44336',
                hover_color='#da190b'
            )
            cancel_btn.pack(side='right', padx=5)

            # Initial load of list
            update_list()

        except Exception as e:
            messagebox.showerror("Error", f"Error in playlist creation window: {str(e)}")

            create_btn = ctk.CTkButton(
                button_frame,
                text="Create Playlist",
                command=create_playlist_file,
                font=self.button_font,
                fg_color='#4CAF50',
                hover_color='#45a049'
            )
            create_btn.pack(side='right', padx=5)

            cancel_btn = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=cancel,
                font=self.button_font,
                fg_color='#f44336',
                hover_color='#da190b'
            )
            cancel_btn.pack(side='right', padx=5)

            # Initial load of list
            update_list()

        except Exception as e:
            messagebox.showerror("Error", f"Error in playlist creation window: {str(e)}")
    
    def export_collections_data(self):
        """Export a CSV file containing all collections and their ROMs"""
        try:
            # Get the save location from the user
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Save Collections Report"
            )
            
            if not file_path:  # User cancelled
                return
                
            # Create a dictionary to store collection data
            collections_data = {}
            
            # Process each ROM in the list
            for rom in self.rom_list:
                # Split the ROM name to get base name and collection
                if " (" in rom and ")" in rom:
                    base_name = rom.rsplit(" (", 1)[0]
                    collection = rom.rsplit(" (", 1)[1].rstrip(")")
                    
                    # Get the description if available
                    description = self.rom_descriptions.get(base_name, "")
                    
                    # Initialize collection list if needed
                    if collection not in collections_data:
                        collections_data[collection] = []
                        
                    # Add ROM data to collection
                    collections_data[collection].append({
                        'ROM Name': base_name,
                        'Description': description
                    })
            
            # Export as CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow(['Collection', 'ROM Name', 'Description'])
                
                # Write data for each collection
                for collection, roms in sorted(collections_data.items()):
                    for rom in sorted(roms, key=lambda x: x['ROM Name'].lower()):
                        writer.writerow([
                            collection,
                            rom['ROM Name'],
                            rom['Description']
                        ])
                        
            # Show success message
            messagebox.showinfo(
                "Export Complete",
                f"Collections data has been exported to:\n{file_path}"
            )
            
            # Update status bar
            self.status_bar.configure(
                text=f"Collections data exported successfully to {os.path.basename(file_path)}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting collections data: {str(e)}")
            self.status_bar.configure(text="Error exporting collections data")
    
    def remove_random_roms(self):
        """Remove a percentage of ROMs at random and move their artwork."""
        try:
            # Get the selected collection
            selected_collection = self.collection_var.get()
            if selected_collection == "All Collections":
                messagebox.showerror("Error", "Please select a specific collection.")
                return

            # Pre-filter ROMs in the selected collection
            filtered_roms = [
                rom.rsplit(' (', 1)[0] for rom in self.rom_list
                if f"({selected_collection})" in rom
            ]

            if not filtered_roms:
                messagebox.showinfo("No ROMs", f"No ROMs found in the '{selected_collection}' collection.")
                return

            # Popup to select the percentage of ROMs to remove
            def open_percentage_popup():
                popup = tk.Toplevel()
                popup.title("Select Percentage to Remove")
                popup.geometry("300x200")
                popup.configure(bg='#2c2c2c')

                # Center the popup on the screen
                screen_width = popup.winfo_screenwidth()
                screen_height = popup.winfo_screenheight()
                x = (screen_width // 2) - 150
                y = (screen_height // 2) - 100
                popup.geometry(f"+{x}+{y}")

                label = ctk.CTkLabel(
                    popup,
                    text="Select Percentage of ROMs to Remove:",
                    font=("Arial", 14),
                    text_color="white",
                )
                label.pack(pady=10)

                percentage_var = tk.IntVar(value=80)  # Default to 80%
                percentages = [20, 40, 60, 80, 100]

                for percentage in percentages:
                    ctk.CTkRadioButton(
                        popup,
                        text=f"{percentage}%",
                        variable=percentage_var,
                        value=percentage,
                        font=("Arial", 12),
                        text_color="white",
                    ).pack(anchor="w", padx=20, pady=5)

                # Confirm button
                def confirm_selection():
                    selected_percentage = percentage_var.get()
                    popup.destroy()
                    proceed_with_removal(selected_percentage)

                confirm_button = ctk.CTkButton(
                    popup,
                    text="Confirm",
                    command=confirm_selection,
                    fg_color="#4CAF50",
                    hover_color="#45a049",
                )
                confirm_button.pack(pady=20)

                popup.transient(self.parent_tab)
                popup.grab_set()
                popup.mainloop()

            # Removal logic after percentage selection
            def proceed_with_removal(percentage):
                roms_to_remove_count = int(len(filtered_roms) * (percentage / 100))
                if roms_to_remove_count == 0:
                    messagebox.showinfo("Too Few ROMs", "Not enough ROMs to remove.")
                    return

                # Randomly select ROMs to remove
                roms_to_remove = random.sample(filtered_roms, roms_to_remove_count)

                # Use the existing move_roms logic to handle file and artwork movement
                self.move_roms(roms_to_remove)

            # Open the percentage selection popup
            open_percentage_popup()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def select_games_to_remove(self):
        """Open a window to select games to remove from the current collection view"""
        try:
            # Get the selected collection
            selected_collection = self.collection_var.get()
            if selected_collection == "All Collections":
                messagebox.showerror("Error", "Please select a specific collection.")
                return

            # Pre-filter ROMs and get their base names
            filtered_roms = []
            for full_rom in self.rom_list:
                if f"({selected_collection})" in full_rom:
                    base_rom = full_rom.rsplit(' (', 1)[0]
                    desc = self.rom_descriptions.get(base_rom.split(" (")[0], base_rom.split(" (")[0])
                    filtered_roms.append((base_rom, desc, full_rom))
            
            filtered_roms.sort(key=lambda x: x[1].lower())

            # Create window
            select_window = tk.Toplevel(self.parent_tab)
            select_window.title(f"Select Games to Remove - {selected_collection}")
            select_window.configure(bg='#2c2c2c')

            # Window sizing
            screen_width = select_window.winfo_screenwidth()
            screen_height = select_window.winfo_screenheight()
            window_width = int(screen_width * 0.4)
            window_height = int(screen_height * 0.6)
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            select_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # Calculate window size as a percentage of the screen size
            window_width = int(screen_width * 0.4)  # 60% of screen width
            window_height = int(screen_height * 0.6)  # 70% of screen height

            # Calculate the position to center the window
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

            # Set the window size and position
            select_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # Main container - set dark background color
            main_frame = ctk.CTkFrame(select_window, fg_color='#2c2c2c')
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)

            # Add search functionality
            search_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            search_frame.pack(fill='x', padx=5, pady=5)

            search_label = ctk.CTkLabel(search_frame, text="Search:", font=self.label_font)
            search_label.pack(side='left', padx=5)

            search_var = tk.StringVar()
            search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, font=self.button_font)
            search_entry.pack(side='left', fill='x', expand=True, padx=5)

            # Create list frame with fixed height and dark background
            list_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            list_frame.pack(fill='both', expand=True, padx=5, pady=5)

            # Use a Treeview instead of canvas + checkboxes for better performance
            tree = ttk.Treeview(list_frame, selectmode='none', show='tree')
            tree.pack(side='left', fill='both', expand=True)

            # Configure Treeview style for dark theme and larger font
            style = ttk.Style()
            
            # Configure the background colors
            style.map('Treeview', background=[('selected', '#2c2c2c')])
            
            style.configure("Treeview", 
                        background="#2c2c2c", 
                        foreground="white", 
                        fieldbackground="#2c2c2c",
                        font=('TkDefaultFont', 12))
            
            style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
            
            style.configure("Treeview.Heading", 
                        background="#2c2c2c", 
                        foreground="white",
                        font=('TkDefaultFont', 12))
            
            # Configure item height and tags for better spacing with larger font
            tree.tag_configure('custom', font=('TkDefaultFont', 12))
            tree.tag_configure('checked', background='#2d5a27')
            tree.tag_configure('unchecked', background='#2c2c2c')

            # Add scrollbar to Treeview
            scrollbar = ctk.CTkScrollbar(list_frame, command=tree.yview)
            scrollbar.pack(side='right', fill='y')
            tree.configure(yscrollcommand=scrollbar.set)

            # Dictionary to track checked items and their full ROM names
            checked_items = {}
            item_to_rom = {}
            desc_to_display = {}

            def toggle_check(event):
                item = tree.identify_row(event.y)
                if item:
                    checked_items[item] = not checked_items.get(item, False)
                    if checked_items[item]:
                        tree.item(item, text="☒ " + desc_to_display[item], tags=('custom', 'checked'))
                    else:
                        tree.item(item, text="☐ " + desc_to_display[item], tags=('custom', 'unchecked'))

            tree.bind('<Button-1>', toggle_check)

            def update_list(search_text=''):
                tree.delete(*tree.get_children())
                search_text = search_text.lower()
                
                # Filter items based on search text
                visible_items = [
                    (base_rom, desc, full_rom) for base_rom, desc, full_rom in filtered_roms
                    if search_text in desc.lower() or search_text in base_rom.lower()
                ]

                # Batch insert items
                for base_rom, desc, full_rom in visible_items:
                    item = tree.insert('', 'end', text="☐ " + desc, tags=('custom', 'unchecked'))
                    checked_items[item] = False
                    desc_to_display[item] = desc
                    item_to_rom[item] = base_rom  # Store the base ROM name (without collection)

            # Optimize search with a delay to prevent too frequent updates
            search_after_id = None
            def on_search(*args):
                nonlocal search_after_id
                if search_after_id:
                    select_window.after_cancel(search_after_id)
                search_after_id = select_window.after(150, lambda: update_list(search_var.get()))

            search_var.trace_add('write', on_search)

            # Button frame with dark background
            button_frame = ctk.CTkFrame(main_frame, fg_color='#2c2c2c')
            button_frame.pack(fill='x', pady=5)

            def select_all():
                for item in tree.get_children():
                    checked_items[item] = True
                    tree.item(item, text="☒ " + desc_to_display[item], tags=('custom', 'checked'))

            def select_none():
                for item in tree.get_children():
                    checked_items[item] = False
                    tree.item(item, text="☐ " + desc_to_display[item], tags=('custom', 'unchecked'))

            select_all_btn = ctk.CTkButton(
                button_frame,
                text="Select All",
                command=select_all,
                font=self.button_font
            )
            select_all_btn.pack(side='left', padx=5)

            select_none_btn = ctk.CTkButton(
                button_frame,
                text="Select None",
                command=select_none,
                font=self.button_font
            )
            select_none_btn.pack(side='left', padx=5)

            on_close = self.main_app.show_popup(select_window)

            def confirm_removal():
                selected_items = [item for item, checked in checked_items.items() if checked]
                if not selected_items:
                    messagebox.showinfo("No Selection", "No games were selected.")
                    return

                selected_roms = [item_to_rom[item] for item in selected_items]
                if on_close:
                    on_close()
                self.move_roms(selected_roms)

            def cancel():
                if on_close:
                    on_close()

            confirm_btn = ctk.CTkButton(
                button_frame,
                text="Confirm",
                command=confirm_removal,
                font=self.button_font,
                fg_color='#4CAF50',
                hover_color='#45a049'
            )
            confirm_btn.pack(side='right', padx=5)

            cancel_btn = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=cancel,
                font=self.button_font,
                fg_color='#f44336',
                hover_color='#da190b'
            )
            cancel_btn.pack(side='right', padx=5)

            # Initial load of list
            update_list()

        except Exception as e:
            messagebox.showerror("Error", f"Error in select games window: {str(e)}")

    def show_instructions_popup(self, button_key):
        """Show the instructions popup for the given button."""
        show_popup_flag = self.config_manager.get_setting('Settings', f'show_{button_key}_instructions', 'True')
        if show_popup_flag != 'True':
            self.execute_button_action(button_key)
            return

        popup = tk.Toplevel(self.parent_tab)
        popup.title("Instructions")
        popup.geometry("600x400")
        popup.configure(bg='#2c2c2c')

        # Center the window
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        window_width = 600
        window_height = 400
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Title label
        title_text = "Instructions for Moving Artwork" if button_key == 'show_move_artwork_button' else "Instructions for Removing ROMs"
        title_label = ctk.CTkLabel(
            popup,
            text=title_text,
            wraplength=500,
            text_color='white',
            font=('Helvetica', 18, 'bold')
        )
        title_label.pack(pady=(20, 10))

        # Instructions text box
        instructions_text = ctk.CTkTextbox(
            popup,
            width=500,
            height=200,
            text_color='white',
            font=('Helvetica', 14),
            fg_color='#2c2c2c',
            state='normal'
        )
        instructions_text.insert('1.0', self.get_instructions(button_key))
        instructions_text.configure(state='disabled')
        instructions_text.pack(pady=(10, 20), padx=20)

        # Do not display again checkbox
        do_not_show_var = tk.BooleanVar()
        do_not_show_checkbox = ctk.CTkCheckBox(
            popup,
            text="Do not show again",
            variable=do_not_show_var,
            font=('Helvetica', 12)
        )
        do_not_show_checkbox.pack(pady=10)

        # Get centralized popup management from main app
        on_close = self.main_app.show_popup(popup)

        def on_ok():
            if do_not_show_var.get():
                self.config_manager.config.set('Settings', f'show_{button_key}_instructions', 'False')
                self.config_manager.save_config()
            if on_close:
                on_close()
            self.execute_button_action(button_key)

        ok_button = ctk.CTkButton(
            popup,
            text="OK",
            command=on_ok,
            fg_color='#4CAF50',
            hover_color='#45a049'
        )
        ok_button.pack(pady=20)

    def execute_button_action(self, button_key):
        """Execute the action associated with the button."""
        if button_key == 'show_move_artwork_button':
            self.move_artwork()
        elif button_key == 'show_move_roms_button':
            self.move_roms()

    def get_instructions(self, button_key):
        """Return the instructions text for the given button."""
        if button_key == 'show_move_artwork_button':
            return (
                "1. Select a Collection from the dropdown menu.\n\n"
                "2. All artwork that does not have an associated ROM file under the system's ROM folder will be moved to medium_artwork_moved.\n"
            )
        elif button_key == 'show_move_roms_button':
            return (
                "1. Select a Collection from the dropdown menu.\n\n"
                "Note. Even though you can naviagte to any folder, you must move ROMs\n"
                "from the collection you pick from in the dropdown menu, so the\napp"
                " knows the rom path.\n\n"
                "2. Click 'Move ROMs' and navigate to the text file containing the ROMs.\n\n"
                "3. In the TXT file, each ROM should be on a new line.\nDo not add file extensions.\n\n"
                "4. All ROMs in the text file will be moved to the Collections folder under\nroms_moved.\n\n"
                "5. Move Artwork will move all the artwork for the selected ROMs\nto medium_artwork_moved.\n"
            )
        return ""

    def update_button_visibility(self):
        """Update the visibility of the buttons based on the configuration."""
        for setting_key, button in self.buttons.items():
            show_button = self.config_manager.get_setting('Settings', setting_key, True)  # Use True as default
            if show_button:
                button.pack(side='right', padx=5)
            else:
                button.pack_forget()

    def toggle_button_visibility(self, **kwargs):
        """Toggle the visibility of the buttons internally."""
        for setting_key, button in self.buttons.items():
            if setting_key in kwargs:
                self.config_manager.config.set('Settings', setting_key, str(kwargs[setting_key]))
        self.config_manager.save_config()
        self.update_button_visibility()

    def load_initial_data(self):
        """Load initial ROM data and populate collection dropdown"""
        try:
            # Load ROM descriptions first, before filtering anything
            self.rom_descriptions = {}
            csv_path = self.get_csv_file_path()
            with open(csv_path, newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    rom_name = row.get('ROM Name', '').strip()
                    description = row.get('Description', '').strip()
                    if rom_name and description:  # Remove the self.rom_list check
                        self.rom_descriptions[rom_name] = description

            # Get ROM list and collections
            self.rom_list, self.rom_collections, self.rom_file_names = self.scan_collections_for_roms()

            # Get unique collections and sort them
            collections = sorted(set(self.rom_collections.values()))

            # Update dropdown values
            self.collection_dropdown.configure(
                values=["All Collections"] + collections
            )

            # Populate initial ROM list
            self.populate_rom_list()

        except Exception as e:
            messagebox.showerror("Error", f"Error loading initial data: {str(e)}")
            self.status_bar.configure(text="Error loading initial data")

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

    def scan_collections_for_roms(self, excluded_collections=None, excluded_roms=None):
        root_dir = PathManager.get_base_path()
        collections_dir = os.path.join(root_dir, 'collections')
        rom_list = []
        rom_collections = {}
        rom_file_names = {}
        duplicate_roms = {}

        # Default exclude lists
        default_collection_excludes = [
            "*zzzSettings*", "*zzzShutdown*", "*PCGameLauncher*"
        ]

        default_rom_excludes = ["*cmd*"]

        # Get additional excludes from config
        additional_collection_excludes = self.config_manager.get_setting(
            'Settings', 'additional_collection_excludes', []
        )
        if isinstance(additional_collection_excludes, str):
            additional_collection_excludes = [additional_collection_excludes] if additional_collection_excludes else []

        additional_rom_excludes = self.config_manager.get_setting(
            'Settings', 'additional_rom_excludes', []
        )
        if isinstance(additional_rom_excludes, str):
            additional_rom_excludes = [additional_rom_excludes] if additional_rom_excludes else []

        # Initialize and extend exclude lists
        if excluded_collections is None:
            excluded_collections = []
        excluded_collections.extend(default_collection_excludes)
        excluded_collections.extend(additional_collection_excludes)

        if excluded_roms is None:
            excluded_roms = []
        excluded_roms.extend(default_rom_excludes)
        excluded_roms.extend(additional_rom_excludes)

        def matches_exclude_pattern(name, patterns):
            return any(
                fnmatch.fnmatch(name.lower(), pattern.lower())
                for pattern in patterns
            )

        def get_most_specific_collection(collections):
            # Select the most specific (longest) collection name
            return sorted(collections, key=len, reverse=True)[0]

        def resolve_path(path, variables):
            for var, value in variables.items():
                path = path.replace(f"%{var}%", value)
            return path

        # First pass: gather all ROMs and their locations
        for collection_name in os.listdir(collections_dir):
            if matches_exclude_pattern(collection_name, excluded_collections):
                continue

            # Get removed games for this collection
            removed_games = self.config_manager.get_setting(
                'RemovedGames',
                collection_name,
                ''
            ).split(',')
            removed_games = [x.lower() for x in removed_games if x]

            collection_path = os.path.join(collections_dir, collection_name)
            settings_path = os.path.join(collection_path, 'settings.conf')

            if os.path.isdir(collection_path) and os.path.isfile(settings_path):
                rom_folder = None
                extensions = []
                variables = {
                    "BASE_ITEM_PATH": collections_dir,
                    "ITEM_COLLECTION_NAME": collection_name
                }

                with open(settings_path, 'r') as settings_file:
                    for line in settings_file:
                        line = line.strip()
                        if line.startswith("#"):
                            continue
                        if line.startswith("list.path"):
                            rom_folder = line.split("=", 1)[1].strip()
                            rom_folder = resolve_path(rom_folder, variables)
                        elif line.startswith("list.extensions"):
                            ext_line = line.split("=", 1)[1].strip()
                            extensions = [ext.strip() for ext in ext_line.split(",")]

                if not rom_folder or not os.path.isdir(rom_folder):
                    rom_folder = os.path.join(collection_path, 'roms')

                if rom_folder and extensions and os.path.isdir(rom_folder):
                    for file in os.listdir(rom_folder):
                        file_path = os.path.join(rom_folder, file)
                        if os.path.isfile(file_path) and any(file.endswith(ext) for ext in extensions):
                            filename_without_extension = os.path.splitext(file)[0]

                            if matches_exclude_pattern(filename_without_extension, excluded_roms):
                                continue

                            # Skip if game is in removed list
                            if filename_without_extension.lower() in removed_games:
                                continue

                            # Initialize rom entry if it doesn't exist
                            if filename_without_extension not in rom_collections:
                                rom_collections[filename_without_extension] = {
                                    'collections': set(),
                                    'paths': []
                                }

                            # Add this collection and path
                            rom_collections[filename_without_extension]['collections'].add(collection_name)
                            if file_path not in rom_collections[filename_without_extension]['paths']:
                                rom_collections[filename_without_extension]['paths'].append(file_path)

                            # Add collection name to ROM's display name
                            collection_with_rom = f"{filename_without_extension} ({collection_name})"
                            if collection_with_rom not in rom_list:
                                rom_list.append(collection_with_rom)

                            # Store the actual file name
                            rom_file_names[collection_with_rom] = filename_without_extension

                            # Track duplicates for debugging
                            if len(rom_collections[filename_without_extension]['collections']) > 1:
                                duplicate_roms[filename_without_extension] = \
                                    list(rom_collections[filename_without_extension]['collections'])

        # Convert rom_collections to a format that maps ROMs to their most specific collection
        simple_rom_collections = {
            rom: get_most_specific_collection(info['collections'])
            for rom, info in rom_collections.items()
        }

        return rom_list, simple_rom_collections, rom_file_names

    def handle_sort_change(self, _):
        """Handle sorting toggle change"""
        if self.search_var.get():
            self.filter_roms()
        else:
            self.populate_rom_list()

    def handle_collection_change(self, _):
        """Handle collection dropdown change"""
        self.filter_roms()

    def clear_filters(self):
        """Clear all filters and reset the ROM list"""
        self.search_var.set("")
        self.collection_var.set("All Collections")
        self.sort_var.set("Name")
        self.populate_rom_list()

    def populate_rom_list(self):
        try:
            self.filter_roms()
        except Exception as e:
            messagebox.showerror("Error", f"Error loading ROM list: {str(e)}")
            self.status_bar.configure(text="Error loading ROMs")

    def filter_roms(self, *args):
        try:
            # Clear previous list
            self.rom_listbox.delete('1.0', 'end')

            # Get filter values
            search_term = self.search_var.get().lower()
            selected_collection = self.collection_var.get()

            # Filter ROMs
            filtered_roms = []
            for rom in self.rom_list:
                # Split ROM name and collection info
                base_rom_name = rom.split(" (")[0]
                collection_info = rom.split("(")[-1].strip(")")

                # Strict collection filtering
                if selected_collection != "All Collections":
                    # Exact collection match only
                    if selected_collection != collection_info:
                        continue

                # Get description if available and create display text
                description = self.rom_descriptions.get(base_rom_name, '')
                display_text = f"{description if description else base_rom_name} ({collection_info})"

                # Check search term against both description and ROM name
                if (search_term in display_text.lower() or
                    search_term in base_rom_name.lower()):
                    filtered_roms.append(display_text)

            # Sort filtered ROMs based on toggle
            if self.sort_var.get() == "Name":
                filtered_roms = sorted(filtered_roms)
            else:
                filtered_roms = sorted(
                    filtered_roms,
                    key=lambda rom: rom.split("(")[-1].strip(")")
                )

            # Display filtered ROMs
            self.rom_listbox.insert('1.0', f"Matching ROMs: {len(filtered_roms)}\n\n")
            for rom in filtered_roms:
                self.rom_listbox.insert('end', f"{rom}\n")

            # Update status
            self.status_bar.configure(text=f"Found {len(filtered_roms)} matching ROMs")

        except Exception as e:
            messagebox.showerror("Error", f"Error filtering ROM list: {str(e)}")
            self.status_bar.configure(text="Error filtering ROMs")

    def move_artwork(self):
        """Move artwork files based on the selected collection"""
        try:
            # MODIFICATION: Define a list of excluded folders
            EXCLUDED_FOLDERS = [
                'desktop', '.ds_store', 'thumbs.db', 'system', 'temp', 'cache', 'metadata', '.thumbnail', '.cache',
                'ctrltype', 'numberplayers', 'year','manufacturer',
                'playlist', 'playlist2', 'playlist3', 'playlist4', 'playlist5', 'playlist6', 'playlist7', 'playlist8', 'playlist9'
            ]

            # Get the selected collection
            selected_collection = self.collection_var.get()
            if selected_collection == "All Collections":
                messagebox.showerror("Error", "Please select a specific collection.")
                return

            root_dir = PathManager.get_base_path()
            collections_dir = os.path.join(root_dir, 'collections')
            collection_path = os.path.join(collections_dir, selected_collection)
            settings_path = os.path.join(collection_path, 'settings.conf')

            # Default to 'roms' folder if no specific path found
            rom_folder = os.path.join(collection_path, 'roms')
            variables = {
                "BASE_ITEM_PATH": collections_dir,
                "ITEM_COLLECTION_NAME": selected_collection
            }

            # Try to read list.path from settings.conf
            if os.path.isfile(settings_path):
                with open(settings_path, 'r') as settings_file:
                    for line in settings_file:
                        line = line.strip()
                        if line.startswith("list.path"):
                            rom_folder = line.split("=", 1)[1].strip()
                            rom_folder = self.resolve_path(rom_folder, variables)
                            break

            # Validate ROM folder
            if not os.path.isdir(rom_folder):
                messagebox.showerror("Error", f"ROM folder not found: {rom_folder}")
                return

            # Source path for medium artwork (with collection name)
            source_path = os.path.join(collections_dir, selected_collection, 'medium_artwork')
            if not os.path.exists(source_path):
                messagebox.showerror("Error", f"Medium artwork folder not found: {source_path}")
                return

            # Get list of ROM names (without extension)
            rom_names = set(os.path.splitext(f)[0].lower() for f in os.listdir(rom_folder) if os.path.isfile(os.path.join(rom_folder, f)))

            # Find artwork files for ROMs not in the collection
            missing_rom_artwork = set()
            for subfolder in os.listdir(source_path):
                # MODIFICATION: Skip excluded folders
                if any(excluded.lower() in subfolder.lower() for excluded in EXCLUDED_FOLDERS):
                    continue

                subfolder_path = os.path.join(source_path, subfolder)
                if os.path.isdir(subfolder_path):
                    for file in os.listdir(subfolder_path):
                        file_base_name = os.path.splitext(file)[0].lower()
                        # Additional check to ignore excluded folders/files
                        if (file_base_name.lower() not in rom_names and
                            file_base_name.lower() != 'default' and
                            not any(excluded.lower() in file_base_name.lower() for excluded in EXCLUDED_FOLDERS)):
                            # Check if the ROM file exists in the rom_folder
                            rom_file_path = os.path.join(rom_folder, file_base_name)
                            if not os.path.exists(rom_file_path):
                                missing_rom_artwork.add(file_base_name)

            # If no artwork to move, exit
            if not missing_rom_artwork:
                messagebox.showinfo("No Artwork", "No artwork found for missing ROMs.")
                return

            # Custom confirmation dialog with scrollable list
            def create_scrollable_confirmation():
                confirm_window = tk.Toplevel()
                confirm_window.title(f"Confirm ROM Move - {selected_collection}")
                confirm_window.geometry("400x500")
                confirm_window.configure(bg='#2c2c2c')

                # Add proper window management
                confirm_window.transient(self.parent_tab.winfo_toplevel())
                confirm_window.attributes('-topmost', True)
                confirm_window.focus_force()

                # Center the window on the screen
                screen_width = confirm_window.winfo_screenwidth()
                screen_height = confirm_window.winfo_screenheight()
                window_width = 400
                window_height = 500
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                confirm_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

                # Label with improved styling
                label = ctk.CTkLabel(
                    confirm_window,
                    text=f"Are you sure you want to move artwork for these {len(missing_rom_artwork)} missing ROMs in the '{selected_collection}' collection?",
                    wraplength=380,
                    text_color='white',
                    font=('Helvetica', 14)
                )
                label.pack(pady=10, padx=10)

                # Scrollable text widget with dark theme
                text_frame = ctk.CTkFrame(confirm_window, fg_color='#3c3c3c')
                text_frame.pack(expand=True, fill='both', padx=10, pady=10)

                text_widget = ctk.CTkTextbox(
                    text_frame,
                    height=300,
                    text_color='white',
                    fg_color='#3c3c3c',
                )
                text_widget.pack(expand=True, fill='both')

                # Sort and insert ROM names
                for rom in sorted(missing_rom_artwork):
                    text_widget.insert('end', f"{rom}\n")
                text_widget.configure(state='disabled')  # Make read-only

                # Buttons frame with improved styling
                button_frame = ctk.CTkFrame(confirm_window, fg_color='#2c2c2c')
                button_frame.pack(pady=10)

                # Get centralized popup management from main app
                on_close = self.main_app.show_popup(confirm_window)

                def on_confirm():
                    if on_close:
                        on_close()
                    proceed_with_move()

                def on_cancel():
                    if on_close:
                        on_close()

                confirm_button = ctk.CTkButton(
                    button_frame,
                    text="Confirm",
                    command=on_confirm,
                    fg_color='#4CAF50',
                    hover_color='#45a049'
                )
                confirm_button.pack(side='left', padx=5)

                cancel_button = ctk.CTkButton(
                    button_frame,
                    text="Cancel",
                    command=on_cancel,
                    fg_color='#f44336',
                    hover_color='#da190b'
                )
                cancel_button.pack(side='left', padx=5)

            def proceed_with_move():
                # Move artwork logic
                moved_artwork_path = os.path.join(collection_path, 'medium_artwork_moved')
                if not os.path.exists(moved_artwork_path):
                    os.makedirs(moved_artwork_path)

                for subfolder in os.listdir(source_path):
                    # MODIFICATION: Skip excluded folders during move
                    if any(excluded.lower() in subfolder.lower() for excluded in EXCLUDED_FOLDERS):
                        continue

                    subfolder_path = os.path.join(source_path, subfolder)
                    if os.path.isdir(subfolder_path):
                        dest_subfolder = os.path.join(moved_artwork_path, subfolder)
                        if not os.path.exists(dest_subfolder):
                            os.makedirs(dest_subfolder)

                        for file in os.listdir(subfolder_path):
                            file_base_name = os.path.splitext(file)[0].lower()
                            file_path = os.path.join(subfolder_path, file)

                            if (file_base_name.lower() not in rom_names and
                                file_base_name.lower() != 'default' and
                                not any(excluded.lower() in file_base_name.lower() for excluded in EXCLUDED_FOLDERS)):
                                shutil.move(file_path, os.path.join(dest_subfolder, file))

                self.status_bar.configure(text="Artwork for missing ROMs moved successfully")

            # Show custom confirmation dialog
            create_scrollable_confirmation()

        except Exception as e:
            messagebox.showerror("Error", f"Error moving artwork: {str(e)}")
            self.status_bar.configure(text="Error moving artwork")

    def move_roms(self, rom_list=None):
        """Move ROMs based on a list from a text file or provided list"""
        try:
            # Get the selected collection
            selected_collection = self.collection_var.get()
            if selected_collection == "All Collections":
                messagebox.showerror("Error", "Please select a specific collection.")
                return

            # If rom_list is None, get it from a text file
            if rom_list is None:
                # Prompt the user to select the text file containing the list of ROMs
                file_path = filedialog.askopenfilename(
                    title="Select ROM List File",
                    filetypes=[("Text Files", "*.txt")]
                )
                if not file_path:
                    messagebox.showinfo("Cancelled", "Operation cancelled by the user.")
                    return

                # Read the list of ROM names from the text file
                with open(file_path, 'r') as file:
                    rom_list = [line.strip() for line in file.readlines()]

            root_dir = PathManager.get_base_path()
            collections_dir = os.path.join(root_dir, 'collections')
            collection_path = os.path.join(collections_dir, selected_collection)
            settings_path = os.path.join(collection_path, 'settings.conf')

            # Default to 'roms' folder if no specific path found
            rom_folder = os.path.join(collection_path, 'roms')
            extensions = []
            variables = {
                "BASE_ITEM_PATH": collections_dir,
                "ITEM_COLLECTION_NAME": selected_collection
            }

            # Try to read list.path and list.extensions from settings.conf
            if os.path.isfile(settings_path):
                with open(settings_path, 'r') as settings_file:
                    for line in settings_file:
                        line = line.strip()
                        if line.startswith("list.path"):
                            rom_folder = line.split("=", 1)[1].strip()
                            rom_folder = self.resolve_path(rom_folder, variables)
                        elif line.startswith("list.extensions"):
                            ext_line = line.split("=", 1)[1].strip()
                            # Ensure extensions start with a dot and are lowercase
                            extensions = [
                                f".{ext.strip().lower().lstrip('.')}"
                                for ext in ext_line.split(",")
                            ]

            # Debugging print statements
            print(f"ROM Folder: {rom_folder}")
            print(f"Parsed Extensions: {extensions}")
            print(f"ROM List from file: {rom_list}")

            # Validate ROM folder
            if not os.path.isdir(rom_folder):
                messagebox.showerror("Error", f"ROM folder not found: {rom_folder}")
                return

            # Create a dictionary to map file names to their paths
            file_dict = {}
            for filename in os.listdir(rom_folder):
                name_without_ext = os.path.splitext(filename)[0]
                file_ext = os.path.splitext(filename)[1].lower()
                if not extensions or file_ext in extensions:
                    file_dict[name_without_ext] = os.path.join(rom_folder, filename)

            # Prepare to move ROMs
            moved_roms = []
            not_found_roms = []

            # Iterate through ROM names in the text file
            for rom_name in rom_list:
                if rom_name in file_dict:
                    source_path = file_dict[rom_name]
                    try:
                        print(f"Preparing to move file: {rom_name}")
                        moved_roms.append(rom_name)
                    except FileNotFoundError:
                        print(f"File not found: {source_path}")
                        not_found_roms.append(rom_name)
                else:
                    not_found_roms.append(rom_name)

            # Custom confirmation dialog with scrollable list
            def create_scrollable_confirmation():
                confirm_window = tk.Toplevel()
                confirm_window.title(f"Confirm ROM Move - {selected_collection}")
                confirm_window.geometry("400x500")
                confirm_window.configure(bg='#2c2c2c')

                # Center the window on the screen
                screen_width = confirm_window.winfo_screenwidth()
                screen_height = confirm_window.winfo_screenheight()
                window_width = 400
                window_height = 500
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                confirm_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

                # Label with improved styling
                label = ctk.CTkLabel(
                    confirm_window,
                    text=f"Are you sure you want to move these {len(moved_roms)} ROMs?",
                    wraplength=380,
                    text_color='white',
                    font=('Helvetica', 14)
                )
                label.pack(pady=10, padx=10)

                # Scrollable text widget with dark theme
                text_frame = ctk.CTkFrame(confirm_window, fg_color='#3c3c3c')
                text_frame.pack(expand=True, fill='both', padx=10, pady=10)

                text_widget = ctk.CTkTextbox(
                    text_frame,
                    height=300,
                    text_color='white',
                    fg_color='#3c3c3c',
                )
                text_widget.pack(expand=True, fill='both')

                # Sort and insert ROM names
                for rom in sorted(moved_roms):
                    text_widget.insert('end', f"{rom}\n")
                text_widget.configure(state='disabled')  # Make read-only

                # Buttons frame with improved styling
                button_frame = ctk.CTkFrame(confirm_window, fg_color='#2c2c2c')
                button_frame.pack(pady=10)

                def on_confirm():
                    confirm_window.destroy()
                    proceed_with_move()

                confirm_button = ctk.CTkButton(
                    button_frame,
                    text="Confirm",
                    command=on_confirm,
                    fg_color='#4CAF50',
                    hover_color='#45a049'
                )
                confirm_button.pack(side='left', padx=5)

                cancel_button = ctk.CTkButton(
                    button_frame,
                    text="Cancel",
                    command=confirm_window.destroy,
                    fg_color='#f44336',
                    hover_color='#da190b'
                )
                cancel_button.pack(side='left', padx=5)

                confirm_window.grab_set()  # Make the window modal

            def proceed_with_move():
                # Destination folder for moved ROMs
                moved_roms_path = os.path.join(collection_path, 'roms_moved')
                if not os.path.exists(moved_roms_path):
                    os.makedirs(moved_roms_path)

                # Show loading indicator
                loading_popup = self.show_loading_popup("Moving ROMs...")

                # Perform the actual move
                moved_count = 0
                for rom_name in moved_roms:
                    source_path = file_dict[rom_name]
                    dest_path = os.path.join(moved_roms_path, os.path.basename(source_path))
                    try:
                        print(f"Moving file: {rom_name}")
                        shutil.move(source_path, dest_path)
                        moved_count += 1
                    except FileNotFoundError:
                        print(f"File not found: {source_path}")
                        not_found_roms.append(rom_name)

                # Close loading indicator
                loading_popup.destroy()

                # Update status bar
                self.status_bar.configure(text=f"Moved {moved_count} ROMs to 'roms_moved' folder")

                # Write the list of moved ROMs to a text file
                moved_roms_log_path = os.path.join(moved_roms_path, '_moved_roms.txt')
                with open(moved_roms_log_path, 'w') as log_file:
                    for rom in moved_roms:
                        log_file.write(f"{rom}\n")

                # Write the list of not found ROMs to a text file
                not_found_roms_log_path = os.path.join(moved_roms_path, '_roms_not_found.txt')
                with open(not_found_roms_log_path, 'w') as log_file:
                    for rom in not_found_roms:
                        log_file.write(f"{rom}\n")

                # Print ROMs that were not found (for debugging)
                if not_found_roms:
                    print("ROMs not found:")
                    for rom in not_found_roms:
                        print(rom)

                # Call the new method to move artwork for the moved ROMs
                self.move_artwork_for_roms(moved_roms)

            # Show custom confirmation dialog
            create_scrollable_confirmation()

        except Exception as e:
            import traceback
            traceback.print_exc()  # This will print the full stack trace
            messagebox.showerror("Error", f"Error moving ROMs: {str(e)}")
            self.status_bar.configure(text="Error moving ROMs")

    def move_artwork_for_roms(self, rom_list):
        """Move artwork files for the specified ROMs"""
        try:
            # Get the selected collection
            selected_collection = self.collection_var.get()
            if selected_collection == "All Collections":
                messagebox.showerror("Error", "Please select a specific collection.")
                return

            root_dir = PathManager.get_base_path()
            collections_dir = os.path.join(root_dir, 'collections')
            collection_path = os.path.join(collections_dir, selected_collection)
            settings_path = os.path.join(collection_path, 'settings.conf')

            # Default to 'roms' folder if no specific path found
            rom_folder = os.path.join(collection_path, 'roms')
            variables = {
                "BASE_ITEM_PATH": collections_dir,
                "ITEM_COLLECTION_NAME": selected_collection
            }

            # Try to read list.path from settings.conf
            if os.path.isfile(settings_path):
                with open(settings_path, 'r') as settings_file:
                    for line in settings_file:
                        line = line.strip()
                        if line.startswith("list.path"):
                            rom_folder = line.split("=", 1)[1].strip()
                            rom_folder = self.resolve_path(rom_folder, variables)
                            break

            # Validate ROM folder
            if not os.path.isdir(rom_folder):
                messagebox.showerror("Error", f"ROM folder not found: {rom_folder}")
                return

            # Source path for medium artwork (with collection name)
            source_path = os.path.join(collections_dir, selected_collection, 'medium_artwork')
            if not os.path.exists(source_path):
                messagebox.showerror("Error", f"Medium artwork folder not found: {source_path}")
                return

            # Convert rom_list to a set of lowercase ROM names (without extension)
            rom_names_set = set(rom.lower() for rom in rom_list)

            # Find artwork files for the specified ROMs
            artwork_to_move = set()
            for subfolder in os.listdir(source_path):
                subfolder_path = os.path.join(source_path, subfolder)
                if os.path.isdir(subfolder_path):
                    for file in os.listdir(subfolder_path):
                        file_base_name = os.path.splitext(file)[0].lower()
                        if file_base_name in rom_names_set:
                            artwork_to_move.add(file_base_name)

            # Debugging: Print the number of artwork files identified
            print(f"Artwork to move: {len(artwork_to_move)}")

            # If no artwork to move, exit
            if not artwork_to_move:
                messagebox.showinfo("No Artwork", "No artwork found for the specified ROMs.")
                return

            # Custom confirmation dialog with scrollable list
            def create_scrollable_confirmation():
                confirm_window = tk.Toplevel()
                confirm_window.title(f"Confirm Artwork Move - {selected_collection}")
                confirm_window.geometry("400x500")
                confirm_window.configure(bg='#2c2c2c')

                # Center the window on the screen
                screen_width = confirm_window.winfo_screenwidth()
                screen_height = confirm_window.winfo_screenheight()
                window_width = 400
                window_height = 500
                x = (screen_width // 2) - (window_width // 2)
                y = (screen_height // 2) - (window_height // 2)
                confirm_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

                # Label with improved styling
                label = ctk.CTkLabel(
                    confirm_window,
                    text=f"Are you sure you want to move artwork for these {len(artwork_to_move)} ROMs in the '{selected_collection}' collection?",
                    wraplength=380,
                    text_color='white',
                    font=('Helvetica', 14)
                )
                label.pack(pady=10, padx=10)

                # Scrollable text widget with dark theme
                text_frame = ctk.CTkFrame(confirm_window, fg_color='#3c3c3c')
                text_frame.pack(expand=True, fill='both', padx=10, pady=10)

                text_widget = ctk.CTkTextbox(
                    text_frame,
                    height=300,
                    text_color='white',
                    fg_color='#3c3c3c',
                )
                text_widget.pack(expand=True, fill='both')

                # Sort and insert ROM names
                for rom in sorted(artwork_to_move):
                    text_widget.insert('end', f"{rom}\n")
                text_widget.configure(state='disabled')  # Make read-only

                # Buttons frame with improved styling
                button_frame = ctk.CTkFrame(confirm_window, fg_color='#2c2c2c')
                button_frame.pack(pady=10)

                def on_confirm():
                    confirm_window.destroy()
                    proceed_with_move()

                confirm_button = ctk.CTkButton(
                    button_frame,
                    text="Confirm",
                    command=on_confirm,
                    fg_color='#4CAF50',
                    hover_color='#45a049'
                )
                confirm_button.pack(side='left', padx=5)

                cancel_button = ctk.CTkButton(
                    button_frame,
                    text="Cancel",
                    command=confirm_window.destroy,
                    fg_color='#f44336',
                    hover_color='#da190b'
                )
                cancel_button.pack(side='left', padx=5)

                confirm_window.grab_set()  # Make the window modal

            def proceed_with_move():
                # Move artwork logic
                moved_artwork_path = os.path.join(collection_path, 'medium_artwork_moved')

                for subfolder in os.listdir(source_path):
                    subfolder_path = os.path.join(source_path, subfolder)
                    if os.path.isdir(subfolder_path):
                        dest_subfolder = os.path.join(moved_artwork_path, subfolder)
                        artwork_found = False

                        for file in os.listdir(subfolder_path):
                            file_base_name = os.path.splitext(file)[0].lower()
                            if file_base_name in artwork_to_move:
                                artwork_found = True
                                file_path = os.path.join(subfolder_path, file)
                                if not os.path.exists(dest_subfolder):
                                    os.makedirs(dest_subfolder)
                                shutil.move(file_path, os.path.join(dest_subfolder, file))

                        # Only create the destination folder if artwork was found
                        if artwork_found and not os.path.exists(dest_subfolder):
                            os.makedirs(dest_subfolder)

                self.status_bar.configure(text="Artwork for specified ROMs moved successfully")

            # Show custom confirmation dialog
            create_scrollable_confirmation()

        except Exception as e:
            messagebox.showerror("Error", f"Error moving artwork: {str(e)}")
            self.status_bar.configure(text="Error moving artwork")

    def resolve_path(self, path, variables):
        for var, value in variables.items():
            path = path.replace(f"%{var}%", value)
        return path

    def show_loading_popup(self, message):
        popup = tk.Toplevel(self.parent_tab)
        popup.title("Loading")
        popup.geometry("200x100")
        popup.configure(bg='#2c2c2c')

        label = ctk.CTkLabel(
            popup,
            text=message,
            text_color='white',
            font=('Helvetica', 14)
        )
        label.pack(pady=20, padx=20)

        # Center the window on the screen
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        window_width = 200
        window_height = 100
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        popup.transient(self.parent_tab)
        popup.grab_set()
        popup.update()
        return popup

    def show_scrollable_list_with_prompt(self, title, items):
        confirm_window = tk.Toplevel()
        confirm_window.title(title)
        confirm_window.geometry("400x500")
        confirm_window.configure(bg='#2c2c2c')

        # Center the window on the screen
        screen_width = confirm_window.winfo_screenwidth()
        screen_height = confirm_window.winfo_screenheight()
        window_width = 400
        window_height = 500
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        confirm_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Label with improved styling
        label = ctk.CTkLabel(
            confirm_window,
            text=f"{title}:",
            wraplength=380,
            text_color='white',
            font=('Helvetica', 14)
        )
        label.pack(pady=10, padx=10)

        # Scrollable text widget with dark theme
        text_frame = ctk.CTkFrame(confirm_window, fg_color='#3c3c3c')
        text_frame.pack(expand=True, fill='both', padx=10, pady=10)

        text_widget = ctk.CTkTextbox(
            text_frame,
            height=300,
            text_color='white',
            fg_color='#3c3c3c',
        )
        text_widget.pack(expand=True, fill='both')

        # Sort and insert ROM names
        for rom in sorted(items):
            text_widget.insert('end', f"{rom}\n")
        text_widget.configure(state='disabled')  # Make read-only

        # Buttons frame with improved styling
        button_frame = ctk.CTkFrame(confirm_window, fg_color='#2c2c2c')
        button_frame.pack(pady=10)

        def on_confirm():
            confirm_window.destroy()
            self.move_artwork()

        confirm_button = ctk.CTkButton(
            button_frame,
            text="Move Artwork",
            command=on_confirm,
            fg_color='#4CAF50',
            hover_color='#45a049'
        )
        confirm_button.pack(side='left', padx=5)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Do Not Move Artwork",
            command=confirm_window.destroy,
            fg_color='#f44336',
            hover_color='#da190b'
        )
        cancel_button.pack(side='left', padx=5)

        confirm_window.grab_set()  # Make the window modal

# Main application driver
def main():
    # Initialize GUI with customtkinter
    config_manager = ConfigManager()

    appearance_mode = config_manager.get_appearance_mode()
    ctk.set_appearance_mode(appearance_mode)
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = FilterGamesApp(root)  # This will create and show the splash screen

    # The following will now happen after splash screen closes
    def after_splash():
        # Load fullscreen preference from config
        fullscreen_mode = app.config_manager.get_fullscreen_preference()
        if fullscreen_mode:
            root.attributes("-fullscreen", True)

        # Add appearance mode frame with fullscreen state
        app.add_appearance_mode_frame(fullscreen=fullscreen_mode)

    # Schedule the after_splash function to run after initialization
    root.after(100, after_splash)
    
    root.mainloop()

if __name__ == "__main__":
    main()





