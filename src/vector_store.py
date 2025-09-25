import json
import os
from typing import List, Dict, Any

import faiss
import numpy as np
import yaml
from langchain.docstore.document import Document
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.vectorstores.base import VectorStoreRetriever
import snowflake.connector

def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """Loads the YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_snowflake_connection(config: Dict[str, Any]) -> snowflake.connector.SnowflakeConnection:
    """Establishes a connection to Snowflake."""
    snowflake_config = config['snowflake']
    return snowflake.connector.connect(
        user=snowflake_config['user'],
        password=snowflake_config['password'],
        account=snowflake_config['account'],
        warehouse=snowflake_config['warehouse'],
        database=snowflake_config['database'],
        schema=snowflake_config['schema']
    )


def setup_snowflake_tables(conn: snowflake.connector.SnowflakeConnection, config: Dict[str, Any]):
    """Creates the necessary tables in Snowflake if they don't exist."""
    cursor = conn.cursor()
    doc_table = config['snowflake']['documents_table']
    emb_table = config['snowflake']['embeddings_table']

    try:
        # Create documents table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {doc_table} (
            doc_id VARCHAR PRIMARY KEY,
            source_path VARCHAR,
            file_type VARCHAR,
            created_at TIMESTAMP_NTZ,
            modified_at TIMESTAMP_NTZ
        );
        """)

        # Create embeddings table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {emb_table} (
            id VARCHAR PRIMARY KEY,
            doc_id VARCHAR,
            chunk_id INTEGER,
            vector VECTOR(FLOAT, 384),
            metadata VARIANT,
            FOREIGN KEY (doc_id) REFERENCES {doc_table}(doc_id)
        );
        """)
    finally:
        cursor.close()


def embed_and_store(docs: List[Document], config: Dict[str, Any]) -> VectorStoreRetriever:
    """
    Generates embeddings for the given documents and stores them in the specified vector store.
    """
    embedding_model_name = config['embedding_model']
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)

    if config['vector_store'] == 'faiss':
        index_path = config['faiss_index_path']
        metadata_path = config['faiss_metadata_path']
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        vector_store = FAISS.from_documents(docs, embeddings)
        vector_store.save_local(os.path.dirname(index_path), os.path.basename(index_path))
        metadata = [doc.metadata for doc in docs]
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        return vector_store.as_retriever(search_kwargs={"k": config.get("retrieval_k", 5)})

    elif config['vector_store'] == 'snowflake':
        conn = get_snowflake_connection(config)
        setup_snowflake_tables(conn, config)
        cursor = conn.cursor()

        doc_table = config['snowflake']['documents_table']
        emb_table = config['snowflake']['embeddings_table']

        try:
            # Note: This is a simplified example. In a real-world scenario,
            # you would want to handle document updates and de-duplication.
            for i, doc in enumerate(docs):
                doc_id = f"{doc.metadata['source_path']}_{doc.metadata['modified_at']}"

                # Insert into documents table (if not exists)
                cursor.execute(
                    f"INSERT INTO {doc_table} (doc_id, source_path, file_type, created_at, modified_at) "
                    f"SELECT %s, %s, %s, %s, %s "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {doc_table} WHERE doc_id = %s)",
                    (doc_id, doc.metadata['source_path'], doc.metadata['file_type'], doc.metadata['created_at'], doc.metadata['modified_at'], doc_id)
                )

                # Embed and insert into embeddings table
                embedding_vector = embeddings.embed_query(doc.page_content)
                chunk_id = i
                emb_id = f"{doc_id}_{chunk_id}"

                cursor.execute(
                    f"INSERT INTO {emb_table} (id, doc_id, chunk_id, vector, metadata) VALUES (%s, %s, %s, %s, PARSE_JSON(%s))",
                    (emb_id, doc_id, chunk_id, embedding_vector, json.dumps(doc.metadata))
                )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        # Retrieval from Snowflake would require a custom retriever class.
        # For now, returning a placeholder as the focus is on storage.
        # A proper implementation would use LangChain's SnowflakeVectorStore.
        print("Embeddings stored in Snowflake. Retrieval is not implemented in this version.")
        # This is a placeholder. A real retriever would be needed.
        # from langchain.vectorstores import SnowflakeVectorStore
        # return SnowflakeVectorStore(connection=conn, ...).as_retriever()
        return None # Placeholder

    else:
        raise ValueError(f"Unsupported vector store: {config['vector_store']}")