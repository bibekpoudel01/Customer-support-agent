import logfire
import traceback
import sys
from pathlib import Path
from typing import List
from langchain_core.documents import Document

try:
    from src.ingestion.data_loader import docx_parser, html_parser, json_parser, pdf_parser, txt_parser
except ImportError:
    logfire.error("Failed to import document parsers. Ensure the module paths are correct.")
    traceback.print_exc()
    sys.exit(1) 
logfire.configure(send_to_logfire=False)

def load_documents(sources: List[str]) -> List[Document]:
    """
    Load documents from URLs, PDF files/dirs, or TXT files.

    Args:
        sources: List of URLs or local file/directory paths.

    Returns:
        List of loaded Document objects.
    """
    docs: List[Document] = []

    for src in sources:
        file_path = Path(src)
        try:
            if file_path.suffix.lower() == '.pdf':
                content = pdf_parser.parse_pdf_pymupdf(str(file_path))
            elif file_path.suffix.lower() in ('.md', '.txt'):
                content = txt_parser.parse_text(str(file_path))
            elif file_path.suffix.lower() == '.docx':
                content = docx_parser.parse_docx(str(file_path))
            elif file_path.suffix.lower() == '.html':
                content = html_parser.parse_langchain_html(str(file_path))
            elif file_path.suffix.lower() == '.json':
                content = json_parser.json_loader(str(file_path))
            else:
                logfire.error(f"Unsupported file type: {file_path}")
                continue

            if content and content.strip():
                docs.append(Document(
                    page_content=content,
                    metadata={"source": str(file_path), "type": file_path.suffix.lower()}
                ))
        except Exception as e:
            logfire.error(f"Failed to load {file_path}: {e}")
            continue

    return docs


if __name__ == "__main__":

    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "DATA" / "true_data"

    files = [
        str(file)
        for file in data_dir.iterdir()
        if file.is_file()
    ]

    loaders = load_documents(files)

    print(f"Loaded {len(loaders)} documents")

    for doc in loaders:
        print(f"Source: {doc.metadata['source']}")