from __future__ import annotations

from app.services.indexer.code_index import extract_symbols, index_directory
from app.services.indexer.languages import spec_for_path


def _kinds_by_name(symbols):
    return {s.name: s.kind for s in symbols}


def test_extract_python_symbols():
    src = (
        b"import os\n"
        b"from a.b import c\n\n"
        b"class Foo:\n"
        b"    def method_one(self):\n"
        b"        pass\n\n"
        b"def top_level():\n"
        b"    pass\n"
    )
    symbols = extract_symbols(src, spec_for_path("x.py"))
    by_name = _kinds_by_name(symbols)
    assert by_name.get("Foo") == "class"
    assert by_name.get("method_one") == "method"
    assert by_name.get("top_level") == "function"
    assert any(s.kind == "import" for s in symbols)


def test_python_line_numbers():
    src = b"def a():\n    pass\n\ndef b():\n    pass\n"
    symbols = [s for s in extract_symbols(src, spec_for_path("x.py")) if s.kind == "function"]
    a = next(s for s in symbols if s.name == "a")
    b = next(s for s in symbols if s.name == "b")
    assert a.start_line == 1
    assert b.start_line == 4


def test_extract_javascript_symbols():
    src = b"export function doThing() {}\nclass Thing {}\n"
    by_name = _kinds_by_name(extract_symbols(src, spec_for_path("u.js")))
    assert by_name.get("doThing") == "function"
    assert by_name.get("Thing") == "class"


def test_index_directory_skips_ignored_dirs(sample_repo):
    files = index_directory(sample_repo)
    paths = {f.path for f in files}
    assert "src/app.py" in paths
    assert "src/util.js" in paths
    assert not any("node_modules" in p for p in paths)

    all_names = {s.name for f in files for s in f.symbols}
    assert {"Widget", "render", "helper", "doThing", "Thing"} <= all_names
    assert "nope" not in all_names


def test_spec_for_unknown_extension_is_none():
    assert spec_for_path("image.png") is None
    assert spec_for_path("data.json") is None
