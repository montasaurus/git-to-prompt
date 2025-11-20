from pathlib import Path

from git import Repo
from pytest import CaptureFixture
from syrupy.assertion import SnapshotAssertion

from git_to_prompt.cli import app


def test_show_includes_patch_by_default(
    temp_git_repo: Path, capsys: CaptureFixture[str], snapshot: SnapshotAssertion
):
    """show should output a single commit with patch included by default."""

    repo = Repo(temp_git_repo)
    head_sha = repo.head.commit.hexsha

    app(f"show {head_sha} --repo-path {temp_git_repo}")

    captured = capsys.readouterr().out

    assert captured == snapshot


def test_show_respects_no_patch(
    temp_git_repo: Path, capsys: CaptureFixture[str], snapshot: SnapshotAssertion
):
    """Passing --no-patch should omit the patch element."""

    repo = Repo(temp_git_repo)
    head_sha = repo.head.commit.hexsha

    app(f"show --no-patch {head_sha} --repo-path {temp_git_repo}")

    captured = capsys.readouterr().out

    assert captured == snapshot


def test_show_with_path_filter(
    temp_git_repo: Path, capsys: CaptureFixture[str], snapshot: SnapshotAssertion
):
    """Paths passed after -- should filter to commits touching that path."""

    repo = Repo(temp_git_repo)
    head_sha = repo.head.commit.hexsha

    app(f"show {head_sha} --repo-path {temp_git_repo} -- test.txt")

    captured = capsys.readouterr().out

    assert captured == snapshot
