Small extraction + mapping test harness cloned from pre_auth project.

Includes:
- `src/scripts/pdf_color_extraction.py` (partial)
- `scripts/pdf_to_ground_truth.py`
- `scripts/auto_map_unvalidated.py`
- a couple of tests that do *not* require PyMuPDF to run (they monkeypatch extracting behavior)
- **Usage guide:** see `docs/usage_guide.md` for detailed instructions on extracting PDFs, generating canonical GT JSON, running diffs, and integrating extraction into ML pipelines

Quick example: importing the preauth-friendly extractor from a sibling checkout or via PYTHONPATH

Add this repo to `PYTHONPATH` (POSIX shell) and call the extractor programmatically:

```sh
export PYTHONPATH="$PYTHONPATH:/path/to/pdf_extract.git"
python -c "from src.extract_pdf_preauth import extract_to_canonical, json; print(json.dumps(extract_to_canonical('/path/to/user.pdf'), indent=2))"
```

Other convenient options to consume this extractor from another repo:

- Editable install (from the repo root):

```sh
# run once from the pdf_extract repo root
pip install -e .
# then in your code
from src.extract_pdf_preauth import extract_to_canonical
```

- Install directly from git (useful in CI):

```sh
pip install git+https://github.com/<your-org>/pdf_extract.git@main
```

- Git subtree/submodule or simple checkout and add to `sys.path` (POSIX Python example):

```py
import sys
from pathlib import Path
sys.path.insert(0, str(Path('../pdf_extract.git').resolve()))
from src.extract_pdf_preauth import extract_to_canonical
```

- Import directly via `importlib` without installing (advanced):

```py
from importlib import util
from pathlib import Path
spec = util.spec_from_file_location('extract_pdf_preauth', str(Path('../pdf_extract.git')/ 'src' / 'extract_pdf_preauth.py'))
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)
canon = mod.extract_to_canonical('/path/to/user.pdf')
```

This produces the canonical, text-only JSON (no `_bbox`, `_page`, `_spans`) suitable for downstream ingestion.

Activate the project virtualenv and run tests:

    . .venv_pdfextract/bin/activate
    pip install -r requirements.txt  # include pymupdf if you need PDF tests
    pytest -q
