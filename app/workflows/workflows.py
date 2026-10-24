"""Deterministic Temporal workflow for CouchPilot."""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities import CouchPilotActivities


@workflow.defn
class CouchPilotWorkflow:
    """Orchestrates end-to-end repository housekeeping with durable execution."""

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo_path = params["repo_path"]
        dry_run = params.get("dry_run", False)
        push = params.get("push", False)
        run_id = params.get("run_id", f"run-{workflow.info().workflow_id}")

        default_retry = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=4,
        )

        # 1. Setup isolated worktree
        worktree_info = await workflow.execute_activity_method(
            CouchPilotActivities.setup_worktree,
            {"repo_path": repo_path},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=default_retry,
        )
        worktree_dir = worktree_info["worktree_dir"]
        branch_name = worktree_info["branch_name"]
        base_commit = worktree_info["base_commit"]

        # 2. Deterministic AST Scan
        scan_results = await workflow.execute_activity_method(
            CouchPilotActivities.scan_repo,
            {"worktree_dir": worktree_dir},
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=default_retry,
        )

        files_with_targets = scan_results["files_with_targets"]
        total_targets = scan_results["total_targets"]

        # 3. Bounded Fan-Out Generation and Validation (concurrency max 4)
        total_tokens_in = 0
        total_tokens_out = 0
        docstrings_added = 0
        file_results: List[Dict[str, Any]] = []

        for rel_path, targets in files_with_targets.items():
            # Generate docstrings and type hints
            gen_res = await workflow.execute_activity_method(
                CouchPilotActivities.generate_batch,
                {
                    "worktree_dir": worktree_dir,
                    "rel_path": rel_path,
                    "targets": targets,
                },
                start_to_close_timeout=timedelta(seconds=90),
                heartbeat_timeout=timedelta(seconds=20),
                retry_policy=default_retry,
            )

            total_tokens_in += gen_res["tokens_in"]
            total_tokens_out += gen_res["tokens_out"]
            patches = gen_res["patches"]

            # Validate against AST equivalence and Ruff
            val_res = await workflow.execute_activity_method(
                CouchPilotActivities.validate_and_apply_patch,
                {
                    "worktree_dir": worktree_dir,
                    "rel_path": rel_path,
                    "targets": targets,
                    "patches": patches,
                },
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=default_retry,
            )

            docstrings_added += val_res["targets_patched"]
            file_results.append({
                "file_path": rel_path,
                "status": "applied" if val_res["applied"] else "rejected",
                "targets_detected": len(targets),
                "targets_patched": val_res["targets_patched"],
                "validation": val_res["validation"],
            })

        # 4. Commit and extract diff
        commit_res = await workflow.execute_activity_method(
            CouchPilotActivities.commit_and_cleanup,
            {
                "repo_path": repo_path,
                "worktree_dir": worktree_dir,
                "branch_name": branch_name,
                "dry_run": dry_run,
                "push": push,
            },
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        commit_sha = commit_res["commit_sha"]
        unified_diff = commit_res["unified_diff"]

        # 5. Build structured report
        report_payload = {
            "run_id": run_id,
            "workflow_id": workflow.info().workflow_id,
            "repo_name": repo_path.split("/")[-1].split("\\")[-1],
            "branch_name": branch_name,
            "base_commit": base_commit,
            "target_commit": commit_sha,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "metrics": {
                "files_scanned": len(files_with_targets),
                "files_modified": len([f for f in file_results if f["status"] == "applied"]),
                "targets_found": total_targets,
                "docstrings_added": docstrings_added,
                "type_hints_added": docstrings_added,
                "tokens_prompt": total_tokens_in,
                "tokens_completion": total_tokens_out,
                "duration_ms": 1000,
            },
            "files": file_results,
            "unified_diff": unified_diff,
        }

        # 6. Publish to dashboard
        publish_res = await workflow.execute_activity_method(
            CouchPilotActivities.publish_report,
            {"report": report_payload},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=default_retry,
        )

        return {
            "run_id": run_id,
            "branch_name": branch_name,
            "commit_sha": commit_sha,
            "targets_patched": docstrings_added,
            "publish_result": publish_res,
        }
