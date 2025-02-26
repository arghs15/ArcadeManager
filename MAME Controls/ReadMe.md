Here's a detailed explanation of the search process for game controls in your application:

Step 1: Initial ROM Detection
The app scans your roms/ directory to find all available ROM files
It strips the file extensions to get base ROM names (e.g., "sf2.zip" → "sf2")
This creates the self.available_roms set with all your ROM names
Step 2: Direct Match in controls.json
For each ROM in your collection, the app first tries to find an exact match in controls.json
It searches for a game entry where romname exactly equals your ROM name
Example: For "sf2", it looks for "romname": "sf2" in controls.json
If found, this is the most straightforward match
Step 3: Regional Variant Detection
If no direct match is found, it tries regional variants
It strips region codes like "j" (Japan), "u" (USA), "e" (Europe), etc.
Example: "sf2j" (Street Fighter 2 Japan) → base name "sf2"
It then tries to match this base name against other entries in controls.json
If a match is found (e.g., "sf2" in controls.json matches the base name of "sf2j"), it's considered a variant match
Step 4: Clone/Parent Relationship Search
If still no match, it consults mame.xml for relationships
It looks up your ROM in mame.xml and checks for two key attributes:
cloneof: Indicates this ROM is a clone of another game
romof: Indicates what ROM set/hardware platform this game uses
Example for "vsava" (Vampire Savior Asia):
mame.xml shows cloneof="vsav" meaning it's a clone of "vsav"
The app then looks for "vsav" in controls.json to use its controls for "vsava"
Example for "aof2":
mame.xml shows romof="neogeo" meaning it runs on Neo Geo hardware
The app finds "neogeo" in controls.json and uses those generic Neo Geo controls
Step 5: Results Organization
Direct matches: ROM has an exact entry in controls.json
Variant matches: ROM is a regional variant of a game in controls.json
Clone matches: ROM is a clone or shares hardware with a game in controls.json
Unmatched ROMs: No control data could be found through any method
The key advantage of the clone/parent detection is handling platforms like Neo Geo where dozens of games ("aof", "aof2", "kof97", etc.) all share the same control layout defined in a single "neogeo" entry in controls.json. Instead of needing individual entries for each game, they all inherit from the hardware platform entry.

This tiered approach maximizes your coverage by intelligently connecting related games rather than requiring exact matches for everything.




