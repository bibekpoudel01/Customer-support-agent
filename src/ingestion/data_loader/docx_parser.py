import docx
import logfire


def parse_docx(file_path: str) -> str:
    try:
        logfire.info(f"Parsing DOCX file: {file_path}")
        doc = docx.Document(file_path)
        text = "\n".join(
            paragraph.text.strip()
            for paragraph in doc.paragraphs
            if paragraph.text.strip()
        )
        return text

    except Exception as e:
        logfire.error(f"Error parsing DOCX file {file_path}: {e}")
        return ""
