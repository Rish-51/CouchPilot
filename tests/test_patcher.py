"""Unit tests and golden-file verification for the Patcher."""
import pytest
from app.core.models import Patch
from app.core.patcher import Patcher
from app.core.scanner import Scanner


def test_bottom_to_top_patching(scanner: Scanner, patcher: Patcher):
    with open("sample_repo/calculator.py", "r", encoding="utf-8") as f:
        original = f.read()

    targets = scanner.scan_file("sample_repo/calculator.py")
    assert len(targets) > 0

    pairs = []
    for t in targets[:3]:
        p = Patch(
            target_qualified_name=t.qualified_name,
            file_path=t.file_path,
            start_byte=t.start_byte,
            end_byte=t.end_byte,
            generated_docstring=f"Execute {t.qualified_name}.",
            param_annotations={param: "float" for param in t.missing_type_annotations},
            return_annotation="float",
        )
        pairs.append((t, p))

    patched = patcher.apply_patches(original, pairs)
    assert '"""Execute add."""' in patched
    assert '"""Execute subtract."""' in patched
    assert '"""Execute multiply."""' in patched
    assert "def add(a: float, b: float) -> float:" in patched
    assert "def subtract(a: float, b: float) -> float:" in patched


def test_golden_diff(scanner: Scanner, patcher: Patcher):
    """Verify that patching produces deterministic, expected diff format."""
    code = "def compute(val):\n    return val * 2\n"
    target = scanner.scan_file("temp.py", code_bytes=code.encode("utf-8"))[0]

    patch = Patch(
        target_qualified_name="compute",
        file_path="temp.py",
        start_byte=target.start_byte,
        end_byte=target.end_byte,
        generated_docstring="Compute double of value.",
        param_annotations={"val": "int"},
        return_annotation="int",
    )

    result = patcher.apply_patches(code, [(target, patch)])
    expected = (
        'def compute(val: int) -> int:\n'
        '    """Compute double of value."""\n'
        '    return val * 2\n'
    )
    assert result == expected
