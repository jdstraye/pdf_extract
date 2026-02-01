import json
from pathlib import Path
import pytest
pytest.importorskip("fitz", reason="PyMuPDF required for PDF extraction")

from src.extract_pdf_preauth import extract_to_canonical
from tests.test_pdf_extraction_ground_truth import load_json, compare_dicts


def test_single_pdf_matches_ground_truth():
    # pick a validated sample (one of the existing validated users)
    uid = 'user_1314_credit_summary_2025-09-01_092724'
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    assert pdf.exists(), 'PDF missing for sample test'
    assert gt_path.exists(), 'GT missing for sample test'

    canon = extract_to_canonical(pdf)
    gt = load_json(gt_path)
    assert compare_dicts(canon, gt), 'Canonical extractor output did not match GT (ignoring transient keys)'
