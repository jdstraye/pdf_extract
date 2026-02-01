PDF Extractor — Usage Guide

This guide describes common usage patterns for the PDF extraction utilities in this repository.

* Run extraction for a single user:
  - `python scripts/run_sample_extraction.py user_1314` — writes `data/extracted/...` (used by many tests).


## Pre-auth friendly extractor (new)

We've added a small wrapper intended for downstream repos (e.g., `../pre_auth.git`) to produce canonical, text-only JSON outputs without spans or layout metadata.

Usage (CLI):

- From this repo root:
  - `python -m src.extract_pdf_preauth path/to/user_1234.pdf --out /path/to/out.json`
  - If `--out` is omitted, JSON will be printed to stdout.

Programmatic usage (recommended):

- Import and call directly from Python in other repos:

```py
from src.extract_pdf_preauth import extract_to_canonical
canon = extract_to_canonical('/full/path/to/user_1234.pdf')
# write to desired location
import json
open('/tmp/user_1234_canon.json','w',encoding='utf-8').write(json.dumps(canon, indent=2))
```

Notes for downstream repos (e.g., `../pre_auth.git`):

- Add this repo as a checkout dependency or put it on PYTHONPATH. Example (POSIX shell):

```sh
# from within ../pre_auth.git
export PYTHONPATH="$PYTHONPATH:/path/to/pdf_extract.git"
python -c "from src.extract_pdf_preauth import extract_to_canonical; import json; print(json.dumps(extract_to_canonical('/path/to/pdf'), indent=2))"
```

- The produced JSON is the canonical text-only GT (same shape as `data/extracted/*_ground_truth.json` when produced without spans). It intentionally omits `_bbox`, `_page`, `_spans` and other transient layout keys so downstream systems can consume a stable schema.

- The included integration test `tests/integration/test_extract_pdf_preauth_integration.py` shows how to iterate over PDFs in `data/pdf_analysis/` and validate outputs against `data/extracted/*_ground_truth.json` (the test ignores transient metadata during comparison).
