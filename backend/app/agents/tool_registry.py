import os
import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.chunk import Chunk
from app.models.workflow import WorkflowExecutionORM
from app.models.memory import RepositoryMemoryORM
from app.services.retrieval_service import retrieval_service
from app.agents.base_tool import BaseTool
from app.ai.prompt_loader import prompt_loader

class RepoSearchTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, query: str = "", top_k: int = 5, **kwargs) -> str:
        if not query:
            return "Error: Search query is empty."
        chunks_with_scores = retrieval_service.retrieve_chunks(
            db=self.registry.db,
            repository_id=self.registry.repository_id,
            query=query,
            top_k=top_k
        )
        if not chunks_with_scores:
            return "No matching code chunks found."
        results = []
        for i, (chunk, score) in enumerate(chunks_with_scores):
            results.append(
                f"Result {i+1} (Score: {score:.3f})\n"
                f"File: {chunk.path} (Lines {chunk.start_line}-{chunk.end_line})\n"
                f"Content:\n{chunk.content}\n"
                f"{'-'*40}"
            )
        return "\n".join(results)

class FunctionSearchTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, query: str = "", **kwargs) -> str:
        chunks = (
            self.registry.db.query(Chunk)
            .filter(
                Chunk.repository_id == self.registry.repository_id,
                Chunk.content.like("%def %") | Chunk.content.like("%function %") | Chunk.content.like("%async %")
            )
            .limit(20)
            .all()
        )
        if not chunks:
            return "No function declarations found."
        results = []
        for chunk in chunks:
            lines = chunk.content.split("\n")
            for idx, line in enumerate(lines):
                if ("def " in line or "function " in line) and (not query or query.lower() in line.lower()):
                    line_num = chunk.start_line + idx
                    results.append(f"File: {chunk.path} | Line {line_num}: {line.strip()}")
        return "\n".join(results[:30]) if results else "No functions matching search query found."

class ClassSearchTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, query: str = "", **kwargs) -> str:
        chunks = (
            self.registry.db.query(Chunk)
            .filter(
                Chunk.repository_id == self.registry.repository_id,
                Chunk.content.like("%class %") | Chunk.content.like("%interface %")
            )
            .limit(20)
            .all()
        )
        if not chunks:
            return "No class declarations found."
        results = []
        for chunk in chunks:
            lines = chunk.content.split("\n")
            for idx, line in enumerate(lines):
                if ("class " in line or "interface " in line) and (not query or query.lower() in line.lower()):
                    line_num = chunk.start_line + idx
                    results.append(f"File: {chunk.path} | Line {line_num}: {line.strip()}")
        return "\n".join(results[:30]) if results else "No classes matching search query found."

class SymbolSearchTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, symbol: str = "", **kwargs) -> str:
        if not symbol:
            return "Error: Symbol name is empty."
        chunks = (
            self.registry.db.query(Chunk)
            .filter(
                Chunk.repository_id == self.registry.repository_id,
                Chunk.content.like(f"%{symbol}%")
            )
            .limit(10)
            .all()
        )
        if not chunks:
            return f"No occurrences of symbol '{symbol}' found."
        results = []
        for chunk in chunks:
            matches = []
            lines = chunk.content.split("\n")
            for idx, line in enumerate(lines):
                if re.search(r'\b(def|class|function|interface|const|let|var|type|struct)\b.*\b' + re.escape(symbol) + r'\b', line):
                    line_num = chunk.start_line + idx
                    matches.append(f"  Line {line_num}: {line.strip()}")
            if matches:
                results.append(f"File: {chunk.path}\n" + "\n".join(matches))
        if not results:
            for chunk in chunks[:3]:
                results.append(
                    f"File: {chunk.path} (Lines {chunk.start_line}-{chunk.end_line} contains mentions):\n"
                    f"{chunk.content[:200]}..."
                )
        return "\n\n".join(results)

class DirectoryReaderTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, path: str = "", **kwargs) -> str:
        target_dir = os.path.join(self.registry.workspace_path, path.lstrip("/\\"))
        if not os.path.exists(target_dir):
            return f"Error: Path '{path}' does not exist."
        if not os.path.isdir(target_dir):
            return f"Error: '{path}' is a file, not a directory."
        try:
            items = os.listdir(target_dir)
            out = [f"Contents of directory '{path if path else '/'}':"]
            for item in sorted(items):
                full = os.path.join(target_dir, item)
                is_dir = os.path.isdir(full)
                prefix = "[DIR] " if is_dir else "[FILE]"
                out.append(f"  {prefix} {item}")
            return "\n".join(out)
        except Exception as e:
            return f"Error reading directory: {str(e)}"

class RepoStatsTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, **kwargs) -> str:
        total_files = 0
        total_lines = 0
        extensions = {}
        for root, dirs, files in os.walk(self.registry.workspace_path):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", "__pycache__", ".gemini")]
            for f in files:
                total_files += 1
                ext = os.path.splitext(f)[1] or "no-extension"
                extensions[ext] = extensions.get(ext, 0) + 1
                try:
                    with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as file_obj:
                        total_lines += len(file_obj.readlines())
                except:
                    pass
        stats = {
            "workspace_path": self.registry.workspace_path,
            "total_files": total_files,
            "total_lines_approx": total_lines,
            "file_types": extensions
        }
        return json.dumps(stats, indent=2)

class DependencyAnalyzerTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, **kwargs) -> str:
        deps_info = []
        pkg_json_path = os.path.join(self.registry.workspace_path, "package.json")
        if os.path.exists(pkg_json_path):
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                deps_info.append("Node.js package.json Dependencies:")
                if "dependencies" in data:
                    deps_info.append("  Production Dependencies:")
                    for k, v in data["dependencies"].items():
                        deps_info.append(f"    - {k}: {v}")
                if "devDependencies" in data:
                    deps_info.append("  Dev Dependencies:")
                    for k, v in data["devDependencies"].items():
                        deps_info.append(f"    - {k}: {v}")
            except Exception as e:
                deps_info.append(f"Error parsing package.json: {str(e)}")

        reqs_path = os.path.join(self.registry.workspace_path, "requirements.txt")
        if os.path.exists(reqs_path):
            try:
                with open(reqs_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                deps_info.append("Python requirements.txt Dependencies:")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        deps_info.append(f"  - {line}")
            except Exception as e:
                deps_info.append(f"Error reading requirements.txt: {str(e)}")

        if not deps_info:
            return "No standard package manager dependency files found."
        return "\n".join(deps_info)

class GitDiffReaderTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, **kwargs) -> str:
        try:
            import git
            if os.path.exists(os.path.join(self.registry.workspace_path, ".git")):
                repo = git.Repo(self.registry.workspace_path)
                diff = repo.git.diff()
                return diff if diff else "No changes detected (clean working directory)."
            return "Not a git repository workspace. (No .git folder found)."
        except Exception as e:
            return f"Error reading git diff: {str(e)}"

class ConfigReaderTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, path: str = "", **kwargs) -> str:
        if not path:
            root_files = os.listdir(self.registry.workspace_path)
            config_files = [f for f in root_files if f.endswith((".json", ".config.js", ".config.ts", ".yaml", ".yml", ".ini"))]
            return "Workspace configuration files detected:\n" + "\n".join([f"  - {f}" for f in config_files])
        # Use FileReader logic
        file_tool = FileReaderTool(self.registry)
        return file_tool.execute(path=path)

class FileReaderTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, path: str = "", **kwargs) -> str:
        if not path:
            return "Error: File path is empty."
        clean_path = path.lstrip("/\\")
        full_path = os.path.join(self.registry.workspace_path, clean_path)
        if not os.path.exists(full_path):
            return f"Error: File '{path}' does not exist in workspace."
        if os.path.isdir(full_path):
            return f"Error: '{path}' is a directory, not a file."
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            lines = content.split("\n")
            numbered = [f"{idx+1}: {line}" for idx, line in enumerate(lines)]
            return "\n".join(numbered)
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"

class DocGeneratorTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, content: str = "", path: str = "", **kwargs) -> str:
        if not path or not content:
            return "Error: Path or content missing."
        return f"Successfully drafted documentation for '{path}' ({len(content)} characters)."

class ChunkRetrieverTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, path: str = "", **kwargs) -> str:
        if not path:
            return "Error: Path parameter is required."
        chunks = (
            self.registry.db.query(Chunk)
            .filter(
                Chunk.repository_id == self.registry.repository_id,
                Chunk.path == path
            )
            .all()
        )
        if not chunks:
            return f"No indexed chunks found for file '{path}'."
        out = []
        for c in chunks:
            out.append(f"--- Chunk ID: {c.id} (Lines {c.start_line}-{c.end_line}) ---\n{c.content}\n")
        return "\n".join(out)

class ContextSelectorTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, files: List[str] = None, **kwargs) -> str:
        if not files:
            return "No files specified for context selection."
        selected = []
        file_tool = FileReaderTool(self.registry)
        for f in files[:5]: # Cap at 5 context files for LLM safety limits
            content = file_tool.execute(path=f)
            if not content.startswith("Error:"):
                # truncate to avoid bloating context
                selected.append(f"=== File: {f} ===\n{content[:2000]}...\n")
        return "\n".join(selected)

class PromptLibraryTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, agent: str = "", version: str = "1.0.0", **kwargs) -> str:
        if not agent:
            return "Error: Agent parameter is required."
        try:
            sys_p, user_p, meta = prompt_loader.load_prompt(agent, version)
            return json.dumps({
                "agent": agent,
                "version": version,
                "metadata": meta,
                "system_prompt_preview": sys_p[:200] + "...",
                "user_prompt_preview": user_p[:200] + "..."
            }, indent=2)
        except Exception as e:
            return f"Error loading prompt from PromptLibrary: {str(e)}"

class RepositoryMemoryTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, action: str = "get", key: str = "general", content: str = "", **kwargs) -> str:
        if action.lower() == "save":
            if not content:
                return "Error: Content is empty."
            mem = RepositoryMemoryORM(
                repository_id=self.registry.repository_id,
                memory_key=key,
                content=content
            )
            self.registry.db.add(mem)
            self.registry.db.commit()
            return f"Successfully saved memory key '{key}' to database repository store."
        else:
            mems = (
                self.registry.db.query(RepositoryMemoryORM)
                .filter(
                    RepositoryMemoryORM.repository_id == self.registry.repository_id,
                    RepositoryMemoryORM.memory_key == key
                )
                .order_by(RepositoryMemoryORM.created_at.desc())
                .all()
            )
            if not mems:
                return f"No previous repository memories found for key '{key}'."
            out = []
            for m in mems[:5]:
                out.append(f"[{m.created_at.isoformat()}] Memory:\n{m.content}\n{'-'*40}")
            return "\n".join(out)

class WorkflowHistoryTool(BaseTool):
    def __init__(self, registry):
        self.registry = registry

    def execute(self, limit: int = 5, **kwargs) -> str:
        runs = (
            self.registry.db.query(WorkflowExecutionORM)
            .filter(WorkflowExecutionORM.repository_id == self.registry.repository_id)
            .order_by(WorkflowExecutionORM.created_at.desc())
            .limit(limit)
            .all()
        )
        if not runs:
            return "No workflow execution history found for this repository."
        out = []
        for r in runs:
            out.append(
                f"Workflow ID: {r.id}\n"
                f"  Type: {r.workflow_type} | Status: {r.status}\n"
                f"  Goal: {r.goal}\n"
                f"  Duration: {(r.duration or 0.0):.1f}s\n"
                f"{'-'*40}"
            )
        return "\n".join(out)

class ToolRegistry:
    """
    Registry container mapping available conformant tool instances.
    """
    def __init__(self, workspace_path: str, repository_id: str, db: Session):
        self.workspace_path = workspace_path
        self.repository_id = repository_id
        self.db = db
        
        self.tools: Dict[str, BaseTool] = {
            "repo_search": RepoSearchTool(self),
            "rag_retrieval": RepoSearchTool(self),
            "function_search": FunctionSearchTool(self),
            "class_search": ClassSearchTool(self),
            "symbol_search": SymbolSearchTool(self),
            "directory_reader": DirectoryReaderTool(self),
            "repo_stats": RepoStatsTool(self),
            "dependency_analyzer": DependencyAnalyzerTool(self),
            "git_diff_reader": GitDiffReaderTool(self),
            "config_reader": ConfigReaderTool(self),
            "file_reader": FileReaderTool(self),
            "doc_generator": DocGeneratorTool(self),
            "chunk_retriever": ChunkRetrieverTool(self),
            "context_selector": ContextSelectorTool(self),
            "prompt_library": PromptLibraryTool(self),
            "repository_memory": RepositoryMemoryTool(self),
            "workflow_history": WorkflowHistoryTool(self)
        }

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        tool_key = tool_name.strip().lower().replace(" ", "_")
        if tool_key not in self.tools:
            return f"Error: Tool '{tool_name}' is not registered."
        try:
            return self.tools[tool_key].execute(**arguments)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
