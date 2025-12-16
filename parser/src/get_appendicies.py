import re
from typing import List, Dict, Any, Optional
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
import json

APP_RE = re.compile(r"^\s*ПРИЛОЖЕНИЕ\s*", re.IGNORECASE)

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def iter_block_items_in_order(doc: Document):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)

def _style_name(paragraph: Paragraph) -> str:
    try:
        return (paragraph.style.name or "").strip()
    except Exception:
        return ""

def _is_heading(paragraph: Paragraph) -> bool:
    """
    Считаем 'заголовком' абзацы со стилями:
    - Heading 1/2/3... (англ)
    - Заголовок 1/2/3... (рус)
    При желании можно расширить список.
    """
    name = _style_name(paragraph).lower()
    return name.startswith("heading") or name.startswith("заголовок")

def _extract_letter_or_id(title: str) -> Optional[str]:
    """
    Пытаемся вытащить идентификатор после слова ПРИЛОЖЕНИЕ:
    'ПРИЛОЖЕНИЕ А ...' -> 'А'
    'ПРИЛОЖЕНИЕ 1 ...' -> '1'
    'ПРИЛОЖЕНИЕ №2 ...' -> '2'
    Если не нашли — None.
    """
    t = _normalize(title)
    m = re.match(r"^\s*ПРИЛОЖЕНИЕ\s+(?:№\s*)?([A-ZА-ЯЁ]|\d+)\b", t, flags=re.IGNORECASE)
    return m.group(1) if m else None

def find_appendices_in_headings(docx_path: str) -> List[Dict[str, Any]]:
    doc = Document(docx_path)

    appendices: List[Dict[str, Any]] = []
    paragraph_index = 0

    for block_index, item in enumerate(iter_block_items_in_order(doc)):
        if not isinstance(item, Paragraph):
            continue

        paragraph_index += 1
        text = _normalize(item.text)
        if not text:
            continue

        if not _is_heading(item):
            continue

        if not APP_RE.match(text):
            continue

        appendices.append({
            "kind": "appendix",
            "title": text,
            "id": _extract_letter_or_id(text),   # буква/номер (если удалось)
            "heading_style": _style_name(item),  # какой стиль заголовка
            "position": {
                "block_index": block_index,
                "paragraph_index": paragraph_index,
            }
        })

    return appendices

def build_appendices_json(docx_path: str) -> Dict[str, Any]:
    appendices = find_appendices_in_headings(docx_path)
    return {
        "appendices": appendices,
        "summary": {
            "appendices_total": len(appendices),
        }
    }

def get_result(path):
    tree = build_appendices_json(path)
    print(tree)
    with open("../results/applications.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    get_result("../../original.docx")
