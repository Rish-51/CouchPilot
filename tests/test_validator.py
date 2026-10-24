"""Unit tests for the safety validator gate and AST equivalence."""
import pytest
from app.core.validator import Validator, verify_ast_equivalence


def test_ast_equivalence_accepts_docstrings_and_annotations():
    original = (
        "def add(a, b):\n"
        "    return a + b\n"
    )
    patched = (
        "def add(a: int, b: int) -> int:\n"
        '    """Add two numbers together."""\n'
        "    return a + b\n"
    )
    is_equiv, err = verify_ast_equivalence(original, patched)
    assert is_equiv is True
    assert err is None


def test_ast_equivalence_rejection():
    """Safety Invariant #3: Body altering changes must be rejected."""
    original = (
        "def compute(x):\n"
        "    return x * 2\n"
    )
    # Patch sneakily changes the calculation or injects code
    body_altering_patch = (
        "def compute(x: int) -> int:\n"
        '    """Compute doubled value."""\n'
        "    return x * 3\n"
    )
    is_equiv, err = verify_ast_equivalence(original, body_altering_patch)
    assert is_equiv is False
    assert "AST equivalence violation" in err

    # Injected statement
    injected_stmt_patch = (
        "def compute(x: int) -> int:\n"
        '    """Compute doubled value."""\n'
        "    print('Logging telemetry')\n"
        "    return x * 2\n"
    )
    is_equiv2, err2 = verify_ast_equivalence(original, injected_stmt_patch)
    assert is_equiv2 is False
    assert "AST equivalence violation" in err2


def test_validator_full_flow(validator: Validator):
    orig = "def sub(a, b):\n    return a - b\n"
    clean_patch = (
        "def sub(a: int, b: int) -> int:\n"
        '    """Subtract b from a."""\n'
        "    return a - b\n"
    )
    res = validator.validate_code_change(orig, clean_patch, "math.py")
    assert res.syntax_valid is True
    assert res.ast_equivalent is True
    assert res.dropped_from_commit is False

    bad_patch = (
        "def sub(a, b):\n"
        "    return a - b + 10\n"
    )
    res_bad = validator.validate_code_change(orig, bad_patch, "math.py")
    assert res_bad.ast_equivalent is False
    assert res_bad.dropped_from_commit is True
