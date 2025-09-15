import logging
import os
from datetime import datetime

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/chatbot_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

# Create loggers for different modules
chat_logger = logging.getLogger("chat")
session_logger = logging.getLogger("session")
storage_logger = logging.getLogger("storage")
main_logger = logging.getLogger("main")