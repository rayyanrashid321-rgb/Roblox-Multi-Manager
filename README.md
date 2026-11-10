# Roblox Multi Manager

Desktop Windows tool for running multiple Roblox clients, managing launch profiles, and editing FastFlags.

## Features

- Multi-instance (holds Roblox singleton mutex)
- Launch profiles (Place ID + private server link code + notes)
- FastFlags editor with performance / balanced / high quality presets
- Dashboard with live client count
- Auto-detect Roblox install
- Settings (auto-start multi-instance)
- Pure Python — no cookies or passwords stored

## Requirements

- Windows 10 or 11
- Python 3.8+ (or build the .exe)

## Quick Start

1. Download the ZIP from this repo.
2. Extract it.
3. Close all Roblox windows.
4. Run `python launcher.py`
5. Click **Start Multi-Instance**, then launch Roblox or use profiles.

## Make a double-click .exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name RobloxMulti launcher.py
```

The app is in the `dist` folder.

## Notes

- FastFlags only include client-side graphics flags. Roblox may ignore non-allowlisted ones. Restart Roblox after saving.
- Profiles store only Place ID / link code / notes.
- Use responsibly. Multiple accounts are allowed; ban evasion / botting is not.

MIT License
