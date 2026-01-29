import json
from pathlib import Path
from collections import Counter
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


def _norm_factor_tuple(f):
    import re
    clr = f.get('color') if isinstance(f, dict) else None
    txt = (f.get('factor') if isinstance(f, dict) else str(f)) or ''
    txtn = re.sub(r'[^a-z0-9]+','', txt.lower())
    return (clr, txtn)


@pytest.mark.parametrize('uid', VALID_USERS)
def test_credit_factors_match_gt(uid):
    pdf = Path(f'data/pdf_analysis/{uid}.pdf')
    raw = extract_pdf_all_fields(str(pdf), include_spans=True)
    canon = build_text_only_gt(raw, include_spans=True)

    gt_path = Path(f'data/extracted/{uid}_ground_truth.json')
    gt = json.loads(gt_path.read_text(encoding='utf-8'))
    if isinstance(gt, dict) and 'rec' in gt:
        gt = gt['rec']

    # Build counters of (color,normalized_text)
    A = Counter([_norm_factor_tuple(f) for f in gt.get('credit_factors',[])])
    B = Counter([_norm_factor_tuple(f) for f in canon.get('credit_factors',[])])

    # Require the set of factor texts to match
    assert set([t for (_,t) in A.elements()]) == set([t for (_,t) in B.elements()]), f"Factor text mismatch for {uid}"

    # When GT specifies colors for factors, require the extractor to match those colors per-factor
    # Build mapping: normalized_text -> multiset of colors
    from collections import defaultdict
    def build_color_map(cnt, src):
        m = defaultdict(list)
        for c in src:
            clr, txt = _norm_factor_tuple(c)
            m[txt].append(clr)
        return {k: Counter(v) for k, v in m.items()}

    map_gt = build_color_map(A, gt.get('credit_factors', []))
    map_ex = build_color_map(B, canon.get('credit_factors', []))

    for txt, gc in map_gt.items():
        # only enforce when GT has non-empty color counts (i.e., colors were annotated)
        if sum((1 for k,v in gc.items() if k is not None and v>0)) == 0:
            continue
        ex_colors = map_ex.get(txt, Counter())
        assert gc == ex_colors, f"Color mismatch for factor '{txt}' in {uid}: gt={gc} ex={ex_colors}"
