"""Streamlit UI for RAG-ing application."""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import RAG-ing components
try:
    from ..config.settings import Settings, EmbeddingModelConfig, LLMConfig, SnowflakeConfig
    from ..models.embedding_manager import embedding_manager
    from ..models.llm_manager import llm_manager
    from ..storage.vector_store import vector_store_manager
    from ..chunking import chunking_service
    from ..connectors import ConfluenceConnector, MediumConnector, social_connector_manager
except ImportError:
    # For running as standalone script
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from rag_ing.config.settings import Settings, EmbeddingModelConfig, LLMConfig, SnowflakeConfig
    from rag_ing.models.embedding_manager import embedding_manager
    from rag_ing.models.llm_manager import llm_manager
    from rag_ing.storage.vector_store import vector_store_manager
    from rag_ing.chunking import chunking_service
    from rag_ing.connectors import ConfluenceConnector, MediumConnector, social_connector_manager


def init_session_state():
    """Initialize session state variables."""
    if 'settings' not in st.session_state:
        st.session_state.settings = Settings()
    
    if 'documents' not in st.session_state:
        st.session_state.documents = []
    
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = None
    
    if 'embedding_model_loaded' not in st.session_state:
        st.session_state.embedding_model_loaded = False
    
    if 'llm_loaded' not in st.session_state:
        st.session_state.llm_loaded = False


def sidebar_configuration():
    """Sidebar for configuration settings."""
    st.sidebar.title("⚙️ Configuration")
    
    # Embedding Model Configuration
    st.sidebar.subheader("🔤 Embedding Model")
    
    embedding_provider = st.sidebar.selectbox(
        "Provider",
        embedding_manager.list_available_providers(),
        index=0
    )
    
    recommended_models = embedding_manager.get_recommended_models(embedding_provider)
    embedding_model = st.sidebar.selectbox(
        "Model",
        recommended_models,
        index=0 if recommended_models else None
    )
    
    embedding_api_key = st.sidebar.text_input(
        "API Key",
        type="password",
        help="Enter API key for the embedding provider"
    )
    
    # LLM Configuration
    st.sidebar.subheader("🤖 Language Model")
    
    llm_provider = st.sidebar.selectbox(
        "Provider",
        llm_manager.list_available_providers(),
        index=0
    )
    
    recommended_llm_models = llm_manager.get_recommended_models(llm_provider)
    llm_model = st.sidebar.selectbox(
        "Model",
        recommended_llm_models,
        index=0 if recommended_llm_models else None
    )
    
    llm_api_key = st.sidebar.text_input(
        "LLM API Key",
        type="password",
        help="Enter API key for the LLM provider"
    )
    
    llm_temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.1
    )
    
    # Vector Store Configuration
    st.sidebar.subheader("🗄️ Vector Store")
    
    vector_store_type = st.sidebar.selectbox(
        "Type",
        vector_store_manager.list_available_stores(),
        index=0
    )
    
    # Snowflake configuration (if selected)
    snowflake_config = None
    if vector_store_type == "snowflake":
        st.sidebar.write("**Snowflake Configuration**")
        sf_account = st.sidebar.text_input("Account")
        sf_user = st.sidebar.text_input("User")
        sf_password = st.sidebar.text_input("Password", type="password")
        sf_warehouse = st.sidebar.text_input("Warehouse")
        sf_database = st.sidebar.text_input("Database")
        sf_schema = st.sidebar.text_input("Schema")
        
        if all([sf_account, sf_user, sf_password, sf_warehouse, sf_database, sf_schema]):
            snowflake_config = SnowflakeConfig(
                account=sf_account,
                user=sf_user,
                password=sf_password,
                warehouse=sf_warehouse,
                database=sf_database,
                schema=sf_schema
            )
    
    # Load Models Button
    if st.sidebar.button("🔄 Load Models"):
        with st.spinner("Loading models..."):
            try:
                # Load embedding model
                embedding_config = EmbeddingModelConfig(
                    provider=embedding_provider,
                    model_name=embedding_model,
                    api_key=embedding_api_key
                )
                embedding_manager.load_model(embedding_config)
                st.session_state.embedding_model_loaded = True
                
                # Load LLM
                llm_config = LLMConfig(
                    provider=llm_provider,
                    model_name=llm_model,
                    api_key=llm_api_key,
                    temperature=llm_temperature
                )
                llm_manager.load_model(llm_config)
                st.session_state.llm_loaded = True
                
                # Create vector store
                if vector_store_type == "snowflake" and snowflake_config:
                    st.session_state.vector_store = vector_store_manager.create_snowflake_store(
                        snowflake_config, embedding_manager._current_model
                    )
                elif vector_store_type == "faiss":
                    st.session_state.vector_store = vector_store_manager.create_faiss_store(
                        embedding_manager._current_model
                    )
                elif vector_store_type == "chroma":
                    st.session_state.vector_store = vector_store_manager.create_chroma_store(
                        embedding_manager._current_model
                    )
                
                st.sidebar.success("✅ Models loaded successfully!")
                
            except Exception as e:
                st.sidebar.error(f"❌ Error loading models: {e}")


def document_sources_tab():
    """Tab for configuring and connecting document sources."""
    st.header("📄 Document Sources")
    
    source_type = st.selectbox(
        "Select Source Type",
        ["Confluence", "Medium", "Twitter", "Reddit"]
    )
    
    if source_type == "Confluence":
        confluence_ui()
    elif source_type == "Medium":
        medium_ui()
    elif source_type == "Twitter":
        twitter_ui()
    elif source_type == "Reddit":
        reddit_ui()


def confluence_ui():
    """UI for Confluence connector."""
    st.subheader("🏢 Confluence")
    
    col1, col2 = st.columns(2)
    
    with col1:
        base_url = st.text_input("Base URL", placeholder="https://your-domain.atlassian.net")
        username = st.text_input("Username")
        
    with col2:
        api_token = st.text_input("API Token", type="password")
        space_key = st.text_input("Space Key (optional)")
    
    if st.button("🔗 Connect to Confluence"):
        if base_url and username and api_token:
            try:
                config = {
                    "base_url": base_url,
                    "username": username,
                    "api_token": api_token,
                    "space_key": space_key if space_key else None
                }
                
                connector = ConfluenceConnector(config)
                
                with st.spinner("Connecting to Confluence..."):
                    if connector.connect():
                        st.success("✅ Connected to Confluence!")
                        
                        # Fetch documents
                        fetch_limit = st.number_input("Number of documents to fetch", min_value=1, max_value=100, value=10)
                        
                        if st.button("📥 Fetch Documents"):
                            with st.spinner("Fetching documents..."):
                                documents = connector.fetch_documents(limit=fetch_limit)
                                
                                if documents:
                                    st.session_state.documents.extend(documents)
                                    st.success(f"✅ Fetched {len(documents)} documents from Confluence!")
                                    
                                    # Show preview
                                    st.subheader("📋 Document Preview")
                                    for i, doc in enumerate(documents[:3]):  # Show first 3
                                        with st.expander(f"Document {i+1}: {doc.metadata.get('title', 'Untitled')}"):
                                            st.write(f"**Content:** {doc.page_content[:500]}...")
                                            st.write(f"**Metadata:** {doc.metadata}")
                                else:
                                    st.warning("⚠️ No documents found")
                    else:
                        st.error("❌ Failed to connect to Confluence")
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please fill in all required fields")


def medium_ui():
    """UI for Medium connector."""
    st.subheader("📝 Medium")
    
    col1, col2 = st.columns(2)
    
    with col1:
        user_id = st.text_input("User ID (@username)")
        
    with col2:
        rss_url = st.text_input("RSS URL (optional)")
    
    if st.button("🔗 Connect to Medium"):
        if user_id or rss_url:
            try:
                config = {
                    "user_id": user_id if user_id else None,
                    "rss_url": rss_url if rss_url else None
                }
                
                connector = MediumConnector(config)
                
                with st.spinner("Connecting to Medium..."):
                    if connector.connect():
                        st.success("✅ Connected to Medium!")
                        
                        # Fetch documents
                        fetch_limit = st.number_input("Number of articles to fetch", min_value=1, max_value=50, value=5)
                        
                        if st.button("📥 Fetch Articles"):
                            with st.spinner("Fetching articles..."):
                                documents = connector.fetch_documents(limit=fetch_limit)
                                
                                if documents:
                                    st.session_state.documents.extend(documents)
                                    st.success(f"✅ Fetched {len(documents)} articles from Medium!")
                                    
                                    # Show preview
                                    st.subheader("📋 Article Preview")
                                    for i, doc in enumerate(documents[:3]):
                                        with st.expander(f"Article {i+1}: {doc.metadata.get('title', 'Untitled')}"):
                                            st.write(f"**Content:** {doc.page_content[:500]}...")
                                            st.write(f"**Metadata:** {doc.metadata}")
                                else:
                                    st.warning("⚠️ No articles found")
                    else:
                        st.error("❌ Failed to connect to Medium")
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please provide either User ID or RSS URL")


def twitter_ui():
    """UI for Twitter connector."""
    st.subheader("🐦 Twitter/X")
    
    col1, col2 = st.columns(2)
    
    with col1:
        bearer_token = st.text_input("Bearer Token", type="password")
        
    with col2:
        username = st.text_input("Username to fetch from")
    
    if st.button("🔗 Connect to Twitter"):
        if bearer_token and username:
            try:
                config = {
                    "bearer_token": bearer_token,
                    "username": username
                }
                
                connector = social_connector_manager.create_connector("twitter", config)
                
                with st.spinner("Connecting to Twitter..."):
                    if connector.connect():
                        st.success("✅ Connected to Twitter!")
                        
                        # Fetch documents
                        fetch_limit = st.number_input("Number of tweets to fetch", min_value=1, max_value=100, value=10)
                        include_replies = st.checkbox("Include replies")
                        
                        if st.button("📥 Fetch Tweets"):
                            with st.spinner("Fetching tweets..."):
                                documents = connector.fetch_documents(limit=fetch_limit, include_replies=include_replies)
                                
                                if documents:
                                    st.session_state.documents.extend(documents)
                                    st.success(f"✅ Fetched {len(documents)} tweets!")
                                    
                                    # Show preview
                                    st.subheader("📋 Tweet Preview")
                                    for i, doc in enumerate(documents[:3]):
                                        with st.expander(f"Tweet {i+1}"):
                                            st.write(f"**Content:** {doc.page_content}")
                                            st.write(f"**Author:** {doc.metadata.get('author_name', 'Unknown')}")
                                            st.write(f"**Created:** {doc.metadata.get('created_at', 'Unknown')}")
                                else:
                                    st.warning("⚠️ No tweets found")
                    else:
                        st.error("❌ Failed to connect to Twitter")
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please fill in all required fields")


def reddit_ui():
    """UI for Reddit connector."""
    st.subheader("🔴 Reddit")
    
    col1, col2 = st.columns(2)
    
    with col1:
        client_id = st.text_input("Client ID")
        client_secret = st.text_input("Client Secret", type="password")
        
    with col2:
        subreddit = st.text_input("Subreddit")
        sort_method = st.selectbox("Sort by", ["hot", "new", "top", "rising"])
    
    if st.button("🔗 Connect to Reddit"):
        if client_id and client_secret and subreddit:
            try:
                config = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "subreddit": subreddit
                }
                
                connector = social_connector_manager.create_connector("reddit", config)
                
                with st.spinner("Connecting to Reddit..."):
                    if connector.connect():
                        st.success("✅ Connected to Reddit!")
                        
                        # Fetch documents
                        fetch_limit = st.number_input("Number of posts to fetch", min_value=1, max_value=100, value=10)
                        
                        if st.button("📥 Fetch Posts"):
                            with st.spinner("Fetching posts..."):
                                documents = connector.fetch_documents(limit=fetch_limit, sort=sort_method)
                                
                                if documents:
                                    st.session_state.documents.extend(documents)
                                    st.success(f"✅ Fetched {len(documents)} posts from r/{subreddit}!")
                                    
                                    # Show preview
                                    st.subheader("📋 Post Preview")
                                    for i, doc in enumerate(documents[:3]):
                                        with st.expander(f"Post {i+1}: {doc.metadata.get('title', 'Untitled')[:50]}..."):
                                            st.write(f"**Content:** {doc.page_content[:500]}...")
                                            st.write(f"**Author:** {doc.metadata.get('author', 'Unknown')}")
                                            st.write(f"**Score:** {doc.metadata.get('score', 0)}")
                                else:
                                    st.warning("⚠️ No posts found")
                    else:
                        st.error("❌ Failed to connect to Reddit")
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please fill in all required fields")


def processing_tab():
    """Tab for document processing and vector storage."""
    st.header("⚙️ Document Processing")
    
    if not st.session_state.documents:
        st.warning("⚠️ No documents loaded. Please fetch documents from the Document Sources tab first.")
        return
    
    if not st.session_state.embedding_model_loaded:
        st.warning("⚠️ No embedding model loaded. Please configure and load models in the sidebar first.")
        return
    
    st.write(f"📊 **Total Documents:** {len(st.session_state.documents)}")
    
    # Chunking Configuration
    st.subheader("✂️ Text Chunking")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        chunk_size = st.number_input("Chunk Size", min_value=100, max_value=2000, value=1000)
    
    with col2:
        chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=500, value=200)
    
    with col3:
        chunk_method = st.selectbox("Chunking Method", chunking_service.get_available_methods())
    
    # Update chunking configuration
    from rag_ing.config.settings import ChunkingConfig
    chunking_config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunking_service.update_config(chunking_config)
    
    if st.button("✂️ Chunk Documents"):
        with st.spinner("Chunking documents..."):
            try:
                chunked_docs = chunking_service.chunk_documents(st.session_state.documents, chunk_method)
                
                if chunked_docs:
                    st.success(f"✅ Created {len(chunked_docs)} chunks from {len(st.session_state.documents)} documents")
                    
                    # Show statistics
                    stats = chunking_service.get_chunk_statistics(chunked_docs)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Chunks", stats['total_chunks'])
                    with col2:
                        st.metric("Avg Chunk Size", f"{stats['average_chunk_size']:.0f}")
                    with col3:
                        st.metric("Min Size", stats['min_chunk_size'])
                    with col4:
                        st.metric("Max Size", stats['max_chunk_size'])
                    
                    # Store in vector database
                    if st.session_state.vector_store:
                        if st.button("🗄️ Store in Vector Database"):
                            with st.spinner("Storing vectors..."):
                                try:
                                    vector_store_manager.add_documents(chunked_docs)
                                    st.success("✅ Documents stored in vector database!")
                                except Exception as e:
                                    st.error(f"❌ Error storing vectors: {e}")
                    else:
                        st.warning("⚠️ No vector store configured. Please configure in the sidebar.")
                
            except Exception as e:
                st.error(f"❌ Error chunking documents: {e}")


def query_tab():
    """Tab for querying the RAG system."""
    st.header("🔍 Query & Chat")
    
    if not st.session_state.vector_store:
        st.warning("⚠️ No vector store available. Please process documents first.")
        return
    
    if not st.session_state.llm_loaded:
        st.warning("⚠️ No LLM loaded. Please configure and load models in the sidebar first.")
        return
    
    # Query interface
    st.subheader("💬 Ask Questions")
    
    query = st.text_input("Enter your question:", placeholder="What would you like to know?")
    
    col1, col2 = st.columns(2)
    with col1:
        num_results = st.slider("Number of results to retrieve", min_value=1, max_value=10, value=4)
    
    with col2:
        include_sources = st.checkbox("Include sources in response", value=True)
    
    if st.button("🔍 Search") and query:
        with st.spinner("Searching..."):
            try:
                # Perform similarity search
                results = vector_store_manager.similarity_search(query, k=num_results)
                
                if results:
                    st.subheader("📄 Retrieved Documents")
                    
                    # Display results
                    context_text = ""
                    for i, doc in enumerate(results):
                        with st.expander(f"Result {i+1} - {doc.metadata.get('title', 'Document')}"):
                            st.write(f"**Content:** {doc.page_content}")
                            st.write(f"**Source:** {doc.metadata.get('source', 'Unknown')}")
                            if 'similarity' in doc.metadata:
                                st.write(f"**Similarity:** {doc.metadata['similarity']:.3f}")
                        
                        context_text += f"\n\nDocument {i+1}:\n{doc.page_content}"
                    
                    # Generate response using LLM
                    st.subheader("🤖 AI Response")
                    
                    prompt = f"""Based on the following context documents, please answer the question: "{query}"

Context:
{context_text}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information to fully answer the question, please mention that."""
                    
                    with st.spinner("Generating response..."):
                        try:
                            response = llm_manager.generate(prompt)
                            st.write(response)
                            
                            if include_sources:
                                st.subheader("📚 Sources")
                                for i, doc in enumerate(results):
                                    source_info = f"**Source {i+1}:** {doc.metadata.get('source', 'Unknown')}"
                                    if doc.metadata.get('title'):
                                        source_info += f" - {doc.metadata['title']}"
                                    if doc.metadata.get('url'):
                                        source_info += f" ([Link]({doc.metadata['url']}))"
                                    st.write(source_info)
                        
                        except Exception as e:
                            st.error(f"❌ Error generating response: {e}")
                
                else:
                    st.warning("⚠️ No relevant documents found for your query.")
            
            except Exception as e:
                st.error(f"❌ Error performing search: {e}")


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="RAG-ing",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔍 RAG-ing")
    st.markdown("*A comprehensive RAG application with multiple connectors and dynamic model selection*")
    
    # Initialize session state
    init_session_state()
    
    # Sidebar configuration
    sidebar_configuration()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📄 Document Sources", "⚙️ Processing", "🔍 Query & Chat"])
    
    with tab1:
        document_sources_tab()
    
    with tab2:
        processing_tab()
    
    with tab3:
        query_tab()
    
    # Footer
    st.markdown("---")
    st.markdown("Built with ❤️ using LangChain and Streamlit")


if __name__ == "__main__":
    main()