"""
Parse uploaded files (PDF, DOCX, TXT) into plain text.
"""
import io


def parse_file(file_bytes: bytes, filename: str) -> str:
    """
    Parse file bytes into a plain text string.
    Supports: .pdf, .docx, .txt (and any other file treated as UTF-8 text).
    """
    name = filename.lower()

    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
        return "\n\n".join(pages)

    elif name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    else:
        # .txt or any unknown extension — treat as UTF-8 text
        return file_bytes.decode("utf-8", errors="replace")
