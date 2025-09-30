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
        page_title="iConnect",
        page_icon="🔗",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom CSS styling to match the mockup exactly
    st.markdown("""
    <style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;500;600;700&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css');
    
    /* Global styling - clean white background */
    .stApp {
        background: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 3rem;
        padding-bottom: 2rem;
        max-width: 1000px;
        background: white;
        margin: 0 auto;
        min-height: 100vh;
    }
    
    /* Hide Streamlit branding and menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Custom title styling - exactly like mockup */
    .custom-title {
        font-size: 48px;
        font-weight: 300;
        color: #4a90e2 !important;
        text-align: center;
        margin: 40px 0 10px 0;
        letter-spacing: -1px;
    }
    
    .custom-subtitle {
        font-size: 16px;
        color: #8e8e93 !important;
        text-align: center;
        margin-bottom: 50px;
        font-weight: 400;
    }
    
    /* Large search container - matching mockup */
    .search-container {
        max-width: 700px;
        margin: 0 auto 40px auto;
        position: relative;
    }
    
    /* Search input styling - large rounded like mockup */
    .stTextInput > div > div > input {
        border: 2px solid #e8e8e8 !important;
        border-radius: 50px !important;
        padding: 16px 50px 16px 20px !important;
        font-size: 14px !important;
        font-family: 'Segoe UI', sans-serif !important;
        background: linear-gradient(90deg, #fafafa 0%, #ffffff 50%, #fafafa 100%) !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        outline: none !important;
        transition: all 0.3s ease !important;
        max-width: 650px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1e88e5 !important;
        background: linear-gradient(90deg, #ffffff 0%, #f0f8ff 50%, #ffffff 100%) !important;
        box-shadow: 0 6px 20px rgba(30,136,229,0.2) !important;
    }
    
    /* Hide text input label */
    .stTextInput > label {
        display: none;
    }
    
    /* Search button styling - circular like mockup */
    .search-button-container {
        position: absolute;
        right: 5px;
        top: 50%;
        transform: translateY(-50%);
    }
    
    .search-button {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        background: #4a90e2;
        border: none;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        transition: background 0.3s ease;
    }
    
    .search-button:hover {
        background: #357abd;
    }
    
    /* Category buttons styling - matching home.html exactly */
    .category-buttons {
        display: flex;
        justify-content: center;
        gap: 5px;
        margin: 30px 0 50px 0;
        flex-wrap: wrap;
    }
    
    .category-btn {
        padding: 10px 19px;
        border: 2px solid #e8e8e8;
        border-radius: 20px;
        background: linear-gradient(135deg, #ffffff 0%, #f9f9f9 100%);
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 11px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        position: relative;
        overflow: hidden;
        color: #333;
    }
    
    .category-btn:hover {
        border-color: #1e88e5;
        color: #1e88e5;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30,136,229,0.15);
    }
    
    .category-btn.active {
        background: linear-gradient(135deg, #1e88e5, #26a69a);
        border-color: #1e88e5;
        color: white;
        box-shadow: 0 4px 15px rgba(30,136,229,0.3);
        transform: translateY(-1px);
    }
    
    /* FAQ Section styling */
    .faq-section {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .faq-title {
        font-size: 14px;
        font-weight: 600;
        color: #8e8e93;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 20px;
        text-align: left;
    }
    
    /* Custom expander styling */
    .streamlit-expanderHeader {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        margin-bottom: 10px;
        padding: 15px 20px;
        font-size: 16px;
        font-weight: 500;
        color: #333;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f8f9fa;
    }
    
    .streamlit-expanderContent {
        border: none;
        padding: 0 20px 15px 20px;
    }
    
    /* Results styling */
    .result-container {
        background: white;
        padding: 25px;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        margin: 20px 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* Metrics styling */
    .stMetric {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e8e8e8;
    }
    
    /* Remove sidebar completely */
    .css-1d391kg {
        display: none;
    }
    
    /* Footer styling */
    .custom-footer {
        text-align: center;
        color: #8e8e93;
        font-size: 14px;
        margin-top: 60px;
        padding-top: 30px;
        border-top: 1px solid #e8e8e8;
    }
    
    /* Hide default streamlit components */
    .stTextInput > div > div > input::placeholder {
        color: #8e8e93;
        font-size: 16px;
    }
    
    /* Override any default text colors */
    h1, .custom-title {
        color: #4a90e2 !important;
    }
    
    p, .custom-subtitle {
        color: #8e8e93 !important;
    }
    
    /* Add auto-focus JavaScript */
    </style>
    <script>
    // Auto-focus search input when page loads
    setTimeout(function() {
        const searchInput = document.querySelector('input[placeholder*="Search PopHealth"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }, 100);
    
    // Re-focus on any page update
    const observer = new MutationObserver(function(mutations) {
        setTimeout(function() {
            const searchInput = document.querySelector('input[placeholder*="Search PopHealth"]');
            if (searchInput && document.activeElement !== searchInput) {
                searchInput.focus();
            }
        }, 50);
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Initialize RAG system
    rag_system = initialize_rag_system()
    if not rag_system:
        st.stop()
    
    # Main header - matching mockup exactly
    st.markdown('<h1 class="custom-title">iConnect</h1>', unsafe_allow_html=True)
    st.markdown('<p class="custom-subtitle">IntegraConnect AI-Powered Search</p>', unsafe_allow_html=True)
    
    # Search interface - large rounded search bar like mockup
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    query = st.text_input(
        "search",
        placeholder="Search PopHealth models, documentation, or ask questions...",
        label_visibility="collapsed",
        key="search_input"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Category buttons - matching home.html exactly
    st.markdown("""
    <div class="category-buttons">
        <button class="category-btn active">
            📄 Confluence
        </button>
        <button class="category-btn active">
            🎫 Jira
        </button>
        <button class="category-btn active">
            🏢 Internal Sites
        </button>
        <button class="category-btn active">
            ☁️ Salesforce
        </button>
        <button class="category-btn">
            🌍 External Sites
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    # Add FAQ section - matching mockup
    st.markdown('<div class="faq-section">', unsafe_allow_html=True)
    st.markdown('<div class="faq-title">FREQUENTLY ASKED QUESTIONS</div>', unsafe_allow_html=True)
    
    # FAQ items matching the mockup
    with st.expander("FISH testing shows del(11q), del(17p), del(19p), t(11;14) as positive - which ones can be curated?"):
        st.markdown("Click to see detailed AI response with sources →")
    
    with st.expander("While running Pipeline, I am getting xyz issue?"):
        st.markdown("Click to see detailed AI response with sources →")
    
    with st.expander("Patient has lymphadenopathy - how do I curate the scan results?"):
        st.markdown("Click to see detailed AI response with sources →")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process search query when Enter is pressed or form is submitted
    if query and query.strip():
        with st.spinner("Processing your query..."):
            try:
                # Process query through RAG system (using technical audience by default)
                result = rag_system.query_documents(
                    query=query.strip(),
                    audience="technical"  # Default to technical audience
                )
                
                # Display results
                st.markdown('<div class="result-container">', unsafe_allow_html=True)
                st.success("✅ Query processed successfully!")
                
                # Response
                st.subheader("📝 Response")
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
                    st.subheader("📚 Sources")
                    for i, source in enumerate(result["sources"][:3], 1):
                        with st.expander(f"Source {i}: {source.metadata.get('source', 'Unknown')}"):
                            st.markdown(source.page_content[:500] + "..." if len(source.page_content) > 500 else source.page_content)
                
                # Feedback
                st.subheader("💭 Feedback")
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
                
                st.markdown('</div>', unsafe_allow_html=True)
                        
            except Exception as e:
                st.error(f"Query processing failed: {e}")
                st.info("💡 Tip: Make sure your query is clear and specific.")
    
    elif query and not query.strip():
        st.warning("Please enter a query to search.")
    
    # Footer
    st.markdown('<div class="custom-footer">iConnect - Intelligent Document Analysis</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()