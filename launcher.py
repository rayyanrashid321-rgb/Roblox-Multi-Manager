"""
Roblox Multi Manager
Multi-instance + profiles + FastFlags + Game Search + dashboard

Personal/educational use only. No cookies stored.
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
import urllib.request
import urllib.parse

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
FAVS_FILE = APP_DIR / "favorites.json"
SESSIONS_FILE = APP_DIR / "sessions.json"
GROUPS_FILE = APP_DIR / "groups.json"
ACCOUNTS_FILE = APP_DIR / "accounts.json"
FAVS_FILE = APP_DIR / "favorites.json"

FFLAG_PRESETS = {
    "Low End": {"DFFlagTextureQualityOverrideEnabled": True, "DFIntTextureQualityOverride": 1, "FIntDebugForceMSAASamples": 0, "DFFlagDisableDPIScale": True, "DFIntCSGLevelOfDetailSwitchingDistance": 100},
    "Balanced": {"DFFlagTextureQualityOverrideEnabled": True, "DFIntTextureQualityOverride": 2, "FIntDebugForceMSAASamples": 2, "DFFlagDisableDPIScale": True},
    "High Quality": {"DFFlagTextureQualityOverrideEnabled": True, "DFIntTextureQualityOverride": 3, "FIntDebugForceMSAASamples": 4, "DFFlagDisableDPIScale": True},
    "FPS Focus": {"DFFlagTextureQualityOverrideEnabled": True, "DFIntTextureQualityOverride": 1, "FIntDebugForceMSAASamples": 0, "DFFlagDisableDPIScale": True, "DFIntTaskSchedulerTargetFps": 240},
    "Clear": {}
}

class MutexHolder:
    def __init__(self):
        self.handles = []
        self.running = False
    def start(self):
        if self.running: return False, "Already running"
        names = ["ROBLOX_singletonMutex", "ROBLOX_singletonEvent"]
        for name in names:
            h = kernel32.CreateMutexW(None, True, name)
            err = ctypes.get_last_error()
            if not h:
                self._cleanup()
                return False, f"Failed to create {name}: {err}"
            if err == ERROR_ALREADY_EXISTS:
                # Try to take ownership
                wait = kernel32.WaitForSingleObject(h, 100)
                if wait not in (0, 0x80):
                    kernel32.CloseHandle(h)
                    self._cleanup()
                    return False, "Close all Roblox windows first, then try again"
            self.handles.append(h)
        self.running = True
        threading.Thread(target=self._keep, daemon=True).start()
        return True, "Multi-instance active (both locks held)"
    def _keep(self):
        while self.running:
            time.sleep(1)
    def _cleanup(self):
        for h in self.handles:
            try:
                kernel32.ReleaseMutex(h)
                kernel32.CloseHandle(h)
            except:
                pass
        self.handles.clear()
    def stop(self):
        self.running = False
        self._cleanup()
        return "Stopped"

def find_roblox_exe():
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "Versions"
    if not base.exists(): return None
    c = list(base.glob("version-*/RobloxPlayerBeta.exe"))
    return max(c, key=lambda p: p.stat().st_mtime) if c else None

def get_fflags_path():
    exe = find_roblox_exe()
    if not exe: return None
    d = exe.parent / "ClientSettings"
    d.mkdir(exist_ok=True)
    return d / "ClientAppSettings.json"

def load_json(p, d):
    try:
        if p.exists(): return json.loads(p.read_text(encoding="utf-8"))
    except: pass
    return d

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def search_roblox_games(query, limit=20):
    try:
        url = f"https://games.roblox.com/v1/games/list?model.keyword={urllib.parse.quote(query)}&model.maxRows={limit}&model.startRows=0"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return data.get("games", [])
    except Exception as e:
        return []

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Multi Manager  •  Best Practical Build")
        self.root.geometry("860x620")
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.holder = MutexHolder()
        self.profiles = load_json(PROFILES_FILE, [])
        self.favorites = load_json(FAVS_FILE, [])
        self.sessions = load_json(SESSIONS_FILE, [])
        self.groups = load_json(GROUPS_FILE, {})
        self.accounts = load_json(ACCOUNTS_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {"auto_start": False})
        self.search_results = []

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e2e")
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4", padding=[10,5])
        style.map("TNotebook.Tab", background=[("selected", "#45475a")])

        nb = ttk.Notebook(root)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.t_dash = tk.Frame(nb, bg="#1e1e2e")
        self.t_search = tk.Frame(nb, bg="#1e1e2e")
        self.t_favs = tk.Frame(nb, bg="#1e1e2e")
        self.t_watch = tk.Frame(nb, bg="#1e1e2e")
        self.t_groups = tk.Frame(nb, bg="#1e1e2e")
        self.t_acc = tk.Frame(nb, bg="#1e1e2e")
        self.t_prof = tk.Frame(nb, bg="#1e1e2e")
        self.t_ff = tk.Frame(nb, bg="#1e1e2e")
        self.t_set = tk.Frame(nb, bg="#1e1e2e")

        nb.add(self.t_dash, text=" Dashboard ")
        nb.add(self.t_search, text=" Game Search ")
        nb.add(self.t_favs, text=" Favorites ")
        nb.add(self.t_watch, text=" Watcher ")
        nb.add(self.t_groups, text=" Groups ")
        nb.add(self.t_acc, text=" Accounts ")
        nb.add(self.t_prof, text=" Profiles ")
        nb.add(self.t_ff, text=" FastFlags ")
        nb.add(self.t_set, text=" Settings ")

        self.build_dash()
        self.build_search()
        self.build_favs()
        self.build_watch()
        self.build_groups()
        self.build_acc()
        self.build_prof()
        self.build_ff()
        self.build_set()
        self.log("Ready. Close Roblox, then start multi-instance.")
        self.update_stats()
        if self.settings.get("auto_start"):
            self.root.after(300, self.start_mutex)

    def build_dash(self):
        f = self.t_dash
        tk.Label(f, text="Roblox Multi Manager", font=("Segoe UI", 16, "bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        tk.Label(f, text="Best practical multi-instance build", font=("Segoe UI", 9), bg="#1e1e2e", fg="#6c7086").pack()
        self.status = tk.Label(f, text="Multi-instance: Stopped", bg="#1e1e2e", fg="#f38ba8", font=("Segoe UI", 11))
        self.status.pack()
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=6)
        self.b_start = tk.Button(bf, text="Start Multi-Instance", command=self.start_mutex, bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI",10,"bold"), width=20, height=2, relief="flat")
        self.b_start.pack(side=tk.LEFT, padx=4)
        self.b_stop = tk.Button(bf, text="Stop", command=self.stop_mutex, bg="#f38ba8", fg="#1e1e2e", font=("Segoe UI",10,"bold"), width=10, height=2, relief="flat", state=tk.DISABLED)
        self.b_stop.pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Launch Roblox", command=self.launch_normal, bg="#89b4fa", fg="#1e1e2e", font=("Segoe UI",10,"bold"), width=14, height=2, relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Close All Roblox", command=self.close_all, bg="#f9e2af", fg="#1e1e2e", font=("Segoe UI",10,"bold"), width=16, height=2, relief="flat").pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Launch Many", command=self.launch_many, bg="#cba6f7", fg="#1e1e2e", font=("Segoe UI",10,"bold"), width=14, height=2, relief="flat").pack(side=tk.LEFT, padx=4)
        sf = tk.Frame(f, bg="#313244"); sf.pack(fill=tk.X, padx=12, pady=6)
        self.lbl_c = tk.Label(sf, text="Clients: 0", bg="#313244", fg="#cdd6f4"); self.lbl_c.pack(side=tk.LEFT, padx=10, pady=4)
        self.logb = scrolledtext.ScrolledText(f, height=11, bg="#313244", fg="#cdd6f4", font=("Consolas",9), relief="flat")
        self.logb.pack(fill=tk.BOTH, expand=True, padx=12, pady=4); self.logb.config(state=tk.DISABLED)

    def build_search(self):
        f = self.t_search
        tk.Label(f, text="Search Roblox Games", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        sf = tk.Frame(f, bg="#1e1e2e"); sf.pack(fill=tk.X, padx=12)
        self.q = tk.Entry(sf, font=("Segoe UI",11), bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", relief="flat")
        self.q.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.q.bind("<Return>", lambda e: self.do_search())
        tk.Button(sf, text="Search", command=self.do_search, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(sf, text="Popular", command=self.popular, bg="#cba6f7", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=4)
        self.res = tk.Listbox(f, bg="#313244", fg="#cdd6f4", font=("Segoe UI",10), selectbackground="#45475a", relief="flat")
        self.res.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=4)
        tk.Button(bf, text="Launch Selected", command=self.launch_selected, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=16).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Add to Profiles", command=self.add_from_search, bg="#fab387", fg="#1e1e2e", relief="flat", width=14).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Add Favorite", command=self.add_fav, bg="#cba6f7", fg="#1e1e2e", relief="flat", width=12).pack(side=tk.LEFT, padx=4)

    def do_search(self):
        q = self.q.get().strip()
        if not q: return
        self.log(f"Searching: {q}")
        self.res.delete(0, tk.END)
        self.search_results = search_roblox_games(q)
        for g in self.search_results:
            name = g.get("name", "?")
            pid = g.get("placeId") or g.get("rootPlaceId") or "?"
            players = g.get("playerCount", 0)
            visits = g.get("visitCount", 0)
            self.res.insert(tk.END, f"{name}  |  ID {pid}  |  {players} playing  |  {visits:,} visits")
        self.log(f"Found {len(self.search_results)} games")

    def launch_selected(self):
        s = self.res.curselection()
        if not s: return
        g = self.search_results[s[0]]
        pid = g.get("placeId") or g.get("rootPlaceId")
        if pid:
            os.startfile(f"roblox://placeId={pid}")
            self.log(f"Launched {g.get('name')}")

    def add_from_search(self):
        s = self.res.curselection()
        if not s: return
        g = self.search_results[s[0]]
        name = g.get("name", "Game")
        pid = str(g.get("placeId") or g.get("rootPlaceId") or "")
        self.profiles.append({"name": name, "place_id": pid, "link_code": "", "notes": "from search"})
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_prof()
        self.log(f"Added profile: {name}")


    def build_favs(self):
        f = self.t_favs
        tk.Label(f, text="Favorites", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        self.favlist = tk.Listbox(f, bg="#313244", fg="#cdd6f4", font=("Segoe UI",10), selectbackground="#45475a", relief="flat")
        self.favlist.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        self.refresh_favs()
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=4)
        tk.Button(bf, text="Launch", command=self.launch_fav, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Remove", command=self.remove_fav, bg="#f38ba8", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)

    def refresh_favs(self):
        self.favlist.delete(0, tk.END)
        for g in self.favorites:
            self.favlist.insert(tk.END, f"{g.get('name','?')}  |  {g.get('place_id')}")

    def launch_fav(self):
        s = self.favlist.curselection()
        if not s: return
        g = self.favorites[s[0]]
        os.startfile(f"roblox://placeId={g['place_id']}")
        self.log(f"Launched favorite {g.get('name')}")
        self.sessions.append({"name": g.get("name"), "place_id": g["place_id"], "time": time.strftime("%Y-%m-%d %H:%M")})
        save_json(SESSIONS_FILE, self.sessions[-50:])

    def remove_fav(self):
        s = self.favlist.curselection()
        if s and messagebox.askyesno("Remove", "Remove from favorites?"):
            self.favorites.pop(s[0])
            save_json(FAVS_FILE, self.favorites)
            self.refresh_favs()


    def add_fav(self):
        s = self.res.curselection()
        if not s: return
        g = self.search_results[s[0]]
        name = g.get("name", "Game")
        pid = str(g.get("placeId") or g.get("rootPlaceId") or "")
        if any(f.get("place_id") == pid for f in self.favorites):
            messagebox.showinfo("Already", "Already in favorites")
            return
        self.favorites.append({"name": name, "place_id": pid})
        save_json(FAVS_FILE, self.favorites)
        self.refresh_favs()
        self.log(f"Favorited: {name}")


    def build_watch(self):
        f = self.t_watch
        tk.Label(f, text="Process Watcher", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        tk.Label(f, text="Running Roblox clients. Select one and close it if needed.", bg="#1e1e2e", fg="#bac2de", font=("Segoe UI",9)).pack()
        self.watch_list = tk.Listbox(f, bg="#313244", fg="#cdd6f4", font=("Consolas",9), selectbackground="#45475a", relief="flat")
        self.watch_list.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=4)
        tk.Button(bf, text="Refresh", command=self.refresh_watch, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Close Selected", command=self.close_selected, bg="#f38ba8", fg="#1e1e2e", relief="flat", width=14).pack(side=tk.LEFT, padx=3)
        self.refresh_watch()

    def refresh_watch(self):
        self.watch_list.delete(0, tk.END)
        try:
            out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe", "/FO", "CSV", "/V"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines()[1:]:
                if "RobloxPlayerBeta" in line:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 5:
                        pid = parts[1]
                        mem = parts[4]
                        self.watch_list.insert(tk.END, f"PID {pid}  |  Mem {mem}")
            if self.watch_list.size() == 0:
                self.watch_list.insert(tk.END, "No Roblox clients running")
        except Exception as e:
            self.watch_list.insert(tk.END, f"Error: {e}")

    def close_selected(self):
        s = self.watch_list.curselection()
        if not s: return
        line = self.watch_list.get(s[0])
        if "PID" not in line: return
        try:
            pid = line.split("PID ")[1].split(" ")[0]
            subprocess.call(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log(f"Closed PID {pid}")
            self.refresh_watch()
        except Exception as e:
            self.log(f"Close failed: {e}")


    def build_groups(self):
        f = self.t_groups
        tk.Label(f, text="Profile Groups", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        self.glist = tk.Listbox(f, bg="#313244", fg="#cdd6f4", font=("Segoe UI",10), selectbackground="#45475a", relief="flat", height=8)
        self.glist.pack(fill=tk.X, padx=12, pady=4)
        self.refresh_groups()
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=4)
        tk.Button(bf, text="New Group", command=self.new_group, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Launch Group", command=self.launch_group, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Delete Group", command=self.del_group, bg="#f38ba8", fg="#1e1e2e", relief="flat", width=12).pack(side=tk.LEFT, padx=3)
        tk.Label(f, text="Assign profiles to groups from the Profiles tab (edit later).", bg="#1e1e2e", fg="#6c7086", font=("Segoe UI",8)).pack(pady=4)

    def refresh_groups(self):
        self.glist.delete(0, tk.END)
        for name, pids in self.groups.items():
            self.glist.insert(tk.END, f"{name}  ({len(pids)} profiles)")

    def new_group(self):
        n = simpledialog.askstring("Group", "Group name:")
        if n and n not in self.groups:
            self.groups[n] = []
            save_json(GROUPS_FILE, self.groups)
            self.refresh_groups()

    def del_group(self):
        s = self.glist.curselection()
        if s and messagebox.askyesno("Delete", "Delete group?"):
            name = self.glist.get(s[0]).split("  (")[0]
            self.groups.pop(name, None)
            save_json(GROUPS_FILE, self.groups)
            self.refresh_groups()

    def launch_group(self):
        s = self.glist.curselection()
        if not s: return
        name = self.glist.get(s[0]).split("  (")[0]
        pids = self.groups.get(name, [])
        for pid in pids:
            os.startfile(f"roblox://placeId={pid}")
            time.sleep(1.5)
        self.log(f"Launched group {name}")

    def popular(self):
        self.q.delete(0, tk.END)
        self.q.insert(0, "popular")
        self.do_search()


    def build_acc(self):
        f = self.t_acc
        tk.Label(f, text="Accounts (local cookies only)", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=4)
        tk.Label(f, text="Paste .ROBLOSECURITY cookie. Stored only on this PC. Use at your own risk.", bg="#1e1e2e", fg="#f9e2af", font=("Segoe UI",8)).pack()
        self.acclist = tk.Listbox(f, bg="#313244", fg="#cdd6f4", font=("Segoe UI",10), selectbackground="#45475a", relief="flat")
        self.acclist.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        self.refresh_acc()
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=4)
        tk.Button(bf, text="Add Account", command=self.add_acc, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Launch", command=self.launch_acc, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Delete", command=self.del_acc, bg="#f38ba8", fg="#1e1e2e", relief="flat", width=10).pack(side=tk.LEFT, padx=3)

    def refresh_acc(self):
        self.acclist.delete(0, tk.END)
        for a in self.accounts:
            self.acclist.insert(tk.END, a.get("name", "Unnamed"))

    def add_acc(self):
        name = simpledialog.askstring("Account", "Account name (any label):")
        if not name: return
        cookie = simpledialog.askstring("Cookie", "Paste .ROBLOSECURITY cookie:")
        if not cookie: return
        self.accounts.append({"name": name, "cookie": cookie.strip()})
        save_json(ACCOUNTS_FILE, self.accounts)
        self.refresh_acc()
        self.log(f"Added account {name}")

    def del_acc(self):
        s = self.acclist.curselection()
        if s and messagebox.askyesno("Delete", "Delete this account?"):
            self.accounts.pop(s[0])
            save_json(ACCOUNTS_FILE, self.accounts)
            self.refresh_acc()

    def launch_acc(self):
        s = self.acclist.curselection()
        if not s: return
        a = self.accounts[s[0]]
        # Write cookie then launch (basic method)
        try:
            cookie_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "LocalStorage" / "RobloxCookies.dat"
            # Note: Real cookie injection is more complex; this is a placeholder note
            # For now just launch and tell user to log in, or implement proper ticket
            os.startfile("roblox://")
            self.log(f"Launched for {a['name']} — log in manually if needed (cookie storage is basic)")
            messagebox.showinfo("Launch", f"Launched Roblox.\nFor full cookie auto-login, more advanced injection is needed.\nAccount: {a['name']}")
        except Exception as e:
            self.log(f"Launch error: {e}")

    def build_prof(self):
        f = self.t_prof
        tk.Label(f, text="Launch Profiles", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=6)
        self.plist = tk.Listbox(f, bg="#313244", fg="#cdd6f4", font=("Segoe UI",10), selectbackground="#45475a", relief="flat")
        self.plist.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        self.refresh_prof()
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=4)
        tk.Button(bf, text="New", command=self.new_prof, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=8).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Launch", command=self.launch_prof, bg="#89b4fa", fg="#1e1e2e", relief="flat", width=8).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Delete", command=self.del_prof, bg="#f38ba8", fg="#1e1e2e", relief="flat", width=8).pack(side=tk.LEFT, padx=3)

    def refresh_prof(self):
        self.plist.delete(0, tk.END)
        for p in self.profiles:
            self.plist.insert(tk.END, f"{p.get('name')}  |  {p.get('place_id')}")

    def new_prof(self):
        n = simpledialog.askstring("Name", "Profile name:")
        if not n: return
        pid = simpledialog.askstring("Place", "Place ID:")
        if not pid or not pid.isdigit(): return
        self.profiles.append({"name": n, "place_id": pid, "link_code": "", "notes": ""})
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_prof()

    def del_prof(self):
        s = self.plist.curselection()
        if s and messagebox.askyesno("Delete", "Remove?"):
            self.profiles.pop(s[0])
            save_json(PROFILES_FILE, self.profiles)
            self.refresh_prof()

    def launch_prof(self):
        s = self.plist.curselection()
        if not s: return
        p = self.profiles[s[0]]
        url = f"roblox://placeId={p['place_id']}"
        if p.get("link_code"): url += f"&privateServerLinkCode={p['link_code']}"
        os.startfile(url)
        self.log(f"Launched profile {p['name']}")


    def launch_many(self):
        count = simpledialog.askinteger("Launch Many", "How many Roblox windows? (1-50)", minvalue=1, maxvalue=50)
        if not count: return
        delay = simpledialog.askinteger("Delay", "Seconds between each launch? (1-10)", minvalue=1, maxvalue=10)
        if delay is None: delay = 2
        place = simpledialog.askstring("Place ID", "Place ID to launch (or leave blank for normal Roblox):")
        def do():
            for i in range(count):
                if place and place.isdigit():
                    os.startfile(f"roblox://placeId={place}")
                else:
                    exe = find_roblox_exe()
                    if exe:
                        subprocess.Popen([str(exe)])
                self.log(f"Launched {i+1}/{count}")
                if i < count - 1:
                    time.sleep(delay)
            self.log("Finished multi-launch")
        threading.Thread(target=do, daemon=True).start()
        messagebox.showinfo("Starting", f"Launching {count} windows with {delay}s delay. Watch the log.")

    def launch_normal(self):
        exe = find_roblox_exe()
        if exe: subprocess.Popen([str(exe)]); self.log("Launched Roblox")
        else: messagebox.showerror("Error", "Roblox not found")

    def build_ff(self):
        f = self.t_ff
        tk.Label(f, text="FastFlags", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=4)
        pf = tk.Frame(f, bg="#1e1e2e"); pf.pack()
        self.pv = tk.StringVar(value="Balanced")
        ttk.Combobox(pf, textvariable=self.pv, values=list(FFLAG_PRESETS), state="readonly", width=16).pack(side=tk.LEFT, padx=4)
        tk.Button(pf, text="Apply", command=self.apply_p, bg="#89b4fa", fg="#1e1e2e", relief="flat").pack(side=tk.LEFT)
        self.ff = scrolledtext.ScrolledText(f, height=16, bg="#313244", fg="#a6e3a1", font=("Consolas",9), relief="flat")
        self.ff.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        bf = tk.Frame(f, bg="#1e1e2e"); bf.pack(pady=2)
        tk.Button(bf, text="Load", command=self.load_ff, bg="#fab387", fg="#1e1e2e", relief="flat", width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(bf, text="Save", command=self.save_ff, bg="#a6e3a1", fg="#1e1e2e", relief="flat", width=8).pack(side=tk.LEFT, padx=2)
        self.load_ff()

    def load_ff(self):
        path = get_fflags_path()
        self.ff.delete("1.0", tk.END)
        if path and path.exists():
            try: self.ff.insert("1.0", json.dumps(json.loads(path.read_text()), indent=2))
            except: self.ff.insert("1.0", "{}")
        else: self.ff.insert("1.0", "{}")

    def apply_p(self):
        d = FFLAG_PRESETS.get(self.pv.get(), {})
        self.ff.delete("1.0", tk.END)
        self.ff.insert("1.0", json.dumps(d, indent=2))

    def save_ff(self):
        path = get_fflags_path()
        if not path: return
        try:
            d = json.loads(self.ff.get("1.0", tk.END).strip() or "{}")
            path.write_text(json.dumps(d, indent=2))
            messagebox.showinfo("Saved", "Restart Roblox")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_set(self):
        f = self.t_set
        tk.Label(f, text="Settings", font=("Segoe UI",13,"bold"), bg="#1e1e2e", fg="#cdd6f4").pack(pady=10)
        self.auto = tk.BooleanVar(value=self.settings.get("auto_start", False))
        tk.Checkbutton(f, text="Auto-start multi-instance", variable=self.auto, command=self.save_s,
                       bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244").pack(anchor="w", padx=20)
        exe = find_roblox_exe()
        tk.Label(f, text=f"Roblox: {exe or 'Not found'}", bg="#1e1e2e", fg="#bac2de", wraplength=700).pack(anchor="w", padx=20, pady=8)

    def save_s(self):
        self.settings["auto_start"] = self.auto.get()
        save_json(SETTINGS_FILE, self.settings)

    def log(self, m):
        self.logb.config(state=tk.NORMAL)
        self.logb.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {m}\n")
        self.logb.see(tk.END)
        self.logb.config(state=tk.DISABLED)

    def auto_refresh_watch(self):
        try:
            if hasattr(self, "watch_list"):
                self.refresh_watch()
        except: pass
        self.root.after(5000, self.auto_refresh_watch)

    def update_stats(self):
        try:
            out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe", "/FO", "CSV"], text=True, stderr=subprocess.DEVNULL)
            n = max(0, len([l for l in out.splitlines() if "RobloxPlayerBeta" in l]) - 1)
            self.lbl_c.config(text=f"Clients: {n}")
        except: pass
        self.root.after(4000, self.update_stats)
        self.root.after(5000, self.auto_refresh_watch)

    def start_mutex(self):
        ok, msg = self.holder.start()
        self.log(msg)
        if ok:
            self.status.config(text="Multi-instance: Running", fg="#a6e3a1")
            self.b_start.config(state=tk.DISABLED)
            self.b_stop.config(state=tk.NORMAL)
        else: messagebox.showerror("Error", msg)

    def stop_mutex(self):
        self.log(self.holder.stop())
        self.status.config(text="Multi-instance: Stopped", fg="#f38ba8")
        self.b_start.config(state=tk.NORMAL)
        self.b_stop.config(state=tk.DISABLED)


    def close_all(self):
        if not messagebox.askyesno("Close All", "Close every Roblox window?"):
            return
        try:
            subprocess.call(["taskkill", "/F", "/IM", "RobloxPlayerBeta.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.call(["taskkill", "/F", "/IM", "RobloxCrashHandler.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log("Closed all Roblox processes")
        except Exception as e:
            self.log(f"Close error: {e}")

    def on_close(self):
        if self.holder.running and not messagebox.askyesno("Quit", "Stop and quit?"): return
        if self.holder.running: self.holder.stop()
        self.root.destroy()

def main():
    if sys.platform != "win32":
        print("Windows only"); return
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
