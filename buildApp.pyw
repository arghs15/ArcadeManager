import os
import subprocess

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
    
    # PyInstaller command
    command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--add-data", "meta\\hyperlist\\META.csv;meta\\hyperlist",
        "--add-data", "Logo.png;.",
        "--add-data", "icon.ico;.",
        "--icon=icon.ico",
        "CustomisationFUA.pyw"
    ]
    
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
