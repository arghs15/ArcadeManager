# MAME Control Configuration Checker

A powerful tool for managing, analyzing, and configuring MAME control layouts for your ROM collection. This application helps you visualize control mappings, check for custom configurations, and generate controller setup files.

## Features

- 🎮 **Control Visualization**: Easily view control layouts for each MAME game
- 🔍 **Smart ROM Detection**: Identifies ROMs through direct matches, regional variants, and clone relationships
- 📊 **Comprehensive Analysis**: Displays statistics and detailed ROM coverage information
- ⚙️ **Config Generation**: Automatically creates control configuration files for compatible controllers
- 🔄 **Dual Processing Modes**: Choose between comprehensive or high-speed analysis
- 📋 **Custom Config Support**: View and manage your existing MAME control configurations
- 👁️ **In-Game Reference Mode**: Large, easy-to-read display for mid-game control reference

## Installation

1. **Place the script in your MAME directory** - The application needs access to your MAME files
2. **Ensure required data files are present**:
   - `controls.json` - Contains control layouts for games
   - `gamedata.json` - Additional game control information (optional but recommended)
   - `mame.xml` - MAME ROM database for relationship detection (optional)
3. **Install dependencies**: `pip install customtkinter`
4. **Run the application**: `python MAME_Controls.pyw`

## Usage

### Basic Navigation

- **Game List**: Browse and select games from the left panel
- **Search**: Filter games by typing in the search box
- **Control Display**: View detailed control information on the right panel

### Mode Selection

The application offers two processing modes:

- **Normal Mode**: Uses controls.json and mame.xml for maximum accuracy
- **Fast Mode**: Uses only gamedata.json for speed and expanded coverage

Toggle between modes using the "Fast Mode" switch in the interface.

### Special Features

- **XInput Mappings**: Toggle between standard and XInput control display
- **In-Game Mode**: Switch to a large-format display for easier in-game reference
- **Show Unmatched ROMs**: Analyze which ROMs are missing control data
- **Generate Info Files**: Create controller configuration files for all ROMs

## Data Sources

### controls.json

The primary data source for MAME control information in normal mode. Contains standardized control layouts developed by the MAME community.

### gamedata.json

A comprehensive alternative data source used exclusively in fast mode. May contain more detailed information for certain games, particularly for racing and specialized arcade cabinets.

### mame.xml

Used to identify relationships between ROMs (parent/clone, hardware platform) in normal mode. Helps expand control coverage by applying parent control layouts to clone ROMs.

## Game Selection Indicators

In the game list, each ROM is prefixed with indicators:

- `*` - ROM has a custom configuration in the cfg directory
- `+` - ROM has control data available
- `-` - ROM lacks control data

## Understanding Analysis Results

The unmatched ROM analysis provides detailed information about your collection:

- **Direct Matches**: ROMs found directly in the control data
- **Variant Matches**: ROMs matched by removing region codes (e.g., sf2j → sf2)
- **Clone Matches**: ROMs matched via clone/parent relationships
- **Unmatched ROMs**: ROMs with no available control data

## Performance Considerations

- **Fast Mode**: Significantly improves startup time by only loading gamedata.json
- **Normal Mode**: Provides comprehensive analysis but may be slower to start, especially with large mame.xml files
- **Generating Config Files**: Works with whichever data source is active in the current mode

## Tips and Tricks

- Press F11 to toggle fullscreen mode
- Press Escape to exit fullscreen mode
- Use the search box to quickly find specific games
- The blue highlight shows which game is currently selected
- Check the "In-Game Mode" switch for a simplified, larger control display
- Generate info files to create control configuration files for all your ROMs

## Contributing

Contributions to improve the application are welcome! Some ways to help:

- Add more specialized control handling for specific game genres
- Expand the default control mappings for racing games, etc.
- Improve performance for large ROM collections
- Create additional visualization options

## License

This application is provided as open source software. You are free to use, modify, and distribute it according to your needs.

## Acknowledgments

This tool builds upon the work of the MAME community and various control mapping projects that have documented arcade control layouts over the years.
