# Contributing

1. Read `AGENTS.md`, relevant architecture/task documents, and current Git status.
2. Create and activate a virtual environment, then install `requirements.txt`.
3. Copy the secrets example locally only if live verification is explicitly authorized; never commit the copy.
4. Create an isolated branch from updated `main`.
5. Make a focused change within the allowed module boundaries.
6. Run `python -m unittest discover -s tests -v` before requesting review.
7. Update documentation and tests for behavior/data changes.
8. Open a PR with test output, concise rationale, and remaining limitations.

Use conventional, descriptive commit prefixes such as `feat:`, `fix:`, `test:`, `docs:`, or `chore:`. Never include secret values, production logs, or real account identifiers in commits, issues, screenshots, or PR descriptions.
