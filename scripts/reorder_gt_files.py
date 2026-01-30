"""Reorder GT JSON files in data/extracted to a canonical, human-friendly sequence.

Desired order per user request:
1) Top line: credit_score, monthly_payments, credit_freeze, fraud_alert, deceased
2) Credit Report Details: age, address, revolving accounts, real_estate, line of credit, installment, miscellaneous, public_records, collections, inquiries, late_pays
3) credit_factors
4) Anything remaining (preserve alphabetical order)

This script preserves keys and values exactly (no renaming or value changes). It handles legacy "rec" wrappers.
"""
from pathlib import Path
import json

GT_DIR = Path('data/extracted')
files = sorted(GT_DIR.glob('*_ground_truth.json'))

# canonical sequences of keys (use both nested and flat key names when appropriate)
TOP_LINE = ['credit_score', 'monthly_payments', 'credit_freeze', 'fraud_alert', 'deceased']
DETAILS = [
    'age', 'address',
    # revolving: nested or flat
    'revolving_accounts_open', 'revolving_open_count', 'revolving_open_total',
    'real_estate_open', 'real_estate_open_count', 'real_estate_open_total',
    'line_of_credit_accounts_open', 'line_of_credit_accounts_open_count', 'line_of_credit_accounts_open_total',
    'installment_accounts_open', 'installment_open_count', 'installment_open_total',
    'miscellaneous_accounts_open', 'miscellaneous_accounts_open_count', 'miscellaneous_accounts_open_total',
    'public_records', 'public_records_details',
    'collections', 'collections_open', 'collections_closed', 'collections_open_count', 'collections_closed_count',
    'inquiries_last_6_months', 'inquiries_6mo', 'late_pays', 'late_pays_lt2yr', 'late_pays_gt2yr'
]

for p in files:
    try:
        s = p.read_text(encoding='utf-8')
        obj = json.loads(s)
    except Exception as e:
        print('SKIP (invalid json):', p, e)
        continue
    wrapped = False
    if isinstance(obj, dict) and 'rec' in obj and isinstance(obj['rec'], dict):
        src = obj['rec']
        wrapped = True
    else:
        src = obj
    new = {}
    # 1) top line
    for k in TOP_LINE:
        if k in src:
            new[k] = src[k]
    # 2) credit report details
    for k in DETAILS:
        if k in src and k not in new:
            new[k] = src[k]
    # 3) credit_factors
    if 'credit_factors' in src and 'credit_factors' not in new:
        new['credit_factors'] = src['credit_factors']
    # 4) append remaining keys in original order
    for k in src:
        if k not in new:
            new[k] = src[k]
    # write back preserving wrapper shape
    out_obj = {'rec': new} if wrapped else new
    p.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Reordered:', p.name)
print('Done')
