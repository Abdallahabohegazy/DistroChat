import json
import os
import sys

def _configure_tk_env() -> None:
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return
    candidates = [
        os.path.join(sys.base_prefix, "tcl"),
        r"C:\Users\montafe\AppData\Local\Programs\Python\Python314\tcl",
    ]
    for base in candidates:
        tcl = os.path.join(base, "tcl8.6")
        tk = os.path.join(base, "tk8.6")
        if os.path.isdir(tcl) and os.path.isdir(tk):
            os.environ.setdefault("TCL_LIBRARY", tcl)
            os.environ.setdefault("TK_LIBRARY", tk)
            break


_configure_tk_env()

import customtkinter as ctk

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DistroChat.client.client import ChatClient
from DistroChat.client.gui.chat_screen import ChatScreen
from DistroChat.client.gui.login_screen import LoginScreen
from DistroChat.shared import ui_theme as U


class DistroChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DistroChat")
        self.geometry("1280x760")
        self.configure(fg_color=U.BG)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.client: ChatClient | None = None
        self.username = ""
        self.login_screen = LoginScreen(self, self._handle_login, self._handle_register)
        self.chat_screen: ChatScreen | None = None

    def _connect_client(self, ip: str, port: int) -> bool:
        self.client = ChatClient(ip, port)
        self.client.on_message = self._on_message
        self.client.on_error = self._on_error
        self.client.on_disconnect = self._on_disconnect
        return self.client.connect()

    def _handle_login(self, username: str, password: str, ip: str, port: int) -> None:
        if not username.strip():
            self.login_screen.show_error("Username is required.")
            return
        if not password:
            self.login_screen.show_error("Password is required.")
            return
        if not self._connect_client(ip, port):
            self.login_screen.show_error("Server offline or unreachable")
            return
        self.username = username
        self.client.login(username, password)

    def _handle_register(self, username: str, password: str, ip: str, port: int) -> None:
        if not username.strip():
            self.login_screen.show_error("Username is required.")
            return
        if len(password) < 4:
            self.login_screen.show_error("Password must be at least 4 characters.")
            return
        if not self._connect_client(ip, port):
            self.login_screen.show_error("Server offline or unreachable")
            return
        self.client.register(username, password, f"{username}@distrochat.local")
        self.client.login(username, password)

    def _show_chat(self) -> None:
        if self.chat_screen:
            return
        self.login_screen.destroy()
        self.chat_screen = ChatScreen(
            self,
            on_send=lambda text: self.client.send_chat(text),
            on_command=self._handle_command,
            on_room_switch=self._on_room_switch,
            on_send_file=lambda p: self.client.send_file(p),
            on_typing=lambda: self.client.send_typing(),
            on_logout=self._handle_logout,
        )
        self.after(5000, self._poll_server_state)

    def _handle_logout(self) -> None:
        if self.client:
            self.client.disconnect("logout")
            self.client = None
        if self.chat_screen:
            self.chat_screen.destroy()
            self.chat_screen = None
        
        # Re-show login screen
        self.login_screen = LoginScreen(self, self._handle_login, self._handle_register)
        self.login_screen.pack(fill="both", expand=True, padx=20, pady=20)

    def _poll_server_state(self) -> None:
        if self.client and self.client.running:
            self.client.send_command("/stats")
            self.after(5000, self._poll_server_state)

    def _handle_command(self, cmd: str) -> None:
        if cmd.startswith("/dm "):
            parts = cmd.split(" ", 2)
            if len(parts) == 3:
                self.client.send_dm(parts[1], parts[2])
                return
        if cmd.startswith("/join "):
            parts = cmd.split(" ", 2)
            self.client.join_room(parts[1], parts[2] if len(parts) > 2 else "")
            return
        if cmd == "/rooms":
            self.client.send_command("/rooms")
            return
        if cmd == "/who":
            self.client.send_command("/who")
            return
        if cmd == "/help":
            self.client.send_command("/help")
            return
        if cmd == "/quit":
            self.client.disconnect("quit")
            self.destroy()
            return
        self.client.send_command(cmd)

    def _on_room_switch(self, _old_room: str, new_room: str) -> None:
        self.client.join_room(new_room)

    def _on_message(self, msg: dict) -> None:
        self.after(0, lambda: self._on_message_ui(msg))

    def _on_message_ui(self, msg: dict) -> None:
        if msg.get("type") == "auth_fail":
            if self.login_screen.winfo_exists():
                self.login_screen.show_error(msg.get("content", "Auth failed"))
            return
        if msg.get("type") == "auth_ok":
            self.after(0, self._show_chat)
            return
        if msg.get("type") == "server_msg" and isinstance(msg.get("content"), str) and msg["content"].startswith("{"):
            try:
                stats = json.loads(msg["content"])
                if self.chat_screen:
                    self.chat_screen.users_panel.set_users(stats.get("users", []))
                    
                    # Update room list on the left
                    room_activity = stats.get("room_activity", {})
                    if room_activity:
                        room_names = sorted(room_activity.keys())
                        self.chat_screen.rooms_panel.refresh_rooms(room_names)
                return
            except Exception:
                pass
        if not self.chat_screen:
            return
        
        msg_room = msg.get("room")
        cur_room = self.chat_screen.current_room
        mtype = msg.get("type")

        if mtype == "typing":
            if msg_room == cur_room:
                self.chat_screen.set_typing(f"{msg.get('sender')} is typing...")
            return

        # Only show chat/file messages if they are for the current room
        # Or if it's a global message (no room specified)
        is_global = msg_room in (None, "", "None")
        if mtype in ("chat", "file", "server_msg"):
            if msg.get("content") == "CLEAR_UI" and msg.get("sender") == "server":
                self.chat_screen.chat_box.configure(state="normal")
                self.chat_screen.chat_box.delete("1.0", tk.END)
                self.chat_screen.chat_box.configure(state="disabled")
                return

            if msg_room == cur_room or is_global:
                self.chat_screen.append_message(msg, self.username)
            elif msg_room and not is_global:
                self.chat_screen.rooms_panel.increment_unread(msg_room)
        else:
            # DMs or other types
            self.chat_screen.append_message(msg, self.username)

    def _on_error(self, error_text: str) -> None:
        self.after(0, lambda: self._on_error_ui(error_text))

    def _on_error_ui(self, error_text: str) -> None:
        if self.chat_screen:
            self.chat_screen.append_message(
                {"type": "error", "sender": "error", "content": error_text, "timestamp": ""},
                self.username,
            )
        else:
            self.login_screen.show_error(error_text)

    def _on_disconnect(self, reason: str) -> None:
        self.after(0, lambda: self._on_disconnect_ui(reason))

    def _on_disconnect_ui(self, reason: str) -> None:
        if self.chat_screen:
            self.chat_screen.append_message(
                {"type": "server_msg", "sender": "server", "content": f"Disconnected: {reason}", "timestamp": ""},
                self.username,
            )


def main() -> None:
    app = DistroChatApp()
    app.mainloop()


if __name__ == "__main__":
    main()

