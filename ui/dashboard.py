"""Main CustomTkinter Dashboard Application for Agentic AI Desktop Assistant."""
import os
import queue
import threading
import time
import datetime
import json
import customtkinter as ctk
from typing import Optional

from core.agent_brain import ReActAgentBrain
from core.memory_manager import MemoryManager
from core.safety_guard import SafetyGuard, ActionRiskLevel
from voice.voice_engine import VoiceEngine
from ui.components import StatusBadge, MetricCard, ChatBubble, SafetyConfirmationDialog, THEME

# Set CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AgentDashboardApp(ctk.CTk):
    """Modern Desktop AI Assistant UI with asynchronous ReAct engine & voice integration."""

    def __init__(self):
        super().__init__()

        self.title("Agentic AI Desktop Workstation")
        self.geometry("1100x780")
        self.minsize(900, 650)
        self.configure(fg_color=THEME["bg_dark"])

        # Thread-safe queues
        self.ui_queue = queue.Queue()
        self.is_processing = False

        # Initialize Subsystems
        self.memory = MemoryManager()
        self.safety = SafetyGuard(confirmation_callback=self._gui_safety_prompt)
        self.agent = ReActAgentBrain(
            memory_manager=self.memory,
            safety_guard=self.safety,
            on_step_callback=self._on_agent_step
        )
        self.voice = VoiceEngine(
            on_speech_recognized=self._on_speech_input,
            on_status_change=self._on_voice_status
        )

        # Build Interface
        self._create_header()
        self._create_telemetry_bar()
        self._create_chat_area()
        self._create_control_panel()

        # Start background polling & telemetry
        self.after(100, self._process_ui_queue)
        self._start_telemetry_loop()

        # Welcome message
        self._add_chat_bubble(
            "agent",
            "👋 **Welcome to Agentic AI Workstation!**\n\nI am your autonomous desktop copilot. I can organize files, run diagnostic benchmarks, execute self-healing Python scripts, conduct web research, and perform security audits.\n\n*Type a prompt below or click the microphone to speak.*"
        )

    def _create_header(self):
        """Builds top status bar and branding."""
        header_frame = ctk.CTkFrame(self, fg_color=THEME["card_bg"], height=60, corner_radius=0, border_width=1, border_color=THEME["card_border"])
        header_frame.pack(fill="x", side="top")

        # Brand / Title
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        logo_lbl = ctk.CTkLabel(title_box, text="⚡", font=ctk.CTkFont(size=22))
        logo_lbl.pack(side="left", padx=(0, 8))

        brand_lbl = ctk.CTkLabel(
            title_box,
            text="AGENTIC AI",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=THEME["text_main"]
        )
        brand_lbl.pack(side="left")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text="Autonomous Desktop Copilot",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=THEME["text_muted"]
        )
        sub_lbl.pack(side="left", padx=(10, 0))

        # Right status area
        status_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_box.pack(side="right", padx=20, pady=12)

        # Voice Toggle
        self.voice_btn = ctk.CTkButton(
            status_box,
            text="🎤 Voice Input",
            width=110,
            height=32,
            fg_color="#21262d",
            hover_color=THEME["accent_blue"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle_voice_capture
        )
        self.voice_btn.pack(side="right", padx=(10, 0))

        # ReAct Status Badge
        self.status_badge = StatusBadge(status_box, initial_status="Idle")
        self.status_badge.pack(side="right")

    def _create_telemetry_bar(self):
        """Displays live hardware and diagnostic metric cards."""
        telemetry_frame = ctk.CTkFrame(self, fg_color="transparent", height=90)
        telemetry_frame.pack(fill="x", padx=20, pady=(15, 5))
        telemetry_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="metric_group")

        self.cpu_card = MetricCard(telemetry_frame, title="CPU LOAD", unit="%", icon="💻")
        self.cpu_card.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.ram_card = MetricCard(telemetry_frame, title="MEMORY USAGE", unit="%", icon="🧠")
        self.ram_card.grid(row=0, column=1, padx=4, sticky="ew")

        self.disk_card = MetricCard(telemetry_frame, title="SYSTEM DISK", unit="%", icon="💾")
        self.disk_card.grid(row=0, column=2, padx=4, sticky="ew")

        self.battery_card = MetricCard(telemetry_frame, title="POWER / BATTERY", unit="%", icon="🔋")
        self.battery_card.grid(row=0, column=3, padx=(8, 0), sticky="ew")

    def _create_chat_area(self):
        """Creates threaded, scrollable conversation view."""
        self.chat_container = ctk.CTkScrollableFrame(
            self,
            fg_color=THEME["bg_dark"],
            corner_radius=0
        )
        self.chat_container.pack(fill="both", expand=True, padx=20, pady=10)

    def _create_control_panel(self):
        """Creates input bar, quick actions, and send buttons."""
        bottom_frame = ctk.CTkFrame(self, fg_color=THEME["card_bg"], corner_radius=12, border_width=1, border_color=THEME["card_border"])
        bottom_frame.pack(fill="x", padx=20, pady=(0, 18))

        # Quick action pills
        quick_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        quick_frame.pack(fill="x", padx=14, pady=(10, 6))

        quick_actions = [
            ("🔮 Laptop Lifespan", "Mera laptop kitna saal chalega? Deep hardware health prediction do"),
            ("⚡ Speed Benchmark", "Benchmark my computer compute power and memory speed"),
            ("🛡️ Vulnerability Audit", "Scan local system vulnerabilities and open port exposure"),
            ("📱 QR Generator", "Generate QR code for https://google.com"),
            ("🌤️ Weather Report", "Delhi ka live weather report batao"),
            ("💱 100 USD to INR", "Convert 100 USD to INR"),
            ("✍️ Draft Leave Email", "Draft a sick leave email for my manager"),
            ("📋 My Todo Tasks", "Show my todo task list"),
            ("📊 System Health", "Show system health and top memory consumers"),
            ("🧹 Clean Disk Scan", "Scan temporary files to reclaim storage"),
            ("🧹 Clear Chat", "__ACTION_CLEAR__")
        ]

        for label, prompt in quick_actions:
            btn = ctk.CTkButton(
                quick_frame,
                text=label,
                height=26,
                fg_color="#21262d",
                hover_color="#30363d",
                text_color=THEME["text_muted"],
                font=ctk.CTkFont(size=11),
                command=lambda p=prompt: self._on_quick_action(p)
            )
            btn.pack(side="left", padx=(0, 6))

        # Input Row
        input_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(4, 12))

        self.entry_box = ctk.CTkEntry(
            input_row,
            placeholder_text="Ask Agentic AI to organize files, diagnose system, audit security, run scripts...",
            height=44,
            fg_color="#0d1117",
            border_width=1,
            border_color=THEME["card_border"],
            text_color=THEME["text_main"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.entry_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_box.bind("<Return>", lambda event: self._send_user_message())

        self.send_btn = ctk.CTkButton(
            input_row,
            text="Send ➔",
            width=90,
            height=44,
            fg_color=THEME["accent_blue"],
            hover_color="#388bfd",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._send_user_message
        )
        self.send_btn.pack(side="right")

    def _start_telemetry_loop(self):
        """Spawns background telemetry updater."""
        def _telemetry_worker():
            import psutil
            while True:
                try:
                    cpu_p = psutil.cpu_percent(interval=1.0)
                    ram = psutil.virtual_memory()
                    disk = psutil.disk_usage("/")
                    battery = psutil.sensors_battery()
                    
                    batt_pct = battery.percent if battery else 100.0
                    batt_txt = f"{batt_pct:.0f}% {'⚡' if (battery and battery.power_plugged) else '🔋'}" if battery else "AC Power"

                    self.ui_queue.put({
                        "type": "telemetry",
                        "cpu": cpu_p,
                        "ram": ram.percent,
                        "ram_txt": f"{ram.percent:.1f}% ({round(ram.used/(1024**3), 1)}GB)",
                        "disk": disk.percent,
                        "disk_txt": f"{disk.percent:.1f}% ({round(disk.used/(1024**3), 1)}GB)",
                        "battery": batt_pct,
                        "battery_txt": batt_txt
                    })
                except Exception:
                    pass
                time.sleep(2.0)

        t = threading.Thread(target=_telemetry_worker, daemon=True)
        t.start()

    def _process_ui_queue(self):
        """Processes queued messages on the main GUI thread."""
        try:
            while not self.ui_queue.empty():
                item = self.ui_queue.get_nowait()
                msg_type = item.get("type")

                if msg_type == "telemetry":
                    self.cpu_card.update_value(item["cpu"])
                    self.ram_card.update_value(item["ram"], custom_text=item["ram_txt"])
                    self.disk_card.update_value(item["disk"], custom_text=item["disk_txt"])
                    self.battery_card.update_value(item["battery"], custom_text=item["battery_txt"])

                elif msg_type == "status":
                    self.status_badge.set_status(item["content"])

                elif msg_type == "chat_bubble":
                    self._add_chat_bubble(
                        role=item["role"],
                        message=item["message"],
                        meta=item.get("meta")
                    )

                elif msg_type == "tts":
                    self.voice.speak(item["text"])

                elif msg_type == "speech_input":
                    self.entry_box.delete(0, "end")
                    self.entry_box.insert(0, item["text"])
                    self._send_user_message()

                elif msg_type == "safety_modal":
                    self._open_safety_modal(item)

        except Exception as e:
            print(f"[UI Queue Error] {e}")
        finally:
            self.after(60, self._process_ui_queue)

    def _add_chat_bubble(self, role: str, message: str, meta: Optional[str] = None):
        """Renders a chat bubble in the scrollable view."""
        timestamp = meta or datetime.datetime.now().strftime("%H:%M:%S")
        bubble = ChatBubble(self.chat_container, role=role, message=message, meta=timestamp)
        bubble.pack(fill="x", pady=6, padx=8)

        # Auto-scroll to bottom
        self.chat_container._parent_canvas.yview_moveto(1.0)

    def _on_agent_step(self, step_payload: dict):
        """ReAct engine step callback -> schedules UI updates."""
        step_type = step_payload.get("type")
        content = step_payload.get("content")

        if step_type == "status":
            self.ui_queue.put({"type": "status", "content": str(content)})

        elif step_type == "thought":
            self.ui_queue.put({
                "type": "chat_bubble",
                "role": "thought",
                "message": str(content)
            })

        elif step_type == "tool_call":
            self.ui_queue.put({
                "type": "chat_bubble",
                "role": "tool",
                "message": str(content)
            })

        elif step_type == "observation":
            obs_str = json.dumps(content, indent=2) if isinstance(content, (dict, list)) else str(content)
            self.ui_queue.put({
                "type": "chat_bubble",
                "role": "observation",
                "message": f"```json\n{obs_str}\n```"
            })

        elif step_type == "final_answer":
            self.ui_queue.put({
                "type": "chat_bubble",
                "role": "agent",
                "message": str(content)
            })
            # TTS voice output for final response
            self.ui_queue.put({"type": "tts", "text": str(content)})

    def _gui_safety_prompt(self, action_name: str, explanation: str, risk_level: ActionRiskLevel) -> bool:
        """Thread-safe human-in-the-loop confirmation modal synchronization."""
        sync_event = threading.Event()
        approval_result = [False]

        def _on_decision(allowed: bool):
            approval_result[0] = allowed
            sync_event.set()

        self.ui_queue.put({
            "type": "safety_modal",
            "action_name": action_name,
            "explanation": explanation,
            "risk_level": risk_level.value,
            "callback": _on_decision
        })

        # Wait for user input in modal dialog
        sync_event.wait(timeout=60)
        return approval_result[0]

    def _open_safety_modal(self, modal_data: dict):
        """Displays modal confirmation dialog."""
        SafetyConfirmationDialog(
            parent=self,
            action_name=modal_data["action_name"],
            explanation=modal_data["explanation"],
            risk_level=modal_data["risk_level"],
            callback=modal_data["callback"]
        )

    def _send_user_message(self):
        """Handles submission of user prompt and spawns background ReAct cycle."""
        text = self.entry_box.get().strip()
        if not text or self.is_processing:
            return

        self.entry_box.delete(0, "end")
        self._add_chat_bubble("user", text)

        self.is_processing = True
        self.send_btn.configure(state="disabled")
        self.status_badge.set_status("Thinking")

        def _agent_thread():
            try:
                self.agent.execute_react_cycle(text)
            except Exception as e:
                self.ui_queue.put({
                    "type": "chat_bubble",
                    "role": "agent",
                    "message": f"❌ An unexpected error occurred: {str(e)}"
                })
            finally:
                self.is_processing = False
                self.ui_queue.put({"type": "status", "content": "Idle"})
                self.send_btn.configure(state="normal")

        t = threading.Thread(target=_agent_thread, daemon=True)
        t.start()

    def _on_quick_action(self, prompt: str):
        """Triggers predefined quick actions."""
        if prompt == "__ACTION_CLEAR__":
            for widget in self.chat_container.winfo_children():
                widget.destroy()
            self.memory.clear_history()
            self._add_chat_bubble("agent", "🧹 Conversation history cleared. How may I assist you now?")
            return

        self.entry_box.delete(0, "end")
        self.entry_box.insert(0, prompt)
        self._send_user_message()

    def _toggle_voice_capture(self):
        """Activates speech recognition in background."""
        if self.voice.is_listening:
            return
        self.voice_btn.configure(text="🎙️ Listening...", fg_color=THEME["accent_red"])
        self.status_badge.set_status("Listening...")
        self.voice.start_listening_async()

    def _on_speech_input(self, transcribed_text: str):
        """Callback when voice transcription finishes."""
        self.voice_btn.configure(text="🎤 Voice Input", fg_color="#21262d")
        self.ui_queue.put({"type": "speech_input", "text": transcribed_text})

    def _on_voice_status(self, status: str):
        """Callback for voice calibration/status."""
        self.ui_queue.put({"type": "status", "content": status})
        if "idle" in status.lower() or "timeout" in status.lower():
            self.voice_btn.configure(text="🎤 Voice Input", fg_color="#21262d")
