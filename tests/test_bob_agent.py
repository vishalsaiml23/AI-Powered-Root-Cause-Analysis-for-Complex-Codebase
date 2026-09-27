"""Tests for BobAgent - uses mocked OpenAI client."""
import json, os, sys
from unittest.mock import MagicMock, patch
import pytest
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from rca_engine.bob_agent import BobAgent, RCAResult, FixProposal

MOCK_RCA = json.dumps({
    "culprit_file": "discount.py", "culprit_symbol": "calculate_discount",
    "culprit_line": 55, "confidence_score": 96,
    "root_cause_explanation": "No clamp on discount.",
    "propagation_steps": ["step1","step2"], "symptom_class": "Runtime Exception",
})
MOCK_FIX = json.dumps({
    "diff_patch": "-return 0\n+return clamped", "fixed_source": "def f(): return 0.0",
    "rationale": "Clamp prevents negatives.", "side_effects": "None.",
})
MOCK_TESTS = "def test_regression():\n    assert True\n"

GRAPH = {"nodes":[{"id":"discount.py::__file__","file_path":"discount.py","name":"discount.py","qualified_name":"discount.py","kind":"file","line_number":0}],"edges":[]}
SOURCES = {"discount.py":"def calculate_discount(s,c=None,v=None):\n    return 0.0\n"}

def _completion(text):
    msg = MagicMock(); msg.content = text
    choice = MagicMock(); choice.message = msg
    comp = MagicMock(); comp.choices = [choice]
    return comp

@pytest.fixture
def agent_mock():
    import openai as oai
    mc = MagicMock()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
        with patch.object(oai, "OpenAI", return_value=mc):
            a = BobAgent(); a._client = mc; yield a, mc

def test_analyze_root_cause(agent_mock):
    a, mc = agent_mock
    mc.chat.completions.create.return_value = _completion(MOCK_RCA)
    r = a.analyze_root_cause(GRAPH, "bug", SOURCES)
    assert isinstance(r, RCAResult)
    assert r.culprit_file == "discount.py"
    assert r.culprit_line == 55
    assert r.confidence_score == 96

def test_analyze_calls_gpt4o(agent_mock):
    a, mc = agent_mock
    mc.chat.completions.create.return_value = _completion(MOCK_RCA)
    a.analyze_root_cause(GRAPH, "bug", SOURCES)
    mc.chat.completions.create.assert_called_once()
    assert mc.chat.completions.create.call_args[1]["model"] == "gpt-4o"

def test_generate_fix(agent_mock):
    a, mc = agent_mock
    mc.chat.completions.create.return_value = _completion(MOCK_FIX)
    rca = RCAResult("discount.py","calculate_discount",55,96,"msg",[],"Runtime")
    fix = a.generate_fix(rca, SOURCES["discount.py"])
    assert isinstance(fix, FixProposal) and len(fix.diff_patch) > 0

def test_generate_tests(agent_mock):
    a, mc = agent_mock
    mc.chat.completions.create.return_value = _completion(MOCK_TESTS)
    rca = RCAResult("discount.py","calculate_discount",55,96,"msg",[],"Runtime")
    fix = FixProposal("d","s","r","n")
    tests = a.generate_regression_tests(rca, fix)
    assert "def test_" in tests

def test_missing_api_key():
    env = {k:v for k,v in os.environ.items() if k != "OPENAI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            BobAgent()

def test_parse_json_fences(agent_mock):
    a, _ = agent_mock
    assert a._parse_json('```json\n{"k":1}\n```') == {"k": 1}

def test_parse_json_malformed(agent_mock):
    a, _ = agent_mock
    assert a._parse_json("garbage!!") == {}

def test_parse_json_embedded(agent_mock):
    a, _ = agent_mock
    assert a._parse_json('prefix {"x": 99} postfix').get("x") == 99
