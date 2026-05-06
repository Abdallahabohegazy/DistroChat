# DistroChat — Distributed Multi-Client Chat System

Python 3.11+ distributed multi-client chat with:
- TCP client-server (multi-threaded) + length-prefixed JSON protocol
- SQLite persistence (users/messages/rooms/bans)
- AES encryption (via `cryptography`)
- Modern GUI using CustomTkinter
- Admin dashboard (stats, user management, logs, broadcast)

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run server

```bash
python DistroChat\server\server.py
```

Server reads `config.json` from the workspace root.

## Run client GUI

```bash
python DistroChat\client\gui\app.py
```

## Run admin dashboard

```bash
python DistroChat\admin\admin_dashboard.py
```

## Connect from different machines on the same Wi‑Fi

- Start the server on a machine and allow inbound TCP on the configured port (default `5050`) in the firewall.
- Find the server LAN IP (e.g., `192.168.1.x`) and use it in the client login screen.
- Ensure all devices are on the same Wi‑Fi network.

## Team members

- Name 1
- Name 2
- Name 3

## Screenshots

- (add screenshots here)

