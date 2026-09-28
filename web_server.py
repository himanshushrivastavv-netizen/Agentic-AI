"""FastAPI Localhost Web Server for Agentic AI Assistant.

Provides interactive Web GUI on http://localhost:8000 with live telemetry,
ReAct thought-action-observation streaming, and speech support.
"""
import os
import sys
import psutil
import json
from typing import Dict, Any, List
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from rich.console import Console

from core.agent_brain import ReActAgentBrain
from core.memory_manager import MemoryManager
from core.safety_guard import SafetyGuard, ActionRiskLevel

console = Console()
app = FastAPI(title="Agentic AI Web Interface", version="1.0.0")

# Initialize AI Backend
memory = MemoryManager()
safety = SafetyGuard()
agent = ReActAgentBrain(memory_manager=memory, safety_guard=safety)

class ChatRequest(BaseModel):
    message: str

@app.get("/api/telemetry")
async def get_telemetry():
    """Returns live hardware telemetry."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()
        batt_pct = battery.percent if battery else 100.0
        batt_status = "Charging" if (battery and battery.power_plugged) else "Battery"

        return {
            "status": "success",
            "cpu": cpu,
            "ram": ram.percent,
            "ram_used_gb": round(ram.used / (1024 ** 3), 1),
            "ram_total_gb": round(ram.total / (1024 ** 3), 1),
            "disk": disk.percent,
            "disk_used_gb": round(disk.used / (1024 ** 3), 1),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "battery": batt_pct,
            "battery_status": batt_status
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Processes user query through the ReAct Agent reasoning loop."""
    user_msg = req.message.strip()
    if not user_msg:
        return JSONResponse(status_code=400, content={"error": "Empty message"})

    steps_recorded = []

    def _step_tracker(step_payload: Dict[str, Any]):
        steps_recorded.append(step_payload)

    # Attach temporary step callback
    agent.on_step_callback = _step_tracker
    try:
        final_answer = agent.execute_react_cycle(user_msg)
        return {
            "status": "success",
            "user_query": user_msg,
            "steps": steps_recorded,
            "final_answer": final_answer
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "steps": steps_recorded
        }

@app.get("/api/history")
async def get_history():
    """Retrieves SQLite conversation history."""
    return {"history": memory.get_recent_history(limit=50)}

@app.post("/api/clear")
async def clear_history():
    """Clears history."""
    memory.clear_history()
    return {"status": "success", "message": "History cleared"}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves modern dark-themed web workstation."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agentic AI Desktop Workstation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #090c10;
      --bg-surface: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --accent-blue: #2f81f7;
      --accent-purple: #8957e5;
      --accent-green: #238636;
      --accent-amber: #d29922;
      --accent-red: #f85149;
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
      --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'Fira Code', Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Top Navigation */
    header {
      background: var(--card-bg);
      border-bottom: 1px solid var(--card-border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-logo {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 0 15px rgba(47, 129, 247, 0.4);
    }

    .brand-title {
      font-size: 1.15rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }

    .brand-subtitle {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-pill {
      background: var(--bg-surface);
      border: 1px solid var(--card-border);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 0.82rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent-green);
      box-shadow: 0 0 8px var(--accent-green);
    }

    .status-dot.thinking { background: var(--accent-purple); box-shadow: 0 0 8px var(--accent-purple); }
    .status-dot.executing { background: var(--accent-amber); box-shadow: 0 0 8px var(--accent-amber); }
    .status-dot.healing { background: #e36209; box-shadow: 0 0 8px #e36209; }

    .btn-voice {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }

    .btn-voice:hover { background: #30363d; border-color: var(--accent-blue); }
    .btn-voice.active { background: var(--accent-red); border-color: var(--accent-red); }

    /* Main Grid */
    main {
      flex: 1;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    /* Telemetry Cards */
    .telemetry-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }

    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .metric-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .metric-value {
      font-size: 1.4rem;
      font-weight: 800;
      color: var(--text-main);
    }

    .progress-bar-bg {
      width: 100%;
      height: 6px;
      background: #21262d;
      border-radius: 3px;
      overflow: hidden;
    }

    .progress-bar-fill {
      height: 100%;
      width: 0%;
      background: var(--accent-blue);
      border-radius: 3px;
      transition: width 0.4s ease, background-color 0.4s ease;
    }

    /* Chat Area */
    .chat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      flex: 1;
      min-height: 480px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .chat-messages {
      flex: 1;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: calc(100vh - 350px);
    }

    .message-bubble {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 0.92rem;
      line-height: 1.5;
    }

    .message-bubble.user {
      align-self: flex-end;
      background: #1f6feb;
      color: #fff;
      border-bottom-right-radius: 4px;
    }

    .message-bubble.agent {
      align-self: flex-start;
      background: var(--bg-surface);
      border: 1px solid var(--card-border);
      border-bottom-left-radius: 4px;
    }

    .message-bubble.thought {
      align-self: flex-start;
      background: #1b1726;
      border: 1px solid var(--accent-purple);
      color: #d2bcf3;
      font-size: 0.85rem;
    }

    .message-bubble.tool {
      align-self: flex-start;
      background: #1e1912;
      border: 1px solid var(--accent-amber);
      color: #f1e05a;
      font-family: var(--font-mono);
      font-size: 0.82rem;
    }

    .message-bubble.observation {
      align-self: flex-start;
      background: #0f1c15;
      border: 1px solid var(--accent-green);
      color: #7ee787;
      font-family: var(--font-mono);
      font-size: 0.82rem;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .bubble-meta {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 700;
    }

    pre, code {
      font-family: var(--font-mono);
      background: #0d1117;
      padding: 8px 12px;
      border-radius: 6px;
      display: block;
      margin: 8px 0;
      overflow-x: auto;
    }

    code:not(pre code) {
      display: inline;
      padding: 2px 6px;
    }

    /* Quick Actions */
    .quick-actions {
      padding: 10px 16px;
      background: var(--bg-surface);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .quick-chip {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 0.78rem;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s ease;
    }

    .quick-chip:hover {
      background: #30363d;
      color: var(--text-main);
      border-color: var(--accent-blue);
    }

    /* Input Controls */
    .input-bar {
      padding: 14px 16px;
      background: var(--card-bg);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 10px;
    }

    .input-box {
      flex: 1;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text-main);
      padding: 12px 16px;
      font-size: 0.95rem;
      font-family: var(--font-main);
      outline: none;
      transition: border-color 0.2s;
    }

    .input-box:focus {
      border-color: var(--accent-blue);
    }

    .btn-send {
      background: var(--accent-blue);
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0 24px;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    .btn-send:hover { opacity: 0.9; }
    .btn-send:disabled { background: #30363d; cursor: not-allowed; }

    @media (max-width: 768px) {
      .telemetry-bar { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-logo">⚡</div>
      <div>
        <div class="brand-title">AGENTIC AI</div>
        <div class="brand-subtitle">Autonomous Desktop & Diagnostic Copilot</div>
      </div>
    </div>
    <div class="header-controls">
      <div class="status-pill">
        <div class="status-dot" id="statusDot"></div>
        <span id="statusText">Idle</span>
      </div>
      <button class="btn-voice" id="voiceBtn" onclick="toggleVoiceInput()">🎙️ Voice Input</button>
    </div>
  </header>

  <main>
    <!-- Telemetry Cards -->
    <div class="telemetry-bar">
      <div class="metric-card">
        <div class="metric-header"><span>💻 CPU LOAD</span><span id="cpuVal">--%</span></div>
        <div class="metric-value" id="cpuMain">0%</div>
        <div class="progress-bar-bg"><div class="progress-bar-fill" id="cpuBar"></div></div>
      </div>
      <div class="metric-card">
        <div class="metric-header"><span>🧠 MEMORY USAGE</span><span id="ramVal">-- GB</span></div>
        <div class="metric-value" id="ramMain">0%</div>
        <div class="progress-bar-bg"><div class="progress-bar-fill" id="ramBar"></div></div>
      </div>
      <div class="metric-card">
        <div class="metric-header"><span>💾 SYSTEM DISK</span><span id="diskVal">-- GB</span></div>
        <div class="metric-value" id="diskMain">0%</div>
        <div class="progress-bar-bg"><div class="progress-bar-fill" id="diskBar"></div></div>
      </div>
      <div class="metric-card">
        <div class="metric-header"><span>🔋 POWER</span><span id="battVal">AC</span></div>
        <div class="metric-value" id="battMain">100%</div>
        <div class="progress-bar-bg"><div class="progress-bar-fill" id="battBar"></div></div>
      </div>
    </div>

    <!-- Chat Workstation -->
    <div class="chat-card">
      <div class="chat-messages" id="chatFeed">
        <div class="message-bubble agent">
          <div class="bubble-meta">🤖 AGENTIC AI WORKSTATION</div>
          👋 <strong>Welcome!</strong> I am your Agentic AI Assistant running live on <code>localhost:8000</code>.<br><br>
          I can organize local directories, diagnose system health, audit web security headers, execute self-healing Python scripts in sandbox, and research online topics.
        </div>
      </div>

      <!-- Quick Action Pills -->
      <div class="quick-actions">
        <div class="quick-chip" onclick="quickPrompt('WhatsApp bhejo 9876543210 ko message: Meeting at 5 PM')">💬 Send WhatsApp</div>
        <div class="quick-chip" onclick="quickPrompt('Send email to manager@example.com')">✉️ Send Email</div>
        <div class="quick-chip" onclick="quickPrompt('Mera laptop kitna saal chalega? Deep hardware health prediction do')">🔮 Laptop Lifespan Predictor</div>
        <div class="quick-chip" onclick="quickPrompt('Benchmark my computer compute power and memory speed')">⚡ Speed Benchmark</div>
        <div class="quick-chip" onclick="quickPrompt('Generate QR code for https://google.com')">📱 QR Generator</div>
        <div class="quick-chip" onclick="quickPrompt('Delhi ka live weather report batao')">🌤️ Live Weather</div>
        <div class="quick-chip" onclick="quickPrompt('Convert 100 USD to INR')">💱 Currency Converter</div>
        <div class="quick-chip" onclick="quickPrompt('Draft a sick leave email for my manager')">✍️ Draft Leave Email</div>
        <div class="quick-chip" onclick="quickPrompt('Show my todo task list')">📋 Todo Tasks</div>
        <div class="quick-chip" onclick="quickPrompt('Show system health and top memory consumers')">📊 System Diagnostics</div>
        <div class="quick-chip" onclick="quickPrompt('Scan temporary files to reclaim storage')">🧹 Clean Disk Scan</div>
        <div class="quick-chip" onclick="clearConversation()">🧹 Clear Chat</div>
      </div>

      <!-- Input Bar -->
      <div class="input-bar">
        <input type="text" id="userInput" class="input-box" placeholder="Ask Agentic AI to diagnose, organize, research, or execute code..." onkeydown="if(event.key==='Enter') sendMessage()">
        <button class="btn-send" id="sendBtn" onclick="sendMessage()">Send ➔</button>
      </div>
    </div>
  </main>

  <script>
    // Live Telemetry Poller
    async function updateTelemetry() {
      try {
        const res = await fetch('/api/telemetry');
        const data = await res.json();
        if (data.status === 'success') {
          // CPU
          document.getElementById('cpuMain').innerText = data.cpu.toFixed(1) + '%';
          document.getElementById('cpuBar').style.width = data.cpu + '%';
          setBarColor('cpuBar', data.cpu);

          // RAM
          document.getElementById('ramMain').innerText = data.ram.toFixed(1) + '%';
          document.getElementById('ramVal').innerText = `${data.ram_used_gb} / ${data.ram_total_gb} GB`;
          document.getElementById('ramBar').style.width = data.ram + '%';
          setBarColor('ramBar', data.ram);

          // Disk
          document.getElementById('diskMain').innerText = data.disk.toFixed(1) + '%';
          document.getElementById('diskVal').innerText = `${data.disk_used_gb} GB`;
          document.getElementById('diskBar').style.width = data.disk + '%';

          // Battery
          document.getElementById('battMain').innerText = data.battery.toFixed(0) + '%';
          document.getElementById('battVal').innerText = data.battery_status;
          document.getElementById('battBar').style.width = data.battery + '%';
        }
      } catch (err) {}
    }

    function setBarColor(id, pct) {
      const el = document.getElementById(id);
      if (pct > 85) el.style.backgroundColor = 'var(--accent-red)';
      else if (pct > 65) el.style.backgroundColor = 'var(--accent-amber)';
      else el.style.backgroundColor = 'var(--accent-blue)';
    }

    setInterval(updateTelemetry, 2000);
    updateTelemetry();

    // Chat handling
    async function sendMessage() {
      const input = document.getElementById('userInput');
      const text = input.value.trim();
      if (!text) return;

      appendBubble('user', '👤 YOU', text);
      input.value = '';

      setAgentStatus('Thinking...', 'thinking');
      document.getElementById('sendBtn').disabled = true;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();

        if (data.status === 'success') {
          // Render intermediate thoughts & tool calls
          if (data.steps && data.steps.length > 0) {
            data.steps.forEach(step => {
              if (step.type === 'thought') {
                appendBubble('thought', '🧠 AGENT THOUGHT', step.content);
              } else if (step.type === 'tool_call') {
                appendBubble('tool', '⚙️ TOOL EXECUTION', step.content);
              } else if (step.type === 'observation') {
                const obs = typeof step.content === 'object' ? JSON.stringify(step.content, null, 2) : step.content;
                appendBubble('observation', '🔬 OBSERVATION', obs);
              }
            });
          }
          // Render Final Answer
          appendBubble('agent', '🤖 AGENTIC AI', formatMarkdown(data.final_answer));
          speakText(data.final_answer);
        } else {
          appendBubble('agent', '⚠️ ERROR', data.error || 'Failed processing request.');
        }
      } catch (e) {
        appendBubble('agent', '⚠️ CONNECTION ERROR', e.message);
      } finally {
        setAgentStatus('Idle', 'idle');
        document.getElementById('sendBtn').disabled = false;
      }
    }

    function appendBubble(role, meta, content) {
      const feed = document.getElementById('chatFeed');
      const bubble = document.createElement('div');
      bubble.className = `message-bubble ${role}`;
      bubble.innerHTML = `<div class="bubble-meta">${meta}</div><div>${content}</div>`;
      feed.appendChild(bubble);
      feed.scrollTop = feed.scrollHeight;
    }

    function quickPrompt(text) {
      document.getElementById('userInput').value = text;
      sendMessage();
    }

    async function clearConversation() {
      await fetch('/api/clear', { method: 'POST' });
      const feed = document.getElementById('chatFeed');
      feed.innerHTML = `
        <div class="message-bubble agent">
          <div class="bubble-meta">🤖 AGENTIC AI WORKSTATION</div>
          🧹 Conversation history cleared. What would you like to explore next?
        </div>
      `;
    }

    function setAgentStatus(label, stateClass) {
      const dot = document.getElementById('statusDot');
      const text = document.getElementById('statusText');
      text.innerText = label;
      dot.className = 'status-dot ' + (stateClass || '');
    }

    function formatMarkdown(text) {
      if (!text) return '';
      return text
        .replace(/### (.*?)\\n/g, '<h3 style="margin: 8px 0; font-size: 1.05rem;">$1</h3>')
        .replace(/#### (.*?)\\n/g, '<h4 style="margin: 6px 0; font-size: 0.95rem; color: var(--text-muted);">$1</h4>')
        .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
        .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
        .replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\\n/g, '<br>');
    }

    // Web Speech API Voice Input
    let recognition;
    function toggleVoiceInput() {
      const btn = document.getElementById('voiceBtn');
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Web Speech API is not supported in this browser. Please use Chrome or Edge.');
        return;
      }

      if (recognition && btn.classList.contains('active')) {
        recognition.stop();
        btn.classList.remove('active');
        btn.innerText = '🎙️ Voice Input';
        return;
      }

      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        btn.classList.add('active');
        btn.innerText = '🔴 Listening...';
        setAgentStatus('Listening...', 'thinking');
      };

      recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        document.getElementById('userInput').value = text;
        sendMessage();
      };

      recognition.onend = () => {
        btn.classList.remove('active');
        btn.innerText = '🎙️ Voice Input';
        setAgentStatus('Idle', 'idle');
      };

      recognition.start();
    }

    // Speech synthesis helper
    function speakText(text) {
      if (!('speechSynthesis' in window)) return;
      const clean = text.replace(/[*#`_]/g, '');
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

def start_server(port: int = 5000):
    """Starts FastAPI uvicorn server with dynamic port selection."""
    import socket
    target_port = port
    for p in [port, 5050, 8080, 8088, 3000]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', p))
            s.close()
            target_port = p
            break
        except Exception:
            continue

    console.print(f"[bold green]Starting Agentic AI Localhost Web Server on http://localhost:{target_port}[/bold green]")
    uvicorn.run(app, host="127.0.0.1", port=target_port, log_level="warning")

if __name__ == "__main__":
    start_server(5000)
