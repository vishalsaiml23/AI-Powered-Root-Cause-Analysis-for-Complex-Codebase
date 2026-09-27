"""Tests for DependencyGraph."""
import os, sys, json, pytest
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from rca_engine.ast_analyzer import ASTAnalyzer
from rca_engine.dependency_graph import DependencyGraph
SAMPLE_DIR = os.path.join(PROJECT_ROOT, "sample_targets", "ecommerce_checkout")

@pytest.fixture(scope="module")
def built_graph():
    syms = ASTAnalyzer().analyze(SAMPLE_DIR)
    g = DependencyGraph(); g.build(syms, SAMPLE_DIR); return g

def test_graph_has_nodes(built_graph):
    assert len(built_graph.get_graph_dict()["nodes"]) > 0

def test_graph_has_edges(built_graph):
    assert len(built_graph.get_graph_dict()["edges"]) > 0

def test_file_nodes_present(built_graph):
    names = {n["name"] for n in built_graph.get_graph_dict()["nodes"] if n["kind"] == "file"}
    assert {"cart.py","checkout.py","discount.py","tax.py"} <= names

def test_symbol_nodes_present(built_graph):
    names = {n["name"] for n in built_graph.get_graph_dict()["nodes"] if n["kind"] != "file"}
    for nm in ("Cart","CartItem","calculate_discount","calculate_sales_tax"):
        assert nm in names

def test_import_edge_checkout_to_discount(built_graph):
    edges = [e for e in built_graph.get_graph_dict()["edges"] if e["edge_type"] == "imports"]
    assert any("checkout" in e["source"] and "discount" in e["target"] for e in edges)

def test_import_edge_checkout_to_tax(built_graph):
    edges = [e for e in built_graph.get_graph_dict()["edges"] if e["edge_type"] == "imports"]
    assert any("checkout" in e["source"] and "tax" in e["target"] for e in edges)

def test_json_serializable(built_graph):
    json.dumps(built_graph.get_graph_dict())  # must not raise

def test_get_source_files(built_graph):
    sources = built_graph.get_source_files()
    assert sources and all(isinstance(v, str) for v in sources.values())

def test_rebuild_idempotent():
    syms = ASTAnalyzer().analyze(SAMPLE_DIR)
    g = DependencyGraph(); g.build(syms, SAMPLE_DIR)
    c1 = len(g.get_graph_dict()["nodes"]); g.build(syms, SAMPLE_DIR)
    assert c1 == len(g.get_graph_dict()["nodes"])
