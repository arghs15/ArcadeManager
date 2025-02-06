# ConfigManager Documentation

## Overview
The ConfigManager class provides a robust configuration management system with multiple layers of settings and overrides. It handles application settings, button visibility, tab visibility, and path management for various build types.

## Configuration Priority
Settings are loaded and applied in the following order (highest to lowest priority):

1. User Settings (customisation.ini in autochanger folder)
2. Distribution Overrides (config_overrides.json in PyInstaller bundle)
3. Class Defaults (defined in AVAILABLE_SETTINGS and BUTTON_VISIBILITY_STATES)

## Key Components

### 1. Settings Management
- **AVAILABLE_SETTINGS**: Dictionary of all possible settings with their defaults, types, and visibility
- **Settings Categories**:
  - `Settings`: General application settings
  - `Controls`: Control configuration settings
  - `Tabs`: Tab visibility settings

Example structure:
```python
AVAILABLE_SETTINGS = {
    'Settings': {
        'setting_name': {
            'default': 'default_value',
            'description': 'Setting description',
            'type': str,  # or bool, List[str], etc.
            'hidden': False  # Whether visible in INI
        }
    }
}
```

### 2. Button Visibility
- **BUTTON_VISIBILITY_STATES**: Controls visibility of UI buttons
- Supports two states: 'always' or 'never'
- Configured in dedicated `[ButtonVisibility]` section in INI file
- Cached for performance

### 3. Build Types
- **BUILD_TYPE_PATHS**: Defines paths for different build configurations
- Three main types:
  - 'D': Deluxe build with no zzzShutdown or zzzSettings folder. Reads from autochangers\themes
  - 'U': Universe builds that read from zzzShutdown
  - 'S': Reads from zzzSettigns
- Build type determines ROM, video, and logo paths

### 4. Path Management
- Handles multiple path types:
  - Theme paths
  - ROM paths
  - Video paths
  - Logo paths
- Supports custom paths and multi-path configurations
- Caches resolved paths for performance

## File Structure

### 1. customisation.ini
Location: `autochanger/customisation.ini`
```ini
[DEFAULT]
config_version = 2.2.9

[Settings]
setting_name = value

[ButtonVisibility]
button_name = always/never

[Controls]
controls_file = controls5.conf

[Tabs]
tab_name_tab = always/auto/never
```

### 2. config_overrides.json
Location: Bundled with PyInstaller
```json
{
    "Settings": {
        "setting_name": {
            "default": "value",
            "type": "str",
            "hidden": false
        }
    },
    "ButtonVisibility": {
        "button_name": {
            "default": "always",
            "type": "str"
        }
    }
}
```

## Key Features

### 1. Version Management
- Tracks configuration version in DEFAULT section
- Handles version upgrades while preserving user settings
- Falls back to defaults if version mismatch occurs

### 2. Cache Management
- Caches frequently accessed values:
  - Build type
  - Button visibility states
  - Tab visibility states
  - Theme paths
- Thread-safe implementation for build type detection

### 3. Logging
- Comprehensive logging system
- Logs stored in autochanger/application.log
- Configurable log levels
- Debug mode for detailed logging

## Usage Examples

### 1. Reading Settings
```python
config = ConfigManager()
value = config.get_setting('Settings', 'setting_name', default='default_value')
```

### 2. Button Visibility
```python
is_visible = config.determine_button_visibility('button_name')
config.update_button_visibility('button_name', 'always')
```

### 3. Path Management
```python
paths = config.get_theme_paths()
build_type = config.get_build_type()
```

## Common Operations

### 1. Updating Settings
```python
config.set_setting('Settings', 'setting_name', 'new_value')
config.save_config()
```

### 2. Tab Visibility
```python
is_visible = config.determine_tab_visibility('tab_name')
config.update_tab_visibility('tab_name', 'always')
```

### 3. Controls Management
```python
controls_file = config.get_controls_file()
config.update_controls_file('new_controls.conf')
```

## Best Practices

1. **Setting Updates**
   - Always use provided methods instead of direct access
   - Call save_config() after updates
   - Check setting existence before updates

2. **Path Handling**
   - Use get_theme_paths() for consistent path resolution
   - Consider build type when handling paths
   - Use cached paths when available

3. **Configuration Changes**
   - Add new settings to AVAILABLE_SETTINGS
   - Document new settings with descriptions
   - Consider backward compatibility

4. **Error Handling**
   - Handle missing configuration gracefully
   - Provide sensible defaults
   - Log configuration errors appropriately

## Troubleshooting

1. **Missing Settings**
   - Check setting exists in AVAILABLE_SETTINGS
   - Verify INI file contains correct sections
   - Check for typos in setting names

2. **Button Visibility Issues**
   - Check ButtonVisibility section in INI
   - Verify button name matches exactly
   - Check config_overrides.json defaults

3. **Path Resolution Problems**
   - Verify build type detection
   - Check path existence on disk
   - Validate custom path configurations
