import json
from pathlib import Path
import pytest
pytest.importorskip("fitz", reason="PyMuPDF required for PDF extraction")

from src.extract_pdf_preauth import extract_to_canonical
from tests.test_pdf_extraction_ground_truth import load_json, compare_dicts

GT_DIR = Path('data/extracted')
PDF_DIR = Path('data/pdf_analysis')


@pytest.mark.parametrize('gt_path', sorted(GT_DIR.glob('*_ground_truth.json')))
def test_all_validated_pdfs(gt_path):
    # For each ground-truth file, compare canonical extractor output for the same PDF
    uid = gt_path.stem.replace('_ground_truth', '')
    pdf = PDF_DIR / f"{uid}.pdf"
    if not pdf.exists():
        pytest.skip(f"Missing PDF for {uid}")
    gt = load_json(gt_path)
    canon = extract_to_canonical(pdf)
    assert compare_dicts(canon, gt), f"Mismatch for {uid} (canonical extractor vs GT)"
