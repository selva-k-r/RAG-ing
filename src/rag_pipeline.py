import os
import json
from typing import Dict, Any, List

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.docstore.document import Document

from src.vector_store import load_config


def format_docs(docs: List[Document]) -> str:
    """
    Formats the retrieved documents into a single string with their metadata.
    """
    return "\n\n".join(
        f"Source: {doc.metadata.get('source_path', 'N/A')}\n"
        f"Section: {doc.metadata.get('section_header', 'N/A')}\n"
        f"Content: {doc.page_content}"
        for doc in docs
    )


def get_rag_chain(config: Dict[str, Any]) -> Runnable:
    """
    Creates and returns the RAG chain.
    """
    # 1. Load vector store and create retriever
    embedding_model = HuggingFaceEmbeddings(model_name=config['embedding_model'])

    index_dir = os.path.dirname(config['faiss_index_path'])
    index_name = os.path.basename(config['faiss_index_path'])

    if not os.path.exists(os.path.join(index_dir, f"{index_name}.faiss")):
        raise FileNotFoundError(
            f"FAISS index not found at {config['faiss_index_path']}. "
            "Please run the ingestion pipeline (main.py) first."
        )

    vector_store = FAISS.load_local(
        index_dir,
        embedding_model,
        index_name,
        allow_dangerous_deserialization=True
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": config.get("retrieval_k", 5)})

    # 2. Construct prompt template
    prompt_template_str = """
System: You are an expert assistant for oncology and technical documentation. Your task is to answer the user's query based *only* on the provided context. You must provide two distinct views in your answer:
1.  A clinical/business view for non-technical stakeholders.
2.  A technical/implementation view for developers.

You must also cite the sources of your information from the context provided.

Your final output must be a single, valid JSON object with the following keys: "clinical_view", "technical_view", and "sources".

Context:
{context}

Query: {query}

Answer (in JSON format):
"""
    prompt = PromptTemplate.from_template(prompt_template_str)

    # 3. Initialize LLM
    if config['model_provider'] == 'azure_openai':
        llm = AzureChatOpenAI(
            api_key=config['azure_openai']['api_key'],
            azure_endpoint=config['azure_openai']['endpoint'],
            api_version=config['azure_openai']['api_version'],
            azure_deployment=config['azure_openai']['deployment_name'],
            temperature=0,
            max_retries=3,
        )
    elif config['model_provider'] == 'local_llm':
        llm = ChatOpenAI(
            base_url=config['local_llm']['base_url'],
            api_key=config['local_llm']['api_key'],
            temperature=0,
        )
    else:
        raise ValueError(f"Unsupported model provider: {config['model_provider']}")

    # 4. Create and return RAG chain
    return (
        {"context": retriever | format_docs, "query": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def answer_query(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Answers a query using the RAG pipeline.
    """
    rag_chain = get_rag_chain(config)
    llm_response_str = rag_chain.invoke(query)

    try:
        response_json = json.loads(llm_response_str)

        for key in ["clinical_view", "technical_view", "sources"]:
            if key not in response_json:
                response_json[key] = f"Missing '{key}' in LLM response." if key != "sources" else []

        if isinstance(response_json.get('sources'), list):
            response_json['sources'] = list(dict.fromkeys(response_json['sources']))

        return response_json

    except (json.JSONDecodeError, TypeError) as e:
        return {
            "clinical_view": "Error: The model's response could not be parsed.",
            "technical_view": f"The model returned a non-JSON response. Error: {e}. Raw output: {llm_response_str}",
            "sources": []
        }