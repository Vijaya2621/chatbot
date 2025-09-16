import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

class PDFProcessor:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def process_pdf(self, file_path: str):
        try:
            # Load PDF
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            if not documents:
                raise ValueError("No content found in PDF")
            
            # Split documents
            texts = self.text_splitter.split_documents(documents)
            
            if not texts:
                raise ValueError("No text chunks created from PDF")
            
            # Create vector store
            vector_store = FAISS.from_documents(texts, self.embeddings)
            
            # Clean up uploaded file
            os.remove(file_path)
            return vector_store
            
        except Exception as e:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e