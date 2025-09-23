import pytest
from langchain.docstore.document import Document
from rag_ing.chunking import chunking_service
from rag_ing.config.settings import ChunkingConfig

@pytest.fixture
def sample_document():
    """Fixture for a sample document."""
    return Document(
        page_content="This is a test document. It has several sentences. The purpose is to test the chunking service.",
        metadata={"source": "test"}
    )

def test_chunk_documents_recursive(sample_document):
    """Test recursive text splitting."""
    config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
    chunking_service.update_config(config)

    chunks = chunking_service.chunk_documents([sample_document], chunk_method="recursive")

    assert len(chunks) > 1
    assert all(isinstance(chunk, Document) for chunk in chunks)
    for chunk in chunks:
        assert len(chunk.page_content) <= 50

def test_chunk_documents_respects_size_and_overlap(sample_document):
    """Test that chunk size and overlap are respected."""
    config = ChunkingConfig(chunk_size=30, chunk_overlap=15)
    chunking_service.update_config(config)

    chunks = chunking_service.chunk_documents([sample_document], chunk_method="recursive")

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.page_content) <= 30

    # Check for overlap by seeing if the start of the next chunk is in the previous one
    for i in range(len(chunks) - 1):
        assert chunks[i+1].page_content[:5] in chunks[i].page_content


def test_chunk_empty_document():
    """Test chunking an empty document."""
    empty_doc = Document(page_content="", metadata={"source": "empty"})
    config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
    chunking_service.update_config(config)

    chunks = chunking_service.chunk_documents([empty_doc], chunk_method="recursive")

    assert len(chunks) == 0

def test_get_available_methods():
    """Test that available chunking methods are returned."""
    methods = chunking_service.get_available_methods()
    assert isinstance(methods, list)
    assert "recursive" in methods
    assert "character" in methods

def test_get_chunk_statistics(sample_document):
    """Test chunk statistics calculation."""
    config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
    chunking_service.update_config(config)
    chunks = chunking_service.chunk_documents([sample_document], chunk_method="recursive")

    stats = chunking_service.get_chunk_statistics(chunks)

    assert stats["total_chunks"] == len(chunks)
    assert stats["average_chunk_size"] > 0
    assert stats["min_chunk_size"] > 0
    assert stats["max_chunk_size"] > 0
    assert stats["min_chunk_size"] <= stats["max_chunk_size"]
