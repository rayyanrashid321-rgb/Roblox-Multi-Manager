# Roblox Multi Manager

Windows desktop tool for multi-instance Roblox, game search, favorites, profiles, and FastFlags.

## Features

- Multi-instance (holds Roblox singleton mutex)
- Game Search — live results with players and visits, one-click launch
- Favorites — save games and launch them later
- Launch profiles (Place ID + optional private server)
- FastFlags editor with Low End / Balanced / High Quality / FPS Focus presets
- Dashboard with client count + Close All Roblox
- Auto-detect Roblox install
- Auto-start multi-instance
- Process Watcher — list running clients by PID and memory, close selected ones
- Profile Groups — create groups and launch multiple places at once
- Popular games quick search
- Local session notes
- No cookies or passwords stored

## Requirements

- Windows 10 or 11
- Python 3.8+ (or build an .exe)

## Quick Start

1. Download the ZIP from this repo.
2. Extract it.
3. Close all Roblox windows.
4. Run: `python launcher.py`
5. Click **Start Multi-Instance**, then use Game Search, Favorites, or Profiles.

## Make a double-click .exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name RobloxMulti launcher.py
```

The .exe appears in the `dist` folder.

## Notes

- FastFlags are client-side. Restart Roblox after saving. Some flags may be ignored.
- Profiles and favorites store only Place IDs and names.
- Use responsibly. Multiple accounts are allowed; ban evasion and botting are not.

MIT License
