import re
from typing import List, Dict, Optional, Tuple, Any

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python
    PY_LANGUAGE = Language(tree_sitter_python.language())
    py_parser = Parser(PY_LANGUAGE)
except Exception:
    PY_LANGUAGE = None
    py_parser = None

class ParsedSymbol:
    def __init__(
        self,
        name: str,
        kind: str,
        start_line: int,
        end_line: int,
        content: str,
        parent_name: Optional[str] = None,
        signature: Optional[str] = None,
        docstring: Optional[str] = None,
        calls: Optional[List[str]] = None,
    ):
        self.name = name
        self.kind = kind  # class, function, method, interface
        self.parent_name = parent_name
        self.signature = signature or ""
        self.docstring = docstring or ""
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.calls = calls or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "parent_name": self.parent_name,
            "signature": self.signature,
            "docstring": self.docstring,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "calls": self.calls,
        }

class ParsedImport:
    def __init__(self, module: str, imported_symbols: List[str], raw_statement: str):
        self.module = module
        self.imported_symbols = imported_symbols
        self.raw_statement = raw_statement

class ParsedFile:
    def __init__(
        self,
        rel_path: str,
        symbols: List[ParsedSymbol],
        imports: List[ParsedImport],
        file_docstring: Optional[str] = None
    ):
        self.rel_path = rel_path
        self.symbols = symbols
        self.imports = imports
        self.file_docstring = file_docstring

def extract_python_docstring(body_node, source_bytes: bytes) -> Optional[str]:
    """Extracts python docstring from function/class body if present"""
    for child in body_node.children:
        if child.type == "expression_statement":
            for expr_child in child.children:
                if expr_child.type == "string":
                    doc = source_bytes[expr_child.start_byte:expr_child.end_byte].decode("utf-8", errors="replace")
                    # Strip quotes
                    return doc.strip("\"' \n\t")
        elif child.type not in ["comment", ""]:
            break
    return None

def extract_calls_from_node(node, source_bytes: bytes) -> List[str]:
    """Extracts function/method call names within an AST node"""
    calls = []
    stack = [node]
    while stack:
        curr = stack.pop()
        if curr.type == "call":
            # function child
            fn_node = curr.child_by_field_name("function")
            if fn_node:
                call_text = source_bytes[fn_node.start_byte:fn_node.end_byte].decode("utf-8", errors="replace").strip()
                # If obj.method(), take method name as well as full expression
                if "." in call_text:
                    parts = call_text.split(".")
                    calls.append(parts[-1])
                calls.append(call_text)
        for child in curr.children:
            stack.append(child)
    return list(dict.fromkeys(calls))

def parse_python_with_treesitter(code: str, rel_path: str) -> ParsedFile:
    source_bytes = code.encode("utf-8")
    tree = py_parser.parse(source_bytes)
    root = tree.root_node
    
    symbols: List[ParsedSymbol] = []
    imports: List[ParsedImport] = []
    file_docstring = extract_python_docstring(root, source_bytes)

    lines = code.splitlines(keepends=True)

    def get_lines_content(start_line: int, end_line: int) -> str:
        # lines is 0-indexed, start_line/end_line are 1-indexed
        return "".join(lines[start_line - 1 : end_line])

    for node in root.children:
        # Imports
        if node.type == "import_statement":
            raw = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
            # import foo, bar
            for child in node.children:
                if child.type == "dotted_name":
                    name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip()
                    imports.append(ParsedImport(module=name, imported_symbols=[name], raw_statement=raw))
        elif node.type == "import_from_statement":
            raw = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
            module_name = ""
            syms = []
            module_node = node.child_by_field_name("module_name")
            if module_node:
                module_name = source_bytes[module_node.start_byte:module_node.end_byte].decode("utf-8", errors="replace").strip()
            for child in node.children:
                if child.type == "dotted_name" and child != module_node:
                    syms.append(source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").strip())
            imports.append(ParsedImport(module=module_name, imported_symbols=syms, raw_statement=raw))

        # Top-level Functions
        elif node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            ret_node = node.child_by_field_name("return_type")
            body_node = node.child_by_field_name("body")
            
            fn_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "anonymous"
            params = source_bytes[params_node.start_byte:params_node.end_byte].decode("utf-8", errors="replace") if params_node else "()"
            ret = f" -> {source_bytes[ret_node.start_byte:ret_node.end_byte].decode('utf-8', errors='replace')}" if ret_node else ""
            signature = f"def {fn_name}{params}{ret}"

            start_l = node.start_point[0] + 1
            end_l = node.end_point[0] + 1
            content = get_lines_content(start_l, end_l)
            docstring = extract_python_docstring(body_node, source_bytes) if body_node else None
            calls = extract_calls_from_node(body_node if body_node else node, source_bytes)

            symbols.append(ParsedSymbol(
                name=fn_name,
                kind="function",
                start_line=start_l,
                end_line=end_l,
                content=content,
                signature=signature,
                docstring=docstring,
                calls=calls
            ))

        # Class Definitions
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            super_node = node.child_by_field_name("superclasses")
            body_node = node.child_by_field_name("body")

            class_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace") if name_node else "AnonymousClass"
            supers = source_bytes[super_node.start_byte:super_node.end_byte].decode("utf-8", errors="replace") if super_node else ""
            signature = f"class {class_name}{supers}"

            start_l = node.start_point[0] + 1
            end_l = node.end_point[0] + 1
            content = get_lines_content(start_l, end_l)
            docstring = extract_python_docstring(body_node, source_bytes) if body_node else None

            symbols.append(ParsedSymbol(
                name=class_name,
                kind="class",
                start_line=start_l,
                end_line=end_l,
                content=content,
                signature=signature,
                docstring=docstring,
                calls=[]
            ))

            # Parse methods inside the class
            if body_node:
                for member in body_node.children:
                    if member.type in ("function_definition", "async_function_definition"):
                        m_name_node = member.child_by_field_name("name")
                        m_params_node = member.child_by_field_name("parameters")
                        m_ret_node = member.child_by_field_name("return_type")
                        m_body = member.child_by_field_name("body")

                        m_name = source_bytes[m_name_node.start_byte:m_name_node.end_byte].decode("utf-8", errors="replace") if m_name_node else "method"
                        m_params = source_bytes[m_params_node.start_byte:m_params_node.end_byte].decode("utf-8", errors="replace") if m_params_node else "()"
                        m_ret = f" -> {source_bytes[m_ret_node.start_byte:m_ret_node.end_byte].decode('utf-8', errors='replace')}" if m_ret_node else ""
                        m_sig = f"def {class_name}.{m_name}{m_params}{m_ret}"

                        m_start = member.start_point[0] + 1
                        m_end = member.end_point[0] + 1
                        m_content = get_lines_content(m_start, m_end)
                        m_doc = extract_python_docstring(m_body, source_bytes) if m_body else None
                        m_calls = extract_calls_from_node(m_body if m_body else member, source_bytes)

                        symbols.append(ParsedSymbol(
                            name=f"{class_name}.{m_name}",
                            kind="method",
                            parent_name=class_name,
                            start_line=m_start,
                            end_line=m_end,
                            content=m_content,
                            signature=m_sig,
                            docstring=m_doc,
                            calls=m_calls
                        ))

    return ParsedFile(rel_path=rel_path, symbols=symbols, imports=imports, file_docstring=file_docstring)


def parse_generic_fallback(code: str, rel_path: str, lang: str) -> ParsedFile:
    """
    High-fidelity structural fallback parser using regex matching for
    JavaScript, TypeScript, Go, Rust, Java, C++, etc.
    Extracts functions, classes, interfaces, and imports.
    """
    symbols: List[ParsedSymbol] = []
    imports: List[ParsedImport] = []
    lines = code.splitlines(keepends=True)

    # Import pattern (ES6, Go, etc.)
    import_re = re.compile(r'^\s*(?:import\s+(?:\{([^}]+)\}|\*\s+as\s+(\w+)|(\w+))?\s*from\s*[\'"]([^\'"]+)[\'"]|import\s+[\'"]([^\'"]+)[\'"])', re.MULTILINE)
    for match in import_re.finditer(code):
        raw = match.group(0)
        named = match.group(1)
        mod = match.group(4) or match.group(5) or ""
        syms = [s.strip() for s in named.split(",")] if named else []
        imports.append(ParsedImport(module=mod, imported_symbols=syms, raw_statement=raw))

    # Function patterns: export function foo(args), const foo = (args) =>, function foo(args), func (r *Receiver) Foo(args)
    patterns = [
        # JS/TS class / interface
        ("class", re.compile(r'^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+[A-Za-z0-9_$.]+)?(?:\s+implements\s+[A-Za-z0-9_$,\s]+)?', re.MULTILINE)),
        ("interface", re.compile(r'^\s*(?:export\s+)?interface\s+([A-Za-z0-9_$]+)', re.MULTILINE)),
        # JS/TS function
        ("function", re.compile(r'^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)', re.MULTILINE)),
        # JS/TS arrow func: const foo = (args) =>
        ("function", re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?::\s*[^=]+)?\s*=>', re.MULTILINE)),
        # Go func: func (r *Receiver) Method(args) or func Func(args)
        ("function", re.compile(r'^\s*func\s+(?:\([^)]+\)\s+)?([A-Za-z0-9_]+)\s*\(([^)]*)\)', re.MULTILINE)),
    ]

    for kind, regex in patterns:
        for match in regex.finditer(code):
            name = match.group(1)
            sig = match.group(0).strip()
            # Approximate line span by counting preceding newlines
            start_pos = match.start()
            start_l = code.count("\n", 0, start_pos) + 1
            # Find closing brace if possible
            end_l = min(len(lines), start_l + 30)  # default bounding window
            content = "".join(lines[start_l - 1 : end_l])
            # Simple call finder: word followed by parenthesis
            calls = list(dict.fromkeys(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(', content)))

            symbols.append(ParsedSymbol(
                name=name,
                kind=kind,
                start_line=start_l,
                end_line=end_l,
                content=content,
                signature=sig,
                calls=calls
            ))

    return ParsedFile(rel_path=rel_path, symbols=symbols, imports=imports)


def parse_code_file(code: str, rel_path: str, language: str) -> ParsedFile:
    """
    Main entry point for parsing code into symbols, imports, and AST calls.
    Uses tree-sitter when available for Python, and fallback multi-lang AST for others.
    """
    if language == "python" and py_parser is not None:
        try:
            return parse_python_with_treesitter(code, rel_path)
        except Exception:
            return parse_generic_fallback(code, rel_path, language)
    return parse_generic_fallback(code, rel_path, language)
