import hashlib
from typing import List, Dict, Any, Optional
from app.ingestion.parser import ParsedFile, ParsedSymbol

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def compute_chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

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
        chunk_type: str = "symbol"
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
        self.chunk_type = chunk_type
        self.token_count = estimate_tokens(content)
        self.content_hash = compute_chunk_hash(self.get_embedding_text())

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
            "token_count": self.token_count,
            "content_hash": self.content_hash,
            "docstring": self.docstring,
            "importance_score": self.importance_score,
            "chunk_type": self.chunk_type,
            "embedding_text": self.get_embedding_text()
        }

def split_large_symbol(sym: ParsedSymbol, file_path: str, max_tokens: int = 800) -> List[SymbolChunk]:
    """
    Splits symbols exceeding ~800 tokens at logical boundaries (blank lines or blocks)
    while preserving signature and context header on all slices.
    """
    lines = sym.content.splitlines(keepends=True)
    chunks: List[SymbolChunk] = []
    curr_lines: List[str] = []
    curr_tokens = 0
    slice_start = sym.start_line
    part = 1

    for idx, line in enumerate(lines):
        line_tok = estimate_tokens(line)
        # If we hit max_tokens and find a logical boundary (empty line or indentation change)
        if curr_tokens + line_tok > max_tokens and (line.strip() == "" or idx == len(lines) - 1):
            slice_content = "".join(curr_lines)
            slice_end = slice_start + len(curr_lines) - 1
            chunks.append(
                SymbolChunk(
                    file_path=file_path,
                    symbol_name=f"{sym.name} (Part {part})",
                    kind=sym.kind,
                    signature=sym.signature,
                    parent_class=sym.parent_name,
                    start_line=slice_start,
                    end_line=slice_end,
                    content=slice_content,
                    docstring=sym.docstring if part == 1 else "",
                    chunk_type="symbol_part"
                )
            )
            part += 1
            slice_start = slice_end + 1
            curr_lines = [line]
            curr_tokens = line_tok
        else:
            curr_lines.append(line)
            curr_tokens += line_tok

    if curr_lines:
        slice_content = "".join(curr_lines)
        chunks.append(
            SymbolChunk(
                file_path=file_path,
                symbol_name=f"{sym.name} (Part {part})" if part > 1 else sym.name,
                kind=sym.kind,
                signature=sym.signature,
                parent_class=sym.parent_name,
                start_line=slice_start,
                end_line=slice_start + len(curr_lines) - 1,
                content=slice_content,
                docstring=sym.docstring if part == 1 else "",
                chunk_type="symbol" if part == 1 else "symbol_part"
            )
        )

    return chunks

def chunk_file_by_symbols(
    parsed_file: ParsedFile,
    file_content: str,
    node_scores: Optional[Dict[str, float]] = None
) -> List[SymbolChunk]:
    """
    Chunks a parsed file adhering to Phase 2 rules:
    - One chunk per symbol
    - Prefix with context (file path, signature, parent class)
    - Split symbols over ~800 tokens at logical boundaries
    - Merge tiny symbols (getters, 1-liners) in the same file into a merged chunk
    - Include a file-header chunk with imports and top-level docstrings
    """
    chunks: List[SymbolChunk] = []
    node_scores = node_scores or {}

    # 1. File-header chunk (imports & top-level comments)
    header_lines = []
    for imp in parsed_file.imports[:15]:
        header_lines.append(imp.raw_statement)
    if parsed_file.file_docstring:
        header_lines.insert(0, f'"""{parsed_file.file_docstring}"""')

    if header_lines:
        header_content = "\n".join(header_lines)
        chunks.append(
            SymbolChunk(
                file_path=parsed_file.rel_path,
                symbol_name=f"{parsed_file.rel_path}::header",
                kind="file_header",
                signature=f"File Header: {parsed_file.rel_path}",
                parent_class=None,
                start_line=1,
                end_line=max(1, len(header_lines)),
                content=header_content,
                docstring=parsed_file.file_docstring,
                importance_score=node_scores.get(f"file:{parsed_file.rel_path}", 1.0),
                chunk_type="file_header"
            )
        )

    # 2. Separate tiny symbols vs standard symbols
    tiny_symbols: List[ParsedSymbol] = []
    for sym in parsed_file.symbols:
        node_id = f"sym:{parsed_file.rel_path}:{sym.name}"
        score = node_scores.get(node_id, 1.0)
        tok_count = estimate_tokens(sym.content)

        # Split large symbol over ~800 tokens
        if tok_count > 800:
            sub_chunks = split_large_symbol(sym, parsed_file.rel_path, max_tokens=800)
            for sc in sub_chunks:
                sc.importance_score = score
            chunks.extend(sub_chunks)
        elif (sym.end_line - sym.start_line) <= 3 and tok_count < 35:
            # Tiny symbol (getter, 1-liner constant/property)
            tiny_symbols.append(sym)
        else:
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
                    importance_score=score,
                    chunk_type="symbol"
                )
            )

    # 3. Merge tiny symbols into grouped chunks
    if tiny_symbols:
        merged_content = "\n\n".join([f"# {s.kind} {s.name}\n{s.content}" for s in tiny_symbols])
        min_start = min(s.start_line for s in tiny_symbols)
        max_end = max(s.end_line for s in tiny_symbols)
        names = ", ".join([s.name for s in tiny_symbols])
        chunks.append(
            SymbolChunk(
                file_path=parsed_file.rel_path,
                symbol_name=f"Merged Properties ({names[:50]}...)",
                kind="merged_properties",
                signature=f"Merged tiny definitions in {parsed_file.rel_path}",
                parent_class=None,
                start_line=min_start,
                end_line=max_end,
                content=merged_content,
                docstring=None,
                importance_score=1.0,
                chunk_type="tiny_symbols"
            )
        )

    # Fallback for plain files (configs, sql, markdown)
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
                content=file_content[:4000],
                docstring=parsed_file.file_docstring,
                importance_score=node_scores.get(f"file:{parsed_file.rel_path}", 1.0),
                chunk_type="file"
            )
        )

    return chunks
