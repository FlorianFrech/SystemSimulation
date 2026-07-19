.PHONY: sync test build publish-testpypi publish bump-patch bump-minor bump-major bump-patch-dry bump-minor-dry bump-major-dry

sync:
	uv sync --python 3.13 --extra all

test:
	uv run pytest tests

build:
	uv build --no-sources

publish-testpypi:
	uv publish --index testpypi

publish:
	uv publish

bump-patch:
	python scripts/bump_version.py patch

bump-minor:
	python scripts/bump_version.py minor

bump-major:
	python scripts/bump_version.py major

bump-patch-dry:
	python scripts/bump_version.py patch --dry-run

bump-minor-dry:
	python scripts/bump_version.py minor --dry-run

bump-major-dry:
	python scripts/bump_version.py major --dry-run
