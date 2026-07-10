"""
Pydantic models for API request/response bodies.
"""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
