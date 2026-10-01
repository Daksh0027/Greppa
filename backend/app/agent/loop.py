import os
import json
import logging
from typing import List, Dict, Any, Optional, Generator
from sqlalchemy.orm import Session
from app.core.models import Repository, FileRecord, SymbolRecord, SymbolEdgeRecord
from app.search.hybrid import HybridSearchEngine
from app.search.expander import GraphExpander
from app.search.packer import ContextPacker
from app.llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger("greppa.agent")

class AgentStep:
    def __init__(self, step_number: int, thought: str, action: str, action_input: Dict[str, Any], observation: str):
        self.step_number = step_number
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation
        }

class AgentResult:
    def __init__(self, answer: str, citations: List[Dict[str, Any]], steps: List[AgentStep]):
        self.answer = answer
        self.citations = citations
        self.steps = steps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": self.citations,
            "steps": [s.to_dict() for s in self.steps]
        }

class CodebaseAgent:
    def __init__(self, db: Session, repo_id: int, api_key: Optional[str] = None, max_steps: int = 6):
        self.db = db
        self.repo_id = repo_id
        self.llm = get_llm_provider(api_key=api_key)
        self.search_engine = HybridSearchEngine(db, repo_id, api_key=api_key)
        self.expander = GraphExpander(db, repo_id)
        self.max_steps = max_steps
        self.repo = db.query(Repository).filter(Repository.id == repo_id).first()

    def run(self, query: str) -> AgentResult:
        """
        Runs the multi-step agent reasoning loop to answer complex architectural queries.
        Searches, reads, follows call edges, and synthesizes answers with citations.
        """
        steps: List[AgentStep] = []
        collected_citations: Dict[str, Dict[str, Any]] = {}
        visited_symbols = set()

        # Step 1: Initial Hybrid Retrieval
        hits = self.search_engine.search(query, top_k=8)
        expanded = self.expander.expand_hits(hits, max_expanded=4)
        packed = ContextPacker(token_budget=6000).pack(expanded)

        for c in packed.citations:
            collected_citations[f"{c['file_path']}:{c['start_line']}"] = c

        top_symbols_summary = [f"- {h.symbol_name} in `{h.file_path}` (Lines {h.start_line}-{h.end_line})" for h in hits[:5]]
        step1 = AgentStep(
            step_number=1,
            thought=f"Initial search for symbols and concepts related to '{query}'. Found {len(hits)} relevant candidates.",
            action="hybrid_search",
            action_input={"query": query},
            observation=f"Top candidate symbols:\n" + "\n".join(top_symbols_summary)
        )
        steps.append(step1)

        # Step 2: Follow Call Graph for top hits
        if hits:
            top_hit = hits[0]
            visited_symbols.add(top_hit.symbol_name)
            callers = self.db.query(SymbolEdgeRecord).filter(
                SymbolEdgeRecord.repo_id == self.repo_id,
                SymbolEdgeRecord.target_symbol == top_hit.symbol_name,
                SymbolEdgeRecord.edge_type == "calls"
            ).all()

            callees = self.db.query(SymbolEdgeRecord).filter(
                SymbolEdgeRecord.repo_id == self.repo_id,
                SymbolEdgeRecord.source_symbol == top_hit.symbol_name,
                SymbolEdgeRecord.edge_type == "calls"
            ).all()

            caller_names = [f"`{c.source_symbol}` in {c.source_file}" for c in callers]
            callee_names = [f"`{c.target_symbol}`" for c in callees]

            obs = (
                f"Inspecting call hierarchy for `{top_hit.symbol_name}`:\n"
                f"- Callers: {', '.join(caller_names) if caller_names else 'None (Top-level or entrypoint)'}\n"
                f"- Callees: {', '.join(callee_names) if callee_names else 'None (Leaf function)'}"
            )

            step2 = AgentStep(
                step_number=2,
                thought=f"Expanding call graph around primary symbol `{top_hit.symbol_name}` to uncover execution flow.",
                action="follow_call_hierarchy",
                action_input={"symbol_name": top_hit.symbol_name},
                observation=obs
            )
            steps.append(step2)

        # Step 3: Deep inspection of second hit or callee if available
        if len(hits) > 1 and len(steps) < self.max_steps:
            second_hit = hits[1]
            visited_symbols.add(second_hit.symbol_name)
            step3 = AgentStep(
                step_number=3,
                thought=f"Examining secondary critical component `{second_hit.symbol_name}` in `{second_hit.file_path}`.",
                action="read_symbol",
                action_input={"symbol_name": second_hit.symbol_name, "file_path": second_hit.file_path},
                observation=f"Signature: {second_hit.header}\nPurpose: {second_hit.summary or 'Core module logic'}"
            )
            steps.append(step3)

        # Step 4: Final Synthesis with Citations
        synthesis_prompt = (
            f"You are an expert software architect analyzing the repository '{self.repo.name if self.repo else 'Project'}'.\n"
            f"User Question: \"{query}\"\n\n"
            f"Retrieved Code and Call Hierarchy:\n"
            f"{packed.context_str}\n\n"
            "Instructions:\n"
            "1. Answer the question thoroughly, explaining the end-to-end execution flow.\n"
            "2. Cite every key function, class, and method with its exact file and line numbers (e.g. `[path:start-end]`).\n"
            "3. Mention who calls whom based on the provided call graph.\n"
            "4. Be direct, technical, and precise."
        )

        final_answer = self.llm.generate_answer(
            prompt=synthesis_prompt,
            system_instruction="You are Greppa, an advanced large-repo code intelligence engine. Always provide file and line citations."
        )

        final_citations = list(collected_citations.values())

        return AgentResult(
            answer=final_answer,
            citations=final_citations,
            steps=steps
        )
