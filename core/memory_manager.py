"""Memory Manager module using ChromaDB and SQLite for episodic, semantic, and conversational persistence."""
import os
import sqlite3
import datetime
import json
import uuid
from typing import List, Dict, Any, Optional
from rich.console import Console

console = Console()

class MemoryManager:
    """Manages long-term vector embeddings via ChromaDB and structured conversation history via SQLite."""

    def __init__(self, data_dir: str = "./data/memory"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.chroma_dir = os.path.join(self.data_dir, "chroma")
        os.makedirs(self.chroma_dir, exist_ok=True)
        self.sqlite_path = os.path.join(self.data_dir, "chat_history.db")
        
        self.chroma_client = None
        self.collection = None
        self._init_sqlite()
        self._init_chromadb()

    def _init_sqlite(self):
        """Initializes SQLite database for structured conversation logging and notes."""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id TEXT PRIMARY KEY,
                        role TEXT NOT NULL,
                        message TEXT NOT NULL,
                        metadata TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes_store (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            console.print(f"[bold green][MemoryManager][/bold green] SQLite database initialized at {self.sqlite_path}")
        except Exception as e:
            console.print(f"[bold red][MemoryManager][/bold red] SQLite init error: {e}")

    def _init_chromadb(self):
        """Initializes local ChromaDB client and default collection."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
            self.collection = self.chroma_client.get_or_create_collection(
                name="agent_memory",
                metadata={"description": "Long-term episodic and factual memory"}
            )
            console.print(f"[bold green][MemoryManager][/bold green] ChromaDB vector store initialized at {self.chroma_dir}")
        except Exception as e:
            console.print(f"[bold yellow][MemoryManager][/bold yellow] ChromaDB initialization fallback: {e}")
            self.chroma_client = None
            self.collection = None

    def store_interaction(self, role: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Persists a message in SQLite and ChromaDB vector store."""
        msg_id = str(uuid.uuid4())
        meta_dict = metadata or {}
        meta_dict["role"] = role
        meta_dict["timestamp"] = datetime.datetime.now().isoformat()
        
        # SQLite storage
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversation_history (id, role, message, metadata) VALUES (?, ?, ?, ?)",
                    (msg_id, role, message, json.dumps(meta_dict))
                )
                conn.commit()
        except Exception as e:
            console.print(f"[bold red][MemoryManager][/bold red] Failed to store interaction in SQLite: {e}")

        # Vector memory storage
        if self.collection is not None and len(message.strip()) > 0:
            try:
                # Flat metadata for chromadb
                clean_meta = {k: str(v) for k, v in meta_dict.items()}
                self.collection.add(
                    documents=[message],
                    metadatas=[clean_meta],
                    ids=[msg_id]
                )
            except Exception as e:
                console.print(f"[bold yellow][MemoryManager][/bold yellow] Vector memory add warning: {e}")

    def get_recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent conversation history from SQLite."""
        history = []
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, role, message, metadata, timestamp FROM conversation_history ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                for row in reversed(rows):
                    meta = {}
                    try:
                        meta = json.loads(row[3]) if row[3] else {}
                    except Exception:
                        pass
                    history.append({
                        "id": row[0],
                        "role": row[1],
                        "message": row[2],
                        "metadata": meta,
                        "timestamp": row[4]
                    })
        except Exception as e:
            console.print(f"[bold red][MemoryManager][/bold red] Failed to retrieve history: {e}")
        return history

    def semantic_search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Searches long-term vector memory for relevant context."""
        results = []
        if self.collection is not None:
            try:
                query_res = self.collection.query(
                    query_texts=[query],
                    n_results=min(n_results, max(1, self.collection.count()))
                )
                if query_res and "documents" in query_res and query_res["documents"]:
                    docs = query_res["documents"][0]
                    metas = query_res["metadatas"][0] if "metadatas" in query_res else [{}] * len(docs)
                    dists = query_res.get("distances", [[]])[0] if "distances" in query_res else [0.0] * len(docs)
                    for doc, meta, dist in zip(docs, metas, dists):
                        results.append({
                            "document": doc,
                            "metadata": meta,
                            "distance": dist
                        })
            except Exception as e:
                console.print(f"[bold yellow][MemoryManager][/bold yellow] Semantic search error: {e}")
        return results

    def clear_history(self):
        """Clears local conversation history table."""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversation_history")
                conn.commit()
            console.print("[bold green][MemoryManager][/bold green] Conversation history cleared.")
        except Exception as e:
            console.print(f"[bold red][MemoryManager][/bold red] Failed to clear history: {e}")
