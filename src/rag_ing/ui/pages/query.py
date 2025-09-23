import streamlit as st
from rag_ing.storage.vector_store import vector_store_manager
from rag_ing.models.llm_manager import llm_manager

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

    query = st.text_input("Enter your question:", placeholder="What would you like to know?", key="query_input")

    col1, col2 = st.columns(2)
    with col1:
        num_results = st.slider("Number of results to retrieve", min_value=1, max_value=10, value=4, key="num_results")

    with col2:
        include_sources = st.checkbox("Include sources in response", value=True, key="include_sources")

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
