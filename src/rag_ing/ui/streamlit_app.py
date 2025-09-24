import streamlit as st
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import RAG-ing components
try:
    from ..config.settings import Settings
    from .components.sidebar import sidebar_configuration
    from .pages.document_sources import document_sources_tab
    from .pages.processing import processing_tab
    from .pages.query import query_tab
except ImportError:
    # For running as a standalone script
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from rag_ing.config.settings import Settings
    from rag_ing.ui.components.sidebar import sidebar_configuration
    from rag_ing.ui.pages.document_sources import document_sources_tab
    from rag_ing.ui.pages.processing import processing_tab
    from rag_ing.ui.pages.query import query_tab

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