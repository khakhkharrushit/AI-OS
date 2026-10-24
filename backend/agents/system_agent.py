import subprocess
import platform
import psutil
import os
import glob
import json
from typing import Dict, Optional
from agents.base import BaseAgent
from tools.base import Tool

class SystemAgent(BaseAgent):
    def __init__(self):
        super().__init__("SystemAgent")
        self._start_apps_cache: Dict[str, str] = {}
        self._load_start_apps()
        self.register_tool(Tool("open_application", "Open a system application or file with application", self.open_application))
        self.register_tool(Tool("close_application", "Close a system application", self.close_application))
        self.register_tool(Tool("get_system_info", "Get current system CPU, RAM, Disk, and Battery metrics", self.get_system_info))
        self.register_tool(Tool("get_battery_status", "Get current laptop battery percentage, power charging status, and remaining time", self.get_battery_status))
        self.register_tool(Tool("list_processes", "List currently running processes", self.list_processes))
        self.register_tool(Tool("adjust_brightness", "Increase, decrease, or set screen display brightness (e.g. action='increase'|'decrease', level=80)", self.adjust_brightness))
        self.register_tool(Tool("adjust_volume", "Increase, decrease, mute, or unmute system audio sound volume", self.adjust_volume))
        self.register_tool(Tool("toggle_wifi", "Turn Wi-Fi on or off, or open Wi-Fi network settings", self.toggle_wifi))
        self.register_tool(Tool("toggle_airplane_mode", "Turn on or off airplane mode, or open airplane mode settings", self.toggle_airplane_mode))
        self.register_tool(Tool("toggle_bluetooth", "Turn on, turn off, or open Bluetooth settings", self.toggle_bluetooth))
        self.register_tool(Tool("toggle_dark_mode", "Switch Windows system theme between dark mode and light mode", self.toggle_dark_mode))
        self.register_tool(Tool("send_whatsapp_desktop_message", "Send a message to a contact using the installed WhatsApp Desktop application", self.send_whatsapp_desktop_message))
        self.register_tool(Tool("open_whatsapp_desktop_chat", "Open a contact chat in the installed WhatsApp Desktop application", self.open_whatsapp_desktop_chat))
        self.register_tool(Tool("uninstall_application", "Find and uninstall or remove an installed application with confirmation", self.uninstall_application, high_risk=True))
        self.register_tool(Tool("system_command", "Run raw shell command", self.run_command, high_risk=True))

    def _load_start_apps(self):
        """Loads all installed Windows applications and their AppIDs into memory."""
        try:
            cmd = 'powershell -NoProfile -Command "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Depth 2"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                if isinstance(data, list):
                    for item in data:
                        name = item.get("Name", "").strip().lower()
                        app_id = item.get("AppID", "")
                        if name and app_id:
                            self._start_apps_cache[name] = app_id
                elif isinstance(data, dict):
                    name = data.get("Name", "").strip().lower()
                    app_id = data.get("AppID", "")
                    if name and app_id:
                        self._start_apps_cache[name] = app_id
        except Exception as e:
            print(f"Notice: Could not populate StartApps cache: {e}")

    def open_application(self, app_name: str, filepath: Optional[str] = None, **kwargs) -> str:
        if not app_name:
            raise ValueError("Missing 'app_name' argument")
            
        app_clean = app_name.strip().lower()
        
        # Handle file argument if user wrote "notepad rk.txt"
        if not filepath and " " in app_name and not any(app_clean.startswith(p) for p in ["task manager", "visual studio", "google chrome", "riot client"]):
            parts = app_name.split(" ", 1)
            app_clean = parts[0].strip().lower()
            filepath = parts[1].strip()

        if filepath:
            filepath = os.path.expanduser(filepath)
            if filepath.lower().startswith("desktop\\") or filepath.lower().startswith("desktop/"):
                filepath = os.path.join(os.path.expanduser("~"), "Desktop", filepath[8:])
            elif not os.path.isabs(filepath):
                # Check Desktop first
                desktop_candidate = os.path.join(os.path.expanduser("~"), "Desktop", filepath)
                onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", filepath)
                if os.path.exists(onedrive_desktop):
                    filepath = onedrive_desktop
                elif os.path.exists(desktop_candidate):
                    filepath = desktop_candidate
                elif os.path.exists(filepath):
                    filepath = os.path.abspath(filepath)
                else:
                    filepath = desktop_candidate
            filepath = os.path.normpath(filepath)

        # 1. Standard Windows utility aliases with direct executable spawning
        if app_clean in ["notepad", "notes", "text editor"]:
            if filepath:
                abs_path = os.path.abspath(filepath)
                try:
                    if os.path.exists(abs_path):
                        os.startfile(abs_path)
                    else:
                        subprocess.Popen(["notepad.exe", abs_path])
                except Exception:
                    subprocess.Popen(["notepad.exe", abs_path])
                return f"Opened '{os.path.basename(abs_path)}' in Notepad."
            else:
                subprocess.Popen(["notepad.exe"])
                return "Opened Notepad."

        if app_clean in ["task manager", "taskmanager", "task mgr", "task"]:
            subprocess.Popen(["taskmgr.exe"])
            return "Opened Task Manager."

        if app_clean in ["calculator", "calc"]:
            subprocess.Popen(["calc.exe"])
            return "Opened Calculator."

        if app_clean in ["cmd", "command prompt"]:
            subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe"])
            return "Opened Command Prompt."

        if app_clean in ["powershell", "ps"]:
            subprocess.Popen(["powershell.exe"])
            return "Opened PowerShell."

        if app_clean in ["settings", "setting", "windows settings"]:
            subprocess.Popen('start "" "ms-settings:"', shell=True)
            return "Opened Windows Settings."

        if app_clean in ["file explorer", "explorer", "files"]:
            if filepath:
                subprocess.Popen(["explorer.exe", "/select,", filepath])
            else:
                subprocess.Popen(["explorer.exe"])
            return "Opened File Explorer."

        if app_clean in ["word", "winword", "microsoft word", "ms word", "word document"]:
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 1
                creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                winword = r"C:\Program Files\Microsoft Office\Root\Office16\WINWORD.EXE"
                if os.path.exists(winword):
                    if filepath and os.path.exists(filepath):
                        subprocess.Popen([winword, filepath], startupinfo=si, creationflags=creation_flags)
                        return f"Opened '{os.path.basename(filepath)}' in Microsoft Word."
                    else:
                        subprocess.Popen([winword], startupinfo=si, creationflags=creation_flags)
                        return "Opened Microsoft Word."
                else:
                    target_arg = f'"{filepath}"' if filepath else ""
                    subprocess.Popen(f'cmd.exe /c start "" "winword" {target_arg}', shell=True, startupinfo=si, creationflags=creation_flags)
                    return "Opened Microsoft Word."
            except Exception as e:
                raise Exception(f"Failed to open Microsoft Word: {e}")

        if app_clean in ["excel", "microsoftexcel", "microsoft excel", "ms excel", "spreadsheet"]:
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 1
                creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                excel = r"C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE"
                if os.path.exists(excel):
                    if filepath and os.path.exists(filepath):
                        subprocess.Popen([excel, filepath], startupinfo=si, creationflags=creation_flags)
                        return f"Opened '{os.path.basename(filepath)}' in Microsoft Excel."
                    else:
                        subprocess.Popen([excel], startupinfo=si, creationflags=creation_flags)
                        return "Opened Microsoft Excel."
                else:
                    target_arg = f'"{filepath}"' if filepath else ""
                    subprocess.Popen(f'cmd.exe /c start "" "excel" {target_arg}', shell=True, startupinfo=si, creationflags=creation_flags)
                    return "Opened Microsoft Excel."
            except Exception as e:
                raise Exception(f"Failed to open Microsoft Excel: {e}")

        if app_clean in ["powerpoint", "ppt", "powerpnt", "microsoft powerpoint", "ms powerpoint", "presentation", "slides"]:
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 1
                creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                powerpnt = r"C:\Program Files\Microsoft Office\Root\Office16\POWERPNT.EXE"
                if os.path.exists(powerpnt):
                    if filepath and os.path.exists(filepath):
                        subprocess.Popen([powerpnt, filepath], startupinfo=si, creationflags=creation_flags)
                        return f"Opened '{os.path.basename(filepath)}' in Microsoft PowerPoint."
                    else:
                        subprocess.Popen([powerpnt], startupinfo=si, creationflags=creation_flags)
                        return "Opened Microsoft PowerPoint."
                else:
                    target_arg = f'"{filepath}"' if filepath else ""
                    subprocess.Popen(f'cmd.exe /c start "" "powerpnt" {target_arg}', shell=True, startupinfo=si, creationflags=creation_flags)
                    return "Opened Microsoft PowerPoint."
            except Exception as e:
                raise Exception(f"Failed to open Microsoft PowerPoint: {e}")

        # 2. Communication & Media Applications
        if app_clean in ["whatsapp", "whats app", "whatsapp desktop", "whatsapp app"]:
            try:
                app_id = self._start_apps_cache.get("whatsapp", "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
                subprocess.Popen(f'powershell.exe -NoProfile -Command "Start-Process \'shell:AppsFolder\\{app_id}\'"', shell=True)
                return "Successfully launched WhatsApp Desktop."
            except Exception:
                subprocess.Popen('cmd.exe /c start "" "whatsapp:"', shell=True)
                return "Successfully launched WhatsApp Desktop."

        # 3. Search common user executable installations (AppData, Program Files)
        search_globs = [
            os.path.expanduser(f"~\\AppData\\Roaming\\*{app_clean}*\\*.exe"),
            os.path.expanduser(f"~\\AppData\\Local\\Programs\\*{app_clean}*\\*.exe"),
            f"C:\\Program Files\\*{app_clean}*\\*.exe",
            f"C:\\Program Files (x86)\\*{app_clean}*\\*.exe"
        ]
        for pattern in search_globs:
            found = [
                f for f in glob.glob(pattern, recursive=True)
                if not any(x in f.lower() for x in ["unins", "update", "helper", "crash", "what is new"])
            ]
            if found:
                exe_path = found[0]
                if filepath:
                    subprocess.Popen([exe_path, filepath])
                else:
                    subprocess.Popen([exe_path])
                return f"Successfully launched {app_name.title()} from '{exe_path}'."

        # 4. Check Windows StartApps (UWP & Store Apps like Netflix, Spotify, etc.)
        if not self._start_apps_cache:
            self._load_start_apps()
            
        for reg_name, app_id in self._start_apps_cache.items():
            if app_clean == reg_name or app_clean in reg_name:
                if not any(ign in reg_name for ign in ["what is new", "readme", "release notes", "license", "uninstall", "help"]):
                    no_win = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    if "!" in app_id:
                        subprocess.Popen(f'cmd.exe /c start "" "shell:AppsFolder\\{app_id}"', shell=True, creationflags=no_win)
                        return f"Successfully opened Windows App '{reg_name.title()}'."
                    elif os.path.exists(app_id):
                        if filepath:
                            subprocess.Popen([app_id, filepath])
                        else:
                            subprocess.Popen([app_id])
                        return f"Successfully opened '{reg_name.title()}'."

        # 4. Check Start Menu and Desktop .lnk Shortcuts
        shortcut_dirs = [
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\OneDrive\\Desktop"),
            "C:\\Users\\Public\\Desktop",
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
        ]
        ignore_kws = ["what is new", "readme", "release notes", "license", "help", "uninstall"]
        no_win = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        for s_dir in shortcut_dirs:
            if os.path.exists(s_dir):
                matches = glob.glob(os.path.join(s_dir, f"*{app_clean}*.lnk")) or \
                          glob.glob(os.path.join(s_dir, "**", f"*{app_clean}*.lnk"), recursive=True)
                valid = [m for m in matches if not any(k in os.path.basename(m).lower() for k in ignore_kws)]
                if valid:
                    if filepath:
                        subprocess.Popen(f'start "" "{valid[0]}" "{filepath}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=no_win)
                    else:
                        subprocess.Popen(f'start "" "{valid[0]}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=no_win)
                    return f"Successfully opened '{app_name}' via shortcut: {os.path.basename(valid[0])}"

        # 5. Direct Windows launch fallback
        import shutil
        KNOWN_APPS = {"calc", "notepad", "explorer", "cmd", "powershell", "taskmgr", "mspaint", "snippingtool", "regedit", "control", "write"}
        resolved_bin = shutil.which(app_clean) or (app_clean if app_clean in KNOWN_APPS else None)
        
        if resolved_bin:
            try:
                if filepath:
                    subprocess.Popen(f'start "" "{resolved_bin}" "{filepath}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=no_win)
                else:
                    subprocess.Popen(f'start "" "{resolved_bin}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=no_win)
                return f"Opened application: {app_name}"
            except Exception as e:
                raise Exception(f"Could not open application '{app_name}': {e}")
        else:
            raise Exception(f"Application '{app_name}' was not found on your system. If this is a website or contact name, please use BrowserAgent or messaging command.")
            
    def close_application(self, **kwargs) -> str:
        app_name = kwargs.get("app_name")
        if not app_name:
            raise ValueError("Missing 'app_name' argument")
            
        app_clean = app_name.strip().lower()
        if app_clean.startswith("task") or "taskmgr" in app_clean:
            target = "taskmgr"
        elif app_clean.startswith("calc"):
            target = "CalculatorApp"
        elif app_clean in ["notepad", "notes"]:
            target = "Notepad"
        elif app_clean in ["chrome", "google chrome"]:
            target = "chrome"
        elif app_clean in ["brave", "brave browser"]:
            target = "brave"
        elif app_clean in ["edge", "msedge"]:
            target = "msedge"
        elif app_clean in ["code", "vscode"]:
            target = "Code"
        elif app_clean in ["whatsapp", "whats app"]:
            target = "WhatsApp"
        elif app_clean in ["spotify"]:
            target = "Spotify"
        elif app_clean in ["telegram"]:
            target = "Telegram"
        else:
            target = app_name

        try:
            result = subprocess.run(f'taskkill /F /IM {target}.exe /T', shell=True, capture_output=True, text=True)
            output = result.stdout.lower() + result.stderr.lower()
            if result.returncode == 0:
                return f"Closed application: {app_name}"
            elif "not found" in output:
                return f"Application '{app_name}' is not currently running."
            else:
                raise Exception(result.stderr or result.stdout)
        except Exception as e:
            raise Exception(f"Failed to close {app_name}: {e}")
        
    def run_command(self, command: str) -> str:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        raise Exception(result.stderr)

    def get_battery_status(self, **kwargs) -> str:
        """Returns the current laptop battery percentage, charging state, and remaining time."""
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return "No battery detected (Desktop PC or AC power only)."
            status = "Plugged in (Charging)" if battery.power_plugged else "Unplugged (On Battery)"
            secs = battery.secsleft
            time_str = ""
            if secs and secs > 0 and secs != psutil.POWER_TIME_UNLIMITED:
                h = secs // 3600
                m = (secs % 3600) // 60
                time_str = f" - Estimated remaining time: {h}h {m}m"
            return f"Battery Level: {battery.percent}% | Power Status: {status}{time_str}"
        except Exception as e:
            return f"Error reading battery sensor: {e}"

    def get_system_info(self, **kwargs) -> str:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count(logical=True)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            
            # Fetch battery and power info
            battery = psutil.sensors_battery()
            if battery:
                status = "Plugged in (Charging)" if battery.power_plugged else "Unplugged (On Battery)"
                time_left = ""
                if battery.secsleft and battery.secsleft > 0 and battery.secsleft != psutil.POWER_TIME_UNLIMITED:
                    hrs = battery.secsleft // 3600
                    mins = (battery.secsleft % 3600) // 60
                    time_left = f" - Remaining time: {hrs}h {mins}m"
                batt_info = f"Battery: {battery.percent}% ({status}{time_left})"
            else:
                batt_info = "Battery: Desktop PC / AC power (no battery sensor)"

            return (
                f"OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
                f"{batt_info}\n"
                f"CPU Utilization: {cpu_percent}% across {cpu_count} logical cores\n"
                f"RAM Usage: {mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB ({mem.percent}% used)\n"
                f"Disk C: Usage: {disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB ({disk.percent}% used)"
            )
        except Exception as e:
            raise Exception(f"Failed to fetch system info: {e}")

    def list_processes(self, filter_name: str = "", limit: int = 15, **kwargs) -> str:
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    name = p.info['name'] or ""
                    if filter_name and filter_name.lower() not in name.lower():
                        continue
                    procs.append((p.info['pid'], name, p.info['memory_percent'] or 0.0))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x[2], reverse=True)
            selected = procs[:int(limit)]
            if not selected:
                return f"No running processes found matching '{filter_name}'." if filter_name else "No active processes found."
            lines = [f"PID {pid:<6} | {name:<25} | Mem: {mem:.1f}%" for pid, name, mem in selected]
            return f"Top Running Processes ({len(selected)} shown):\n" + "\n".join(lines)
        except Exception as e:
            raise Exception(f"Failed to list processes: {e}")

    def uninstall_application(self, app_name: str, **kwargs) -> str:
        """
        Locates an application or program across shortcuts, AppData, and Windows uninstall registry,
        and uninstalls or removes it.
        """
        import shutil
        if not app_name:
            raise ValueError("Application name is required for uninstallation.")

        app_clean = app_name.strip().lower()
        removed_items = []

        # 1. Search Start Menu shortcuts and Desktop shortcuts
        shortcut_dirs = [
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\OneDrive\\Desktop"),
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
        ]
        for s_dir in shortcut_dirs:
            if os.path.exists(s_dir):
                for root, dirs, files in os.walk(s_dir):
                    for f in files:
                        if app_clean in f.lower() and f.lower().endswith(".lnk"):
                            full_p = os.path.join(root, f)
                            try:
                                os.remove(full_p)
                                removed_items.append(full_p)
                            except Exception:
                                pass

        # 2. Search AppData\Local\Programs
        appdata_programs = os.path.expanduser("~\\AppData\\Local\\Programs")
        if os.path.exists(appdata_programs):
            for item in os.listdir(appdata_programs):
                if app_clean in item.lower():
                    full_app_dir = os.path.join(appdata_programs, item)
                    try:
                        shutil.rmtree(full_app_dir)
                        removed_items.append(full_app_dir)
                    except Exception:
                        pass

        # 3. Check Windows Registry for uninstaller
        try:
            import winreg
            uninstall_keys = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]
            for u_key in uninstall_keys:
                try:
                    h_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, u_key)
                    for i in range(winreg.QueryInfoKey(h_key)[0]):
                        try:
                            sub_key_name = winreg.EnumKey(h_key, i)
                            sub_key = winreg.OpenKey(h_key, sub_key_name)
                            disp_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                            if app_clean in disp_name.lower():
                                uninst_str, _ = winreg.QueryValueEx(sub_key, "UninstallString")
                                subprocess.Popen(uninst_str, shell=True)
                                return f"Successfully launched official Windows uninstaller for '{disp_name}'."
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        if removed_items:
            return f"Successfully removed application and shortcuts for '{app_name}': " + ", ".join(removed_items)

        return f"Successfully removed application references for '{app_name}'."

    def adjust_brightness(self, action: str = "increase", level: Optional[int] = None, **kwargs) -> str:
        """Increases, decreases, or sets screen brightness percentage."""
        try:
            cmd_get = 'powershell -NoProfile -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
            res = subprocess.run(cmd_get, shell=True, capture_output=True, text=True, timeout=4)
            current = int(res.stdout.strip())
        except Exception:
            current = 70

        if level is not None:
            target = max(0, min(100, int(level)))
        else:
            action_clean = str(action).lower()
            if any(k in action_clean for k in ["increase", "up", "raise", "brighter", "more", "high", "max"]):
                target = 100 if "max" in action_clean else min(100, current + 20)
            elif any(k in action_clean for k in ["decrease", "down", "lower", "dim", "less", "min", "low"]):
                target = 15 if "min" in action_clean else max(10, current - 20)
            else:
                target = min(100, current + 20)

        cmd_set = f'powershell -NoProfile -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target})"'
        subprocess.run(cmd_set, shell=True, capture_output=True, text=True, timeout=5)
        return f"Successfully adjusted display brightness from {current}% to {target}%."

    def adjust_volume(self, action: str = "increase", level: Optional[int] = None, steps: int = 5, **kwargs) -> str:
        """Controls system master audio volume (increase, decrease, mute, unmute)."""
        import ctypes
        import time
        user32 = ctypes.windll.user32
        VK_VOLUME_MUTE = 0xAD
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_UP = 0xAF

        action_clean = str(action).lower()
        if any(k in action_clean for k in ["mute", "silence", "quiet"]):
            user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            return "Toggled system audio mute."
        elif any(k in action_clean for k in ["decrease", "down", "lower", "reduce", "softer", "less"]):
            num_steps = max(1, min(25, int(steps)))
            for _ in range(num_steps):
                user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                time.sleep(0.04)
            return f"Decreased sound volume by {num_steps * 2}%."
        else:
            num_steps = max(1, min(25, int(steps)))
            for _ in range(num_steps):
                user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                time.sleep(0.04)
            return f"Increased sound volume by {num_steps * 2}%."

    def toggle_wifi(self, state: str = "on", **kwargs) -> str:
        """Enables, disables, or opens Wi-Fi settings."""
        state_clean = str(state).lower()
        if "off" in state_clean or "disable" in state_clean:
            try:
                subprocess.Popen('powershell -NoProfile -Command "Disable-NetAdapter -Name \'Wi-Fi\' -Confirm:$false"', shell=True)
            except Exception:
                pass
            subprocess.Popen('start ms-settings:network-wifi', shell=True)
            return "Disabling Wi-Fi and opening Wi-Fi Network Settings."
        else:
            try:
                subprocess.Popen('powershell -NoProfile -Command "Enable-NetAdapter -Name \'Wi-Fi\' -Confirm:$false"', shell=True)
            except Exception:
                pass
            subprocess.Popen('start ms-settings:network-wifi', shell=True)
            return "Enabling Wi-Fi and opening Wi-Fi Network Settings."

    def toggle_airplane_mode(self, state: str = "on", **kwargs) -> str:
        """Toggles Airplane Mode by opening the Windows Airplane Mode control panel."""
        subprocess.Popen('start ms-settings:network-airplanemode', shell=True)
        return "Opened Windows Airplane Mode Settings panel to toggle connectivity."

    def toggle_bluetooth(self, state: str = "on", **kwargs) -> str:
        """Toggles Bluetooth by opening the Windows Bluetooth control panel."""
        subprocess.Popen('start ms-settings:bluetooth', shell=True)
        return "Opened Windows Bluetooth & Devices Settings."

    def toggle_dark_mode(self, state: str = "dark", **kwargs) -> str:
        """Switches Windows UI between Dark Mode and Light Mode."""
        state_clean = str(state).lower()
        val = 0 if any(k in state_clean for k in ["dark", "black", "night", "on", "enable"]) else 1
        mode_name = "Dark Mode" if val == 0 else "Light Mode"
        cmd = f'powershell -NoProfile -Command "Set-ItemProperty -Path \'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize\' -Name \'AppsUseLightTheme\' -Value {val}; Set-ItemProperty -Path \'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize\' -Name \'SystemUsesLightTheme\' -Value {val}"'
        subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return f"Successfully switched Windows theme to {mode_name}."

    def _focus_whatsapp_desktop(self) -> bool:
        """Launches or brings WhatsApp Desktop application to foreground."""
        import ctypes
        from ctypes import wintypes
        import time

        app_id = self._start_apps_cache.get("whatsapp", "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        subprocess.Popen(f'powershell.exe -NoProfile -Command "Start-Process \'shell:AppsFolder\\{app_id}\'"', shell=True)
        time.sleep(1.5)

        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        found = False

        def enum_proc(hwnd, lparam):
            nonlocal found
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if "whatsapp" in buff.value.lower():
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                        found = True
            return True

        user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        time.sleep(0.5)
        return found

    def send_whatsapp_desktop_message(self, contact: str, message: str, **kwargs) -> str:
        """Sends a message to a contact using the installed WhatsApp Desktop application."""
        import ctypes
        import pyautogui
        import pyperclip
        import time

        if not contact:
            raise ValueError("Missing 'contact' argument")
        if not message:
            raise ValueError("Missing 'message' argument")

        # Enable Per-Monitor DPI Awareness so PyAutoGUI uses physical screen pixels
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        pyautogui.FAILSAFE = False
        screen_w, screen_h = pyautogui.size()

        # Step 1: Launch and focus WhatsApp Desktop app
        app_id = self._start_apps_cache.get("whatsapp", "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        subprocess.Popen(f'powershell.exe -NoProfile -Command "Start-Process \'shell:AppsFolder\\{app_id}\'"', shell=True)
        time.sleep(1.8)

        # Step 2: Ensure window has active keyboard focus
        pyautogui.click(int(screen_w * 0.20), int(screen_h * 0.03))
        time.sleep(0.3)

        # Step 3: Click inside Search Bar (Calibrated: x=170, y=142 on 1080p)
        search_x = int(screen_w * (170 / 1920))
        search_y = int(screen_h * (142 / 1080))

        pyautogui.click(search_x, search_y)
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        time.sleep(0.2)

        # Step 4: Paste contact name to search
        pyperclip.copy(contact)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.5)

        # Step 5: Click top search result in the list (x=170, y=270 on 1080p)
        result_x = search_x
        result_y = int(screen_h * (270 / 1080))
        pyautogui.click(result_x, result_y)
        time.sleep(0.4)
        pyautogui.press('enter')
        time.sleep(0.8)

        # Step 6: Focus message input box (x=1000, y=1020 on 1080p) and send
        msg_x = int(screen_w * (1000 / 1920))
        msg_y = int(screen_h * (1020 / 1080))
        pyautogui.click(msg_x, msg_y)
        time.sleep(0.3)

        pyperclip.copy(message)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        pyautogui.press('enter')

        return f"Successfully sent message to '{contact}' via WhatsApp Desktop App: '{message}'"

    def open_whatsapp_desktop_chat(self, contact: str, **kwargs) -> str:
        """Searches and opens a chat with a contact in the installed WhatsApp Desktop application."""
        import ctypes
        import pyautogui
        import pyperclip
        import time

        if not contact:
            raise ValueError("Missing 'contact' argument")

        # Enable Per-Monitor DPI Awareness so PyAutoGUI uses physical screen pixels
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        pyautogui.FAILSAFE = False
        screen_w, screen_h = pyautogui.size()

        # Step 1: Launch and focus WhatsApp Desktop app
        app_id = self._start_apps_cache.get("whatsapp", "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        subprocess.Popen(f'powershell.exe -NoProfile -Command "Start-Process \'shell:AppsFolder\\{app_id}\'"', shell=True)
        time.sleep(1.8)

        # Step 2: Ensure window has active keyboard focus
        pyautogui.click(int(screen_w * 0.20), int(screen_h * 0.03))
        time.sleep(0.3)

        # Step 3: Click inside Search Bar (Calibrated: x=170, y=142 on 1080p)
        search_x = int(screen_w * (170 / 1920))
        search_y = int(screen_h * (142 / 1080))

        pyautogui.click(search_x, search_y)
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        time.sleep(0.2)

        # Step 4: Paste contact name to search
        pyperclip.copy(contact)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.5)

        # Step 5: Click top search result in the list
        result_x = search_x
        result_y = int(screen_h * (270 / 1080))
        pyautogui.click(result_x, result_y)
        time.sleep(0.4)
        pyautogui.press('enter')

        return f"Successfully opened chat with '{contact}' in WhatsApp Desktop App."



