import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import filedialog, simpledialog, ttk


def _configure_tk_env() -> None:
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return
    candidates = [
        os.path.join(sys.base_prefix, "tcl"),
        r"C:\Users\montafe\AppData\Local\Programs\Python\Python314\tcl",
    ]
    for base in candidates:
        tcl = os.path.join(base, "tcl8.6")
        tk_dir = os.path.join(base, "tk8.6")
        if os.path.isdir(tcl) and os.path.isdir(tk_dir):
            os.environ.setdefault("TCL_LIBRARY", tcl)
            os.environ.setdefault("TK_LIBRARY", tk_dir)
            break


_configure_tk_env()

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DistroChat.client.client import ChatClient
from DistroChat.shared import ui_theme as U


class AdminDashboard(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DistroChat Admin")
        self.geometry("1280x820")
        self.minsize(960, 640)
        self.configure(fg_color=U.BG)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.client: ChatClient | None = None
        self.stats_points: deque[float] = deque(maxlen=120)
        self._dashboard_ready = False
        self._pending_logs: list[str] = []
        self._ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._cached_users: list[dict] = []
        self._last_log_snapshot = ""
        self._last_log_mtime = 0.0
        self._last_log_poll = 0.0
        self._log_path = U.read_log_path_from_config(ROOT)
        self._log_missing_notice_shown = False
        self._font_title = ctk.CTkFont(size=26, weight="bold")
        self._font_sub = ctk.CTkFont(size=14)
        self._font_small = ctk.CTkFont(size=12)
        self._font_stat = ctk.CTkFont(size=22, weight="bold")

        self._build_connect_view()
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.after(80, self._drain_ui_queue)

    def _tab_shell(self, tab: ctk.CTkBaseClass) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(tab, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=U.TAB_PAD_X, pady=U.TAB_PAD_Y)
        return outer

    def _build_connect_view(self) -> None:
        outer = ctk.CTkFrame(self, fg_color=U.BG)
        outer.pack(fill="both", expand=True)

        center = ctk.CTkFrame(outer, fg_color="transparent")
        center.place(relx=0.5, rely=0.48, anchor="center")

        card = ctk.CTkFrame(center, fg_color=U.CARD, corner_radius=U.CARD_RADIUS_LARGE, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        card.pack(padx=32, pady=32)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=36, pady=32)

        ctk.CTkLabel(inner, text="Admin console", font=self._font_title, text_color=U.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="Sign in with an Admin or Moderator account.\nOptional: set admin_bootstrap in config.json to create the first admin user.",
            font=self._font_small,
            text_color=U.MUTED,
            justify="left",
        ).pack(anchor="w", pady=(8, 20))

        row_net = ctk.CTkFrame(inner, fg_color="transparent")
        row_net.pack(fill="x", pady=(0, 10))
        row_net.grid_columnconfigure((0, 1), weight=1)
        self.ip_entry = ctk.CTkEntry(row_net, placeholder_text="Server host", height=40, font=self._font_small)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.port_entry = ctk.CTkEntry(row_net, placeholder_text="Port", height=40, width=120, font=self._font_small)
        self.port_entry.insert(0, "5050")
        self.port_entry.grid(row=0, column=1, sticky="e")

        self.user_entry = ctk.CTkEntry(inner, placeholder_text="Username", height=40, font=self._font_small)
        self.user_entry.pack(fill="x", pady=(0, 10))
        self.pass_entry = ctk.CTkEntry(inner, placeholder_text="Password", height=40, show="*", font=self._font_small)
        self.pass_entry.pack(fill="x", pady=(0, 14))

        self.err = ctk.CTkLabel(inner, text="", text_color=U.DANGER, font=self._font_small, wraplength=400, justify="left")
        self.err.pack(anchor="w", pady=(0, 8))

        ctk.CTkButton(
            inner,
            text="Connect & sign in",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=U.ACCENT,
            hover_color=U.ACCENT_HOVER,
            command=self._connect_clicked,
        ).pack(fill="x", pady=(8, 0))

        self._login_frame = outer

    def _connect_clicked(self) -> None:
        self.err.configure(text="Connecting…")
        host = self.ip_entry.get().strip() or "127.0.0.1"
        try:
            port = int(self.port_entry.get().strip() or "5050")
        except ValueError:
            self.err.configure(text="Invalid port")
            return
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()

        def worker() -> None:
            client = ChatClient(host, port)

            def enqueue_msg(m: dict) -> None:
                self._ui_queue.put(("msg", dict(m)))

            def enqueue_err(e: str) -> None:
                self._ui_queue.put(("err", str(e)))

            client.on_message = enqueue_msg
            client.on_error = enqueue_err
            if not client.connect():
                self._ui_queue.put(("err", "Cannot connect to server"))
                return
            self._ui_queue.put(("connected", client))
            client.login(username, password)

        threading.Thread(target=worker, daemon=True).start()

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                kind, payload = self._ui_queue.get_nowait()
                if kind == "connected":
                    self.client = payload  # type: ignore[assignment]
                elif kind == "msg":
                    self._on_msg_ui(payload)  # type: ignore[arg-type]
                elif kind == "err":
                    self._on_client_error_ui(str(payload))
        except queue.Empty:
            pass
        if self._dashboard_ready:
            self._maybe_refresh_server_log()
        self.after(80, self._drain_ui_queue)

    def _on_window_close(self) -> None:
        try:
            if self.client and getattr(self.client, "running", False):
                self.client.disconnect("window closed")
        except Exception:
            pass
        self.client = None
        self.destroy()

    def _on_client_error_ui(self, error_text: str) -> None:
        if self._dashboard_ready and hasattr(self, "session_log"):
            self._append_session(f"[ERROR] {error_text}")
        elif hasattr(self, "err"):
            self.err.configure(text=error_text)

    def _on_msg_ui(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "auth_fail":
            if hasattr(self, "err"):
                self.err.configure(text=msg.get("content", "Login failed"))
            if self.client:
                self.client.disconnect("auth failed")
                self.client = None
            return
        if t == "auth_ok":
            if msg.get("role") not in ("admin", "moderator"):
                if hasattr(self, "err"):
                    self.err.configure(text="Account must be Admin or Moderator.")
                if self.client:
                    self.client.disconnect("not staff")
                    self.client = None
                return
            self._build_dashboard()
            self._request_stats()
            self._append_session("Dashboard connected.")
            return
        if t == "error":
            if self._dashboard_ready:
                self._append_session(f"[SERVER] {msg.get('content', '')}")
            return
        if t == "server_msg":
            content = msg.get("content", "")
            if isinstance(content, str) and content.startswith("{"):
                try:
                    stats = json.loads(content)
                    self._apply_stats(stats)
                except Exception:
                    pass
                return
            if self._dashboard_ready:
                self._append_session(f"[{msg.get('timestamp', '')}] {msg.get('sender', 'server')}: {content}")
            return
        if not self._dashboard_ready:
            return
        if t == "kick":
            self._append_session(f"[KICK] {msg.get('content', '')}")
            return
        self._append_session(f"[{msg.get('timestamp', '')}] {msg.get('sender', '')} [{t}]: {msg.get('content', '')}")

    def _build_dashboard(self) -> None:
        if self._dashboard_ready:
            return
        self._login_frame.destroy()

        header = ctk.CTkFrame(self, fg_color=U.CARD, corner_radius=0, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        hl = ctk.CTkFrame(header, fg_color="transparent")
        hl.pack(fill="both", expand=True, padx=20, pady=10)
        ctk.CTkLabel(hl, text="DistroChat", font=ctk.CTkFont(size=18, weight="bold"), text_color=U.TEXT).pack(side="left")
        ctk.CTkLabel(hl, text="Control panel", font=self._font_sub, text_color=U.MUTED).pack(side="left", padx=(10, 0))

        self._tabs = ctk.CTkTabview(
            self,
            fg_color=U.BG,
            segmented_button_fg_color=U.CARD,
            segmented_button_selected_color=U.ACCENT,
            segmented_button_selected_hover_color=U.ACCENT_HOVER,
            segmented_button_unselected_color=U.INNER,
            segmented_button_unselected_hover_color=U.BORDER,
            corner_radius=U.CARD_RADIUS_LARGE,
            border_width=U.BORDER_WIDTH,
            border_color=U.BORDER,
        )
        self._tabs.pack(fill="both", expand=True, padx=U.TAB_PAD_X, pady=(0, U.TAB_PAD_X))

        t1 = self._tabs.add("  Live stats  ")
        t2 = self._tabs.add("  Users  ")
        t3 = self._tabs.add("  Logs  ")
        t4 = self._tabs.add("  Broadcast  ")

        self._build_tab_stats(self._tab_shell(t1))
        self._build_tab_users(self._tab_shell(t2))
        self._build_tab_logs(self._tab_shell(t3))
        self._build_tab_broadcast(self._tab_shell(t4))

        self._dashboard_ready = True
        for line in self._pending_logs:
            self._append_session(line)
        self._pending_logs.clear()
        self.after(4000, self._tick_stats)

    def _stat_box(self, parent: ctk.CTkFrame, title: str, row: int, col: int) -> ctk.CTkLabel:
        box = ctk.CTkFrame(parent, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        box.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        parent.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(box, text=title, font=self._font_small, text_color=U.MUTED).pack(anchor="w", padx=14, pady=(12, 4))
        val = ctk.CTkLabel(box, text="—", font=self._font_stat, text_color=U.TEXT)
        val.pack(anchor="w", padx=14, pady=(0, 14))
        return val

    def _build_tab_stats(self, parent: ctk.CTkFrame) -> None:
        wrap = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        grid = ctk.CTkFrame(wrap, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 8))
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1)

        self.online_label = self._stat_box(grid, "Online now", 0, 0)
        self.uptime_label = self._stat_box(grid, "Server uptime", 0, 1)
        self.mpm_label = self._stat_box(grid, "Messages / min", 0, 2)

        db_card = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        db_card.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(db_card, text="Database", font=self._font_sub, text_color=U.MUTED).pack(anchor="w", padx=14, pady=(12, 4))
        self.dbstats_label = ctk.CTkLabel(
            db_card,
            text="—",
            font=self._font_small,
            text_color=U.TEXT,
            justify="left",
            anchor="w",
        )
        self.dbstats_label.pack(fill="x", padx=14, pady=(0, 14))

        rooms_card = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        rooms_card.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(rooms_card, text="Room activity", font=self._font_sub, text_color=U.MUTED).pack(anchor="w", padx=14, pady=(12, 4))
        self.rooms_label = ctk.CTkLabel(
            rooms_card,
            text="—",
            font=self._font_small,
            text_color=U.TEXT,
            justify="left",
            anchor="w",
        )
        self.rooms_label.pack(fill="x", padx=14, pady=(0, 14))

        chart_card = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        chart_card.pack(fill="both", expand=True, pady=(0, 8))
        ctk.CTkLabel(chart_card, text="Message rate (recent samples)", font=self._font_sub, text_color=U.MUTED).pack(anchor="w", padx=14, pady=(12, 6))

        fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=U.CARD)
        self.ax = fig.add_subplot(111, facecolor=U.INNER)
        self.ax.tick_params(colors=U.MUTED)
        self.ax.set_title("", color=U.TEXT)
        self.ax.set_xlabel("Sample", color=U.MUTED, fontsize=9)
        self.ax.set_ylabel("Count", color=U.MUTED, fontsize=9)
        self.ax.set_ylim(0, 10)
        self.ax.spines["bottom"].set_color(U.BORDER)
        self.ax.spines["top"].set_color(U.BORDER)
        self.ax.spines["left"].set_color(U.BORDER)
        self.ax.spines["right"].set_color(U.BORDER)
        inner_chart = ctk.CTkFrame(chart_card, fg_color="transparent")
        inner_chart.pack(fill="both", expand=True, padx=8, pady=(0, 12))
        self.canvas = FigureCanvasTkAgg(fig, master=inner_chart)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_tab_users(self, parent: ctk.CTkFrame) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        bar = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        bar.pack(fill="x", pady=(0, 10))
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(inner, text="Online users", font=self._font_sub, text_color=U.TEXT).pack(side="left", padx=(0, 16))
        self.search_var = tk.StringVar()
        search = ctk.CTkEntry(inner, textvariable=self.search_var, placeholder_text="Search by username…", height=36, width=280)
        search.pack(side="left", padx=(0, 10))
        search.bind("<KeyRelease>", self._filter_user_table)
        ctk.CTkButton(inner, text="Refresh", width=100, height=36, command=self._request_stats).pack(side="right")

        table_shell = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        table_shell.pack(fill="both", expand=True, pady=(0, 10))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Admin.Treeview",
            background=U.INNER,
            fieldbackground=U.INNER,
            foreground=U.TEXT,
            rowheight=28,
        )
        style.configure("Admin.Treeview.Heading", background=U.CARD, foreground=U.TEXT, font=("Segoe UI", 10, "bold"))
        style.map("Admin.Treeview", background=[("selected", U.LIST_SELECT)])

        cols = ("username", "role", "ip", "room", "join_time")
        self.user_table = ttk.Treeview(table_shell, columns=cols, show="headings", style="Admin.Treeview", height=16)
        self.user_table.heading("username", text="Username")
        self.user_table.heading("role", text="Role")
        self.user_table.heading("ip", text="IP")
        self.user_table.heading("room", text="Room")
        self.user_table.heading("join_time", text="Connected at")
        self.user_table.column("username", width=150)
        self.user_table.column("role", width=110)
        self.user_table.column("ip", width=140)
        self.user_table.column("room", width=130)
        self.user_table.column("join_time", width=180)
        vsb = ttk.Scrollbar(table_shell, orient="vertical", command=self.user_table.yview)
        self.user_table.configure(yscrollcommand=vsb.set)
        self.user_table.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", pady=10, padx=(0, 10))

        actions = ctk.CTkFrame(wrap, fg_color="transparent")
        actions.pack(fill="x")
        ctk.CTkButton(
            actions,
            text="Kick",
            width=100,
            height=38,
            fg_color=U.BTN_SECONDARY,
            hover_color=U.BTN_SECONDARY_HOVER,
            command=lambda: self._act("/kick"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Ban",
            width=100,
            height=38,
            fg_color=U.BAN_BG,
            hover_color=U.BAN_HOVER,
            command=lambda: self._act("/ban"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Unban",
            width=110,
            height=38,
            fg_color=U.BTN_SECONDARY,
            hover_color=U.BTN_SECONDARY_HOVER,
            command=lambda: self._act("/unban"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Mute…",
            width=100,
            height=38,
            fg_color=U.BTN_SECONDARY,
            hover_color=U.BTN_SECONDARY_HOVER,
            command=self._act_mute_dialog,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Promote mod",
            width=120,
            height=38,
            fg_color=U.PROMOTE_BG,
            hover_color=U.PROMOTE_HOVER,
            command=lambda: self._act("/promote"),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            actions,
            text="Select a row, then an action. Ban / Promote require Admin.",
            font=self._font_small,
            text_color=U.MUTED,
        ).pack(side="left", padx=(16, 0))

    def _build_tab_logs(self, parent: ctk.CTkFrame) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        toolbar = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        toolbar.pack(fill="x", pady=(0, 10))
        tb = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(tb, text="Log level", font=self._font_small, text_color=U.MUTED).pack(side="left", padx=(0, 8))
        self.level_var = tk.StringVar(value="ALL")
        ctk.CTkOptionMenu(
            tb,
            variable=self.level_var,
            values=["ALL", "INFO", "WARNING", "ERROR"],
            width=140,
            height=34,
            command=lambda _v: self._on_log_level_change(),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            tb,
            text="Reload file",
            width=140,
            height=34,
            fg_color=U.BTN_SECONDARY,
            hover_color=U.BTN_SECONDARY_HOVER,
            command=self._force_reload_log,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            tb,
            text="Export view",
            width=120,
            height=34,
            fg_color=U.BTN_SECONDARY,
            hover_color=U.BTN_SECONDARY_HOVER,
            command=self._export_logs,
        ).pack(side="left")

        file_card = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        file_card.pack(fill="both", expand=True, pady=(0, 10))
        ctk.CTkLabel(
            file_card,
            text=f"Server log file: {self._log_path}",
            font=self._font_small,
            text_color=U.MUTED,
        ).pack(anchor="w", padx=14, pady=(12, 6))
        self.log_text = tk.Text(
            file_card,
            bg=U.INNER,
            fg=U.TEXT,
            wrap="word",
            font=U.FONT_LOG,
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 12))
        self.log_text.tag_configure("log_info", foreground=U.TEXT)
        self.log_text.tag_configure("log_warn", foreground="#fbbf24")
        self.log_text.tag_configure("log_error", foreground="#f87171")

        sess_card = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        sess_card.pack(fill="x")
        ctk.CTkLabel(sess_card, text="Admin session (commands & replies)", font=self._font_sub, text_color=U.MUTED).pack(anchor="w", padx=14, pady=(10, 6))
        self.session_log = ctk.CTkTextbox(sess_card, height=120, font=self._font_small, fg_color=U.INNER, text_color=U.TEXT)
        self.session_log.pack(fill="x", padx=10, pady=(0, 12))

    def _build_tab_broadcast(self, parent: ctk.CTkFrame) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        card = ctk.CTkFrame(wrap, fg_color=U.CARD, corner_radius=U.CARD_RADIUS, border_width=U.BORDER_WIDTH, border_color=U.BORDER)
        card.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(inner, text="Message to everyone or one room", font=self._font_sub, text_color=U.TEXT).pack(anchor="w", pady=(0, 8))
        self.broadcast_text = ctk.CTkTextbox(inner, height=200, font=self._font_small, fg_color=U.INNER, text_color=U.TEXT)
        self.broadcast_text.pack(fill="both", expand=True, pady=(0, 16))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(row, text="Target", font=self._font_small, text_color=U.MUTED).pack(side="left", padx=(0, 12))
        self.target_var = tk.StringVar(value="All")
        self._broadcast_rooms = ["All", "#general", "#random", "#announcements"]
        self.room_menu = ctk.CTkOptionMenu(row, variable=self.target_var, values=self._broadcast_rooms, width=260, height=36)
        self.room_menu.pack(side="left")

        ctk.CTkButton(
            inner,
            text="Send broadcast",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=U.SUCCESS,
            hover_color=U.SUCCESS_HOVER,
            command=self._broadcast,
        ).pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            inner,
            text="All — server-wide announcement. Specific room — posts as chat in that room.",
            font=self._font_small,
            text_color=U.MUTED,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

    def _tick_stats(self) -> None:
        if not self._dashboard_ready:
            return
        if self.client and getattr(self.client, "running", False):
            self.client.send_command("/stats")
        self.after(4000, self._tick_stats)

    def _append_session(self, line: str) -> None:
        if not self._dashboard_ready or not hasattr(self, "session_log"):
            self._pending_logs.append(line)
            return
        self.session_log.insert("end", line + "\n")
        self.session_log.see("end")

    @staticmethod
    def _log_tag_for_line(line: str) -> str:
        upper = line.upper()
        if "ERROR" in upper or "[ERROR]" in upper:
            return "log_error"
        if "WARNING" in upper or "WARN" in upper:
            return "log_warn"
        return "log_info"

    def _request_stats(self) -> None:
        if self.client and getattr(self.client, "running", False):
            self.client.send_command("/stats")

    def _apply_stats(self, stats: dict) -> None:
        if not self._dashboard_ready:
            return
        online = int(stats.get("online_users", 0))
        mpm = float(stats.get("messages_per_minute", 0))
        rooms = stats.get("room_activity") or {}
        dbs = stats.get("db_stats") or {}

        self.online_label.configure(text=str(online))
        self.mpm_label.configure(text=f"{mpm:.0f}")
        if isinstance(rooms, dict) and rooms:
            pretty = "  ·  ".join(f"{k}: {v}" for k, v in sorted(rooms.items()))
            self.rooms_label.configure(text=pretty)
        else:
            self.rooms_label.configure(text="No room activity yet")

        up = stats.get("uptime_seconds")
        if up is not None:
            s = int(up)
            h, r = divmod(s, 3600)
            m, sec = divmod(r, 60)
            self.uptime_label.configure(text=f"{h}h {m}m {sec}s")

        self.dbstats_label.configure(
            text=f"Users: {dbs.get('total_users', '—')}   "
            f"Messages: {dbs.get('total_messages', '—')}   "
            f"Rooms: {dbs.get('total_rooms', '—')}   "
            f"Banned: {dbs.get('banned_users', '—')}"
        )

        self.stats_points.append(mpm)
        series = list(self.stats_points)
        self.ax.clear()
        self.ax.set_facecolor(U.INNER)
        self.ax.fill_between(range(len(series)), series, alpha=0.25, color=U.SUCCESS)
        self.ax.plot(range(len(series)), series, color=U.SUCCESS, linewidth=2.2)
        self.ax.tick_params(colors=U.MUTED)
        self.ax.set_xlabel("Sample", color=U.MUTED, fontsize=9)
        self.ax.set_ylabel("Count", color=U.MUTED, fontsize=9)
        for spine in self.ax.spines.values():
            spine.set_color(U.BORDER)
        ymax = max(series) if series else 0.0
        self.ax.set_ylim(0, max(5.0, ymax * 1.2 + 1.0))
        self.canvas.draw()

        users = list(stats.get("users") or [])
        self._cached_users = users
        room_names = ["All"] + sorted(
            {str(u.get("room", "#general")) for u in users} | set(rooms.keys()) | set(self._broadcast_rooms[1:])
        )
        self._broadcast_rooms = room_names
        cur_target = self.target_var.get()
        if cur_target not in self._broadcast_rooms:
            self.target_var.set("All")
        try:
            self.room_menu.configure(values=self._broadcast_rooms)
        except Exception:
            pass
        self._filter_user_table()

    def _filter_user_table(self, _event: object | None = None) -> None:
        if not hasattr(self, "user_table"):
            return
        q = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        for row in self.user_table.get_children():
            self.user_table.delete(row)
        for u in self._cached_users:
            uname = str(u.get("username", ""))
            if q and q not in uname.lower():
                continue
            self.user_table.insert(
                "",
                tk.END,
                values=(
                    uname,
                    u.get("role", "user"),
                    u.get("ip", ""),
                    u.get("room", ""),
                    u.get("join_time", ""),
                ),
            )

    def _selected_username(self) -> str:
        sel = self.user_table.selection()
        if not sel:
            return ""
        vals = self.user_table.item(sel[0]).get("values") or ()
        return str(vals[0]) if vals else ""

    def _act(self, cmd: str) -> None:
        user = self._selected_username()
        if not user:
            self._append_session("Select a user in the table first.")
            return
        if self.client and getattr(self.client, "running", False):
            if cmd == "/ban":
                reason = simpledialog.askstring("Ban", f"Reason for banning {user}?", parent=self) or "No reason"
                self.client.send_command(f"/ban {user} {reason}")
            elif cmd == "/unban":
                self.client.send_command(f"/unban {user}")
            else:
                self.client.send_command(f"{cmd} {user}")

    def _act_mute_dialog(self) -> None:
        user = self._selected_username()
        if not user:
            self._append_session("Select a user in the table first.")
            return
        sec = simpledialog.askinteger("Mute", f"Mute {user} for how many seconds?", parent=self, minvalue=1, maxvalue=86400)
        if sec and self.client and getattr(self.client, "running", False):
            self.client.send_command(f"/mute {user} {int(sec)}")

    def _broadcast(self) -> None:
        text = self.broadcast_text.get("1.0", tk.END).strip()
        if not text or not self.client or not getattr(self.client, "running", False):
            return
        target = self.target_var.get()
        if target == "All":
            self.client.send_command(f"/broadcast {text}")
        else:
            self.client.send_chat(f"[Admin] {text}", room=target)
        self._append_session(f"Sent to {target}")

    def _export_logs(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path or not hasattr(self, "log_text"):
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.log_text.get("1.0", tk.END))

    def _force_reload_log(self) -> None:
        self._last_log_snapshot = ""
        self._last_log_mtime = 0.0
        self._maybe_refresh_server_log(force=True)

    def _on_log_level_change(self) -> None:
        self._last_log_mtime = 0.0
        self._maybe_refresh_server_log(force=True)

    def _maybe_refresh_server_log(self, force: bool = False) -> None:
        if not self._dashboard_ready or not hasattr(self, "log_text"):
            return
        now = time.time()
        if not force and (now - self._last_log_poll) < 2.0:
            return
        self._last_log_poll = now
        path = self._log_path
        if not os.path.isfile(path):
            if force or not self._log_missing_notice_shown:
                self._log_missing_notice_shown = True
                self.log_text.configure(state="normal")
                self.log_text.delete("1.0", tk.END)
                self.log_text.insert("1.0", f"(No log file yet. Expected path:\n{path})\n", "log_info")
                self.log_text.configure(state="disabled")
            return
        self._log_missing_notice_shown = False
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return
        if not force and mtime == self._last_log_mtime:
            return
        self._last_log_mtime = mtime
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return
        if text == self._last_log_snapshot and not force:
            return
        self._last_log_snapshot = text
        lines = text.splitlines()
        tail = lines[-800:] if len(lines) > 800 else lines
        level = self.level_var.get() if hasattr(self, "level_var") else "ALL"
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        for line in tail:
            if level == "INFO" and "INFO" not in line.upper():
                continue
            if level == "WARNING" and "WARNING" not in line.upper() and "WARN" not in line.upper():
                continue
            if level == "ERROR" and "ERROR" not in line.upper():
                continue
            self.log_text.insert(tk.END, line + "\n", (self._log_tag_for_line(line),))
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")


def main() -> None:
    app = AdminDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
