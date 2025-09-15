from langchain_community.llms import Ollama
import session_manager
import re
from logger import chat_logger

class ChatHandler:
    def __init__(self):
        self.llm = Ollama(model="mistral", temperature=0.7)
    
    def handle_message(self, message: str, session_id: str) -> str:
        chat_logger.info(f"Processing message from session {session_id[:8]}...")
        
        # Input validation
        if not message or not message.strip():
            return "Please enter a valid question or message."
        
        if len(message.strip()) < 2:
            return "Please enter a more detailed question."
        
        # Clean the message
        message = message.strip()
        
        # Get or create session (works without PDF too)
        session = session_manager.get_session(session_id)
        if not session:
            # Create session without PDF for general chat
            session = session_manager.create_session(session_id, None, "General Chat")
        
        # Store user message
        session_manager.add_message(session_id, "user", message)
        
        # Check if it's a personal info question
        if self._is_personal_question(message):
            response = self._handle_personal_question(message, session)
        # Check if it's about uploaded document
        elif session.get("vector_store") and self._is_document_question(message):
            response = self._handle_document_question(message, session)
        else:
            # General AI conversation
            response = self._handle_general_question(message, session)
        
        # Store assistant response
        session_manager.add_message(session_id, "assistant", response)
        
        chat_logger.info(f"Response generated for session {session_id[:8]}...")
        return response
    
    def _is_personal_question(self, message: str) -> bool:
        """Check if user is asking about personal information"""
        personal_keywords = [
            "my name", "what is my", "who am i", "remember", "i told you",
            "what did i say", "do you know my", "about me", "my age",
            "my job", "my work", "my hobby", "my favorite", "where do i"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in personal_keywords)
    
    def _is_document_question(self, message: str) -> bool:
        """Check if question is about the uploaded document"""
        doc_keywords = [
            "document", "pdf", "file", "text", "according to", "based on",
            "in the document", "what does it say", "from the file"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in doc_keywords)
    
    def _handle_personal_question(self, message: str, session: dict) -> str:
        """Handle questions about personal information"""
        message_lower = message.lower()
        
        # Search chat history for relevant personal info
        chat_history = session.get("chat_history", [])
        
        # Look for specific information
        if "name" in message_lower:
            for msg in reversed(chat_history):
                if msg["role"] == "user":
                    content = msg["content"].lower()
                    if "my name is" in content or "i am" in content:
                        # Extract name
                        if "my name is" in content:
                            name = content.split("my name is")[1].strip().split()[0]
                        else:
                            name = content.split("i am")[1].strip().split()[0]
                        return f"Your name is {name}."
            return "I don't know your name yet. Please tell me!"
        
        elif "age" in message_lower:
            for msg in reversed(chat_history):
                if msg["role"] == "user" and ("i am" in msg["content"].lower() and "years old" in msg["content"].lower()):
                    age_match = re.search(r'(\d+)\s*years?\s*old', msg["content"].lower())
                    if age_match:
                        return f"You are {age_match.group(1)} years old."
            return "I don't know your age. Please tell me!"
        
        elif "job" in message_lower or "work" in message_lower:
            for msg in reversed(chat_history):
                if msg["role"] == "user":
                    content = msg["content"].lower()
                    if "i work" in content or "my job" in content or "i am a" in content:
                        return f"Based on what you told me: {msg['content']}"
            return "I don't know about your work. Please tell me!"
        
        # General personal info search
        relevant_info = []
        for msg in reversed(chat_history[-10:]):  # Last 10 messages
            if msg["role"] == "user" and any(word in msg["content"].lower() for word in ["my", "i am", "i work", "i like", "i live"]):
                relevant_info.append(msg["content"])
        
        if relevant_info:
            context = "\n".join(relevant_info)
            prompt = f"Based on this personal information: {context}\n\nQuestion: {message}\n\nAnswer:"
            return self.llm.invoke(prompt)
        
        return "I don't have that information about you yet. Feel free to tell me more about yourself!"
    
    def _handle_document_question(self, message: str, session: dict) -> str:
        """Handle questions about uploaded document"""
        try:
            docs = session["vector_store"].similarity_search(message, k=3)
            if docs:
                context = "\n".join([doc.page_content for doc in docs[:2]])
                prompt = f"Context from document: {context}\n\nQuestion: {message}\n\nAnswer based on the document:"
                return self.llm.invoke(prompt)
            else:
                return "I couldn't find relevant information in the uploaded document."
        except Exception as e:
            chat_logger.error(f"Document search error: {e}")
            return "I couldn't search the document. Please try again."
    
    def _handle_general_question(self, message: str, session: dict) -> str:
        """Handle general AI questions"""
        # Include recent chat history for context
        chat_history = session.get("chat_history", [])
        recent_context = ""
        
        if len(chat_history) > 1:
            recent_messages = chat_history[-6:]  # Last 3 exchanges
            context_parts = []
            for msg in recent_messages:
                if msg["role"] == "user":
                    context_parts.append(f"User: {msg['content']}")
                else:
                    context_parts.append(f"Assistant: {msg['content']}")
            recent_context = "\n".join(context_parts)
        
        if recent_context:
            prompt = f"Previous conversation:\n{recent_context}\n\nUser: {message}\n\nAssistant:"
        else:
            prompt = f"User: {message}\n\nAssistant:"
        
        return self.llm.invoke(prompt)