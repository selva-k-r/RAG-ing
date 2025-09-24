import streamlit as st
from rag_ing.chunking import chunking_service
from rag_ing.storage.vector_store import vector_store_manager

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
        chunk_size = st.number_input("Chunk Size", min_value=100, max_value=2000, value=1000, key="chunk_size")

    with col2:
        chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=500, value=200, key="chunk_overlap")

    with col3:
        chunk_method = st.selectbox("Chunking Method", chunking_service.get_available_methods(), key="chunk_method")

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
