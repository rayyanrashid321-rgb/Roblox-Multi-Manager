"""
Roblox Multi Manager
Multi-instance + profiles + FastFlags + process monitor + tray-ready

For personal/educational use only.
Does not store cookies or passwords.
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

# ---------- Mutex ----------
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

APP_DIR = Path.home() / ".roblox_multi"
APP_DIR.mkdir(exist_ok=True)
PROFILES_FILE = APP_DIR / "profiles.json"
SETTINGS_FILE = APP_DIR / "settings.json"

FFLAG_PRESETS = {
    "Performance (Low End)": {
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
    "Clear": {}
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
        self.thread = threading.Thread(target=self._keep, daemon=True)
        self.thread.start()
        return True, "Multi-instance active"

    def _keep(self):
        while self.running:
            time.sleep(1)

    def stop(self):
        self.running = False
        if self.handle:
            kernel32.ReleaseMutex(self.handle)
            kernel32.CloseHandle(self.handle)
            self.handle = None
        return "Multi-instance stopped"

def find_roblox_exe():
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "Versions"
    if not base.exists():
        return None
    cands = list(base.glob("version-*/RobloxPlayerBeta.exe"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None

def get_fflags_path():
    exe = find_roblox_exe()
    if not exe:
        return None
    d = exe.parent / "ClientSettings"
    d.mkdir(exist_ok=True)
    return d / "ClientAppSettings.json"

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
        self.root.geometry("820x600")
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.holder = MutexHolder()
        self.profiles = load_json(PROFILES_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {"auto_start": False})

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e2e")
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#45475a")])

        nb = ttk.Notebook(root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_dash = tk.Frame(nb, bg="#1e1e2e")
        self.tab_profiles = tk.Frame(nb, bg="#1e1e2e")
        self.tab_fflags = tk.Frame(nb, bg="#1e1e2e")
        self.tab_settings = tk.Frame(nb, bg="#1e1e2e")

        nb.add(self.tab_dash, text=" Dashboard ")
        nb.add(self.tab_profiles, text=" Profiles ")
        nb.add(self.tab_fflags, text=" FastFlags ")
        nb.add(self.tab_settings, text=" Settings ")

        self.build_dash()
        self.build_profiles()
        self.build_fflags()
        self.build_settings()

        self.log("Ready. Close all Roblox, then start multi-instance.")
        self.update_stats()
        if self.settings.get("auto_start"):
            self.root.after(400, self.start_mutex)

    def build_dash(self):
        f = self.tab_dash
        tk.Label(f, text="Roblox Multi Manager", font=("Segoe UI", 16, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=10)

        self.status = tk.Label(f, text="Multi-instance: Stopped", font=("Segoe UI", 11),
                               bg="#1e1e2e", fg="#f38ba8")
        self.status.pack()

        bf = tk.Frame(f, bg="#1e1e2e")
        bf.pack(pady=8)
        self.btn_start = tk.Button(bf, text="Start Multi-Instance", command=self.start_mutex,
                                    bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                                    width=20, height=2, relief="flat")
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_stop = tk.Button(bf, text="Stop", command=self.stop_mutex,
                                   bg="#f38ba8", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                                   width=12, height=2, relief="flat", state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Launch Roblox", command=self.launch_normal,
                  bg="#89b4fa", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                  width=16, height=2, relief="flat").pack(side=tk.LEFT, padx=5)

        stats = tk.Frame(f, bg="#313244")
        stats.pack(fill=tk.X, padx=15, pady=8)
        self.lbl_procs = tk.Label(stats, text="Roblox clients: 0", bg="#313244", fg="#cdd6f4", font=("Segoe UI", 10))
        self.lbl_procs.pack(side=tk.LEFT, padx=12, pady=6)
        self.lbl_ram = tk.Label(stats, text="RAM: —", bg="#313244", fg="#cdd6f4", font=("Segoe UI", 10))
        self.lbl_ram.pack(side=tk.LEFT, padx=12)

        self.log_box = scrolledtext.ScrolledText(f, height=12, bg="#313244", fg="#cdd6f4",
                                                  font=("Consolas", 9), relief="flat")
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=6)
        self.log_box.config(state=tk.DISABLED)

    def build_profiles(self):
        f = self.tab_profiles
        tk.Label(f, text="Launch Profiles (no cookies stored)", font=("Segoe UI", 13, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=8)
        lf = tk.Frame(f, bg="#1e1e2e")
        lf.pack(fill=tk.BOTH, expand=True, padx=15)
        self.plist = tk.Listbox(lf, bg="#313244", fg="#cdd6f4", font=("Segoe UI", 10),
                                selectbackground="#45475a", relief="flat")
        self.plist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.refresh_profiles()

        bf = tk.Frame(f, bg="#1e1e2e")
        bf.pack(pady=6)
        tk.Button(bf, text="New", command=self.new_profile, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Launch", command=self.launch_profile, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Delete", command=self.delete_profile, bg="#f38ba8", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)

    def refresh_profiles(self):
        self.plist.delete(0, tk.END)
        for p in self.profiles:
            self.plist.insert(tk.END, f"{p.get('name','?')}  |  Place {p.get('place_id','')}  |  {p.get('notes','')[:30]}")

    def new_profile(self):
        name = simpledialog.askstring("Profile", "Name:")
        if not name: return
        place = simpledialog.askstring("Place ID", "Place ID:")
        if not place or not place.isdigit():
            messagebox.showwarning("Invalid", "Place ID must be numbers")
            return
        link = simpledialog.askstring("Link Code", "Private server link code (optional):") or ""
        notes = simpledialog.askstring("Notes", "Notes (optional):") or ""
        self.profiles.append({"name": name, "place_id": place, "link_code": link, "notes": notes})
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_profiles()
        self.log(f"Added profile: {name}")

    def delete_profile(self):
        s = self.plist.curselection()
        if not s: return
        if messagebox.askyesno("Delete", "Delete this profile?"):
            self.profiles.pop(s[0])
            save_json(PROFILES_FILE, self.profiles)
            self.refresh_profiles()

    def launch_profile(self):
        s = self.plist.curselection()
        if not s:
            messagebox.showinfo("Select", "Pick a profile")
            return
        p = self.profiles[s[0]]
        url = f"roblox://placeId={p['place_id']}"
        if p.get("link_code"):
            url += f"&privateServerLinkCode={p['link_code']}"
        self.log(f"Launching {p['name']}")
        try:
            os.startfile(url)
        except Exception as e:
            messagebox.showerror("Launch", str(e))

    def launch_normal(self):
        exe = find_roblox_exe()
        if not exe:
            messagebox.showerror("Error", "Roblox not found")
            return
        subprocess.Popen([str(exe)])
        self.log("Launched Roblox")

    def build_fflags(self):
        f = self.tab_fflags
        tk.Label(f, text="FastFlags (client graphics only)", font=("Segoe UI", 13, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        pf = tk.Frame(f, bg="#1e1e2e")
        pf.pack()
        self.preset = tk.StringVar(value="Balanced")
        ttk.Combobox(pf, textvariable=self.preset, values=list(FFLAG_PRESETS), state="readonly", width=22).pack(side=tk.LEFT, padx=4)
        tk.Button(pf, text="Apply Preset", command=self.apply_preset, bg="#89b4fa", fg="#1e1e2e", relief="flat").pack(side=tk.LEFT)

        self.ff = scrolledtext.ScrolledText(f, height=18, bg="#313244", fg="#a6e3a1", font=("Consolas", 9), relief="flat")
        self.ff.pack(fill=tk.BOTH, expand=True, padx=15, pady=6)

        bf = tk.Frame(f, bg="#1e1e2e")
        bf.pack(pady=4)
        tk.Button(bf, text="Load", command=self.load_ff, bg="#fab387", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Save", command=self.save_ff, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Clear", command=lambda: self.ff.delete("1.0", tk.END) or self.ff.insert("1.0", "{}"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        self.load_ff()

    def load_ff(self):
        path = get_fflags_path()
        self.ff.delete("1.0", tk.END)
        if path and path.exists():
            try:
                self.ff.insert("1.0", json.dumps(json.loads(path.read_text()), indent=2))
                self.log("Loaded FastFlags")
            except Exception:
                self.ff.insert("1.0", "{}")
        else:
            self.ff.insert("1.0", "{}")

    def apply_preset(self):
        data = FFLAG_PRESETS.get(self.preset.get(), {})
        self.ff.delete("1.0", tk.END)
        self.ff.insert("1.0", json.dumps(data, indent=2))
        self.log(f"Preset: {self.preset.get()}")

    def save_ff(self):
        path = get_fflags_path()
        if not path:
            messagebox.showerror("Error", "Roblox not found")
            return
        try:
            data = json.loads(self.ff.get("1.0", tk.END).strip() or "{}")
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.log("FastFlags saved — restart Roblox")
            messagebox.showinfo("Saved", "Restart Roblox for changes")
        except Exception as e:
            messagebox.showerror("JSON error", str(e))

    def build_settings(self):
        f = self.tab_settings
        tk.Label(f, text="Settings", font=("Segoe UI", 13, "bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=12)
        self.auto = tk.BooleanVar(value=self.settings.get("auto_start", False))
        tk.Checkbutton(f, text="Auto-start multi-instance on launch", variable=self.auto,
                       command=self.save_settings, bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e").pack(anchor="w", padx=30)
        exe = find_roblox_exe()
        tk.Label(f, text=f"Roblox: {exe or 'Not found'}", bg="#1e1e2e", fg="#bac2de",
                 font=("Segoe UI", 9), wraplength=700).pack(anchor="w", padx=30, pady=10)
        tk.Label(f, text=f"Data: {APP_DIR}", bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack(anchor="w", padx=30)

    def save_settings(self):
        self.settings["auto_start"] = self.auto.get()
        save_json(SETTINGS_FILE, self.settings)

    def log(self, msg):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def update_stats(self):
        try:
            import subprocess
            out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe", "/FO", "CSV"], text=True, stderr=subprocess.DEVNULL)
            lines = [l for l in out.splitlines() if "RobloxPlayerBeta" in l]
            count = max(0, len(lines) - 1)
            self.lbl_procs.config(text=f"Roblox clients: {count}")
            self.lbl_ram.config(text="RAM: see Task Manager")
        except Exception:
            self.lbl_procs.config(text="Roblox clients: ?")
        self.root.after(3000, self.update_stats)

    def start_mutex(self):
        ok, msg = self.holder.start()
        self.log(msg)
        if ok:
            self.status.config(text="Multi-instance: Running", fg="#a6e3a1")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Error", msg)

    def stop_mutex(self):
        self.log(self.holder.stop())
        self.status.config(text="Multi-instance: Stopped", fg="#f38ba8")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def on_close(self):
        if self.holder.running and not messagebox.askyesno("Quit", "Stop multi-instance and quit?"):
            return
        if self.holder.running:
            self.holder.stop()
        self.root.destroy()

def main():
    if sys.platform != "win32":
        print("Windows only")
        return
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
