"""Self-Healing Script Sandbox module for isolated Python code execution and diagnostic tracebacks."""
import os
import sys
import tempfile
import time
import subprocess
from typing import Dict, Any
from rich.console import Console

console = Console()

class SandboxRunner:
    """Provides isolated script execution with traceback capture and self-healing analysis."""

    def __init__(self, sandbox_dir: str = "./data/sandbox"):
        self.sandbox_dir = os.path.abspath(sandbox_dir)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        self.python_executable = sys.executable

    def execute_python_code(self, code_string: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Executes Python code in an isolated subprocess.
        Captures stdout, stderr, and returns structured feedback for self-healing loops.
        """
        if not code_string.strip():
            return {
                "status": "error",
                "success": False,
                "stdout": "",
                "stderr": "Empty code payload provided.",
                "exit_code": -1,
                "needs_healing": True,
                "error_type": "ValueError"
            }

        temp_script = None
        start_time = time.time()
        try:
            # Create unique temp script file in the sandbox directory
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                dir=self.sandbox_dir,
                delete=False,
                encoding="utf-8"
            ) as f:
                temp_script = f.name
                f.write(code_string)

            # Isolated execution
            proc = subprocess.run(
                [self.python_executable, temp_script],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.sandbox_dir
            )
            elapsed_time = round(time.time() - start_time, 3)

            is_success = (proc.returncode == 0)
            stderr_output = proc.stderr.strip()
            stdout_output = proc.stdout.strip()

            error_type = None
            needs_healing = not is_success
            
            if not is_success:
                # Classify error type from stderr
                if "SyntaxError" in stderr_output:
                    error_type = "SyntaxError"
                elif "NameError" in stderr_output:
                    error_type = "NameError"
                elif "TypeError" in stderr_output:
                    error_type = "TypeError"
                elif "ImportError" in stderr_output or "ModuleNotFoundError" in stderr_output:
                    error_type = "ModuleNotFoundError"
                elif "IndexError" in stderr_output or "KeyError" in stderr_output:
                    error_type = "LookupError"
                elif "ZeroDivisionError" in stderr_output:
                    error_type = "ZeroDivisionError"
                elif "AttributeError" in stderr_output:
                    error_type = "AttributeError"
                else:
                    error_type = "RuntimeError"

            return {
                "status": "success" if is_success else "error",
                "success": is_success,
                "stdout": stdout_output,
                "stderr": stderr_output,
                "exit_code": proc.returncode,
                "execution_time_sec": elapsed_time,
                "needs_healing": needs_healing,
                "error_type": error_type,
                "raw_code": code_string
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "success": False,
                "stdout": "",
                "stderr": f"Script execution exceeded timeout limit of {timeout} seconds.",
                "exit_code": -1,
                "execution_time_sec": timeout,
                "needs_healing": True,
                "error_type": "TimeoutError",
                "raw_code": code_string
            }
        except Exception as e:
            return {
                "status": "error",
                "success": False,
                "stdout": "",
                "stderr": f"Sandbox execution failure: {str(e)}",
                "exit_code": -1,
                "execution_time_sec": round(time.time() - start_time, 3),
                "needs_healing": True,
                "error_type": "SystemError",
                "raw_code": code_string
            }
        finally:
            if temp_script and os.path.exists(temp_script):
                try:
                    os.remove(temp_script)
                except Exception:
                    pass
