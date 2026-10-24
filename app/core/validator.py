"""Safety validation gate: AST-equivalence checking and Ruff lint verification."""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional, Tuple
from app.core.models import ValidationResult


class DocstringAndAnnotationStripper(ast.NodeTransformer):
    """Strips docstrings and type annotations to verify pure AST equivalence."""

    def _strip_docstring_from_body(self, body_list):
        if body_list and isinstance(body_list[0], ast.Expr):
            val = body_list[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                body_list.pop(0)

    def visit_Module(self, node: ast.Module) -> ast.AST:
        self._strip_docstring_from_body(node.body)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self._strip_docstring_from_body(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self._strip_docstring_from_body(node.body)
        node.returns = None
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self.visit_FunctionDef(node)  # type: ignore[arg-type]


def verify_ast_equivalence(original_code: str, patched_code: str) -> Tuple[bool, Optional[str]]:
    """Verify that original and patched code have identical ASTs once docstrings/annotations are removed."""
    try:
        orig_tree = ast.parse(original_code)
    except SyntaxError as e:
        return False, f"Original code syntax error: {e}"

    try:
        patched_tree = ast.parse(patched_code)
    except SyntaxError as e:
        return False, f"Patched code syntax error: {e}"

    stripper = DocstringAndAnnotationStripper()
    clean_orig = stripper.visit(orig_tree)
    clean_patched = stripper.visit(patched_tree)

    dump_orig = ast.dump(clean_orig, include_attributes=False)
    dump_patched = ast.dump(clean_patched, include_attributes=False)

    if dump_orig != dump_patched:
        return False, "AST equivalence violation: Patched code alters executable statements or logic."

    return True, None


class Validator:
    """Per-file verification gate combining AST equivalence, syntax check, and Ruff."""

    def __init__(self, ruff_path: str = "ruff") -> None:
        self.ruff_path = ruff_path

    def _get_ruff_cmd(self, action: str, extra_args: Optional[list] = None) -> list:
        extra = extra_args or []
        ruff_bin = shutil.which("ruff")
        if ruff_bin:
            return [ruff_bin, action] + extra
        
        # Check adjacent to sys.executable (e.g. in venv/Scripts)
        candidate = os.path.join(os.path.dirname(sys.executable), "ruff.exe")
        if os.path.exists(candidate):
            return [candidate, action] + extra

        return [sys.executable, "-m", "ruff", action] + extra

    def run_ruff_check(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Run ruff check --select E9,F on the specified file."""
        try:
            cmd = self._get_ruff_cmd("check", ["--select", "E9,F", file_path])
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                return False, proc.stdout or proc.stderr
            return True, None
        except Exception as e:
            return False, f"Failed to execute ruff check: {e}"

    def run_ruff_format(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Run ruff format to clean up formatting on touched file."""
        try:
            cmd = self._get_ruff_cmd("format", [file_path])
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                return False, proc.stdout or proc.stderr
            return True, None
        except Exception as e:
            return False, f"Failed to execute ruff format: {e}"

    def validate_code_change(
        self,
        original_code: str,
        patched_code: str,
        file_path: str
    ) -> ValidationResult:
        """Execute full verification suite on a candidate file patch."""
        # 1. Syntax check
        try:
            ast.parse(patched_code)
        except SyntaxError as e:
            return ValidationResult(
                file_path=file_path,
                syntax_valid=False,
                ast_equivalent=False,
                ruff_check_passed=False,
                ruff_format_passed=False,
                error_message=f"SyntaxError in patched code: {e}",
                dropped_from_commit=True,
            )

        # 2. AST equivalence check (Invariant #3)
        is_equiv, equiv_err = verify_ast_equivalence(original_code, patched_code)
        if not is_equiv:
            return ValidationResult(
                file_path=file_path,
                syntax_valid=True,
                ast_equivalent=False,
                ruff_check_passed=False,
                ruff_format_passed=False,
                error_message=equiv_err,
                dropped_from_commit=True,
            )

        # 3. Write to temporary file for Ruff verification
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(patched_code)
            tmp_path = tmp.name

        try:
            # Format cleanly
            fmt_ok, _ = self.run_ruff_format(tmp_path)
            # Lint check
            check_ok, check_err = self.run_ruff_check(tmp_path)

            if not check_ok:
                return ValidationResult(
                    file_path=file_path,
                    syntax_valid=True,
                    ast_equivalent=True,
                    ruff_check_passed=False,
                    ruff_format_passed=fmt_ok,
                    error_message=f"Ruff lint violation: {check_err}",
                    dropped_from_commit=True,
                )

            return ValidationResult(
                file_path=file_path,
                syntax_valid=True,
                ast_equivalent=True,
                ruff_check_passed=True,
                ruff_format_passed=fmt_ok,
                error_message=None,
                dropped_from_commit=False,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
