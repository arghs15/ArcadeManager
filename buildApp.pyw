import os
import subprocess
import sys

def main():
    # Prompt user for the full path to the script location
    #script_location = input("Enter the full path to the script directory: ").strip()
    
    # Automatically determine the script's directory
    script_location = os.path.dirname(os.path.abspath(__file__))
    print(f"The script is running from: {script_location}")
    
    # Check if the provided path exists
    if not os.path.isdir(script_location):
        print("Error: The provided path does not exist.")
        return
    
    # Change to the script directory
    os.chdir(script_location)
    
    # on unix, delimiter is :
    delimiter = ";" if os.name == "nt" else ":"

    # PyInstaller command
    command = [
        "pyinstaller",
        "--windowed",
        "--noconfirm",
        "--add-data", f"meta{os.sep}hyperlist{os.sep}META.csv{delimiter}meta{os.sep}hyperlist",
        "--add-data", f"whats_new.json{delimiter}.",
#        "--add-data", f"config_overrides.json{delimiter}.",
#        "--add-data", f"build_types.json{delimiter}.",
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
        print("Build completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running PyInstaller: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
