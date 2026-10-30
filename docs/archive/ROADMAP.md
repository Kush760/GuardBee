# Roadmap

## After the hackathon

1. Evolve the MVP local SQLite simulated audit (`audit_store.py`) into a protected production-grade store with retention, backup, and access controls (MVP already persists simulation-only rows across restart; it is not a compliance archive).
2. Add reviewed multi-source synthetic/SIEM ingestion adapters with schema mapping.
3. Introduce role-based access control, analyst identity, and authorization records.
4. Evaluate stronger retrieval and policy governance after measuring the current TF-IDF baseline.
5. Add guarded model evaluation, prompt regression tests, and human review for Nemotron outputs.
6. Add production-specific controls only after threat modeling, privacy review, observability, and approval workflows are designed.

These are future possibilities, not implemented GuardBee features beyond the MVP behaviors already documented in Scope v2.2 and the root README.
