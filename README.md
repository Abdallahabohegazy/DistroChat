# DistroChat
A distributed multi-client chat system built with Python, featuring secure communication, persistent storage, role-based moderation, and a modern desktop GUI.

---

## Overview
**DistroChat** is a Distributed Computing project that implements a real-time chat platform using a TCP client-server architecture.  
It supports multiple rooms, direct messages, moderation commands, admin controls, and encrypted message exchange.

This project was designed to provide hands-on experience with:
- Concurrent network programming
- Distributed system communication patterns
- Secure messaging
- Data persistence and role-based access control

---

## Features

- Multi-threaded TCP server for handling multiple clients concurrently
- Length-prefixed JSON message protocol
- AES-based encrypted communication
- SQLite persistence for users, messages, rooms, and bans
- Room system (public/private rooms)
- Direct messaging between users
- Role-based permissions:
  - User
  - Moderator
  - Admin
- Moderation commands (`/kick`, `/mute`, `/ban`, `/unban`, etc.)
- Admin dashboard for monitoring and broadcast
- Desktop GUI client built with CustomTkinter
- Chat history and room activity tracking

---

## Tech Stack

- **Language:** Python 3.11+
- **Networking:** TCP sockets + threading
- **Database:** SQLite
- **Encryption:** `cryptography` (AES)
- **GUI:** CustomTkinter

---

## Project Structure

```text
DistroChat/
├─ DistroChat/
│  ├─ server/
│  │  ├─ server.py
│  │  ├─ client_handler.py
│  │  ├─ db_manager.py
│  │  ├─ room_manager.py
│  │  └─ admin_manager.py
│  ├─ client/
│  │  ├─ client.py
│  │  └─ gui/
│  │     ├─ app.py
│  │     ├─ login_screen.py
│  │     ├─ chat_screen.py
│  │     ├─ rooms_panel.py
│  │     └─ users_panel.py
│  ├─ admin/
│  │  └─ admin_dashboard.py
│  └─ shared/
│     └─ ui_theme.py
├─ config.json
├─ COMMANDS.md
└─ README.md
