import os
import json
import pickle
import shutil
from typing import Dict, List, Optional
import time
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class PersistentStorage:
    def __init__(self, storage_dir="data"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(f"{storage_dir}/sessions", exist_ok=True)
        os.makedirs(f"{storage_dir}/vectors", exist_ok=True)
    
    def save_session(self, session_id: str, session_data: dict):
        """Save session data to file"""
        session_file = f"{self.storage_dir}/sessions/{session_id}.json"
        
        # Prepare data for JSON (exclude vector_store)
        json_data = {
            "session_id": session_id,
            "filename": session_data.get("filename", ""),
            "chat_history": session_data.get("chat_history", []),
            "created_at": session_data.get("created_at", time.time()),
            "last_activity": time.time(),
            "has_vector_store": session_data.get("vector_store") is not None
        }
        
        with open(session_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Save vector store separately if exists
        if session_data.get("vector_store"):
            vector_path = f"{self.storage_dir}/vectors/{session_id}"
            try:
                session_data["vector_store"].save_local(vector_path)
            except Exception as e:
                pass
    
    def load_session(self, session_id: str) -> Optional[dict]:
        """Load session data from file"""
        session_file = f"{self.storage_dir}/sessions/{session_id}.json"
        
        if not os.path.exists(session_file):
            return None
        
        try:
            with open(session_file, 'r') as f:
                json_data = json.load(f)
            
            session_data = {
                "session_id": json_data["session_id"],
                "filename": json_data["filename"],
                "chat_history": json_data["chat_history"],
                "created_at": json_data["created_at"],
                "last_activity": json_data["last_activity"],
                "vector_store": None
            }
            
            # Load vector store if exists
            if json_data.get("has_vector_store"):
                vector_path = f"{self.storage_dir}/vectors/{session_id}"
                if os.path.exists(vector_path):
                    try:
                        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                        vector_store = FAISS.load_local(vector_path, embeddings, allow_dangerous_deserialization=True)
                        session_data["vector_store"] = vector_store
                    except Exception as e:
                        pass
            
            return session_data
            
        except Exception as e:
            return None
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        session_file = f"{self.storage_dir}/sessions/{session_id}.json"
        return os.path.exists(session_file)
    
    def cleanup_old_sessions(self, max_age_days=7):
        """Clean up sessions older than max_age_days"""
        sessions_dir = f"{self.storage_dir}/sessions"
        vectors_dir = f"{self.storage_dir}/vectors"
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        for filename in os.listdir(sessions_dir):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                session_file = os.path.join(sessions_dir, filename)
                
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    if current_time - data.get("last_activity", 0) > max_age_seconds:
                        # Remove session file
                        os.remove(session_file)
                        
                        # Remove vector store if exists
                        vector_path = os.path.join(vectors_dir, session_id)
                        if os.path.exists(vector_path):
                            shutil.rmtree(vector_path)
                        
                        pass
                        
                except Exception as e:
                    pass