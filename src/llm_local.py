import subprocess
import json
from pathlib import Path
from typing import Optional


def find_llama_binary() -> Optional[Path]:
    root = Path(__file__).resolve().parent.parent
    # common places
    candidates = [
        root / 'llama' / 'main.exe',
        root / 'llama' / 'main',
        root / 'llama' / 'llama-cli.exe',
        root / 'llama' / 'llama-cli',
        root / 'llama' / 'llama.exe',
        root / 'llama' / 'llama',
        root / 'main.exe',
        root / 'main',
    ]
    for p in candidates:
        if p.exists():
            return p
    # search repo for main.exe
    for p in root.rglob('main.exe'):
        return p
    return None


def find_model_file() -> Optional[Path]:
    root = Path(__file__).resolve().parent.parent
    models_dir = root / 'models'
    if models_dir.exists():
        for ext in ('*.bin', '*.gguf', '*.bin.q4*'):
            for p in models_dir.glob(ext):
                return p
    # try searching for ggml/gguf files anywhere
    for p in root.rglob('*.gguf'):
        return p
    for p in root.rglob('*.bin'):
        return p
    return None


def find_template_file() -> Optional[Path]:
    root = Path(__file__).resolve().parent.parent
    candidate = root / 'llm_template.txt'
    if candidate.exists():
        return candidate
    # also check project root
    for p in (root,):
        t = p / 'llm_template.txt'
        if t.exists():
            return t
    return None


def is_available() -> bool:
    return find_llama_binary() is not None and find_model_file() is not None


def generate_comment(combined: dict, template_path: Optional[str] = None, max_tokens: int = 256, timeout: int = 30) -> str:
    bin_path = find_llama_binary()
    model_path = find_model_file()
    if bin_path is None or model_path is None:
        raise RuntimeError('llama binary or model not found')

    if template_path:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception:
            template = None
    else:
        # auto-detect template in project root
        tpl = find_template_file()
        if tpl is not None:
            try:
                with open(tpl, 'r', encoding='utf-8') as f:
                    template = f.read()
            except Exception:
                template = None
        else:
            template = None

    if template:
        prompt = template + '\n\nContext JSON:\n' + json.dumps(combined, ensure_ascii=False, indent=2)
    else:
        prompt = (
            'You are a helpful reviewer. Write a concise commentary for the document based on the following JSON result. '
            'Keep the comment short (2-5 sentences) and refer to important failed checks and suggestions where applicable.\n\n'
            'Context JSON:\n' + json.dumps(combined, ensure_ascii=False, indent=2)
        )

    args = [str(bin_path), '-m', str(model_path), '-p', prompt, '-n', str(max_tokens), '--temp', '0.2']
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        out = proc.stdout.strip()
        if not out:
            # sometimes llama prints to stderr
            out = proc.stderr.strip()
        return out
    except Exception as e:
        raise
