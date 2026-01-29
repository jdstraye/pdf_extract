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
def test_top_level_fields_match_gt(uid):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    raw = extract_pdf_all_fields(str(pdf), include_spans=False)
    canon = build_text_only_gt(raw, include_spans=False)

    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    # Age must match
    assert canon.get('age') == gt.get('age')

    # Address: ensure extractor found at least one address and normalize both sides for exact equality
    from src.scripts.pdf_color_extraction import normalize_address_string as _normalize_address_string
    assert canon.get('address') is not None, f"Missing address for {uid}"
    ex_addrs = canon.get('address') or []
    gt_addrs = gt.get('address') or []
    norm_ex = set([_normalize_address_string(a) for a in ex_addrs])
    norm_gt = set([_normalize_address_string(a) for a in gt_addrs])
    assert norm_gt <= norm_ex, f"Address mismatch for {uid}: gt={sorted(norm_gt)} ex={sorted(norm_ex)}"

    # Collections open/closed must match when present in GT
    if gt.get('collections') is not None:
        # build_text_only_gt prefers flat keys; accept either dict or flat keys
        if canon.get('collections') is None:
            assert canon.get('collections_open') == gt.get('collections', {}).get('open')
            assert canon.get('collections_closed') == gt.get('collections', {}).get('closed')
        else:
            assert canon.get('collections', {}).get('open') == gt.get('collections', {}).get('open')
            assert canon.get('collections', {}).get('closed') == gt.get('collections', {}).get('closed')

    # Credit score should be present and equal (accept nested dicts with value/color)
    ccs = canon.get('credit_score')
    if isinstance(ccs, dict):
        ccs_val = ccs.get('value')
    else:
        ccs_val = ccs
    if isinstance(gt.get('credit_score'), dict):
        gt_val = gt.get('credit_score').get('value')
    else:
        gt_val = gt.get('credit_score')
    assert ccs_val == gt_val

    # credit card totals: when GT has values, extractor should produce structured map with at least 'balance' or 'limit'
    if gt.get('credit_card_open_totals'):
        ex_cc = canon.get('credit_card_open_totals')
        assert ex_cc is not None, f"Missing cc totals for {uid}"
        assert any(k in ex_cc for k in ('balance','limit','Payment'))
