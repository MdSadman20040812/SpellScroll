import os
import django

# Setup Django settings for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spellscroll.settings')
django.setup()

from vector_store.chroma_client import chroma_client
from vector_store.embedder import embedder

def test_embedder_dimensions():
    # Verify that the embedder generates a 384-dimensional vector
    vec = embedder.embed_text("Test query")
    assert len(vec) == 384
    assert isinstance(vec[0], float)

def test_chroma_upsert_and_query():
    # Reset first
    chroma_client.reset_all()
    
    # Upsert test item
    chroma_client.upsert_webtoon(
        doc_id="test_1",
        text="A magical story about a young girl who discovers a hidden spell scroll.",
        metadata={"title": "Magic Scroll", "rank": 1}
    )
    
    # Query with matching text
    results = chroma_client.query_webtoons("spell scroll", top_k=1)
    assert len(results) == 1
    assert results[0]['id'] == "test_1"
    assert "spell scroll" in results[0]['document'].lower()
