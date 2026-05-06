import json
import os
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from DistroChat.shared import ui_theme as U


class LoginScreen(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTk,
        on_login: Callable[[str, str, str, int], None],
        on_register: Callable[[str, str, str, int], None],
    ):
        super().__init__(master, fg_color=U.BG)
        self.on_login = on_login
        self.on_register = on_register
        self.cfg_path = "client_last_server.json"
        self._build_ui()
        self._load_last_server()

    def _build_ui(self) -> None:
        self.pack(fill="both", expand=True, padx=20, pady=20)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="DistroChat Login",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=U.TEXT,
        ).grid(row=0, column=0, pady=(20, 14))

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username")
        self.username_entry.grid(row=1, column=0, padx=30, pady=8, sticky="ew")

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Password", show="*")
        self.password_entry.grid(row=2, column=0, padx=30, pady=8, sticky="ew")

        self.ip_entry = ctk.CTkEntry(self, placeholder_text="Server IP (e.g. 192.168.1.8)")
        self.ip_entry.grid(row=3, column=0, padx=30, pady=8, sticky="ew")

        self.port_entry = ctk.CTkEntry(self, placeholder_text="Port (e.g. 5050)")
        self.port_entry.insert(0, "5050")
        self.port_entry.grid(row=4, column=0, padx=30, pady=8, sticky="ew")

        self.error_label = ctk.CTkLabel(self, text="", text_color=U.DANGER)
        self.error_label.grid(row=5, column=0, padx=30, pady=(0, 8), sticky="w")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=6, column=0, pady=16)
        ctk.CTkButton(buttons, text="Login", width=120, command=self._try_login).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Register", width=120, command=self._try_register).pack(side="left", padx=8)

    def _load_last_server(self) -> None:
        if not os.path.exists(self.cfg_path):
            return
        try:
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, data.get("ip", "127.0.0.1"))
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(data.get("port", 5050)))
        except Exception:
            pass

    def _save_last_server(self, ip: str, port: int) -> None:
        try:
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump({"ip": ip, "port": port}, f)
        except Exception:
            pass

    def _collect(self) -> tuple[str, str, str, int]:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        ip = self.ip_entry.get().strip() or "127.0.0.1"
        port = int(self.port_entry.get().strip() or "5050")
        return username, password, ip, port

    def _try_login(self) -> None:
        try:
            username, password, ip, port = self._collect()
            self._save_last_server(ip, port)
            self.error_label.configure(text="")
            self.on_login(username, password, ip, port)
        except Exception as exc:
            self.error_label.configure(text=str(exc))

    def _try_register(self) -> None:
        try:
            username, password, ip, port = self._collect()
            self._save_last_server(ip, port)
            self.error_label.configure(text="")
            self.on_register(username, password, ip, port)
        except Exception as exc:
            self.error_label.configure(text=str(exc))

    def show_error(self, message: str) -> None:
        self.error_label.configure(text=message)

