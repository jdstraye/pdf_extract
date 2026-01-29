import json
from pathlib import Path
import pytest
pytest.importorskip("fitz", reason="PyMuPDF required for PDF extraction")

from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt

VALID_USERS = [
    'user_1131_credit_summary_2025-09-01_132805',
    'user_1140_credit_summary_2025-09-01_132703',
    'user_1314_credit_summary_2025-09-01_092724',
    'user_582_credit_summary_2025-09-01_100800',
    'user_584_credit_summary_2025-09-01_103626',
    'user_692_credit_summary_2025-09-01_105038',
    'user_705_credit_summary_2025-09-01_101711',
    'user_1514_credit_summary_2025-09-01_145557',
    'user_1254_credit_summary_2025-09-01_095528',
    'user_618_credit_summary_2025-09-01_101143',
]

@pytest.mark.parametrize('uid', VALID_USERS)
def test_credit_score_color_matches_gt_when_specified(uid):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    raw = extract_pdf_all_fields(str(pdf), include_spans=True)
    canon = build_text_only_gt(raw, include_spans=True)

    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    gt_color = gt.get('credit_score_color')
    ex_color = canon.get('credit_score_color')
    # only assert when GT specifies a color
    if gt_color is not None:
        assert ex_color is not None, f"Missing credit_score_color for {uid}"
        assert ex_color == gt_color, f"Color mismatch for {uid}: gt={gt_color} ex={ex_color}"
