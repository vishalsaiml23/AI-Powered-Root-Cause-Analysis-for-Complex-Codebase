# AI-Powered Root Cause Analysis — Implementation Plan

## Top-Level Overview

**Goal:** Build a fully working, end-to-end AI-Powered Root Cause Analysis (RCA) tool that takes a Python codebase and a bug description as input, autonomously traces the fault, proposes a fix using the OpenAI GPT-4o API, verifies the fix with real pytest execution, generates regression tests, and presents the full journey through a multi-step Streamlit UI.

**Scope:** Python codebases only. The sample target is the `ecommerce_checkout` mini-application (cart, checkout, discount, tax) with the discount-clamp bug deliberately planted. The system must be runnable locally and demonstrate a measurable before/after scenario.

**Stack:**
- **Frontend:** Streamlit multi-step wizard (`rca_frontend/app.py`)
- **Backend:** FastAPI (`rca_backend/main.py`)
- **AI Core:** OpenAI GPT-4o via the `openai` Python SDK (`rca_engine/bob_agent.py`)
- **Analysis:** Python `ast` stdlib module (`rca_engine/ast_analyzer.py`, `rca_engine/dependency_graph.py`)
- **Verification:** `subprocess` + `pytest` (`rca_engine/verification_engine.py`)
- **Report:** Markdown generation (`rca_engine/report_generator.py`)

**Reference output:** `reports/DEMO_RCA_REPORT.md` defines the exact shape of the final report.

---

## Sub-Task 1: Sample Target — E-Commerce Checkout Codebase

**Status:** [ ] pending

### Intent
Implement the four Python modules that form the buggy e-commerce sample codebase. These are the files the RCA engine will analyze. They must be small (~50–100 lines each), realistic, and contain the known discount-clamp bug in `discount.py` exactly as described in the demo report.

### Expected Outcomes
- `sample_targets/ecommerce_checkout/cart.py` — `CartItem` dataclass and `Cart` class with `add_item`, `subtotal` methods.
- `sample_targets/ecommerce_checkout/discount.py` — `calculate_discount(subtotal, coupon_code, voucher_code)` with the bug: total discount is returned without clamping to subtotal.
- `sample_targets/ecommerce_checkout/tax.py` — `calculate_sales_tax(taxable_amount, rate)` that raises `ValueError` on negative input.
- `sample_targets/ecommerce_checkout/checkout.py` — `CheckoutSummary` dataclass and `CheckoutService.process_checkout()` that wires cart → discount → tax → summary.
- `sample_targets/ecommerce_checkout/test_checkout.py` — 4 pytest tests: 2 that pass (standard checkout, small discount), 2 that fail (stacked discount exceeds subtotal, large voucher edge case) before the fix is applied.
- `sample_targets/ecommerce_checkout/__init__.py` — package imports exposing the key symbols.
- Running `pytest sample_targets/ecommerce_checkout/` pre-fix produces exactly 2 failures.

### Todo List
1. Implement `cart.py` with `CartItem` (item_id, name, price, quantity, total property) and `Cart` (items list, add_item, subtotal).
2. Implement `discount.py` with coupon registry (`SAVE10`=10%, `SAVE20`=20%, `VIP50`=50%) and voucher registry (`GIFT50`=$50, `BONUS100`=$100), and `calculate_discount` that accumulates discount WITHOUT the clamp — the bug.
3. Implement `tax.py` with `calculate_sales_tax(taxable_amount, rate=0.08)` that raises `ValueError` if `taxable_amount < 0`.
4. Implement `checkout.py` with `CheckoutSummary` (subtotal, discount_amount, taxable_subtotal, tax_amount, final_total) and `CheckoutService.process_checkout`.
5. Implement `test_checkout.py` with exactly 4 tests that match the bug scenario described in the demo report.
6. Populate `__init__.py` to re-export `Cart`, `CartItem`, `CheckoutService`, `CheckoutSummary`, `calculate_discount`, `calculate_sales_tax`.
7. Verify pre-fix run: `pytest sample_targets/ecommerce_checkout/ -v` → 2 pass, 2 fail.

### Relevant Context
- Demo report section 2 defines the exact class/function/method names and the fault propagation chain.
- Demo report section 3 shows the precise bug line and the correct fix (do NOT apply the fix in this sub-task — the bug must remain planted).
- Demo report section 5 shows the regression test suite structure (generated later by the agent — `test_checkout.py` is separate from those).

---

## Sub-Task 2: AST Analyzer & Dependency Graph

**Status:** [ ] pending

### Intent
Build the static analysis layer that parses Python source files, extracts symbols (classes, functions, methods), and constructs a dependency graph (import edges + call edges). This is the foundation that the RCA engine uses to identify how a bug propagates through the codebase.

### Expected Outcomes
- `rca_engine/ast_analyzer.py` — `ASTAnalyzer` class that accepts a directory path and returns a list of `SymbolNode` objects (file, name, kind, line_number, source_snippet).
- `rca_engine/dependency_graph.py` — `DependencyGraph` class that accepts the `ASTAnalyzer` output and builds edges: import edges (file A imports file B) and call edges (function A calls function B). Exposes `get_graph_dict()` returning a JSON-serializable adjacency structure.
- `tests/test_ast_analyzer.py` — tests covering: symbol extraction from a small inline Python snippet, correct identification of class vs function vs method kinds.
- `tests/test_dependency_graph.py` — tests covering: import edge detection, call edge detection on the sample ecommerce checkout files.

### Todo List
1. Define `SymbolNode` as a dataclass in `ast_analyzer.py` (fields: file_path, name, qualified_name, kind, line_number, source_snippet).
2. Implement `ASTAnalyzer.analyze(repo_path: str) -> list[SymbolNode]` using Python's stdlib `ast` module to walk all `.py` files.
3. Implement `DependencyGraph.build(symbols: list[SymbolNode], repo_path: str)` using `ast.Import` / `ast.ImportFrom` nodes for import edges and `ast.Call` nodes for call edges.
4. Implement `DependencyGraph.get_graph_dict()` returning `{"nodes": [...], "edges": [...]}`.
5. Write `tests/test_ast_analyzer.py` — at minimum test that analyzing `sample_targets/ecommerce_checkout/` extracts `Cart`, `CartItem`, `calculate_discount`, `calculate_sales_tax`, `CheckoutService`.
6. Write `tests/test_dependency_graph.py` — test that checkout.py → discount.py import edge is detected.
7. Run `pytest tests/test_ast_analyzer.py tests/test_dependency_graph.py` → all pass.

### Relevant Context
- Demo report section 2 (Fault Propagation Chain) shows the exact nodes and edges the graph must contain for the ecommerce sample.
- Use only Python stdlib `ast` — no third-party tree-sitter required for the prototype.

---

## Sub-Task 3: Bob Agent (GPT-4o Orchestration)

**Status:** [ ] pending

### Intent
Build the AI orchestration layer that takes the dependency graph and bug description, calls GPT-4o to identify the root cause, propose a fix, and generate regression tests. This is the "Bob 2.0 agent core" — implemented as a real LLM API integration using the `openai` Python SDK.

### Expected Outcomes
- `rca_engine/bob_agent.py` — `BobAgent` class with:
  - `analyze_root_cause(graph_dict, bug_description, source_files) -> RCAResult`
  - `generate_fix(rca_result, target_file_source) -> FixProposal`
  - `generate_regression_tests(rca_result, fix_proposal) -> str` (Python test source code)
- `RCAResult` dataclass: culprit_file, culprit_symbol, culprit_line, confidence_score, root_cause_explanation, propagation_steps.
- `FixProposal` dataclass: diff_patch, fixed_source, rationale.
- `tests/test_bob_agent.py` — unit tests that mock the OpenAI client so no real API key is needed during testing.
- OpenAI API key is read from the environment variable `OPENAI_API_KEY`.

### Todo List
1. Define `RCAResult` and `FixProposal` dataclasses in `bob_agent.py`.
2. Implement `BobAgent.__init__` that initializes `openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])`.
3. Implement `analyze_root_cause`: build a system prompt describing the agent's role, a user message containing the serialized graph and bug description, call `gpt-4o` with structured JSON output, parse and return `RCAResult`.
4. Implement `generate_fix`: call GPT-4o with the culprit file's source and the RCA result, request a minimal unified diff + fixed source.
5. Implement `generate_regression_tests`: call GPT-4o to write 3–5 pytest test functions targeting the identified defect and its edge cases.
6. Write `tests/test_bob_agent.py` — mock `openai.OpenAI`, assert correct prompt construction and response parsing.
7. Run `pytest tests/test_bob_agent.py` → all pass (mocked, no API key required).

### Relevant Context
- Demo report section 5 shows the expected shape of generated regression tests.
- Demo report section 6 shows the 4 conceptual sub-agents (DependencyTracer, ErrorFlowAnalyzer, FixGenerator, TestGenerator) — implement these as sequential GPT-4o calls within the single `BobAgent` class.
- Keep prompts concise: the graph serialization must be compact enough to fit in context.

---

## Sub-Task 4: Verification Engine

**Status:** [ ] pending

### Intent
Build the module that applies a proposed fix to the target file, runs pytest against the affected directory, captures the output, then optionally reverts the file. This gives the system its measurable before/after test results.

### Expected Outcomes
- `rca_engine/verification_engine.py` — `VerificationEngine` class with:
  - `run_baseline(test_dir: str) -> TestRunResult` — run pytest before any fix.
  - `apply_and_verify(target_file: str, fixed_source: str, test_dir: str) -> TestRunResult` — write the fixed source to disk, run pytest, return result.
  - `revert(target_file: str, original_source: str)` — restore the original file.
- `TestRunResult` dataclass: passed, failed, errors, exit_code, stdout, duration_seconds.
- `tests/test_verification_engine.py` — tests that use `tmp_path` (pytest fixture) to run real pytest on a minimal inline test file without touching the sample target.

### Todo List
1. Define `TestRunResult` dataclass.
2. Implement `VerificationEngine.run_baseline(test_dir)` using `subprocess.run(["pytest", test_dir, "-v", "--tb=short"], capture_output=True)` and parsing the output.
3. Implement `VerificationEngine.apply_and_verify(target_file, fixed_source, test_dir)` — write fixed_source, call run_baseline, return result.
4. Implement `VerificationEngine.revert(target_file, original_source)`.
5. Write `tests/test_verification_engine.py` — create a temp dir with a minimal buggy Python file + test, verify baseline fails, apply fix, verify passes.
6. Run `pytest tests/test_verification_engine.py` → all pass.

### Relevant Context
- Demo report section 4 shows the exact pytest output format expected (pre-patch: 2 fail, post-patch: 4 pass).
- Parse `N passed`, `N failed` from pytest's summary line using a simple regex.

---

## Sub-Task 5: Report Generator

**Status:** [ ] pending

### Intent
Build the module that assembles all artifacts (RCA result, fix proposal, test results, regression tests) into the final markdown report, matching the structure of `reports/DEMO_RCA_REPORT.md`.

### Expected Outcomes
- `rca_engine/report_generator.py` — `ReportGenerator.generate(rca_result, fix_proposal, baseline_result, verified_result, regression_tests_source, session_id) -> str` returns a markdown string.
- The markdown output must include: executive summary table, mermaid fault propagation flowchart, unified diff patch block, pre/post test result table, regression test code block, agent audit trail table.
- The report can be saved to `reports/` as a `.md` file.

### Todo List
1. Implement `ReportGenerator.generate(...)` producing all 6 sections from the demo report.
2. Build the mermaid flowchart dynamically from the `DependencyGraph` output (use the graph nodes/edges to emit `flowchart TD` nodes and edges).
3. Format the diff patch from `FixProposal.diff_patch`.
4. Include the regression test source code verbatim in a fenced Python block.
5. Add a `save(report_markdown: str, output_path: str)` helper that writes the file.

### Relevant Context
- `reports/DEMO_RCA_REPORT.md` is the exact structural template — every section heading and table column name must match.
- Session ID should be generated as `f"bob-rca-{int(time.time())}"`.

---

## Sub-Task 6: FastAPI Backend

**Status:** [ ] pending

### Intent
Build the FastAPI application that orchestrates the full RCA pipeline as a REST API. The Streamlit frontend calls this backend. Using a REST boundary keeps the UI and the analysis engine independently runnable and testable.

### Expected Outcomes
- `rca_backend/main.py` — FastAPI app with:
  - `POST /analyze` — accepts `{ repo_path: str, bug_description: str }`, runs the full pipeline (AST → graph → BobAgent → VerificationEngine → ReportGenerator), returns the full RCA result as JSON.
  - `GET /health` — returns `{ "status": "ok" }`.
- Response model includes all fields needed by the frontend: culprit_file, culprit_symbol, root_cause_explanation, diff_patch, pre_test_result, post_test_result, report_markdown.
- `run_backend.py` — starts the backend with `uvicorn rca_backend.main:app --reload --port 8000`.

### Todo List
1. Define Pydantic request/response models for `POST /analyze`.
2. Implement the `/analyze` endpoint: instantiate `ASTAnalyzer`, `DependencyGraph`, `BobAgent`, `VerificationEngine`, `ReportGenerator`; call them in sequence; return the assembled response.
3. Add `GET /health`.
4. Implement `run_backend.py` using `uvicorn.run`.
5. Handle `OPENAI_API_KEY` not set: return HTTP 503 with a clear error message.

### Relevant Context
- Keep the analysis synchronous for the prototype (no async task queue needed).
- The pipeline order: `ASTAnalyzer.analyze()` → `DependencyGraph.build()` → `BobAgent.analyze_root_cause()` → `BobAgent.generate_fix()` → `BobAgent.generate_regression_tests()` → `VerificationEngine.run_baseline()` → `VerificationEngine.apply_and_verify()` → `ReportGenerator.generate()`.

---

## Sub-Task 7: Streamlit Frontend

**Status:** [ ] pending

### Intent
Build the multi-step Streamlit wizard that guides a developer through the full RCA workflow with a clean, demo-ready UI.

### Expected Outcomes
- `rca_frontend/app.py` — 4-step Streamlit wizard:
  - **Step 1 — Repository:** Text input for repo path (pre-filled with sample target path), "Analyze" button.
  - **Step 2 — Bug Description:** Text area for bug description (pre-filled with "Invalid discount value during checkout — ValueError in tax calculation").
  - **Step 3 — Analysis Progress:** Spinner / status messages while calling the backend; show each pipeline stage as it completes.
  - **Step 4 — Results:** Tabbed view with: (a) Executive Summary card, (b) Fault Propagation diagram (render Mermaid via `st.markdown`), (c) Proposed Fix diff, (d) Test Results before/after table, (e) Full Report download button.
- `run_frontend.py` — starts the frontend with `streamlit run rca_frontend/app.py --server.port 8501`.

### Todo List
1. Implement step state management using `st.session_state` to track which wizard step is active.
2. Implement Step 1 repo path input with default pointing to `sample_targets/ecommerce_checkout`.
3. Implement Step 2 bug description textarea.
4. Implement Step 3 backend call using `requests.post("http://localhost:8000/analyze", json={...})` with a spinner.
5. Implement Step 4 tabbed results view rendering all sections from the API response.
6. Add "Download Full Report" button using `st.download_button` with the markdown report as the payload.
7. Implement `run_frontend.py`.

### Relevant Context
- The `ui-plan.md` file is currently empty and can be used for any additional frontend notes.
- Mermaid diagrams render in Streamlit via `st.markdown(mermaid_block, unsafe_allow_html=True)` with a custom HTML wrapper using the mermaid.js CDN.

---

## Sub-Task 8: Bob Custom Mode & Skill

**Status:** [ ] pending

### Intent
Define the Bob custom mode and the `rca-analyzer` skill so that the project is self-contained as a Bob demo — developers opening this project in Bob get an RCA-specialized persona and a skill they can invoke directly from the Bob chat.

### Expected Outcomes
- `ai-root-cause-analysis/.bob/custom_modes.yaml` — defines an `rca-analyst` mode with a role focused on root cause analysis, bug tracing, and fix generation.
- `ai-root-cause-analysis/.bob/skills/rca-analyzer/SKILL.md` — skill instructions that tell Bob how to walk through the RCA process manually using Bob's own tools (read files, trace dependencies, identify culprits, propose fixes).
- `ai-root-cause-analysis/.bob/mcp.json` — empty JSON config (no MCP servers needed for the prototype; file exists to confirm no tools are configured).

### Todo List
1. Write `custom_modes.yaml` defining the `rca-analyst` mode.
2. Write `SKILL.md` with step-by-step instructions Bob follows when the skill is activated.
3. Write `mcp.json` as `{}` (empty config).

### Relevant Context
- Use the `create-mode` and `create-skill` Bob skills for guidance on schema/frontmatter.
- The mode should emphasize: read-only codebase analysis, dependency tracing, root cause identification, minimal fix proposals.

---

## Sub-Task 9: Documentation & Hackathon Artifacts

**Status:** [ ] pending

### Intent
Write all missing documentation files that are required for the hackathon submission: README, demo script, and presentation slides. These are currently empty placeholder files.

### Expected Outcomes
- `README.md` — covers project purpose, architecture diagram (ASCII), setup instructions (pip install, env vars), how to run, and example output.
- `HACKATHON_DEMO_SCRIPT.md` — 3–5 minute narrative script with exact steps, expected outputs, and the before/after timing claim ("45 minutes → 8 minutes").
- `PRESENTATION_SLIDES.md` — slide deck outline in markdown: problem statement, solution architecture, live demo flow, business value, IBM Bob 2.0 differentiator, judging criteria alignment.

### Todo List
1. Write `README.md` with setup, run, and architecture sections.
2. Write `HACKATHON_DEMO_SCRIPT.md` with the full narrative and stage directions.
3. Write `PRESENTATION_SLIDES.md` with slide-by-slide content.

### Relevant Context
- The demo report (`reports/DEMO_RCA_REPORT.md`) provides all concrete numbers and output to reference in the script and slides.
- The "IBM Bob 2.0" angle for the slides: Bob is used as the planning and implementation IDE, with the LLM API (GPT-4o) acting as the runtime AI core.

---

## Sub-Task 10: End-to-End Validation

**Status:** [ ] pending

### Intent
Run the full system end-to-end against the sample target to verify the demo works reliably before the hackathon. Catch integration issues across all layers.

### Expected Outcomes
- All unit tests pass: `pytest tests/ -v`
- Backend starts without error: `python run_backend.py`
- Frontend starts without error: `python run_frontend.py`
- Submitting the ecommerce_checkout path + bug description through the UI returns a fully populated results page
- The downloaded report matches the structure of `reports/DEMO_RCA_REPORT.md`
- Pre-fix test run shows 2 failures; post-fix shows 4 passes

### Todo List
1. Run `pytest tests/ -v` — all pass.
2. Run `pytest sample_targets/ecommerce_checkout/ -v` — confirm exactly 2 failures (bug is still planted).
3. Start backend, start frontend, run the full wizard flow.
4. Download the generated report and compare structure against `reports/DEMO_RCA_REPORT.md`.
5. Confirm the generated regression tests (from GPT-4o) are valid Python and pass after the fix is applied.
6. Document any issues found and fix them before marking this sub-task complete.

### Relevant Context
- This sub-task should be done last, after all other sub-tasks are complete.
- The `OPENAI_API_KEY` environment variable must be set before running the backend.
