"""
FastAPI Backend for AI-Powered Root Cause Analysis.

Exposes two endpoints:
  GET  /health   - liveness check
  POST /analyze  - full RCA pipeline
"""
from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Ensure the project root is on the path so rca_engine imports work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rca_engine.ast_analyzer import ASTAnalyzer
from rca_engine.dependency_graph import DependencyGraph
from rca_engine.bob_agent import BobAgent, RCAResult, FixProposal
from rca_engine.verification_engine import VerificationEngine
from rca_engine.report_generator import ReportGenerator

app = FastAPI(
    title="AI-Powered RCA API",
    description="Root Cause Analysis powered by IBM Bob 2.0 + GPT-4o",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    repo_path: str
    bug_description: str


class TestResultModel(BaseModel):
    passed: int
    failed: int
    errors: int
    exit_code: int
    stdout: str
    duration_seconds: float


class AnalyzeResponse(BaseModel):
    session_id: str
    culprit_file: str
    culprit_symbol: str
    culprit_line: int
    confidence_score: int
    root_cause_explanation: str
    propagation_steps: List[str]
    symptom_class: str
    diff_patch: str
    fixed_source: str
    fix_rationale: str
    pre_test_result: TestResultModel
    post_test_result: TestResultModel
    regression_tests: str
    report_markdown: str
    duration_seconds: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    """
    Run the full RCA pipeline:
      1. AST analysis
      2. Dependency graph
      3. LLM root cause identification (GPT-4o)
      4. LLM fix generation
      5. pytest baseline (pre-fix)
      6. pytest verification (post-fix)
      7. LLM regression test generation
      8. Report assembly
    """
    t0 = time.time()
    session_id = f"bob-rca-{int(t0)}"

    # Check API key early to give a clear error
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY environment variable is not set. "
                   "Set it before starting the backend.",
        )

    repo_path = os.path.abspath(request.repo_path)
    if not os.path.isdir(repo_path):
        raise HTTPException(
            status_code=400,
            detail=f"Repository path does not exist: {repo_path}",
        )

    # --- 1. AST analysis ---
    analyzer = ASTAnalyzer()
    symbols = analyzer.analyze(repo_path)
    if not symbols:
        raise HTTPException(status_code=400, detail="No Python symbols found in the given path.")

    # --- 2. Dependency graph ---
    graph = DependencyGraph()
    graph.build(symbols, repo_path)
    graph_dict = graph.get_graph_dict()
    source_files = graph.get_source_files()

    # --- 3. Root cause analysis ---
    agent = BobAgent()
    rca_result = agent.analyze_root_cause(graph_dict, request.bug_description, source_files)

    # --- 4. Fix generation ---
    culprit_source = source_files.get(rca_result.culprit_file, "")
    if not culprit_source:
        # Try to find by basename
        for path, src in source_files.items():
            if rca_result.culprit_file in path:
                culprit_source = src
                rca_result.culprit_file = path
                break

    fix_proposal = agent.generate_fix(rca_result, culprit_source)

    # --- 5. Baseline pytest run ---
    engine = VerificationEngine()
    baseline = engine.run_baseline(repo_path)

    # --- 6. Apply fix and verify ---
    culprit_full_path = os.path.join(repo_path, rca_result.culprit_file)
    if not os.path.exists(culprit_full_path):
        # try searching
        for root, _, files in os.walk(repo_path):
            for f in files:
                if rca_result.culprit_file in f or f in rca_result.culprit_file:
                    culprit_full_path = os.path.join(root, f)
                    break

    verified = engine.apply_and_verify(culprit_full_path, fix_proposal.fixed_source, repo_path)

    # Revert after verification (keep the file in original buggy state for demo repeatability)
    engine.revert(culprit_full_path, culprit_source)

    # --- 7. Regression tests ---
    regression_tests = agent.generate_regression_tests(rca_result, fix_proposal)

    # --- 8. Report ---
    reporter = ReportGenerator()
    report_markdown = reporter.generate(
        rca_result=rca_result,
        fix_proposal=fix_proposal,
        baseline_result=baseline,
        verified_result=verified,
        regression_tests_source=regression_tests,
        graph_dict=graph_dict,
        session_id=session_id,
    )

    # Save the report
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    reporter.save(report_markdown, os.path.join(reports_dir, f"RCA_{session_id}.md"))

    total_duration = round(time.time() - t0, 1)

    return AnalyzeResponse(
        session_id=session_id,
        culprit_file=rca_result.culprit_file,
        culprit_symbol=rca_result.culprit_symbol,
        culprit_line=rca_result.culprit_line,
        confidence_score=rca_result.confidence_score,
        root_cause_explanation=rca_result.root_cause_explanation,
        propagation_steps=rca_result.propagation_steps,
        symptom_class=rca_result.symptom_class,
        diff_patch=fix_proposal.diff_patch,
        fixed_source=fix_proposal.fixed_source,
        fix_rationale=fix_proposal.rationale,
        pre_test_result=TestResultModel(
            passed=baseline.passed, failed=baseline.failed, errors=baseline.errors,
            exit_code=baseline.exit_code, stdout=baseline.stdout,
            duration_seconds=baseline.duration_seconds,
        ),
        post_test_result=TestResultModel(
            passed=verified.passed, failed=verified.failed, errors=verified.errors,
            exit_code=verified.exit_code, stdout=verified.stdout,
            duration_seconds=verified.duration_seconds,
        ),
        regression_tests=regression_tests,
        report_markdown=report_markdown,
        duration_seconds=total_duration,
    )
