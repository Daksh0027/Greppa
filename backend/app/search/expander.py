from typing import List, Dict, Optional, Any, Set
from sqlalchemy.orm import Session
from app.core.models import SymbolEdgeRecord, SymbolRecord, FileRecord
from app.search.hybrid import SearchHit

class GraphContext:
    def __init__(self, hit: SearchHit):
        self.hit = hit
        self.callers: List[Dict[str, Any]] = []
        self.callees: List[Dict[str, Any]] = []
        self.parent_class: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.hit.to_dict(),
            "callers": self.callers,
            "callees": self.callees,
            "parent_class": self.parent_class
        }

class GraphExpander:
    def __init__(self, db: Session, repo_id: int):
        self.db = db
        self.repo_id = repo_id

    def expand_hits(self, hits: List[SearchHit], max_expanded: int = 5) -> List[GraphContext]:
        """
        Expands top search hits using the symbol graph:
        - Pulls in incoming callers (who calls this?)
        - Pulls in outgoing callees (what does this call?)
        - Pulls in parent class definition if method
        """
        expanded: List[GraphContext] = []

        for hit in hits[:max_expanded]:
            ctx = GraphContext(hit)
            sym_name = hit.symbol_name
            if not sym_name:
                expanded.append(ctx)
                continue

            # 1. Incoming Callers (who calls this symbol?)
            caller_edges = self.db.query(SymbolEdgeRecord).filter(
                SymbolEdgeRecord.repo_id == self.repo_id,
                SymbolEdgeRecord.target_symbol == sym_name,
                SymbolEdgeRecord.edge_type == "calls"
            ).limit(5).all()

            for edge in caller_edges:
                # Find caller symbol record
                caller_sym = self.db.query(SymbolRecord).filter(
                    SymbolRecord.repo_id == self.repo_id,
                    SymbolRecord.name == edge.source_symbol,
                    SymbolRecord.file.has(FileRecord.path == edge.source_file)
                ).first()

                ctx.callers.append({
                    "file_path": edge.source_file,
                    "symbol_name": edge.source_symbol,
                    "signature": caller_sym.signature if caller_sym else "",
                    "start_line": caller_sym.start_line if caller_sym else None,
                    "end_line": caller_sym.end_line if caller_sym else None
                })

            # 2. Outgoing Callees (what does this symbol call?)
            callee_edges = self.db.query(SymbolEdgeRecord).filter(
                SymbolEdgeRecord.repo_id == self.repo_id,
                SymbolEdgeRecord.source_symbol == sym_name,
                SymbolEdgeRecord.edge_type == "calls"
            ).limit(5).all()

            for edge in callee_edges:
                callee_sym = self.db.query(SymbolRecord).filter(
                    SymbolRecord.repo_id == self.repo_id,
                    SymbolRecord.name == edge.target_symbol
                ).first()

                ctx.callees.append({
                    "file_path": edge.target_file,
                    "symbol_name": edge.target_symbol,
                    "signature": callee_sym.signature if callee_sym else "",
                    "start_line": callee_sym.start_line if callee_sym else None,
                    "end_line": callee_sym.end_line if callee_sym else None
                })

            # 3. Parent Class Definition
            sym_rec = self.db.query(SymbolRecord).filter(
                SymbolRecord.repo_id == self.repo_id,
                SymbolRecord.name == sym_name,
                SymbolRecord.file.has(FileRecord.path == hit.file_path)
            ).first()

            if sym_rec and sym_rec.parent_symbol_name:
                parent_rec = self.db.query(SymbolRecord).filter(
                    SymbolRecord.repo_id == self.repo_id,
                    SymbolRecord.name == sym_rec.parent_symbol_name,
                    SymbolRecord.file.has(FileRecord.path == hit.file_path)
                ).first()

                if parent_rec:
                    ctx.parent_class = {
                        "name": parent_rec.name,
                        "signature": parent_rec.signature,
                        "docstring": parent_rec.docstring,
                        "start_line": parent_rec.start_line,
                        "end_line": parent_rec.end_line,
                        "file_path": hit.file_path
                    }

            expanded.append(ctx)

        return expanded
