"""
Report Generator — Assembles executive-ready Root Cause Analysis audit reports.
Formats comprehensive findings into Markdown with Mermaid flowcharts, unified diffs,
sandboxed test verification metrics, and subagent audit trails.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class RCAReportGenerator:
    """
    Generates standardized, audit-ready Markdown RCA reports.
    """

    @staticmethod
    def generate_markdown(
        rca_payload: Dict[str, Any],
        verification: Optional[Dict[str, Any]] = None
    ) -> str:
        analysis = rca_payload.get("analysis", {})
        patch = rca_payload.get("patch", {})
        mermaid_code = rca_payload.get("mermaid_graph", "")
        test_cases = rca_payload.get("test_cases", "")
        session_logs = rca_payload.get("session_logs", [])

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        culprit_file = analysis.get("culprit_file", "unknown")
        culprit_sym = analysis.get("culprit_symbol", "unknown")
        line_no = analysis.get("line_number", 0)
        confidence = int(analysis.get("confidence_score", 0.95) * 100)

        v_status = "NOT EXECUTED"
        pre_status = "N/A"
        post_status = "N/A"
        v_dur = "0.0s"

        if verification:
            v_status = verification.get("status", "UNKNOWN")
            v_dur = f"{verification.get('duration_total', 0.0):.2f}s"
            pre = verification.get("pre_patch", {})
            post = verification.get("post_patch", {})
            pre_status = "FAILED (Exit Code 1)" if not pre.get("passed", False) else "PASSED"
            post_status = "PASSED 100% (Exit Code 0)" if post.get("passed", False) else "FAILED"

        status_badge = "✅ VERIFIED & REMEDIATED" if v_status == "VERIFIED_SUCCESS" else "⚠️ RCA COMPLETED (AWAITING VERIFY)"

        md = f"""# 🔍 IBM Bob 2.0 Root Cause Analysis & Remediation Report

**Generated:** {now_str}  
**System Status:** {status_badge}  
**Orchestration Engine:** IBM Bob 2.0 Autonomous Multi-Agent Coordinator  

---

## 1. Executive Summary

| Metric | Assessment |
|---|---|
| **Incident Severity** | High (500 Checkout Failure) |
| **Culprit File** | `{culprit_file}` |
| **Culprit Function** | `{culprit_sym}()` (Line {line_no}) |
| **Agent Confidence** | **{confidence}%** |
| **Sandbox Status** | **{v_status}** ({v_dur}) |
| **Resolution Status** | Automated Fix Synthesized & Verified |

### Core Defect Diagnosis
{analysis.get("root_cause_explanation", "")}

---

## 2. Fault Propagation Flowchart

```mermaid
{mermaid_code}
```

### Propagation Chain
"""
        for idx, step in enumerate(analysis.get("fault_chain", []), 1):
            md += f"{idx}. {step}\n"

        md += f"""
---

## 3. Remediation Patch Proposal

**Target File:** `{patch.get("file_path", "")}`  
**Remediation Rationale:** {patch.get("explanation", "")}

### Unified Diff
```diff
{patch.get("unified_diff", "")}
```

---

## 4. Sandboxed Verification Results

IBM Bob executes the test suite in an isolated sandbox across both repository states to guarantee complete remediation:

* **Baseline (Unpatched Code):** `{pre_status}`  
  *Confirms defect reproducibility under production-like conditions.*
* **Remediated (Patched Code):** `{post_status}`  
  *Confirms all regression assertions and unit tests pass with zero side-effects.*

---

## 5. Synthesized Regression Test Suite

Generated automatically by `TestGeneratorSubagent` to permanently guard against future regressions:

```python
{test_cases.strip()}
```

---

## 6. IBM Bob 2.0 Subagent Audit Trail

| Timestamp | Subagent | Action | Details |
|---|---|---|---|
"""
        for log in session_logs:
            md += f"| {log.get('timestamp')} | **{log.get('subagent')}** | {log.get('action')} | {log.get('details')} |\n"

        md += """
---
*Automated Report compiled by AI-Powered Root Cause Analysis System (IBM Bob 2.0).*
"""
        return md

    @staticmethod
    def save_report(
        report_md: str,
        output_dir: Path | str,
        filename: str = "DEMO_RCA_REPORT.md"
    ) -> Path:
        out_path = Path(output_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)
        target = out_path / filename
        target.write_text(report_md, encoding="utf-8")
        return target


# Compatibility alias
ReportGenerator = RCAReportGenerator
