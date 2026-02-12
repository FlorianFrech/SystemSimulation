.PHONY: bump-patch bump-minor bump-major bump-patch-dry bump-minor-dry bump-major-dry

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
