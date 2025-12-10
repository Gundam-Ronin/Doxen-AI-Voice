import os
from typing import List, Optional

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = None

def get_openai_client():
    global client
    if client is None and OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX = os.environ.get("PINECONE_INDEX", "cortana-kb")

class VectorSearch:
    def __init__(self):
        self.pinecone_client = None
        self.index = None
        if PINECONE_API_KEY:
            try:
                from pinecone import Pinecone
                self.pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
                self.index = self.pinecone_client.Index(PINECONE_INDEX)
            except Exception as e:
                print(f"Pinecone initialization error: {e}")
    
    def create_embedding(self, text: str) -> List[float]:
        openai_client = get_openai_client()
        if not openai_client:
            return []
        
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return []
    
    def upsert_document(self, doc_id: str, text: str, metadata: dict) -> bool:
        if not self.index:
            return False
        
        try:
            embedding = self.create_embedding(text)
            if not embedding:
                return False
            
            self.index.upsert(vectors=[{
                "id": doc_id,
                "values": embedding,
                "metadata": metadata
            }])
            return True
        except Exception as e:
            print(f"Upsert error: {e}")
            return False
    
    def search(self, query: str, business_id: int, top_k: int = 5) -> List[dict]:
        if not self.index:
            return []
        
        try:
            embedding = self.create_embedding(query)
            if not embedding:
                return []
            
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                filter={"business_id": business_id}
            )
            
            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "content": match.metadata.get("content", ""),
                    "title": match.metadata.get("title", "")
                }
                for match in results.matches
            ]
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        if not self.index:
            return False
        
        try:
            self.index.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False

vector_search = VectorSearch()

def get_relevant_context(query: str, business_id: int) -> str:
    results = vector_search.search(query, business_id)
    if not results:
        return ""
    
    context_parts = []
    for result in results[:3]:
        if result["score"] > 0.7:
            context_parts.append(f"- {result['title']}: {result['content']}")
    
    return "\n".join(context_parts)
