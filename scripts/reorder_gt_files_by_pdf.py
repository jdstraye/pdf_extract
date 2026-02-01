"""Reorder GT JSON files to match the canonical key order derived from the PDF for each file.

This places keys in the same sequence as `build_text_only_gt` produces for the corresponding PDF,
with the late_pays nested expanded to flat keys and account categories normalized to flat count/total keys.
"""
from pathlib import Path
import json
from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt

GT_DIR = Path('data/extracted')
PDF_DIR = Path('data/pdf_analysis')

account_mappings = [
    ('revolving_accounts_open', 'revolving_open_count', 'revolving_open_total'),
    ('installment_accounts_open', 'installment_open_count', 'installment_open_total'),
    ('real_estate_open', 'real_estate_open_count', 'real_estate_open_total'),
    ('line_of_credit_accounts_open', 'line_of_credit_accounts_open_count', 'line_of_credit_accounts_open_total'),
    ('miscellaneous_accounts_open', 'miscellaneous_accounts_open_count', 'miscellaneous_accounts_open_total'),
]

for p in sorted(GT_DIR.glob('*_ground_truth.json')):
    uid = p.stem.replace('_ground_truth', '')
    pdf = PDF_DIR / f"{uid}.pdf"
    try:
        rec = extract_pdf_all_fields(str(pdf), include_spans=False)
        canon = build_text_only_gt(rec, include_spans=False)
    except Exception:
        print('SKIP (extract failed):', p.name)
        continue
    # build expected order
    expected = []
    if 'late_pays' in canon and isinstance(canon.get('late_pays'), dict):
        expected.extend(['late_pays_lt2yr', 'late_pays_gt2yr'])
    for nkey, ckey, tkey in account_mappings:
        if nkey in canon and isinstance(canon.get(nkey), dict):
            expected.extend([ckey, tkey])
        else:
            if ckey in canon:
                expected.append(ckey)
            if tkey in canon:
                expected.append(tkey)
    # append any other keys from canon that are not meta or nested
    for k in canon:
        if k in ('late_pays',) or k in [m[0] for m in account_mappings] or k in ('credit_card_open_totals','public_records_details'):
            continue
        if k not in expected:
            expected.append(k)
    # Now reorder GT p according to expected
    try:
        s = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        print('SKIP (invalid json):', p.name)
        continue
    wrapped = isinstance(s, dict) and 'rec' in s and isinstance(s['rec'], dict)
    src = s['rec'] if wrapped else s
    new = {}
    for k in expected:
        if k in src:
            new[k] = src[k]
    # append the rest in original order
    for k in src:
        if k not in new:
            new[k] = src[k]
    out = {'rec': new} if wrapped else new
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Reordered to PDF order:', p.name)
print('Done')
