from persistent_storage import PersistentStorage
import time
from logger import session_logger, storage_logger

# Initialize persistent storage
storage = PersistentStorage()

# In-memory cache for active sessions
active_sessions = {}

def create_session(session_id: str, vector_store, filename: str):
    session_data = {
        "session_id": session_id,
        "vector_store": vector_store,
        "filename": filename or "General Chat",
        "chat_history": [],
        "created_at": time.time(),
        "last_activity": time.time()
    }
    
    # Cache in memory
    active_sessions[session_id] = session_data
    
    # Save to disk
    storage.save_session(session_id, session_data)
    
    session_logger.info(f"Session created: {session_id[:8]}...")
    return session_data

def update_session_with_pdf(session_id: str, vector_store, filename: str):
    """Update existing session with PDF data, preserving chat history"""
    session = get_session(session_id)
    
    if session:
        # Update existing session
        session["vector_store"] = vector_store
        session["filename"] = filename
        session["last_activity"] = time.time()
        
        # Update cache
        active_sessions[session_id] = session
        
        # Save to disk
        storage.save_session(session_id, session)
        
        return session
    else:
        # Create new session if none exists
        return create_session(session_id, vector_store, filename)

def get_session(session_id: str):
    # Try memory cache first
    if session_id in active_sessions:
        return active_sessions[session_id]
    
    # Load from disk
    session_data = storage.load_session(session_id)
    if session_data:
        # Cache in memory
        active_sessions[session_id] = session_data
        return session_data
    
    return None

def add_message(session_id: str, role: str, content: str):
    session = get_session(session_id)
    if session:
        session["chat_history"].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        session["last_activity"] = time.time()
        
        # Update cache
        active_sessions[session_id] = session
        
        # Save to disk
        storage.save_session(session_id, session)

def get_chat_history(session_id: str):
    session = get_session(session_id)
    return session["chat_history"] if session else []

def delete_session(session_id: str):
    """Delete a specific session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
    
    # Delete from disk
    import os
    session_file = f"{storage.storage_dir}/sessions/{session_id}.json"
    if os.path.exists(session_file):
        os.remove(session_file)
    
    # Delete vector store
    vector_path = f"{storage.storage_dir}/vectors/{session_id}"
    if os.path.exists(vector_path):
        import shutil
        shutil.rmtree(vector_path)

def cleanup_old_sessions():
    """Clean up sessions older than 7 days"""
    storage.cleanup_old_sessions(7)