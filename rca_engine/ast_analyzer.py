"""
AST Analyzer — Multi-language static analysis of source files.

Parses Python ASTs via Python's standard `ast` module, and provides
lexical parsing for TypeScript / JavaScript files. Extracts symbols,
call graphs, imports, and metadata.
"""
from __future__ import annotations

import ast
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


@dataclass
class CodeSymbol:
    """Represents a named code entity extracted from source code."""
    name: str
    kind: str               # "function" | "class" | "method"
    line_number: int
    file_path: str
    docstring: Optional[str] = None
    source_snippet: str = ""
    qualified_name: str = ""

    def __post_init__(self):
        if not self.qualified_name:
            self.qualified_name = self.name


# Alias for compatibility
SymbolNode = CodeSymbol


@dataclass
class FileAnalysis:
    """Represents the static analysis result of a single source file."""
    file_path: str
    relative_path: str
    language: str           # "python" | "typescript" | "javascript"
    line_count: int
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    called_functions: List[str] = field(default_factory=list)
    content: str = ""


def _extract_source_snippet(source_lines: List[str], node: ast.AST, max_lines: int = 5) -> str:
    start = max(0, getattr(node, "lineno", 1) - 1)
    end = min(start + max_lines, len(source_lines))
    snippet = "".join(source_lines[start:end])
    return textwrap.dedent(snippet).strip()


class CodebaseScanner:
    """
    Scans a directory of code files and generates FileAnalysis records.
    Supports Python, JavaScript, and TypeScript files.
    """

    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
    }

    IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        "venv",
        ".venv",
        "dist",
        "build",
    }

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()

    def scan(self) -> Dict[str, FileAnalysis]:
        """
        Walk all supported files under root_dir and extract symbols and imports.
        Returns a dict mapping relative path string to FileAnalysis.
        """
        results: Dict[str, FileAnalysis] = {}

        if not self.root_dir.exists():
            return results

        if self.root_dir.is_file():
            fa = self._analyze_file(self.root_dir, self.root_dir.parent)
            if fa:
                results[fa.relative_path] = fa
            return results

        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            dirnames[:] = [d for d in dirnames if d not in self.IGNORE_DIRS and not d.startswith(".")]

            for filename in sorted(filenames):
                file_path = Path(dirpath) / filename
                ext = file_path.suffix.lower()
                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue

                fa = self._analyze_file(file_path, self.root_dir)
                if fa:
                    results[fa.relative_path] = fa

        return results

    def _analyze_file(self, file_path: Path, base_dir: Path) -> Optional[FileAnalysis]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        rel_path = file_path.relative_to(base_dir).as_posix()
        ext = file_path.suffix.lower()
        language = self.SUPPORTED_EXTENSIONS.get(ext, "unknown")
        lines = content.splitlines(keepends=True)

        if language == "python":
            symbols, imports, calls = self._parse_python(content, rel_path, lines)
        else:
            symbols, imports, calls = self._parse_js_ts(content, rel_path, lines)

        return FileAnalysis(
            file_path=str(file_path),
            relative_path=rel_path,
            language=language,
            line_count=len(lines),
            symbols=symbols,
            imports=imports,
            called_functions=calls,
            content=content,
        )

    def _parse_python(self, content: str, rel_path: str, lines: List[str]):
        symbols: List[CodeSymbol] = []
        imports: List[str] = []
        calls: List[str] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return symbols, imports, calls

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)

        def visit(node: ast.AST, parent_class: Optional[str] = None):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, getattr(ast, "AsyncFunctionDef", ()))):
                    kind = "method" if parent_class else "function"
                    qualified = f"{parent_class}.{child.name}" if parent_class else child.name
                    snippet = _extract_source_snippet(lines, child)
                    doc = ast.get_docstring(child)
                    symbols.append(CodeSymbol(
                        name=child.name,
                        kind=kind,
                        line_number=child.lineno,
                        file_path=rel_path,
                        docstring=doc,
                        source_snippet=snippet,
                        qualified_name=qualified,
                    ))
                    visit(child, parent_class=parent_class)
                elif isinstance(child, ast.ClassDef):
                    snippet = _extract_source_snippet(lines, child)
                    doc = ast.get_docstring(child)
                    symbols.append(CodeSymbol(
                        name=child.name,
                        kind="class",
                        line_number=child.lineno,
                        file_path=rel_path,
                        docstring=doc,
                        source_snippet=snippet,
                        qualified_name=child.name,
                    ))
                    visit(child, parent_class=child.name)
                else:
                    visit(child, parent_class=parent_class)

        visit(tree)
        symbols.sort(key=lambda s: s.line_number)
        return symbols, imports, calls

    def _parse_js_ts(self, content: str, rel_path: str, lines: List[str]):
        symbols: List[CodeSymbol] = []
        imports: List[str] = []
        calls: List[str] = []

        import_pattern = re.compile(r'import\s+(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]')
        fn_pattern = re.compile(r'(?:function\s+([A-Za-z0-9_$]+)|const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|(?:export\s+)?class\s+([A-Za-z0-9_$]+))')
        call_pattern = re.compile(r'\b([A-Za-z0-9_$]+)\s*\(')

        for line in lines:
            imp_m = import_pattern.search(line)
            if imp_m:
                imports.append(imp_m.group(1))

        for idx, line in enumerate(lines, 1):
            m = fn_pattern.search(line)
            if m:
                name = m.group(1) or m.group(2) or m.group(3)
                kind = "class" if "class" in line else "function"
                start = max(0, idx - 1)
                end = min(len(lines), start + 5)
                snippet = "".join(lines[start:end]).strip()
                symbols.append(CodeSymbol(
                    name=name,
                    kind=kind,
                    line_number=idx,
                    file_path=rel_path,
                    source_snippet=snippet,
                    qualified_name=name,
                ))

            for call_m in call_pattern.finditer(line):
                callee = call_m.group(1)
                if callee not in {"if", "for", "while", "switch", "catch", "import", "function"}:
                    calls.append(callee)

        return symbols, imports, calls


class ASTAnalyzer:
    """Analyzes a Python project directory and returns a flat list of SymbolNodes."""

    def analyze(self, repo_path: str) -> List[CodeSymbol]:
        scanner = CodebaseScanner(repo_path)
        res = scanner.scan()
        all_symbols: List[CodeSymbol] = []
        for fa in res.values():
            all_symbols.extend(fa.symbols)
        return sorted(all_symbols, key=lambda s: (s.file_path, s.line_number))
