"""General User Automation tools for everyday file management, web research, apps, and notes."""
import os
import shutil
import hashlib
import subprocess
import datetime
import requests
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

class GeneralTools:
    """Everyday user automation tools suite."""

    CATEGORY_MAP = {
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".odt", ".rtf", ".md"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        "Media": [".mp4", ".mkv", ".mp3", ".wav", ".flac", ".mov", ".avi", ".aac"],
        "Code": [".py", ".js", ".html", ".css", ".json", ".ts", ".cpp", ".c", ".java", ".go", ".rs", ".sql", ".sh", ".bat", ".ps1"]
    }

    def __init__(self, notes_dir: str = "./data/notes"):
        self.notes_dir = os.path.abspath(notes_dir)
        os.makedirs(self.notes_dir, exist_ok=True)

    def organize_directory(self, target_path: str) -> Dict[str, Any]:
        """
        Scans folder and categorizes loose files into subdirectories:
        Documents, Images, Archives, Media, Code, and Others.
        """
        target = os.path.abspath(os.path.expanduser(target_path))
        if not os.path.exists(target) or not os.path.isdir(target):
            return {"status": "error", "message": f"Directory does not exist: {target}"}

        moved_summary = {cat: 0 for cat in self.CATEGORY_MAP}
        moved_summary["Others"] = 0
        details = []

        try:
            for item in os.listdir(target):
                item_path = os.path.join(target, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    assigned_cat = "Others"
                    for cat, extensions in self.CATEGORY_MAP.items():
                        if ext in extensions:
                            assigned_cat = cat
                            break

                    cat_dir = os.path.join(target, assigned_cat)
                    os.makedirs(cat_dir, exist_ok=True)
                    dest_path = os.path.join(cat_dir, item)

                    # Avoid collision
                    if os.path.exists(dest_path):
                        base_name, file_ext = os.path.splitext(item)
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest_path = os.path.join(cat_dir, f"{base_name}_{timestamp}{file_ext}")

                    shutil.move(item_path, dest_path)
                    moved_summary[assigned_cat] += 1
                    details.append({"file": item, "category": assigned_cat, "destination": dest_path})

            total_moved = sum(moved_summary.values())
            return {
                "status": "success",
                "message": f"Successfully organized {total_moved} files in {target}",
                "summary": moved_summary,
                "details": details
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed organizing directory: {str(e)}"}

    def find_duplicate_files(self, target_path: str) -> Dict[str, Any]:
        """
        Identifies duplicate files in the given directory by cryptographic hash comparison.
        """
        target = os.path.abspath(os.path.expanduser(target_path))
        if not os.path.exists(target) or not os.path.isdir(target):
            return {"status": "error", "message": f"Directory does not exist: {target}"}

        hash_map: Dict[str, List[str]] = {}
        duplicates: List[Dict[str, Any]] = []

        try:
            for root, _, files in os.walk(target):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        # Quick size check first
                        file_size = os.path.getsize(file_path)
                        if file_size == 0:
                            continue
                        
                        hasher = hashlib.sha256()
                        with open(file_path, "rb") as f:
                            while chunk := f.read(65536):
                                hasher.update(chunk)
                        file_hash = hasher.hexdigest()

                        if file_hash in hash_map:
                            hash_map[file_hash].append(file_path)
                        else:
                            hash_map[file_hash] = [file_path]
                    except (PermissionError, FileNotFoundError):
                        continue

            for file_hash, paths in hash_map.items():
                if len(paths) > 1:
                    size = os.path.getsize(paths[0])
                    duplicates.append({
                        "hash": file_hash,
                        "file_size_bytes": size,
                        "count": len(paths),
                        "paths": paths
                    })

            return {
                "status": "success",
                "target_path": target,
                "total_duplicate_groups": len(duplicates),
                "duplicates": duplicates
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed scanning duplicates: {str(e)}"}

    def web_research(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Searches web information, parses textual paragraphs, and synthesizes key takeaways.
        Uses DuckDuckGo HTML search and Wikipedia API fallback.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        results = []
        
        # 1. DuckDuckGo Instant Answer / HTML Search
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            resp = requests.get(ddg_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                web_snippets = soup.find_all("div", class_="result__body")
                for snippet in web_snippets[:max_results]:
                    title_elem = snippet.find("a", class_="result__snippet") or snippet.find("a", class_="result__url")
                    title_header = snippet.find("h2", class_="result__title")
                    title = title_header.get_text(strip=True) if title_header else "Web Result"
                    body = snippet.find("a", class_="result__snippet")
                    text = body.get_text(strip=True) if body else ""
                    link = snippet.find("a", class_="result__url")
                    url = link.get("href", "") if link else ""
                    if text:
                        results.append({
                            "source": "DuckDuckGo",
                            "title": title,
                            "snippet": text,
                            "url": url
                        })
        except Exception as e:
            console.print(f"[bold yellow][GeneralTools][/bold yellow] DuckDuckGo search failed: {e}")

        # 2. Wikipedia Summary Fallback
        if len(results) < max_results:
            try:
                wiki_api = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query)}"
                wiki_resp = requests.get(wiki_api, headers=headers, timeout=6)
                if wiki_resp.status_code == 200:
                    data = wiki_resp.json()
                    extract = data.get("extract", "")
                    title = data.get("title", query)
                    url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                    if extract:
                        results.append({
                            "source": "Wikipedia",
                            "title": title,
                            "snippet": extract,
                            "url": url
                        })
            except Exception as e:
                console.print(f"[bold yellow][GeneralTools][/bold yellow] Wikipedia fallback search error: {e}")

        if not results:
            return {
                "status": "partial",
                "query": query,
                "message": f"No live search results retrieved for '{query}'. Synthesizing offline knowledge.",
                "results": []
            }

        synthesis = "\n\n".join([f"- **{r['title']}** ({r['source']}): {r['snippet']}" for r in results])
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results,
            "synthesis": synthesis
        }

    def manage_application(self, app_name: str, action: str) -> Dict[str, Any]:
        """
        Launches or closes specified desktop programs safely via subprocess.
        action: 'open' | 'launch' | 'close' | 'kill' | 'terminate'
        """
        action = action.lower().strip()
        app_name = app_name.strip()

        # Map common friendly app names to Windows executables
        app_map = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "taskmgr": "taskmgr.exe",
            "task manager": "taskmgr.exe",
            "mspaint": "mspaint.exe",
            "paint": "mspaint.exe",
            "chrome": "chrome.exe",
            "msedge": "msedge.exe",
            "edge": "msedge.exe"
        }

        exe_target = app_map.get(app_name.lower(), app_name)
        if not exe_target.endswith(".exe") and not os.path.isabs(exe_target):
            exe_target = f"{exe_target}.exe"

        try:
            if action in ["open", "launch", "start"]:
                proc = subprocess.Popen(
                    exe_target,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return {
                    "status": "success",
                    "action": "launch",
                    "application": app_name,
                    "target_executable": exe_target,
                    "message": f"Successfully triggered launch for '{app_name}' (PID: {proc.pid})"
                }

            elif action in ["close", "kill", "terminate", "stop"]:
                # Windows taskkill
                proc = subprocess.run(
                    f"taskkill /F /IM {exe_target} /T",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if proc.returncode == 0:
                    return {
                        "status": "success",
                        "action": "terminate",
                        "application": app_name,
                        "output": proc.stdout.strip(),
                        "message": f"Terminated instances of '{app_name}'"
                    }
                else:
                    return {
                        "status": "warning",
                        "action": "terminate",
                        "application": app_name,
                        "output": proc.stderr.strip() or proc.stdout.strip(),
                        "message": f"Could not find or terminate active process '{exe_target}'"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported action '{action}'. Valid actions are: 'launch', 'close'."
                }
        except Exception as e:
            return {"status": "error", "message": f"Application management error: {str(e)}"}

    def create_quick_note(self, note_name: str, text: str) -> Dict[str, Any]:
        """
        Appends timestamped entries to a dedicated local note file (.md / .txt).
        """
        try:
            clean_name = "".join(c for c in note_name if c.isalnum() or c in (" ", "_", "-")).strip()
            if not clean_name:
                clean_name = "QuickNote"
            filename = f"{clean_name}.md"
            note_path = os.path.join(self.notes_dir, filename)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_entry = f"\n### Entry [{timestamp}]\n{text.strip()}\n\n---\n"

            mode = "a" if os.path.exists(note_path) else "w"
            with open(note_path, mode, encoding="utf-8") as f:
                if mode == "w":
                    f.write(f"# Notes: {clean_name}\nCreated: {timestamp}\n\n---\n")
                f.write(formatted_entry)

            return {
                "status": "success",
                "note_title": clean_name,
                "filepath": note_path,
                "timestamp": timestamp,
                "message": f"Saved quick note entry to {filename}"
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed creating note: {str(e)}"}
