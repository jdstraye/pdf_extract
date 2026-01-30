import json
from pathlib import Path
import pytest

from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt

# Allowed nested structures (only these may be dicts at top-level)
ALLOWED_NESTED = {'credit_card_open_totals', 'public_records_details'}

# Suffixes to ignore when comparing keys/order
META_SUFFIXES = ('_bbox', '_page', '_spans')

GT_DIR = Path('data/extracted')


def _load_gt(p: Path):
    s = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(s, dict) and 'rec' in s and isinstance(s['rec'], dict):
        return s['rec']
    return s


def test_gt_no_unexpected_nested_structures():
    files = sorted(GT_DIR.glob('*_ground_truth.json'))
    bad = []
    for p in files:
        gt = _load_gt(p)
        for k, v in gt.items():
            if isinstance(v, dict) and k not in ALLOWED_NESTED:
                bad.append((p.name, k))
    assert not bad, f"Found unexpected nested structures: {bad}"


def test_gt_keyset_and_order_matches_pdf():
    # Build a canonical key order for each PDF and then ensure GT files have the same keys and same order
    files = sorted(GT_DIR.glob('*_ground_truth.json'))
    # compute union of keys across all canonical outputs (excluding allowed nested and meta suffixes)
    master_keys = None
    canonical_orders = {}
    for p in files:
        uid = p.stem.replace('_ground_truth', '')
        pdf = Path('data/pdf_analysis') / f"{uid}.pdf"
        rec = extract_pdf_all_fields(str(pdf), include_spans=False)
        canon = build_text_only_gt(rec, include_spans=False)
        # filter keys and normalize nested structures into their flat forms
        canon_keys = []
        # if nested late_pays present, expand to flat keys
        if 'late_pays' in canon and isinstance(canon.get('late_pays'), dict):
            canon_keys.extend(['late_pays_lt2yr', 'late_pays_gt2yr'])
        # account categories that may appear as nested dicts; normalize to flat keys
        account_mappings = [
            ('revolving_accounts_open', 'revolving_open_count', 'revolving_open_total'),
            ('installment_accounts_open', 'installment_open_count', 'installment_open_total'),
            ('real_estate_open', 'real_estate_open_count', 'real_estate_open_total'),
            ('line_of_credit_accounts_open', 'line_of_credit_accounts_open_count', 'line_of_credit_accounts_open_total'),
            ('miscellaneous_accounts_open', 'miscellaneous_accounts_open_count', 'miscellaneous_accounts_open_total'),
        ]
        for nkey, ckey, tkey in account_mappings:
            if nkey in canon and isinstance(canon.get(nkey), dict):
                canon_keys.extend([ckey, tkey])
            elif ckey in canon or tkey in canon:
                if ckey in canon:
                    canon_keys.append(ckey)
                if tkey in canon:
                    canon_keys.append(tkey)
        # include other non-meta, non-nested keys
        for k in list(canon.keys()):
            if k in ('late_pays',) or k in [m[0] for m in account_mappings] or k in ALLOWED_NESTED:
                continue
            if k.endswith(META_SUFFIXES):
                continue
            if k not in canon_keys:
                canon_keys.append(k)
        canonical_orders[p.name] = canon_keys
        if master_keys is None:
            master_keys = list(canon_keys)
        else:
            # ensure master contains all keys seen
            for k in canon_keys:
                if k not in master_keys:
                    master_keys.append(k)

    # Now build master set as union of canonical keys and actual GT keys (excluding allowed nested and meta suffixes)
    master_set = set(master_keys)
    for p in files:
        gt = _load_gt(p)
        gt_extra = [k for k in list(gt.keys()) if not k.endswith(META_SUFFIXES) and k not in ALLOWED_NESTED]
        for k in gt_extra:
            if k not in master_set:
                master_set.add(k)
    # ensure master_keys includes any extras found in GTs (preserve existing order but append extras)
    for k in sorted(master_set):
        if k not in master_keys:
            master_keys.append(k)

    for p in files:
        gt = _load_gt(p)
        gt_keys = [k for k in list(gt.keys()) if not k.endswith(META_SUFFIXES) and k not in ALLOWED_NESTED]
        assert set(gt_keys) == set(master_keys), f"GT {p.name} has keyset mismatch. Expected {sorted(master_keys)} vs {sorted(set(gt_keys))}"
        # check order: the GT keys should follow the PDF canonical order for that file
        expected_order = canonical_orders[p.name]
        # compare only relative ordering of master keys as they appear in expected_order
        # map each key in master_keys to its index in expected_order or large number if missing
        order_indices = {k: (expected_order.index(k) if k in expected_order else 9999) for k in master_keys}
        gt_indices = [order_indices[k] for k in gt_keys]
        assert gt_indices == sorted(gt_indices), f"GT {p.name} key order does not match PDF canonical order"
