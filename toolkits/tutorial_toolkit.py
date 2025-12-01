"""Tools for tutorial generation leveraging the knowledge base and codebase."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from loguru import logger
from smolagents import Tool, tool

from toolkits.rag_store import SimpleChromaRAGStore
from utils.path_utils import ensure_directory, resolve_within_root

_MAX_SEARCH_FILE_SIZE_BYTES = 100_000  # Reduced to 100KB for speed
_MAX_READ_LINES = 500  # Limit file reads to protect context
_DEFAULT_RAG_MAX_SNIPPETS = 5
_SNIPPET_PADDING_CHARS = 240
_TREE_MAX_DEPTH = 3
_TREE_MAX_ITEMS = 200

# Explicit ignore set for tree/search
_IGNORED_DIRS = {
    "__pycache__", "node_modules", "venv", ".git", ".idea", ".vscode", "dist", "build"
}

_CODE_SEARCH_SKIP_SUFFIXES = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".class", 
    ".zip", ".tar", ".gz", ".png", ".jpg", ".pdf", ".lock"
}

_CODE_SEARCH_ALLOWED_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt", ".sh", "Dockerfile", "Makefile"
}

def _read_text_file_truncated(path: Path) -> str:
    """Reads file content with line limits."""
    try:
        lines = []
        with path.open("r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= _MAX_READ_LINES:
                    lines.append(f"\n... [Truncated after {_MAX_READ_LINES} lines] ...")
                    break
                lines.append(line)
        return "".join(lines)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File '{path.name}' is binary or not UTF-8 decodable."
        ) from exc

def _write_text_file(path: Path, content: str, append: bool = False) -> None:
    ensure_directory(path.parent)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        handle.write(content)

def build_tutorial_tools(
    *,
    codebase_root: str,
    knowledge_base_root: str,
    tutorial_output_root: str,
    enable_code_search: bool = False,
    enable_rag: bool = False,
    rag_max_snippets: int = _DEFAULT_RAG_MAX_SNIPPETS,
    rag_force_rebuild: bool = False, # Added explicit control
) -> List[Tool]:
    codebase_path = Path(codebase_root).expanduser().resolve()
    kb_path = Path(knowledge_base_root).expanduser().resolve()
    output_path = ensure_directory(tutorial_output_root)

    rag_store: Optional[SimpleChromaRAGStore] = None
    if enable_rag:
        rag_storage_root = ensure_directory(
            (output_path.parent if output_path.parent != output_path else output_path)
            / "rag_vector_store"
        )
        try:
            rag_store = SimpleChromaRAGStore(
                codebase_root=codebase_path,
                knowledge_base_root=kb_path,
                persist_directory=rag_storage_root,
            )
            # CRITICAL FIX: Do not force rebuild by default. 
            # This prevents 5-10 minute delays on agent startup.
            rag_store.ensure_index(
                include_codebase=True,
                include_knowledge_base=True,
                force_rebuild=rag_force_rebuild,
            )
        except Exception as exc: 
            logger.warning("Failed to initialize RAG vector store: {}", exc)
            rag_store = None

    max_snippets = max(1, rag_max_snippets)

    def _is_safe_entry(entry: Path) -> bool:
        return not entry.name.startswith(".") and entry.name not in _IGNORED_DIRS

    @tool
    def list_knowledge_base(dir_path: str = ".") -> List[str]:
        """List markdown files in the knowledge base.
        
        Args:
            dir_path: Relative directory path within the knowledge base to inspect.
        """
        resolved = resolve_within_root(kb_path, dir_path)
        if not resolved.is_dir():
            return []
        return sorted(entry.name for entry in resolved.iterdir() if _is_safe_entry(entry))

    @tool
    def read_knowledge_base_file(file_path: str) -> str:
        """Read a markdown file from the knowledge base.
        
        Args:
            file_path: Relative path to the markdown file inside the knowledge base directory.
        """
        resolved = resolve_within_root(kb_path, file_path)
        return _read_text_file_truncated(resolved)

    @tool
    def read_codebase_file(file_path: str) -> str:
        """Read a source file from the codebase (Truncated at 500 lines).
        
        Args:
            file_path: Relative path of the source file to read from the codebase root.
        """
        resolved = resolve_within_root(codebase_path, file_path)
        
        if any(p in _IGNORED_DIRS for p in resolved.parts):
             raise ValueError(f"Access to directories like {resolved.parent.name} is restricted.")

        if not resolved.is_file():
            raise FileNotFoundError(f"File '{file_path}' not found.")
            
        if resolved.suffix.lower() in _CODE_SEARCH_SKIP_SUFFIXES:
            raise ValueError(f"Binary file '{file_path}' is not supported.")
            
        return _read_text_file_truncated(resolved)

    @tool
    def list_codebase_directory(dir_path: str = ".") -> List[str]:
        """List entries in the codebase.
        
        Args:
            dir_path: Relative directory path whose contents should be listed.
        """
        resolved = resolve_within_root(codebase_path, dir_path)
        if not resolved.is_dir():
            return []
        return sorted(entry.name for entry in resolved.iterdir() if _is_safe_entry(entry))

    @tool
    def write_tutorial_file(file_path: str, content: str, append: bool = False) -> str:
        """Write tutorial content to the tutorials output directory.
        
        Args:
            file_path: Relative path for the tutorial markdown file to create.
            content: Markdown content to write into the file.
            append: When True, append instead of overwriting.
        """
        resolved = resolve_within_root(output_path, file_path)
        _write_text_file(resolved, content, append=append)
        return str(resolved)

    @tool
    def get_codebase_tree(max_depth: int = _TREE_MAX_DEPTH) -> str:
        """Return a tree view of the accessible codebase (Max depth 3).
        
        Args:
            max_depth: Depth to traverse. Default is 3.
        """
        lines: List[str] = ["."]
        
        def _build_tree(directory: Path, prefix: str, depth: int):
            if depth > max_depth or len(lines) > _TREE_MAX_ITEMS:
                return

            entries = sorted(child for child in directory.iterdir() if _is_safe_entry(child))
            
            for index, entry in enumerate(entries):
                connector = "└── " if index == len(entries) - 1 else "├── "
                child_prefix = "    " if index == len(entries) - 1 else "│   "
                
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    if depth < max_depth:
                        _build_tree(entry, prefix + child_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")

        _build_tree(codebase_path, "", 1)
        if len(lines) > _TREE_MAX_ITEMS:
            lines.append("... (Tree truncated) ...")
            
        return "```markdown\n" + "\n".join(lines) + "\n```"

    tools: List[Tool] = [
        list_knowledge_base,
        read_knowledge_base_file,
        read_codebase_file,
        list_codebase_directory,
        write_tutorial_file,
        get_codebase_tree,
    ]

    if enable_code_search:
        @tool
        def grep_codebase(
            pattern: str,
            dir_path: str = ".",
            ignore_case: bool = True,
            max_matches: int = 20,
        ) -> List[str]:
            """Search codebase files using regex. Skips binaries and large files.
            
            Args:
                pattern: Regular expression to search for within files.
                dir_path: Relative directory or file path to scope the search (defaults to the repo root).
                ignore_case: Perform case-insensitive matching when True.
                max_matches: Maximum number of line hits to return.
            """
            if not pattern:
                return []
            try:
                resolved = resolve_within_root(codebase_path, dir_path)
            except ValueError:
                return []

            flags = re.IGNORECASE if ignore_case else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as exc:
                return [f"Invalid regular expression: {exc}"]

            matches: List[str] = []

            # Generator for safe files
            def _iterate_files(root_path: Path):
                if root_path.is_file():
                    yield root_path
                    return
                for p in root_path.rglob("*"):
                    # Basic exclusion checks
                    if not p.is_file(): continue
                    if any(part in _IGNORED_DIRS for part in p.parts): continue
                    if p.name.startswith("."): continue
                    yield p

            for file_path in _iterate_files(resolved):
                if len(matches) >= max_matches:
                    break

                # Size and extension checks
                if file_path.suffix.lower() in _CODE_SEARCH_SKIP_SUFFIXES: continue
                # Relaxed extension check to allow Makefiles, etc.
                is_text = (file_path.suffix.lower() in _CODE_SEARCH_ALLOWED_SUFFIXES 
                           or file_path.suffix == "") 
                if not is_text: continue
                
                try:
                    if file_path.stat().st_size > _MAX_SEARCH_FILE_SIZE_BYTES: continue
                    content = file_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue

                for line_num, line in enumerate(content.splitlines(), start=1):
                    if regex.search(line):
                        relative = file_path.relative_to(codebase_path)
                        matches.append(f"{relative}:{line_num}: {line.strip()[:200]}") # Truncate match line
                        if len(matches) >= max_matches:
                            break
                            
            return matches

        tools.append(grep_codebase)

    if enable_rag:
        @tool
        def retrieve_relevant_context(
            query: str,
            max_snippets: int = max_snippets,
        ) -> List[Dict[str, str]]:
            """Retrieve snippets relevant to the query using RAG.
            
            Args:
                query: Free-text query to match against files.
                max_snippets: Maximum number of snippets to return in total.
            
            Note: This tool uses vector search. It is fuzzy and semantic.
            For exact string matching, use 'grep_codebase'.
            """
            normalized_query = query.strip()
            if not normalized_query:
                return []
            
            limit = max(1, max_snippets)
            
            # Primary method: Vector Search
            if rag_store:
                try:
                    return rag_store.query(
                        normalized_query,
                        top_k=limit,
                        include_codebase=True,
                        include_knowledge_base=True,
                    )[:limit]
                except Exception as exc:
                    logger.error(f"RAG query failed: {exc}")
                    return [{"error": "RAG search failed. Please use grep_codebase or navigation tools."}]
            
            return [{"error": "RAG is not enabled. Please use grep_codebase."}]

        tools.append(retrieve_relevant_context)

    return tools