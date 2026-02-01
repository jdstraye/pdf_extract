Small extraction + mapping test harness cloned from pre_auth project.

Includes:
- `src/scripts/pdf_color_extraction.py` (partial)
- `scripts/pdf_to_ground_truth.py`
- `scripts/auto_map_unvalidated.py`
- a couple of tests that do *not* require PyMuPDF to run (they monkeypatch extracting behavior)
- **Usage guide:** see `docs/usage_guide.md` for detailed instructions on extracting PDFs, generating canonical GT JSON, running diffs, and integrating extraction into ML pipelines

Activate the project virtualenv and run tests:

    . .venv_pdfextract/bin/activate
    pip install -r requirements.txt  # include pymupdf if you need PDF tests
    pytest -q
