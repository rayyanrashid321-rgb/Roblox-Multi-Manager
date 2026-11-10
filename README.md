# Roblox Multi Manager

Best practical version of a Windows multi-instance Roblox tool built in Python.

## Features

- Multi-instance (holds the Roblox singleton mutex)
- Launch Many — start up to 50 windows with a delay
- Game Search + Popular games
- Favorites
- Profiles and Profile Groups
- FastFlags editor with presets (Low End, Balanced, High Quality, FPS Focus)
- Process Watcher — list clients by PID/memory and close selected
- Dashboard with live client count
- Close All Roblox
- Auto-start multi-instance option
- No cookies or passwords stored

## Requirements

- Windows 10 or 11
- Python 3.8 or newer (only if you run the .py file)

## How to download and use

### Option 1: Run the Python file (simplest)

1. Go to https://github.com/rayyanrashid321-rgb/Roblox-Multi-Manager
2. Click the green **Code** button → **Download ZIP**
3. Extract the ZIP to a folder
4. Close every Roblox window
5. Open the folder, right-click inside it → **Open in Terminal** (or PowerShell)
6. Type:
   ```
   python launcher.py
   ```
7. Click **Start Multi-Instance**, then use the other buttons/tabs

### Option 2: Make a double-click .exe (no Python needed later)

1. Do steps 1–3 above
2. Open PowerShell in the extracted folder and run:
   ```powershell
   pip install pyinstaller
   pyinstaller --onefile --windowed --name RobloxMulti launcher.py
   ```
3. When it finishes, open the new `dist` folder
4. Double-click **RobloxMulti.exe**
5. You can move that .exe anywhere and run it like a normal app

## First-time tips

- Always start multi-instance **before** opening Roblox
- Use **Launch Many** if you want a lot of windows (add a delay of 2–5 seconds)
- Use the **Watcher** tab to see or close individual clients
- FastFlags need a Roblox restart to take effect

## Notes

- Profiles, favorites, and groups store only Place IDs and names
- Use responsibly. Multiple accounts are allowed; ban evasion and botting are not

MIT License
