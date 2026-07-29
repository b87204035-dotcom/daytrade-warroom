import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_required_files():
    for p in ["index.html","app.js","styles.css",".github/workflows/warroom.yml","scripts/update_report.py","data/latest.json"]:
        assert (ROOT/p).exists(), p

def test_seed_json():
    json.loads((ROOT/"data/latest.json").read_text(encoding="utf-8"))
