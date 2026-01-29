import json
from pathlib import Path
import pytest
pytest.importorskip("fitz", reason="PyMuPDF required for PDF extraction")

from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt


def test_table_detection_user_1314():
    pdf = Path('data/pdf_analysis/user_1314_credit_summary_2025-09-01_092724.pdf')
    raw = extract_pdf_all_fields(str(pdf), include_spans=False)
    canon = build_text_only_gt(raw, include_spans=False)

    gt_path = Path('data/extracted/user_1314_credit_summary_2025-09-01_092724_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    # Age and address should be detected
    assert canon.get('age') == gt.get('age')
    assert canon.get('address') is not None

    # Account tables should be present in canonicalized output (flat keys are expected)
    assert canon.get('revolving_open_count') == gt.get('revolving_accounts_open').get('count')
    assert canon.get('revolving_open_total') == gt.get('revolving_accounts_open').get('amount')
    assert canon.get('installment_open_count') == gt.get('installment_accounts_open').get('count')
    assert canon.get('installment_open_total') == gt.get('installment_accounts_open').get('amount')
