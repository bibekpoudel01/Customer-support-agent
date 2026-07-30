import os
import re 
from typing import List
import logfire
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv(override=True)
os.environ['HF_TOKEN'] = os.getenv("HF_TOKEN", "")

_EMBEDDINGS_CACHE = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def create_semantic_chunks(documents: List[Document]) -> List[Document]:
    """
    Splits documents into chunks using SemanticChunker and cleans up unwanted newlines.
    """
    if not documents:
        return []

    try:
        splitter = SemanticChunker(
            embeddings=_EMBEDDINGS_CACHE,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95.0 
        )
        
        chunks = splitter.split_documents(documents)
        
   
        for chunk in chunks:
            chunk.metadata['cleaned'] = True
            chunk.page_content = re.sub(r'\s+', ' ', chunk.page_content).strip()
            
            

        logfire.info(f"✅ Created and cleaned {len(chunks)} chunks from {len(documents)} documents.")
        return chunks
        
    except Exception as e:
        logfire.error(f"Error creating chunks: {e}", exc_info=True)
        return []
    



