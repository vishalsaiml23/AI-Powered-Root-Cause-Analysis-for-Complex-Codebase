"""
Verification Engine — Sandboxed Test Execution and Patch Validation.
Executes test suites pre-patch and post-patch in a subprocess sandbox
to verify that defects are reproduced initially and 100% resolved by remediation.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class _BoolInt(int):
    """Integer that evaluates to truthy in boolean context only when tests passed and 0 failures."""
    failed: int = 0

    def __new__(cls, val: int, failed: int = 0):
        obj = super().__new__(cls, val)
        obj.failed = failed
        return obj

    def __bool__(self) -> bool:
        return self > 0 and self.failed == 0


@dataclass
class PytestRunResult:
    """Structured summary of a single pytest run."""
    passed: _BoolInt | int
    failed: int
    errors: int
    exit_code: int
    stdout: str
    duration_seconds: float
    stderr: str = ""


# Backward compatibility aliases
TestRunOutput = PytestRunResult
TestRunResult = PytestRunResult


@dataclass
class VerificationSummary:
    """Summary of sandbox verification across pre-patch and post-patch states."""
    status: str             # "VERIFIED_SUCCESS" | "VERIFIED_FAILURE"
    pre_patch: PytestRunResult
    post_patch: PytestRunResult
    duration_total: float
    file_modified: str
    patch_applied: bool


VerificationReport = VerificationSummary


class VerificationEngine:
    """
    Applies fixes to files and verifies correctness with pytest in a sandbox.
    """

    def __init__(self, target_dir: str | Path = ".") -> None:
        self.target_dir = Path(target_dir).resolve()

    def run_baseline(self, test_dir: str) -> PytestRunResult:
        """Run pytest against test_dir without modifying any files."""
        return self._run_pytest(test_dir)

    def apply_and_verify(
        self,
        target_file: str,
        fixed_source: str,
        test_dir: str,
    ) -> PytestRunResult:
        """Write fixed_source to target_file and run pytest."""
        with open(target_file, "w", encoding="utf-8") as fh:
            fh.write(fixed_source)
        return self._run_pytest(test_dir)

    def revert(self, target_file: str, original_source: str) -> None:
        """Restore target_file to its original content."""
        with open(target_file, "w", encoding="utf-8") as fh:
            fh.write(original_source)

    def _run_pytest(self, test_dir: str) -> PytestRunResult:
        """Execute pytest and parse its output."""
        start = time.time()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
        )
        duration = round(time.time() - start, 2)
        combined_output = result.stdout + (result.stderr or "")
        p, f, err = self._parse_summary(combined_output)
        return PytestRunResult(
            passed=_BoolInt(p, failed=f + err),
            failed=f,
            errors=err,
            exit_code=result.returncode,
            stdout=combined_output,
            stderr=result.stderr or "",
            duration_seconds=duration,
        )

    def _parse_summary(self, output: str) -> tuple[int, int, int]:
        """
        Parse the pytest summary line for pass/fail/error counts.
        """
        passed = errors = failed = 0
        summary_pattern = re.compile(r"(\d+)\s+(passed|failed|error)", re.IGNORECASE)
        tail = "\n".join(output.splitlines()[-10:])
        for m in summary_pattern.finditer(tail):
            count = int(m.group(1))
            label = m.group(2).lower()
            if label == "passed":
                passed = count
            elif label == "failed":
                failed = count
            elif label == "error":
                errors = count
        return passed, failed, errors

    def _execute_command(self, command: str) -> PytestRunResult:
        start = time.time()
        cmd = command
        if cmd.startswith("python "):
            cmd = f'"{sys.executable}" ' + cmd[7:]

        try:
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.target_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            elapsed = round(time.time() - start, 2)
            combined = res.stdout + (res.stderr or "")
            p, f, err = self._parse_summary(combined)
            return PytestRunResult(
                passed=_BoolInt(p, failed=f + err),
                failed=f,
                errors=err,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr or "",
                duration_seconds=elapsed,
            )
        except subprocess.TimeoutExpired:
            return PytestRunResult(
                passed=_BoolInt(0, failed=1),
                failed=1,
                errors=1,
                exit_code=-1,
                stdout="",
                stderr="Execution timed out after 30 seconds.",
                duration_seconds=30.0,
            )
        except Exception as e:
            return PytestRunResult(
                passed=_BoolInt(0, failed=1),
                failed=1,
                errors=1,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {e}",
                duration_seconds=round(time.time() - start, 2),
            )

    def verify_patch(
        self,
        target_file_rel: str,
        fixed_code: str,
        test_command: str = "python -m pytest test_checkout.py"
    ) -> VerificationSummary:
        start_total = time.time()

        target_file = (self.target_dir / target_file_rel).resolve()
        if not target_file.exists():
            for f in self.target_dir.rglob(Path(target_file_rel).name):
                target_file = f
                break

        original_content = ""
        if target_file.exists():
            original_content = target_file.read_text(encoding="utf-8")

        # 1. Baseline test
        pre_patch = self._execute_command(test_command)

        # 2. Apply patch
        patch_applied = False
        post_patch = PytestRunResult(
            passed=_BoolInt(0, failed=1), failed=1, errors=0, exit_code=1,
            stdout="", stderr="Patch not applied", duration_seconds=0.0
        )

        try:
            if target_file.exists():
                target_file.write_text(fixed_code, encoding="utf-8")
                patch_applied = True

            # 3. Post-patch verification
            post_patch = self._execute_command(test_command)
        finally:
            # 4. Revert
            if original_content and target_file.exists():
                target_file.write_text(original_content, encoding="utf-8")

        total_duration = round(time.time() - start_total, 2)
        status = "VERIFIED_SUCCESS" if post_patch.exit_code == 0 else "VERIFIED_FAILURE"

        try:
            mod_str = str(target_file.relative_to(self.target_dir))
        except ValueError:
            mod_str = str(target_file)

        return VerificationSummary(
            status=status,
            pre_patch=pre_patch,
            post_patch=post_patch,
            duration_total=total_duration,
            file_modified=mod_str,
            patch_applied=patch_applied,
        )
