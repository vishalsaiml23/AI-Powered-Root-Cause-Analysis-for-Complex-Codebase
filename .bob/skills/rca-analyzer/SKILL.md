---
name: rca-analyzer
description: >-
  Use when the user wants to perform a manual root cause analysis on a Python
  codebase using Bob tools. Walks through dependency tracing, fault localization,
  fix proposal, and verification step by step.
---

# RCA Analyzer Skill

When activated, follow these steps in order to perform a manual root cause analysis.

## Step 1 - Understand the Bug Report

Ask the user (or read from context) for:
- The observed error message or unexpected behavior.
- The file or module where the error surfaces.
- Any stack trace or test output available.

## Step 2 - Map the Codebase Structure

Use `GetSymbolsOverview` on each relevant file to extract classes, functions, and methods.
Use `FindSymbol` to locate the exact definition of any symbol mentioned in the error.

## Step 3 - Trace Import Dependencies

Use `grep` to find all `import` and `from ... import` statements that reference the files
involved in the bug.
Build a mental import graph: which file imports which, and what symbols are shared.

## Step 4 - Trace the Call Chain

Starting from the error surface (e.g. the function that raises the exception), trace backward:
- Who calls this function?
- What arguments does it receive?
- Where do those argument values originate?

Use `FindReferencingSymbols` to find all call sites of suspicious functions.
Use `read_file` with line ranges to read the relevant sections of each file.

## Step 5 - Identify the Root Cause

State your diagnosis:
- Culprit file and line number.
- Culprit symbol (function/method name).
- Confidence score (0-100%).
- Root cause explanation in one sentence.
- Propagation chain (ordered list of steps from root cause to symptom).

## Step 6 - Propose the Minimal Fix

Using `read_file` to confirm the exact buggy line(s), propose the minimal change:
- Show a before/after diff in a code block.
- Explain why this fix is correct and safe.
- Note any edge cases the fix handles.

## Step 7 - Verify

If the project has tests, use `execute_command` to run pytest before and after the fix:
  python -m pytest <test_dir> -v

Report:
- Pre-fix: N passed, M failed.
- Post-fix: all passed.

## Step 8 - Summarize

Produce a concise summary table:

| Attribute | Value |
|---|---|
| Culprit File | ... |
| Culprit Symbol | ... |
| Line Number | ... |
| Confidence | ...% |
| Fix Applied | Yes / No |
| Tests After Fix | N/N passed |
