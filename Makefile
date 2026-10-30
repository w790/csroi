.PHONY: check

check:
	uv run ruff format . && \
	uv run mypy . --strict && \
	uv run ruff check . --extend-select I --fix && \
	uv run deptry . && \
	uv run pytest -q
