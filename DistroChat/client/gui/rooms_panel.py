import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog
from typing import Callable

from DistroChat.shared import ui_theme as U


class RoomsPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame, on_switch: Callable[[str], None], on_create: Callable[[dict], None], on_join: Callable[[dict], None], on_logout: Callable[[], None]):
        super().__init__(master, width=220, fg_color=U.BG)
        self.on_switch = on_switch
        self.on_create = on_create
        self.on_join = on_join
        self.on_logout = on_logout
        self.rooms: list[str] = ["#general", "#random", "#announcements"]
        self.badges: dict[str, int] = {}
        self._build()

    def _build(self) -> None:
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="Rooms", font=ctk.CTkFont(size=18, weight="bold"), text_color=U.TEXT).pack(pady=(10, 8))
        self.listbox = tk.Listbox(
            self,
            bg=U.INNER,
            fg=U.TEXT,
            selectbackground=U.LIST_SELECT,
            selectforeground=U.TEXT,
            borderwidth=0,
            highlightthickness=0,
        )
        self.listbox.pack(fill="both", expand=True, padx=8)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(button_row, text="+ Create Room", command=self._create_room_popup).pack(fill="x", pady=4)
        ctk.CTkButton(button_row, text="+ Join Room", command=self._join_room_popup).pack(fill="x", pady=4)
        ctk.CTkButton(button_row, text="Logout", fg_color=U.DANGER, hover_color="#b91c1c", command=self.on_logout).pack(fill="x", pady=(12, 4))
        self.refresh_rooms(self.rooms)

    @staticmethod
    def _normalize_room_name(name: str) -> str:
        n = (name or "").strip()
        if not n:
            return n
        if not n.startswith("#"):
            n = "#" + n.lstrip("#")
        return n

    def _on_select(self, _event: object) -> None:
        idx = self.listbox.curselection()
        if not idx:
            return
        room_display = self.listbox.get(idx[0])
        room = room_display.split(" ")[0]
        self.badges[room] = 0
        self.refresh_rooms(self.rooms)
        self.on_switch(room)

    def refresh_rooms(self, rooms: list[str]) -> None:
        self.rooms = rooms
        self.listbox.delete(0, tk.END)
        for room in rooms:
            badge = self.badges.get(room, 0)
            suffix = f" ({badge})" if badge > 0 else ""
            self.listbox.insert(tk.END, f"{room}{suffix}")

    def increment_unread(self, room: str) -> None:
        self.badges[room] = self.badges.get(room, 0) + 1
        self.refresh_rooms(self.rooms)

    def _create_room_popup(self) -> None:
        name = simpledialog.askstring("Create Room", "Room name (#optional):", parent=self)
        if not name:
            return
        name = self._normalize_room_name(name)
        desc = simpledialog.askstring("Create Room", "Description:", parent=self) or ""
        private = simpledialog.askstring("Create Room", "Private? (yes/no):", parent=self) or "no"
        pw = ""
        if private.lower().startswith("y"):
            pw = simpledialog.askstring("Create Room", "Room password:", parent=self, show="*") or ""
        self.on_create({"name": name, "description": desc, "private": private.lower().startswith("y"), "password": pw})

    def _join_room_popup(self) -> None:
        name = simpledialog.askstring("Join Room", "Room name:", parent=self)
        if not name:
            return
        name = self._normalize_room_name(name)
        pw = simpledialog.askstring("Join Room", "Password (if private):", parent=self, show="*") or ""
        self.on_join({"name": name, "password": pw})

