from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.services.indexer.code_index import iter_source_files
from app.services.indexer.languages import MAX_FILE_BYTES

DOC_EXTENSIONS = (".md", ".mdx", ".markdown", ".rst")
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class DiscoveredDoc:
    path: str
    title: str | None
    kind: str
    content_hash: str
    content: str


def _title_for(path: Path, content: str) -> str | None:
    match = _H1.search(content)
    if match:
        return match.group(1).strip()[:512]
    return path.stem


def discover_documents(root: Path) -> list[DiscoveredDoc]:
    docs: list[DiscoveredDoc] = []
    for path in iter_source_files(root):
        if not path.name.lower().endswith(DOC_EXTENSIONS):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) > MAX_FILE_BYTES:
            continue
        content = data.decode("utf-8", "replace")
        docs.append(
            DiscoveredDoc(
                path=path.relative_to(root).as_posix(),
                title=_title_for(path, content),
                kind="markdown",
                content_hash=hashlib.sha256(data).hexdigest(),
                content=content,
            )
        )
    return docs
