"""Generate a triage report for PDFs whose extraction doesn't match ground truth.
Produces a markdown report listing differing keys and showing extracted evidence where available.
"""
import json
from pathlib import Path
from datetime import datetime
import sys
from pathlib import Path
# Ensure repo root on sys.path so tests and scripts can be imported when running standalone
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
from tests.test_pdf_extraction_ground_truth import load_json, compare_dicts, _normalize_aliases, pdf_to_ground_truth_name
from src.scripts.pdf_color_extraction import extract_pdf_all_fields
from scripts.pdf_to_ground_truth import build_text_only_gt

PDF_DIR = Path('data/pdf_analysis')
GT_DIR = Path('data/extracted')

pdfs = sorted([p for p in PDF_DIR.glob('user_*_credit_summary_2025*.pdf')])
report = []
for pdf in pdfs:
    gt_path = GT_DIR / pdf_to_ground_truth_name(str(pdf))
    if not gt_path.exists():
        continue
    gt = load_json(str(gt_path))
    ex = extract_pdf_all_fields(str(pdf))
    if compare_dicts(ex, gt):
        continue
    # compute normalized versions for diff
    na = _normalize_aliases(gt)
    nb = _normalize_aliases(build_text_only_gt(ex, include_spans=False))
    diff_keys = []
    for k in sorted(set(list(na.keys()) + list(nb.keys()))):
        if na.get(k) != nb.get(k):
            diff_keys.append((k, na.get(k), nb.get(k)))
    # gather evidence: lines and credit_factors
    evidence = {
        'extracted_credit_factors': ex.get('credit_factors'),
        'extracted_all_lines_obj_sample': ex.get('all_lines_obj')[:10] if ex.get('all_lines_obj') else [],
    }
    report.append({'pdf': str(pdf), 'gt_file': str(gt_path), 'diff_keys': diff_keys, 'evidence': evidence})

# Write report
out_dir = Path('.github/ai-conversations')
out_dir.mkdir(parents=True, exist_ok=True)
now = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
out_path = out_dir / f'triage_report_{now}.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('# Triage Report\n\n')
    f.write('Generated: %s UTC\n\n' % now)
    for item in report:
        f.write('## %s\n' % Path(item['pdf']).stem)
        f.write(f'- PDF: `{item["pdf"]}`\n')
        f.write(f'- GT: `{item["gt_file"]}`\n')
        f.write('\n')
        f.write('### Differences\n')
        for k, gv, ev in item['diff_keys']:
            f.write(f'- **{k}**: GT=`{gv}`  |  EXTRACTED=`{ev}`\n')
        f.write('\n')
        f.write('### Evidence (extracted)\n')
        f.write('```json\n')
        json.dump(item['evidence'], f, indent=2, ensure_ascii=False)
        f.write('\n```\n\n')

print('Wrote triage report to', out_path)
