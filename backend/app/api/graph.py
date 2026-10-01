from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Repository, FileRecord, SymbolRecord, SymbolEdgeRecord
from app.ingestion.graph_builder import SymbolGraph
from app.ingestion.parser import ParsedFile, ParsedSymbol, ParsedImport

router = APIRouter(prefix="/repos/{repo_id}/graph", tags=["graph"])

@router.get("")
def get_repository_graph(
    repo_id: int,
    max_nodes: int = 120,
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    files = db.query(FileRecord).filter(FileRecord.repo_id == repo_id).all()
    symbols = db.query(SymbolRecord).filter(SymbolRecord.repo_id == repo_id).all()
    edges = db.query(SymbolEdgeRecord).filter(SymbolEdgeRecord.repo_id == repo_id).all()

    # Build React Flow nodes
    nodes = []
    # Index top symbols by importance
    sorted_symbols = sorted(symbols, key=lambda s: s.importance_score or 1.0, reverse=True)[:max_nodes]
    active_symbol_names = set(s.name for s in sorted_symbols)
    active_files = set(s.file.path for s in sorted_symbols if s.file)

    import math
    total = len(sorted_symbols)
    radius = max(350, total * 9)
    angle_step = 2 * math.pi / max(total, 1)

    for i, s in enumerate(sorted_symbols):
        angle = i * angle_step
        x = 500 + radius * math.cos(angle)
        y = 500 + radius * math.sin(angle)
        fpath = s.file.path if s.file else ""

        nodes.append({
            "id": f"sym:{s.id}",
            "type": "symbolNode",
            "position": {"x": round(x, 1), "y": round(y, 1)},
            "data": {
                "id": s.id,
                "label": s.name,
                "kind": s.kind,
                "file_path": fpath,
                "signature": s.signature,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "importance": round(s.importance_score or 1.0, 3)
            }
        })

    # Build React Flow edges
    rf_edges = []
    sym_name_to_node_id = {s.name: f"sym:{s.id}" for s in sorted_symbols}

    for idx, e in enumerate(edges):
        if e.source_symbol in sym_name_to_node_id and e.target_symbol in sym_name_to_node_id:
            rf_edges.append({
                "id": f"edge-{idx}",
                "source": sym_name_to_node_id[e.source_symbol],
                "target": sym_name_to_node_id[e.target_symbol],
                "label": e.edge_type,
                "animated": e.edge_type == "calls",
                "style": {
                    "stroke": "#3b82f6" if e.edge_type == "calls" else "#10b981",
                    "strokeWidth": 1.5
                }
            })

    return {
        "nodes": nodes,
        "edges": rf_edges,
        "total_nodes": len(nodes),
        "total_edges": len(rf_edges)
    }
