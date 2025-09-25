"""Module 4: UI Layer

Objective: Provide user interface for query input and response display.
"""

import logging
import streamlit as st
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from ..config.settings import Settings
from ..utils.exceptions import UIError

logger = logging.getLogger(__name__)


class UILayerModule:
    """Module for YAML-driven user interface with audience toggle and feedback capture."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.ui_config = config.ui
        self._initialize_session_state()
    
    def _initialize_session_state(self) -> None:
        """Initialize Streamlit session state variables."""
        if 'audience' not in st.session_state:
            st.session_state.audience = 'clinical'
        
        if 'feedback_history' not in st.session_state:
            st.session_state.feedback_history = []
        
        if 'query_history' not in st.session_state:
            st.session_state.query_history = []
        
        if 'current_model' not in st.session_state:
            st.session_state.current_model = self.ui_config.default_model
        
        if 'current_source' not in st.session_state:
            st.session_state.current_source = self.ui_config.default_source
    
    def render_main_interface(self) -> Dict[str, Any]:
        """Render the main query interface."""
        st.title("🧬 Oncology RAG Assistant")
        st.markdown("*AI-powered biomedical information retrieval and analysis*")
        
        # Render sidebar controls
        self._render_sidebar()
        
        # Main query interface
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_area(
                "Enter your oncology-related question:",
                placeholder="e.g., What are the key biomarkers for breast cancer diagnosis?",
                height=100,
                key="query_input"
            )
        
        with col2:
            st.markdown("### Quick Actions")
            
            if st.button("🔍 Submit Query", type="primary"):
                if query.strip():
                    return self._process_query_submission(query)
                else:
                    st.error("Please enter a query")
            
            if st.button("🧹 Clear History"):
                self._clear_history()
                st.success("History cleared")
        
        # Display recent queries
        self._render_query_history()
        
        return {}
    
    def render_response_interface(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render response with markdown formatting and source attribution."""
        if not response_data:
            return {}
        
        st.markdown("---")
        st.subheader("📋 Response")
        
        # Main response
        response_text = response_data.get("response", "")\n        st.markdown(response_text)
        
        # Source attribution
        if "retrieval_summary" in response_data:
            self._render_source_attribution(response_data["retrieval_summary"])
        
        # Chunk metadata (if enabled)
        if (self.ui_config.show_chunk_metadata and 
            "context_chunks" in response_data):
            self._render_chunk_metadata(response_data["context_chunks"])
        
        # Feedback collection (if enabled)
        feedback = {}
        if self.ui_config.feedback_enabled:
            feedback = self._render_feedback_panel(
                response_data.get("query", ""),
                response_text
            )
        
        # Response metadata
        self._render_response_metadata(response_data.get("metadata", {}))
        
        return {"feedback": feedback}
    
    def _render_sidebar(self) -> None:
        """Render sidebar with audience toggle and configuration."""
        st.sidebar.title("⚙️ Configuration")
        
        # Audience toggle (if enabled)
        if self.ui_config.audience_toggle:
            st.sidebar.subheader("🎯 Audience Mode")
            
            audience_options = ["Clinical", "Technical"]
            current_audience = st.session_state.audience.title()
            
            selected_audience = st.sidebar.radio(
                "Select your role:",
                audience_options,
                index=audience_options.index(current_audience) if current_audience in audience_options else 0,
                help="This affects response style and terminology"
            )
            
            st.session_state.audience = selected_audience.lower()
            
            # Show audience-specific guidance
            if selected_audience == "Clinical":
                st.sidebar.info("🏥 **Clinical Mode**\\nMedical terminology, patient-focused guidance, clinical protocols")
            else:
                st.sidebar.info("⚙️ **Technical Mode**\\nImplementation details, system configuration, methodological information")
        
        # Model selection
        st.sidebar.subheader("🤖 Model Settings")
        
        current_model = st.sidebar.selectbox(
            "Language Model:",
            ["biomistral", "gpt-4", "claude-3-sonnet"],
            index=0,
            key="model_selector"
        )
        st.session_state.current_model = current_model
        
        # Source selection
        st.sidebar.subheader("📚 Data Sources")
        
        current_source = st.sidebar.selectbox(
            "Primary Source:",
            ["confluence", "local_files", "mixed"],
            index=0,
            key="source_selector"
        )
        st.session_state.current_source = current_source
        
        # Advanced settings expander
        with st.sidebar.expander("🔧 Advanced Settings"):
            st.slider("Top-K Results", min_value=1, max_value=10, value=5, key="top_k")
            st.checkbox("Ontology Filtering", value=True, key="ontology_filter")
            st.selectbox("Date Range", ["last_12_months", "last_6_months", "last_month", "all"], key="date_range")
    
    def _process_query_submission(self, query: str) -> Dict[str, Any]:
        """Process and validate query submission."""
        # Validate query
        if len(query.strip()) < 3:
            st.error("Query too short. Please provide at least 3 characters.")
            return {}
        
        if len(query) > 1000:
            st.warning("Query truncated to 1000 characters.")
            query = query[:1000]
        
        # Add to query history
        query_entry = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "audience": st.session_state.audience,
            "model": st.session_state.current_model,
            "source": st.session_state.current_source
        }
        
        st.session_state.query_history.append(query_entry)
        
        # Keep only last 10 queries
        if len(st.session_state.query_history) > 10:
            st.session_state.query_history = st.session_state.query_history[-10:]
        
        # Return query configuration for processing
        return {
            "query": query,
            "audience": st.session_state.audience,
            "model": st.session_state.current_model,
            "source": st.session_state.current_source,
            "filters": {
                "top_k": st.session_state.get("top_k", 5),
                "ontology_match": st.session_state.get("ontology_filter", True),
                "date_range": st.session_state.get("date_range", "last_12_months")
            }
        }
    
    def _render_source_attribution(self, retrieval_summary: Dict[str, Any]) -> None:
        """Render source attribution information."""
        st.subheader("📖 Sources")
        
        num_results = retrieval_summary.get("num_results", 0)
        sources = retrieval_summary.get("sources", [])
        has_ontology = retrieval_summary.get("has_ontology_codes", False)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Results Found", num_results)
        
        with col2:
            st.metric("Unique Sources", len(sources))
        
        with col3:
            ontology_status = "✅ Present" if has_ontology else "❌ None"
            st.metric("Ontology Codes", ontology_status)
        
        # List sources
        if sources:
            st.write("**Source Documents:**")
            for i, source in enumerate(sources, 1):
                st.write(f"{i}. {source}")
    
    def _render_chunk_metadata(self, context_chunks: List[Dict[str, Any]]) -> None:
        """Render chunk metadata in expandable section."""
        with st.expander(f"📝 View Retrieved Context ({len(context_chunks)} chunks)"):
            for chunk in context_chunks:
                st.markdown(f"**Chunk {chunk['relevance_rank']}** - {chunk['source']}")
                
                if "ontology_codes" in chunk and chunk["ontology_codes"]:
                    st.write(f"🏷️ Ontology: {', '.join(chunk['ontology_codes'])}")
                
                if "date" in chunk:
                    st.write(f"📅 Date: {chunk['date']}")
                
                st.text_area(
                    "Content:",
                    chunk['content'][:300] + "..." if len(chunk['content']) > 300 else chunk['content'],
                    height=100,
                    key=f"chunk_{chunk['id']}"
                )
                st.markdown("---")
    
    def _render_feedback_panel(self, query: str, response: str) -> Dict[str, Any]:
        """Render feedback collection panel."""
        st.subheader("📝 Feedback")
        st.write("Help us improve by rating this response:")
        
        # Generate unique key for this query
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        col1, col2 = st.columns(2)
        
        with col1:
            clarity = st.slider(
                "Response Clarity",
                min_value=1, max_value=5, value=3,
                help="How clear and understandable is the response?",
                key=f"clarity_{query_hash}"
            )
            
            citation = st.slider(
                "Citation Quality",
                min_value=1, max_value=5, value=3,
                help="How well does the response cite relevant sources?",
                key=f"citation_{query_hash}"
            )
        
        with col2:
            safety = st.slider(
                "Safety & Accuracy",
                min_value=1, max_value=5, value=3,
                help="How safe and accurate is the medical information?",
                key=f"safety_{query_hash}"
            )
            
            usefulness = st.slider(
                "Overall Usefulness",
                min_value=1, max_value=5, value=3,
                help="How useful is this response for your work?",
                key=f"usefulness_{query_hash}"
            )
        
        # Additional feedback
        comments = st.text_area(
            "Additional Comments (optional):",
            placeholder="Any specific feedback or suggestions?",
            key=f"comments_{query_hash}"
        )
        
        # Submit feedback
        if st.button("Submit Feedback", key=f"submit_{query_hash}"):
            feedback = {
                "query_hash": query_hash,
                "timestamp": datetime.now().isoformat(),
                "audience": st.session_state.audience,
                "ratings": {
                    "clarity": clarity,
                    "citation": citation,
                    "safety": safety,
                    "usefulness": usefulness
                },
                "comments": comments,
                "query_length": len(query),
                "response_length": len(response)
            }
            
            # Store feedback in session state
            st.session_state.feedback_history.append(feedback)
            
            st.success("Thank you for your feedback! 🙏")
            
            return feedback
        
        return {}
    
    def _render_response_metadata(self, metadata: Dict[str, Any]) -> None:
        """Render response metadata in expandable section."""
        with st.expander("ℹ️ Response Metadata"):
            col1, col2 = st.columns(2)
            
            with col1:
                if "response_time" in metadata:
                    st.metric("Response Time", f"{metadata['response_time']:.2f}s")
                
                if "model_config" in metadata:
                    model_info = metadata["model_config"]
                    st.write(f"**Model:** {model_info.get('model', 'Unknown')}")
                    st.write(f"**Provider:** {model_info.get('provider', 'Unknown')}")
            
            with col2:
                if "prompt_length" in metadata:
                    st.metric("Prompt Length", f"{metadata['prompt_length']} chars")
                
                if "response_length" in metadata:
                    st.metric("Response Length", f"{metadata['response_length']} chars")
                
                if "num_sources" in metadata:
                    st.metric("Sources Used", metadata["num_sources"])
    
    def _render_query_history(self) -> None:
        """Render recent query history."""
        if st.session_state.query_history:
            with st.expander(f"📚 Recent Queries ({len(st.session_state.query_history)})"):
                for i, query_entry in enumerate(reversed(st.session_state.query_history), 1):
                    timestamp = datetime.fromisoformat(query_entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    audience_icon = "🏥" if query_entry["audience"] == "clinical" else "⚙️"
                    
                    st.write(f"**{i}.** {audience_icon} *{timestamp}* - {query_entry['model']}")
                    st.write(f"   {query_entry['query'][:100]}{'...' if len(query_entry['query']) > 100 else ''}")
                    
                    if st.button(f"Rerun Query {i}", key=f"rerun_{i}"):
                        st.session_state.query_input = query_entry["query"]
                        st.rerun()
    
    def _clear_history(self) -> None:
        """Clear query and feedback history."""
        st.session_state.query_history = []
        st.session_state.feedback_history = []
    
    def get_ui_stats(self) -> Dict[str, Any]:
        """Get UI usage statistics."""
        total_queries = len(st.session_state.query_history)
        total_feedback = len(st.session_state.feedback_history)
        
        # Calculate average ratings if feedback exists
        avg_ratings = {}
        if total_feedback > 0:
            ratings_sum = {
                "clarity": 0,
                "citation": 0,
                "safety": 0,
                "usefulness": 0
            }
            
            for feedback in st.session_state.feedback_history:
                for rating_type, value in feedback["ratings"].items():
                    ratings_sum[rating_type] += value
            
            avg_ratings = {
                rating_type: total / total_feedback 
                for rating_type, total in ratings_sum.items()
            }
        
        return {
            "total_queries": total_queries,
            "total_feedback": total_feedback,
            "feedback_rate": total_feedback / max(1, total_queries),
            "avg_ratings": avg_ratings,
            "current_audience": st.session_state.audience,
            "current_model": st.session_state.current_model,
            "current_source": st.session_state.current_source
        }
    
    def export_feedback(self) -> List[Dict[str, Any]]:
        """Export feedback data for analysis."""
        return st.session_state.feedback_history.copy()
    
    def is_responsive(self) -> bool:
        """Check if UI is responsive and properly initialized."""
        required_keys = ['audience', 'feedback_history', 'query_history']
        return all(key in st.session_state for key in required_keys)