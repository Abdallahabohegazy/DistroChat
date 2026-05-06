import customtkinter as ctk
import tkinter as tk
from typing import Callable

from DistroChat.shared import ui_theme as U


class UsersPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame, on_dm_open: Callable[[str], None]):
        super().__init__(master, width=230, fg_color=U.BG)
        self.on_dm_open = on_dm_open
        self.users: list[dict] = []
        self._build()

    def _build(self) -> None:
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="Online Users", font=ctk.CTkFont(size=18, weight="bold"), text_color=U.TEXT).pack(pady=(10, 8))
        self.search_var = tk.StringVar()
        search = ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search user")
        search.pack(fill="x", padx=8, pady=6)
        search.bind("<KeyRelease>", self._render)

        self.listbox = tk.Listbox(
            self,
            bg=U.INNER,
            fg=U.TEXT,
            selectbackground=U.LIST_SELECT,
            selectforeground=U.TEXT,
            borderwidth=0,
            highlightthickness=0,
        )
        self.listbox.pack(fill="both", expand=True, padx=8, pady=6)
        self.listbox.bind("<Double-Button-1>", self._open_dm)

    def set_users(self, users: list[dict]) -> None:
        self.users = users
        self._render()

    def _render(self, _event: object = None) -> None:
        q = self.search_var.get().strip().lower()
        self.listbox.delete(0, tk.END)
        for u in self.users:
            name = u.get("username", "")
            if q and q not in name.lower():
                continue
            role = u.get("role", "user")
            badge = "👑" if role == "admin" else ("🛡️" if role == "moderator" else "•")
            self.listbox.insert(tk.END, f"{badge} {name}")

    def _open_dm(self, _event: object) -> None:
        idx = self.listbox.curselection()
        if not idx:
            return
        label = self.listbox.get(idx[0])
        parts = label.split(" ", 1)
        user = parts[1] if len(parts) > 1 else parts[0]
        self.on_dm_open(user)

