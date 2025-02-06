# Customisation CoinOPS Build Manager

A Python-based GUI application for managing gaming collections, themes, and configurations. Built with customtkinter and tkinter, this tool provides a comprehensive interface for managing ROMs, artwork, and playlists across different collections.

## Features

- Theme Management: Create and manage multiple theme collections
- ROM Filtering: Filter and manage arcade/game ROMs
- Playlist Creation: Generate and manage custom playlists
- Advanced Configurations: Customize game settings and controls
- Collection Management: Organize and maintain game collections
- Built-in System Monitor: Track system performance and resource usage

## Deployment

To build the application for distribution, use the included `buildApp.pyw` script. This script uses PyInstaller to create a standalone executable with all necessary resources:

1. Ensure packages are installed:
```bash
pip install -r requirements.txt
```

2. Run `buildApp.pyw`

The script will automatically:
- Detect the current directory
- Package required resources (META.csv, JSON files, icons)
- Create a single-file executable (`customisation.exe`)

```python
# buildApp.pyw contents
import os
import subprocess

def main():
    # Automatically determine script location
    script_location = os.path.dirname(os.path.abspath(__file__))
    
    # PyInstaller command with required resources
    command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--add-data", "meta\\hyperlist\\META.csv;meta\\hyperlist",
        "--add-data", "whats_new.json;.",
        "--add-data", "config_overrides.json;.",
        "--add-data", "build_types.json;.",
        "--add-data", "Logo.png;.",
        "--add-data", "icon.ico;.",
        "--icon=icon.ico",
        "Customisation.pyw"
    ]
    
    try:
        subprocess.run(command, check=True)
        print("Build completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running PyInstaller: {e}")

if __name__ == "__main__":
    main()
```

The resulting `customisation.exe` will be created in the `dist` directory.

## Splash Screen and Loading

The splash screen currently uses the Helper.jpg file in the root of all builds as a temp place holder until an official splash image is created.

## Configuration Files
The application uses a three-tier configuration hierarchy:

1. **customisation.ini** (Highest Priority)
   - User settings and preferences
   - Overrides all other settings
   - Can be manually edited for maximum control
   - Created automatically on first run
   - Located in `autochanger/customisation.ini`

2. **config_overrides.json** (Middle Priority)
   - Developer-focused configuration
   - Overrides hardcoded defaults
   - Useful for maintaining different feature sets without code changes
   - Optional file, won't affect functionality if missing

3. **Hardcoded Defaults** (Lowest Priority)
   - Base configuration in the code
   - Used when no overrides exist
   - Ensures basic functionality

### customisation.ini
The highest priority configuration file that represents user settings. Created automatically on first run, this file can be manually edited to enable or disable various features. Any settings here will override both JSON overrides and hardcoded values:
```ini
[Settings]
fullscreen = false
appearance_mode = Dark
# Additional settings can be added manually to override any feature
```

## Asset Files

- `icon.ico` (application icon)
- `Logo.png` (application logo)
- `meta\\hyperlist\\META.csv` (used for Filter Games)
- `whats_new.json` (used for easy edits to the Whats New popup)
- `config_overrides.json` (list of settings to configure)
- `build_types.json` (list of build types used for Themes tab)

### config_overrides.json (Optional)
A developer-focused configuration that overrides hardcoded defaults without touching the base code. These overrides will be superseded by any settings in customisation.ini. Ideal for maintaining different feature sets or creating custom builds:
```json
{
  "Tabs": {
    "multi_path_themes_tab": {
      "default": "always",
      "type": "str"
    }
  },
  "ButtonVisibility": {
    "show_move_artwork_button": {
      "default": "always",
      "type": "str"
    }
  }
}
```

### whats_new.json (Optional)
Defines content for the "What's New" popup, displaying recent changes and features:
```json
{
  "version": "2.2.9",
  "sections": [
    {
      "section_header": "New Features",
      "section_color": "#4CAF50",
      "items": [
        {
          "title": "Feature Title",
          "description": "Feature description",
          "icon_key": "feature_icon",
          "full_width": true
        }
      ]
    }
  ]
}
```

## Build Types and Paths
The application supports multiple build types with specific paths:

- Settings (S): `collections/zzzSettings/`
  - ROMs: `/collections/zzzSettings/roms`
  - Videos: `/collections/zzzSettings/medium_artwork/video`
  - Logos: `/collections/zzzSettings/medium_artwork/logo`

- Shutdown (U): `collections/zzzShutdown/`
  - ROMs: `/collections/zzzShutdown/roms`
  - Videos: `/collections/zzzShutdown/medium_artwork/video`
  - Logos: `/collections/zzzShutdown/medium_artwork/logo`

- Dynamic (D): `- Themes`
  - Videos: `/autochanger/themes/video`
  - Logos: `/autochanger/themes/logo`

## Custom Configuration

### Adding Collection Exclusions
Add patterns to exclude specific collections or ROMs using config_overrides.json:
```json
{
  "Settings": {
    "additional_collection_excludes": {
      "default": ["pattern1", "pattern2"],
      "type": "List[str]"
    }
  }
}
```

### Custom Themes
Add additional theme folders:
```json
{
  "Settings": {
    "additional_theme_folders": {
      "default": ["path1", "path2"],
      "type": "List[str]"
    }
  }
}
```

## Tab and Button Management

### Tab Visibility
Tabs can be controlled with three states:
- `always`: Tab is always shown
- `never`: Tab is never shown
- `auto`: Tab visibility depends on context (build type, folder existence)

### Button Visibility
Buttons can be controlled with two states:
- `always`: Button is visible
- `never`: Button is hidden

These can be configured in:
1. customisation.ini (for user preferences)
2. config_overrides.json (for default states)

## Performance Monitoring

The application includes built-in performance monitoring:
- System resource usage
- Startup timing
- Tab load times
- Memory usage

Access these metrics through the "System Info" button in the application.
