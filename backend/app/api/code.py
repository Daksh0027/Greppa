import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Repository, FileRecord, SymbolRecord

router = APIRouter(prefix="/repos/{repo_id}", tags=["code & files"])

@router.get("/files")
def list_repository_files(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    files = db.query(FileRecord).filter(FileRecord.repo_id == repo_id).order_by(FileRecord.importance_score.desc()).all()
    return [
        {
            "id": f.id,
            "path": f.path,
            "language": f.language,
            "line_count": f.line_count,
            "importance_score": f.importance_score,
            "summary": f.summary
        }
        for f in files
    ]

@router.get("/code")
def get_file_content(
    repo_id: int,
    path: str = Query(..., description="Relative path of the file"),
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Sanitize path to prevent directory traversal
    norm_path = os.path.normpath(path).replace("\\", "/")
    if norm_path.startswith("..") or "/../" in norm_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    abs_path = os.path.join(repo.url_or_path, norm_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail=f"File not found: {norm_path}")

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Find symbols in this file
        file_rec = db.query(FileRecord).filter(
            FileRecord.repo_id == repo_id,
            FileRecord.path == norm_path
        ).first()

        symbols = []
        if file_rec:
            sym_records = db.query(SymbolRecord).filter(SymbolRecord.file_id == file_rec.id).all()
            symbols = [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "signature": s.signature,
                    "importance": s.importance_score
                }
                for s in sym_records
            ]

        return {
            "path": norm_path,
            "content": content,
            "language": file_rec.language if file_rec else "plaintext",
            "symbols": symbols
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
