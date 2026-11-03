
import io
from pathlib import Path

import pymupdf as fitz
import pandas as pd
from docx import Document as WordDocument


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}


def extract_text(file_bytes: bytes, filename: str) -> str:
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file format.")

    if extension == ".pdf":
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            if pdf.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported.")

            pages = []
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text")
                if text.strip():
                    pages.append(f"[Page {page_number}]\n{text}")

            result = "\n\n".join(pages)

    elif extension == ".docx":
        document = WordDocument(io.BytesIO(file_bytes))

        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        tables = []
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                tables.append(" | ".join(cells))

        result = "\n".join(paragraphs + tables)

    elif extension == ".txt":
        result = file_bytes.decode("utf-8-sig")

    elif extension == ".csv":
        dataframe = pd.read_csv(
            io.BytesIO(file_bytes),
            dtype=str,
            keep_default_na=False,
            nrows=10000
        )
        result = dataframe.to_csv(index=False)

    else:
        raise ValueError("Unsupported file format.")

    result = result.strip()

    if not result:
        raise ValueError("No extractable text was found in this file.")

    return result


def split_into_chunks(text: str, chunk_size=1200, overlap=150):
    if overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size.")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks
