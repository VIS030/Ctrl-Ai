"""
CTRL.AI — Python Agent Backend
WebSocket server that executes real system commands and streams results to the frontend.

Requirements:
    pip install websockets psutil pillow pyautogui

Run:
    python server.py
"""

import asyncio
import websockets
import json
import subprocess
import platform
import os
import sys
import time
import base64
import socket
import shutil
import signal
import threading
from datetime import datetime
from io import BytesIO

import psutil

# Optional imports — graceful fallback
try:
    import pyautogui
    HAS_GUI = True
except Exception:
    HAS_GUI = False

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except Exception:
    HAS_PIL = False


# ─── Config ───────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 9000
AGENT_VERSION = "2.4.1"
AGENT_ID = f"AGENT-{socket.gethostname()[:6].upper()}"
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

START_TIME = time.time()
connected_clients: set = set()
command_history: list = []


# ─── Helpers ──────────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%H:%M:%S")


def make_msg(type_: str, **kwargs) -> str:
    return json.dumps({"type": type_, "ts": ts(), **kwargs})


def run_shell(cmd: str, timeout: int = 10) -> dict:
    """Run a shell command and return stdout/stderr."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Command timed out after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


# ─── System Info ──────────────────────────────────────────────────────────────
def get_sysinfo() -> dict:
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    boot_time = psutil.boot_time()
    uptime_secs = int(time.time() - boot_time)
    uh = uptime_secs // 3600
    um = (uptime_secs % 3600) // 60
    us = uptime_secs % 60

    # IP
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"

    # Public IP (fast local guess)
    public_ip = "N/A"
    try:
        _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _sock.connect(("8.8.8.8", 80))
        public_ip = _sock.getsockname()[0]
        _sock.close()
    except Exception:
        pass

    return {
        "os": f"{platform.system()} {platform.release()}",
        "hostname": socket.gethostname(),
        "arch": platform.machine(),
        "cpu_brand": platform.processor() or "Unknown CPU",
        "cpu_percent": cpu,
        "cpu_count": psutil.cpu_count(),
        "ram_total": ram.total,
        "ram_used": ram.used,
        "ram_percent": ram.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "net_sent": net.bytes_sent,
        "net_recv": net.bytes_recv,
        "uptime": f"{uh:02d}:{um:02d}:{us:02d}",
        "local_ip": local_ip,
        "public_ip": public_ip,
        "username": os.getenv("USERNAME") or os.getenv("USER") or "unknown",
        "python": sys.version.split()[0],
        "agent_id": AGENT_ID,
        "agent_version": AGENT_VERSION,
        "platform": platform.system(),
    }


def get_processes() -> list:
    procs = []
    try:
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
            try:
                mem = p.info["memory_info"]
                procs.append({
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "cpu": round(p.info["cpu_percent"] or 0, 1),
                    "mem": round((mem.rss if mem else 0) / 1024 / 1024, 1),
                    "status": p.info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        return [{"error": str(e)}]
    procs.sort(key=lambda x: x.get("mem", 0), reverse=True)
    return procs[:50]


def get_network_info() -> dict:
    net = psutil.net_io_counters()
    addrs = psutil.net_if_addrs()
    info = {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "interfaces": {}
    }
    for iface, addrs_list in addrs.items():
        info["interfaces"][iface] = [
            {"family": str(a.family), "address": a.address, "netmask": a.netmask}
            for a in addrs_list
        ]
    return info


def get_files(path: str = None) -> dict:
    if path is None:
        path = os.path.expanduser("~")
    try:
        entries = []
        with os.scandir(path) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size if not entry.is_dir() else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "path": entry.path,
                    })
                except Exception:
                    pass
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"path": path, "entries": entries, "error": None}
    except PermissionError:
        return {"path": path, "entries": [], "error": "Permission denied"}
    except Exception as e:
        return {"path": path, "entries": [], "error": str(e)}


def take_screenshot() -> str | None:
    """Take a screenshot and return base64 JPEG."""
    if HAS_PIL:
        try:
            img = ImageGrab.grab()
            buf = BytesIO()
            img = img.resize((1280, int(img.height * 1280 / img.width)), Image.LANCZOS)
            img.save(buf, format="JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            pass
    if HAS_GUI:
        try:
            img = pyautogui.screenshot()
            buf = BytesIO()
            img = img.resize((1280, int(img.height * 1280 / img.width)))
            img.save(buf, format="JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            pass
    return None


def kill_process(pid: int) -> dict:
    try:
        p = psutil.Process(pid)
        p.terminate()
        return {"ok": True, "msg": f"Process {pid} ({p.name()}) terminated."}
    except psutil.NoSuchProcess:
        return {"ok": False, "msg": f"No process with PID {pid}"}
    except psutil.AccessDenied:
        return {"ok": False, "msg": f"Access denied to kill PID {pid}"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def get_clipboard() -> str:
    try:
        if IS_WINDOWS:
            r = run_shell("powershell -command Get-Clipboard")
            return r["stdout"] or "(empty)"
        elif IS_MAC:
            r = run_shell("pbpaste")
            return r["stdout"] or "(empty)"
        else:
            r = run_shell("xclip -selection clipboard -o")
            if r["returncode"] == 0:
                return r["stdout"] or "(empty)"
            r = run_shell("xsel --clipboard --output")
            return r["stdout"] or "(empty)"
    except Exception as e:
        return f"Error: {e}"


# ─── Command Dispatcher ───────────────────────────────────────────────────────
async def handle_command(ws, data: dict):
    cmd = data.get("cmd", "").strip()
    args = data.get("args", {})
    command_history.append({"cmd": cmd, "ts": ts()})

    async def send(type_, **kwargs):
        try:
            await ws.send(make_msg(type_, **kwargs))
        except Exception:
            pass

    # ── SHELL PASSTHROUGH ──────────────────────────────────────────────────
    if cmd == "shell":
        raw = args.get("command", "")
        if not raw:
            await send("log", level="error", msg="No command provided.")
            return
        await send("log", level="cmd", msg=f"$ {raw}")
        result = await asyncio.to_thread(run_shell, raw, 30)
        if result["stdout"]:
            for line in result["stdout"].splitlines():
                await send("log", level="success", msg=line)
        if result["stderr"]:
            for line in result["stderr"].splitlines():
                await send("log", level="error", msg=line)
        await send("log", level="info", msg=f"Exit code: {result['returncode']}")

    # ── SYSINFO ───────────────────────────────────────────────────────────
    elif cmd == "sysinfo":
        await send("log", level="cmd", msg="Fetching system information...")
        info = await asyncio.to_thread(get_sysinfo)
        await send("sysinfo", data=info)
        await send("log", level="success", msg=f"OS: {info['os']} | Host: {info['hostname']}")
        await send("log", level="info", msg=f"CPU: {info['cpu_brand']} ({info['cpu_count']} cores) @ {info['cpu_percent']}%")
        await send("log", level="info", msg=f"RAM: {info['ram_percent']}% used of {round(info['ram_total']/1e9,1)} GB")
        await send("log", level="info", msg=f"Disk: {info['disk_percent']}% used of {round(info['disk_total']/1e9,1)} GB")
        await send("log", level="info", msg=f"Uptime: {info['uptime']} | IP: {info['local_ip']}")

    # ── RESOURCES (live polling) ───────────────────────────────────────────
    elif cmd == "resources":
        info = await asyncio.to_thread(get_sysinfo)
        await send("resources", data={
            "cpu": info["cpu_percent"],
            "ram": info["ram_percent"],
            "disk": info["disk_percent"],
            "net_sent": info["net_sent"],
            "net_recv": info["net_recv"],
        })

    # ── PROCESSES ─────────────────────────────────────────────────────────
    elif cmd == "processes":
        await send("log", level="cmd", msg="Enumerating processes...")
        procs = await asyncio.to_thread(get_processes)
        await send("processes", data=procs)
        await send("log", level="success", msg=f"Found {len(procs)} processes (top 50 by memory).")

    # ── KILL ──────────────────────────────────────────────────────────────
    elif cmd == "kill":
        pid = int(args.get("pid", 0))
        result = await asyncio.to_thread(kill_process, pid)
        level = "success" if result["ok"] else "error"
        await send("log", level=level, msg=result["msg"])

    # ── SCREENSHOT ────────────────────────────────────────────────────────
    elif cmd == "screenshot":
        await send("log", level="cmd", msg="Capturing screenshot...")
        img_b64 = await asyncio.to_thread(take_screenshot)
        if img_b64:
            await send("screenshot", data=img_b64)
            await send("log", level="success", msg=f"Screenshot captured ({len(img_b64)//1024} KB).")
        else:
            await send("log", level="error", msg="Screenshot failed. Install Pillow: pip install Pillow")

    # ── FILES ─────────────────────────────────────────────────────────────
    elif cmd == "files":
        path = args.get("path", None)
        result = await asyncio.to_thread(get_files, path)
        await send("files", data=result)
        if result["error"]:
            await send("log", level="error", msg=result["error"])
        else:
            await send("log", level="success", msg=f"Listed {len(result['entries'])} items in {result['path']}")

    # ── NETWORK ───────────────────────────────────────────────────────────
    elif cmd == "network":
        await send("log", level="cmd", msg="Fetching network info...")
        info = await asyncio.to_thread(get_network_info)
        await send("network", data=info)
        for iface, addrs in list(info["interfaces"].items())[:4]:
            for a in addrs:
                if a["address"] and ":" not in a["address"]:
                    await send("log", level="info", msg=f"{iface}: {a['address']} / {a.get('netmask','')}")

    # ── CLIPBOARD ─────────────────────────────────────────────────────────
    elif cmd == "clipboard":
        await send("log", level="cmd", msg="Reading clipboard...")
        content = await asyncio.to_thread(get_clipboard)
        await send("clipboard", data=content)
        preview = content[:100] + ("..." if len(content) > 100 else "")
        await send("log", level="success", msg=f"Clipboard: {preview}")

    # ── WHOAMI ────────────────────────────────────────────────────────────
    elif cmd == "whoami":
        raw_cmd = "whoami /all" if IS_WINDOWS else "id && whoami"
        result = await asyncio.to_thread(run_shell, raw_cmd)
        for line in (result["stdout"] or result["stderr"]).splitlines()[:10]:
            await send("log", level="success", msg=line)

    # ── IPCONFIG / IFCONFIG ───────────────────────────────────────────────
    elif cmd in ("ipconfig", "ifconfig"):
        shell_cmd = "ipconfig /all" if IS_WINDOWS else "ip addr show" if IS_LINUX else "ifconfig"
        result = await asyncio.to_thread(run_shell, shell_cmd)
        for line in (result["stdout"] or result["stderr"]).splitlines():
            await send("log", level="info", msg=line)

    # ── TASKLIST / PS ─────────────────────────────────────────────────────
    elif cmd in ("tasklist", "ps"):
        shell_cmd = "tasklist" if IS_WINDOWS else "ps aux"
        result = await asyncio.to_thread(run_shell, shell_cmd)
        for line in (result["stdout"] or result["stderr"]).splitlines()[:30]:
            await send("log", level="info", msg=line)

    # ── LS / DIR ──────────────────────────────────────────────────────────
    elif cmd in ("ls", "dir"):
        path = args.get("path", ".")
        shell_cmd = f'dir "{path}"' if IS_WINDOWS else f'ls -la "{path}"'
        result = await asyncio.to_thread(run_shell, shell_cmd)
        for line in (result["stdout"] or result["stderr"]).splitlines():
            await send("log", level="success", msg=line)
        await handle_command(ws, {"cmd": "files", "args": {"path": path}})

    # ── PWD / CD ──────────────────────────────────────────────────────────
    elif cmd == "pwd":
        await send("log", level="success", msg=os.getcwd())

    elif cmd == "cd":
        path = args.get("path", "~")
        try:
            os.chdir(os.path.expanduser(path))
            await send("log", level="success", msg=f"Changed to: {os.getcwd()}")
        except Exception as e:
            await send("log", level="error", msg=str(e))

    # ── LOCK ──────────────────────────────────────────────────────────────
    elif cmd == "lock":
        await send("log", level="warn", msg="Locking screen...")
        if IS_WINDOWS:
            run_shell("rundll32.exe user32.dll,LockWorkStation")
        elif IS_LINUX:
            run_shell("loginctl lock-session")
        elif IS_MAC:
            run_shell('/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend')
        await send("log", level="success", msg="Lock command sent.")

    # ── SHUTDOWN ──────────────────────────────────────────────────────────
    elif cmd == "shutdown":
        await send("log", level="warn", msg="Shutdown command received. Sending in 30s. Run 'shutdown_cancel' to abort.")
        if IS_WINDOWS:
            run_shell("shutdown /s /t 30")
        elif IS_LINUX or IS_MAC:
            run_shell("shutdown -h +0.5")

    elif cmd == "shutdown_cancel":
        if IS_WINDOWS:
            run_shell("shutdown /a")
        elif IS_LINUX or IS_MAC:
            run_shell("shutdown -c")
        await send("log", level="success", msg="Shutdown cancelled.")

    # ── REBOOT ────────────────────────────────────────────────────────────
    elif cmd == "reboot":
        await send("log", level="warn", msg="Rebooting in 30s...")
        if IS_WINDOWS:
            run_shell("shutdown /r /t 30")
        elif IS_LINUX or IS_MAC:
            run_shell("shutdown -r +0.5")

    # ── OPEN FILE/URL ─────────────────────────────────────────────────────
    elif cmd == "open":
        target = args.get("target", "")
        if IS_WINDOWS:
            run_shell(f'start "" "{target}"')
        elif IS_MAC:
            run_shell(f'open "{target}"')
        else:
            run_shell(f'xdg-open "{target}"')
        await send("log", level="success", msg=f"Opened: {target}")

    # ── PING ──────────────────────────────────────────────────────────────
    elif cmd == "ping":
        host = args.get("host", "8.8.8.8")
        flag = "-n 4" if IS_WINDOWS else "-c 4"
        result = await asyncio.to_thread(run_shell, f"ping {flag} {host}")
        for line in (result["stdout"] or result["stderr"]).splitlines():
            await send("log", level="info", msg=line)

    # ── ENV ───────────────────────────────────────────────────────────────
    elif cmd == "env":
        for k, v in list(os.environ.items())[:30]:
            await send("log", level="info", msg=f"{k}={v}")

    # ── HISTORY ───────────────────────────────────────────────────────────
    elif cmd == "history":
        for i, h in enumerate(command_history[-20:], 1):
            await send("log", level="info", msg=f"{i:3}  [{h['ts']}]  {h['cmd']}")

    # ── CLEAR ─────────────────────────────────────────────────────────────
    elif cmd == "clear":
        await send("clear")

    # ── HELP ──────────────────────────────────────────────────────────────
    elif cmd == "help":
        cmds = [
            "shell <cmd>    — run any shell command",
            "sysinfo        — full system info",
            "resources      — CPU/RAM/Disk/Net stats",
            "processes      — list running processes",
            "kill <pid>     — terminate a process",
            "screenshot     — capture screen",
            "files [path]   — browse filesystem",
            "network        — network interfaces",
            "clipboard      — read clipboard",
            "whoami         — current user/groups",
            "ipconfig       — network configuration",
            "tasklist       — running tasks",
            "ls [path]      — list directory",
            "pwd            — current directory",
            "cd <path>      — change directory",
            "ping <host>    — ping a host",
            "open <path>    — open file or URL",
            "env            — environment variables",
            "lock           — lock screen",
            "shutdown       — shutdown machine",
            "reboot         — reboot machine",
            "history        — command history",
            "clear          — clear terminal",
            "help           — this help",
        ]
        for c in cmds:
            await send("log", level="info", msg=c)

    else:
        await send("log", level="error", msg=f"Unknown command: '{cmd}'. Type 'help' for list.")


# ─── WebSocket Handler ────────────────────────────────────────────────────────
async def handle_client(ws):
    connected_clients.add(ws)
    remote = ws.remote_address
    print(f"[+] Client connected: {remote}")

    # Send handshake
    info = get_sysinfo()
    await ws.send(make_msg("handshake", agent_id=AGENT_ID, version=AGENT_VERSION, sysinfo=info))

    # Start resource polling loop for this client
    async def poll_resources():
        while ws in connected_clients:
            try:
                res_info = get_sysinfo()
                await ws.send(make_msg("resources", data={
                    "cpu": res_info["cpu_percent"],
                    "ram": res_info["ram_percent"],
                    "disk": res_info["disk_percent"],
                    "net_sent": res_info["net_sent"],
                    "net_recv": res_info["net_recv"],
                    "uptime": res_info["uptime"],
                }))
            except Exception:
                break
            await asyncio.sleep(4)

    poll_task = asyncio.create_task(poll_resources())

    try:
        async for message in ws:
            try:
                data = json.loads(message)
                await handle_command(ws, data)
            except json.JSONDecodeError:
                await ws.send(make_msg("log", level="error", msg="Invalid JSON message."))
            except Exception as e:
                await ws.send(make_msg("log", level="error", msg=f"Server error: {e}"))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        poll_task.cancel()
        connected_clients.discard(ws)
        print(f"[-] Client disconnected: {remote}")


# ─── Entry Point ──────────────────────────────────────────────────────────────
async def main():
    print(f"""
╔══════════════════════════════════════════╗
║          CTRL.AI — Python Agent          ║
║  Agent ID : {AGENT_ID:<28} ║
║  Version  : {AGENT_VERSION:<28} ║
║  Platform : {platform.system():<28} ║
║  Host     : {HOST}:{PORT:<23} ║
╚══════════════════════════════════════════╝
  GUI support  : {'YES (pyautogui)' if HAS_GUI else 'NO — pip install pyautogui'}
  PIL support  : {'YES (Pillow)' if HAS_PIL else 'NO — pip install Pillow'}

  Listening for connections...
""")

    async with websockets.serve(handle_client, HOST, PORT, ping_interval=20, ping_timeout=60):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Agent stopped.")
