from __future__ import annotations

import os
import subprocess
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from tavily import TavilyClient

from autodev.config import Settings


class ReadFileInput(BaseModel):
    path: str = Field(description="File path relative to workspace root.")


class WriteFileInput(BaseModel):
    path: str = Field(description="File path relative to workspace root.")
    content: str = Field(description="Full text content to write.")


class SearchCodeInput(BaseModel):
    pattern: str = Field(description="Regex pattern to search.")
    glob: str = Field(default="*.py", description="Glob filter.")


class ShellInput(BaseModel):
    command: str = Field(description="Shell command to execute in workspace.")


class TavilySearchInput(BaseModel):
    query: str = Field(description="Search query for real-time web search.")
    max_results: int = Field(default=5, description="Maximum number of returned results.")


def _confirm(settings: Settings, action: str) -> bool:
    if settings.execution_mode == "auto" and settings.allow_unsafe_auto_exec:
        return True
    answer = input(f"[confirm] {action}? (y/N): ").strip().lower()
    return answer in {"y", "yes"}


def build_builtin_tools(settings: Settings) -> list[StructuredTool]:
    workspace = settings.workspace

    def read_file(path: str) -> str:
        target = (workspace / path).resolve()
        if not str(target).startswith(str(workspace.resolve())):
            return "Denied: path outside workspace."
        if not target.exists():
            return f"Not found: {path}"
        return target.read_text(encoding="utf-8")

    def write_file(path: str, content: str) -> str:
        if not _confirm(settings, f"Write file {path}"):
            return "Cancelled by user."
        target = (workspace / path).resolve()
        if not str(target).startswith(str(workspace.resolve())):
            return "Denied: path outside workspace."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {path}"

    def search_code(pattern: str, glob: str = "*.py") -> str:
        import re

        compiled = re.compile(pattern)
        matches: list[str] = []
        for file_path in workspace.rglob(glob):
            if ".venv" in file_path.parts:
                continue
            try:
                for i, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
                    if compiled.search(line):
                        rel = file_path.relative_to(workspace)
                        matches.append(f"{rel}:{i}:{line}")
            except UnicodeDecodeError:
                continue
        return "\n".join(matches[:200]) or "No matches."

    def run_shell(command: str) -> str:
        if not _confirm(settings, f"Run shell command `{command}`"):
            return "Cancelled by user."
        completed = subprocess.run(
            command,
            cwd=workspace,
            shell=True,
            capture_output=True,
            text=True,
        )
        return f"exit={completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"

    def web_search_tavily(query: str, max_results: int = 5) -> str:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            return "TAVILY_API_KEY is missing. Add it to .env to enable real-time web search."
        try:
            client = TavilyClient(api_key=api_key)
            result = client.search(
                query=query,
                max_results=max(1, min(max_results, 10)),
                search_depth="advanced",
            )
        except Exception as exc:  # noqa: BLE001
            return f"Tavily search failed: {exc}"

        output: list[str] = []
        answer = result.get("answer")
        if answer:
            output.append(f"Answer: {answer}")
        for idx, item in enumerate(result.get("results", []), start=1):
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content = (item.get("content", "") or "").strip()
            output.append(f"[{idx}] {title}\n{url}\n{content[:500]}")
        return "\n\n".join(output) or "No Tavily results."

    return [
        StructuredTool.from_function(
            func=read_file,
            name="read_file",
            description="Read a UTF-8 text file from workspace.",
            args_schema=ReadFileInput,
        ),
        StructuredTool.from_function(
            func=write_file,
            name="write_file",
            description="Write UTF-8 text to a file in workspace.",
            args_schema=WriteFileInput,
        ),
        StructuredTool.from_function(
            func=search_code,
            name="search_code",
            description="Regex search across workspace code files.",
            args_schema=SearchCodeInput,
        ),
        StructuredTool.from_function(
            func=run_shell,
            name="run_shell",
            description="Execute a shell command in workspace.",
            args_schema=ShellInput,
        ),
        StructuredTool.from_function(
            func=web_search_tavily,
            name="web_search_tavily",
            description="Run real-time web search using Tavily API.",
            args_schema=TavilySearchInput,
        ),
    ]
