import os
import sys
import logfire
def parse_text(file_path: str):
    with logfire.span("Text Parsing", filename=file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            logfire.error(f"Error parsing text file {file_path}: {e}")
            return ""


