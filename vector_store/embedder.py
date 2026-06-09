import numpy as np
import hashlib

class LocalEmbedder:
    def __init__(self):
        self.model = None
        try:
            # Try to load real sentence-transformers model
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Loaded SentenceTransformer 'all-MiniLM-L6-v2' successfully.")
        except Exception as e:
            print(f"SentenceTransformer not loaded (using deterministic fallback): {e}")

    def embed_text(self, text: str) -> list:
        if self.model:
            try:
                embedding = self.model.encode(text)
                if hasattr(embedding, 'tolist'):
                    return embedding.tolist()
                return list(embedding)
            except Exception as e:
                print(f"Error generating embedding with model (falling back): {e}")
                
        # Deterministic fallback vector generation (dimension 384)
        # Matches all-MiniLM-L6-v2 dimensions exactly
        dims = 384
        vector = np.zeros(dims)
        for i in range(dims):
            hash_val = hashlib.md5(f"{text}_{i}".encode('utf-8')).hexdigest()
            vector[i] = (int(hash_val, 16) % 2000 - 1000) / 1000.0
            
        # Normalize the vector for cosine similarity calculations
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    def embed_batch(self, texts: list) -> list:
        return [self.embed_text(t) for t in texts]

# Instantiate singleton embedder
embedder = LocalEmbedder()
