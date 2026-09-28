"""Entry Point for Agentic AI Desktop Application.

Initializes directory structures, creates sample test files, mounts subsystems,
and boots the CustomTkinter desktop interface.
"""
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def setup_environment():
    """Ensures required data directories and sample playground files exist."""
    required_dirs = [
        "./data",
        "./data/memory",
        "./data/notes",
        "./data/sandbox",
        "./data/sample_files"
    ]
    for d in required_dirs:
        os.makedirs(os.path.abspath(d), exist_ok=True)

    # Create a sample log file for instant log audit testing
    sample_log = os.path.abspath("./data/sample.log")
    if not os.path.exists(sample_log):
        with open(sample_log, "w", encoding="utf-8") as f:
            f.write(
                "2026-09-28 10:00:01 [INFO] System boot sequence completed.\n"
                "2026-09-28 10:02:14 [WARN] High memory pressure detected on worker pool.\n"
                "2026-09-28 10:05:30 [ERROR] Connection failed to database shard-02.\n"
                "2026-09-28 10:07:45 [CRITICAL] Authentication service failed response.\n"
                "2026-09-28 10:10:00 [INFO] Auto-recovery executed successfully.\n"
            )

    # Create a couple of sample unorganized files for testing file organizer
    sample_files_dir = os.path.abspath("./data/sample_files")
    sample_items = {
        "invoice_march.pdf": "Sample PDF Document invoice",
        "diagram_architecture.png": "Sample PNG image file content",
        "archive_backup.zip": "Sample zip archive payload",
        "data_processing.py": "print('Sample python script')\n",
        "duplicate_sample.txt": "This is a duplicate test file content for hash matching.",
        "duplicate_copy.txt": "This is a duplicate test file content for hash matching."
    }
    for fname, content in sample_items.items():
        fpath = os.path.join(sample_files_dir, fname)
        if not os.path.exists(fpath):
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)

def print_banner():
    """Prints a structured banner to console."""
    table = Table(title="🚀 Agentic AI Desktop Workstation Initialized", border_style="bright_blue")
    table.add_column("Subsystem", style="cyan", justify="left")
    table.add_column("Status", style="green", justify="left")
    table.add_column("Details", style="magenta", justify="left")

    table.add_row("GUI Engine", "Active", "CustomTkinter Dark Theme (1100x780)")
    table.add_row("ReAct Brain", "Active", "Multi-step Reasoning & Tool Router")
    table.add_row("Vector Memory", "Active", "Local ChromaDB & SQLite Persistence")
    table.add_row("Safety Guard", "Active", "Human-in-the-Loop Dialogs")
    table.add_row("Voice Layer", "Active", "Offline Pyttsx3 TTS & STT Worker")
    table.add_row("Self-Healing Sandbox", "Active", "Isolated Subprocess Runner")

    console.print(table)
    console.print(Panel.fit(
        "[bold cyan]Launching Agentic AI Desktop GUI Window...[/bold cyan]\n"
        "[dim]Ready for everyday automation, technical diagnostics, and autonomous coding.[/dim]",
        border_style="green"
    ))

def main():
    """Application entry point."""
    setup_environment()
    print_banner()

    from ui.dashboard import AgentDashboardApp
    app = AgentDashboardApp()
    app.mainloop()

if __name__ == "__main__":
    main()
