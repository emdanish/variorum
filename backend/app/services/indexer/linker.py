from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from app.services.indexer.code_index import FileSymbols
from app.services.indexer.docs import DiscoveredDoc

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LINKABLE_KINDS = frozenset({"function", "class", "method", "interface"})
_MIN_SYMBOL_LEN = 4
_PATH_CONFIDENCE = 0.8
_SYMBOL_CONFIDENCE = 0.6


@dataclass(frozen=True)
class HeuristicLink:
    doc_path: str
    path: str
    symbol_name: str | None
    confidence: float


def link_documents(
    docs: list[DiscoveredDoc],
    files: list[FileSymbols],
    *,
    max_links_per_doc: int = 25,
) -> list[HeuristicLink]:
    """Heuristically associate docs with code. A doc links to a file when it
    mentions the file path, and to a file's symbol when it mentions a
    sufficiently distinctive symbol name. Deliberately simple and evidence-based;
    later milestones can refine confidence with the AI layer."""
    known_paths = [f.path for f in files]
    symbol_to_paths: dict[str, set[str]] = defaultdict(set)
    for file in files:
        for symbol in file.symbols:
            if symbol.kind in _LINKABLE_KINDS and len(symbol.name) >= _MIN_SYMBOL_LEN:
                symbol_to_paths[symbol.name].add(file.path)

    links: list[HeuristicLink] = []
    for doc in docs:
        seen: set[tuple[str, str | None]] = set()
        doc_links: list[HeuristicLink] = []

        for path in known_paths:
            if path in doc.content and (path, None) not in seen:
                seen.add((path, None))
                doc_links.append(HeuristicLink(doc.path, path, None, _PATH_CONFIDENCE))

        words = set(_WORD.findall(doc.content))
        for name, paths in symbol_to_paths.items():
            if name not in words:
                continue
            for path in paths:
                key = (path, name)
                if key in seen:
                    continue
                seen.add(key)
                doc_links.append(HeuristicLink(doc.path, path, name, _SYMBOL_CONFIDENCE))

        doc_links.sort(key=lambda link: link.confidence, reverse=True)
        links.extend(doc_links[:max_links_per_doc])

    return links
