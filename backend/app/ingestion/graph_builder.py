import os
import networkx as nx
from typing import List, Dict, Tuple, Optional, Any, Set
from app.ingestion.parser import ParsedFile, ParsedSymbol, ParsedImport

class SymbolGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        # Symbol definitions mapping: symbol_name -> List[Tuple[rel_path, ParsedSymbol]]
        self.definitions_by_name: Dict[str, List[Tuple[str, ParsedSymbol]]] = {}
        # File imports mapping: rel_path -> List[ParsedImport]
        self.imports_by_file: Dict[str, List[ParsedImport]] = {}
        # Parsed files
        self.files_by_path: Dict[str, ParsedFile] = {}

    def add_file(self, parsed_file: ParsedFile):
        rel_path = parsed_file.rel_path
        self.files_by_path[rel_path] = parsed_file
        self.imports_by_file[rel_path] = parsed_file.imports

        file_node_id = f"file:{rel_path}"
        self.graph.add_node(file_node_id, type="file", label=os.path.basename(rel_path), path=rel_path)

        for sym in parsed_file.symbols:
            sym_node_id = f"sym:{rel_path}:{sym.name}"
            self.graph.add_node(
                sym_node_id,
                type="symbol",
                label=sym.name,
                kind=sym.kind,
                path=rel_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                signature=sym.signature
            )
            # Edge: file DEFINES symbol
            self.graph.add_edge(file_node_id, sym_node_id, edge_type="defines")

            # Register definition for call resolution
            if sym.name not in self.definitions_by_name:
                self.definitions_by_name[sym.name] = []
            self.definitions_by_name[sym.name].append((rel_path, sym))

            # Also index unqualified name if it's Class.method
            if "." in sym.name:
                short_name = sym.name.split(".")[-1]
                if short_name not in self.definitions_by_name:
                    self.definitions_by_name[short_name] = []
                self.definitions_by_name[short_name].append((rel_path, sym))

    def build_edges(self):
        """
        Resolves IMPORTS and CALLS across all files in the repository.
        """
        # 1. Resolve imports
        for rel_path, imports in self.imports_by_file.items():
            file_node_id = f"file:{rel_path}"
            for imp in imports:
                # Find matching target file if internal
                target_file = self._resolve_import_to_file(imp.module, rel_path)
                if target_file:
                    target_file_node_id = f"file:{target_file}"
                    if self.graph.has_node(target_file_node_id):
                        self.graph.add_edge(file_node_id, target_file_node_id, edge_type="imports")
                
                # Link imported symbols
                for sym_name in imp.imported_symbols:
                    if sym_name in self.definitions_by_name:
                        for def_path, _ in self.definitions_by_name[sym_name]:
                            target_sym_node = f"sym:{def_path}:{sym_name}"
                            if self.graph.has_node(target_sym_node):
                                self.graph.add_edge(file_node_id, target_sym_node, edge_type="imports_symbol")

        # 2. Resolve calls
        for rel_path, parsed_file in self.files_by_path.items():
            for sym in parsed_file.symbols:
                caller_node_id = f"sym:{rel_path}:{sym.name}"
                for called_name in sym.calls:
                    target = self._resolve_call(called_name, rel_path, sym)
                    if target:
                        target_path, target_sym = target
                        callee_node_id = f"sym:{target_path}:{target_sym.name}"
                        if self.graph.has_node(callee_node_id):
                            self.graph.add_edge(caller_node_id, callee_node_id, edge_type="calls")

    def _resolve_import_to_file(self, module_str: str, current_file: str) -> Optional[str]:
        """Heuristic resolver from module string (e.g. app.core.models or ./models) to file path"""
        norm = module_str.replace(".", "/").strip("/")
        candidates = [
            f"{norm}.py",
            f"{norm}.ts",
            f"{norm}.js",
            f"{norm}/index.ts",
            f"{norm}/index.js",
            f"{norm}/__init__.py"
        ]
        # Check against existing files in repo
        for c in candidates:
            if c in self.files_by_path:
                return c
            # Try relative to current file's directory
            curr_dir = os.path.dirname(current_file).replace("\\", "/")
            rel_candidate = f"{curr_dir}/{c}".replace("//", "/")
            if rel_candidate in self.files_by_path:
                return rel_candidate
        return None

    def _resolve_call(self, called_name: str, current_file: str, caller_sym: ParsedSymbol) -> Optional[Tuple[str, ParsedSymbol]]:
        """Resolves a call name to the most likely target definition"""
        matches = self.definitions_by_name.get(called_name)
        if not matches:
            return None
        # Preference 1: defined in the same file
        for path, sym in matches:
            if path == current_file and sym.name != caller_sym.name:
                return (path, sym)
        # Preference 2: defined in an imported module
        current_imports = self.imports_by_file.get(current_file, [])
        for imp in current_imports:
            if called_name in imp.imported_symbols:
                for path, sym in matches:
                    if sym.name == called_name:
                        return (path, sym)
        # Fallback: first match
        return matches[0]

    def compute_pagerank(self, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-5) -> Dict[str, float]:
        """
        Computes PageRank importance score across all nodes in the symbol graph.
        Uses pure-Python power iteration with dangling node redistribution,
        avoiding external scipy dependencies.
        Returns a mapping of node_id -> importance_score (normalized, baseline ~1.0).
        """
        nodes = list(self.graph.nodes)
        N = len(nodes)
        if N == 0:
            return {}
        if N == 1:
            return {nodes[0]: 1.0}

        # Initialize uniform distribution
        scores = {node: 1.0 / N for node in nodes}
        out_degrees = {node: self.graph.out_degree(node) for node in nodes}
        dangling_nodes = [node for node in nodes if out_degrees[node] == 0]

        for _ in range(max_iter):
            dangling_sum = sum(scores[node] for node in dangling_nodes)
            new_scores = {}
            for node in nodes:
                # Inbound contributions
                inbound_sum = sum(
                    scores[pred] / out_degrees[pred]
                    for pred in self.graph.predecessors(node)
                )
                new_scores[node] = (
                    (1.0 - damping) / N
                    + damping * (inbound_sum + dangling_sum / N)
                )

            # Check convergence (L1 norm)
            diff = sum(abs(new_scores[n] - scores[n]) for n in nodes)
            scores = new_scores
            if diff < tol:
                break

        # Normalize so baseline mean is ~1.0
        avg_score = sum(scores.values()) / max(len(scores), 1)
        normalized = {}
        for node, score in scores.items():
            norm_score = round(score / avg_score, 4)
            normalized[node] = max(norm_score, 0.1)

        return normalized

    def get_file_importance_scores(self, node_scores: Dict[str, float]) -> Dict[str, float]:
        """Aggregates PageRank scores for each file"""
        file_scores = {}
        for rel_path, parsed_file in self.files_by_path.items():
            file_node_id = f"file:{rel_path}"
            f_score = node_scores.get(file_node_id, 1.0)
            # Add up symbol scores inside file
            sym_scores = [node_scores.get(f"sym:{rel_path}:{s.name}", 1.0) for s in parsed_file.symbols]
            if sym_scores:
                avg_sym = sum(sym_scores) / len(sym_scores)
                f_score = 0.5 * f_score + 0.5 * avg_sym
            file_scores[rel_path] = round(f_score, 4)
        return file_scores

    def get_react_flow_graph(self, max_nodes: int = 150) -> Dict[str, Any]:
        """
        Generates nodes and edges ready for React Flow rendering in the frontend!
        Prioritizes high PageRank nodes for clean, non-laggy visualization.
        """
        node_scores = self.compute_pagerank()
        sorted_nodes = sorted(self.graph.nodes(data=True), key=lambda x: node_scores.get(x[0], 0.0), reverse=True)
        top_node_ids = set([n[0] for n in sorted_nodes[:max_nodes]])

        rf_nodes = []
        import math
        # Circular / grid layout positioning
        total = len(top_node_ids)
        radius = max(300, total * 8)
        angle_step = 2 * math.pi / max(total, 1)

        for i, (node_id, data) in enumerate(sorted_nodes[:max_nodes]):
            angle = i * angle_step
            x = 400 + radius * math.cos(angle)
            y = 400 + radius * math.sin(angle)
            score = node_scores.get(node_id, 1.0)

            rf_nodes.append({
                "id": node_id,
                "type": "customNode",
                "position": {"x": round(x, 1), "y": round(y, 1)},
                "data": {
                    "id": node_id,
                    "label": data.get("label", node_id),
                    "nodeType": data.get("type", "symbol"),
                    "kind": data.get("kind", ""),
                    "path": data.get("path", ""),
                    "startLine": data.get("start_line"),
                    "endLine": data.get("end_line"),
                    "signature": data.get("signature", ""),
                    "importance": score
                }
            })

        rf_edges = []
        edge_id = 0
        for u, v, data in self.graph.edges(data=True):
            if u in top_node_ids and v in top_node_ids:
                edge_id += 1
                rf_edges.append({
                    "id": f"e{edge_id}",
                    "source": u,
                    "target": v,
                    "label": data.get("edge_type", "calls"),
                    "animated": data.get("edge_type") == "calls",
                    "style": {
                        "stroke": "#3b82f6" if data.get("edge_type") == "calls" else "#10b981",
                        "strokeWidth": 1.5
                    }
                })

        return {"nodes": rf_nodes, "edges": rf_edges}
