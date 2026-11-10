# Roblox Multi Manager

Simple Windows desktop tool for multi-instance Roblox, game search, launch profiles, and FastFlags.

## Features

- Multi-instance (holds the Roblox singleton mutex)
- Game Search — type a name, see results with player count and visits, launch or save to profiles
- Launch profiles (Place ID + optional private server link)
- FastFlags editor with presets
- Dashboard with live client count
- Close All Roblox button
- Auto-detect Roblox install
- Auto-start multi-instance option
- No cookies, passwords, or account login stored

## Requirements

- Windows 10 or 11
- Python 3.8+ (or build an .exe)

## Quick Start

1. Download the ZIP from this repo.
2. Extract it.
3. Close all Roblox windows.
4. Run: `python launcher.py`
5. Click **Start Multi-Instance**, then use Game Search or Profiles.

## Make a double-click .exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name RobloxMulti launcher.py
```

The .exe appears in the `dist` folder.

## Notes

- FastFlags are client-side only. Restart Roblox after saving.
- Profiles store only Place ID / link code / notes.
- Use responsibly. Multiple accounts are allowed; ban evasion and botting are not.

MIT License
