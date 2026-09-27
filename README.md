# AI-Powered Root Cause Analysis for Complex Codebases

> **IBM Bob 2.0 Hackathon Project**  
> Autonomously traces bugs, proposes fixes, and verifies them — in under 10 minutes.

---

## What It Does

Given a Python codebase and a bug description, this system:

1. **Parses** every `.py` file and builds a dependency graph (AST + import/call edges)
2. **Identifies** the root cause using GPT-4o (ErrorFlowAnalyzer role)
3. **Generates** a minimal code fix (FixGenerator role)
4. **Verifies** the fix by running pytest before and after
5. **Produces** a full RCA report with Mermaid flowchart, diff, and test results
6. **Synthesises** a regression test suite to prevent future regressions

---

## Architecture

```
Streamlit UI (port 8501)
      |
      | POST /analyze
      v
FastAPI Backend (port 8000)
      |
      +-- ASTAnalyzer        (stdlib ast)
      +-- DependencyGraph    (import + call edges)
      +-- BobAgent           (GPT-4o via openai SDK)
      |     +-- ErrorFlowAnalyzer  role
      |     +-- FixGenerator       role
      |     +-- TestGenerator      role
      +-- VerificationEngine (subprocess + pytest)
      +-- ReportGenerator    (markdown + Mermaid)
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- `pip install fastapi uvicorn streamlit openai requests`
- An OpenAI API key with GPT-4o access

### 1. Set your API key

```powershell
$env:OPENAI_API_KEY = "sk-..."   # PowerShell
```

```bash
export OPENAI_API_KEY="sk-..."   # bash / zsh
```

### 2. Start the backend

```bash
cd ai-root-cause-analysis
python run_backend.py
# Running on http://localhost:8000
```

### 3. Start the frontend

In a second terminal:

```bash
cd ai-root-cause-analysis
python run_frontend.py
# Running on http://localhost:8501
```

### 4. Run the demo

Open `http://localhost:8501` in your browser and follow the 4-step wizard:

1. **Repository** — pre-filled with `sample_targets/ecommerce_checkout`
2. **Bug Description** — pre-filled with the checkout ValueError scenario
3. **Analysis** — watch the pipeline run live
4. **Results** — view the root cause, fix diff, test results, and download the report

---

## Running Tests

```bash
cd ai-root-cause-analysis
python -m pytest tests/ -v
```

Expected: **33 passed**

---

## The Demo Scenario

The sample target (`sample_targets/ecommerce_checkout/`) has a deliberately planted bug:

**`discount.py` — `calculate_discount()` returns total discount without clamping it to the cart subtotal.**

When a 20% coupon (`SAVE20`) and a $50 gift voucher (`GIFT50`) are applied to a $60 cart:
- Combined discount = $62.00
- Taxable subtotal = **-$2.00** (impossible!)
- `calculate_sales_tax()` raises `ValueError: Taxable subtotal cannot be negative`

The AI system identifies the exact defect, proposes the one-line fix:

```python
# Before (buggy):
return round(total_discount, 2)

# After (fixed):
clamped_discount = max(0.0, min(total_discount, subtotal))
return round(clamped_discount, 2)
```

And verifies: 2 tests failing before → 4 tests passing after.

---

## Project Structure

```
ai-root-cause-analysis/
  rca_engine/
    ast_analyzer.py       # Symbol extraction via Python stdlib ast
    dependency_graph.py   # Import + call graph builder
    bob_agent.py          # GPT-4o orchestration (3 sequential LLM calls)
    verification_engine.py# pytest runner with apply/revert support
    report_generator.py   # Markdown + Mermaid report builder
  rca_backend/
    main.py               # FastAPI app with /health and /analyze endpoints
  rca_frontend/
    app.py                # Streamlit 4-step wizard
  sample_targets/
    ecommerce_checkout/   # Buggy demo codebase
  tests/                  # 33 unit tests (no API key required)
  reports/                # Auto-generated RCA reports
  .bob/
    custom_modes.yaml     # rca-analyst Bob mode
    skills/rca-analyzer/  # Manual RCA skill for Bob
```

---

## Environment Variables

| Variable | Required | Description |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Yes | OpenAI API key with GPT-4o access |

---

## IBM Bob 2.0 Integration

This project is built **with** IBM Bob 2.0 as the development IDE:

- The `rca-analyst` custom mode (`.bob/custom_modes.yaml`) gives Bob a root cause analysis persona
- The `rca-analyzer` skill (`.bob/skills/rca-analyzer/SKILL.md`) guides Bob through manual RCA
- The entire codebase was designed, implemented, and validated using Bob in Agent mode

The runtime AI backbone (GPT-4o API) provides autonomous analysis capability that runs without Bob being present.
