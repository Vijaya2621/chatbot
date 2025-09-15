from persistent_storage import PersistentStorage
import time
import os
import shutil
from logger import session_logger, storage_logger
from langchain_community.vectorstores import FAISS

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
    session_logger.info(f"Updating session {session_id[:8]}... with PDF: {filename}")
    session = get_session(session_id)
    session_logger.info(f"Found existing session: {session is not None}")
    
    if session:
        # Merge with existing vector store if present
        if session.get("vector_store"):
            try:
                # Get all documents from both vector stores
                existing_docs = [session["vector_store"].docstore._dict[doc_id] for doc_id in session["vector_store"].docstore._dict]
                new_docs = [vector_store.docstore._dict[doc_id] for doc_id in vector_store.docstore._dict]
                all_docs = existing_docs + new_docs
                
                # Create new merged vector store
                embeddings = vector_store.embeddings
                session["vector_store"] = FAISS.from_documents(all_docs, embeddings)
                session_logger.info(f"Merged vector store for session {session_id[:8]}...")
            except Exception as e:
                # If merge fails, replace (fallback)
                session["vector_store"] = vector_store
                session_logger.warning(f"Vector merge failed, replaced for session {session_id[:8]}... Error: {e}")
        else:
            session["vector_store"] = vector_store
        
        # Update filename to show multiple documents (avoid duplicates)
        old_filename = session.get("filename", "")
        if old_filename and old_filename != "General Chat":
            # Split existing filenames and create a set to avoid duplicates
            existing_files = set(f.strip() for f in old_filename.split(","))
            if filename not in existing_files:
                existing_files.add(filename)
                session["filename"] = ", ".join(sorted(existing_files))
                session_logger.info(f"Updated filename: {session['filename']}")
            else:
                session_logger.info(f"Filename already exists: {filename}")
        else:
            session["filename"] = filename
            session_logger.info(f"Set new filename: {filename}")
            
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
    session_file = f"{storage.storage_dir}/sessions/{session_id}.json"
    if os.path.exists(session_file):
        os.remove(session_file)
    
    # Delete vector store
    vector_path = f"{storage.storage_dir}/vectors/{session_id}"
    if os.path.exists(vector_path):
        shutil.rmtree(vector_path)

def cleanup_old_sessions():
    """Clean up sessions older than 7 days"""
    storage.cleanup_old_sessions(7)