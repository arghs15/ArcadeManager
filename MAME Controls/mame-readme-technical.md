# MAME Control Configuration Checker: Technical Details

This document provides in-depth technical information about the operating modes of the MAME Control Configuration Checker, specifically focusing on the Normal and Fast modes and their internal processes.

## Normal Mode: Detailed Process Flow

Normal mode prioritizes accuracy and comprehensive coverage by using controls.json and mame.xml.

### Data Loading Sequence

1. **controls.json** - Loaded first and completely into memory
   - Parsed into the `self.controls_data` list
   - Regional variant mappings are created for efficient lookups

2. **mame.xml** (if available)
   - Parsed into the `self.mame_xml_data` dictionary
   - ROM relationships (parent/clone, hardware platforms) are extracted
   - Can be a slow process due to the large file size (often 100+ MB)

3. **ROMs Directory**
   - Scanned to identify available ROMs in your collection
   - File extensions are stripped to get base ROM names

### ROM Lookup Process

For each ROM in your collection, the application follows this exact sequence:

1. **Direct Match in controls.json**
   ```python
   game_data = next((game for game in self.controls_data if game['romname'] == romname), None)
   ```
   - Looks for an exact match of the ROM name in controls.json
   - If found, returns a copy of the complete game data

2. **Variant Match by Region Code**
   ```python
   base_name = re.sub(r'[jubew]$', '', romname)
   for game in self.controls_data:
       control_base = re.sub(r'[jubew]$', '', game['romname'])
       if base_name == control_base:
           # Return modified variant data
   ```
   - Strips regional suffixes (j=Japan, u=USA, e=Europe, etc.)
   - Compares the base names to find potential matches
   - If matched, returns a modified copy with "(Variant)" appended to the name

3. **mame.xml Clone/Parent Relationships**
   - **Clone of Parent**:
     ```python
     parent_rom = self.mame_xml_data[romname].get('cloneof')
     parent_data = next((game for game in self.controls_data if game['romname'] == parent_rom), None)
     ```
     - Checks if this ROM is a clone of another game
     - If the parent ROM has control data, uses that with "(Clone)" designation

   - **Hardware Platform**:
     ```python
     rom_of = self.mame_xml_data[romname].get('romof')
     source_data = next((game for game in self.controls_data if game['romname'] == rom_of), None)
     ```
     - Checks if the ROM uses a shared hardware platform (e.g., neogeo)
     - If found, uses the platform's control data with "(Derived)" designation

4. **Not Found**
   - If no match is found through any method, returns `None`
   - ROM will be listed as "unmatched" in the analysis

### Technical Considerations

- **Memory Usage**: Higher than Fast mode due to loading multiple data sources
- **Startup Time**: Slower, primarily due to parsing mame.xml
- **Coverage Quality**: Highest accuracy with proper relationships maintained
- **XML Parsing**: Uses ElementTree with iterative parsing to manage large files

## Fast Mode: Detailed Process Flow

Fast mode prioritizes speed and simplicity by using only gamedata.json.

### Data Loading Sequence

1. **gamedata.json** - Loaded exclusively into memory
   - Parsed into the `self.gamedata_json` dictionary
   - Both main entries and clones are indexed directly for fast lookup
   - Clone relationships are preserved within the data

2. **ROMs Directory**
   - Scanned to identify available ROMs in your collection
   - File extensions are stripped to get base ROM names

### ROM Lookup Process

For each ROM in your collection, the Fast mode follows this exact sequence:

1. **Direct Match in gamedata.json**
   ```python
   if romname in self.gamedata_json:
       game_data = self.gamedata_json[romname]
       # Convert to internal format...
   ```
   - Checks if the ROM name exists directly in gamedata.json
   - If found, converts the data to the internal format used by the application

2. **Finding Control Data**
   ```python
   # Find controls (direct or in a clone)
   controls = None
   if 'controls' in game_data:
       controls = game_data['controls']
   elif 'clones' in game_data:
       for clone in game_data['clones'].values():
           if 'controls' in clone:
               controls = clone['controls']
               break
   ```
   - First checks if the game itself has control data
   - If not, searches through its clones for control data
   - Uses the first set of controls found

3. **Special Processing for Control Types**
   - Racing games, fighting games, and other specialized cabinets get additional processing:
     ```python
     # Special control meanings for racing games
     racing_controls = {
         'daytona': { ... },
         'sega_rally': { ... },
     }
     ```

4. **Format Conversion**
   - gamedata.json uses a different structure than controls.json
   - The fast mode converts this to a unified internal format:
     ```python
     converted_data = {
         'romname': romname,
         'gamename': game_data.get('description', romname),
         'numPlayers': int(game_data.get('playercount', 1)),
         # ...other fields...
         'players': []  # Will contain control data
     }
     ```

5. **Not Found**
   - If the ROM isn't in gamedata.json, returns `None`
   - ROM will be listed as "unmatched" in the analysis

### Technical Considerations

- **Memory Usage**: Lower than Normal mode, only loading a single data source
- **Startup Time**: Significantly faster due to skipping mame.xml parsing
- **Coverage**: May find more ROMs due to gamedata.json's broader coverage
- **JSON Parsing**: Uses Python's built-in json module for fast loading

## Performance Comparison

| Aspect | Normal Mode | Fast Mode |
|--------|------------|-----------|
| Startup Time | Slower (10-30 seconds) | Fast (1-3 seconds) |
| Memory Usage | Higher (~200-500 MB) | Lower (~50-100 MB) |
| ROM Coverage | Comprehensive with relationships | Simple but broad |
| Data Accuracy | Preserves exact relationships | May simplify some relationships |
| Config Generation | Based on controls.json | Based on gamedata.json |

## Mode Selection Guidelines

### When to Use Normal Mode

- When generating configuration files for maximum accuracy
- When analyzing ROM relationships in detail
- When precise control mappings are critical
- When you need to see exact clone/parent relationships

### When to Use Fast Mode

- For day-to-day browsing and reference
- When startup speed is important
- On systems with limited RAM
- When you want to maximize control data coverage
- For working with specialized arcade cabinets (racing, etc.)

## Implementation Details

### Normal Mode Data Flow

```
controls.json → self.controls_data
                ↓
mame.xml     → self.mame_xml_data 
                ↓
ROM request  → get_game_data_from_all_sources()
                ↓
             → [Direct Match] → [Variant Match] → [Clone/Parent Match] → Not Found
```

### Fast Mode Data Flow

```
gamedata.json → self.gamedata_json
                 ↓
ROM request   → get_game_data_from_gamedata_only()
                 ↓
              → [Direct Match] → [Check Game Controls] → [Check Clone Controls] → Not Found
                                        ↓
                                [Convert to Internal Format]
```

## Config Generation Process

The config generation process adapts based on the active mode:

### Normal Mode Config Generation

1. Iterates through `self.controls_data` (from controls.json)
2. For each ROM that exists in your collection:
   - Gets the game data from controls.json or its relationships
   - Maps the controls to the template format
   - Generates and saves the config file

### Fast Mode Config Generation

1. Iterates through all available ROMs in your collection
2. For each ROM:
   - Gets the game data from gamedata.json
   - Maps the controls to the template format
   - Generates and saves the config file

This approach ensures that regardless of which mode you're using, you can generate config files for all ROMs with available control data.
