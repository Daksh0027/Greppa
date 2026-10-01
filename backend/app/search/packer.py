from typing import List, Dict, Any, Tuple
from app.search.expander import GraphContext

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

class PackedContext:
    def __init__(self, context_str: str, citations: List[Dict[str, Any]], token_count: int):
        self.context_str = context_str
        self.citations = citations
        self.token_count = token_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_str": self.context_str,
            "citations": self.citations,
            "token_count": self.token_count
        }

class ContextPacker:
    def __init__(self, token_budget: int = 8000):
        self.token_budget = token_budget

    def pack(self, contexts: List[GraphContext]) -> PackedContext:
        """
        Packs retrieved and expanded symbols into a coherent, citation-rich prompt
        strictly respecting the token budget.
        """
        sections: List[str] = []
        citations: List[Dict[str, Any]] = []
        current_tokens = 0
        seen_chunks = set()

        for ctx in contexts:
            hit = ctx.hit
            chunk_key = f"{hit.file_path}:{hit.start_line}:{hit.end_line}"
            if chunk_key in seen_chunks:
                continue
            seen_chunks.add(chunk_key)

            # 1. Main Symbol Hit
            citation_tag = f"File: {hit.file_path} (Lines {hit.start_line}-{hit.end_line})"
            hit_header = f"### [{citation_tag}] Symbol: {hit.symbol_name} ({hit.header})\n"
            hit_body = f"```\n{hit.content}\n```\n"

            # 2. Graph Expansion Context (Callers & Callees)
            graph_meta = []
            if ctx.parent_class:
                graph_meta.append(f"  * Parent Class: `{ctx.parent_class['name']}` ({ctx.parent_class['signature']})")
            if ctx.callers:
                caller_strs = [f"`{c['symbol_name']}` in {c['file_path']}" for c in ctx.callers]
                graph_meta.append(f"  * Called by: {', '.join(caller_strs)}")
            if ctx.callees:
                callee_strs = [f"`{c['symbol_name']}`" for c in ctx.callees]
                graph_meta.append(f"  * Calls: {', '.join(callee_strs)}")

            graph_section = "\n".join(graph_meta) + "\n" if graph_meta else ""
            block = hit_header + graph_section + hit_body
            block_tokens = estimate_tokens(block)

            if current_tokens + block_tokens > self.token_budget:
                # If budget nearly exceeded, stop packing more chunks
                break

            sections.append(block)
            current_tokens += block_tokens
            citations.append({
                "file_path": hit.file_path,
                "symbol_name": hit.symbol_name,
                "start_line": hit.start_line,
                "end_line": hit.end_line,
                "importance": hit.importance_score
            })

        full_context = "\n".join(sections)
        return PackedContext(context_str=full_context, citations=citations, token_count=current_tokens)
