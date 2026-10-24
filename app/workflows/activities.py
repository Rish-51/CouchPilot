"""Temporal activities for repository housekeeping."""
import os
import time
from datetime import datetime
from typing import Any, Dict, List
import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.core.git_ops import GitManager
from app.core.llm_client import GemmaClient
from app.core.models import FileDiffResult, Patch, Report, ReportMetrics, RunStatus, Target, ValidationResult
from app.core.patcher import Patcher
from app.core.scanner import Scanner
from app.core.sentry_ops import get_sentry_manager
from app.core.validator import Validator


class CouchPilotActivities:
    """Collection of Temporal activities executing housekeeping operations."""

    def __init__(self) -> None:
        self.scanner = Scanner()
        self.patcher = Patcher()
        self.validator = Validator()
        self.llm_client = GemmaClient()
        self.sentry = get_sentry_manager()

    @activity.defn
    async def setup_worktree(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Create an isolated worktree and review branch."""
        repo_path = params["repo_path"]
        branch_name = params.get("branch_name")

        if not os.path.exists(repo_path):
            raise ApplicationError(
                f"Repository path does not exist: {repo_path}",
                type="RepoNotFoundError",
                non_retryable=True,
            )

        git_mgr = GitManager(repo_path)
        if not branch_name:
            branch_name = git_mgr.generate_branch_name()

        worktree_dir, _ = git_mgr.create_isolated_worktree(branch_name)
        return {
            "worktree_dir": worktree_dir,
            "branch_name": branch_name,
            "base_commit": git_mgr.repo.head.commit.hexsha,
        }

    @activity.defn
    async def scan_repo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scan repository deterministically using tree-sitter."""
        worktree_dir = params["worktree_dir"]

        with self.sentry.span(
            op="scan.repo",
            description="Static analysis scan across repository",
            tags={"engine": "tree-sitter"}
        ):
            results = self.scanner.scan_directory(worktree_dir)
            total_targets = sum(len(targets) for targets in results.values())

            # Convert targets to JSON serializable dicts
            serialized: Dict[str, List[dict]] = {}
            for file_path, targets in results.items():
                rel_path = os.path.relpath(file_path, worktree_dir)
                serialized[rel_path] = [t.model_dump() for t in targets]

            return {
                "files_with_targets": serialized,
                "total_targets": total_targets,
                "total_files": len(serialized),
            }

    @activity.defn
    async def generate_batch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate docstrings and type hints using Gemma for a file batch."""
        worktree_dir = params["worktree_dir"]
        rel_path = params["rel_path"]
        target_dicts = params["targets"]

        file_full_path = os.path.join(worktree_dir, rel_path)
        with open(file_full_path, "r", encoding="utf-8") as f:
            code = f.read()

        targets = [Target.model_validate(t) for t in target_dicts]
        activity.heartbeat(f"Generating for {rel_path} ({len(targets)} targets)")

        patches, tokens_in, tokens_out, latency_ms = self.llm_client.generate_batch(
            file_path=rel_path,
            file_content=code,
            targets=targets,
        )

        return {
            "rel_path": rel_path,
            "patches": [p.model_dump() for p in patches],
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
        }

    @activity.defn
    async def validate_and_apply_patch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify candidate patches against AST equivalence and apply clean changes."""
        worktree_dir = params["worktree_dir"]
        rel_path = params["rel_path"]
        target_dicts = params["targets"]
        patch_dicts = params["patches"]

        file_full_path = os.path.join(worktree_dir, rel_path)
        with open(file_full_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        targets = [Target.model_validate(t) for t in target_dicts]
        patches = [Patch.model_validate(p) for p in patch_dicts]

        target_map = {t.qualified_name: t for t in targets}
        pairs = []
        for p in patches:
            if p.target_qualified_name in target_map:
                pairs.append((target_map[p.target_qualified_name], p))

        patched_code = self.patcher.apply_patches(original_code, pairs)

        # Safety invariant #3 & #5: Validate changes
        validation = self.validator.validate_code_change(original_code, patched_code, file_full_path)

        if not validation.dropped_from_commit:
            with open(file_full_path, "w", encoding="utf-8") as f:
                f.write(patched_code)

        return {
            "rel_path": rel_path,
            "validation": validation.model_dump(),
            "applied": not validation.dropped_from_commit,
            "targets_patched": len(pairs) if not validation.dropped_from_commit else 0,
        }

    @activity.defn
    async def commit_and_cleanup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Commit verified changes to review branch and return unified diff."""
        repo_path = params["repo_path"]
        worktree_dir = params["worktree_dir"]
        branch_name = params["branch_name"]
        dry_run = params.get("dry_run", False)
        push = params.get("push", False)

        git_mgr = GitManager(repo_path)
        git_mgr.worktree_dir = worktree_dir
        git_mgr.worktree_repo = git_mgr.repo.__class__(worktree_dir)

        diff = git_mgr.extract_diff()
        commit_sha = "dry-run"

        if not dry_run:
            commit_sha = git_mgr.commit_changes(
                commit_message=f"housekeeping: docstrings and type annotations ({branch_name})",
                branch_name=branch_name,
            )
            if push:
                git_mgr.push_review_branch(branch_name)

        git_mgr.cleanup_worktree()
        return {
            "commit_sha": commit_sha,
            "unified_diff": diff,
        }

    @activity.defn
    async def publish_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Publish completed run report to FastAPI dashboard with X-CouchPilot-Key header."""
        report_dict = params["report"]
        dashboard_url = os.getenv("COUCHPILOT_DASHBOARD_URL", "http://localhost:8000")
        api_key = os.getenv("COUCHPILOT_API_KEY", "couchpilot_secret_key_change_me_in_prod")

        endpoint = f"{dashboard_url.rstrip('/')}/api/reports"
        headers = {
            "X-CouchPilot-Key": api_key,
            "Content-Type": "application/json",
        }

        with self.sentry.span(
            op="report.publish",
            description="Push housekeeping report to dashboard",
            tags={"dashboard_url": dashboard_url}
        ) as span:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(endpoint, json=report_dict, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if span:
                        span.set_data("status_code", resp.status_code)
                        span.set_data("report_id", data.get("report_id"))
                    return data
            except httpx.HTTPStatusError as e:
                if e.response.status_code in {401, 403}:
                    raise ApplicationError(
                        f"Authentication failure publishing report: {e}",
                        type="InvalidDashboardKeyError",
                        non_retryable=True,
                    )
                raise
            except Exception as e:
                # Dashboard might be offline during local runs; return local fallback
                return {"status": "saved_locally_only", "error": str(e)}
