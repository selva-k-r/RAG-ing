import streamlit as st
from rag_ing.config.settings import settings, EmbeddingModelConfig, LLMConfig, SnowflakeConfig
from rag_ing.models.embedding_manager import embedding_manager
from rag_ing.models.llm_manager import llm_manager
from rag_ing.storage.vector_store import vector_store_manager

def sidebar_configuration():
    """Sidebar for configuration settings."""
    st.sidebar.title("⚙️ Configuration")

    # Embedding Model Configuration
    st.sidebar.subheader("🔤 Embedding Model")

    embedding_provider = st.sidebar.selectbox(
        "Provider",
        embedding_manager.list_available_providers(),
        index=0,
        key="embedding_provider",
    )

    recommended_models = embedding_manager.get_recommended_models(embedding_provider)
    embedding_model = st.sidebar.selectbox(
        "Model",
        recommended_models,
        index=0 if recommended_models else None,
        key="embedding_model",
    )

    embedding_api_key = st.sidebar.text_input(
        "API Key",
        type="password",
        help="Enter API key for the embedding provider",
        key="embedding_api_key",
        value=settings.get_api_key(embedding_provider) or ""
    )

    # LLM Configuration
    st.sidebar.subheader("🤖 Language Model")

    llm_provider = st.sidebar.selectbox(
        "Provider",
        llm_manager.list_available_providers(),
        index=0,
        key="llm_provider",
    )

    recommended_llm_models = llm_manager.get_recommended_models(llm_provider)
    llm_model = st.sidebar.selectbox(
        "Model",
        recommended_llm_models,
        index=0 if recommended_llm_models else None,
        key="llm_model",
    )

    llm_api_key = st.sidebar.text_input(
        "LLM API Key",
        type="password",
        help="Enter API key for the LLM provider",
        key="llm_api_key",
        value=settings.get_api_key(llm_provider) or ""
    )

    llm_temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.settings.llm.temperature,
        step=0.1,
        key="llm_temperature",
    )

    # Vector Store Configuration
    st.sidebar.subheader("🗄️ Vector Store")

    vector_store_type = st.sidebar.selectbox(
        "Type",
        vector_store_manager.list_available_stores(),
        index=0,
        key="vector_store_type",
    )

    # Snowflake configuration (if selected)
    snowflake_config = None
    if vector_store_type == "snowflake":
        st.sidebar.write("**Snowflake Configuration**")
        sf_account = st.sidebar.text_input("Account", key="sf_account", value=st.session_state.settings.snowflake.account if st.session_state.settings.snowflake else "")
        sf_user = st.sidebar.text_input("User", key="sf_user", value=st.session_state.settings.snowflake.user if st.session_state.settings.snowflake else "")
        sf_password = st.sidebar.text_input("Password", type="password", key="sf_password", value=st.session_state.settings.snowflake.password if st.session_state.settings.snowflake else "")
        sf_warehouse = st.sidebar.text_input("Warehouse", key="sf_warehouse", value=st.session_state.settings.snowflake.warehouse if st.session_state.settings.snowflake else "")
        sf_database = st.sidebar.text_input("Database", key="sf_database", value=st.session_state.settings.snowflake.database if st.session_state.settings.snowflake else "")
        sf_schema = st.sidebar.text_input("Schema", key="sf_schema", value=st.session_state.settings.snowflake.schema if st.session_state.settings.snowflake else "")

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
                # Update settings in session state
                st.session_state.settings.embedding_model.provider = embedding_provider
                st.session_state.settings.embedding_model.model_name = embedding_model
                st.session_state.settings.embedding_model.api_key = embedding_api_key
                st.session_state.settings.llm.provider = llm_provider
                st.session_state.settings.llm.model_name = llm_model
                st.session_state.settings.llm.api_key = llm_api_key
                st.session_state.settings.llm.temperature = llm_temperature
                if snowflake_config:
                    st.session_state.settings.snowflake = snowflake_config

                # Load embedding model
                embedding_manager.load_model(st.session_state.settings.embedding_model)
                st.session_state.embedding_model_loaded = True

                # Load LLM
                llm_manager.load_model(st.session_state.settings.llm)
                st.session_state.llm_loaded = True

                # Create vector store
                if vector_store_type == "snowflake" and st.session_state.settings.snowflake:
                    st.session_state.vector_store = vector_store_manager.create_snowflake_store(
                        st.session_state.settings.snowflake, embedding_manager._current_model
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
