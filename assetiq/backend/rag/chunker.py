def chunk_text(text, chunk_size=400, overlap=100):
    """
    Splits text into overlapping chunks.
    Works for any document from any plant.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks