# GuardBee MVP v2.2 recovery notes

## Recovered exactly from session artifacts
- Python modules matching Final sizes: `engine.py`, `app.py`, `ai_client.py`, `audit_store.py`, `data_loader.py`, `retrieval.py`, `workflow.py`, `ui_presentation.py`, tests, enriched `policies.json`, and MVP docs.
- INC-1001…INC-1003 event cores (unchanged from baseline).
- INC-1014 event cores EVT-417/418/419 (proposal order/timestamps/IP).
- High-confidence event/IP bindings for INC-1006/1008/1010/1012/1013 (EVT ranges and IPs from session engine dumps).

## Reconstructed (original upload/ffce0f1 blobs were not present)
- Titles/accounts/timestamps for INC-1004…1013 (except recovered IP/EVT facts above).
- `tests/fixtures/*` rebuilt to satisfy scenario contracts and engine-authoritative classifications.
- Commit `ffce0f1`, `Guardbee_Final/`, and the non-empty ZIP were verified missing after the environment reset; this package restores a complete runnable MVP tree without recloning or force-pushing.
