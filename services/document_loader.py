import random
import re

import requests
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.docstore.document import Document


def load_document_text(url: str) -> str | None:
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
    random.shuffle(chunks)

    if num_topics is not None:
        chunks = chunks[:num_topics]

    return chunks
