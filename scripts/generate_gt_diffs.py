#!/usr/bin/env python3
"""Generate GT diffs report and write to .reports/gt_diff_report.json"""
import json, re, sys
from pathlib import Path
from collections import Counter

from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt

GT_DIR = Path('data/extracted')
OUT_DIR = Path('.reports')
OUT_FILE = OUT_DIR / 'gt_diff_report.json'

print('GT dir:', GT_DIR)
if not GT_DIR.exists():
    print('Error: GT dir does not exist', file=sys.stderr)
    sys.exit(1)

def load_json(path):
    s = Path(path).read_text(encoding='utf-8')
    try:
        obj = json.loads(s)
    except json.decoder.JSONDecodeError:
        s_fixed = re.sub(r'"date"\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', r'"date": "\1"', s)
        obj = json.loads(s_fixed)
    if isinstance(obj, dict) and 'rec' in obj and isinstance(obj['rec'], dict):
        return obj['rec']
    return obj

# Normalization helper (copied from tests)
def _normalize_aliases(d):
    d = dict(d)
    if 'inquiries_6mo' in d and 'inquiries_last_6_months' not in d:
        d['inquiries_last_6_months'] = d['inquiries_6mo']
    if 'inquiries_last_6_months' in d and 'inquiries_6mo' not in d:
        d['inquiries_6mo'] = d['inquiries_last_6_months']
    if 'collections_open' not in d and 'collections_open_count' in d:
        d['collections_open'] = d.get('collections_open_count')
    if 'collections_closed' not in d and 'collections_closed_count' in d:
        d['collections_closed'] = d.get('collections_closed_count')
    nested_mappings = [
        ('revolving_accounts_open', 'revolving_open_count', 'revolving_open_total'),
        ('installment_accounts_open', 'installment_open_count', 'installment_open_total'),
        ('real_estate_open', 'real_estate_open_count', 'real_estate_open_total'),
        ('line_of_credit_accounts_open', 'line_of_credit_accounts_open_count', 'line_of_credit_accounts_open_total'),
        ('miscellaneous_accounts_open', 'miscellaneous_accounts_open_count', 'miscellaneous_accounts_open_total'),
    ]
    for nkey, ckey, tkey in nested_mappings:
        if nkey in d and ckey not in d:
            nd = d.get(nkey, {})
            d[ckey] = nd.get('count') if isinstance(nd, dict) else None
            d[tkey] = nd.get('amount') if isinstance(nd, dict) else None
        if ckey in d and nkey not in d:
            d[nkey] = {'count': d.get(ckey), 'amount': d.get(tkey)}
    if 'collections' in d and 'collections_open' not in d:
        c = d.get('collections', {})
        if isinstance(c, dict):
            d['collections_open'] = c.get('open')
            d['collections_closed'] = c.get('closed')
    if 'collections_open' in d and 'collections' not in d:
        d['collections'] = {'open': d.get('collections_open'), 'closed': d.get('collections_closed')}
    if 'credit_factors' in d and isinstance(d['credit_factors'], list):
        d['red_credit_factors_count'] = sum(1 for f in d['credit_factors'] if f.get('color') == 'red')
        d['green_credit_factors_count'] = sum(1 for f in d['credit_factors'] if f.get('color') == 'green')
        d['black_credit_factors_count'] = sum(1 for f in d['credit_factors'] if f.get('color') == 'black')
    if isinstance(d.get('credit_score'), dict):
        cs = d.get('credit_score', {})
        d['credit_score'] = cs.get('value')
        d['credit_score_color'] = cs.get('color')
    if 'pdf_file' in d:
        pf = d.get('pdf_file')
        d['source'] = pf
        d['filename'] = pf.split('/')[-1]
        d.pop('pdf_file', None)
    if 'late_pays' in d and isinstance(d['late_pays'], dict):
        lp = d['late_pays']
        d['late_pays_2yr'] = lp.get('last_2_years')
        d['late_pays_gt2yr'] = lp.get('last_over_2_years')
    if 'late_pays_2yr' in d and 'late_pays' not in d:
        d['late_pays'] = {'last_2_years': d.get('late_pays_2yr'), 'last_over_2_years': d.get('late_pays_gt2yr')}
    if 'credit_card_open_totals_no_retail' in d and 'credit_card_open_totals' not in d:
        d['credit_card_open_totals'] = d.pop('credit_card_open_totals_no_retail')
    if 'credit_card_open_totals' in d and isinstance(d['credit_card_open_totals'], dict):
        cc = dict(d['credit_card_open_totals'])
        if 'utilization_percent' in cc and 'Percent' not in cc:
            cc['Percent'] = cc.pop('utilization_percent')
        if 'payment' in cc and 'Payment' not in cc:
            cc['Payment'] = cc.pop('payment')
        d['credit_card_open_totals'] = cc
    if 'credit_card_open_totals' not in d:
        d['credit_card_open_totals'] = None
    def _norm_addr(s):
        s2 = s.replace(',\\s', ', ')
        s2 = s2.rstrip(', ')
        s2 = s2.replace(', ,', ',')
        s2 = s2.replace(', ,', ',')
        s2 = s2.replace(',  ', ', ')
        s2 = s2.replace(', ,', ',')
        s2 = ' '.join(s2.split())
        s2 = re.sub(r',\\s*(\\d{5})$', r' \\1', s2)
        return s2
    if 'address' in d:
        if isinstance(d['address'], str):
            d['address'] = [_norm_addr(d['address'])]
        elif isinstance(d['address'], list):
            d['address'] = [_norm_addr(x) for x in d['address']]
    if 'credit_factors' in d and isinstance(d['credit_factors'], list):
        simplified = []
        for f in d['credit_factors']:
            if isinstance(f, dict):
                simplified.append({'factor': f.get('factor'), 'color': f.get('color')})
            else:
                simplified.append({'factor': f, 'color': None})
        d['credit_factors'] = simplified
    return d


def simplify_cf_list(cf_list):
    def normtext(s):
        return re.sub(r'[^a-z0-9]+', '', (s or '').lower())
    out = []
    for f in (cf_list or []):
        if not isinstance(f, dict):
            out.append((None, normtext(str(f))))
        else:
            out.append((f.get('color'), normtext(f.get('factor',''))))
    return out


def _serialize_counter(c):
    """Convert a Counter with tuple keys into a JSON-serializable dict."""
    out_c = {}
    for kk, vv in c.items():
        if isinstance(kk, tuple):
            col, txt = kk
            key = f"{col if col is not None else 'None'}||{txt}"
        else:
            key = str(kk)
        out_c[key] = vv
    return out_c


def compare_and_report(gt_path):
    pdf_name = Path(gt_path).stem.replace('_ground_truth','')
    pdf_path = Path('data/pdf_analysis') / f"{pdf_name}.pdf"
    gt = load_json(gt_path)
    try:
        raw = extract_pdf_all_fields(str(pdf_path))
        # canonicalize extractor output to the text-only GT shape for fair comparison
        extracted = build_text_only_gt(raw, include_spans=False)
    except Exception as e:
        extracted = {'_extract_error': str(e)}
    na = _normalize_aliases(gt)
    nb = _normalize_aliases(extracted)
    keys = set(list(na.keys()) + list(nb.keys()))
    diffs = []
    for k in sorted(keys):
        a = na.get(k)
        b = nb.get(k)
        if k == 'credit_factors' and 'credit_factors' in na and 'credit_factors' in nb:
            A = Counter(simplify_cf_list(a))
            B = Counter(simplify_cf_list(b))
            if A != B:
                diffs.append({'key': k, 'type': 'credit_factors_mismatch', 'gt': _serialize_counter(A), 'ex': _serialize_counter(B)})
        else:
            if a != b:
                diffs.append({'key': k, 'gt': a, 'ex': b})
    return pdf_name, diffs


def main():
    files = sorted(GT_DIR.glob('*_ground_truth.json'))
    out = {}
    for f in files:
        name, diffs = compare_and_report(f)
        out[name] = diffs
        print('Processed', name, 'diffs:', len(diffs))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, default=str, indent=2), encoding='utf-8')
    print('Wrote', OUT_FILE)

if __name__ == '__main__':
    main()
