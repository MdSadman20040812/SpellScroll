import os
import numpy as np
from django.conf import settings
from .embedder import embedder

CHROMA_PERSIST_DIR = getattr(settings, 'CHROMA_PERSIST_DIR', './vector_store/chroma_data')

class ChromaClientManager:
    def __init__(self):
        self.client = None
        self.webtoon_collection = None
        self.context_collection = None
        self.is_mock = False
        
        # Internal mock DB structure
        self.mock_db = {"webtoon_universe": {}, "context_window_db": {}}
        
        try:
            import chromadb
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            
            # Initialize collections using cosine distance
            self.webtoon_collection = self.client.get_or_create_collection(
                name="webtoon_universe", metadata={"hnsw:space": "cosine"}
            )
            self.context_collection = self.client.get_or_create_collection(
                name="context_window_db", metadata={"hnsw:space": "cosine"}
            )
            print("ChromaDB persistent client & collections initialized.")
        except Exception as e:
            print(f"ChromaDB package/init not available (running in fallback mock mode): {e}")
            self.is_mock = True

    def upsert_webtoon(self, doc_id: str, text: str, metadata: dict):
        embedding = embedder.embed_text(text)
        if not self.is_mock and self.webtoon_collection:
            try:
                self.webtoon_collection.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text],
                    metadatas=[metadata]
                )
                return
            except Exception as e:
                print(f"Chroma upsert failed (falling back to mock): {e}")
                
        self.mock_db["webtoon_universe"][doc_id] = {
            "embedding": embedding,
            "document": text,
            "metadata": metadata
        }

    def query_webtoons(self, query_text: str, top_k: int = 10) -> list:
        query_embedding = embedder.embed_text(query_text)
        if not self.is_mock and self.webtoon_collection:
            try:
                results = self.webtoon_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                output = []
                if results and 'ids' in results and results['ids'] and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        output.append({
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "distance": results['distances'][0][i] if 'distances' in results else 0.0
                        })
                return output
            except Exception as e:
                print(f"Chroma query failed (falling back to mock): {e}")
                
        # Mock search using cosine similarity
        output = []
        q_v = np.array(query_embedding)
        for doc_id, data in self.mock_db["webtoon_universe"].items():
            d_v = np.array(data["embedding"])
            denom = (np.linalg.norm(q_v) * np.linalg.norm(d_v)) + 1e-9
            similarity = np.dot(q_v, d_v) / denom
            distance = float(1.0 - similarity)
            output.append({
                "id": doc_id,
                "document": data["document"],
                "metadata": data["metadata"],
                "distance": distance
            })
        return sorted(output, key=lambda x: x["distance"])[:top_k]

    def upsert_context_memory(self, doc_id: str, text: str, metadata: dict):
        embedding = embedder.embed_text(text)
        if not self.is_mock and self.context_collection:
            try:
                self.context_collection.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text],
                    metadatas=[metadata]
                )
                return
            except Exception as e:
                print(f"Chroma context upsert failed (falling back to mock): {e}")
                
        self.mock_db["context_window_db"][doc_id] = {
            "embedding": embedding,
            "document": text,
            "metadata": metadata
        }

    def query_context_memory(self, query_text: str, top_k: int = 3) -> list:
        query_embedding = embedder.embed_text(query_text)
        if not self.is_mock and self.context_collection:
            try:
                results = self.context_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                output = []
                if results and 'ids' in results and results['ids'] and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        output.append({
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i]
                        })
                return output
            except Exception as e:
                print(f"Chroma context query failed (falling back to mock): {e}")
                
        output = []
        q_v = np.array(query_embedding)
        for doc_id, data in self.mock_db["context_window_db"].items():
            d_v = np.array(data["embedding"])
            denom = (np.linalg.norm(q_v) * np.linalg.norm(d_v)) + 1e-9
            similarity = np.dot(q_v, d_v) / denom
            distance = float(1.0 - similarity)
            output.append({
                "id": doc_id,
                "document": data["document"],
                "metadata": data["metadata"],
                "distance": distance
            })
        sorted_res = sorted(output, key=lambda x: x["distance"])[:top_k]
        return [{"id": r["id"], "document": r["document"], "metadata": r["metadata"]} for r in sorted_res]

    def reset_all(self):
        if not self.is_mock and self.client:
            try:
                self.client.reset()
                # Recreate collections after reset
                self.webtoon_collection = self.client.get_or_create_collection(name="webtoon_universe")
                self.context_collection = self.client.get_or_create_collection(name="context_window_db")
                return
            except Exception as e:
                print(f"Chroma client reset error (clearing locally): {e}")
        self.mock_db = {"webtoon_universe": {}, "context_window_db": {}}

# Singleton Chroma DB controller
chroma_client = ChromaClientManager()

def reset_chroma_collections():
    chroma_client.reset_all()
