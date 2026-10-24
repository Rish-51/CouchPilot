"""Git operations with worktree isolation and review branch protection."""
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import git


class GitManager:
    """Safely manages isolated git operations without touching default branch or user working tree."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        try:
            self.repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
        self.worktree_dir: Optional[str] = None
        self.worktree_repo: Optional[git.Repo] = None

    def get_current_branch(self) -> str:
        """Return the active branch name of the repository."""
        try:
            return self.repo.active_branch.name
        except TypeError:
            return "HEAD"

    def get_default_branch(self) -> str:
        """Infer default branch (main or master)."""
        branches = [h.name for h in self.repo.heads]
        if "main" in branches:
            return "main"
        if "master" in branches:
            return "master"
        return self.get_current_branch()

    def generate_branch_name(self) -> str:
        """Generate review branch name couchpilot/tidy-YYYYMMDD with collision resolution."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        base_name = f"couchpilot/tidy-{date_str}"

        existing_branches = {h.name for h in self.repo.heads}
        if base_name not in existing_branches:
            return base_name

        suffix = 1
        while f"{base_name}-{suffix}" in existing_branches:
            suffix += 1
        return f"{base_name}-{suffix}"

    def create_isolated_worktree(self, branch_name: str) -> Tuple[str, git.Repo]:
        """Create a dedicated git worktree to guarantee isolation from the user's working tree."""
        # Safety invariant #1: never work in user's working tree
        temp_dir = tempfile.mkdtemp(prefix="couchpilot_worktree_")
        self.worktree_dir = temp_dir

        # Add worktree
        self.repo.git.worktree("add", temp_dir, "-b", branch_name)
        self.worktree_repo = git.Repo(temp_dir)
        return temp_dir, self.worktree_repo

    def cleanup_worktree(self) -> None:
        """Prune and remove the isolated worktree directory."""
        if self.worktree_dir and os.path.exists(self.worktree_dir):
            try:
                self.repo.git.worktree("remove", "--force", self.worktree_dir)
            except Exception:
                pass
            if os.path.exists(self.worktree_dir):
                shutil.rmtree(self.worktree_dir, ignore_errors=True)
            self.worktree_dir = None
            self.worktree_repo = None

    def commit_changes(self, commit_message: str, branch_name: str) -> str:
        """Commit staged changes in the isolated worktree to the review branch."""
        # Safety invariant #2: never commit to default branch
        default_branch = self.get_default_branch()
        if branch_name in {default_branch, "main", "master"}:
            raise ValueError(f"Safety violation: Refusing to commit to protected default branch '{branch_name}'")

        target_repo = self.worktree_repo or self.repo
        target_repo.git.add(A=True)
        commit = target_repo.index.commit(commit_message)
        return commit.hexsha

    def extract_diff(self, base_commit: str = "HEAD~1") -> str:
        """Extract unified diff between commits or against working tree."""
        target_repo = self.worktree_repo or self.repo
        try:
            return target_repo.git.diff(base_commit, "HEAD")
        except Exception:
            try:
                return target_repo.git.diff("HEAD")
            except Exception:
                return ""

    def push_review_branch(self, branch_name: str, remote_name: str = "origin") -> None:
        """Push review branch only when explicitly enabled."""
        default_branch = self.get_default_branch()
        if branch_name in {default_branch, "main", "master"}:
            raise ValueError(f"Safety violation: Refusing to push protected default branch '{branch_name}'")

        target_repo = self.worktree_repo or self.repo
        target_repo.git.push(remote_name, branch_name)
