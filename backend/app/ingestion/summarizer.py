import os
from typing import List, Dict, Optional, Tuple, Any
from app.ingestion.parser import ParsedFile, ParsedSymbol
from app.llm.provider import LLMProvider

class HierarchicalSummarizer:
    def __init__(self, llm: LLMProvider):
        self.llm = llm
        # Cache: hash -> summary_text
        self.summary_cache: Dict[str, str] = {}

    def summarize_function(self, symbol: ParsedSymbol, rel_path: str) -> str:
        """Level 1: Summarizes a function or method"""
        cache_key = f"func:{rel_path}:{symbol.name}:{len(symbol.content)}"
        if cache_key in self.summary_cache:
            return self.summary_cache[cache_key]

        if symbol.docstring and len(symbol.docstring) > 10:
            summary = f"{symbol.kind.title()} `{symbol.name}` ({symbol.signature}): {symbol.docstring.strip()}"
        else:
            prompt = (
                f"Explain concisely (1-2 sentences) what this {symbol.kind} does, its inputs, and return value.\n"
                f"File: {rel_path}\n"
                f"Signature: {symbol.signature}\n\n"
                f"Code:\n{symbol.content[:2000]}"
            )
            summary = self.llm.generate_summary(prompt)

        self.summary_cache[cache_key] = summary
        return summary

    def summarize_file(
        self,
        parsed_file: ParsedFile,
        content_hash: str,
        cached_summary: Optional[str] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Level 2: Summarizes a file bottom-up from its child symbol summaries.
        Returns (file_summary, {symbol_name: symbol_summary}).
        """
        if cached_summary:
            return cached_summary, {}

        symbol_summaries: Dict[str, str] = {}
        sym_texts = []
        for sym in parsed_file.symbols:
            sym_sum = self.summarize_function(sym, parsed_file.rel_path)
            symbol_summaries[sym.name] = sym_sum
            sym_texts.append(f"- {sym.name} ({sym.kind}): {sym_sum}")

        file_doc = f"File Header: {parsed_file.file_docstring}\n" if parsed_file.file_docstring else ""
        sym_bullets = "\n".join(sym_texts[:20]) if sym_texts else "No discrete exported functions."
        
        prompt = (
            f"Generate a concise 2-3 sentence overview for file `{parsed_file.rel_path}` based on its symbols:\n"
            f"{file_doc}"
            f"Symbols:\n{sym_bullets}"
        )
        file_summary = self.llm.generate_summary(prompt)
        self.summary_cache[content_hash] = file_summary
        return file_summary, symbol_summaries

    def summarize_folders(self, file_summaries: Dict[str, str]) -> Dict[str, str]:
        """
        Level 3: Summarizes folders bottom-up from the file summaries inside them.
        """
        folder_files: Dict[str, List[Tuple[str, str]]] = {}
        for path, summary in file_summaries.items():
            folder = os.path.dirname(path).replace("\\", "/") or "root"
            if folder not in folder_files:
                folder_files[folder] = []
            folder_files[folder].append((os.path.basename(path), summary))

        folder_summaries: Dict[str, str] = {}
        for folder, items in folder_files.items():
            items_str = "\n".join([f"- {name}: {s}" for name, s in items[:15]])
            prompt = (
                f"Generate a concise architecture summary (2 sentences) for directory `{folder}` based on its files:\n"
                f"{items_str}"
            )
            folder_summaries[folder] = self.llm.generate_summary(prompt)

        return folder_summaries

    def summarize_repository(self, folder_summaries: Dict[str, str], repo_name: str) -> str:
        """
        Level 4: Synthesizes high-level repository overview and tour from folder summaries.
        """
        folders_str = "\n".join([f"- Directory `{d}`: {s}" for d, s in folder_summaries.items()])
        prompt = (
            f"Generate a high-level architectural overview for repository `{repo_name}` based on its module directories:\n"
            f"{folders_str}\n\n"
            "Include: Core purpose, architectural layers, and main entrypoints."
        )
        return self.llm.generate_summary(prompt)
