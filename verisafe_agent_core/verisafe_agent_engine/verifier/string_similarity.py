import Levenshtein
import numpy as np
from client import client

import os
import pickle
import numpy as np
import atexit
from utils import log

# Global variables
embedding_model: str = "text-embedding-3-small"
string_similarity_threshold: float = 0.7

# Create .cache directory if it doesn't exist
cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(cache_dir, exist_ok=True)
cache_file = os.path.join(cache_dir, "embedding_cache.pkl")

# Load cache from file if it exists
cache: dict[str, np.ndarray] = {}
if os.path.exists(cache_file):
    try:
        with open(cache_file, "rb") as f:
            cache = pickle.load(f)
            log(f"Successfully loaded cache from {cache_file}")
            log(f"Cache size: {len(cache)}")
    except Exception as e:
        log(f"Error loading cache: {e}", "red")


def save_cache():
    """Save cache to file before program ends"""
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(cache, f)
    except Exception as e:
        log(f"Error saving cache: {e}", "red")


# Register save_cache function to be called when program exits
atexit.register(save_cache)


def query_embedding(query: str) -> np.ndarray:
    if query in cache:
        return cache[query]
    else:
        embedding = client.embeddings.create(
            input=[query], model="text-embedding-3-small"
        )
        cache[query] = np.array(embedding.data[0].embedding)
        return cache[query]


def cosine_similarity(a: str, b: str) -> float:
    embedding_a = query_embedding(a)
    embedding_b = query_embedding(b)
    return np.dot(embedding_a, embedding_b) / (
        np.linalg.norm(embedding_a) * np.linalg.norm(embedding_b)
    )


def ratio_sim(s1, s2):
    return Levenshtein.ratio(s1, s2)


def jaro_sim(s1, s2):
    return Levenshtein.jaro(s1, s2)


def jaro_winkler_sim(s1, s2):
    return Levenshtein.jaro_winkler(s1, s2)


def embedding_sim(s1, s2):
    return cosine_similarity(s1, s2)
