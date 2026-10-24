"""Unit tests for the tree-sitter AST scanner."""
import pytest
from app.core.models import TargetType
from app.core.scanner import Scanner


def test_scan_calculator(scanner: Scanner):
    targets = scanner.scan_file("sample_repo/calculator.py")
    assert len(targets) == 6

    names = {t.qualified_name for t in targets}
    assert "add" in names
    assert "subtract" in names
    assert "multiply" in names
    assert "divide" in names
    assert "quick_square" in names
    assert "async_compute_sum" in names

    # Verify parameter detection
    add_target = next(t for t in targets if t.qualified_name == "add")
    assert add_target.parameters == ["a", "b"]
    assert add_target.missing_docstring is True
    assert add_target.missing_type_annotations == ["a", "b"]
    assert add_target.has_return_annotation is False


def test_scan_user_service(scanner: Scanner):
    targets = scanner.scan_file("sample_repo/user_service.py")
    assert len(targets) == 7

    target_map = {t.qualified_name: t for t in targets}
    assert "UserService" in target_map
    assert target_map["UserService"].target_type == TargetType.CLASS

    assert "UserService.__init__" in target_map
    assert target_map["UserService.__init__"].target_type == TargetType.METHOD
    # self should be omitted from unannotated params
    assert "self" not in target_map["UserService.__init__"].missing_type_annotations
    assert "db_conn" in target_map["UserService.__init__"].missing_type_annotations


def test_scan_directory(scanner: Scanner):
    results = scanner.scan_directory("sample_repo")
    assert len(results) >= 2
    for file_path, targets in results.items():
        assert file_path.endswith(".py")
        assert len(targets) > 0
