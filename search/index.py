from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import Optional
import pandas as pd
import streamlit as st

def get_embeddings(model,texts:list):
    encoder = SentenceTransformer(model)
    vectors = encoder.encode(texts,show_progress_bar=True)
    return vectors

def create_index(vectors):
    vector_dimension = vectors.shape[1]
    print(vector_dimension)
    index = faiss.IndexFlatL2(vector_dimension)
    print('intialized index')
    # faiss.normalize_L2(vectors)
    print('normalized index')
    index.add(vectors)
    return index

def query(index,query_string,model,k:Optional[int]=None):
    encoder = SentenceTransformer(model)
    search_vector = encoder.encode(query_string)
    _vector = np.array([search_vector])
    # faiss.normalize_L2(_vector)
    k = k or index.ntotal
    distances, ann = index.search(_vector, k=k)
    results = pd.DataFrame({'distances': distances[0], 'ann': ann[0]})
    return results

def save_index(index,path):
    faiss.write_index(index, path)

def load_index(index,path):
    index = faiss.read_index(path)
    return index