"""
Load environment variables and expose configuration constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH") or "data/chroma_db"
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH") or "data/assetiq.db"
