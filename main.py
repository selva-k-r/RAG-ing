import logging
from src.ingestion import load_documents
from src.vector_store import embed_and_store, load_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Main function to run the data ingestion and embedding pipeline.
    """
    logging.info("Starting the RAG pipeline...")

    # Load configuration
    try:
        config = load_config()
        logging.info("Configuration loaded successfully.")
    except FileNotFoundError:
        logging.error("Configuration file not found. Please ensure 'config.yaml' exists.")
        return
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return

    # Step 1: Load and process documents
    try:
        logging.info(f"Loading documents from '{config.get('data_path', './data')}'...")
        docs = load_documents(config.get('data_path', './data'), config.get('tmp_path', './data_tmp'))
        if not docs:
            logging.warning("No documents were loaded. Please check the data directory and file types.")
            return
        logging.info(f"Successfully loaded and processed {len(docs)} document chunks.")
    except Exception as e:
        logging.error(f"Error during document ingestion: {e}")
        return

    # Step 2: Embed and store documents
    try:
        logging.info(f"Embedding and storing documents using '{config['vector_store']}'...")
        retriever = embed_and_store(docs, config)
        if retriever:
            logging.info("Successfully created and stored embeddings.")
            # Example of a quick test
            test_results = retriever.get_relevant_documents("What is iConnect?")
            logging.info(f"Retriever test returned {len(test_results)} results.")
        else:
            logging.info("Embedding and storage process completed (Snowflake).")

    except Exception as e:
        logging.error(f"Error during embedding and storage: {e}")
        return

    logging.info("RAG pipeline execution finished.")

if __name__ == '__main__':
    main()