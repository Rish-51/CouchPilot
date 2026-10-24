"""Data contracts and schemas for CouchPilot."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TargetType(str, Enum):
    FUNCTION = "function"
    METHOD = "method"
    ASYNC_FUNCTION = "async_function"
    CLASS = "class"


class Target(BaseModel):
    """Deterministic node target extracted by tree-sitter."""
    file_path: str
    qualified_name: str
    target_type: TargetType
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    signature: str
    parameters: List[str] = Field(default_factory=list)
    existing_docstring: Optional[str] = None
    missing_docstring: bool = True
    missing_type_annotations: List[str] = Field(default_factory=list)
    has_return_annotation: bool = False
    body_indentation: str = "    "


class Patch(BaseModel):
    """Generated documentation or type annotation patch."""
    target_qualified_name: str
    file_path: str
    start_byte: int
    end_byte: int
    generated_docstring: Optional[str] = None
    param_annotations: Dict[str, str] = Field(default_factory=dict)
    return_annotation: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ValidationResult(BaseModel):
    """Verification outcome per touched file."""
    file_path: str
    syntax_valid: bool = True
    ast_equivalent: bool = True
    ruff_check_passed: bool = True
    ruff_format_passed: bool = True
    error_message: Optional[str] = None
    dropped_from_commit: bool = False


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class FileDiffResult(BaseModel):
    file_path: str
    status: str
    targets_detected: int = 0
    targets_patched: int = 0
    validation: ValidationResult
    unified_diff: str = ""


class ReportMetrics(BaseModel):
    files_scanned: int = 0
    files_modified: int = 0
    targets_found: int = 0
    docstrings_added: int = 0
    type_hints_added: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    duration_ms: int = 0


class Report(BaseModel):
    """Schema posted to POST /api/reports and stored by dashboard."""
    run_id: str
    workflow_id: Optional[str] = None
    repo_name: str
    branch_name: str
    base_commit: str = "HEAD"
    target_commit: Optional[str] = None
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metrics: ReportMetrics = Field(default_factory=ReportMetrics)
    files: List[FileDiffResult] = Field(default_factory=list)
    unified_diff: str = ""
    sentry_trace_id: Optional[str] = None
    error: Optional[str] = None
