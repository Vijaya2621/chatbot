from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import json
import uvicorn
import threading
import time
from pdf_processor import PDFProcessor
import session_manager
from chat_handler import ChatHandler
from logger import main_logger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://chatbot-gamma-tan.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
pdf_processor = PDFProcessor()
chat_handler = ChatHandler()

class ChatMessage(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), session_id: str = Form(None)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        file_path = f"uploads/{session_id}_{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process PDF and create vector store
        vector_store = pdf_processor.process_pdf(file_path)
        
        # Update existing session or create new one
        updated_session = session_manager.update_session_with_pdf(session_id, vector_store, file.filename)
        
        main_logger.info(f"PDF processed: {file.filename} for session {session_id[:8]}...")
        return {"session_id": session_id, "filename": updated_session.get("filename", file.filename)}
    
    except Exception as e:
        main_logger.error(f"PDF processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/chat")
async def chat(chat_message: ChatMessage):
    try:
        # Create session if it doesn't exist
        if not session_manager.get_session(chat_message.session_id):
            session_manager.create_session(chat_message.session_id, None, "General Chat")
        
        response = chat_handler.handle_message(chat_message.message, chat_message.session_id)
        return ChatResponse(response=response, session_id=chat_message.session_id)
    except Exception as e:
        main_logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Check if session has vector store from JSON data
    session_file = f"data/sessions/{session_id}.json"
    has_vector_store = False
    if os.path.exists(session_file):
        try:
            with open(session_file, 'r') as f:
                json_data = json.load(f)
            has_vector_store = json_data.get("has_vector_store", False)
        except:
            pass
    
    return {
        "history": session.get("chat_history", []),
        "filename": session.get("filename", ""),
        "has_vector_store": has_vector_store
    }

@app.delete("/session/{session_id}")
async def delete_session_endpoint(session_id: str):
    try:
        session_manager.delete_session(session_id)
        main_logger.info(f"Session deleted: {session_id[:8]}...")
        return {"message": "Session deleted successfully"}
    except Exception as e:
        main_logger.error(f"Session deletion error: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

if __name__ == "__main__":
    # Start cleanup task in background
    def cleanup_task():
        while True:
            time.sleep(24 * 60 * 60)  # Run daily
            try:
                session_manager.cleanup_old_sessions()
                main_logger.info("Daily cleanup completed")
            except Exception as e:
                main_logger.error(f"Cleanup error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    
    main_logger.info("Starting PDF Chatbot server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)