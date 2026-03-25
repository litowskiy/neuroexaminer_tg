import random
import re

import requests
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain.docstore.document import Document


def load_document_text(url: str) -> str:
    match_ = re.search(r"/document/d/([a-zA-Z0-9-_]+)", url)
    if match_ is None:
        raise ValueError(f"Invalid Google Docs URL: {url}")
    doc_id = match_.group(1)

    response = requests.get(
        f"https://docs.google.com/document/d/{doc_id}/export?format=txt",
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def split_markdown_into_topics(
    markdown_text: str, num_topics: int | None = None
) -> list[Document]:
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
        ("######", "Header 6"),
    ]

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(markdown_text)

    # Если Markdown-заголовков нет (например, обычный .txt из Google Docs),
    # разбиваем текст на части по символам
    meaningful = [c for c in chunks if len(c.page_content.strip()) > 50]
    if not meaningful:
        fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        raw_chunks = fallback_splitter.split_text(markdown_text)
        chunks = [
            Document(
                page_content=chunk,
                metadata={"Header 1": "Документ", "Header 2": f"Раздел {i + 1}"},
            )
            for i, chunk in enumerate(raw_chunks)
            if len(chunk.strip()) > 50
        ]
    else:
        chunks = meaningful

    random.shuffle(chunks)

    if num_topics is not None:
        chunks = chunks[:num_topics]

    return chunks
