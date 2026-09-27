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

import openai
from rca_engine.ast_analyzer import ASTAnalyzer
from rca_engine.dependency_graph import DependencyGraph
from rca_engine.bob_agent import BobAgent, BobAgentCoordinator, RCAResult, FixProposal
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

    # --- 3. Root cause analysis + fix generation ---
    # Try GPT-4o first; fall back to local BobAgentCoordinator if quota is exhausted
    engine = VerificationEngine()
    try:
        agent = BobAgent()
        rca_result = agent.analyze_root_cause(graph_dict, request.bug_description, source_files)

        culprit_source = source_files.get(rca_result.culprit_file, "")
        if not culprit_source:
            for path, src in source_files.items():
                if rca_result.culprit_file in path:
                    culprit_source = src
                    rca_result.culprit_file = path
                    break

        fix_proposal = agent.generate_fix(rca_result, culprit_source)
        regression_tests = agent.generate_regression_tests(rca_result, fix_proposal)

    except (openai.RateLimitError, openai.AuthenticationError, EnvironmentError):
        # Fall back to local hardcoded coordinator (no API key needed)
        from rca_engine.ast_analyzer import CodebaseScanner
        coordinator = BobAgentCoordinator(repo_path)
        coordinator.initialize_with_analyses(CodebaseScanner(repo_path).scan())
        result = coordinator.run_full_rca(request.bug_description)

        a = result["analysis"]
        p = result["patch"]
        rca_result = RCAResult(
            culprit_file=a["culprit_file"],
            culprit_symbol=a["culprit_symbol"],
            culprit_line=a["line_number"],
            confidence_score=int(a["confidence_score"] * 100),
            root_cause_explanation=a["root_cause_explanation"],
            propagation_steps=a["fault_chain"],
            symptom_class=a["error_symptom"],
        )
        fix_proposal = FixProposal(
            diff_patch=p["unified_diff"],
            fixed_source=p["full_fixed_file"],
            rationale=p["explanation"],
        )
        regression_tests = result["test_cases"]
        culprit_source = p["full_fixed_file"]

    # --- 4. Baseline pytest run ---
    culprit_source_original = source_files.get(rca_result.culprit_file, "")
    if not culprit_source_original:
        for path, src in source_files.items():
            if rca_result.culprit_file in path:
                culprit_source_original = src
                rca_result.culprit_file = path
                break
    culprit_source = culprit_source_original

    baseline = engine.run_baseline(repo_path)

    # --- 5. Apply fix and verify ---
    culprit_full_path = os.path.join(repo_path, rca_result.culprit_file)
    if not os.path.exists(culprit_full_path):
        for root, _, files in os.walk(repo_path):
            for f in files:
                if rca_result.culprit_file in f or f in rca_result.culprit_file:
                    culprit_full_path = os.path.join(root, f)
                    break

    verified = engine.apply_and_verify(culprit_full_path, fix_proposal.fixed_source, repo_path)
    engine.revert(culprit_full_path, culprit_source)

    # --- 8. Report ---
    from rca_engine.dependency_graph import CodeDependencyGraph
    mermaid_graph = CodeDependencyGraph().generate_mermaid()

    rca_payload = {
        "analysis": {
            "culprit_file": rca_result.culprit_file,
            "culprit_symbol": rca_result.culprit_symbol,
            "line_number": rca_result.culprit_line,
            "confidence_score": rca_result.confidence_score / 100.0,
            "root_cause_explanation": rca_result.root_cause_explanation,
            "error_symptom": rca_result.symptom_class,
            "fault_chain": rca_result.propagation_steps,
        },
        "patch": {
            "file_path": rca_result.culprit_file,
            "unified_diff": fix_proposal.diff_patch,
            "explanation": fix_proposal.rationale,
            "original_code_snippet": "",
            "fixed_code_snippet": "",
            "full_fixed_file": fix_proposal.fixed_source,
        },
        "mermaid_graph": mermaid_graph,
        "test_cases": regression_tests,
        "session_logs": [],
    }
    verification_payload = {
        "status": "VERIFIED_SUCCESS" if verified.exit_code == 0 else "FAILED",
        "duration_total": verified.duration_seconds,
        "pre_patch": {"passed": baseline.exit_code == 0},
        "post_patch": {"passed": verified.exit_code == 0},
    }
    report_markdown = ReportGenerator.generate_markdown(rca_payload, verification_payload)

    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    ReportGenerator.save_report(report_markdown, reports_dir, f"RCA_{session_id}.md")

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
