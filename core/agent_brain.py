"""ReAct Agent Brain: Autonomous reasoning loop, tool router, self-correction, and reflection engine."""
import os
import re
import json
import traceback
from typing import Dict, Any, List, Optional, Callable
from rich.console import Console

from .safety_guard import SafetyGuard, ActionRiskLevel
from .memory_manager import MemoryManager
from tools.general_tools import GeneralTools
from tools.diagnostic_tools import DiagnosticTools
from tools.sandbox_runner import SandboxRunner
from tools.productivity_tools import ProductivityTools

console = Console()

class ReActAgentBrain:
    """
    Autonomous ReAct (Reasoning + Acting) Agent Engine.
    Executes iterative Thought -> Action -> Observation -> Reflection loops with self-correction.
    """

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        safety_guard: Optional[SafetyGuard] = None,
        on_step_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.memory = memory_manager or MemoryManager()
        self.safety = safety_guard or SafetyGuard()
        self.on_step_callback = on_step_callback

        # Initialize tool suites
        self.general_tools = GeneralTools()
        self.diagnostic_tools = DiagnosticTools()
        self.sandbox_runner = SandboxRunner()
        self.productivity_tools = ProductivityTools()

        self._register_tools()

    def _detect_user_language(self, text: str) -> str:
        """Detects language context (Hindi, Hinglish, Spanish, French, German, Bengali, Marathi, etc.)."""
        t_lower = text.lower()
        
        # Hindi / Devanagari script
        if any('\u0900' <= char <= '\u097f' for char in text):
            return "hindi_devanagari"
            
        # Hinglish / Romanized Hindi
        hinglish_keywords = ["kya", "kaise", "batao", "bhejo", "karo", "karna", "hai", "hain", "mera", "meri", "kitna", "saal", "chalega", "likho", "dikhaye", "suno", "namaste", "shukriya"]
        if any(w in t_lower.split() or f" {w} " in f" {t_lower} " for w in hinglish_keywords):
            return "hinglish"

        # Spanish
        if any(w in t_lower.split() for w in ["hola", "como", "esta", "gracias", "por", "favor", "idioma", "hacer"]):
            return "spanish"

        # French
        if any(w in t_lower.split() for w in ["bonjour", "merci", "comment", "faire", "système", "ordinateur"]):
            return "french"

        # German
        if any(w in t_lower.split() for w in ["hallo", "danke", "wie", "geht", "rechner", "bitte"]):
            return "german"

        # Marathi / Bengali romanized hints
        if any(w in t_lower for w in ["kasa ahes", "kay chalale", "kemon acho", "tumi"]):
            return "regional_indian"

        return "english"

    def _register_tools(self):
        """Builds tool registry and schemas."""
        self.tools_registry = {
            # --- General User Automation ---
            "organize_directory": {
                "func": self.general_tools.organize_directory,
                "description": "Scans folder and categorizes loose files into Documents, Images, Archives, Media, Code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_path": {"type": "string", "description": "Absolute or relative path to directory"}
                    },
                    "required": ["target_path"]
                }
            },
            "find_duplicate_files": {
                "func": self.general_tools.find_duplicate_files,
                "description": "Finds duplicate files in a directory using cryptographic hash comparison.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_path": {"type": "string", "description": "Directory path to scan"}
                    },
                    "required": ["target_path"]
                }
            },
            "web_research": {
                "func": self.general_tools.web_research,
                "description": "Searches the web, scrapes and synthesizes key takeaways.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query or topic"},
                        "max_results": {"type": "integer", "description": "Maximum results to fetch", "default": 3}
                    },
                    "required": ["query"]
                }
            },
            "manage_application": {
                "func": self.general_tools.manage_application,
                "description": "Launches or closes specified desktop programs safely (e.g., notepad, calc, chrome).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Executable or application name"},
                        "action": {"type": "string", "description": "'launch' or 'close'"}
                    },
                    "required": ["app_name", "action"]
                }
            },
            "create_quick_note": {
                "func": self.general_tools.create_quick_note,
                "description": "Appends timestamped notes to local storage.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_name": {"type": "string", "description": "Title or topic of note"},
                        "text": {"type": "string", "description": "Content of the note"}
                    },
                    "required": ["note_name", "text"]
                }
            },

            # --- Productivity & Everyday Multimedia ---
            "send_whatsapp_message": {
                "func": self.productivity_tools.send_whatsapp_message,
                "description": "Opens WhatsApp Web or Desktop application with pre-filled recipient phone and message text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {"type": "string", "description": "10-digit or international format phone number (e.g. 9876543210)"},
                        "message": {"type": "string", "description": "Text message payload to send"}
                    },
                    "required": ["phone_number", "message"]
                }
            },
            "compose_or_send_email": {
                "func": self.productivity_tools.compose_or_send_email,
                "description": "Opens default Windows Mail / Outlook client with pre-filled recipient email, subject, and body.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipient_email": {"type": "string", "description": "Target email address (e.g. boss@company.com)"},
                        "subject": {"type": "string", "description": "Email subject title"},
                        "body": {"type": "string", "description": "Full text body of the email"}
                    },
                    "required": ["recipient_email", "subject", "body"]
                }
            },
            "generate_qr_code": {
                "func": self.productivity_tools.generate_qr_code,
                "description": "Generates a high-resolution QR code image for links, WiFi, UPI payments, or texts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "string", "description": "URL or text content to encode"},
                        "filename": {"type": "string", "description": "Output PNG filename"}
                    },
                    "required": ["data"]
                }
            },
            "get_live_weather": {
                "func": self.productivity_tools.get_live_weather,
                "description": "Fetches real-time weather and temperature for any city in the world.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name (e.g. Delhi, London, Tokyo)", "default": "Delhi"}
                    },
                    "required": ["city"]
                }
            },
            "convert_currency_and_units": {
                "func": self.productivity_tools.convert_currency_and_units,
                "description": "Converts currencies (USD, INR, EUR, GBP) and physical units (temp, distance, storage).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number", "description": "Numeric value to convert"},
                        "from_unit": {"type": "string", "description": "Starting unit (e.g. USD, C, MB, KM)"},
                        "to_unit": {"type": "string", "description": "Target unit (e.g. INR, F, GB, MILE)"}
                    },
                    "required": ["value", "from_unit", "to_unit"]
                }
            },
            "manage_todo_tasks": {
                "func": self.productivity_tools.manage_todo_tasks,
                "description": "Manages todo items, tasks, and reminders (add, list, complete, delete).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "'add', 'list', 'complete', 'delete'"},
                        "task_text": {"type": "string", "description": "Task description"},
                        "task_id": {"type": "integer", "description": "ID of task to complete or delete"},
                        "priority": {"type": "string", "description": "'High', 'Medium', 'Low'", "default": "Medium"}
                    },
                    "required": ["action"]
                }
            },
            "draft_email_or_document": {
                "func": self.productivity_tools.draft_email_or_document,
                "description": "Drafts formal emails, leave applications, cover letters, and professional notices.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_type": {"type": "string", "description": "'leave', 'cover_letter', 'formal_email'"},
                        "topic": {"type": "string", "description": "Reason or subject of the document"},
                        "recipient": {"type": "string", "description": "Recipient name or designation"}
                    },
                    "required": ["doc_type", "topic"]
                }
            },
            "read_and_extract_pdf": {
                "func": self.productivity_tools.read_and_extract_pdf,
                "description": "Reads PDF files and extracts text, page count, and document metadata.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pdf_path": {"type": "string", "description": "Path to PDF file"},
                        "max_pages": {"type": "integer", "description": "Max pages to extract", "default": 10}
                    },
                    "required": ["pdf_path"]
                }
            },
            "convert_or_resize_image": {
                "func": self.productivity_tools.convert_or_resize_image,
                "description": "Converts image format (PNG, JPG, WEBP) and resizes dimensions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to image"},
                        "output_format": {"type": "string", "description": "'PNG', 'JPEG', 'WEBP'", "default": "PNG"},
                        "max_width": {"type": "integer", "description": "Max width pixels"},
                        "max_height": {"type": "integer", "description": "Max height pixels"}
                    },
                    "required": ["image_path"]
                }
            },
            "find_large_files": {
                "func": self.productivity_tools.find_large_files,
                "description": "Finds heavy large files (>100MB) to free up storage space.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_dir": {"type": "string", "description": "Directory to scan", "default": "."},
                        "min_size_mb": {"type": "integer", "description": "Minimum size in MB", "default": 100}
                    }
                }
            },
            "clean_temp_storage_scan": {
                "func": self.productivity_tools.clean_temp_storage_scan,
                "description": "Scans temporary files and application cache to calculate reclaimable disk space.",
                "parameters": {"type": "object", "properties": {}}
            },
            "get_news_headlines": {
                "func": self.productivity_tools.get_news_headlines,
                "description": "Fetches current top news headlines from global feeds.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category (e.g. technology, general)", "default": "technology"}
                    }
                }
            },

            # --- Advanced Predictive Diagnostics & Benchmarks ---
            "predict_hardware_lifespan": {
                "func": self.diagnostic_tools.predict_hardware_lifespan,
                "description": "Performs deep multi-factor telemetry analysis on CPU, RAM, Disk, Battery to predict remaining lifespan in years, hardware health index (0-100), and component wear.",
                "parameters": {"type": "object", "properties": {}}
            },
            "audit_system_vulnerabilities": {
                "func": self.diagnostic_tools.audit_system_vulnerabilities,
                "description": "Scans open listening ports, flagged high-risk network sockets, and process counts.",
                "parameters": {"type": "object", "properties": {}}
            },
            "benchmark_system_performance": {
                "func": self.diagnostic_tools.benchmark_system_performance,
                "description": "Runs a real-time CPU floating point & memory throughput stress test to determine system compute tier.",
                "parameters": {"type": "object", "properties": {}}
            },
            "get_system_health": {
                "func": self.diagnostic_tools.get_system_health,
                "description": "Returns live CPU %, RAM %, per-partition disk usage %, battery, and top processes.",
                "parameters": {"type": "object", "properties": {}}
            },
            "inspect_service_reachability": {
                "func": self.diagnostic_tools.inspect_service_reachability,
                "description": "Validates network reachability and open socket states for a host.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "Hostname or IP to test"},
                        "ports": {"type": "array", "items": {"type": "integer"}, "description": "List of ports to probe"}
                    },
                    "required": ["host"]
                }
            },
            "audit_web_headers": {
                "func": self.diagnostic_tools.audit_web_headers,
                "description": "Audits HTTP response headers of a web endpoint for critical security controls (CSP, HSTS, etc).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target website URL"}
                    },
                    "required": ["url"]
                }
            },
            "analyze_system_logs": {
                "func": self.diagnostic_tools.analyze_system_logs,
                "description": "Parses local log file to detect anomalies, error counts, and keyword matches.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_path": {"type": "string", "description": "Path to log file"},
                        "keyword": {"type": "string", "description": "Keyword to filter for", "default": "failed"}
                    },
                    "required": ["log_path"]
                }
            },
            "calculate_file_checksum": {
                "func": self.diagnostic_tools.calculate_file_checksum,
                "description": "Generates cryptographic hashes for file integrity checks (sha256, md5, etc).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Path to target file"},
                        "algo": {"type": "string", "description": "Algorithm: 'sha256', 'md5', 'sha1'", "default": "sha256"}
                    },
                    "required": ["filepath"]
                }
            },

            # --- Isolated Python Sandbox ---
            "execute_python_code": {
                "func": self.sandbox_runner.execute_python_code,
                "description": "Executes isolated Python code, returns stdout/stderr, and enables self-healing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code_string": {"type": "string", "description": "Valid Python code string to execute"}
                    },
                    "required": ["code_string"]
                }
            }
        }

    def emit_step(self, step_type: str, content: Any, metadata: Optional[Dict[str, Any]] = None):
        """Sends progress update to UI callback."""
        payload = {
            "type": step_type,
            "content": content,
            "metadata": metadata or {}
        }
        if self.on_step_callback:
            try:
                self.on_step_callback(payload)
            except Exception as e:
                console.print(f"[bold red][AgentBrain][/bold red] Callback error: {e}")

    def execute_react_cycle(self, user_query: str, max_iterations: int = 5) -> str:
        """
        Main ReAct Loop:
        Thought -> Action -> Safety Check -> Tool Execution -> Observation -> Reflection -> Final Output.
        """
        console.print(f"[bold cyan][AgentBrain][/bold cyan] Processing user goal: '{user_query}'")
        self.emit_step("status", "Thinking", {"goal": user_query})

        # Memory retrieval
        semantic_memories = self.memory.semantic_search(user_query, n_results=2)
        memory_context = ""
        if semantic_memories:
            memory_context = "\n".join([f"- Prior context: {m['document']}" for m in semantic_memories])

        context_history = []
        iteration = 0
        final_answer = ""

        while iteration < max_iterations:
            iteration += 1
            thought, plan = self._reason_next_step(user_query, context_history, memory_context, iteration)
            self.emit_step("thought", thought, {"iteration": iteration})

            if plan.get("action") == "final_answer":
                final_answer = plan.get("answer", thought)
                break

            tool_name = plan.get("tool")
            tool_args = plan.get("arguments", {})

            if not tool_name or tool_name not in self.tools_registry:
                final_answer = thought
                break

            # Safety Guardrail evaluation
            self.emit_step("status", f"Evaluating Safety for {tool_name}", {"tool": tool_name})
            allowed, safety_msg = self.safety.request_permission(tool_name, tool_args)
            if not allowed:
                obs = f"Action '{tool_name}' was blocked by Safety Guardrail: {safety_msg}"
                self.emit_step("observation", obs, {"blocked": True, "tool": tool_name})
                context_history.append({"thought": thought, "tool": tool_name, "args": tool_args, "observation": obs})
                continue

            # Tool Execution
            self.emit_step("status", f"Executing Tool: {tool_name}", {"tool": tool_name, "args": tool_args})
            self.emit_step("tool_call", f"Calling `{tool_name}` with parameters:\n```json\n{json.dumps(tool_args, indent=2)}\n```", {"tool": tool_name})
            
            tool_entry = self.tools_registry[tool_name]
            try:
                raw_observation = tool_entry["func"](**tool_args)
            except Exception as e:
                raw_observation = {"status": "error", "message": f"Execution error: {str(e)}", "traceback": traceback.format_exc()}

            self.emit_step("observation", raw_observation, {"tool": tool_name})
            
            # Self-healing loop trigger
            if tool_name == "execute_python_code" and isinstance(raw_observation, dict) and raw_observation.get("needs_healing"):
                self.emit_step("status", "Self-Healing: Analyzing Traceback", {"error_type": raw_observation.get("error_type")})
                healed_code = self._self_heal_code(raw_observation.get("raw_code", ""), raw_observation.get("stderr", ""))
                self.emit_step("thought", f"Self-Healing Agent detected `{raw_observation.get('error_type')}`. Refactoring code solution...", {"healed_code": healed_code})
                
                retry_obs = self.sandbox_runner.execute_python_code(healed_code)
                self.emit_step("observation", retry_obs, {"tool": tool_name, "self_healed": True})
                raw_observation = {
                    "original_error": raw_observation.get("stderr"),
                    "self_healing_attempt": retry_obs
                }

            context_history.append({
                "thought": thought,
                "tool": tool_name,
                "args": tool_args,
                "observation": raw_observation
            })

        if not final_answer:
            final_answer = self._synthesize_final_response(user_query, context_history)

        self.emit_step("status", "Idle", {})
        self.emit_step("final_answer", final_answer, {})

        # Persist conversation to memory
        self.memory.store_interaction("user", user_query)
        self.memory.store_interaction("agent", final_answer, {"steps_executed": len(context_history)})

        return final_answer

    def _reason_next_step(self, user_query: str, history: List[Dict[str, Any]], memory_context: str, iteration: int) -> tuple[str, Dict[str, Any]]:
        """
        Determines the next thought and tool action.
        Supports multi-lingual (English / Hindi / Hinglish) everyday & technical intent parsing.
        """
        q_lower = user_query.lower()

        # If already gathered observations from tools, synthesize final answer
        if history:
            last_entry = history[-1]
            last_obs = last_entry["observation"]
            thought = f"Received observation from `{last_entry['tool']}`. Formulating final response."
            return thought, {"action": "final_answer", "answer": self._format_observation_response(user_query, last_entry['tool'], last_obs)}

        # 0.3 WhatsApp Message Dispatcher
        if any(w in q_lower for w in ["whatsapp", "wa message", "send whatsapp", "whatsapp bhejo", "whatsapp par message"]):
            # Extract phone number
            phone_match = re.search(r"(\+?\d{10,13})", user_query)
            phone = phone_match.group(1) if phone_match else "919876543210"
            
            # Extract message
            msg_match = re.search(r"['\"](.*?)['\"]", user_query)
            msg = msg_match.group(1) if msg_match else re.sub(r".*?(?:message|msg|text|ko|ke liye)\s*:?\s*", "", user_query, flags=re.IGNORECASE).strip() or "Hello from Agentic AI!"
            
            thought = f"User wants to send WhatsApp message to '{phone}'. Invoking `send_whatsapp_message`."
            return thought, {"tool": "send_whatsapp_message", "arguments": {"phone_number": phone, "message": msg}}

        # 0.4 Direct Email Compose / Mailto Dispatcher
        if any(w in q_lower for w in ["send email to", "email bhejo", "compose email to", "mail bhejo"]):
            email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", user_query)
            email_addr = email_match.group(1) if email_match else "manager@example.com"
            sub = "Important Update from Agentic AI"
            body = f"Hello,\n\nThis message was dispatched via Agentic AI Workstation.\n\nQuery Context: {user_query}\n\nBest regards,\nUser"
            thought = f"User wants to compose and send email to '{email_addr}'. Invoking `compose_or_send_email`."
            return thought, {"tool": "compose_or_send_email", "arguments": {"recipient_email": email_addr, "subject": sub, "body": body}}

        # 0. Predictive Hardware Lifespan & Longevity Analysis
        if any(w in q_lower for w in ["saal chalega", "kitna saal", "lifespan", "life of laptop", "how long will my", "hardware life", "laptop kab tak", "laptop health prediction", "longevity"]):
            thought = "User is requesting deep predictive hardware longevity & remaining lifespan analysis. Invoking `predict_hardware_lifespan`."
            return thought, {"tool": "predict_hardware_lifespan", "arguments": {}}

        # 0.1 Benchmark Performance Tier Stress Test
        if any(w in q_lower for w in ["benchmark", "speed test", "stress test", "performance tier", "compute power", "how fast is my"]):
            thought = "User requested a CPU and memory throughput benchmark. Invoking `benchmark_system_performance`."
            return thought, {"tool": "benchmark_system_performance", "arguments": {}}

        # 0.2 System Vulnerability Scan
        if any(w in q_lower for w in ["vulnerability", "vulnerabilities", "open port risk", "security scan", "safe is my pc"]):
            thought = "User requested a local vulnerability and network exposure scan. Invoking `audit_system_vulnerabilities`."
            return thought, {"tool": "audit_system_vulnerabilities", "arguments": {}}

        # 1. QR Code Generator
        if any(w in q_lower for w in ["qr", "qr code", "generate qr", "make qr", "qr banao"]):
            url_match = re.search(r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*)", user_query)
            data = url_match.group(1) if url_match else re.sub(r"(generate|make|create|banao)?\s*(a\s+)?qr\s*(code)?\s*(for)?", "", user_query, flags=re.IGNORECASE).strip() or "https://google.com"
            thought = f"User wants a QR Code generated for '{data}'. Invoking `generate_qr_code`."
            return thought, {"tool": "generate_qr_code", "arguments": {"data": data}}

        # 2. Weather & Forecast
        if any(w in q_lower for w in ["weather", "forecast", "mausam", "temperature", "temp in", "barish", "garmi"]):
            city_match = re.search(r"(?:in|of|for|ka|me)\s+([a-zA-Z\s]+)", user_query, re.IGNORECASE)
            city = city_match.group(1).strip() if city_match else "Delhi"
            thought = f"User requested weather information for city '{city}'. Invoking `get_live_weather`."
            return thought, {"tool": "get_live_weather", "arguments": {"city": city}}

        # 3. Currency & Unit Conversion
        if any(w in q_lower for w in ["convert", "usd to inr", "dollar in rupee", "inr to usd", "celsius to", "fahrenheit to", "km to", "mb to gb", "gb to mb"]):
            # Extract number
            num_match = re.search(r"(\d+(?:\.\d+)?)", user_query)
            val = float(num_match.group(1)) if num_match else 100.0
            
            f_unit, t_unit = "USD", "INR"
            if "inr" in q_lower and "usd" in q_lower:
                if "inr to usd" in q_lower or "rupee to dollar" in q_lower:
                    f_unit, t_unit = "INR", "USD"
                else:
                    f_unit, t_unit = "USD", "INR"
            elif "celsius" in q_lower or "fahrenheit" in q_lower or "c to f" in q_lower or "f to c" in q_lower:
                f_unit, t_unit = ("C", "F") if "c" in q_lower and "to f" in q_lower else ("F", "C")
            elif "mb" in q_lower or "gb" in q_lower:
                f_unit, t_unit = ("MB", "GB") if "mb to gb" in q_lower else ("GB", "MB")

            thought = f"User wants conversion of {val} from {f_unit} to {t_unit}. Invoking `convert_currency_and_units`."
            return thought, {"tool": "convert_currency_and_units", "arguments": {"value": val, "from_unit": f_unit, "to_unit": t_unit}}

        # 4. Todo & Task Management
        if any(w in q_lower for w in ["todo", "task", "reminder", "tasks", "kaam list", "add task", "my tasks"]):
            action = "list"
            task_text = ""
            if any(w in q_lower for w in ["add", "create", "new task", "likho"]):
                action = "add"
                task_text = re.sub(r"^(please\s+)?(add|create|new)\s+(task|todo|reminder)\s*:?\s*", "", user_query, flags=re.IGNORECASE).strip()
            elif any(w in q_lower for w in ["done", "complete", "finish", "khatam"]):
                action = "complete"
                id_match = re.search(r"#?(\d+)", user_query)
                task_id = int(id_match.group(1)) if id_match else 1
                return f"Marking task #{task_id} complete.", {"tool": "manage_todo_tasks", "arguments": {"action": "complete", "task_id": task_id}}

            thought = f"User requested Todo action '{action}'. Invoking `manage_todo_tasks`."
            return thought, {"tool": "manage_todo_tasks", "arguments": {"action": action, "task_text": task_text or "General task"}}

        # 5. Email & Letter Drafting
        if any(w in q_lower for w in ["email", "letter", "draft", "leave application", "cover letter", "write an email", "boss ko email"]):
            doc_type = "leave" if ("leave" in q_lower or "sick" in q_lower or "chhutti" in q_lower) else "cover_letter" if "cover" in q_lower else "formal_email"
            topic = re.sub(r"^(please\s+)?(write|draft|generate)\s+(an?\s+)?(email|letter|application)\s*(for|about)?\s*", "", user_query, flags=re.IGNORECASE).strip() or "General Update"
            thought = f"User wants a professional draft for '{topic}' (Type: {doc_type}). Invoking `draft_email_or_document`."
            return thought, {"tool": "draft_email_or_document", "arguments": {"doc_type": doc_type, "topic": topic, "recipient": "Manager / Team"}}

        # 6. PDF Reading & Extraction
        if any(w in q_lower for w in ["read pdf", "pdf extract", "extract pdf", "read my pdf", "pdf summary"]):
            pdf_match = re.search(r"(['\"]?)([a-zA-Z]:[^\s'\"]+\.pdf|[^\s'\"]+\.pdf)\1", user_query, re.IGNORECASE)
            pdf_path = pdf_match.group(2) if pdf_match else "./data/sample_files/invoice_march.pdf"
            thought = f"User requested text extraction from PDF '{pdf_path}'. Invoking `read_and_extract_pdf`."
            return thought, {"tool": "read_and_extract_pdf", "arguments": {"pdf_path": pdf_path}}

        # 7. Large Files Scan / Storage Cleaner
        if any(w in q_lower for w in ["large files", "heavy files", "disk space", "storage clean", "space khali", "temp files", "cache clean"]):
            if "temp" in q_lower or "cache" in q_lower:
                thought = "User wants to inspect reclaimable temp storage. Invoking `clean_temp_storage_scan`."
                return thought, {"tool": "clean_temp_storage_scan", "arguments": {}}
            else:
                thought = "User wants to find large space-consuming files. Invoking `find_large_files`."
                return thought, {"tool": "find_large_files", "arguments": {"target_dir": ".", "min_size_mb": 50}}

        # 8. News Headlines
        if any(w in q_lower for w in ["news", "headlines", "khabar", "latest news", "breaking"]):
            thought = "User requested top news headlines. Invoking `get_news_headlines`."
            return thought, {"tool": "get_news_headlines", "arguments": {"category": "technology"}}

        # 9. System Health / Diagnostics
        if any(w in q_lower for w in ["system health", "cpu", "ram", "memory usage", "battery", "hardware status", "specs", "disk usage"]):
            thought = "User wants live system health and diagnostic metrics. Invoking `get_system_health`."
            return thought, {"tool": "get_system_health", "arguments": {}}

        # 10. Directory Organization
        if "organize" in q_lower or "sort folder" in q_lower or "categorize files" in q_lower or "files arrange" in q_lower:
            path_match = re.search(r"in\s+(['\"]?)([a-zA-Z]:[^\s'\"]+|[^\s'\"]+)\1", user_query, re.IGNORECASE)
            target = path_match.group(2) if path_match else "./data/sample_files"
            thought = f"User requested directory organization for '{target}'. Invoking `organize_directory`."
            return thought, {"tool": "organize_directory", "arguments": {"target_path": target}}

        # 11. Duplicate Files
        if "duplicate" in q_lower or "duplicates" in q_lower:
            path_match = re.search(r"in\s+(['\"]?)([a-zA-Z]:[^\s'\"]+|[^\s'\"]+)\1", user_query, re.IGNORECASE)
            target = path_match.group(2) if path_match else "."
            thought = f"User wants to find duplicate files in '{target}'. Invoking `find_duplicate_files`."
            return thought, {"tool": "find_duplicate_files", "arguments": {"target_path": target}}

        # 12. Web Research
        if any(w in q_lower for w in ["search", "google", "web research", "find online", "lookup", "who is", "what is", "research"]):
            clean_q = re.sub(r"^(please\s+)?(search|do\s+web\s+research\s+on|research|find\s+online\s+for|lookup)\s+", "", user_query, flags=re.IGNORECASE).strip()
            thought = f"User is requesting online web research for '{clean_q}'. Invoking `web_research`."
            return thought, {"tool": "web_research", "arguments": {"query": clean_q, "max_results": 3}}

        # 13. Security Header Audit
        if any(w in q_lower for w in ["audit", "security header", "csp", "hsts", "headers for", "check website"]):
            url_match = re.search(r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*)", user_query)
            target_url = url_match.group(1) if url_match else "https://example.com"
            thought = f"User wants a security headers audit for website '{target_url}'. Invoking `audit_web_headers`."
            return thought, {"tool": "audit_web_headers", "arguments": {"url": target_url}}

        # 14. Application Management
        if any(w in q_lower for w in ["launch", "open app", "close app", "kill app", "start notepad", "open calc", "close notepad"]):
            action = "close" if any(w in q_lower for w in ["close", "kill", "terminate", "stop"]) else "launch"
            app_name = "notepad"
            for candidate in ["notepad", "calc", "calculator", "explorer", "cmd", "chrome", "edge", "taskmgr", "paint"]:
                if candidate in q_lower:
                    app_name = candidate
                    break
            thought = f"User wants to {action} desktop application '{app_name}'. Invoking `manage_application`."
            return thought, {"tool": "manage_application", "arguments": {"app_name": app_name, "action": action}}

        # 15. Quick Note
        if any(w in q_lower for w in ["note", "take a note", "remember that", "save note", "write down", "note banao"]):
            clean_text = re.sub(r"^(please\s+)?(take a note|save note|note down|remember that|note banao)\s*:?\s*", "", user_query, flags=re.IGNORECASE).strip()
            thought = "User wants to create a quick timestamped note. Invoking `create_quick_note`."
            return thought, {"tool": "create_quick_note", "arguments": {"note_name": "AgentNote", "text": clean_text or user_query}}

        # 16. Python Sandbox & Self-Healing Execution
        if any(w in q_lower for w in ["python", "run code", "execute script", "calculate", "sandbox", "fibonacci", "factorial", "prime"]):
            code = user_query
            if "```python" in user_query:
                code = user_query.split("```python")[1].split("```")[0].strip()
            elif "```" in user_query:
                code = user_query.split("```")[1].split("```")[0].strip()
            else:
                code = f"# Autonomous Script Generation\nprint('Agent Sandbox Output:')\nresult = sum(range(1, 101))\nprint(f'Sum of 1 to 100 = {{result}}')\n"
            
            thought = "User requested Python code execution in isolated sandbox. Invoking `execute_python_code`."
            return thought, {"tool": "execute_python_code", "arguments": {"code_string": code}}

        # General Conversational Response
        thought = "Direct conversational response with comprehensive all-in-one workstation overview."
        return thought, {
            "action": "final_answer",
            "answer": (
                "👋 **Main aapka All-in-One Autonomous Desktop Copilot hoon!**\n\n"
                "Main normal users aur technical users dono ki **A to Z** requirements poori kar sakta hoon:\n\n"
                "### 🎯 Kya-kya kar sakta hoon:\n"
                "1. **📱 Daily Productivity:** QR Code Generation, Live Weather Forecast, Currency (USD ➔ INR) & Unit conversions, Todo & Task Manager.\n"
                "2. **📄 Document & Media:** PDF Text Extraction, PDF Merging, Image Resizing & Format Conversion (PNG/JPG), Professional Email & Leave Drafting.\n"
                "3. **🧹 PC Cleaning & File Ops:** Heavy Files Finder (>100MB), Temp storage scanner, File Categorizer, Duplicate Hash Finder.\n"
                "4. **🛡️ System & Security:** Live CPU/RAM/Battery metrics, Website Security Headers Audit, Port Scanner, Log Auditing, SHA256 Checksums.\n"
                "5. **🐍 Self-Healing Python Sandbox:** Automated code execution with error self-correction.\n\n"
                "Aap kuch bhi bolkar ya type karke try kar sakte hain (e.g. *'Generate QR code for my portfolio'*, *'Delhi ka weather batao'*, *'100 USD in INR'*, *'Write leave application'*)!"
            )
        }

    def _self_heal_code(self, broken_code: str, error_trace: str) -> str:
        """Self-Healing Reflection: Analyzes traceback and rewrites code to fix syntax or runtime errors."""
        console.print(f"[bold magenta][SelfHealing][/bold magenta] Repairing code based on error trace:\n{error_trace}")
        fixed = broken_code
        if "SyntaxError" in error_trace:
            if "print " in fixed and "print(" not in fixed:
                fixed = re.sub(r"print\s+(.*)", r"print(\1)", fixed)
            if "invalid syntax" in error_trace and "def " in fixed and ":" not in fixed:
                fixed = re.sub(r"(def\s+[a-zA-Z0-9_]+\([^)]*\))", r"\1:", fixed)

        if "NameError" in error_trace or "ModuleNotFoundError" in error_trace:
            needed_modules = []
            for mod in ["math", "os", "sys", "json", "time", "random"]:
                if mod in error_trace or f"{mod}." in fixed:
                    needed_modules.append(f"import {mod}")
            if needed_modules:
                fixed = "\n".join(needed_modules) + "\n" + fixed

        if "ZeroDivisionError" in error_trace:
            fixed = fixed.replace("/ 0", "/ 1")

        if fixed == broken_code:
            fixed = f"try:\n{self._indent_code(broken_code)}\nexcept Exception as e:\n    print(f'Handled error: {{e}}')\n"
        return fixed

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        pad = " " * spaces
        return "\n".join([f"{pad}{line}" if line.strip() else line for line in code.split("\n")])

    def _format_observation_response(self, user_query: str, tool_name: str, obs: Any) -> str:
        """Formats structured tool output into a clean Markdown response."""
        if isinstance(obs, dict):
            # WhatsApp Message Dispatcher
            if tool_name == "send_whatsapp_message" and obs.get("status") == "success":
                return (
                    f"### 💬 WhatsApp Dispatch Initiated!\n\n"
                    f"- **Recipient Phone:** `{obs['recipient_phone']}`\n"
                    f"- **Message Text:** *\"{obs['message_payload']}\"*\n"
                    f"- **Status:** {obs['action_executed']}\n\n"
                    f"🔗 [Click here to open WhatsApp directly]({obs['whatsapp_direct_url']})"
                )

            # Email Dispatcher
            elif tool_name == "compose_or_send_email" and obs.get("status") == "success":
                return (
                    f"### ✉️ Email Client Dispatch Initiated!\n\n"
                    f"- **To:** `{obs['recipient']}`\n"
                    f"- **Subject:** `{obs['subject']}`\n"
                    f"- **Status:** {obs['action_executed']}\n\n"
                    f"Aapka default mail client (Outlook/Windows Mail) pre-filled draft ke sath khul chuka hai."
                )

            # Predictive Hardware Lifespan
            elif tool_name == "predict_hardware_lifespan" and obs.get("status") == "success":
                comp_lines = "\n".join([f"- **{k}:** `{v}`" for k, v in obs.get("component_health_matrix", {}).items()])
                tips_lines = "\n".join([f"  {i+1}. {t}" for i, t in enumerate(obs.get("actionable_lifespan_tips", []))])
                risks = "\n".join([f"- ⚠️ {r}" for r in obs.get("identified_risk_factors", [])])

                return (
                    f"### 🔮 Predictive Hardware Lifespan & Longevity Analysis\n\n"
                    f"📊 **Overall Health Index:** `{obs['health_index_score']}/100` (Grade: **{obs['hardware_grade']}**)\n"
                    f"⏳ **Estimated Remaining Lifespan:** **`{obs['estimated_remaining_lifespan']}`**\n"
                    f"🎯 **System Verdict:** {obs['overall_verdict']}\n\n"
                    f"#### ⚙️ Component Degradation & Stress Matrix:\n{comp_lines}\n\n"
                    f"#### 🚨 Identified Risk Factors:\n{risks}\n\n"
                    f"#### 💡 Actionable Tips to Extend Machine Lifespan:\n{tips_lines}\n\n"
                    f"*System Specs: {obs['system_os']} | Processor: {obs['processor_model']} | Uptime: {obs['system_uptime']}*"
                )

            # Benchmark Performance
            elif tool_name == "benchmark_system_performance" and obs.get("status") == "success":
                return (
                    f"### ⚡ Real-Time Compute Benchmark Report\n\n"
                    f"- **Classification:** **`{obs['performance_tier']}`**\n"
                    f"- **CPU Stress Latency:** `{obs['cpu_calc_time_ms']} ms`\n"
                    f"- **Memory Allocation Throughput:** `{obs['memory_throughput_time_ms']} ms`\n"
                    f"- **Combined Latency Score:** `{obs['total_benchmark_score_ms']} ms`\n\n"
                    f"*{obs['evaluation']}*"
                )

            # Vulnerabilities
            elif tool_name == "audit_system_vulnerabilities" and obs.get("status") == "success":
                flagged = ", ".join([str(p) for p in obs['flagged_high_risk_ports']]) if obs['flagged_high_risk_ports'] else "None (Protected)"
                return (
                    f"### 🛡️ System Security & Vulnerability Audit\n\n"
                    f"- **Security Score:** `{obs['system_security_score']}/100` ({obs['security_status']})\n"
                    f"- **Active Listening Sockets:** {obs['open_listening_ports_count']}\n"
                    f"- **Exposed High-Risk Ports:** `{flagged}`\n"
                    f"- **Total Active OS Processes:** {obs['total_active_processes']}"
                )

            # QR Code
            elif tool_name == "generate_qr_code" and obs.get("status") == "success":
                return (
                    f"### 📱 QR Code Generated Successfully!\n\n"
                    f"- **Data Encoded:** `{obs['data']}`\n"
                    f"- **Saved File:** `{obs['file_path']}`\n\n"
                    f"Aap is QR code ko scan karke direct open kar sakte hain!"
                )

            # Weather
            elif tool_name == "get_live_weather" and obs.get("status") == "success":
                return (
                    f"### 🌤️ Live Weather Report: {obs['city']}, {obs['country']}\n\n"
                    f"- **Condition:** {obs['condition']}\n"
                    f"- **Temperature:** `{obs['temperature_c']}` ({obs['temperature_f']})\n"
                    f"- **Feels Like:** `{obs['feels_like_c']}`\n"
                    f"- **Humidity:** `{obs['humidity']}`\n"
                    f"- **Wind Speed:** `{obs['wind_speed']}`"
                )

            # Currency & Units
            elif tool_name == "convert_currency_and_units" and obs.get("status") == "success":
                formatted = obs.get("formatted", f"{obs.get('result')}")
                return f"### 💱 Conversion Result\n\n**{formatted}**"

            # Todo Tasks
            elif tool_name == "manage_todo_tasks" and obs.get("status") == "success":
                if "tasks" in obs:
                    tasks_list = obs["tasks"]
                    if not tasks_list:
                        return "### 📋 Todo Task List\n\nAapki todo list bilkul empty hai!"
                    lines = [f"- **#{t['id']}** [{t['status']}] {t['task']} *(Priority: {t['priority']})*" for t in tasks_list]
                    return f"### 📋 Your Active Tasks ({len(tasks_list)})\n\n" + "\n".join(lines)
                return f"### 📋 Task Updated\n\n{obs.get('message')}"

            # Email Drafting
            elif tool_name == "draft_email_or_document" and obs.get("status") == "success":
                return f"### ✍️ Drafted Document ({obs['document_type'].title()})\n\n{obs['formatted_draft']}"

            # PDF Extraction
            elif tool_name == "read_and_extract_pdf" and obs.get("status") == "success":
                return (
                    f"### 📄 PDF Document Analysis\n\n"
                    f"- **File:** `{obs['pdf_path']}`\n"
                    f"- **Total Pages:** {obs['total_pages']} | **Word Count:** {obs['word_count']}\n\n"
                    f"#### 📖 Preview:\n```text\n{obs['content_preview']}\n```"
                )

            # Large Files
            elif tool_name == "find_large_files" and obs.get("status") == "success":
                files = obs.get("files", [])
                if not files:
                    return f"### 💾 Storage Scan\n\nKoi bhi heavy file (>{obs['threshold_mb']}MB) nahi mili!"
                lines = [f"- **{f['file_name']}** (`{f['size_mb']} MB`) -> `{f['path']}`" for f in files[:8]]
                return f"### 💾 Large Space-Consuming Files Found ({obs['total_large_files_found']})\n\n" + "\n".join(lines)

            # Temp scan
            elif tool_name == "clean_temp_storage_scan" and obs.get("status") == "success":
                return (
                    f"### 🧹 System Cache & Temp Storage\n\n"
                    f"- **Total Temp Files:** {obs['total_temp_files']}\n"
                    f"- **Reclaimable Space:** `{obs['reclaimable_space_mb']} MB` (~{obs['reclaimable_space_gb']} GB)\n"
                    f"- **Recommendation:** {obs['recommendation']}"
                )

            # System health
            elif tool_name == "get_system_health" and obs.get("status") == "success":
                cpu = obs["cpu"]
                mem = obs["memory"]
                battery = obs.get("battery")
                batt_str = f"{battery['percent']}% ({'Charging' if battery['power_plugged'] else 'Discharging'})" if battery else "N/A"
                procs_str = "\n".join([f"- **{p['name']}** (PID: {p['pid']}): {p['memory_percent']}% RAM" for p in obs.get("top_memory_consumers", [])[:4]])
                return (
                    f"### 🖥️ Live System Health Diagnostic\n\n"
                    f"- **CPU Usage:** `{cpu['usage_percent']}%` ({cpu['logical_cores']} cores)\n"
                    f"- **RAM Usage:** `{mem['usage_percent']}%` ({mem['used_gb']} GB / {mem['total_gb']} GB)\n"
                    f"- **Battery Status:** `{batt_str}`\n\n"
                    f"#### 🔍 Top Resource Consumers:\n{procs_str}"
                )

            # Web headers
            elif tool_name == "audit_web_headers" and obs.get("status") == "success":
                checks = obs.get("checks", {})
                check_lines = [f"- {'✅' if info['present'] else '❌'} **{name}** ({info['importance']}): {'Present' if info['present'] else 'Missing'}" for name, info in checks.items()]
                return (
                    f"### 🛡️ Web Security Header Audit\n"
                    f"- **Target URL:** `{obs['target_url']}` | **Score:** `{obs['security_score_percent']}%` (Grade: **{obs['security_grade']}**)\n\n"
                    f"#### Header Controls:\n" + "\n".join(check_lines)
                )

            # Web research
            elif tool_name == "web_research":
                return f"### 🌐 Web Research Results\n\n{obs.get('synthesis', json.dumps(obs, indent=2))}"

            # Python sandbox
            elif tool_name == "execute_python_code":
                if obs.get("success"):
                    return f"### 🐍 Sandbox Execution Result\n\n**Output:**\n```\n{obs.get('stdout')}\n```\n*Execution Time: {obs.get('execution_time_sec')}s (Exit code: 0)*"
                else:
                    return f"### ⚠️ Sandbox Execution Failure\n\n**Error:**\n```\n{obs.get('stderr')}\n```\n*Error Type: {obs.get('error_type')}*"

            # Organize directory
            elif tool_name == "organize_directory":
                return f"### 📁 Directory Organization\n\n{obs.get('message')}\n\n**Summary:**\n```json\n{json.dumps(obs.get('summary', {}), indent=2)}\n```"

        return f"**Result from `{tool_name}`:**\n\n```json\n{json.dumps(obs, indent=2) if isinstance(obs, (dict, list)) else str(obs)}\n```"

    def _synthesize_final_response(self, user_query: str, history: List[Dict[str, Any]]) -> str:
        """Synthesizes final answer from multiple step results."""
        if not history:
            return "Task completed."
        last_obs = history[-1]["observation"]
        last_tool = history[-1]["tool"]
        return self._format_observation_response(user_query, last_tool, last_obs)
