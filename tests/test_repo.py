import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from git_to_prompt.repo import pack_repository


@pytest.fixture
def mock_repo() -> Generator[str, None, None]:
    """Create a temporary directory with a mock repository structure including a .venv folder.

    The .venv folder contains its own .gitignore with "*" pattern, which should ignore all
    files within that directory.

    Returns:
        Path to the temporary directory containing the mock repository.
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create the basic repository structure
        repo_structure = {
            "main.py": "print('Hello, world!')",
            ".gitignore": ".venv/\n",
            ".venv": {
                ".gitignore": "*\n",  # This should ignore everything in .venv
                "bin": {
                    "activate": "#!/bin/bash\necho 'This is a mock activate script'",
                    "python": "#!/bin/bash\necho 'This is a mock python script'",
                },
                "lib": {
                    "python3.9": {
                        "site-packages": {"example.py": "# This should be ignored"}
                    }
                },
            },
            "src": {
                "__init__.py": "",
                "app.py": "def main():\n    return 'App is running'",
            },
            "tests": {
                "__init__.py": "",
                "test_app.py": "def test_main():\n    assert True",
            },
        }

        # Create the files and directories in the temp directory
        _create_repo_structure(temp_dir, repo_structure)

        # Initialize git repository
        from git import Repo

        repo = Repo.init(temp_dir)

        # Add all files to git
        repo.git.add(all=True)

        # Make an initial commit
        repo.git.commit("-m", "Initial commit")

        yield temp_dir
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)


def _create_repo_structure(base_path: str, structure: dict) -> None:
    """Recursively create a directory structure based on a nested dictionary.

    Args:
        base_path: The base path where the structure should be created.
        structure: A nested dictionary representing the directory structure.
    """
    for name, content in structure.items():
        path = os.path.join(base_path, name)

        if isinstance(content, dict):
            # It's a directory
            os.makedirs(path, exist_ok=True)
            _create_repo_structure(path, content)
        else:
            # It's a file
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)


def test_venv_gitignore_bug(mock_repo: str) -> None:
    """Test that verifies RepomixPython correctly handles nested .gitignore files using GitPython.

    Tests that when a .venv directory contains its own .gitignore file with a "*" pattern
    (which should ignore all files in that directory), RepomixPython correctly excludes those files.

    Args:
        mock_repo: Path to the mock repository created by the fixture.
    """

    # List the actual files in the .venv directory to confirm they exist
    venv_files = []
    for root, _, files in os.walk(os.path.join(mock_repo, ".venv")):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), mock_repo)
            venv_files.append(rel_path)
    print(f"Files in .venv: {venv_files}")

    # Check if .venv/.gitignore exists and what it contains
    venv_gitignore_path = os.path.join(mock_repo, ".venv", ".gitignore")
    if os.path.exists(venv_gitignore_path):
        with open(venv_gitignore_path) as f:
            content = f.read()
        print(f".venv/.gitignore content: {content!r}")

    # Pack the repository
    packed_content = pack_repository(Path(mock_repo))

    # Extract the list of files included in the packed content for easier debugging
    included_files = []
    for line in packed_content.split("\n"):
        if line.startswith("File: "):
            included_files.append(line[6:])  # Remove "File: " prefix
    print(f"Files included in packed content: {included_files}")

    # Files that should be included
    expected_files = [
        "main.py",
        "src/__init__.py",
        "src/app.py",
        "tests/__init__.py",
        "tests/test_app.py",
    ]

    # Files that should be excluded - everything in .venv folder
    excluded_files = [
        ".venv/bin/activate",
        ".venv/bin/python",
        ".venv/lib/python3.9/site-packages/example.py",
    ]

    # Check that expected files are included
    for file_path in expected_files:
        file_marker = f"File: {file_path}"
        assert file_marker in packed_content, (
            f"Expected file {file_path} not found in packed content"
        )

    # Check that .venv files are properly excluded (as GitPython should respect nested .gitignore files)
    venv_files_in_output = [f for f in included_files if f.startswith(".venv/")]
    assert not venv_files_in_output, (
        f"Files from .venv should be excluded due to .venv/.gitignore with '*' pattern. "
        f"Found: {venv_files_in_output}"
    )
