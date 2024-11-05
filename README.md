# ArcadeManager
Gui for filtering games, applying advanced configs, and themes

# Building for Windows

## Install libraries
* Install Python (https://www.python.org/downloads/windows/)

## Setup Instructions

1. Download the necessary files and place `Arcade Manager.pyw` and Trackball.ico in the root directory of the build.
2. Place the `MAMEx.csv` file under the `meta\hyperlist` folder.
3. Make any changes needed to the code or the CSV file.
4. Once ready, run the following command from **CMD** from the root of the build:

```bash
pyinstaller --onefile --windowed --add-data "meta\hyperlist\META.csv;meta\hyperlist" --add-data "Logo.png;." --add-data "Potion.ico;." --icon=Potion.ico "Customisation.pyw"
