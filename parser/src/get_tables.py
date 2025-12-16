import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
import json

CAPTION_RE = re.compile(r"Таблица\s+\d+\.\d+")

@dataclass
class TableCheckResult:
    table_index: int
    caption_text: Optional[str]
    match: bool
    where_found: Optional[str]

    block_index: int                 # позиция среди всех блоков (p+tbl)
    after_paragraph_index: int        # сколько абзацев было до таблицы
    prev_paragraph_text: Optional[str]


def iter_block_items_in_order(doc: Document):
    """
    Yield Paragraph and Table objects in document order (body only).
    """
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def iter_block_items_in_order(doc: Document):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)

def _find_caption_before_table(blocks: List[Tuple[str, object]], tbl_pos: int, lookback: int = 5):
    for k in range(1, lookback + 1):
        j = tbl_pos - k
        if j < 0:
            break
        kind, obj = blocks[j]
        if kind != "p":
            continue
        text = _normalize(obj.text)
        if not text:
            continue
        if CAPTION_RE.search(text):
            return text, ("prev_paragraph" if k == 1 else f"prev_{k}")
    return None, None

def _prev_paragraph_text(blocks: List[Tuple[str, object]], tbl_pos: int) -> Optional[str]:
    for j in range(tbl_pos - 1, -1, -1):
        kind, obj = blocks[j]
        if kind == "p":
            t = _normalize(obj.text)
            return t if t else None
    return None

def check_tables_captions(docx_path: str, lookback: int = 5) -> List[TableCheckResult]:
    doc = Document(docx_path)

    blocks: List[Tuple[str, object]] = []
    for item in iter_block_items_in_order(doc):
        blocks.append(("tbl", item) if isinstance(item, Table) else ("p", item))

    results: List[TableCheckResult] = []
    table_counter = 0
    paragraph_counter = 0  # считаем абзацы по ходу

    for i, (kind, obj) in enumerate(blocks):
        if kind == "p":
            paragraph_counter += 1
            continue

        # kind == "tbl"
        table_counter += 1

        caption, where = _find_caption_before_table(blocks, i, lookback=lookback)
        ok = bool(caption and CAPTION_RE.search(caption))

        results.append(TableCheckResult(
            table_index=table_counter,
            caption_text=caption,
            match=ok,
            where_found=where,
            block_index=i,
            after_paragraph_index=paragraph_counter,
            prev_paragraph_text=_prev_paragraph_text(blocks, i),
        ))

    return results

def results_to_dict(results):
    return [
        {
            "table_index": r.table_index,
            "caption_text": r.caption_text,
            "match": r.match,
            "where_found": r.where_found,
            "position": {
                "block_index": r.block_index,
                "after_paragraph_index": r.after_paragraph_index,
                "prev_paragraph_text": r.prev_paragraph_text,
            }
        }
        for r in results
    ]

def get_results(path):
    results = check_tables_captions(f"../../{path}", lookback=7)
    with open("../results/tables.json", "w", encoding="utf-8") as f:
            json.dump(results_to_dict(results), f, ensure_ascii=False, indent=2)

