# Development Guide — Quick Start 🛠️

This guide helps new contributors get productive quickly with the PDF extraction project.

## Project purpose (elevator pitch)

- Extract structured credit factors and canonical ground-truths from credit summary PDFs.
- Produce stable, text-first JSON outputs used by downstream systems and ML pipelines.

---

## 1) Environment setup (local)

1. Clone the repository and switch to a feature branch:

```sh
git clone git@github.com:<your-org>/pdf_extract.git
cd pdf_extract
git checkout -b feat/your-short-desc
```

2. Create / activate the project virtualenv. There are a couple of commonly used venv names in docs; prefer the pre-auth one where present:

```sh
# POSIX: create an env if not present
python -m venv .venv_pre_auth
source .venv_pre_auth/bin/activate
pip install -r requirements.txt
# if you see .venv_pdfextract used in older docs, that's OK — just activate the env for this repo
```

3. Quick smoke-check that PyMuPDF is available if you plan to run PDF-based tests:

```sh
python -c "import fitz; print('PyMuPDF OK')"
```

> Note: Many tests skip heavy PDF tests if `fitz` is unavailable — see tests that use `pytest.mark.importorskip('fitz')`.

---

## 2) Running the extractor & quick examples

- Run a sample extraction (writes to `data/extracted`):

```sh
python scripts/run_sample_extraction.py user_1314
```

- Convert a single PDF to canonical text-only JSON (CLI):

```sh
python -m src.extract_pdf_preauth data/pdf_analysis/user_1314_credit_summary_2025-09-01_092724.pdf --out /tmp/user_1314.json
```

- Programmatic use (recommended for downstream repos):

```py
from src.extract_pdf_preauth import extract_to_canonical
canon = extract_to_canonical('/full/path/to/user.pdf')
```

- If you need layout metadata for debugging, call the lower-level builder with spans:

```sh
python scripts/pdf_to_ground_truth.py data/pdf_analysis/<file>.pdf --include-spans --out /tmp/out_with_spans.json
```

**Important**: The `extract_to_canonical` wrapper intentionally returns spans-disabled outputs for stable downstream consumption.

---

## 3) Canonical schema & conventions (must-read)

- Flat keys only for these items (no nested dicts):
  - `line_of_credit_accounts_open_count`, `line_of_credit_accounts_open_total`
  - `miscellaneous_accounts_open_count`, `miscellaneous_accounts_open_total`
  - `late_pays_lt2yr` and `late_pays_gt2yr` (always present; numeric default 0)
- Inquiries canonical key: `inquiries_lt6mo`. Legacy GTs may contain `inquiries_last_6_months` or `inquiries_6mo` — the canonicalizer accepts them and prefers `inquiries_lt6mo`.
- Transient layout keys (e.g., `_bbox`, `_page`, `_spans`) are intentionally omitted from canonical outputs unless `include_spans=True` is requested.
- `credit_factors` is emitted as a simplified list of `{factor, color, [hex]}` plus optional spans when requested.

If you change schema behavior, update the GT fixtures under `data/extracted/` and add a focused test demonstrating the intended change.

---

## 4) Tests & running locally

- Focused tests (fast):

```sh
pytest tests/test_gt_quality.py -q
pytest tests/test_pdf_extraction_ground_truth.py::test_user_1314_drop_bad_auth_preserved -q
```

- Full (PDF-heavy) tests:

```sh
pytest -q
```

- Integration test for the preauth wrapper:

```sh
pytest tests/integration/test_extract_pdf_preauth_integration.py -q
```

Test hints:
- PDF-based tests will use `pytest.importorskip('fitz')` so they skip gracefully if `fitz` is not installed.
- If a test fails due to ordering, note that we only enforce internal ordering invariants (account count before total, `late_pays_lt2yr` before `late_pays_gt2yr`).

---

## 5) Committing & PR workflow (short)

- Follow conventional commit prefixes (e.g., `feat(...)`, `fix(...)`, `test(...)`, `docs(...)`). Keep messages concise and add a short body if necessary.
- Run tests locally before committing. If tests fail, create a WIP branch `wip/<short-desc>` and push for review.
- When ready, push your branch and open a PR. Include the tests you ran and the failing tests you fixed.
- If you modify GT fixtures, add or update unit tests that justify the change and document why the GT change is needed in `docs/CHANGES.md`.

---

## 6) Developer notes & policy reminders

- Do not commit large binary assets (PDFs, images) — use git-lfs if unavoidable and notify reviewers.
- The project has an auditing requirement: save a conversation transcript for each AI interaction to `.github/ai-conversations/` (see repo `copilot-instructions.md` for details).
- If you need to change sampling/SMOTE behavior, prefer the SMOTE wrappers in `src/components/smote_sampler.py`.

---

## 7) Troubleshooting (common issues)

- "PyMuPDF import error" → activate the correct venv and `pip install -r requirements.txt` or `pip install pymupdf`.
- GT keyset mismatches → run the canonicalizer `python scripts/pdf_to_ground_truth.py <pdf>` and compare to the GT file with `pytest` failure output to see which keys differ. If a schema change is intended, add/update GT fixtures and tests.

---

## 8) Need help?

Open an issue or ping the maintainers listed in the repo. If you're making a large change, start a draft PR and include focused tests demonstrating the behavior.

Welcome aboard — thanks for contributing! 🎉