import os
import re
from datetime import datetime
from typing import List

import fitz  # PyMuPDF
import tiktoken
from bs4 import BeautifulSoup
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from markdown_it import MarkdownIt

def tiktoken_len(text: str) -> int:
    """Returns the number of tokens in a text string."""
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokens = tokenizer.encode(text)
    return len(tokens)


def load_documents(data_path: str, tmp_path: str) -> List[Document]:
    """
    Loads documents from the specified path, processes them, and returns a list of Document objects.

    Args:
        data_path (str): The path to the data directory.
        tmp_path (str): The path to a temporary directory to store normalized files.

    Returns:
        List[Document]: A list of LangChain Document objects.
    """
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)

    documents = []
    for filename in os.listdir(data_path):
        source_path = os.path.join(data_path, filename)
        if not os.path.isfile(source_path):
            continue

        file_type = filename.split('.')[-1].lower()
        created_at = datetime.fromtimestamp(os.path.getctime(source_path)).isoformat()
        modified_at = datetime.fromtimestamp(os.path.getmtime(source_path)).isoformat()

        if file_type == 'pdf':
            doc = fitz.open(source_path)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            # Normalize text
            text = re.sub(r'\s+', ' ', text).strip()
            # Save normalized text to temp file
            tmp_filepath = os.path.join(tmp_path, f"{os.path.splitext(filename)[0]}_normalized.txt")
            with open(tmp_filepath, 'w', encoding='utf-8') as f:
                f.write(text)

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=tiktoken_len,
            )
            chunks = text_splitter.split_text(text)
            for chunk in chunks:
                metadata = {
                    'source_path': source_path,
                    'file_type': file_type,
                    'section_header': '',
                    'created_at': created_at,
                    'modified_at': modified_at,
                }
                documents.append(Document(page_content=chunk, metadata=metadata))

        elif file_type == 'md':
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split content by headers
            sections = re.split(r'(^#+\s+.*$)', content, flags=re.MULTILINE)
            if sections[0].strip() == "":
                sections = sections[1:]

            # Process each section
            for i in range(0, len(sections), 2):
                header = sections[i].strip()
                section_content = sections[i+1].strip()

                # Clean up the header
                header = header.lstrip('#').strip()

                md_parser = MarkdownIt()
                html_content = md_parser.render(section_content)
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text()
                text = re.sub(r'\s+', ' ', text).strip()

                if not text:
                    continue

                # Save normalized text to temp file
                tmp_filepath = os.path.join(tmp_path, f"{os.path.splitext(filename)[0]}_{header}_normalized.txt")
                with open(tmp_filepath, 'w', encoding='utf-8') as f:
                    f.write(text)

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=50,
                    length_function=tiktoken_len,
                )
                chunks = text_splitter.split_text(text)

                for chunk in chunks:
                    metadata = {
                        'source_path': source_path,
                        'file_type': file_type,
                        'section_header': header,
                        'created_at': created_at,
                        'modified_at': modified_at,
                    }
                    documents.append(Document(page_content=chunk, metadata=metadata))

        elif file_type == 'txt':
            with open(source_path, 'r', encoding='utf-8') as f:
                text = f.read()
            # Normalize text
            text = re.sub(r'\s+', ' ', text).strip()
            # Save normalized text to temp file
            tmp_filepath = os.path.join(tmp_path, f"{os.path.splitext(filename)[0]}_normalized.txt")
            with open(tmp_filepath, 'w', encoding='utf-8') as f:
                f.write(text)

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=tiktoken_len,
            )
            chunks = text_splitter.split_text(text)
            for chunk in chunks:
                metadata = {
                    'source_path': source_path,
                    'file_type': file_type,
                    'section_header': '',
                    'created_at': created_at,
                    'modified_at': modified_at,
                }
                documents.append(Document(page_content=chunk, metadata=metadata))
        else:
            continue # Skip unsupported file types

    return documents