# CTRL.AI — Full Device Control Agent

A real working remote device control agent with Python backend + Web frontend.
Inspired by cl0wd bot style interfaces.

---

## 📁 Files

```
agent/
├── server.py        ← Python WebSocket backend (runs on TARGET machine)
├── index.html       ← Web frontend (open in any browser)
├── requirements.txt ← Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### Step 1 — Install Python dependencies (on target machine)

```bash
pip install websockets psutil Pillow pyautogui
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### Step 2 — Start the agent server

```bash
python server.py
```

You should see:
```
╔══════════════════════════════════════════╗
║          CTRL.AI — Python Agent          ║
║  Agent ID : AGENT-DESKTOP                ║
║  Host     : 0.0.0.0:9000                 ║
╚══════════════════════════════════════════╝
  Listening for connections...
```

### Step 3 — Open the frontend

Just open `index.html` in your browser. Enter:
- `ws://localhost:9000` (if same machine)
- `ws://192.168.x.x:9000` (if on the same LAN)

Click **CONNECT TO AGENT**.

---

## 🌐 Remote Access (Different Network)

To control a machine over the internet:

### Option A — ngrok (easiest)
```bash
# Install ngrok: https://ngrok.com
ngrok tcp 9000
# Use the forwarded address in the frontend, like:
# ws://0.tcp.ngrok.io:12345
```

### Option B — SSH Tunnel
```bash
# On the machine with server.py:
ssh -R 9000:localhost:9000 user@your-vps.com
# Frontend connects to ws://your-vps.com:9000
```

### Option C — VPN (Tailscale/ZeroTier)
Connect both machines to same VPN, use the VPN IP.

---

## 💻 Supported Commands

| Command | Description |
|---------|-------------|
| `sysinfo` | Full OS/CPU/RAM/Disk info |
| `resources` | Live CPU/RAM/Disk/Network stats |
| `processes` | List running processes (top 50) |
| `kill <pid>` | Terminate a process by PID |
| `screenshot` | Capture desktop screenshot |
| `files [path]` | Browse filesystem |
| `network` | Network interfaces |
| `clipboard` | Read clipboard content |
| `whoami` | Current user and groups |
| `shell <cmd>` | Execute any shell command |
| `ipconfig` | IP configuration |
| `tasklist` | Running tasks (Windows style) |
| `ls [path]` | List directory |
| `pwd` | Current directory |
| `cd <path>` | Change directory |
| `ping <host>` | Ping a host |
| `open <path>` | Open file or URL on remote |
| `env` | Environment variables |
| `lock` | Lock the screen |
| `shutdown` | Shutdown the machine (30s delay) |
| `shutdown_cancel` | Cancel pending shutdown |
| `reboot` | Reboot the machine |
| `history` | Command history |
| `clear` | Clear terminal |
| `help` | Show all commands |

You can also type ANY shell command directly — it will be forwarded to the OS shell.

Examples:
```
ipconfig /all
netstat -an
dir C:\Users
cat /etc/passwd
curl ifconfig.me
systeminfo
```

---

## ⚡ Features

- **Real-time system stats** — CPU, RAM, Disk, Network updated every 4 seconds
- **Live screenshot** — capture desktop as JPEG, with auto-screenshot mode (every 5s)
- **File browser** — navigate the filesystem, click folders to enter
- **Process manager** — list and kill processes
- **Full shell access** — run any OS command
- **Clipboard reader** — read clipboard contents
- **Persistent connection** — auto-detects disconnects
- **Command history** — arrow-key navigation in terminal
- **Cross-platform** — Windows, Linux, macOS

---

## 🔒 Security Notes

- This tool gives **full admin control** over the target machine.
- Only use on machines **you own** or have explicit permission to control.
- For security, consider:
  - Adding password authentication to `server.py`
  - Restricting `HOST` to a specific IP instead of `0.0.0.0`
  - Using TLS (wss://) with a reverse proxy like nginx

---

## 🔧 Troubleshooting

**Screenshot not working?**
```bash
pip install Pillow pyautogui
# On Linux, also install:
sudo apt install scrot python3-tk python3-dev
```

**Permission denied for some commands?**
Run `server.py` as Administrator (Windows) or with `sudo` (Linux).

**Can't connect?**
- Check firewall allows port 9000
- Confirm server.py is running
- Try `ws://127.0.0.1:9000` instead of `localhost`
