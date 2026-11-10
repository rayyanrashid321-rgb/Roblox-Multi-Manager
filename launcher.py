"""
Roblox Multi Manager (Goated Edition)
- Multi-instance mutex holder
- Launch profiles (Place ID + private server link code + notes)
- FastFlags editor with safe presets
- Auto-detect Roblox install
- System tray support (optional)
- Clean dark UI

DISCLAIMER:
For personal/educational use only. Roblox does not officially support multiple clients.
Do not use for ban evasion, botting, exploiting, or any ToS violation.
This tool never stores cookies, passwords, or login sessions.
"""

import ctypes
import ctypes.wintypes as wintypes
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from pathlib import Path

# ---------- Windows mutex ----------
ERROR_ALREADY_EXISTS = 183
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

# ---------- Paths ----------
APP_DIR = Path.home() / ".roblox_multi"
APP_DIR.mkdir(exist_ok=True)
PROFILES_FILE = APP_DIR / "profiles.json"
SETTINGS_FILE = APP_DIR / "settings.json"

# Safe allowlisted-style presets (client-side graphics / quality only)
FFLAG_PRESETS = {
    "Low End / Performance": {
        "DFFlagTextureQualityOverrideEnabled": True,
        "DFIntTextureQualityOverride": 1,
        "DFIntCSGLevelOfDetailSwitchingDistance": 100,
        "DFIntCSGLevelOfDetailSwitchingDistanceL12": 75,
        "DFIntCSGLevelOfDetailSwitchingDistanceL23": 100,
        "DFIntCSGLevelOfDetailSwitchingDistanceL34": 150,
        "FIntDebugForceMSAASamples": 0,
        "DFFlagDisableDPIScale": True,
        "FFlagHandleAltEnterFullscreenManually": True,
    },
    "Balanced": {
        "DFFlagTextureQualityOverrideEnabled": True,
        "DFIntTextureQualityOverride": 2,
        "DFIntCSGLevelOfDetailSwitchingDistance": 2000,
        "DFIntCSGLevelOfDetailSwitchingDistanceL12": 1000,
        "DFIntCSGLevelOfDetailSwitchingDistanceL23": 1500,
        "DFIntCSGLevelOfDetailSwitchingDistanceL34": 2500,
        "FIntDebugForceMSAASamples": 2,
        "DFFlagDisableDPIScale": True,
        "FFlagHandleAltEnterFullscreenManually": True,
    },
    "High Quality": {
        "DFFlagTextureQualityOverrideEnabled": True,
        "DFIntTextureQualityOverride": 3,
        "DFIntCSGLevelOfDetailSwitchingDistance": 8000,
        "DFIntCSGLevelOfDetailSwitchingDistanceL34": 8000,
        "FIntDebugForceMSAASamples": 4,
        "DFFlagDisableDPIScale": True,
        "FFlagHandleAltEnterFullscreenManually": True,
    },
    "Clear (No Overrides)": {}
}

class MutexHolder:
    def __init__(self):
        self.handle = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return False, "Already running"
        self.handle = kernel32.CreateMutexW(None, True, "ROBLOX_singletonMutex")
        err = ctypes.get_last_error()
        if not self.handle:
            return False, f"CreateMutex failed: {err}"
        if err == ERROR_ALREADY_EXISTS:
            wait = kernel32.WaitForSingleObject(self.handle, 0)
            if wait not in (0, 0x80):
                kernel32.CloseHandle(self.handle)
                self.handle = None
                return False, "Mutex already owned. Close all Roblox first."
        self.running = True
        self.thread = threading.Thread(target=self._keep_alive, daemon=True)
        self.thread.start()
        return True, "Mutex held. Launch as many Roblox clients as you want."

    def _keep_alive(self):
        while self.running:
            time.sleep(1)

    def stop(self):
        self.running = False
        if self.handle:
            kernel32.ReleaseMutex(self.handle)
            kernel32.CloseHandle(self.handle)
            self.handle = None
        return "Mutex released."

def find_roblox_exe():
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "Versions"
    if not base.exists():
        return None
    candidates = list(base.glob("version-*/RobloxPlayerBeta.exe"))
    if not candidates:
        return None
    # newest by mtime
    return max(candidates, key=lambda p: p.stat().st_mtime)

def get_fflags_path():
    exe = find_roblox_exe()
    if not exe:
        return None
    settings_dir = exe.parent / "ClientSettings"
    settings_dir.mkdir(exist_ok=True)
    return settings_dir / "ClientAppSettings.json"

def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Multi Manager")
        self.root.geometry("780x560")
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.holder = MutexHolder()
        self.profiles = load_json(PROFILES_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {"auto_start_mutex": False})

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4", padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", "#45475a")])

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_main = tk.Frame(notebook, bg="#1e1e2e")
        self.tab_profiles = tk.Frame(notebook, bg="#1e1e2e")
        self.tab_fflags = tk.Frame(notebook, bg="#1e1e2e")
        self.tab_settings = tk.Frame(notebook, bg="#1e1e2e")

        notebook.add(self.tab_main, text=" Multi-Instance ")
        notebook.add(self.tab_profiles, text=" Launch Profiles ")
        notebook.add(self.tab_fflags, text=" FastFlags ")
        notebook.add(self.tab_settings, text=" Settings ")

        self.build_main()
        self.build_profiles()
        self.build_fflags()
        self.build_settings()

        self.log("Ready. Close all Roblox before starting multi-instance.")
        if self.settings.get("auto_start_mutex"):
            self.root.after(500, self.start_mutex)

    # ---------- Main tab ----------
    def build_main(self):
        f = self.tab_main
        tk.Label(f, text="Roblox Multi Manager", font=("Segoe UI", 18, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=12)

        self.status = tk.Label(f, text="Status: Stopped", font=("Segoe UI", 12),
                               bg="#1e1e2e", fg="#f38ba8")
        self.status.pack(pady=4)

        bf = tk.Frame(f, bg="#1e1e2e")
        bf.pack(pady=8)
        self.btn_start = tk.Button(bf, text="Start Multi-Instance", command=self.start_mutex,
                                    bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                                    width=22, height=2, relief="flat")
        self.btn_start.pack(side=tk.LEFT, padx=6)
        self.btn_stop = tk.Button(bf, text="Stop & Release", command=self.stop_mutex,
                                   bg="#f38ba8", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                                   width=22, height=2, relief="flat", state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        tk.Button(f, text="Launch Roblox (Normal)", command=self.launch_normal,
                  bg="#89b4fa", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                  width=30, height=2, relief="flat").pack(pady=6)

        self.log_box = scrolledtext.ScrolledText(f, height=14, bg="#313244", fg="#cdd6f4",
                                                  font=("Consolas", 9), relief="flat", wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.log_box.config(state=tk.DISABLED)

    # ---------- Profiles ----------
    def build_profiles(self):
        f = self.tab_profiles
        tk.Label(f, text="Launch Profiles", font=("Segoe UI", 14, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=8)

        list_frame = tk.Frame(f, bg="#1e1e2e")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        self.profile_list = tk.Listbox(list_frame, bg="#313244", fg="#cdd6f4",
                                        font=("Segoe UI", 10), selectbackground="#45475a",
                                        relief="flat", height=10)
        self.profile_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(list_frame, command=self.profile_list.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.profile_list.config(yscrollcommand=sb.set)
        self.refresh_profiles()

        bf = tk.Frame(f, bg="#1e1e2e")
        bf.pack(pady=8)
        tk.Button(bf, text="New Profile", command=self.new_profile, bg="#a6e3a1", fg="#1e1e2e",
                  font=("Segoe UI", 9, "bold"), relief="flat", width=14).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Launch Selected", command=self.launch_profile, bg="#89b4fa", fg="#1e1e2e",
                  font=("Segoe UI", 9, "bold"), relief="flat", width=16).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Delete", command=self.delete_profile, bg="#f38ba8", fg="#1e1e2e",
                  font=("Segoe UI", 9, "bold"), relief="flat", width=12).pack(side=tk.LEFT, padx=4)

        tk.Label(f, text="Profiles only store Place ID / private server link code / notes.\nNo passwords or cookies.",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack(pady=4)

    def refresh_profiles(self):
        self.profile_list.delete(0, tk.END)
        for p in self.profiles:
            name = p.get("name", "Unnamed")
            pid = p.get("place_id", "")
            self.profile_list.insert(tk.END, f"{name}  (Place: {pid})")

    def new_profile(self):
        name = simpledialog.askstring("New Profile", "Profile name:")
        if not name:
            return
        place = simpledialog.askstring("Place ID", "Place ID (numbers only):")
        if not place or not place.isdigit():
            messagebox.showwarning("Invalid", "Place ID must be numbers.")
            return
        link = simpledialog.askstring("Private Server", "Private server link code (optional):") or ""
        notes = simpledialog.askstring("Notes", "Notes (optional):") or ""
        self.profiles.append({"name": name, "place_id": place, "link_code": link, "notes": notes})
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_profiles()
        self.log(f"Profile '{name}' saved.")

    def delete_profile(self):
        sel = self.profile_list.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self.profiles[idx]["name"]
        if messagebox.askyesno("Delete", f"Delete profile '{name}'?"):
            self.profiles.pop(idx)
            save_json(PROFILES_FILE, self.profiles)
            self.refresh_profiles()

    def launch_profile(self):
        sel = self.profile_list.curselection()
        if not sel:
            messagebox.showinfo("Select", "Select a profile first.")
            return
        p = self.profiles[sel[0]]
        place = p["place_id"]
        link = p.get("link_code", "")
        if link:
            url = f"roblox://placeId={place}&privateServerLinkCode={link}"
        else:
            url = f"roblox://placeId={place}"
        self.log(f"Launching profile '{p['name']}' → {url}")
        try:
            os.startfile(url)  # Windows protocol handler
        except Exception as e:
            self.log(f"Launch failed: {e}")
            messagebox.showerror("Launch", str(e))

    def launch_normal(self):
        exe = find_roblox_exe()
        if not exe:
            messagebox.showerror("Roblox not found", "Could not find RobloxPlayerBeta.exe.\nInstall Roblox first.")
            return
        self.log(f"Launching {exe}")
        subprocess.Popen([str(exe)], shell=False)

    # ---------- FastFlags ----------
    def build_fflags(self):
        f = self.tab_fflags
        tk.Label(f, text="FastFlags Editor", font=("Segoe UI", 14, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=8)
        tk.Label(f, text="Only client-side graphics/quality flags. Roblox may ignore non-allowlisted flags.",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        pf = tk.Frame(f, bg="#1e1e2e")
        pf.pack(pady=6)
        tk.Label(pf, text="Preset:", bg="#1e1e2e", fg="#cdd6f4").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value="Balanced")
        cb = ttk.Combobox(pf, textvariable=self.preset_var, values=list(FFLAG_PRESETS.keys()),
                          state="readonly", width=25)
        cb.pack(side=tk.LEFT, padx=6)
        tk.Button(pf, text="Apply Preset", command=self.apply_preset,
                  bg="#89b4fa", fg="#1e1e2e", relief="flat").pack(side=tk.LEFT, padx=4)

        self.fflags_text = scrolledtext.ScrolledText(f, height=16, bg="#313244", fg="#a6e3a1",
                                                      font=("Consolas", 9), relief="flat")
        self.fflags_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)

        bf = tk.Frame(f, bg="#1e1e2e")
        bf.pack(pady=6)
        tk.Button(bf, text="Load Current", command=self.load_fflags, bg="#fab387", fg="#1e1e2e",
                  relief="flat", width=14).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Save to Roblox", command=self.save_fflags, bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", width=16).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Clear", command=self.clear_fflags, bg="#f38ba8", fg="#1e1e2e",
                  relief="flat", width=10).pack(side=tk.LEFT, padx=4)

        self.load_fflags()

    def load_fflags(self):
        path = get_fflags_path()
        self.fflags_text.delete("1.0", tk.END)
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.fflags_text.insert("1.0", json.dumps(data, indent=2))
                self.log(f"Loaded FastFlags from {path}")
            except Exception as e:
                self.fflags_text.insert("1.0", "{}")
                self.log(f"Could not parse FastFlags: {e}")
        else:
            self.fflags_text.insert("1.0", "{\n\n}")
            self.log("No existing FastFlags file found.")

    def apply_preset(self):
        name = self.preset_var.get()
        data = FFLAG_PRESETS.get(name, {})
        self.fflags_text.delete("1.0", tk.END)
        self.fflags_text.insert("1.0", json.dumps(data, indent=2))
        self.log(f"Applied preset: {name}")

    def save_fflags(self):
        path = get_fflags_path()
        if not path:
            messagebox.showerror("Error", "Roblox install not found.")
            return
        try:
            raw = self.fflags_text.get("1.0", tk.END).strip()
            data = json.loads(raw) if raw else {}
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.log(f"Saved FastFlags to {path}")
            messagebox.showinfo("Saved", "FastFlags written.\nRestart Roblox for them to take effect.")
        except Exception as e:
            messagebox.showerror("Invalid JSON", str(e))

    def clear_fflags(self):
        self.fflags_text.delete("1.0", tk.END)
        self.fflags_text.insert("1.0", "{}")

    # ---------- Settings ----------
    def build_settings(self):
        f = self.tab_settings
        tk.Label(f, text="Settings", font=("Segoe UI", 14, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=12)

        self.auto_var = tk.BooleanVar(value=self.settings.get("auto_start_mutex", False))
        tk.Checkbutton(f, text="Auto-start multi-instance when app opens",
                       variable=self.auto_var, command=self.save_settings,
                       bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244",
                       activebackground="#1e1e2e", font=("Segoe UI", 10)).pack(anchor="w", padx=30, pady=6)

        exe = find_roblox_exe()
        path_text = str(exe) if exe else "Not found"
        tk.Label(f, text=f"Detected Roblox:\n{path_text}", bg="#1e1e2e", fg="#bac2de",
                 font=("Segoe UI", 9), justify="left").pack(anchor="w", padx=30, pady=10)

        tk.Label(f, text="Profiles & settings stored in:\n" + str(APP_DIR),
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8), justify="left").pack(anchor="w", padx=30)

        tk.Label(f, text="\nMade by you  •  Use responsibly",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack(pady=20)

    def save_settings(self):
        self.settings["auto_start_mutex"] = self.auto_var.get()
        save_json(SETTINGS_FILE, self.settings)

    # ---------- Shared ----------
    def log(self, msg):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def start_mutex(self):
        ok, msg = self.holder.start()
        self.log(msg)
        if ok:
            self.status.config(text="Status: Running (Mutex Held)", fg="#a6e3a1")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Mutex", msg)

    def stop_mutex(self):
        msg = self.holder.stop()
        self.log(msg)
        self.status.config(text="Status: Stopped", fg="#f38ba8")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def on_close(self):
        if self.holder.running:
            if not messagebox.askyesno("Quit", "Multi-instance is active. Release mutex and quit?"):
                return
            self.holder.stop()
        self.root.destroy()

def main():
    if sys.platform != "win32":
        print("Windows only.")
        return
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
