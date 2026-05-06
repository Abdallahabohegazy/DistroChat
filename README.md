# 🚀 DistroChat  
### Distributed Multi-Client Secure Chat System

> A distributed real-time chat platform built with Python, designed for secure communication, scalable networking, role-based moderation, and a modern desktop GUI.

---

## 📌 Overview

**DistroChat** is a Distributed Computing project that implements a real-time secure chat system using a **multi-threaded TCP client-server architecture**.

It supports:

- 💬 Public chat rooms  
- 🔒 AES encrypted communication  
- 👤 Direct private messaging  
- 🛡️ Moderation & admin controls  
- 🗄️ Persistent storage with SQLite  
- 🖥️ Desktop GUI with CustomTkinter  

### 🎯 Learning Outcomes

This project provided hands-on experience in:

- Concurrent network programming  
- Distributed communication systems  
- Secure socket-based messaging  
- Role-based access control  
- Database persistence  
- GUI software engineering  

---

## ✨ Features

### 🌐 Networking
- Multi-threaded TCP server
- Concurrent multi-client communication
- Length-prefixed JSON messaging protocol
- Reliable structured packet exchange

### 🔐 Security
- AES encrypted client-server communication
- Secure authentication system
- User role validation

### 🗄️ Persistence
- SQLite database integration:
  - Users
  - Messages
  - Rooms
  - Ban records
  - Logs

### 💬 Chat Functionalities
- Public rooms
- Private/password-protected rooms
- Direct Messaging (DM)
- Chat history
- Room activity tracking

### 👮 Moderation & Administration
- `/kick`
- `/mute`
- `/ban`
- `/unban`
- `/broadcast`
- Admin dashboard for:
  - User management
  - Monitoring
  - Announcements
  - Logs

### 🖥️ GUI
- Modern responsive desktop interface
- CustomTkinter design
- User-friendly controls
- Role-based dashboards

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Core Development |
| TCP Sockets | Networking |
| Threading | Concurrent Clients |
| SQLite | Persistent Storage |
| Cryptography (AES) | Security |
| CustomTkinter | GUI |

---

## 📂 Project Structure

```text
DistroChat/
├── DistroChat/
│   ├── server/
│   │   ├── server.py
│   │   ├── client_handler.py
│   │   ├── db_manager.py
│   │   ├── room_manager.py
│   │   └── admin_manager.py
│   │
│   ├── client/
│   │   ├── client.py
│   │   └── gui/
│   │       ├── app.py
│   │       ├── login_screen.py
│   │       ├── chat_screen.py
│   │       ├── rooms_panel.py
│   │       └── users_panel.py
│   │
│   ├── admin/
│   │   └── admin_dashboard.py
│   │
│   └── shared/
│       └── ui_theme.py
│
├── config.json
├── COMMANDS.md
└── README.md

⚙️ Prerequisites

Before installation, ensure you have:

Python 3.11 or later
pip
Git (optional)
Verify:
python --version
pip --version
📥 Installation
1️⃣ Clone Repository
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
cd <YOUR_REPO_NAME>
2️⃣ Create Virtual Environment
python -m venv .venv
3️⃣ Activate Virtual Environment

Windows PowerShell

.venv\Scripts\Activate.ps1

Windows CMD

.venv\Scripts\activate.bat

macOS/Linux

source .venv/bin/activate
4️⃣ Install Dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
⚙️ Configuration

Edit config.json:

{
  "host": "0.0.0.0",
  "port": 5050,
  "max_clients": 100,
  "room_max_capacity": 50,
  "db_path": "database/distrochat.db",
  "log_path": "logs/chat_logs.txt"
}
Key Settings:
host
port
max_clients
room_max_capacity
db_path
log_path
▶️ Running The Project
Start Server
python DistroChat/server/server.py
Start Client GUI
python DistroChat/client/gui/app.py
Start Admin Dashboard
python DistroChat/admin/admin_dashboard.py
🌍 Running on Multiple Devices (LAN)
Start server on host machine
Allow firewall TCP access for selected port
Find host LAN IP:
ipconfig
Use server IP in client login screen:
192.168.x.x
Ensure all devices are connected to same network
💻 Available Commands
General Commands
/help
/rooms
/who
/join <room>
/create_room <name>
/dm @user <message>
Moderator/Admin Commands
/kick <user>
/mute <user> <seconds>
/ban <user>
/unban <user>
/broadcast <message>

📄 Full documentation available in:

COMMANDS.md
☁️ Upload to GitHub (First Time)
git init
git add .
git commit -m "Initial commit - DistroChat"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin main
🗑️ Uninstallation
Deactivate Environment
deactivate
Remove Project Data

Windows

rmdir /s /q .venv
rmdir /s /q database
rmdir /s /q logs

macOS/Linux

rm -rf .venv database logs
🧩 Troubleshooting
Port Already In Use

Edit:

"port": 5051
Dependency Installation Issues
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Client Cannot Connect
Verify server is running
Check IP/port
Check firewall permissions
🔮 Future Improvements
End-to-End Encryption
File Sharing
Search & Filtering
Docker Deployment
Automated Testing
CI/CD Pipeline
🤝 Team Collaboration

Developed collaboratively as part of a university Distributed Computing project, emphasizing:

Software architecture
Networking
Security
Teamwork
Real-world distributed systems implementation
📜 License

This project is intended for educational purposes under university coursework.
