import logfire
from langchain_community.document_loaders import PyMuPDFLoader

def parse_pdf_pymupdf(file_path: str) -> str:
    with logfire.span("PDF Parsing with PyMuPDF", filename=file_path):
        try:
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
            return "\n".join([doc.page_content for doc in documents if doc.page_content])
        except Exception as e:
            logfire.error(f"Error parsing PDF file {file_path}: {e}")
            return ""

        