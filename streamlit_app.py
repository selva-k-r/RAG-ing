#!/usr/bin/env python3
"""Streamlit app for RAG-ing Modular PoC - Module 4: UI Layer"""

import sys
import os
import logging

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import streamlit as st
from rag_ing.config.settings import Settings
from rag_ing.orchestrator import RAGOrchestrator

# Configure logging to be less verbose for Streamlit
logging.basicConfig(level=logging.WARNING)

@st.cache_resource
def initialize_rag_system():
    """Initialize the RAG system (cached for performance)."""
    try:
        settings = Settings.from_yaml('./config.yaml')
        return RAGOrchestrator('./config.yaml')
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {e}")
        return None

def main():
    """Main Streamlit application."""
    # Set page configuration
    st.set_page_config(
        page_title="🧬 Oncology RAG Assistant",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize RAG system
    rag_system = initialize_rag_system()
    if not rag_system:
        st.stop()
    
    # Main UI
    st.title("🧬 Oncology RAG Assistant")
    st.markdown("*AI-powered biomedical information retrieval and analysis*")
    
    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Audience toggle
        audience = st.selectbox(
            "Target Audience",
            ["clinical", "technical"],
            index=0,
            help="Clinical: Simplified explanations for healthcare providers\nTechnical: Detailed technical information"
        )
        
        # Model selection
        st.subheader("Model Configuration")
        st.text(f"Embedding: PubMedBERT")
        st.text(f"LLM: {rag_system.settings.llm.model}")
        st.text(f"Provider: {rag_system.settings.llm.provider}")
        
        # System status
        st.subheader("System Status")
        try:
            status = rag_system.get_system_status()
            st.success("✅ All modules loaded")
            st.text(f"Vector store: {status['configuration']['vector_store']}")
        except Exception as e:
            st.error(f"❌ System status error: {e}")
    
    # Main query interface
    st.header("💬 Ask a Question")
    
    query = st.text_area(
        "Enter your oncology-related query:",
        placeholder="e.g., What are the key biomarkers for cancer diagnosis?",
        height=100
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🔍 Search", use_container_width=True, type="primary"):
            if query.strip():
                with st.spinner("Processing your query..."):
                    try:
                        # Process query through RAG system
                        result = rag_system.query_documents(
                            query=query.strip(),
                            audience=audience
                        )
                        
                        # Display results
                        st.success("✅ Query processed successfully!")
                        
                        # Response
                        st.header("📝 Response")
                        st.markdown(result["response"])
                        
                        # Metadata
                        with st.expander("📊 Query Details"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Processing Time", f"{result['metadata']['total_processing_time']:.2f}s")
                            with col2:
                                st.metric("Sources Found", len(result["sources"]))
                            with col3:
                                st.metric("Safety Score", f"{result['metadata']['safety_score']:.2f}")
                        
                        # Sources
                        if result["sources"]:
                            st.header("📚 Sources")
                            for i, source in enumerate(result["sources"][:3], 1):
                                with st.expander(f"Source {i}: {source.metadata.get('source', 'Unknown')}"):
                                    st.markdown(source.page_content[:500] + "..." if len(source.page_content) > 500 else source.page_content)
                        
                        # Feedback
                        st.header("💭 Feedback")
                        col1, col2 = st.columns(2)
                        with col1:
                            rating = st.slider("Rate this response", 1, 5, 3)
                        with col2:
                            helpful = st.selectbox("Was this helpful?", ["Yes", "No", "Partially"])
                        
                        feedback_text = st.text_area("Additional comments (optional):")
                        
                        if st.button("Submit Feedback"):
                            try:
                                feedback = {
                                    "rating": rating,
                                    "helpful": helpful,
                                    "comments": feedback_text,
                                    "timestamp": st.session_state.get("query_timestamp")
                                }
                                rag_system.collect_feedback(result["query_hash"], feedback)
                                st.success("Thank you for your feedback!")
                            except Exception as e:
                                st.error(f"Failed to submit feedback: {e}")
                                
                    except Exception as e:
                        st.error(f"Query processing failed: {e}")
                        st.info("💡 Tip: Make sure your query is related to oncology and biomedical topics.")
            else:
                st.warning("Please enter a query to search.")
    
    # Footer
    st.markdown("---")
    st.markdown("*RAG-ing Modular PoC - Oncology-Focused RAG System*")

if __name__ == "__main__":
    main()