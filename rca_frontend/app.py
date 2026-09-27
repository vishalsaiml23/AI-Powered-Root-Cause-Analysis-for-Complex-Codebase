"""
AI-Powered Root Cause Analysis — Streamlit Frontend
Multi-step wizard: Repository → Bug Description → Analysis Progress → Results
"""
import os
import sys
import time

import requests
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI-Powered Root Cause Analysis",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = "http://localhost:8000"
DEFAULT_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "sample_targets", "ecommerce_checkout")
)
DEFAULT_BUG = (
    "Invalid discount value during checkout — a ValueError is thrown in the tax "
    "calculation service when stacked promotions (coupon + voucher) are applied to a "
    "small cart. The error message is: 'Taxable subtotal cannot be negative'."
)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "repo_path" not in st.session_state:
    st.session_state.repo_path = DEFAULT_REPO
if "bug_description" not in st.session_state:
    st.session_state.bug_description = DEFAULT_BUG
if "result" not in st.session_state:
    st.session_state.result = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔍 AI-Powered Root Cause Analysis")
st.caption("Powered by IBM Bob 2.0 + GPT-4o · Hackathon Demo")

# Progress bar
step_labels = ["1 · Repository", "2 · Bug Description", "3 · Analysis", "4 · Results"]
cols = st.columns(4)
for i, (col, label) in enumerate(zip(cols, step_labels)):
    if i + 1 == st.session_state.step:
        col.markdown(f"**🟦 {label}**")
    elif i + 1 < st.session_state.step:
        col.markdown(f"✅ {label}")
    else:
        col.markdown(f"⬜ {label}")

st.divider()

# ---------------------------------------------------------------------------
# Step 1 — Repository Selection
# ---------------------------------------------------------------------------
if st.session_state.step == 1:
    st.subheader("Step 1: Select Repository")
    st.markdown(
        "Enter the path to the Python codebase you want to analyze. "
        "The sample e-commerce checkout repository is pre-filled."
    )
    repo_path = st.text_input(
        "Repository Path",
        value=st.session_state.repo_path,
        placeholder="/absolute/path/to/your/project",
    )
    if st.button("Next →", type="primary"):
        if not os.path.isdir(repo_path):
            st.error(f"Directory not found: `{repo_path}`")
        else:
            st.session_state.repo_path = repo_path
            st.session_state.step = 2
            st.rerun()

# ---------------------------------------------------------------------------
# Step 2 — Bug Description
# ---------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.subheader("Step 2: Describe the Bug")
    st.markdown(
        "Describe the symptom you observed. The more specific, the better the analysis."
    )
    bug_description = st.text_area(
        "Bug Description",
        value=st.session_state.bug_description,
        height=150,
    )
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("Analyze →", type="primary"):
            if not bug_description.strip():
                st.error("Please provide a bug description.")
            else:
                st.session_state.bug_description = bug_description
                st.session_state.step = 3
                st.rerun()

# ---------------------------------------------------------------------------
# Step 3 — Analysis Progress
# ---------------------------------------------------------------------------
elif st.session_state.step == 3:
    st.subheader("Step 3: Running AI Analysis…")

    pipeline_stages = [
        ("🔬", "AST Analysis", "Parsing Python files and extracting symbols"),
        ("🕸️", "Dependency Graph", "Building import and call edges"),
        ("🤖", "ErrorFlowAnalyzer", "Identifying root cause with GPT-4o"),
        ("🔧", "FixGenerator", "Generating minimal patch"),
        ("✅", "Verification", "Running pytest before and after fix"),
        ("🧪", "TestGenerator", "Synthesising regression test suite"),
        ("📄", "Report Assembly", "Compiling the final RCA report"),
    ]

    progress_bar = st.progress(0)
    status_container = st.empty()

    # Animate stages while waiting for the real request
    for i, (icon, stage, detail) in enumerate(pipeline_stages):
        status_container.markdown(f"**{icon} {stage}** — _{detail}_")
        progress_bar.progress((i + 1) / (len(pipeline_stages) + 1))
        time.sleep(0.4)

    status_container.markdown("**⏳ Calling AI backend…**")

    with st.spinner("Waiting for analysis to complete (this may take 30–90 seconds)…"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/analyze",
                json={
                    "repo_path": st.session_state.repo_path,
                    "bug_description": st.session_state.bug_description,
                },
                timeout=180,
            )
            if response.status_code == 200:
                st.session_state.result = response.json()
                progress_bar.progress(1.0)
                status_container.success("✅ Analysis complete!")
                time.sleep(0.8)
                st.session_state.step = 4
                st.rerun()
            else:
                try:
                    detail = response.json().get("detail", response.text)
                except Exception:
                    detail = response.text or f"HTTP {response.status_code}"
                st.error(f"Backend error {response.status_code}: {detail}")
                if st.button("← Back"):
                    st.session_state.step = 2
                    st.rerun()
        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to the backend. "
                "Make sure it is running with `python run_backend.py`."
            )
            if st.button("← Back"):
                st.session_state.step = 2
                st.rerun()
        except requests.exceptions.Timeout:
            st.error("Request timed out. The analysis took too long. Try again.")
            if st.button("← Back"):
                st.session_state.step = 2
                st.rerun()

# ---------------------------------------------------------------------------
# Step 4 — Results
# ---------------------------------------------------------------------------
elif st.session_state.step == 4 and st.session_state.result:
    r = st.session_state.result
    st.subheader("Step 4: Root Cause Analysis Results")

    tabs = st.tabs([
        "📋 Executive Summary",
        "🕸️ Dependency Graph",
        "🔧 Proposed Fix",
        "✅ Test Results",
        "📄 Full Report",
    ])

    # ---- Tab 1: Executive Summary ----
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        col1.metric("Culprit File", r["culprit_file"])
        col2.metric("Culprit Symbol", r["culprit_symbol"])
        col3.metric("Confidence", f"{r['confidence_score']}%")

        st.markdown("### Root Cause")
        st.info(r["root_cause_explanation"])

        st.markdown("### Fault Propagation Steps")
        for i, step in enumerate(r.get("propagation_steps", []), 1):
            st.markdown(f"**{i}.** {step}")

        st.markdown(f"**Symptom Class:** `{r.get('symptom_class', 'N/A')}`")
        st.markdown(f"**Session ID:** `{r['session_id']}` · Total duration: **{r['duration_seconds']}s**")

    # ---- Tab 2: Dependency Graph ----
    with tabs[1]:
        st.markdown("The Mermaid flowchart below shows the dependency graph. "
                    "The culprit file is highlighted in red.")
        # Extract mermaid from the report markdown
        report = r.get("report_markdown", "")
        mermaid_start = report.find("```mermaid")
        mermaid_end = report.find("```", mermaid_start + 10)
        if mermaid_start != -1 and mermaid_end != -1:
            mermaid_code = report[mermaid_start:mermaid_end + 3]
            # Render via mermaid.js CDN
            html = f"""
<div class="mermaid">
{mermaid_code[10:-3].strip()}
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'default'}});</script>
"""
            components.html(html, height=600, scrolling=True)
        else:
            st.info("Dependency graph not available in report.")

    # ---- Tab 3: Proposed Fix ----
    with tabs[2]:
        st.markdown("### Unified Diff")
        diff = r.get("diff_patch", "No diff available")
        st.code(diff, language="diff")

        st.markdown("### Fix Rationale")
        st.success(r.get("fix_rationale", ""))

        st.markdown("### Fixed Source")
        st.code(r.get("fixed_source", ""), language="python")

    # ---- Tab 4: Test Results ----
    with tabs[3]:
        pre = r["pre_test_result"]
        post = r["post_test_result"]

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Pre-Patch (Bug Active)")
            color = "🔴" if pre["failed"] > 0 else "🟢"
            st.metric("Tests Passed", pre["passed"])
            st.metric("Tests Failed", pre["failed"])
            st.markdown(f"**Exit Code:** `{pre['exit_code']}` {color}")
            with st.expander("pytest output"):
                st.text(pre["stdout"])

        with c2:
            st.markdown("#### Post-Patch (Fix Applied)")
            color = "🟢" if post["exit_code"] == 0 else "🔴"
            st.metric("Tests Passed", post["passed"], delta=post["passed"] - pre["passed"])
            st.metric("Tests Failed", post["failed"], delta=-(post["failed"]))
            st.markdown(f"**Exit Code:** `{post['exit_code']}` {color}")
            with st.expander("pytest output"):
                st.text(post["stdout"])

        st.markdown("### Generated Regression Tests")
        st.code(r.get("regression_tests", ""), language="python")

    # ---- Tab 5: Full Report ----
    with tabs[4]:
        report_md = r.get("report_markdown", "")
        st.markdown(report_md)
        st.divider()
        st.download_button(
            label="⬇️ Download Full Report (.md)",
            data=report_md,
            file_name=f"RCA_Report_{r['session_id']}.md",
            mime="text/markdown",
        )

    st.divider()
    if st.button("🔄 Start New Analysis"):
        st.session_state.step = 1
        st.session_state.result = None
        st.rerun()
