import os
import subprocess
import sys
import shutil

def main():
    # Automatically determine the script's directory
    script_location = os.path.dirname(os.path.abspath(__file__))
    print(f"The script is running from: {script_location}")
    
    # Check if the provided path exists
    if not os.path.isdir(script_location):
        print("Error: The provided path does not exist.")
        return
    
    # Change to the script directory
    os.chdir(script_location)
    
    # Set the desired output name for the executable
    output_name = "Customisation"  # Change this to your preferred name
    
    # on unix, delimiter is :
    delimiter = ";" if os.name == "nt" else ":"
    
    # PyInstaller command
    command = [
        "pyinstaller",
        "--windowed",
        "--noconfirm",
        "--name", output_name,  # Set the output name
        "--add-data", f"meta{os.sep}hyperlist{os.sep}META.csv{delimiter}meta{os.sep}hyperlist",
        "--add-data", f"Logo.png{delimiter}.",
        "--add-data", f"icon.ico{delimiter}.",
        "Customisation.pyw"
    ]
    
    # Add --icon if not linux
    if sys.platform != "linux":
        command.insert(1, "--icon=icon.ico")
    
    # Add --onefile if not macOS, macOS uses a folder structure for apps
    if sys.platform != "darwin":
        command.insert(1, "--onefile")
    
    try:
        # Run the PyInstaller command
        print(f"Running: {' '.join(command)}")
        subprocess.run(command, check=True)
        
        # Handle platform-specific executable paths and extensions
        if sys.platform == "win32":
            exe_ext = ".exe"
        elif sys.platform == "darwin":
            exe_ext = ".app"
        else:
            exe_ext = ""
            
        print("Build completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running PyInstaller: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()