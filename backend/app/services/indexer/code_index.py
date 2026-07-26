from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from tree_sitter_language_pack import get_parser

from app.services.indexer.languages import (
    IGNORED_DIRS,
    MAX_FILE_BYTES,
    LanguageSpec,
    spec_for_path,
)

_parsers: dict[str, object] = {}


def _parser(language: str):
    if language not in _parsers:
        _parsers[language] = get_parser(language)  # type: ignore[arg-type]
    return _parsers[language]


@dataclass
class ExtractedSymbol:
    kind: str
    name: str
    language: str
    start_line: int
    end_line: int
    signature: str


@dataclass
class FileSymbols:
    path: str
    language: str
    symbols: list[ExtractedSymbol]


def _first_line(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped.splitlines()[0][:300]


def _node_name(node) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is not None and name_node.text is not None:
        return name_node.text.decode("utf-8", "replace")
    return None


def extract_symbols(source: bytes, spec: LanguageSpec) -> list[ExtractedSymbol]:
    tree = _parser(spec.name).parse(source)
    symbols: list[ExtractedSymbol] = []

    def text_of(node) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", "replace")

    def visit(node, in_class: bool) -> None:
        kind = spec.symbol_nodes.get(node.type)
        if kind is not None:
            name = _node_name(node)
            if name:
                resolved = "method" if kind == "function" and in_class else kind
                symbols.append(
                    ExtractedSymbol(
                        kind=resolved,
                        name=name,
                        language=spec.name,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        signature=_first_line(text_of(node)),
                    )
                )
        elif node.type in spec.import_nodes:
            line = _first_line(text_of(node))
            symbols.append(
                ExtractedSymbol(
                    kind="import",
                    name=line,
                    language=spec.name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=line,
                )
            )

        child_in_class = in_class or node.type in spec.class_node_types
        for child in node.children:
            visit(child, child_in_class)

    visit(tree.root_node, False)
    return symbols


def iter_source_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            yield Path(dirpath) / filename


def index_directory(root: Path) -> list[FileSymbols]:
    results: list[FileSymbols] = []
    for path in iter_source_files(root):
        spec = spec_for_path(path.name)
        if spec is None:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) > MAX_FILE_BYTES:
            continue
        results.append(
            FileSymbols(
                path=path.relative_to(root).as_posix(),
                language=spec.name,
                symbols=extract_symbols(data, spec),
            )
        )
    return results
