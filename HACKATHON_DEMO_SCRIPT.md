# Hackathon Demo Script
## AI-Powered Root Cause Analysis for Complex Codebases
### 3-5 Minute Narrative

---

## Setup (Before Demo - Do This First)

```powershell
# Terminal 1
$env:OPENAI_API_KEY = "sk-YOUR-KEY"
cd ai-root-cause-analysis
python run_backend.py

# Terminal 2
cd ai-root-cause-analysis
python run_frontend.py
```

Confirm pre-demo state (browser at http://localhost:8501):
- [ ] Backend health: `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] Frontend loads on Step 1
- [ ] Sample ecommerce_checkout path is pre-filled
- [ ] Run `pytest sample_targets/ecommerce_checkout/ -v` and show 2 failures

---

## Demo Narrative (speak aloud)

---

### MINUTE 1 - The Problem

> "Imagine you are a developer at 4pm on a Friday. Your QA team just filed a critical bug:
> 'The checkout is broken when customers stack a coupon with a gift voucher.'
> The stack trace says: **ValueError: Taxable subtotal cannot be negative.**
> But the error is thrown in the tax module - not in the discount module where the real problem lives.
> Without AI, a developer would spend 45 minutes grepping through files, adding print statements,
> and piecing together how the discount, checkout, and tax modules interact.
> We can do this in under 8 minutes."

**[Show the test failures]** Run:

```bash
python -m pytest sample_targets/ecommerce_checkout/ -v
```

Output shows: `test_stacked_discount_exceeds_subtotal FAILED` and `test_large_voucher_zero_balance_edge_case FAILED`

---

### MINUTE 2 - Input the Bug

**[Switch to browser - Step 1]**

> "I open the AI Root Cause Analysis tool. The repository is already pointed at our
> ecommerce checkout service. I click Next."

**[Step 2 - Bug Description]**

> "I type the bug description exactly as I received it from QA. I don't need to know
> what caused it - just what I observed. I click Analyze."

---

### MINUTE 3 - The AI Pipeline Runs

**[Step 3 - Analysis Progress screen]**

> "Watch the pipeline execute. First, an AST analyzer parses every Python file and
> extracts 25 symbols. Then a dependency graph builder maps the import and call edges
> between them. Then IBM Bob's AI core - the ErrorFlowAnalyzer - sends this entire
> structured context to GPT-4o and asks: given this dependency graph and this bug
> description, what is the root cause?"
>
> "Notice: we are not just throwing the source code at the LLM and hoping for the best.
> We are sending a structured, semantic graph. That is the architectural difference."

---

### MINUTE 4 - Results and Fix

**[Step 4 - Executive Summary tab]**

> "The AI identified: culprit file discount.py, culprit function calculate_discount,
> line 55, confidence 96%. The root cause: the discount function accumulates coupon
> and voucher values additively without ever checking whether the total exceeds
> the cart subtotal."

**[Fault Propagation tab]**

> "Here is the dependency graph with the faulty node highlighted in red. You can see
> exactly how the error propagates: discount.py produces a negative value, checkout.py
> passes it to tax.py, tax.py raises the ValueError."

**[Proposed Fix tab]**

> "The AI proposes a minimal one-line fix: wrap the return value in max(0, min(discount, subtotal)).
> This clamps the discount to the subtotal and prevents the negative value from ever reaching tax."

---

### MINUTE 5 - Verification and Wrap-Up

**[Test Results tab]**

> "This is the money shot. Before the fix: 2 tests passing, 2 failing.
> After the fix: 4 out of 4 passing. This was verified by actually running pytest
> in a subprocess - not simulated. Real tests. Real results."

**[Download the report]**

> "I click Download Report. I now have a complete, shareable Root Cause Analysis document:
> the dependency graph, the diff, the test results before and after, and a synthesised
> regression test suite to prevent this class of bug forever."

> "Total elapsed time: under 8 minutes. A senior developer doing this manually:
> 45 minutes minimum. That is an 82% reduction in diagnosis time."

---

## Key Talking Points for Judges

- **IBM Bob 2.0** was the IDE used to design and implement the entire system
  (Agent mode, plan files, sub-agents for submodule exploration)
- The `rca-analyst` custom mode and `rca-analyzer` skill in `.bob/` make the project
  a native Bob workspace
- The runtime AI is GPT-4o calling the OpenAI API - IBM Bob orchestrated the build,
  the product uses LLM autonomously at runtime
- The dependency graph approach is architecturally superior to naive "paste code into ChatGPT"
  - it provides structured semantic context
- The before/after pytest execution is REAL - not scripted output

---

## Fallback Plan (if API is unavailable)

Show the pre-generated report: `reports/DEMO_RCA_REPORT.md`
Walk through its sections manually while explaining what the system would have produced.
