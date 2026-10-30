# Branch Plan

`main` is the protected integration branch. Workstream A reviews required checks and merges approved pull requests. Do not force-push shared branches, commit secrets, or bypass review.

| Branch | Owner workstream | Purpose |
| --- | --- | --- |
| `feature/ui-polish` | B | Streamlit presentation and screenshots |
| `feature/incident-data` | C | Synthetic incidents, policies, and test fixtures |
| `feature/policy-and-ai` | D | Retrieval, provider boundary, and AI documentation |
| `feature/qa-and-submission` | E | QA, demo, and submission documentation |

```bash
git clone <repository-url>
cd Guardbee
git switch main
git pull --ff-only origin main
git switch -c feature/ui-polish
# make focused changes and run required tests
git status
git add <intended-files>
git commit -m "docs: describe verified UI workflow"
git push -u origin feature/ui-polish
```

Before updating a branch:

```bash
git switch feature/ui-polish
git fetch origin
git rebase origin/main
# resolve and retest locally if necessary
git push --force-with-lease
```

Use `--force-with-lease` only on your own feature branch after coordination; never on `main`.
