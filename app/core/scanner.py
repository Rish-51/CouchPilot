"""Deterministic AST scanner using tree-sitter."""
import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from tree_sitter import Language, Node, Parser
import tree_sitter_python as tspython

from app.core.models import Target, TargetType


class Scanner:
    """Scans Python files to identify targets missing docstrings or type annotations."""

    def __init__(self) -> None:
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    def scan_file(self, file_path: str, code_bytes: Optional[bytes] = None) -> List[Target]:
        """Scan a single Python file and return all identified targets."""
        if code_bytes is None:
            with open(file_path, "rb") as f:
                code_bytes = f.read()

        # Quick check for syntax validity using Python ast
        try:
            ast.parse(code_bytes)
        except SyntaxError:
            # File has syntax errors, skip deterministic scan
            return []

        tree = self.parser.parse(code_bytes)
        targets: List[Target] = []

        self._scan_node_children(tree.root_node, file_path, code_bytes, prefix="", targets=targets)
        return targets

    def scan_directory(self, dir_path: str) -> Dict[str, List[Target]]:
        """Recursively scan a directory for Python files."""
        results: Dict[str, List[Target]] = {}
        ignore_dirs = {
            ".git", "venv", ".venv", "__pycache__", ".pytest_cache",
            ".ruff_cache", "build", "dist", "node_modules", "impeccable"
        }

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.normpath(os.path.join(root, file))
                    targets = self.scan_file(full_path)
                    if targets:
                        results[full_path] = targets
        return results

    def _scan_node_children(
        self,
        node: Node,
        file_path: str,
        code_bytes: bytes,
        prefix: str,
        targets: List[Target]
    ) -> None:
        for child in node.children:
            if not child.is_named:
                continue

            if child.type == "class_definition":
                self._handle_class(child, file_path, code_bytes, prefix, targets)
            elif child.type == "function_definition":
                self._handle_function(child, file_path, code_bytes, prefix, targets, is_async=False)
            elif child.type == "decorated_definition":
                self._handle_decorated(child, file_path, code_bytes, prefix, targets)

    def _handle_decorated(
        self,
        node: Node,
        file_path: str,
        code_bytes: bytes,
        prefix: str,
        targets: List[Target]
    ) -> None:
        # Check decorators to skip @overload
        decorators = [c for c in node.children if c.type == "decorator"]
        for d in decorators:
            dec_text = code_bytes[d.start_byte:d.end_byte].decode("utf-8", errors="replace")
            if "overload" in dec_text:
                return

        # Find underlying definition
        for child in node.children:
            if child.type == "function_definition":
                self._handle_function(child, file_path, code_bytes, prefix, targets, is_async=False, outer_node=node)
                return
            elif child.type == "class_definition":
                self._handle_class(child, file_path, code_bytes, prefix, targets, outer_node=node)
                return

    def _handle_class(
        self,
        node: Node,
        file_path: str,
        code_bytes: bytes,
        prefix: str,
        targets: List[Target],
        outer_node: Optional[Node] = None
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        qualified_name = f"{prefix}{class_name}" if prefix else class_name

        body_node = node.child_by_field_name("body")
        docstring, missing_doc = self._extract_docstring(body_node, code_bytes)
        body_indent = self._derive_body_indentation(node, body_node, code_bytes)

        sig_node = outer_node if outer_node else node
        sig_text = self._extract_class_signature(node, code_bytes)

        if missing_doc:
            targets.append(
                Target(
                    file_path=file_path,
                    qualified_name=qualified_name,
                    target_type=TargetType.CLASS,
                    start_byte=sig_node.start_byte,
                    end_byte=sig_node.end_byte,
                    start_line=sig_node.start_point[0] + 1,
                    end_line=sig_node.end_point[0] + 1,
                    signature=sig_text,
                    parameters=[],
                    existing_docstring=docstring,
                    missing_docstring=missing_doc,
                    missing_type_annotations=[],
                    has_return_annotation=True,
                    body_indentation=body_indent,
                )
            )

        if body_node:
            self._scan_node_children(body_node, file_path, code_bytes, prefix=f"{qualified_name}.", targets=targets)

    def _handle_function(
        self,
        node: Node,
        file_path: str,
        code_bytes: bytes,
        prefix: str,
        targets: List[Target],
        is_async: bool,
        outer_node: Optional[Node] = None
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        func_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
        qualified_name = f"{prefix}{func_name}" if prefix else func_name

        is_method = bool(prefix)
        target_type = TargetType.METHOD if is_method else (TargetType.ASYNC_FUNCTION if is_async else TargetType.FUNCTION)

        # Inspect parameters and annotations
        params_node = node.child_by_field_name("parameters")
        param_names, unannotated_params = self._inspect_parameters(params_node, code_bytes, is_method=is_method)

        # Inspect return type
        ret_type_node = node.child_by_field_name("return_type")
        has_return = ret_type_node is not None or func_name == "__init__"

        # Inspect docstring
        body_node = node.child_by_field_name("body")
        docstring, missing_doc = self._extract_docstring(body_node, code_bytes)
        body_indent = self._derive_body_indentation(node, body_node, code_bytes)

        sig_node = outer_node if outer_node else node
        sig_text = self._extract_function_signature(node, code_bytes)

        needs_patch = missing_doc or len(unannotated_params) > 0 or not has_return

        if needs_patch:
            targets.append(
                Target(
                    file_path=file_path,
                    qualified_name=qualified_name,
                    target_type=target_type,
                    start_byte=sig_node.start_byte,
                    end_byte=sig_node.end_byte,
                    start_line=sig_node.start_point[0] + 1,
                    end_line=sig_node.end_point[0] + 1,
                    signature=sig_text,
                    parameters=param_names,
                    existing_docstring=docstring,
                    missing_docstring=missing_doc,
                    missing_type_annotations=unannotated_params,
                    has_return_annotation=has_return,
                    body_indentation=body_indent,
                )
            )

    def _inspect_parameters(
        self,
        params_node: Optional[Node],
        code_bytes: bytes,
        is_method: bool
    ) -> Tuple[List[str], List[str]]:
        if not params_node:
            return [], []

        all_params: List[str] = []
        unannotated: List[str] = []

        named_children = [c for c in params_node.children if c.is_named]
        for idx, param_child in enumerate(named_children):
            if is_method and idx == 0:
                # Check for self or cls
                param_text = code_bytes[param_child.start_byte:param_child.end_byte].decode("utf-8", errors="replace")
                if param_text in {"self", "cls"}:
                    all_params.append(param_text)
                    continue

            if param_child.type == "identifier":
                p_name = code_bytes[param_child.start_byte:param_child.end_byte].decode("utf-8", errors="replace")
                all_params.append(p_name)
                unannotated.append(p_name)
            elif param_child.type == "default_parameter":
                name_part = param_child.child_by_field_name("name")
                if name_part:
                    p_name = code_bytes[name_part.start_byte:name_part.end_byte].decode("utf-8", errors="replace")
                    all_params.append(p_name)
                    unannotated.append(p_name)
            elif param_child.type in {"typed_parameter", "typed_default_parameter"}:
                name_part = param_child.child_by_field_name("name")
                if name_part:
                    p_name = code_bytes[name_part.start_byte:name_part.end_byte].decode("utf-8", errors="replace")
                    all_params.append(p_name)

        return all_params, unannotated

    def _extract_docstring(self, body_node: Optional[Node], code_bytes: bytes) -> Tuple[Optional[str], bool]:
        if not body_node:
            return None, True

        named_stmts = [c for c in body_node.children if c.is_named]
        if not named_stmts:
            return None, True

        first_stmt = named_stmts[0]
        if first_stmt.type == "expression_statement":
            inner_exprs = [c for c in first_stmt.children if c.is_named]
            if inner_exprs and inner_exprs[0].type == "string":
                doc_bytes = code_bytes[first_stmt.start_byte:first_stmt.end_byte]
                return doc_bytes.decode("utf-8", errors="replace").strip(), False

        return None, True

    def _derive_body_indentation(self, def_node: Node, body_node: Optional[Node], code_bytes: bytes) -> str:
        if body_node:
            named_stmts = [c for c in body_node.children if c.is_named]
            if named_stmts:
                first_stmt = named_stmts[0]
                line_start_byte = code_bytes.rfind(b"\n", 0, first_stmt.start_byte)
                if line_start_byte != -1:
                    indent_bytes = code_bytes[line_start_byte + 1:first_stmt.start_byte]
                    if indent_bytes.strip() == b"":
                        return indent_bytes.decode("utf-8", errors="replace")

        # Fallback: parent line indent + 4 spaces
        line_start_byte = code_bytes.rfind(b"\n", 0, def_node.start_byte)
        if line_start_byte != -1:
            parent_indent = code_bytes[line_start_byte + 1:def_node.start_byte]
            if parent_indent.strip() == b"":
                return parent_indent.decode("utf-8", errors="replace") + "    "
        return "    "

    def _extract_function_signature(self, node: Node, code_bytes: bytes) -> str:
        body_node = node.child_by_field_name("body")
        end_byte = body_node.start_byte if body_node else node.end_byte
        sig_raw = code_bytes[node.start_byte:end_byte].decode("utf-8", errors="replace").strip()
        if sig_raw.endswith(":"):
            sig_raw = sig_raw[:-1].strip()
        return sig_raw

    def _extract_class_signature(self, node: Node, code_bytes: bytes) -> str:
        body_node = node.child_by_field_name("body")
        end_byte = body_node.start_byte if body_node else node.end_byte
        sig_raw = code_bytes[node.start_byte:end_byte].decode("utf-8", errors="replace").strip()
        if sig_raw.endswith(":"):
            sig_raw = sig_raw[:-1].strip()
        return sig_raw
