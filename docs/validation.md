# Validation

The suite contains 57 tests. Local HTTP health and page checks returned 200.

The synthetic 10 MB monitor benchmark recorded cold refresh 4.008s, warm
refresh 2.025s before the unchanged-snapshot fast path, unchanged selected
poll below 0.001s, and changed selected poll 2.849s. The benchmark creates
temporary local JSONL files and removes them after completion; rerun
`benchmark_monitor.py` to reproduce it.
# WIP checkpoint (current continuation)

The previously recorded **57/full** evidence predates the current WIP and must
not be treated as final-suite certification.  The current full-suite command
and result are:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

**70 passed**, with **2 pandas Period timezone conversion warnings**, in
**14.85s**.  Earlier scheduled-fragment AppTest timeout evidence was historical
WIP only and is not the current full-suite result.  Browser visual QA and
latest real-data startup/cache validation remain TODO.

The most recent targeted AppTest command was:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_app_integration.py -q
```

Result: **4 passed**, with **1 pandas Period timezone warning**.  This was a
targeted AppTest run, not the complete suite.
