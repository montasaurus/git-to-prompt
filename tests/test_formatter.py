import io
from datetime import datetime, timezone

import pytest

from git_to_prompt.formatter import (
    format_commit_as_cxml,
    format_file_change,
    write_commits_as_cxml,
)
from git_to_prompt.log import Commit, FileChange


@pytest.fixture
def sample_commit():
    """Create a sample commit for testing."""
    return Commit(
        hexsha="1234567890abcdef1234567890abcdef12345678",
        short_sha="1234567",
        author_name="Test Author",
        author_email="test@example.com",
        authored_datetime=datetime(2023, 1, 1, tzinfo=timezone.utc),
        committer_name="Test Committer",
        committer_email="committer@example.com",
        committed_datetime=datetime(2023, 1, 2, tzinfo=timezone.utc),
        message="Test commit message\n\nMore details about the commit.",
        subject="Test commit message",
        parent_shas=["abcdef1234567890abcdef1234567890abcdef12"],
        file_changes=[
            FileChange(
                path="test/file.py",
                change_type="M",
                insertions=10,
                deletions=5,
                content="     def test_function():\n     -    return 'old'\n4   +    return 'new'",
                old_path=None,
            ),
        ],
    )


@pytest.fixture
def sample_file_change():
    """Create a sample file change for testing."""
    return FileChange(
        path="test/file.py",
        change_type="M",
        insertions=10,
        deletions=5,
        content="     def test_function():\n     -    return 'old'\n4   +    return 'new'",
        old_path=None,
    )


@pytest.fixture
def renamed_file_change():
    """Create a sample renamed file change for testing."""
    return FileChange(
        path="test/new_name.py",
        change_type="R",
        insertions=1,
        deletions=0,
        content="     def renamed_function():\n4   +    return 'renamed'",
        old_path="test/old_name.py",
    )


def test_format_file_change(sample_file_change: FileChange):
    """Test formatting a file change as CXML."""
    xml = format_file_change(sample_file_change)

    # Verify it has the expected structure
    assert (
        '<file path="test/file.py" change_type="M" insertions="10" deletions="5">'
        in xml
    )
    assert "<diff>" in xml
    assert "def test_function()" in xml
    # HTML entities are used, so check for escaped versions
    assert "-    return &#x27;old&#x27;" in xml
    assert "+    return &#x27;new&#x27;" in xml
    assert "</diff>" in xml
    assert "</file>" in xml


def test_format_renamed_file_change(renamed_file_change: FileChange):
    """Test formatting a renamed file change as CXML."""
    xml = format_file_change(renamed_file_change)

    # Verify it includes the old path
    assert 'old_path="test/old_name.py"' in xml
    assert 'change_type="R"' in xml


def test_format_file_change_without_content():
    """Test formatting a file change without content."""
    file_change = FileChange(
        path="test/file.py",
        change_type="M",
        insertions=10,
        deletions=5,
        content=None,
        old_path=None,
    )

    xml = format_file_change(file_change)

    # Should be a self-closing tag without diff content
    assert (
        '<file path="test/file.py" change_type="M" insertions="10" deletions="5" />'
        in xml
    )
    assert "<diff>" not in xml


def test_format_commit_as_cxml(sample_commit: Commit):
    """Test formatting a commit as CXML."""
    xml = format_commit_as_cxml(sample_commit, 1, include_diffs=True)

    # Verify it contains all the expected elements
    assert '<commit index="1">' in xml
    assert "<sha>1234567890abcdef1234567890abcdef12345678</sha>" in xml
    assert "<short_sha>1234567</short_sha>" in xml
    assert "<author>Test Author <test@example.com></author>" in xml
    assert "<authored_date>2023-01-01T00:00:00+00:00</authored_date>" in xml
    assert "<committer>Test Committer <committer@example.com></committer>" in xml
    assert "<committed_date>2023-01-02T00:00:00+00:00</committed_date>" in xml
    assert "<subject>Test commit message</subject>" in xml
    assert "<parents>" in xml
    assert "<parent>abcdef1234567890abcdef1234567890abcdef12</parent>" in xml
    assert "</parents>" in xml
    assert "<patch>" in xml
    assert '<file path="test/file.py" change_type="M"' in xml
    assert "</patch>" in xml
    assert "<message>" in xml
    assert "Test commit message" in xml
    assert "More details about the commit." in xml
    assert "</message>" in xml
    assert "</commit>" in xml


def test_format_commit_without_diffs(sample_commit: Commit):
    """Test formatting a commit without diffs."""
    xml = format_commit_as_cxml(sample_commit, 1, include_diffs=False)

    # Verify it doesn't contain patch information
    assert "<patch>" not in xml


def test_format_commit_with_special_characters():
    """Test formatting a commit with special XML characters."""
    commit = Commit(
        hexsha="1234567890abcdef1234567890abcdef12345678",
        short_sha="1234567",
        author_name='Test & Author <with> "quotes"',
        author_email="test@example.com",
        authored_datetime=datetime(2023, 1, 1, tzinfo=timezone.utc),
        committer_name='Test & Committer <with> "quotes"',
        committer_email="committer@example.com",
        committed_datetime=datetime(2023, 1, 2, tzinfo=timezone.utc),
        message='Message with <xml> tags & special "characters"',
        subject='Subject with <xml> tags & special "characters"',
        parent_shas=[],
        file_changes=None,
    )

    xml = format_commit_as_cxml(commit, 1, include_diffs=False)

    # Verify special characters are properly escaped
    assert "Test &amp; Author &lt;with&gt; &quot;quotes&quot;" in xml
    assert "Test &amp; Committer &lt;with&gt; &quot;quotes&quot;" in xml
    assert "Message with &lt;xml&gt; tags &amp; special &quot;characters&quot;" in xml
    assert "Subject with &lt;xml&gt; tags &amp; special &quot;characters&quot;" in xml


def test_write_commits_as_cxml(sample_commit: Commit):
    """Test writing multiple commits as CXML."""

    # Create a generator that yields two commits
    def commit_generator():
        yield sample_commit
        yield sample_commit

    # Create an output buffer
    output = io.StringIO()

    # Write the commits
    write_commits_as_cxml(commit_generator(), output, include_files=True)

    # Get the resulting XML
    result = output.getvalue()

    # Verify it has the expected format
    assert result.startswith("<commits>")
    assert result.endswith("</commits>\n")

    # Count the number of commit opening tags with spaces after them to avoid matching substrings
    assert result.count("<commit ") == 2

    # Each commit should have an index
    assert '<commit index="1">' in result
    assert '<commit index="2">' in result
