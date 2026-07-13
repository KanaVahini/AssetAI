from sentence_transformers import SentenceTransformer

# Load once — reused for all documents
model = SentenceTransformer('BAAI/bge-small-en')

def embed(texts):
    """
    Converts list of text strings into vectors.
    """
    return model.encode(texts).tolist()