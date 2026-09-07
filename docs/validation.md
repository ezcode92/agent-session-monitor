# Validation

The suite contains 57 tests. Local HTTP health and page checks returned 200.

The synthetic 10 MB monitor benchmark recorded cold refresh 4.008s, warm
refresh 2.025s before the unchanged-snapshot fast path, unchanged selected
poll below 0.001s, and changed selected poll 2.849s. The benchmark creates
temporary local JSONL files and removes them after completion; rerun
`benchmark_monitor.py` to reproduce it.
