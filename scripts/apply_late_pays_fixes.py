"""Apply late_pays fixes to GT files based on the triage report markdown.

This script parses the triage report produced earlier and updates the matching
`data/extracted/*_ground_truth.json` files so that their `late_pays` nested
structure and the flat `late_pays_lt2yr` / `late_pays_gt2yr` keys match the
'extracted' values from the report.

Usage:
    python scripts/apply_late_pays_fixes.py --report .github/ai-conversations/triage_report_20260131-212501.md

The script makes in-place edits and writes backups `<file>.bak` before modifying.
"""
from pathlib import Path
import json
import re
import argparse

def parse_report(path: Path):
    s = path.read_text()
    sections = s.split('\n## ')[1:]
    fixes = {}
    for sec in sections:
        header = sec.splitlines()[0].strip()
        if '### Differences' not in sec:
            continue
        diff_block = sec.split('### Differences\n')[1].split('\n\n')[0]
        for ln in diff_block.splitlines():
            ln = ln.strip()
            if ln.startswith('- **late_pays**') and 'EXTRACTED=' in ln:
                # extract the EXTRACTED dict
                m = re.search(r"EXTRACTED=`([^`]*)`", ln)
                if m:
                    extracted_str = m.group(1)
                    try:
                        extracted = json.loads(extracted_str.replace("'", '"'))
                    except Exception:
                        # fallback to ast
                        import ast
                        extracted = ast.literal_eval(extracted_str)
                    fixes[header] = extracted
    return fixes


def apply_fixes(fixes: dict):
    for pdf_name, latep in fixes.items():
        # pdf_name is like 'user_1131_credit_summary_2025-09-01_132805'
        gt_name = f"data/extracted/{pdf_name}_ground_truth.json"
        p = Path(gt_name)
        if not p.exists():
            print('missing GT file for', pdf_name, 'expected at', p)
            continue
        bak = p.with_suffix(p.suffix + '.bak')
        bak.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
        obj = json.loads(p.read_text(encoding='utf-8'))
        # write flat canonical late_pays keys (avoid nested representation)
        lt = int(latep.get('last_2_years') or 0)
        gt = int(latep.get('last_over_2_years') or 0)
        obj.pop('late_pays', None)
        obj['late_pays_lt2yr'] = lt
        obj['late_pays_gt2yr'] = gt
        p.write_text(json.dumps(obj, indent=2), encoding='utf-8')
        print('Updated', p)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', default='.github/ai-conversations/triage_report_20260131-212501.md')
    args = ap.parse_args()
    report = Path(args.report)
    if not report.exists():
        print('Report not found:', report)
        raise SystemExit(1)
    fixes = parse_report(report)
    if not fixes:
        print('No late_pays fixes found in report')
        raise SystemExit(0)
    apply_fixes(fixes)
    print('Done.')
