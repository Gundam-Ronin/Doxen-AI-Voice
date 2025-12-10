from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from ..database.session import get_db
from ..database.models import KnowledgebaseDocument, Business
from ..core.vector_search import vector_search

router = APIRouter(prefix="/api/knowledgebase", tags=["knowledgebase"])

class DocumentCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None

@router.get("/{business_id}")
async def list_documents(business_id: int, db: Session = Depends(get_db)):
    docs = db.query(KnowledgebaseDocument).filter(
        KnowledgebaseDocument.business_id == business_id
    ).order_by(KnowledgebaseDocument.updated_at.desc()).all()
    
    return [
        {
            "id": d.id,
            "title": d.title,
            "content": d.content[:200] + "..." if len(d.content) > 200 else d.content,
            "category": d.category,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None
        }
        for d in docs
    ]

@router.get("/{business_id}/{doc_id}")
async def get_document(business_id: int, doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgebaseDocument).filter(
        KnowledgebaseDocument.id == doc_id,
        KnowledgebaseDocument.business_id == business_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "category": doc.category,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
    }

@router.post("/{business_id}")
async def create_document(business_id: int, doc: DocumentCreate, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    new_doc = KnowledgebaseDocument(
        business_id=business_id,
        title=doc.title,
        content=doc.content,
        category=doc.category
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    vector_id = f"kb_{business_id}_{new_doc.id}"
    success = vector_search.upsert_document(
        doc_id=vector_id,
        text=f"{doc.title}\n\n{doc.content}",
        metadata={
            "business_id": business_id,
            "doc_id": new_doc.id,
            "title": doc.title,
            "content": doc.content,
            "category": doc.category or ""
        }
    )
    
    if success:
        new_doc.vector_id = vector_id
        db.commit()
    
    return {
        "id": new_doc.id,
        "title": new_doc.title,
        "message": "Document created successfully",
        "vectorized": success
    }

@router.put("/{business_id}/{doc_id}")
async def update_document(
    business_id: int,
    doc_id: int,
    update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    doc = db.query(KnowledgebaseDocument).filter(
        KnowledgebaseDocument.id == doc_id,
        KnowledgebaseDocument.business_id == business_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)
    
    doc.updated_at = datetime.utcnow()
    db.commit()
    
    if doc.vector_id:
        vector_search.upsert_document(
            doc_id=doc.vector_id,
            text=f"{doc.title}\n\n{doc.content}",
            metadata={
                "business_id": business_id,
                "doc_id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "category": doc.category or ""
            }
        )
    
    return {"message": "Document updated successfully"}

@router.delete("/{business_id}/{doc_id}")
async def delete_document(business_id: int, doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgebaseDocument).filter(
        KnowledgebaseDocument.id == doc_id,
        KnowledgebaseDocument.business_id == business_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.vector_id:
        vector_search.delete_document(doc.vector_id)
    
    db.delete(doc)
    db.commit()
    
    return {"message": "Document deleted successfully"}

@router.post("/{business_id}/search")
async def search_documents(
    business_id: int,
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    results = vector_search.search(query, business_id, top_k)
    
    if not results:
        docs = db.query(KnowledgebaseDocument).filter(
            KnowledgebaseDocument.business_id == business_id,
            KnowledgebaseDocument.content.ilike(f"%{query}%")
        ).limit(top_k).all()
        
        return [
            {
                "id": d.id,
                "title": d.title,
                "content": d.content[:300],
                "score": 0.5
            }
            for d in docs
        ]
    
    return results
