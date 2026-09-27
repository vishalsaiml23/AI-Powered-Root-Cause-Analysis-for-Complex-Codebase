"""Tests for ASTAnalyzer."""
import os, sys, pytest
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from rca_engine.ast_analyzer import ASTAnalyzer, SymbolNode
SAMPLE_DIR = os.path.join(PROJECT_ROOT, "sample_targets", "ecommerce_checkout")

def test_analyze_returns_list():
    symbols = ASTAnalyzer().analyze(SAMPLE_DIR)
    assert isinstance(symbols, list) and len(symbols) > 0

def test_extracts_expected_symbols():
    names = {s.name for s in ASTAnalyzer().analyze(SAMPLE_DIR)}
    assert {"Cart","CartItem","calculate_discount","calculate_sales_tax","CheckoutService"} <= names

def test_symbol_kinds():
    by_name = {s.name: s for s in ASTAnalyzer().analyze(SAMPLE_DIR)}
    assert by_name["Cart"].kind == "class"
    assert by_name["CartItem"].kind == "class"
    assert by_name["calculate_discount"].kind == "function"
    assert by_name["calculate_sales_tax"].kind == "function"

def test_method_kind(tmp_path):
    (tmp_path / "m.py").write_text("class Foo:\n    def bar(self): pass\n")
    symbols = ASTAnalyzer().analyze(str(tmp_path))
    assert any(s.name == "bar" and s.kind == "method" for s in symbols)

def test_symbol_has_line_number():
    for sym in ASTAnalyzer().analyze(SAMPLE_DIR):
        assert sym.line_number >= 1

def test_symbol_has_source_snippet():
    for sym in ASTAnalyzer().analyze(SAMPLE_DIR):
        assert len(sym.source_snippet) > 0

def test_skips_hidden_dirs(tmp_path):
    h = tmp_path / ".hidden"; h.mkdir()
    (h / "s.py").write_text("def hidden_fn(): pass")
    (tmp_path / "v.py").write_text("def visible_fn(): pass")
    names = {s.name for s in ASTAnalyzer().analyze(str(tmp_path))}
    assert "visible_fn" in names and "hidden_fn" not in names

def test_skips_pycache(tmp_path):
    c = tmp_path / "__pycache__"; c.mkdir()
    (c / "x.py").write_text("def cached_fn(): pass")
    assert all(s.name != "cached_fn" for s in ASTAnalyzer().analyze(str(tmp_path)))

def test_syntax_error_skipped(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(:\n    pass\n")
    (tmp_path / "good.py").write_text("def good_fn(): pass\n")
    names = {s.name for s in ASTAnalyzer().analyze(str(tmp_path))}
    assert "good_fn" in names
