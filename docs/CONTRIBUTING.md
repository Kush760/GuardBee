# Contributing

1. Read `AGENTS.md` and inspect current source before changing behavior.
2. Create and activate a virtual environment; install `requirements.txt`.
3. Copy `.streamlit/secrets.toml.example` locally only if live AI verification is authorized; never commit secrets.
4. Branch from updated `main`; keep changes reviewable.
5. Do not modify unrelated protected datasets/tests unless the task explicitly requires it.
6. Run `python -m unittest discover -s tests -v` and report actual results.
7. Update documentation when behavior changes; keep MVP labeled v2.2.
8. Leave `docs/archive/` as historical unless intentionally revising history with approval.
