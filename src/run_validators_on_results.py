import os
import json
from pathlib import Path
from validators import run_all_checks


def process_folder(src_dir: str = 'results', out_dir: str = 'results_checked'):
    src = Path(src_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        print(f"Source folder '{src}' not found")
        return
    for p in src.glob('*.json'):
        try:
            with open(p, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load {p}: {e}")
            continue
        # If parser output is a list (sections), wrap into expected dict
        if isinstance(data, list):
            data_wrapped = {"sections": data, "file": str(p)}
        else:
            data_wrapped = data
        res = run_all_checks(data_wrapped)
        out_p = out / p.name
        with open(out_p, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print(f"Processed {p.name} -> {out_p}")


if __name__ == '__main__':
    process_folder()
