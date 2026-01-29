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
    'user_1254_credit_summary_2025-09-01_095528',
    'user_1514_credit_summary_2025-09-01_145557',
]

@pytest.mark.parametrize('uid', VALID_USERS)
def test_inquiries_and_late_pays_and_collections(uid):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    raw = extract_pdf_all_fields(str(pdf), include_spans=True)
    canon = build_text_only_gt(raw, include_spans=True)

    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    # inquiries: when GT specifies a value, require extractor to match
    if gt.get('inquiries_last_6_months') is not None:
        assert canon.get('inquiries_last_6_months') == gt.get('inquiries_last_6_months')
    # late pays: compare flattened keys when present
    if gt.get('late_pays_2yr') is not None or gt.get('late_pays_gt2yr') is not None:
        assert canon.get('late_pays_2yr') == gt.get('late_pays_2yr')
        assert canon.get('late_pays_gt2yr') == gt.get('late_pays_gt2yr')
    # collections counts
    if gt.get('collections_open') is not None:
        assert canon.get('collections_open') == gt.get('collections_open')
    if gt.get('collections_closed') is not None:
        assert canon.get('collections_closed') == gt.get('collections_closed')
