#!/usr/bin/env python3
"""
The committed notebook outputs are the deliverable -- someone landing on
03_reconciliation.ipynb from a CV should see results without cloning anything.
This asserts that what is committed is genuinely a clean, sequential run:

  * every code cell executed (no None)
  * execution counts are 1..N in order (no out-of-order re-runs)
  * no error outputs
  * charts are actually present

That last check exists because MPLBACKEND=Agg once produced a notebook that
looked complete and contained no images at all, with no error anywhere.
"""

import json
import sys
from pathlib import Path

EXPECTED_CHARTS = {
    "01_data_profiling.ipynb": 4,
    "02_naive_join.ipynb": 2,
    "03_reconciliation.ipynb": 1,
    "04_before_after.ipynb": 2,
}

failures = []

for name, expected_charts in EXPECTED_CHARTS.items():
    path = Path("notebooks") / name
    if not path.exists():
        failures.append(f"{name}: missing")
        continue

    before = len(failures)

    nb = json.loads(path.read_text())
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    counts = [c.get("execution_count") for c in code]

    if any(c is None for c in counts):
        failures.append(f"{name}: {counts.count(None)} unexecuted cell(s)")

    if counts != list(range(1, len(counts) + 1)):
        failures.append(f"{name}: execution counts not sequential -- {counts}")

    errors = sum(
        1
        for c in code
        for o in c.get("outputs", [])
        if o.get("output_type") == "error"
    )
    if errors:
        failures.append(f"{name}: {errors} error output(s)")

    charts = sum(
        1
        for c in code
        for o in c.get("outputs", [])
        if "image/png" in o.get("data", {})
    )
    if charts != expected_charts:
        failures.append(f"{name}: {charts} charts, expected {expected_charts}")

    # Compare against this notebook's own starting point, not the global list --
    # otherwise one early failure silences the `ok` line for every later file.
    if len(failures) == before:
        print(f"  ok  {name}: {len(code)} cells, 1-{len(code)}, {charts} charts")

if failures:
    print("\nFAILED:", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print("\nAll notebooks committed in a clean executed state.")
