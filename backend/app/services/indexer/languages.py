from __future__ import annotations

from dataclasses import dataclass

# Directories that never contain first-party source worth indexing.
IGNORED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".next",
        "out",
        "vendor",
        "target",
        ".idea",
        ".vscode",
    }
)

MAX_FILE_BYTES = 1_000_000


@dataclass(frozen=True)
class LanguageSpec:
    name: str
    symbol_nodes: dict[str, str]  # tree-sitter node type -> symbol kind
    import_nodes: frozenset[str]
    class_node_types: frozenset[str]


_PYTHON = LanguageSpec(
    name="python",
    symbol_nodes={"function_definition": "function", "class_definition": "class"},
    import_nodes=frozenset({"import_statement", "import_from_statement"}),
    class_node_types=frozenset({"class_definition"}),
)

_JS = LanguageSpec(
    name="javascript",
    symbol_nodes={
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
    },
    import_nodes=frozenset({"import_statement"}),
    class_node_types=frozenset({"class_declaration"}),
)

_TS = LanguageSpec(
    name="typescript",
    symbol_nodes={
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
    },
    import_nodes=frozenset({"import_statement"}),
    class_node_types=frozenset({"class_declaration"}),
)

_TSX = LanguageSpec(
    name="tsx",
    symbol_nodes=_TS.symbol_nodes,
    import_nodes=_TS.import_nodes,
    class_node_types=_TS.class_node_types,
)

_EXTENSION_TO_SPEC: dict[str, LanguageSpec] = {
    ".py": _PYTHON,
    ".js": _JS,
    ".jsx": _JS,
    ".mjs": _JS,
    ".cjs": _JS,
    ".ts": _TS,
    ".tsx": _TSX,
}


def spec_for_path(path: str) -> LanguageSpec | None:
    lower = path.lower()
    for ext, spec in _EXTENSION_TO_SPEC.items():
        if lower.endswith(ext):
            return spec
    return None
