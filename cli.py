"""CouchPilot command line interface."""
import asyncio
import os
import sys
import click

from app.core.git_ops import GitManager
from app.core.llm_client import GemmaClient
from app.core.models import Patch, Report, ReportMetrics, RunStatus, Target
from app.core.patcher import Patcher
from app.core.scanner import Scanner
from app.core.sentry_ops import get_sentry_manager
from app.core.validator import Validator


@click.group()
def cli():
    """CouchPilot: Autonomous repository housekeeping agent."""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def scan(repo_path: str):
    """Scan a repository for undocumented or unannotated code."""
    scanner = Scanner()
    click.echo(f"Scanning repository at: {repo_path}")
    results = scanner.scan_directory(repo_path)

    total_targets = 0
    for file_path, targets in results.items():
        click.echo(f"\nFile: {os.path.relpath(file_path, repo_path)} ({len(targets)} targets)")
        for t in targets:
            missing_items = []
            if t.missing_docstring:
                missing_items.append("docstring")
            if t.missing_type_annotations:
                missing_items.append(f"params({', '.join(t.missing_type_annotations)})")
            if not t.has_return_annotation:
                missing_items.append("return_type")

            click.echo(f"  [{t.target_type.value}] {t.qualified_name} -> missing: {', '.join(missing_items)}")
        total_targets += len(targets)

    click.echo(f"\nTotal files needing housekeeping: {len(results)}")
    click.echo(f"Total targets identified: {total_targets}")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--dry-run", is_flag=True, help="Execute scan and generation without committing to a branch.")
@click.option("--push", is_flag=True, help="Push review branch to remote origin.")
def tidy(repo_path: str, dry_run: bool, push: bool):
    """Run full housekeeping: scan, Gemma generation, AST-equivalence check, and review branch commit."""
    sentry = get_sentry_manager()
    scanner = Scanner()
    patcher = Patcher()
    validator = Validator()
    llm = GemmaClient()

    click.echo(f"Starting housekeeping run on {repo_path} (dry-run={dry_run}, push={push})")

    # 1. Worktree isolation
    git_mgr = GitManager(repo_path)
    branch_name = git_mgr.generate_branch_name()
    worktree_dir, _ = git_mgr.create_isolated_worktree(branch_name)

    try:
        # 2. Deterministic Scan
        results = scanner.scan_directory(worktree_dir)
        click.echo(f"Identified {len(results)} files with missing docstrings/types.")

        # 3. Generate and validate per file
        for file_path, targets in results.items():
            rel_path = os.path.relpath(file_path, worktree_dir)
            click.echo(f"Processing {rel_path} ({len(targets)} targets)...")

            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            patches, tokens_in, tokens_out, latency = llm.generate_batch(
                file_path=rel_path,
                file_content=original_code,
                targets=targets,
            )

            if not patches:
                click.echo(f"  Skipped {rel_path}: no valid patches returned.")
                continue

            target_map = {t.qualified_name: t for t in targets}
            pairs = [(target_map[p.target_qualified_name], p) for p in patches if p.target_qualified_name in target_map]
            patched_code = patcher.apply_patches(original_code, pairs)

            # Safety check: AST equivalence & Ruff
            val = validator.validate_code_change(original_code, patched_code, file_path)
            if val.dropped_from_commit:
                click.echo(f"  Rejected {rel_path}: {val.error_message}")
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(patched_code)
                click.echo(f"  Applied {len(pairs)} patches to {rel_path} (ast equivalent: True, ruff clean: True)")

        # 4. Commit and extract diff
        diff = git_mgr.extract_diff()
        if dry_run:
            click.echo("\n--- Dry Run Unified Diff ---")
            click.echo(diff or "(No changes staged)")
        else:
            commit_sha = git_mgr.commit_changes(
                commit_message=f"housekeeping: docstrings and type annotations ({branch_name})",
                branch_name=branch_name,
            )
            click.echo(f"\nCommitted changes to review branch '{branch_name}' (SHA: {commit_sha[:8]})")
            if push:
                git_mgr.push_review_branch(branch_name)
                click.echo(f"Pushed branch '{branch_name}' to origin.")

    finally:
        git_mgr.cleanup_worktree()
        click.echo("Cleaned up isolated worktree.")


@cli.command()
def worker():
    """Start local Temporal worker for CouchPilot workflows."""
    from app.workflows.worker import run_worker
    asyncio.run(run_worker())


if __name__ == "__main__":
    cli()
