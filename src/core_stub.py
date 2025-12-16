#!/usr/bin/env python3
import json
import sys
import os

# Import `run_all_checks` robustly so the script works when run:
# - as a package (python -m src.core_stub) where relative import works,
# - directly as a script (python src/core_stub.py) where relative import fails.
try:
    # preferred when executed as a package
    from .validators import run_all_checks
except Exception:
    try:
        # try top-level import (when src is on PYTHONPATH)
        from validators import run_all_checks
    except Exception:
        # fallback: load validators.py by path
        import importlib.util
        validators_path = os.path.join(os.path.dirname(__file__), 'validators.py')
        spec = importlib.util.spec_from_file_location('validators', validators_path)
        validators = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validators)
        run_all_checks = validators.run_all_checks


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "no file path provided"}, ensure_ascii=False))
        sys.exit(1)
    path = sys.argv[1]
    # If the input is JSON (parser output), load and validate it
    _, ext = os.path.splitext(path)
    ext = ext.lower().lstrip('.')
    if ext == 'json':
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(json.dumps({"error": f"failed to read json: {e}"}, ensure_ascii=False))
            sys.exit(2)

        out = run_all_checks(data)
        out.setdefault("generated_at", None)
        out.setdefault("core_version", "0.1.0-dev")
        print(json.dumps(out, ensure_ascii=False))
        return

    # Fallback: produce a minimal result for non-JSON inputs
    p = os.path.abspath(path)
    file_type = 'pdf' if ext == 'pdf' else 'docx' if ext == 'docx' else 'unknown'
    res = {
        "file": p,
        "file_type": file_type,
        "summary": {"errors": 0, "warnings": 0, "info": 0},
        "issues": []
    }
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
