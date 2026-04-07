# CTRL.AI — Remote Device Control Agent

A real-time remote device control agent built with 
Pure Python WebSockets and Vanilla HTML/CSS/JS.
No Django. No Flask. No framework.

![Dashboard Screenshot](screenshots/dashboard.png)

## 🚀 What It Does

Control any PC remotely from your browser with:

- 💻 Full remote terminal — execute any shell command
- 📊 Live system monitoring — CPU, RAM, Disk, Network
- 📷 Desktop screenshot capture with auto-mode
- 📁 File system browser — navigate entire disk
- ⚙️ Process manager — view and kill processes
- 📋 Clipboard reader
- 🔒 Screen lock, Shutdown, Reboot control

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, websockets, psutil, Pillow |
| Frontend | HTML, CSS, JavaScript |
| Protocol | WebSocket (real-time bidirectional) |
| Platform | Windows, Linux, macOS |

## ⚡ Quick Start

### 1. Clone the repo
git clone https://github.com/YOURNAME/ctrl-ai.git
cd ctrl-ai

### 2. Install dependencies
pip install -r requirements.txt

### 3. Run the agent server
python server.py

### 4. Open index.html in your browser
Enter ws://localhost:9000 and click CONNECT

## 📡 Remote Access

**Same network:** use ws://192.168.x.x:9000

**Over internet (ngrok):**
ngrok tcp 9000
Then use the ngrok address in the frontend.

## 💻 All Commands

| Command | Description |
|---------|-------------|
| `shell <cmd>` | Run any OS shell command |
| `sysinfo` | Full system information |
| `processes` | List running processes |
| `kill <pid>` | Kill a process by PID |
| `screenshot` | Capture desktop |
| `files [path]` | Browse filesystem |
| `network` | Network interfaces |
| `clipboard` | Read clipboard |
| `whoami` | Current user info |
| `lock` | Lock screen |
| `shutdown` | Shutdown machine |
| `reboot` | Reboot machine |

## ⚠️ Legal Notice

This tool is built for educational purposes and 
legitimate use only — managing your own machines, 
home lab, IT administration. Do not use on machines 
you do not own or have permission to access.

## 👤 Author

Built by CAPTAIN
- LinkedIn: linkedin.com/in/YOURPROFILE
- GitHub: github.com/YOURNAME
