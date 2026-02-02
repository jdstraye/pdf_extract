CHANGES — recent notable updates

2026-02-01
- **Preauth-friendly extractor**: Added `src/extract_pdf_preauth.py` with `extract_to_canonical(pdf_path)` and CLI (`python -m src.extract_pdf_preauth <pdf> --out <json>`). This produces canonical, text-only JSON without spans by default.

- **Canonical schema changes**:
  - Flattened nested account structures into explicit keys (e.g., `line_of_credit_accounts_open_count`, `line_of_credit_accounts_open_total`).
  - Flattened `late_pays` into `late_pays_lt2yr` and `late_pays_gt2yr` (numeric default 0).
  - Normalized inquiries aliasing (`inquiries_last_6_months` → `inquiries_lt6mo` canonical).

- **Span handling**: `scripts/pdf_to_ground_truth.py` supports `--include-spans` to attach `_bbox`, `_page`, and `_spans` for debugging/inspection. The preauth wrapper intentionally omits spans to keep output stable.

- **Ordering tests relaxed**: Tests no longer require strict global key ordering. Only important internal ordering invariants are checked (e.g., `*_count` before corresponding `_total`; `late_pays_lt2yr` before `late_pays_gt2yr`). This reduces brittleness when PDFs present fields in different visual order.

- **Tests & docs**: Added unit + integration tests for the preauth extractor, updated `docs/usage_guide.md` with usage and compatibility notes, and added README examples for various consumption methods (PYTHONPATH, editable install, git install, importlib usage).

Notes:
- If you depend on the previous nested schema, update your code to use the flat keys listed above.
- If you want spans in canonical outputs (for debugging), use the CLI `--include-spans` or call low-level helpers with `include_spans=True`.
