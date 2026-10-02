import os
import json
import re
from typing import List, Dict, Any, Optional

def analyze_tech_stack_and_entrypoints(repo_dir: str, scanned_paths: List[str]) -> Dict[str, Any]:
    """
    Analyzes repository manifests, Dockerfiles, and entrypoints:
    - Detects languages and primary frameworks
    - Identifies main application entrypoints
    - Extracts setup & run instructions from README if present
    """
    stack = []
    entrypoints = []
    run_instructions = ""

    # 1. Inspect package.json (Node/TS)
    pkg_path = os.path.join(repo_dir, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "next" in deps:
                    stack.append("Next.js")
                if "react" in deps:
                    stack.append("React")
                if "express" in deps:
                    stack.append("Express")
                if "typescript" in deps:
                    stack.append("TypeScript")
                if "vue" in deps:
                    stack.append("Vue")

                if data.get("main"):
                    entrypoints.append(data.get("main"))
        except Exception:
            pass

    # 2. Inspect Python requirements / pyproject
    req_path = os.path.join(repo_dir, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "fastapi" in content:
                    stack.append("FastAPI")
                if "django" in content:
                    stack.append("Django")
                if "flask" in content:
                    stack.append("Flask")
                if "sqlalchemy" in content:
                    stack.append("SQLAlchemy")
                if "pydantic" in content:
                    stack.append("Pydantic")
                stack.append("Python")
        except Exception:
            pass

    # 3. Inspect Docker & CI
    if os.path.exists(os.path.join(repo_dir, "Dockerfile")):
        stack.append("Docker")
    if os.path.exists(os.path.join(repo_dir, "docker-compose.yml")):
        stack.append("Docker Compose")

    # 4. Entrypoint heuristics from scanned paths
    common_entrypoints = [
        "main.py", "app.py", "server.py", "cli.py", "run.py",
        "index.ts", "index.js", "server.ts", "server.js",
        "src/main.py", "src/app.py", "src/index.ts", "src/index.js",
        "app/main.py"
    ]
    for ep in common_entrypoints:
        norm_ep = ep.replace("\\", "/")
        if norm_ep in scanned_paths and norm_ep not in entrypoints:
            entrypoints.append(norm_ep)

    # 5. Extract How to run from README.md
    for r_name in ["README.md", "readme.md", "README"]:
        r_path = os.path.join(repo_dir, r_name)
        if os.path.exists(r_path):
            try:
                with open(r_path, "r", encoding="utf-8", errors="ignore") as f:
                    readme_text = f.read()
                    # Look for Quick Start or How to Run section
                    match = re.search(r'#+\s*(?:Quick\s*Start|Running|Getting\s*Started|Installation).*?(?=\n#+ |\Z)', readme_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        run_instructions = match.group(0)[:1000].strip()
                    else:
                        run_instructions = readme_text[:600].strip()
            except Exception:
                pass
            break

    # De-duplicate
    stack = list(dict.fromkeys(stack))
    entrypoints = list(dict.fromkeys(entrypoints))

    return {
        "stack": stack if stack else ["Python / Polyglot"],
        "entrypoints": entrypoints if entrypoints else ["main entrypoint"],
        "run_instructions": run_instructions or "Run using project default commands (e.g. python main.py or npm start)."
    }
