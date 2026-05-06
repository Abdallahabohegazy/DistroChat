import base64
import io
import os
import tkinter as tk
from tkinter import filedialog
from typing import Any, Callable, Dict

import customtkinter as ctk
from PIL import Image, ImageTk
from plyer import notification

from DistroChat.client.gui.rooms_panel import RoomsPanel
from DistroChat.client.gui.users_panel import UsersPanel
from DistroChat.shared import ui_theme as U


class ChatScreen(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTk,
        on_send: Callable[[str], None],
        on_command: Callable[[str], None],
        on_room_switch: Callable[[str, str], None],
        on_send_file: Callable[[str], None],
        on_typing: Callable[[], None],
        on_logout: Callable[[], None],
    ):
        super().__init__(master, fg_color=U.BG)
        self.on_send = on_send
        self.on_command = on_command
        self.on_room_switch = on_room_switch
        self.on_send_file = on_send_file
        self.on_typing = on_typing
        self.on_logout = on_logout
        self.current_room = "#general"
        self._img_refs = []
        self._downloads_dir = os.path.join("downloads", "received_images")
        os.makedirs(self._downloads_dir, exist_ok=True)
        self._typing_after_id = None
        self._emoji_window: ctk.CTkToplevel | None = None
        self._emoji_search_var: tk.StringVar | None = None
        self._emoji_container: ctk.CTkScrollableFrame | None = None
        self._emoji_buttons: list[tuple[str, ctk.CTkButton]] = []
        self._emoji_list = [
            # Smileys
            "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "🙂", "🙃",
            "😍", "🥰", "😘", "😗", "😙", "😚", "😋", "😜", "😝", "🤪", "🤨", "🧐",
            "🤓", "😎", "🥳", "🤩", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️",
            "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "😱",
            "😨", "😰", "😥", "😓", "🤗", "🤔", "🫡", "🤭", "🫢", "🤫", "🤥", "😶",
            "🫠", "😴", "🥱", "😪", "🤤", "😵", "🤯", "🤠", "🥸", "😈", "👿", "👻",
            # Gestures
            "👍", "👎", "👌", "🤌", "🤏", "✌️", "🤞", "🫶", "🤟", "🤘", "👏", "🙌",
            "👐", "🤲", "🙏", "💪", "🫵", "👋", "🤝", "✍️",
            # Hearts & symbols
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕",
            "💞", "💓", "💗", "💖", "💘", "💝", "🔥", "💯", "✅", "⭐", "⚡", "🎉",
            "✨", "💫", "🎊", "🏆", "🥇", "🚀",
            # Food & drink
            "🍎", "🍉", "🍓", "🍒", "🍍", "🥭", "🍌", "🍋", "🍇", "🍕", "🍔", "🍟",
            "🌭", "🍿", "🥪", "🌮", "🌯", "🍜", "🍣", "🍩", "🍪", "🍫", "🍰", "🧁",
            "☕", "🍵", "🥤", "🧃", "🍹",
            # Objects / misc
            "📌", "📎", "📚", "💡", "🖥️", "⌨️", "🖱️", "📱", "🎧", "🎮", "🎬", "🎵",
            "🌍", "🌙", "☀️", "🌧️", "⛄", "⚽", "🏀", "🏈", "🏓", "🎯", "🧠", "🕒",
        ]
        self._build_ui()

    def _build_ui(self) -> None:
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.rooms_panel = RoomsPanel(self, self._switch_room, self._create_room, self._join_room, self.on_logout)
        self.rooms_panel.grid(row=0, column=0, sticky="nsw")

        center = ctk.CTkFrame(self, fg_color=U.BG)
        center.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        center.grid_rowconfigure(1, weight=1)
        center.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(center, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.status_dot = ctk.CTkLabel(top, text="●", text_color=U.SUCCESS)
        self.status_dot.pack(side="left", padx=8, pady=6)
        self.room_label = ctk.CTkLabel(
            top, text=self.current_room, font=ctk.CTkFont(size=16, weight="bold"), text_color=U.TEXT
        )
        self.room_label.pack(side="left")

        self.chat_box = tk.Text(center, bg=U.INNER, fg=U.TEXT, wrap="word", state="disabled", borderwidth=0)
        self.chat_box.grid(row=1, column=0, sticky="nsew")
        scroll = ctk.CTkScrollbar(center, command=self.chat_box.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.chat_box.configure(yscrollcommand=scroll.set)

        self.typing_label = ctk.CTkLabel(center, text="", text_color=U.MUTED)
        self.typing_label.grid(row=2, column=0, sticky="w", pady=(2, 4))

        bottom = ctk.CTkFrame(center, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.grid_columnconfigure(1, weight=1)

        emoji_btn = ctk.CTkButton(bottom, text="😊", width=40, command=self._open_emoji_picker)
        emoji_btn.grid(row=0, column=0, padx=4, pady=6)
        self.input_box = ctk.CTkEntry(bottom, placeholder_text="Type a message...")
        self.input_box.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        self.input_box.bind("<Return>", self._submit)
        self.input_box.bind("<KeyRelease>", lambda _e: self.on_typing())
        ctk.CTkButton(bottom, text="📎", width=40, command=self._attach_file).grid(row=0, column=2, padx=4, pady=6)
        ctk.CTkButton(bottom, text="Send", width=80, command=self._submit).grid(row=0, column=3, padx=4, pady=6)

        self.users_panel = UsersPanel(self, self._open_dm)
        self.users_panel.grid(row=0, column=2, sticky="nse")

    def _submit(self, _event: object = None) -> None:
        text = self.input_box.get().strip()
        if not text:
            return
        self.input_box.delete(0, tk.END)
        if text.startswith("/"):
            self._handle_command(text)
        else:
            self.on_send(text)

    def _handle_command(self, text: str) -> None:
        if text == "/clear":
            self.chat_box.configure(state="normal")
            self.chat_box.delete("1.0", tk.END)
            self.chat_box.configure(state="disabled")
            return
        if text.startswith("/dm "):
            parts = text.split(" ", 2)
            if len(parts) == 3 and parts[1].startswith("@"):
                self.on_command(f"/dm {parts[1][1:]} {parts[2]}")
                return
        if text == "/quit":
            self.on_command("/quit")
            return
        self.on_command(text)

    def _switch_room(self, room: str) -> None:
        old = self.current_room
        self.current_room = room
        self.room_label.configure(text=room)
        
        # Clear chat box for the new room
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", tk.END)
        self.chat_box.configure(state="disabled")
        self._img_refs.clear()

        self.on_room_switch(old, room)

    def _create_room(self, room_data: Dict[str, Any]) -> None:
        cmd = f"/create_room {room_data['name']} {room_data['description']}"
        if room_data.get("private"):
            cmd += f" --private {room_data.get('password', '')}"
        self.on_command(cmd)

    def _join_room(self, room_data: Dict[str, Any]) -> None:
        self.on_command(f"/join {room_data['name']} {room_data.get('password', '')}")

    def _open_dm(self, username: str) -> None:
        self.on_command(f"/dm {username} ")

    def _attach_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            self.on_send_file(path)

    def _open_emoji_picker(self) -> None:
        if self._emoji_window and self._emoji_window.winfo_exists():
            self._emoji_window.focus()
            return
        self._emoji_window = ctk.CTkToplevel(self)
        self._emoji_window.title("Emoji Picker")
        self._emoji_window.geometry("500x420")
        self._emoji_window.attributes("-topmost", True)
        self._emoji_window.transient(self.winfo_toplevel())
        self._emoji_window.resizable(False, False)

        container = ctk.CTkFrame(self._emoji_window)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._emoji_search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(container, textvariable=self._emoji_search_var, placeholder_text="Search emoji")
        search_entry.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_entry.bind("<KeyRelease>", self._filter_emoji_buttons)

        self._emoji_container = ctk.CTkScrollableFrame(container)
        self._emoji_container.grid(row=1, column=0, sticky="nsew")
        self._emoji_buttons = []

        cols = 10
        for i, emoji in enumerate(self._emoji_list):
            r, c = divmod(i, cols)
            btn = ctk.CTkButton(
                self._emoji_container,
                text=emoji,
                width=38,
                height=34,
                command=lambda e=emoji: self._insert_emoji(e),
            )
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            self._emoji_buttons.append((emoji, btn))

    def _filter_emoji_buttons(self, _event: object = None) -> None:
        if not self._emoji_search_var:
            return
        query = self._emoji_search_var.get().strip()
        for emoji, btn in self._emoji_buttons:
            if not query or query in emoji:
                btn.grid()
            else:
                btn.grid_remove()

    def _insert_emoji(self, emoji: str) -> None:
        self.input_box.insert(tk.END, emoji)
        self.input_box.focus_set()

    def append_message(self, msg: Dict[str, Any], own_username: str) -> None:
        mtype = msg.get("type")
        sender = msg.get("sender", "unknown")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")
        color = U.TEXT
        if mtype == "server_msg":
            color = U.ACCENT
        elif mtype == "dm":
            color = "#d8b4fe"
        elif sender == own_username:
            color = U.SUCCESS

        self.chat_box.configure(state="normal")
        self.chat_box.insert(tk.END, f"[{ts}] {sender}: ", ("name",))
        self.chat_box.insert(tk.END, f"{content}\n", (f"c_{color}",))
        self.chat_box.tag_config("name", foreground=U.ACCENT)
        self.chat_box.tag_config(f"c_{color}", foreground=color)

        if mtype == "file":
            self._render_inline_image(msg.get("file_data", ""), msg.get("file_name", "image"), int(msg.get("file_size", 0) or 0))
        self.chat_box.configure(state="disabled")
        self.chat_box.see(tk.END)

        if mtype == "dm" and sender != own_username:
            try:
                notification.notify(
                    title=f"DM from {sender}",
                    message=str(content)[:500],
                    timeout=3,
                )
            except Exception:
                pass

    def _render_inline_image(self, payload_b64: str, filename: str, file_size: int = 0) -> None:
        try:
            raw = base64.b64decode(payload_b64.encode("utf-8"))
            img = Image.open(io.BytesIO(raw))
            img.thumbnail((240, 240))
            tk_img = ImageTk.PhotoImage(img)
            self._img_refs.append(tk_img)
            self.chat_box.image_create(tk.END, image=tk_img)
            safe_name = os.path.basename(filename)
            save_name = self._unique_download_name(safe_name)
            save_path = os.path.join(self._downloads_dir, save_name)
            with open(save_path, "wb") as f:
                f.write(raw)
            size_kb = max(1, len(raw) // 1024) if not file_size else max(1, file_size // 1024)
            self.chat_box.insert(tk.END, f"\n[Image: {safe_name} | {size_kb} KB | saved: {save_path}]\n")
        except Exception:
            self.chat_box.insert(tk.END, "[Failed to render image]\n")

    def _unique_download_name(self, filename: str) -> str:
        base, ext = os.path.splitext(filename)
        candidate = filename
        idx = 1
        while os.path.exists(os.path.join(self._downloads_dir, candidate)):
            candidate = f"{base}_{idx}{ext}"
            idx += 1
        return candidate

    def set_typing(self, text: str) -> None:
        self.typing_label.configure(text=text)
        if self._typing_after_id:
            self.after_cancel(self._typing_after_id)
        self._typing_after_id = self.after(2000, lambda: self.typing_label.configure(text=""))

