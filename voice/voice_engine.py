"""Voice engine module for offline Text-to-Speech (TTS) and Speech-to-Text (STT) mic capture."""
import queue
import threading
import time
from typing import Optional, Callable
import speech_recognition as sr
import pyttsx3
from rich.console import Console

console = Console()

class VoiceEngine:
    """Non-blocking offline TTS engine and ambient-noise aware speech recognition worker."""

    def __init__(self, on_speech_recognized: Optional[Callable[[str], None]] = None,
                 on_status_change: Optional[Callable[[str], None]] = None):
        self.on_speech_recognized = on_speech_recognized
        self.on_status_change = on_status_change
        self.is_listening = False
        self.is_tts_enabled = True
        
        self.tts_queue = queue.Queue()
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def _tts_worker(self):
        """Dedicated background thread for pyttsx3 speech synthesis to avoid GUI freezing and COM issues."""
        while True:
            text = self.tts_queue.get()
            if text is None:
                break
            if not self.is_tts_enabled:
                self.tts_queue.task_done()
                continue

            try:
                # Initialize per-session engine on Windows thread to prevent COM concurrency conflicts
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.setProperty("volume", 0.9)
                voices = engine.getProperty("voices")
                if voices:
                    engine.setProperty("voice", voices[0].id)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                console.print(f"[bold red][VoiceEngine][/bold red] TTS synthesis error: {e}")
            finally:
                self.tts_queue.task_done()

    def speak(self, text: str):
        """Enqueues text for non-blocking speech synthesis."""
        if not text or not text.strip():
            return
        # Clean markdown characters for pleasant speech
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace("[", "").replace("]", "")
        self.tts_queue.put(clean_text)

    def listen_mic(self) -> Optional[str]:
        """
        Captures microphone audio synchronously with ambient noise adjustment and returns transcribed string.
        """
        try:
            with sr.Microphone() as source:
                if self.on_status_change:
                    self.on_status_change("Calibrating ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                
                if self.on_status_change:
                    self.on_status_change("Listening for voice input...")
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=12)
                
                if self.on_status_change:
                    self.on_status_change("Transcribing speech...")
                text = self.recognizer.recognize_google(audio)
                console.print(f"[bold green][VoiceEngine][/bold green] Transcribed: '{text}'")
                return text
        except sr.WaitTimeoutError:
            if self.on_status_change:
                self.on_status_change("Listening timed out.")
            return None
        except sr.UnknownValueError:
            if self.on_status_change:
                self.on_status_change("Could not understand audio.")
            return None
        except sr.RequestError as e:
            if self.on_status_change:
                self.on_status_change(f"Speech service error: {e}")
            return None
        except Exception as e:
            console.print(f"[bold red][VoiceEngine][/bold red] Microphone error (PyAudio / device): {e}")
            if self.on_status_change:
                self.on_status_change(f"Microphone unavailable: {str(e)[:40]}")
            return None

    def start_listening_async(self):
        """Starts a background thread to listen once and invoke callback with transcribed text."""
        def _run():
            self.is_listening = True
            text = self.listen_mic()
            self.is_listening = False
            if text and self.on_speech_recognized:
                self.on_speech_recognized(text)
            if self.on_status_change:
                self.on_status_change("Idle")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def toggle_tts(self, enabled: bool):
        """Toggles audio speech output on/off."""
        self.is_tts_enabled = enabled
