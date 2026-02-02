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

## Canonical schema changes (important)

Recent changes to the canonical form (affects what keys you should expect):

- Nested account dicts are flattened into explicit count/total keys. For example:
  - `line_of_credit_accounts_open` → `line_of_credit_accounts_open_count`, `line_of_credit_accounts_open_total`
  - `miscellaneous_accounts_open` → `miscellaneous_accounts_open_count`, `miscellaneous_accounts_open_total`
- `late_pays` nested dicts are replaced by flat numeric keys:
  - `late_pays_lt2yr` and `late_pays_gt2yr` (always present and default to 0 when missing)
- Inquiries are canonicalized to `inquiries_lt6mo`; legacy aliases like `inquiries_last_6_months` are accepted when present but the canonical key will be emitted when possible.

These changes make the produced JSON more stable for downstream consumers. If your downstream pipeline previously relied on nested dicts, update it to use the flat keys above.

## Including spans (optional)

If you need page/bbox/span metadata for debugging or mapping (not recommended for production ingestion), use the `--include-spans` flag on the GT CLI or call the extractor with `include_spans=True` and then call `build_text_only_gt(..., include_spans=True)` when building the canonical output. Example (CLI):

```sh
python scripts/pdf_to_ground_truth.py data/pdf_analysis/user_1314_credit_summary_2025-09-01_092724.pdf --include-spans --out /tmp/user_1314_with_spans.json
```

Note: the preauth wrapper `extract_to_canonical` intentionally returns spans-disabled canonical JSON; call the lower-level helpers if you need spans.

## Ordering & tests

- The test-suite no longer enforces a strict global key order across GT files (ordering varies with PDF presentation). Tests now only enforce internal invariants (e.g., `*_count` comes before the corresponding `_total`, and `late_pays_lt2yr` appears before `late_pays_gt2yr` when both are present).
- This makes tests robust to reasonable layout variations while preserving useful ordering checks for debugging.

## Tests & CI

- Run focused ground-truth tests (PDF-heavy tests will skip when PyMuPDF is not installed):

```sh
pytest tests/test_pdf_extraction_ground_truth.py::test_pdf_extraction_vs_ground_truth -q
```

- Run the new integration test that validates programmatic usage across all GT files:

```sh
pytest tests/integration/test_extract_pdf_preauth_integration.py -q
```

If you update downstream code to depend on the canonical schema, add or update tests showing compatibility with these flat keys.
