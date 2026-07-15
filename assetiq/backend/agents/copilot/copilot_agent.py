import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "rag"))

os.chdir(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, os.path.abspath("backend/rag"))
sys.path.insert(1, os.path.abspath("backend/knowledge_graph"))

sys.path.append(RAG_DIR)


from groq import Groq
from dotenv import load_dotenv
from chroma_store import search

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are AssetIQ Copilot — an expert industrial knowledge assistant.

Rules:
1. Answer ONLY using the documents provided below
2. Always mention which document your answer came from
3. Include specific details — dates, temperatures, equipment tags
4. If answer is not in the documents, say "I don't have that information"
5. Be concise and specific
"""

def run(user_query, plant_name=None):
    # Step 1: Find relevant chunks from vector DB
    results = search(user_query, plant_name=plant_name, top_k=5)
    
    chunks    = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    # Step 2: Build context from retrieved chunks
    context = ""
    for chunk, meta in zip(chunks, metadatas):
        context += f"\n[Source: {meta['filename']}]\n{chunk}\n"
    
    # Step 3: Ask Groq LLM with context
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": 
             f"Documents:\n{context}\n\nQuestion: {user_query}"}
        ]
    )
    
    answer = response.choices[0].message.content
    sources = list(set([m["filename"] for m in metadatas]))
    
    return {
        "answer":  answer,
        "sources": sources,
        "chunks_used": len(chunks)
    }


if __name__ == "__main__":
    # Quick test
    result = run("Why did Pump P-104 fail in March 2024?")
    print("Answer:", result["answer"])
    print("\nSources:", result["sources"])