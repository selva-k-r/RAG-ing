"""Vector store manager for Snowflake and other vector databases."""

from typing import List, Dict, Any, Optional, Tuple
from langchain.vectorstores.base import VectorStore
from langchain_community.vectorstores import FAISS, Chroma
from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings
import snowflake.connector
import pandas as pd
import json
import numpy as np
import logging

from ..config.settings import SnowflakeConfig

logger = logging.getLogger(__name__)


class SnowflakeVectorStore:
    """Custom vector store implementation for Snowflake."""
    
    def __init__(self, config: SnowflakeConfig, embeddings: Embeddings, table_name: str = "documents_vectors"):
        self.config = config
        self.embeddings = embeddings
        self.table_name = table_name
        self.connection = None
        self._connect()
        self._create_table_if_not_exists()
    
    def _connect(self):
        """Connect to Snowflake."""
        try:
            self.connection = snowflake.connector.connect(
                account=self.config.account,
                user=self.config.user,
                password=self.config.password,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
                role=self.config.role
            )
            logger.info("Connected to Snowflake successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def _create_table_if_not_exists(self):
        """Create the vector table if it doesn't exist."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id VARCHAR(255) PRIMARY KEY,
            content TEXT,
            metadata VARIANT,
            vector ARRAY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(create_table_sql)
            logger.info(f"Table {self.table_name} created or already exists")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
        finally:
            cursor.close()
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store."""
        if not documents:
            return []
        
        # Generate embeddings for all documents
        texts = [doc.page_content for doc in documents]
        embeddings = self.embeddings.embed_documents(texts)
        
        # Prepare data for insertion
        insert_data = []
        doc_ids = []
        
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            doc_id = f"doc_{i}_{hash(doc.page_content) % 1000000}"
            doc_ids.append(doc_id)
            
            insert_data.append({
                'id': doc_id,
                'content': doc.page_content,
                'metadata': json.dumps(doc.metadata),
                'vector': embedding
            })
        
        # Insert into Snowflake
        insert_sql = f"""
        INSERT INTO {self.table_name} (id, content, metadata, vector)
        VALUES (%(id)s, %(content)s, %(metadata)s, %(vector)s)
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.executemany(insert_sql, insert_data)
            self.connection.commit()
            logger.info(f"Added {len(documents)} documents to Snowflake")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
        
        return doc_ids
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Perform similarity search."""
        # Generate embedding for the query
        query_embedding = self.embeddings.embed_query(query)
        
        # For simplicity, we'll use a basic cosine similarity approach
        # In production, you might want to use Snowflake's vector functions
        search_sql = f"""
        SELECT id, content, metadata, vector
        FROM {self.table_name}
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(search_sql)
            results = cursor.fetchall()
            
            # Calculate similarities
            similarities = []
            for row in results:
                doc_id, content, metadata_str, vector = row
                
                if vector:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, vector)
                    similarities.append((similarity, doc_id, content, metadata_str))
            
            # Sort by similarity and return top k
            similarities.sort(reverse=True, key=lambda x: x[0])
            top_results = similarities[:k]
            
            # Convert to Document objects
            documents = []
            for similarity, doc_id, content, metadata_str in top_results:
                metadata = json.loads(metadata_str) if metadata_str else {}
                metadata['similarity'] = similarity
                documents.append(Document(page_content=content, metadata=metadata))
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            raise
        finally:
            cursor.close()
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        if not ids:
            return True
        
        placeholders = ','.join(['%s'] * len(ids))
        delete_sql = f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(delete_sql, ids)
            self.connection.commit()
            logger.info(f"Deleted {len(ids)} documents from Snowflake")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()
    
    def close(self):
        """Close the connection."""
        if self.connection:
            self.connection.close()


class VectorStoreManager:
    """Manages different vector store implementations."""
    
    def __init__(self):
        self._stores: Dict[str, Any] = {}
        self._current_store: Optional[Any] = None
        self._current_store_type: Optional[str] = None
    
    def create_snowflake_store(self, config: SnowflakeConfig, embeddings: Embeddings, 
                             table_name: str = "documents_vectors") -> SnowflakeVectorStore:
        """Create a Snowflake vector store."""
        store_key = f"snowflake_{table_name}"
        
        if store_key not in self._stores:
            store = SnowflakeVectorStore(config, embeddings, table_name)
            self._stores[store_key] = store
        
        self._current_store = self._stores[store_key]
        self._current_store_type = "snowflake"
        return self._current_store
    
    def create_faiss_store(self, embeddings: Embeddings, documents: Optional[List[Document]] = None) -> FAISS:
        """Create a FAISS vector store."""
        store_key = "faiss_default"
        
        if store_key not in self._stores:
            if documents:
                texts = [doc.page_content for doc in documents]
                metadatas = [doc.metadata for doc in documents]
                store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            else:
                # Create empty store
                store = FAISS.from_texts(["dummy"], embeddings)
                store.delete([0])  # Remove dummy document
            
            self._stores[store_key] = store
        
        self._current_store = self._stores[store_key]
        self._current_store_type = "faiss"
        return self._current_store
    
    def create_chroma_store(self, embeddings: Embeddings, persist_directory: Optional[str] = None) -> Chroma:
        """Create a Chroma vector store."""
        store_key = f"chroma_{persist_directory or 'default'}"
        
        if store_key not in self._stores:
            store = Chroma(embedding_function=embeddings, persist_directory=persist_directory)
            self._stores[store_key] = store
        
        self._current_store = self._stores[store_key]
        self._current_store_type = "chroma"
        return self._current_store
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the current vector store."""
        if not self._current_store:
            raise ValueError("No vector store selected. Create one first.")
        
        if self._current_store_type == "snowflake":
            return self._current_store.add_documents(documents)
        elif hasattr(self._current_store, 'add_documents'):
            return self._current_store.add_documents(documents)
        else:
            # For stores that don't return IDs
            self._current_store.add_documents(documents)
            return [f"doc_{i}" for i in range(len(documents))]
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Perform similarity search on the current vector store."""
        if not self._current_store:
            raise ValueError("No vector store selected. Create one first.")
        
        return self._current_store.similarity_search(query, k=k)
    
    def get_current_store_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current vector store."""
        if not self._current_store:
            return None
        
        return {
            "type": self._current_store_type,
            "class": self._current_store.__class__.__name__,
        }
    
    def list_available_stores(self) -> List[str]:
        """List available vector store types."""
        return ["snowflake", "faiss", "chroma"]


# Global vector store manager instance
vector_store_manager = VectorStoreManager()