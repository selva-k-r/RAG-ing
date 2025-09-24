import streamlit as st
from rag_ing.connectors import ConfluenceConnector, MediumConnector, social_connector_manager
from rag_ing.config.settings import settings
from rag_ing.utils.exceptions import ConnectionError, AuthenticationError, APIError, DocumentProcessingError

def get_connector_config(source_type: str):
    """Gets the configuration for a given source type."""
    if source_type == "Confluence":
        return settings.connectors.confluence or {}
    elif source_type == "Medium":
        return settings.connectors.medium or {}
    elif source_type == "Twitter":
        return (settings.connectors.social_media or {}).get("twitter", {})
    elif source_type == "Reddit":
        return (settings.connectors.social_media or {}).get("reddit", {})
    return {}

def get_connector(source_type: str, config: dict):
    """Gets the connector for a given source type."""
    if source_type == "Confluence":
        return ConfluenceConnector(config)
    elif source_type == "Medium":
        return MediumConnector(config)
    elif source_type == "Twitter":
        return social_connector_manager.create_connector("twitter", config)
    elif source_type == "Reddit":
        return social_connector_manager.create_connector("reddit", config)
    return None

def document_sources_tab():
    """Tab for configuring and connecting document sources."""
    st.header("📄 Document Sources")

    source_type = st.selectbox(
        "Select Source Type",
        ["Confluence", "Medium", "Twitter", "Reddit"]
    )

    config_ui(source_type)

def config_ui(source_type: str):
    """Renders the configuration UI for the selected source type."""
    source_config = get_connector_config(source_type)

    st.subheader(f"Configure {source_type}")

    if source_type == "Confluence":
        config = confluence_ui(source_config)
    elif source_type == "Medium":
        config = medium_ui(source_config)
    elif source_type == "Twitter":
        config = twitter_ui(source_config)
    elif source_type == "Reddit":
        config = reddit_ui(source_config)

    fetch_limit = st.number_input("Number of documents to fetch", min_value=1, max_value=100, value=10)

    if st.button(f"📥 Fetch from {source_type}"):
        if not all(config.values()):
            st.warning("⚠️ Please fill in all required fields.")
            return

        connector = get_connector(source_type, config)
        if not connector:
            st.error(f"❌ Unknown source type: {source_type}")
            return

        with st.spinner(f"Fetching documents from {source_type}..."):
            try:
                documents = connector.fetch_documents(limit=fetch_limit)
                if documents:
                    st.session_state.documents.extend(documents)
                    st.success(f"✅ Fetched {len(documents)} documents from {source_type}!")

                    # Show preview
                    st.subheader("📋 Document Preview")
                    for i, doc in enumerate(documents[:3]):  # Show first 3
                        with st.expander(f"Document {i+1}: {doc.metadata.get('title', 'Untitled')}"):
                            st.write(f"**Content:** {doc.page_content[:500]}...")
                            st.write(f"**Metadata:** {doc.metadata}")
                else:
                    st.warning("⚠️ No documents found.")

            except AuthenticationError as e:
                st.error(f"🔑 Authentication Error: {e}")
            except ConnectionError as e:
                st.error(f"🔌 Connection Error: {e}")
            except APIError as e:
                st.error(f"💥 API Error: {e}")
            except DocumentProcessingError as e:
                st.error(f"📄 Document Processing Error: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

def confluence_ui(defaults: dict):
    """UI for Confluence connector."""
    col1, col2 = st.columns(2)
    with col1:
        base_url = st.text_input("Base URL", placeholder="https://your-domain.atlassian.net", value=defaults.get("base_url", ""))
        username = st.text_input("Username", value=defaults.get("username", ""))
    with col2:
        api_token = st.text_input("API Token", type="password", value=defaults.get("api_token", ""))
        space_key = st.text_input("Space Key (optional)", value=defaults.get("space_key", ""))

    return {
        "base_url": base_url,
        "username": username,
        "api_token": api_token,
        "space_key": space_key,
    }

def medium_ui(defaults: dict):
    """UI for Medium connector."""
    col1, col2 = st.columns(2)
    with col1:
        user_id = st.text_input("User ID (@username)", value=defaults.get("user_id", ""))
    with col2:
        rss_url = st.text_input("RSS URL (optional)", value=defaults.get("rss_url", ""))

    return {"user_id": user_id, "rss_url": rss_url}

def twitter_ui(defaults: dict):
    """UI for Twitter connector."""
    col1, col2 = st.columns(2)
    with col1:
        bearer_token = st.text_input("Bearer Token", type="password", value=defaults.get("bearer_token", ""))
    with col2:
        username = st.text_input("Username to fetch from", value=defaults.get("username", ""))

    return {"bearer_token": bearer_token, "username": username}

def reddit_ui(defaults: dict):
    """UI for Reddit connector."""
    col1, col2 = st.columns(2)
    with col1:
        client_id = st.text_input("Client ID", value=defaults.get("client_id", ""))
        client_secret = st.text_input("Client Secret", type="password", value=defaults.get("client_secret", ""))
    with col2:
        subreddit = st.text_input("Subreddit", value=defaults.get("subreddit", ""))
        sort_method = st.selectbox("Sort by", ["hot", "new", "top", "rising"])

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "subreddit": subreddit,
        "sort_method": sort_method,
    }
