from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from docx import Document
from docx.text.paragraph import Paragraph
import json

# Heading N / Заголовок N
HEADING_RE = re.compile(r"^(heading|заголовок)\s*(\d+)$", re.IGNORECASE)

# Номер в начале заголовка:
# 1. Название
# 1.2 Название
# 1.2.3 Название
# 1) Название
# 1.2) Название
# 1.2.3) Название
HEADING_NUM_RE = re.compile(
    r"^\s*(?P<num>\d+(?:\.\d+)*)(?:[.)])?\s+(?P<title>.+?)\s*$"
)

def heading_level(p: Paragraph) -> Optional[int]:
    name = (p.style.name or "").strip()
    m = HEADING_RE.match(name)
    if not m:
        return None
    lvl = int(m.group(2))
    return lvl if lvl >= 1 else None

def split_number_from_heading_text(text: str) -> tuple[str, str]:
    """
    Возвращает (number, title).
    Если номер не найден — number="" и title=исходный текст.
    """
    m = HEADING_NUM_RE.match(text or "")
    if not m:
        return "", (text or "").strip()
    return m.group("num"), m.group("title").strip()

@dataclass
class SectionNode:
    number: str
    title: str
    level: int
    content: List[str] = field(default_factory=list)
    children: List["SectionNode"] = field(default_factory=list)

def split_by_sections_with_nesting_text_numbering(docx_path: str) -> List[Dict[str, Any]]:
    doc = Document(docx_path)

    root = SectionNode(number="", title="__root__", level=0)
    stack: List[SectionNode] = [root]

    def attach(node: SectionNode):
        while stack and stack[-1].level >= node.level:
            stack.pop()
        stack[-1].children.append(node)
        stack.append(node)

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue

        lvl = heading_level(p)
        if lvl is not None:
            num, title = split_number_from_heading_text(text)
            node = SectionNode(number=num, title=title, level=lvl)
            attach(node)
        else:
            if len(stack) > 1:  # игнорируем текст до первого заголовка
                stack[-1].content.append(text)

    def to_dict(n: SectionNode) -> Dict[str, Any]:
        return {
            "number": n.number,
            "title": n.title,
            "level": n.level,
            "content": n.content,
            "content_text": "\n".join(n.content),
            "children": [to_dict(ch) for ch in n.children],
        }

    return [to_dict(ch) for ch in root.children]

if __name__ == "__main__":
    tree = split_by_sections_with_nesting_text_numbering("input.docx")

    def print_tree(nodes, indent=0):
        for n in nodes:
            prefix = (n["number"] + " ") if n["number"] else ""
            print("  " * indent + f"- (H{n['level']}) {prefix}{n['title']}")
            print_tree(n["children"], indent + 1)
    print_tree(tree)
    with open("parsed.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
