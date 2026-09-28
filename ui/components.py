"""UI Component library containing Chat Bubbles, Metric Cards, Status Badges, and Safety Confirmation Dialogs."""
import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable

# Color Palette Design Tokens
THEME = {
    "bg_dark": "#0e1117",
    "card_bg": "#161b22",
    "card_border": "#30363d",
    "accent_primary": "#238636",      # Emerald Green
    "accent_blue": "#2f81f7",         # Cyber Blue
    "accent_purple": "#8957e5",       # ReAct Thought Purple
    "accent_orange": "#d29922",       # Tool Action Amber
    "accent_red": "#da3633",          # Danger / High Risk
    "text_main": "#e6edf3",
    "text_muted": "#8b949e",
    "user_bubble": "#1f6feb",
    "agent_bubble": "#161b22",
    "tool_bubble": "#0d1117"
}

class StatusBadge(ctk.CTkFrame):
    """Pill badge showing current ReAct state with color-coded dot."""

    def __init__(self, master, initial_status: str = "Idle", **kwargs):
        super().__init__(master, fg_color=THEME["card_bg"], corner_radius=15, border_width=1, border_color=THEME["card_border"], **kwargs)
        
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2ea043"
        )
        self.dot.pack(side="left", padx=(10, 4), pady=4)
        
        self.label = ctk.CTkLabel(
            self,
            text=initial_status,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["text_main"]
        )
        self.label.pack(side="left", padx=(0, 12), pady=4)

    def set_status(self, status: str):
        """Updates the status badge text and color indicator."""
        self.label.configure(text=status)
        s_lower = status.lower()
        if "thinking" in s_lower:
            self.dot.configure(text_color=THEME["accent_purple"])
        elif "executing" in s_lower or "tool" in s_lower:
            self.dot.configure(text_color=THEME["accent_orange"])
        elif "self-healing" in s_lower:
            self.dot.configure(text_color="#e36209")
        elif "listening" in s_lower or "voice" in s_lower:
            self.dot.configure(text_color=THEME["accent_blue"])
        elif "error" in s_lower or "blocked" in s_lower:
            self.dot.configure(text_color=THEME["accent_red"])
        else:
            self.dot.configure(text_color="#2ea043")


class MetricCard(ctk.CTkFrame):
    """Visual telemetry card showing system resource usage with progress bar."""

    def __init__(self, master, title: str, unit: str = "%", icon: str = "⚡", **kwargs):
        super().__init__(
            master,
            fg_color=THEME["card_bg"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["card_border"],
            **kwargs
        )
        self.unit = unit

        # Header
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=12, pady=(8, 2))

        self.icon_label = ctk.CTkLabel(
            top_frame,
            text=icon,
            font=ctk.CTkFont(size=14)
        )
        self.icon_label.pack(side="left", padx=(0, 6))

        self.title_label = ctk.CTkLabel(
            top_frame,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["text_muted"]
        )
        self.title_label.pack(side="left")

        # Value
        self.value_label = ctk.CTkLabel(
            self,
            text=f"-- {unit}",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=THEME["text_main"]
        )
        self.value_label.pack(anchor="w", padx=14, pady=(0, 4))

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            fg_color="#21262d",
            progress_color=THEME["accent_blue"]
        )
        self.progress.pack(fill="x", padx=12, pady=(0, 10))
        self.progress.set(0.0)

    def update_value(self, value: float, custom_text: Optional[str] = None):
        """Updates numeric value and progress visualization."""
        val_clamped = max(0.0, min(100.0, float(value)))
        self.progress.set(val_clamped / 100.0)

        display_str = custom_text or f"{val_clamped:.1f} {self.unit}"
        self.value_label.configure(text=display_str)

        # Dynamic color alerting
        if val_clamped > 85:
            self.progress.configure(progress_color=THEME["accent_red"])
        elif val_clamped > 65:
            self.progress.configure(progress_color=THEME["accent_orange"])
        else:
            self.progress.configure(progress_color=THEME["accent_blue"])


class ChatBubble(ctk.CTkFrame):
    """Threaded chat bubble with avatar, timestamp, role badge, and content."""

    def __init__(self, master, role: str, message: str, meta: Optional[str] = None, **kwargs):
        role_type = role.lower()
        
        # Color & alignment configurations
        if role_type == "user":
            fg_color = THEME["user_bubble"]
            border_color = "#388bfd"
            align_anchor = "e"
            sender_name = "You (User)"
            avatar = "👤"
        elif role_type == "thought":
            fg_color = "#1f1d2b"
            border_color = THEME["accent_purple"]
            align_anchor = "w"
            sender_name = "Agent (Reasoning Thought)"
            avatar = "🧠"
        elif role_type == "tool":
            fg_color = THEME["tool_bubble"]
            border_color = THEME["accent_orange"]
            align_anchor = "w"
            sender_name = "Tool Execution"
            avatar = "⚙️"
        elif role_type == "observation":
            fg_color = "#121d17"
            border_color = "#238636"
            align_anchor = "w"
            sender_name = "Tool Observation"
            avatar = "🔬"
        else: # Agent Final Response
            fg_color = THEME["agent_bubble"]
            border_color = THEME["card_border"]
            align_anchor = "w"
            sender_name = "Agentic AI"
            avatar = "🤖"

        super().__init__(
            master,
            fg_color=fg_color,
            corner_radius=12,
            border_width=1,
            border_color=border_color,
            **kwargs
        )

        # Bubble Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        header_label = ctk.CTkLabel(
            header,
            text=f"{avatar}  {sender_name}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=THEME["text_muted"] if role_type != "user" else "#d0e2ff"
        )
        header_label.pack(side="left")

        if meta:
            meta_label = ctk.CTkLabel(
                header,
                text=meta,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=THEME["text_muted"]
            )
            meta_label.pack(side="right")

        # Message Text
        font_family = "Consolas" if role_type in ["tool", "observation"] else "Segoe UI"
        self.msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(family=font_family, size=13),
            text_color=THEME["text_main"],
            wraplength=620,
            justify="left"
        )
        self.msg_label.pack(anchor="w", padx=12, pady=(2, 10))


class SafetyConfirmationDialog(ctk.CTkToplevel):
    """Modal confirmation dialog for human-in-the-loop authorization of risky actions."""

    def __init__(self, parent, action_name: str, explanation: str, risk_level: str, callback: Callable[[bool], None]):
        super().__init__(parent)
        self.callback = callback
        self.result = False

        self.title("🛡️ Safety Guardrail Confirmation")
        self.geometry("500x300")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_dark"])

        # Center dialog on parent
        self.transient(parent)
        self.grab_set()

        # Header Warning
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 10))

        warn_icon = ctk.CTkLabel(title_frame, text="⚠️", font=ctk.CTkFont(size=24))
        warn_icon.pack(side="left", padx=(0, 10))

        title_lbl = ctk.CTkLabel(
            title_frame,
            text="Action Requires Approval",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=THEME["text_main"]
        )
        title_lbl.pack(side="left")

        # Risk badge
        risk_color = THEME["accent_red"] if "HIGH" in risk_level or "CRITICAL" in risk_level else THEME["accent_orange"]
        risk_badge = ctk.CTkLabel(
            self,
            text=f"RISK LEVEL: {risk_level}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=risk_color,
            fg_color="#21262d",
            corner_radius=6
        )
        risk_badge.pack(anchor="w", padx=20, pady=(0, 10))

        # Details Box
        detail_box = ctk.CTkTextbox(
            self,
            height=100,
            fg_color=THEME["card_bg"],
            border_width=1,
            border_color=THEME["card_border"],
            text_color=THEME["text_main"],
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        detail_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        detail_box.insert("1.0", f"Action: {action_name}\n\nDetails:\n{explanation}")
        detail_box.configure(state="disabled")

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        deny_btn = ctk.CTkButton(
            btn_frame,
            text="Deny & Block",
            fg_color="#21262d",
            hover_color=THEME["accent_red"],
            text_color="#f85149",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_deny
        )
        deny_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        allow_btn = ctk.CTkButton(
            btn_frame,
            text="Approve & Execute",
            fg_color=THEME["accent_blue"],
            hover_color="#388bfd",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_allow
        )
        allow_btn.pack(side="right", expand=True, fill="x", padx=(10, 0))

    def _on_allow(self):
        self.result = True
        self.callback(True)
        self.destroy()

    def _on_deny(self):
        self.result = False
        self.callback(False)
        self.destroy()
