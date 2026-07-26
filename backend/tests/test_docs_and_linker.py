from __future__ import annotations

from app.services.indexer.code_index import ExtractedSymbol, FileSymbols
from app.services.indexer.docs import DiscoveredDoc, discover_documents
from app.services.indexer.linker import link_documents


def test_discover_documents_finds_markdown_with_title(sample_repo):
    docs = discover_documents(sample_repo)
    readme = next(d for d in docs if d.path == "README.md")
    assert readme.title == "Sample Project"
    assert readme.kind == "markdown"
    assert len(readme.content_hash) == 64


def test_discover_documents_skips_ignored_and_non_docs(sample_repo):
    paths = {d.path for d in discover_documents(sample_repo)}
    assert paths == {"README.md"}


def _sym(name: str, kind: str) -> ExtractedSymbol:
    return ExtractedSymbol(
        kind=kind, name=name, language="python", start_line=1, end_line=2, signature=""
    )


def test_linker_links_by_path_and_symbol():
    files = [
        FileSymbols(
            path="src/app.py",
            language="python",
            symbols=[_sym("Widget", "class"), _sym("helper", "function")],
        )
    ]
    docs = [
        DiscoveredDoc(
            path="README.md",
            title="Doc",
            kind="markdown",
            content_hash="h",
            content="The Widget class lives in src/app.py.",
        )
    ]
    links = link_documents(docs, files)
    path_links = [link for link in links if link.symbol_name is None]
    symbol_links = [link for link in links if link.symbol_name == "Widget"]
    assert any(link.path == "src/app.py" for link in path_links)
    assert symbol_links and symbol_links[0].path == "src/app.py"
    # "helper" is not mentioned in the doc, so it must not be linked
    assert all(link.symbol_name != "helper" for link in links)


def test_linker_ignores_unmentioned_symbols():
    files = [FileSymbols(path="a.py", language="python", symbols=[_sym("Unmentioned", "class")])]
    docs = [
        DiscoveredDoc(
            path="d.md", title="d", kind="markdown", content_hash="h", content="nothing here"
        )
    ]
    assert link_documents(docs, files) == []
