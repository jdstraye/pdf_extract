import sys
from pathlib import Path
# ensure project root is on sys.path for imports like 'scripts' and 'src'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_addoption(parser):
    """Add CLI options used by the ground-truth suite (mirrors pre_auth hooks)."""
    parser.addoption("--pdf_dir", action="store", default="data/pdf_analysis", help="Directory containing PDF fixtures")
    parser.addoption("--ground_truth_dir", action="store", default="data/extracted", help="Directory with ground-truth JSONs")
    parser.addoption("--user_id", action="store", default=None, help="(Optional) single user id to focus tests on")
    parser.addoption("--n_pdfs", action="store", default=10, type=int, help="(Optional) number of PDFs to sample when many are present")

