Final Requirement Document: Modular RAG PoC
This document outlines the complete modular architecture and implementation requirements for a YAML-driven Retrieval-Augmented Generation (RAG) system tailored to oncology use cases. It is split into five modules, each with detailed tasks, configuration hooks, and best practices.

1. Corpus & Embedding Lifecycle
Objective
Ingest oncology-related documents, generate embeddings, and store them for retrieval.

Tasks
YAML-Driven Ingestion Logic

Parse data_source.type: confluence or local_file

For local_file, read from configured path

For confluence, authenticate and fetch pages by space key and filter

Chunking Strategy

Use recursive or semantic splitter

Configure chunk_size and overlap

Preserve semantic boundaries

Embedding Generation

Load embedding model (e.g., PubMedBERT)

Convert chunks to vectors

Include metadata: source, date, ontology codes

Vector Storage

Use Chroma or FAISS

Store vectors with metadata

Validate vector dimensions and schema

YAML Configuration
yaml
data_source:
  type: confluence | local_file
  path: ./data/
  confluence:
    base_url: https://your-domain.atlassian.net/wiki
    auth_token: ${CONFLUENCE_TOKEN}
    space_key: ONCOLOGY
    page_filter: ["biomarkers", "protocols"]

chunking:
  strategy: recursive
  chunk_size: 512
  overlap: 64

embedding_model:
  name: pubmedbert
  device: cpu
Best Practices
Use pydantic for YAML schema validation

Modularize ingestion and embedding

Log embedding stats: chunk count, vector size, processing time

2. Query Processing & Retrieval
Objective
Convert user query to embedding and retrieve relevant chunks.

Tasks
Query Input

Accept query from UI or API

Normalize query text

Embedding Conversion

Use same embedding model as corpus

Convert query to vector

Retrieval Logic

Use cosine similarity or hybrid search

Retrieve top-k chunks

Apply filters: ontology match, date range

Context Packaging

Return retrieved chunks with metadata

Prepare context for LLM prompt

YAML Configuration
yaml
retrieval:
  top_k: 5
  strategy: similarity
  filters:
    ontology_match: true
    date_range: last_12_months
Best Practices
Use caching for repeated queries

Log retrieval latency and hit rate

Validate query format before embedding

3. LLM Orchestration
Objective
Generate grounded response using selected model.

Tasks
Model Loading

Load model via KoboldCpp

Select model and endpoint from YAML

Prompt Construction

Load prompt template

Inject system instructions

Append retrieved context and user query

Model Invocation

Send prompt to model endpoint

Parse and return response

YAML Configuration
yaml
llm:
  model: biomistral
  provider: koboldcpp
  api_url: http://localhost:5000/v1
  prompt_template: ./prompts/business.txt
  system_instruction: "You are a biomedical assistant..."
Best Practices
Use retry logic for timeouts

Abstract model selection via YAML

Log token usage and response time

4. UI Layer
Objective
Provide user interface for query input and response display.

Tasks
Frontend Setup

Use Streamlit or Flask

Build query input box

Display response with markdown formatting

Audience Toggle

Add toggle for clinical vs technical view

Persist toggle state across sessions

Feedback Capture

Add sliders or text area for clarity, citation, safety

Store feedback with timestamp and query hash

YAML Configuration
yaml
ui:
  framework: streamlit
  audience_toggle: true
  feedback_enabled: true
  show_chunk_metadata: true
  default_model: biomistral
  default_source: confluence
Best Practices
Use responsive layout

Validate input before submission

Log user interactions for evaluation

5. Evaluation & Logging
Objective
Track performance and safety of RAG system.

Tasks
Retrieval Metrics

Log precision@1, @3

Track chunk overlap and hit rate

Generation Metrics

Log clarity score

Track citation coverage

Monitor safety adherence

Logging Infrastructure

Use structured logging (JSON)

Timestamp all events

Store logs in configured path

YAML Configuration
yaml
evaluation:
  metrics:
    precision_at_k: true
    citation_coverage: true
    clarity_rating: true
    latency: true
    safety: true
  logging:
    enabled: true
    format: json
    path: ./logs/
Best Practices
Anonymize user data if stored

Separate logs per module

Use YAML to toggle metrics and logging format