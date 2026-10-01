from typing import List, Dict, Any, Optional
from app.ingestion.parser import ParsedFile, ParsedSymbol

class SymbolChunk:
    def __init__(
        self,
        file_path: str,
        symbol_name: str,
        kind: str,
        signature: str,
        parent_class: Optional[str],
        start_line: int,
        end_line: int,
        content: str,
        docstring: Optional[str] = None,
        importance_score: float = 1.0,
    ):
        self.file_path = file_path
        self.symbol_name = symbol_name
        self.kind = kind
        self.signature = signature
        self.parent_class = parent_class
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.docstring = docstring or ""
        self.importance_score = importance_score

    def get_embedding_text(self) -> str:
        """Returns structured representation optimized for vector retrieval"""
        parent_info = f"Parent Class: {self.parent_class}\n" if self.parent_class else ""
        doc_info = f"Docstring: {self.docstring}\n" if self.docstring else ""
        return (
            f"File: {self.file_path}\n"
            f"Symbol: {self.symbol_name} ({self.kind})\n"
            f"Signature: {self.signature}\n"
            f"{parent_info}"
            f"{doc_info}"
            f"\nCode:\n{self.content}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "symbol_name": self.symbol_name,
            "kind": self.kind,
            "signature": self.signature,
            "parent_class": self.parent_class,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "docstring": self.docstring,
            "importance_score": self.importance_score,
            "embedding_text": self.get_embedding_text()
        }

def chunk_file_by_symbols(parsed_file: ParsedFile, file_content: str, node_scores: Optional[Dict[str, float]] = None) -> List[SymbolChunk]:
    """
    Chunks a parsed file strictly by AST symbol boundaries (functions, classes, methods).
    Preserves signature, parent class, and exact file/line span.
    """
    chunks: List[SymbolChunk] = []
    node_scores = node_scores or {}

    for sym in parsed_file.symbols:
        node_id = f"sym:{parsed_file.rel_path}:{sym.name}"
        score = node_scores.get(node_id, 1.0)
        chunks.append(
            SymbolChunk(
                file_path=parsed_file.rel_path,
                symbol_name=sym.name,
                kind=sym.kind,
                signature=sym.signature,
                parent_class=sym.parent_name,
                start_line=sym.start_line,
                end_line=sym.end_line,
                content=sym.content,
                docstring=sym.docstring,
                importance_score=score
            )
        )

    # If the file had no symbols (e.g. config or top-level script), create a whole-file chunk
    if not chunks:
        lines = file_content.splitlines()
        chunks.append(
            SymbolChunk(
                file_path=parsed_file.rel_path,
                symbol_name=parsed_file.rel_path,
                kind="file",
                signature=parsed_file.rel_path,
                parent_class=None,
                start_line=1,
                end_line=len(lines),
                content=file_content[:4000],  # bounded head
                docstring=parsed_file.file_docstring,
                importance_score=node_scores.get(f"file:{parsed_file.rel_path}", 1.0)
            )
        )

    return chunks
