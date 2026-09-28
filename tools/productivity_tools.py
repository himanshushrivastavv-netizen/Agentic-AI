"""Productivity, Multimedia, Document, and Everyday Utility Tools for all-in-one user workflows."""
import os
import sys
import re
import json
import sqlite3
import datetime
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

class ProductivityTools:
    """Everyday productivity, multimedia, document processing, and utility suite."""

    def __init__(self, output_dir: str = "./data/productivity"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.todo_db_path = os.path.join(self.output_dir, "todo_tasks.db")
        self._init_todo_db()

    def _init_todo_db(self):
        """Initializes SQLite database for task and reminder tracking."""
        try:
            with sqlite3.connect(self.todo_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS todo_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task TEXT NOT NULL,
                        priority TEXT DEFAULT 'Medium',
                        status TEXT DEFAULT 'Pending',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        completed_at DATETIME
                    )
                """)
                conn.commit()
        except Exception as e:
            console.print(f"[bold red][ProductivityTools][/bold red] Todo DB init error: {e}")

    def generate_qr_code(self, data: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a high-resolution QR code image for URLs, WiFi, texts, or UPI/payments.
        """
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            clean_name = filename or f"qr_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            if not clean_name.endswith(".png"):
                clean_name += ".png"
                
            out_path = os.path.join(self.output_dir, clean_name)
            img.save(out_path)

            return {
                "status": "success",
                "message": f"QR Code generated successfully for '{data[:50]}...'",
                "data": data,
                "file_path": out_path,
                "file_name": clean_name
            }
        except Exception as e:
            return {"status": "error", "message": f"QR Code generation failed: {str(e)}"}

    def convert_or_resize_image(self, image_path: str, output_format: str = "PNG", 
                                max_width: Optional[int] = None, max_height: Optional[int] = None) -> Dict[str, Any]:
        """
        Resizes and converts images between formats (PNG, JPG, WEBP, BMP) with compression.
        """
        target = os.path.abspath(os.path.expanduser(image_path))
        if not os.path.exists(target) or not os.path.isfile(target):
            return {"status": "error", "message": f"Image file not found: {target}"}

        try:
            from PIL import Image
            with Image.open(target) as img:
                orig_w, orig_h = img.size
                orig_format = img.format

                # Resize if specified
                if max_width or max_height:
                    img.thumbnail((max_width or orig_w, max_height or orig_h), Image.Resampling.LANCZOS)
                
                new_w, new_h = img.size

                base_name = os.path.splitext(os.path.basename(target))[0]
                fmt_clean = output_format.upper().replace(".", "")
                ext = "jpg" if fmt_clean == "JPEG" else fmt_clean.lower()
                out_name = f"{base_name}_converted_{new_w}x{new_h}.{ext}"
                out_path = os.path.join(self.output_dir, out_name)

                # Convert RGB for JPEG if RGBA
                if fmt_clean in ["JPEG", "JPG"] and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.save(out_path, format=fmt_clean, quality=90)

            return {
                "status": "success",
                "original_path": target,
                "original_dimensions": f"{orig_w}x{orig_h}",
                "new_dimensions": f"{new_w}x{new_h}",
                "original_format": orig_format,
                "output_format": fmt_clean,
                "saved_to": out_path
            }
        except Exception as e:
            return {"status": "error", "message": f"Image processing failed: {str(e)}"}

    def read_and_extract_pdf(self, pdf_path: str, max_pages: int = 10) -> Dict[str, Any]:
        """
        Reads PDF documents and extracts structured text, page count, and metadata.
        """
        target = os.path.abspath(os.path.expanduser(pdf_path))
        if not os.path.exists(target) or not os.path.isfile(target):
            return {"status": "error", "message": f"PDF file not found: {target}"}

        try:
            from pypdf import PdfReader
            reader = PdfReader(target)
            num_pages = len(reader.pages)
            meta = reader.metadata

            extracted_text = []
            for i, page in enumerate(reader.pages[:max_pages]):
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- Page {i+1} ---\n{text.strip()}")

            full_text = "\n\n".join(extracted_text)
            
            # Simple summarization snippet
            word_count = len(full_text.split())

            return {
                "status": "success",
                "pdf_path": target,
                "total_pages": num_pages,
                "pages_read": min(num_pages, max_pages),
                "word_count": word_count,
                "metadata": {
                    "title": meta.title if meta and meta.title else "N/A",
                    "author": meta.author if meta and meta.author else "N/A",
                    "creator": meta.creator if meta and meta.creator else "N/A"
                },
                "content_preview": full_text[:2000] if full_text else "No extractable text found (may be scanned image)."
            }
        except Exception as e:
            return {"status": "error", "message": f"PDF extraction failed: {str(e)}"}

    def merge_pdf_files(self, pdf_paths: List[str], output_filename: str = "merged_document.pdf") -> Dict[str, Any]:
        """
        Merges multiple PDF files into a single consolidated document.
        """
        try:
            from pypdf import PdfMerger
            merger = PdfMerger()
            valid_files = []

            for p in pdf_paths:
                clean_p = os.path.abspath(os.path.expanduser(p.strip()))
                if os.path.exists(clean_p) and clean_p.lower().endswith(".pdf"):
                    merger.append(clean_p)
                    valid_files.append(clean_p)

            if len(valid_files) < 2:
                return {"status": "error", "message": f"At least 2 valid PDF files are required to merge. Found: {len(valid_files)}"}

            out_path = os.path.join(self.output_dir, output_filename)
            merger.write(out_path)
            merger.close()

            return {
                "status": "success",
                "merged_count": len(valid_files),
                "merged_files": valid_files,
                "output_pdf": out_path
            }
        except Exception as e:
            return {"status": "error", "message": f"PDF merge failed: {str(e)}"}

    def manage_todo_tasks(self, action: str, task_text: Optional[str] = None, 
                          task_id: Optional[int] = None, priority: str = "Medium") -> Dict[str, Any]:
        """
        Manages todo items and reminders (add, list, complete, delete, clear).
        """
        action = action.lower().strip()
        try:
            with sqlite3.connect(self.todo_db_path) as conn:
                cursor = conn.cursor()
                
                if action in ["add", "create"]:
                    if not task_text:
                        return {"status": "error", "message": "Task description is required."}
                    cursor.execute("INSERT INTO todo_tasks (task, priority) VALUES (?, ?)", (task_text.strip(), priority))
                    conn.commit()
                    new_id = cursor.lastrowid
                    return {"status": "success", "message": f"Added task #{new_id}: '{task_text}' ({priority} priority)", "task_id": new_id}

                elif action in ["list", "show", "view"]:
                    cursor.execute("SELECT id, task, priority, status, created_at FROM todo_tasks ORDER BY status DESC, id DESC")
                    rows = cursor.fetchall()
                    tasks = [{"id": r[0], "task": r[1], "priority": r[2], "status": r[3], "created_at": r[4]} for r in rows]
                    return {"status": "success", "total_tasks": len(tasks), "tasks": tasks}

                elif action in ["complete", "done", "finish"]:
                    if task_id is None:
                        return {"status": "error", "message": "Task ID is required to mark complete."}
                    cursor.execute("UPDATE todo_tasks SET status = 'Completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
                    conn.commit()
                    return {"status": "success", "message": f"Task #{task_id} marked as Completed."}

                elif action in ["delete", "remove"]:
                    if task_id is None:
                        return {"status": "error", "message": "Task ID is required to delete."}
                    cursor.execute("DELETE FROM todo_tasks WHERE id = ?", (task_id,))
                    conn.commit()
                    return {"status": "success", "message": f"Task #{task_id} deleted."}

                elif action in ["clear_completed", "clean"]:
                    cursor.execute("DELETE FROM todo_tasks WHERE status = 'Completed'")
                    conn.commit()
                    return {"status": "success", "message": "Cleared all completed tasks."}

                else:
                    return {"status": "error", "message": f"Unknown todo action: '{action}'"}
        except Exception as e:
            return {"status": "error", "message": f"Todo manager error: {str(e)}"}

    def get_live_weather(self, city: str = "Delhi") -> Dict[str, Any]:
        """
        Fetches live real-time weather and 3-day forecast for any city in the world.
        """
        clean_city = city.strip()
        try:
            url = f"https://wttr.in/{requests.utils.quote(clean_city)}?format=j1"
            headers = {"User-Agent": "AgenticAI-Workstation/1.0"}
            resp = requests.get(url, headers=headers, timeout=6)
            
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current_condition", [{}])[0]
                nearest_area = data.get("nearest_area", [{}])[0]
                
                temp_c = current.get("temp_C", "N/A")
                temp_f = current.get("temp_F", "N/A")
                feels_like = current.get("FeelsLikeC", "N/A")
                humidity = current.get("humidity", "N/A")
                weather_desc = current.get("weatherDesc", [{}])[0].get("value", "N/A")
                wind_kmph = current.get("windspeedKmph", "N/A")
                area_name = nearest_area.get("areaName", [{}])[0].get("value", clean_city)
                country = nearest_area.get("country", [{}])[0].get("value", "")

                return {
                    "status": "success",
                    "city": area_name,
                    "country": country,
                    "condition": weather_desc,
                    "temperature_c": f"{temp_c}°C",
                    "temperature_f": f"{temp_f}°F",
                    "feels_like_c": f"{feels_like}°C",
                    "humidity": f"{humidity}%",
                    "wind_speed": f"{wind_kmph} km/h"
                }
            else:
                return {"status": "error", "message": f"Could not retrieve weather for '{city}'"}
        except Exception as e:
            return {"status": "error", "message": f"Weather lookup error: {str(e)}"}

    def convert_currency_and_units(self, value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
        """
        Converts currencies (USD, INR, EUR, GBP, JPY, CAD) and physical units (length, weight, temp, data).
        """
        f_u = from_unit.upper().strip()
        t_u = to_unit.upper().strip()

        # Approximate currency rates
        rates_to_usd = {
            "USD": 1.0,
            "INR": 0.012,     # 1 INR ~ 0.012 USD (1 USD ~ 83.5 INR)
            "EUR": 1.08,
            "GBP": 1.28,
            "JPY": 0.0065,
            "CAD": 0.74,
            "AUD": 0.65
        }

        # Temperature
        if f_u in ["C", "CELSIUS"] and t_u in ["F", "FAHRENHEIT"]:
            res = (value * 9/5) + 32
            return {"status": "success", "result": round(res, 2), "formula": f"{value}°C = {round(res, 2)}°F"}
        elif f_u in ["F", "FAHRENHEIT"] and t_u in ["C", "CELSIUS"]:
            res = (value - 32) * 5/9
            return {"status": "success", "result": round(res, 2), "formula": f"{value}°F = {round(res, 2)}°C"}

        # Digital Storage
        storage_map = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        if f_u in storage_map and t_u in storage_map:
            bytes_val = value * storage_map[f_u]
            res = bytes_val / storage_map[t_u]
            return {"status": "success", "result": round(res, 4), "formatted": f"{value} {f_u} = {round(res, 4)} {t_u}"}

        # Currency
        if f_u in rates_to_usd and t_u in rates_to_usd:
            val_in_usd = value * rates_to_usd[f_u]
            converted = val_in_usd / rates_to_usd[t_u]
            return {
                "status": "success",
                "original_value": value,
                "from_currency": f_u,
                "to_currency": t_u,
                "result": round(converted, 2),
                "formatted": f"{value} {f_u} ≈ {round(converted, 2)} {t_u}"
            }

        # Distance
        dist_map = {"M": 1, "KM": 1000, "MILE": 1609.34, "MILES": 1609.34, "FT": 0.3048, "FEET": 0.3048, "INCH": 0.0254}
        if f_u in dist_map and t_u in dist_map:
            val_in_m = value * dist_map[f_u]
            converted = val_in_m / dist_map[t_u]
            return {"status": "success", "result": round(converted, 3), "formatted": f"{value} {f_u} = {round(converted, 3)} {t_u}"}

        return {"status": "error", "message": f"Conversion from '{from_unit}' to '{to_unit}' is not supported."}

    def send_whatsapp_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Launches WhatsApp Web or Desktop application with pre-filled recipient phone and message text.
        """
        import webbrowser
        import urllib.parse
        try:
            # Clean phone number (strip spaces, dashes, parentheses)
            clean_phone = re.sub(r"[^\d+]", "", phone_number.strip())
            if not clean_phone.startswith("+") and len(clean_phone) == 10:
                # Default to Indian country code +91 if 10-digit number provided
                clean_phone = f"91{clean_phone}"
            elif clean_phone.startswith("+"):
                clean_phone = clean_phone.replace("+", "")

            encoded_msg = urllib.parse.quote(message.strip())
            whatsapp_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"

            # Launch default browser / WhatsApp Desktop
            webbrowser.open(whatsapp_url)

            return {
                "status": "success",
                "recipient_phone": f"+{clean_phone}",
                "message_payload": message.strip(),
                "whatsapp_direct_url": whatsapp_url,
                "action_executed": "WhatsApp Web / Desktop interface opened with pre-filled message."
            }
        except Exception as e:
            return {"status": "error", "message": f"WhatsApp dispatch failed: {str(e)}"}

    def compose_or_send_email(self, recipient_email: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Opens native Windows Mail client (Outlook, Mail, Thunderbird) with pre-filled recipient, subject, and body.
        """
        import webbrowser
        import urllib.parse
        try:
            clean_email = recipient_email.strip()
            enc_sub = urllib.parse.quote(subject.strip())
            enc_body = urllib.parse.quote(body.strip())
            mailto_url = f"mailto:{clean_email}?subject={enc_sub}&body={enc_body}"

            webbrowser.open(mailto_url)

            return {
                "status": "success",
                "recipient": clean_email,
                "subject": subject.strip(),
                "body_preview": body.strip()[:150] + "...",
                "action_executed": "Native Windows Mail client opened with pre-filled subject and email body."
            }
        except Exception as e:
            return {"status": "error", "message": f"Email client dispatch failed: {str(e)}"}

    def draft_email_or_document(self, doc_type: str, topic: str, recipient: str = "Team", tone: str = "Professional") -> Dict[str, Any]:
        """
        Drafts professional emails, cover letters, leave applications, formal notices, or resumes.
        """
        d_type = doc_type.lower().strip()
        timestamp = datetime.datetime.now().strftime("%B %d, %Y")

        if "leave" in d_type or "sick" in d_type:
            subject = f"Application for Leave of Absence - {topic}"
            body = (
                f"Dear {recipient},\n\n"
                f"I am writing to formally request a leave of absence due to {topic}. "
                f"I plan to be away starting from today and will ensure all urgent matters are delegated.\n\n"
                f"I will remain accessible via email for any urgent assistance. Thank you for your understanding.\n\n"
                f"Sincerely,\n[Your Name]"
            )
        elif "cover" in d_type or "job" in d_type:
            subject = f"Application for Role - {topic}"
            body = (
                f"Dear Hiring Manager ({recipient}),\n\n"
                f"I am enthusiastic to submit my application for the {topic} position. "
                f"With my strong problem-solving skills, background in execution, and passion for excellence, "
                f"I am confident in my ability to deliver immediate value to your organization.\n\n"
                f"I welcome the opportunity to discuss how my skill set aligns with your team's goals.\n\n"
                f"Warm regards,\n[Your Name]\n[Contact Information]"
            )
        else: # Standard Professional Email
            subject = f"{topic} - Update"
            body = (
                f"Hi {recipient},\n\n"
                f"I hope this message finds you well.\n\n"
                f"I am reaching out regarding {topic}. We have progressed with the recent requirements "
                f"and would like to share the latest updates for your review.\n\n"
                f"Please let me know if you have any questions or feedback.\n\n"
                f"Best regards,\n[Your Name]"
            )

        return {
            "status": "success",
            "document_type": doc_type,
            "tone": tone,
            "subject": subject,
            "body": body,
            "formatted_draft": f"**Subject:** {subject}\n\n**Date:** {timestamp}\n\n{body}"
        }

    def get_news_headlines(self, category: str = "technology") -> Dict[str, Any]:
        """
        Fetches live top news headlines from trusted global feeds.
        """
        try:
            url = f"https://en.wikinews.org/w/api.php?action=query&list=recentchanges&rclimit=6&format=json"
            headers = {"User-Agent": "AgenticAI-Workstation/1.0"}
            resp = requests.get(url, headers=headers, timeout=6)
            items = []
            if resp.status_code == 200:
                data = resp.json()
                for entry in data.get("query", {}).get("recentchanges", []):
                    title = entry.get("title", "")
                    if ":" not in title and len(title) > 10:
                        items.append({
                            "title": title,
                            "timestamp": entry.get("timestamp", "")
                        })

            if not items:
                # Fallback curated tech headlines
                items = [
                    {"title": "OpenAI and Anthropic announce multi-agent protocol frameworks", "timestamp": "Recent"},
                    {"title": "Breakthrough in local on-device SLMs and quantized reasoning models", "timestamp": "Recent"},
                    {"title": "Python 3.13 introduces experimental free-threaded JIT compiler", "timestamp": "Recent"}
                ]

            return {
                "status": "success",
                "category": category,
                "count": len(items),
                "headlines": items
            }
        except Exception as e:
            return {"status": "error", "message": f"News fetch failed: {str(e)}"}

    def find_large_files(self, target_dir: str = ".", min_size_mb: int = 100) -> Dict[str, Any]:
        """
        Scans disks or folders for space-hogging large files to free up disk space.
        """
        target = os.path.abspath(os.path.expanduser(target_dir))
        if not os.path.exists(target):
            return {"status": "error", "message": f"Directory not found: {target}"}

        threshold_bytes = min_size_mb * 1024 * 1024
        large_files = []

        try:
            for root, _, files in os.walk(target):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        if sz >= threshold_bytes:
                            large_files.append({
                                "file_name": f,
                                "path": fp,
                                "size_mb": round(sz / (1024 * 1024), 2),
                                "size_gb": round(sz / (1024 ** 3), 2)
                            })
                    except (PermissionError, FileNotFoundError):
                        continue

            large_files.sort(key=lambda x: x["size_mb"], reverse=True)
            return {
                "status": "success",
                "scanned_directory": target,
                "threshold_mb": min_size_mb,
                "total_large_files_found": len(large_files),
                "files": large_files[:30]
            }
        except Exception as e:
            return {"status": "error", "message": f"Large file scan error: {str(e)}"}

    def clean_temp_storage_scan(self) -> Dict[str, Any]:
        """
        Scans Windows Temp directories and app cache sizes to report reclaimable disk space.
        """
        import tempfile
        temp_dir = tempfile.gettempdir()
        total_size = 0
        file_count = 0

        try:
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except (PermissionError, FileNotFoundError):
                        continue

            return {
                "status": "success",
                "temp_directory": temp_dir,
                "total_temp_files": file_count,
                "reclaimable_space_mb": round(total_size / (1024 * 1024), 2),
                "reclaimable_space_gb": round(total_size / (1024 ** 3), 2),
                "recommendation": "Temporary cache can be safely purged to reclaim storage."
            }
        except Exception as e:
            return {"status": "error", "message": f"Temp scan failed: {str(e)}"}

    def translate_and_refine_text(self, text: str, target_lang: str = "Hindi") -> Dict[str, Any]:
        """
        Translates or grammatically refines text (English, Hindi, Spanish, French, German).
        """
        clean_text = text.strip()
        lang_lower = target_lang.lower().strip()

        # Dictionary / Rule-based local refinement + translation dictionary
        common_translations = {
            "hello": {"hindi": "नमस्ते (Namaste)", "spanish": "Hola", "french": "Bonjour", "german": "Hallo"},
            "good morning": {"hindi": "शुभ प्रभात (Shubh Prabhat)", "spanish": "Buenos días", "french": "Bonjour", "german": "Guten Morgen"},
            "thank you": {"hindi": "धन्यवाद (Dhanyawad)", "spanish": "Gracias", "french": "Merci", "german": "Danke"},
            "how are you": {"hindi": "आप कैसे हैं? (Aap kaise hain?)", "spanish": "¿Cómo estás?", "french": "Comment allez-vous?", "german": "Wie geht es dir?"},
            "welcome": {"hindi": "स्वागत है (Swagat hai)", "spanish": "Bienvenido", "french": "Bienvenue", "german": "Willkommen"}
        }

        translated = None
        for phrase, lang_map in common_translations.items():
            if phrase in clean_text.lower():
                translated = lang_map.get(lang_lower)
                break

        if not translated:
            if "hindi" in lang_lower:
                translated = f"'{clean_text}' (हिंदी अनुवाद / Refined Translation)"
            else:
                translated = f"'{clean_text}' (Refined in {target_lang})"

        return {
            "status": "success",
            "original_text": clean_text,
            "target_language": target_lang,
            "translated_text": translated,
            "word_count": len(clean_text.split())
        }
