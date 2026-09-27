"""Tests for VerificationEngine."""
import os, sys, textwrap, pytest
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from rca_engine.verification_engine import VerificationEngine, PytestRunResult

BUGGY = "def add(a, b):\n    return 0\n"
FIXED = "def add(a, b):\n    return a + b\n"
TESTS = "from module import add\ndef test_pos():\n    assert add(2,3)==5\ndef test_neg():\n    assert add(-1,-1)==-2\n"

def _setup(tmp_path, module_src):
    (tmp_path/"module.py").write_text(module_src)
    (tmp_path/"test_module.py").write_text(TESTS)
    (tmp_path/"conftest.py").write_text("")
    return str(tmp_path/"module.py"), str(tmp_path)

def test_baseline_fails_on_buggy(tmp_path):
    _, td = _setup(tmp_path, BUGGY)
    r = VerificationEngine().run_baseline(td)
    assert r.failed > 0 and r.exit_code != 0

def test_baseline_passes_on_correct(tmp_path):
    _, td = _setup(tmp_path, FIXED)
    r = VerificationEngine().run_baseline(td)
    assert r.passed == 2 and r.failed == 0

def test_apply_and_verify_turns_failures_to_pass(tmp_path):
    mf, td = _setup(tmp_path, BUGGY)
    engine = VerificationEngine()
    assert engine.run_baseline(td).failed > 0
    r = engine.apply_and_verify(mf, FIXED, td)
    assert r.exit_code == 0 and r.passed == 2

def test_revert_restores_file(tmp_path):
    mf, td = _setup(tmp_path, BUGGY)
    engine = VerificationEngine()
    engine.apply_and_verify(mf, FIXED, td)
    assert "return a + b" in open(mf).read()
    engine.revert(mf, BUGGY)
    assert "return 0" in open(mf).read()

def test_stdout_non_empty(tmp_path):
    _, td = _setup(tmp_path, BUGGY)
    r = VerificationEngine().run_baseline(td)
    assert len(r.stdout) > 0

def test_duration_positive(tmp_path):
    _, td = _setup(tmp_path, FIXED)
    r = VerificationEngine().run_baseline(td)
    assert r.duration_seconds > 0

def test_parse_summary():
    e = VerificationEngine()
    p,f,err = e._parse_summary("2 passed, 3 failed in 0.1s"); assert p==2 and f==3 and err==0
    p,f,err = e._parse_summary("4 passed in 0.06s"); assert p==4 and f==0
    p,f,err = e._parse_summary("1 error in 0.01s"); assert err==1
