from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from docx import Document
from docx.text.paragraph import Paragraph
import json

HEADING_RE = re.compile(r"^(heading|заголовок)\s*(\d+)$", re.IGNORECASE)

NUM_HEADING_RE = re.compile(
    r"^\d+(\.\d+)*\s+.+$"
)

def parse_numbered_heading(text: str) -> Optional[tuple[str, str, int]]:
    m = NUM_HEADING_RE.match(text or "")
    if not m:
        return None
    name = m.group(0)
    num = name.split()[0]
    title = name.split()[1].strip()
    level = len(num.split("."))
    return num, title, level
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
    m = NUM_HEADING_RE.match(text or "")
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
            if len(stack) > 1:
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

def print_tree(nodes, indent=0):
    for n in nodes:
        prefix = (n["number"] + " ") if n["number"] else ""
        print("  " * indent + f"- (H{n['level']}) {prefix}{n['title']}")
        print_tree(n["children"], indent + 1)

def get_result(path):
    tree = split_by_sections_with_nesting_text_numbering(path)
    print(tree)
    with open("../results/content_tree.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    get_result("../../input.docx")