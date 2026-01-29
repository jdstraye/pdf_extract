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
def test_boolean_indicators_match_gt(uid):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    raw = extract_pdf_all_fields(str(pdf), include_spans=False)
    canon = build_text_only_gt(raw, include_spans=False)

    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    for k in ('credit_freeze', 'fraud_alert', 'deceased'):
        gt_val = gt.get(k)
        ex_val = canon.get(k)
        # Normalize boolean-like values: allow 0/1/False/True equivalence
        def _to_int(v):
            if v is None:
                return None
            if isinstance(v, bool):
                return 1 if v else 0
            try:
                return int(v)
            except Exception:
                return None
        assert _to_int(ex_val) == _to_int(gt_val), f"Mismatch for {uid} {k}: gt={gt_val} ex={ex_val}"
