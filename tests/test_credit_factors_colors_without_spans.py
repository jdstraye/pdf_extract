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
def test_credit_factors_colors_present_without_spans(uid):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    # Do NOT request spans; ensure colors are still derived into credit_factors
    raw = extract_pdf_all_fields(str(pdf), include_spans=False)
    canon = build_text_only_gt(raw, include_spans=False)

    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    import re
    def norm(s):
        return re.sub(r'[^a-z0-9]+', '', (s or '').lower())

    gt_cfs = { norm(f.get('factor')): f.get('color') for f in gt.get('credit_factors', []) }
    ex_cfs = { norm(f.get('factor')): f.get('color') for f in canon.get('credit_factors', []) }

    for k, gt_color in gt_cfs.items():
        if gt_color is None:
            continue
        ex_color = ex_cfs.get(k)
        assert ex_color == gt_color, f"Color mismatch for factor '{k}' in {uid}: gt={gt_color} ex={ex_color}"
