install:
	uv venv

build:
	uv build

test:
	uv run pytest

[confirm("Are you sure you want to delete all runtime data in var?")]
clean:
	git clean var -X --force
