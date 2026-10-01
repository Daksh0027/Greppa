import os
import hashlib
import pathspec
from typing import List, Dict, Optional, Tuple, Set

# File extensions to language mapping
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".css": "css",
}

DEFAULT_IGNORE_PATTERNS = [
    # VCS
    ".git",
    ".svn",
    ".hg",
    # Dependencies
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    # Build outputs
    "dist",
    "build",
    "out",
    ".next",
    "target",
    "bin",
    "obj",
    "coverage",
    ".turbo",
    # Lockfiles & huge generated files
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "go.sum",
    "composer.lock",
    # Minified files
    "*.min.js",
    "*.min.css",
    "*.map",
    # Binaries & Media
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.svg",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.7z",
    "*.mp4",
    "*.mp3",
    "*.wasm",
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
]

MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1MB max file size

class ScannedFile:
    def __init__(self, rel_path: str, abs_path: str, language: str, content_hash: str, line_count: int, size_bytes: int):
        self.rel_path = rel_path.replace("\\", "/")
        self.abs_path = abs_path
        self.language = language
        self.content_hash = content_hash
        self.line_count = line_count
        self.size_bytes = size_bytes

    def read_text(self) -> str:
        with open(self.abs_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

def compute_file_hash(abs_path: str) -> str:
    hasher = hashlib.sha256()
    with open(abs_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_gitignore_spec(repo_root: str) -> pathspec.PathSpec:
    gitignore_path = os.path.join(repo_root, ".gitignore")
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass
    return pathspec.PathSpec.from_lines("gitignore", patterns)

def scan_repository(repo_root: str) -> List[ScannedFile]:
    """
    Scans a repository root, filtering files according to gitignore and ignore lists.
    Computes SHA-256 hashes and line counts for all retained code files.
    """
    spec = load_gitignore_spec(repo_root)
    scanned_files: List[ScannedFile] = []

    for root, dirs, files in os.walk(repo_root):
        rel_dir = os.path.relpath(root, repo_root).replace("\\", "/")
        
        # Filter directories in-place to prevent traversing node_modules, .git, etc.
        dirs[:] = [
            d for d in dirs 
            if not spec.match_file(os.path.join(rel_dir, d).lstrip("./"))
            and d not in [".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "target"]
        ]

        for file in files:
            rel_path = os.path.normpath(os.path.join(rel_dir, file)).replace("\\", "/")
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]
            
            # Check gitignore
            if spec.match_file(rel_path):
                continue

            abs_path = os.path.join(root, file)
            
            # Check file size
            try:
                size_bytes = os.path.getsize(abs_path)
                if size_bytes > MAX_FILE_SIZE_BYTES or size_bytes == 0:
                    continue
            except OSError:
                continue

            _, ext = os.path.splitext(file.lower())
            lang = EXT_TO_LANG.get(ext)
            if not lang:
                continue

            try:
                content_hash = compute_file_hash(abs_path)
                # Count lines
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    line_count = sum(1 for _ in f)
                
                scanned_files.append(
                    ScannedFile(
                        rel_path=rel_path,
                        abs_path=abs_path,
                        language=lang,
                        content_hash=content_hash,
                        line_count=line_count,
                        size_bytes=size_bytes
                    )
                )
            except Exception:
                continue

    return scanned_files
