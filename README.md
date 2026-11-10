# Roblox Multi Manager

A clean, open-source Windows tool for running multiple Roblox clients + launch profiles + FastFlags editor.

## Features

- **Multi-instance** — holds `ROBLOX_singletonMutex` so multiple clients can open
- **Launch Profiles** — save Place ID + optional private server link code + notes
- **Direct Launch** — one-click normal launch or profile launch
- **FastFlags Editor** — load/save `ClientAppSettings.json` with safe graphics presets
- **Auto-detect** Roblox install path
- **Settings** — auto-start mutex on launch
- Dark UI, pure Python (no external dependencies required for core features)

## Requirements

- Windows 10 / 11
- Python 3.8+
- Official Roblox desktop client

## Quick Start

1. Download the repo as ZIP or `git clone`.
2. Close **all** Roblox windows.
3. Run:
   ```bash
   python launcher.py
   ```
4. Go to **Multi-Instance** tab → **Start Multi-Instance**.
5. Keep the window open and launch Roblox (or use profiles).

## Tabs

| Tab | What it does |
|-----|--------------|
| Multi-Instance | Start/stop the mutex + normal launch + log |
| Launch Profiles | Save and launch games / private servers |
| FastFlags | Edit client graphics/quality flags + presets |
| Settings | Auto-start option + detected path |

## FastFlags Notes

- Written to the current Roblox version folder:  
  `%LocalAppData%\Roblox\Versions\version-XXXX\ClientSettings\ClientAppSettings.json`
- Only client-side graphics/quality presets are included. Roblox has an allowlist and may ignore other flags.
- Restart Roblox after saving flags.

## Important Warnings

- Roblox does **not** officially support multiple clients on one PC.
- Using multiple accounts for ban evasion, botting, exploiting, or farming can get accounts banned.
- This tool **never** stores cookies, passwords, or login sessions.
- Antivirus may flag custom launchers. Add an exclusion if needed.
- Use at your own risk. No warranties.

## Make a standalone .exe (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name RobloxMulti launcher.py
```

The `.exe` appears in the `dist` folder.

## License

MIT

Made by you.
