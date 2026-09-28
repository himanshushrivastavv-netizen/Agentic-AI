"""Safety Guardrail module for Human-in-the-Loop verification of destructive actions."""
import enum
import os
import threading
from typing import Callable, Optional, Dict, Any, Tuple
from rich.console import Console

console = Console()

class ActionRiskLevel(enum.Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SafetyGuard:
    """Manages risk assessments and human-in-the-loop authorization for agent actions."""

    def __init__(self, confirmation_callback: Optional[Callable[[str, str, ActionRiskLevel], bool]] = None):
        """
        Args:
            confirmation_callback: Callable taking (action_name, description, risk_level) -> bool
        """
        self.confirmation_callback = confirmation_callback
        self._lock = threading.Lock()
        
        # Actions that inherently require user confirmation
        self.high_risk_actions = {
            "terminate_process": ActionRiskLevel.HIGH,
            "kill_process": ActionRiskLevel.HIGH,
            "delete_file": ActionRiskLevel.HIGH,
            "delete_directory": ActionRiskLevel.CRITICAL,
            "execute_python_code": ActionRiskLevel.MEDIUM,
            "manage_application_kill": ActionRiskLevel.HIGH,
            "overwrite_system_file": ActionRiskLevel.CRITICAL
        }

    def evaluate_risk(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[ActionRiskLevel, str]:
        """Evaluates tool name and arguments to calculate a risk rating and justification."""
        tool_lower = tool_name.lower()
        
        if "delete" in tool_lower or "remove" in tool_lower:
            target = arguments.get("target_path", arguments.get("filepath", "unspecified target"))
            return ActionRiskLevel.HIGH, f"Destructive file deletion requested on: {target}"
            
        if "manage_application" in tool_lower:
            action = str(arguments.get("action", "")).lower()
            app = arguments.get("app_name", "target application")
            if action in ["close", "kill", "terminate", "stop"]:
                return ActionRiskLevel.HIGH, f"Attempting to terminate application/process: {app}"
            return ActionRiskLevel.SAFE, f"Launching application: {app}"

        if "execute_python_code" in tool_lower or "sandbox" in tool_lower:
            code = str(arguments.get("code_string", ""))
            suspicious_keywords = ["os.remove", "shutil.rmtree", "subprocess", "socket", "sys.exit", "rmdir"]
            for kw in suspicious_keywords:
                if kw in code:
                    return ActionRiskLevel.HIGH, f"Sandbox code contains potentially destructive keyword: '{kw}'"
            return ActionRiskLevel.MEDIUM, "Executing dynamic Python code in isolated sandbox"

        if "organize_directory" in tool_lower:
            target = arguments.get("target_path", "")
            return ActionRiskLevel.LOW, f"Moving and categorizing files in directory: {target}"

        return ActionRiskLevel.SAFE, "Read-only or non-destructive operation"

    def request_permission(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluates risk and queries the registered UI callback or console confirmation.
        Returns: (is_allowed, reason)
        """
        risk_level, explanation = self.evaluate_risk(tool_name, arguments)
        
        if risk_level == ActionRiskLevel.SAFE:
            return True, "Action is deemed safe."

        console.print(f"[bold yellow][SafetyGuard][/bold yellow] Action '{tool_name}' evaluated as [{risk_level.value}]: {explanation}")

        # If UI callback is provided, invoke it
        if self.confirmation_callback is not None:
            approved = self.confirmation_callback(tool_name, explanation, risk_level)
            if approved:
                console.print(f"[bold green][SafetyGuard][/bold green] User approved action: {tool_name}")
                return True, "User granted confirmation via GUI."
            else:
                console.print(f"[bold red][SafetyGuard][/bold red] User rejected action: {tool_name}")
                return False, f"Action blocked by user: {explanation}"

        # Default fallback: allow LOW risk, block HIGH and CRITICAL if no handler
        if risk_level in (ActionRiskLevel.LOW, ActionRiskLevel.MEDIUM):
            return True, f"Auto-approved {risk_level.value} risk action in headless mode."
            
        return False, f"Action flagged as {risk_level.value} risk without user confirmation callback."
