from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from pdf_processor import PDFProcessor
import session_manager
from chat_handler import ChatHandler
from logger import main_logger, session_logger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
async def upload_pdf(file: UploadFile = File(...), session_id: str = None):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Use existing session_id or create new one
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
        
        # Update existing session or create new one (preserves chat history)
        session_manager.update_session_with_pdf(session_id, vector_store, file.filename)
        
        main_logger.info(f"PDF processed successfully: {file.filename} for session {session_id[:8]}...")
        return {"session_id": session_id, "filename": file.filename}
    
    except Exception as e:
        main_logger.error(f"PDF processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/chat")
async def chat(chat_message: ChatMessage):
    try:
        # Create session if it doesn't exist (for general chat without PDF)
        if not session_manager.get_session(chat_message.session_id):
            session_manager.create_session(chat_message.session_id, None, "General Chat")
            session_logger.info(f"Created new session: {chat_message.session_id[:8]}...")
        
        response = chat_handler.handle_message(chat_message.message, chat_message.session_id)
        return ChatResponse(response=response, session_id=chat_message.session_id)
    except Exception as e:
        main_logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    history = session_manager.get_chat_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"history": history}

if __name__ == "__main__":
    import uvicorn
    import threading
    import time
    
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