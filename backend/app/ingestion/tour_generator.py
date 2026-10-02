"""
Tour Generation System for Phase 4: Guided Tours

Generates "read the code in this order" walkthroughs by:
1. Starting at entry points (main, app, index, CLI, route handlers)
2. Following the call graph downward
3. Grouping related files by module
4. Generating LLM-based explanations for each step
"""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.models import (
    Repository, FileRecord, SymbolRecord, SymbolEdgeRecord,
    TourRecord, TourStepRecord
)
from app.llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger("greppa.tour_generator")


class TourStep:
    """Represents a single step in a guided tour"""
    def __init__(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        symbol_name: str,
        signature: str,
        content: str,
        importance_score: float
    ):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.symbol_name = symbol_name
        self.signature = signature
        self.content = content
        self.importance_score = importance_score
        self.title: Optional[str] = None
        self.why_it_matters: Optional[str] = None
        self.body: Optional[str] = None


class TourGenerator:
    """Generates guided code tours for repositories"""
    
    def __init__(self, db: Session, repo_id: int, api_key: Optional[str] = None):
        self.db = db
        self.repo_id = repo_id
        self.llm = get_llm_provider(api_key=api_key)
        self.repo = db.query(Repository).filter(Repository.id == repo_id).first()
        
    def generate_big_picture_tour(
        self,
        max_steps: int = 12,
        title: Optional[str] = None
    ) -> Optional[TourRecord]:
        """
        Generates the default "Big Picture" tour that walks through
        the repository architecture from entry points to core abstractions.
        
        Algorithm:
        1. Find entry points (high importance + specific patterns)
        2. Follow call graph downward
        3. Group by module/folder
        4. Cap at max_steps (default: 12)
        5. Generate LLM explanations for each step
        6. Validate file paths and line numbers
        """
        if not self.repo:
            logger.error(f"Repository {self.repo_id} not found")
            return None
            
        logger.info(f"Generating Big Picture tour for repo '{self.repo.name}'")
        
        # Step 1: Identify entry points
        entry_points = self._find_entry_points()
        if not entry_points:
            logger.warning("No entry points found, using top files by importance")
            entry_points = self._get_top_files_by_importance(limit=3)
        
        logger.info(f"Found {len(entry_points)} entry points")
        
        # Step 2: Build candidate list by traversing call graph
        candidates = self._traverse_call_graph(entry_points, max_depth=3)
        
        # Step 3: Select and order steps (keep related files adjacent)
        selected_steps = self._select_tour_steps(candidates, max_steps)
        
        if not selected_steps:
            logger.error("No tour steps could be generated")
            return None
        
        logger.info(f"Selected {len(selected_steps)} steps for tour")
        
        # Step 4: Generate LLM explanations for each step
        for i, step in enumerate(selected_steps):
            logger.info(f"Generating explanation for step {i+1}/{len(selected_steps)}: {step.symbol_name}")
            self._generate_step_explanation(step, i + 1, len(selected_steps))
        
        # Step 5: Validate all steps
        valid_steps = [s for s in selected_steps if self._validate_step(s)]
        
        if not valid_steps:
            logger.error("No valid steps after validation")
            return None
        
        logger.info(f"Validated {len(valid_steps)} steps")
        
        # Step 6: Create tour record
        tour_title = title or f"Big Picture Tour: {self.repo.name}"
        tour_description = (
            f"An architectural walkthrough of {self.repo.name}, starting from entry points "
            f"and exploring the core abstractions and execution flow. "
            f"{len(valid_steps)} key stops."
        )
        
        tour = TourRecord(
            repo_id=self.repo_id,
            tour_type="big_picture",
            title=tour_title,
            description=tour_description
        )
        self.db.add(tour)
        self.db.flush()
        
        # Step 7: Add tour steps
        for order, step in enumerate(valid_steps, start=1):
            step_record = TourStepRecord(
                tour_id=tour.id,
                step_order=order,
                file_path=step.file_path,
                start_line=step.start_line,
                end_line=step.end_line,
                title=step.title or f"Step {order}: {step.symbol_name}",
                why_it_matters=step.why_it_matters or "Core component of the system.",
                body=step.body or step.signature
            )
            self.db.add(step_record)
        
        self.db.commit()
        logger.info(f"Tour '{tour_title}' created with ID {tour.id}")
        
        return tour
    
    def _find_entry_points(self) -> List[FileRecord]:
        """
        Identifies entry point files by looking for:
        - Files marked as entry points (is_entrypoint=True)
        - High-importance files with entry-point naming patterns
        - Main functions, CLI definitions, route handlers
        """
        # First try: explicitly marked entry points
        entry_files = self.db.query(FileRecord).filter(
            FileRecord.repo_id == self.repo_id,
            FileRecord.is_entrypoint == True
        ).order_by(desc(FileRecord.importance_score)).limit(5).all()
        
        if entry_files:
            return entry_files
        
        # Second try: pattern-based detection
        entry_patterns = ['main.py', 'app.py', 'index.', 'server.', 'cli.', '__main__']
        
        pattern_files = []
        for pattern in entry_patterns:
            files = self.db.query(FileRecord).filter(
                FileRecord.repo_id == self.repo_id,
                FileRecord.path.contains(pattern)
            ).order_by(desc(FileRecord.importance_score)).limit(2).all()
            pattern_files.extend(files)
        
        if pattern_files:
            # Remove duplicates and sort by importance
            unique_files = {f.id: f for f in pattern_files}
            return sorted(unique_files.values(), key=lambda x: x.importance_score or 0, reverse=True)[:5]
        
        # Fallback: top files by PageRank
        return self._get_top_files_by_importance(limit=3)
    
    def _get_top_files_by_importance(self, limit: int = 5) -> List[FileRecord]:
        """Gets the most important files by PageRank score"""
        return self.db.query(FileRecord).filter(
            FileRecord.repo_id == self.repo_id
        ).order_by(desc(FileRecord.importance_score)).limit(limit).all()
    
    def _traverse_call_graph(
        self,
        entry_files: List[FileRecord],
        max_depth: int = 3
    ) -> List[TourStep]:
        """
        Traverses the call graph from entry points, collecting important symbols
        in breadth-first order up to max_depth.
        """
        candidates: List[TourStep] = []
        visited_symbols: Set[str] = set()
        
        # Start with top symbols from entry files
        for entry_file in entry_files:
            symbols = self.db.query(SymbolRecord).filter(
                SymbolRecord.file_id == entry_file.id,
                SymbolRecord.kind.in_(['function', 'class', 'method'])
            ).order_by(desc(SymbolRecord.importance_score)).limit(3).all()
            
            for sym in symbols:
                if sym.name not in visited_symbols:
                    visited_symbols.add(sym.name)
                    candidates.append(self._symbol_to_tour_step(sym, entry_file))
        
        # BFS traversal of call graph
        depth = 0
        current_level = [c.symbol_name for c in candidates]
        
        while depth < max_depth and current_level:
            next_level: Set[str] = set()
            
            for symbol_name in current_level:
                # Find callees (what this symbol calls)
                edges = self.db.query(SymbolEdgeRecord).filter(
                    SymbolEdgeRecord.repo_id == self.repo_id,
                    SymbolEdgeRecord.source_symbol == symbol_name,
                    SymbolEdgeRecord.edge_type == "calls"
                ).limit(5).all()
                
                for edge in edges:
                    target_name = edge.target_symbol
                    if target_name not in visited_symbols:
                        # Find the symbol record
                        target_sym = self.db.query(SymbolRecord).filter(
                            SymbolRecord.repo_id == self.repo_id,
                            SymbolRecord.name == target_name
                        ).first()
                        
                        if target_sym:
                            visited_symbols.add(target_name)
                            next_level.add(target_name)
                            target_file = self.db.query(FileRecord).filter(
                                FileRecord.id == target_sym.file_id
                            ).first()
                            
                            if target_file:
                                candidates.append(self._symbol_to_tour_step(target_sym, target_file))
            
            current_level = list(next_level)
            depth += 1
        
        return candidates
    
    def _symbol_to_tour_step(self, symbol: SymbolRecord, file: FileRecord) -> TourStep:
        """Converts a SymbolRecord to a TourStep"""
        return TourStep(
            file_path=file.path,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            symbol_name=symbol.name,
            signature=symbol.signature or f"{symbol.kind} {symbol.name}",
            content=symbol.content,
            importance_score=symbol.importance_score or 1.0
        )
    
    def _select_tour_steps(
        self,
        candidates: List[TourStep],
        max_steps: int
    ) -> List[TourStep]:
        """
        Selects and orders tour steps from candidates:
        1. Prioritize high importance scores
        2. Keep related files (same module/folder) adjacent
        3. Cap at max_steps
        """
        # Sort by importance first
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.importance_score,
            reverse=True
        )
        
        # Group by folder/module
        by_folder: Dict[str, List[TourStep]] = {}
        for step in sorted_candidates:
            folder = "/".join(step.file_path.split("/")[:-1]) or "root"
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(step)
        
        # Select steps, alternating between folders to maintain diversity
        selected: List[TourStep] = []
        folder_lists = list(by_folder.values())
        folder_idx = 0
        
        while len(selected) < max_steps and any(folder_lists):
            if folder_idx >= len(folder_lists):
                folder_idx = 0
            
            if folder_lists[folder_idx]:
                selected.append(folder_lists[folder_idx].pop(0))
            
            # Remove empty lists
            folder_lists = [fl for fl in folder_lists if fl]
            folder_idx += 1
        
        return selected[:max_steps]
    
    def _generate_step_explanation(
        self,
        step: TourStep,
        step_number: int,
        total_steps: int
    ) -> None:
        """
        Generates LLM-based explanations for a tour step:
        - title: Concise step title (under 70 chars)
        - why_it_matters: 1-2 sentences on importance
        - body: 3-5 sentence explanation of what this code does
        """
        prompt = f"""You are generating a guided code tour for the repository "{self.repo.name}".

This is step {step_number} of {total_steps}.

File: {step.file_path}
Symbol: {step.symbol_name} (lines {step.start_line}-{step.end_line})
Signature: {step.signature}

Code:
```
{step.content[:800]}
```

Generate a tour step explanation with these components:

1. **title**: A concise, descriptive title (under 70 characters) that explains what this step covers
2. **why_it_matters**: 1-2 sentences explaining why this component is important to understand
3. **body**: 3-5 sentences explaining what this code does, how it works, and how it fits into the larger system

Format your response as JSON:
{{"title": "...", "why_it_matters": "...", "body": "..."}}

Be technical but clear. Focus on the architecture and execution flow."""

        try:
            response = self.llm.generate_answer(
                prompt=prompt,
                system_instruction="You are an expert software architect creating educational code tours."
            )
            
            # Try to parse JSON response
            import json
            import re
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                explanation = json.loads(json_match.group())
                step.title = explanation.get("title", f"Step {step_number}: {step.symbol_name}")[:255]
                step.why_it_matters = explanation.get("why_it_matters", "Core component of the system.")
                step.body = explanation.get("body", step.signature)
            else:
                # Fallback if JSON parsing fails
                step.title = f"Step {step_number}: {step.symbol_name}"
                step.why_it_matters = "Important component in the codebase architecture."
                step.body = response[:500] if response else step.signature
        
        except Exception as e:
            logger.warning(f"Failed to generate explanation for {step.symbol_name}: {e}")
            step.title = f"Step {step_number}: {step.symbol_name}"
            step.why_it_matters = "Core component worth understanding."
            step.body = step.signature
    
    def _validate_step(self, step: TourStep) -> bool:
        """
        Validates that a tour step has valid file path and line numbers.
        Returns True if valid, False otherwise.
        """
        # Check file exists
        file_record = self.db.query(FileRecord).filter(
            FileRecord.repo_id == self.repo_id,
            FileRecord.path == step.file_path
        ).first()
        
        if not file_record:
            logger.warning(f"Invalid step: file not found: {step.file_path}")
            return False
        
        # Check line numbers are reasonable
        if step.start_line < 1 or step.end_line < step.start_line:
            logger.warning(f"Invalid step: bad line numbers {step.start_line}-{step.end_line}")
            return False
        
        if step.end_line > file_record.line_count + 10:  # Allow some tolerance
            logger.warning(f"Invalid step: end_line {step.end_line} exceeds file length {file_record.line_count}")
            return False
        
        return True
    
    def generate_feature_trace_tour(
        self,
        query: str,
        title: Optional[str] = None,
        max_steps: int = 8
    ) -> Optional[TourRecord]:
        """
        Generates a custom feature trace tour based on a user question.
        Uses agent-based search to find relevant code and trace execution flow.
        
        Example: "How does authentication and token generation work?"
        """
        logger.info(f"Generating feature trace tour for query: '{query}'")
        
        # Use the agent to find relevant code
        from app.agent.loop import CodebaseAgent
        agent = CodebaseAgent(self.db, self.repo_id)
        result = agent.run(query)
        
        if not result.citations:
            logger.warning("No citations found for feature trace query")
            return None
        
        # Convert citations to tour steps
        steps: List[TourStep] = []
        for citation in result.citations[:max_steps]:
            # Find the symbol at this location
            file_record = self.db.query(FileRecord).filter(
                FileRecord.repo_id == self.repo_id,
                FileRecord.path == citation['file_path']
            ).first()
            
            if not file_record:
                continue
            
            # Find symbol that matches the line range
            symbol = self.db.query(SymbolRecord).filter(
                SymbolRecord.file_id == file_record.id,
                SymbolRecord.start_line <= citation['start_line'],
                SymbolRecord.end_line >= citation['end_line']
            ).first()
            
            if symbol:
                step = self._symbol_to_tour_step(symbol, file_record)
                steps.append(step)
        
        if not steps:
            logger.error("No valid steps from citations")
            return None
        
        # Generate explanations contextual to the feature being traced
        for i, step in enumerate(steps):
            self._generate_feature_step_explanation(step, query, i + 1, len(steps))
        
        # Create tour
        tour_title = title or f"Feature Trace: {query[:50]}"
        tour_description = f"A walkthrough tracing the feature: '{query}'. {len(steps)} key steps."
        
        tour = TourRecord(
            repo_id=self.repo_id,
            tour_type="feature_trace",
            title=tour_title,
            description=tour_description
        )
        self.db.add(tour)
        self.db.flush()
        
        for order, step in enumerate(steps, start=1):
            step_record = TourStepRecord(
                tour_id=tour.id,
                step_order=order,
                file_path=step.file_path,
                start_line=step.start_line,
                end_line=step.end_line,
                title=step.title or f"{step.symbol_name}",
                why_it_matters=step.why_it_matters or "Relevant to this feature.",
                body=step.body or step.signature
            )
            self.db.add(step_record)
        
        self.db.commit()
        logger.info(f"Feature trace tour created with ID {tour.id}")
        
        return tour
    
    def _generate_feature_step_explanation(
        self,
        step: TourStep,
        feature_query: str,
        step_number: int,
        total_steps: int
    ) -> None:
        """Generates explanations specific to a feature trace"""
        prompt = f"""You are tracing the feature: "{feature_query}" in repository "{self.repo.name}".

Step {step_number} of {total_steps}:
File: {step.file_path}
Symbol: {step.symbol_name}
Code: {step.content[:600]}

Explain this step's role in implementing "{feature_query}":

1. **title**: Brief title (under 70 chars) describing this step's role
2. **why_it_matters**: Why this component is important for the feature
3. **body**: How this code contributes to implementing the feature

Format as JSON: {{"title": "...", "why_it_matters": "...", "body": "..."}}"""

        try:
            response = self.llm.generate_answer(prompt=prompt)
            import json, re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                explanation = json.loads(json_match.group())
                step.title = explanation.get("title", step.symbol_name)[:255]
                step.why_it_matters = explanation.get("why_it_matters", "Part of the feature implementation.")
                step.body = explanation.get("body", step.signature)
            else:
                step.title = f"{step.symbol_name} (Feature Step)"
                step.why_it_matters = f"Implements part of: {feature_query}"
                step.body = response[:500] if response else step.signature
        except Exception as e:
            logger.warning(f"Failed to generate feature explanation: {e}")
            step.title = step.symbol_name
            step.why_it_matters = f"Related to: {feature_query}"
            step.body = step.signature
