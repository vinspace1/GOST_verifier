from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
import json

NUM_HEADING_RE = re.compile(
    r"^\s*(?P<num>\d+(?:\.\d+)*)\s*(?:[.)])?\s+(?P<title>.+?)\s*$"
)

def parse_numbered_heading_from_text(text: str) -> Optional[Tuple[str, str, int]]:
    m = NUM_HEADING_RE.match(text or "")
    if not m:
        return None
    num = m.group("num")
    title = m.group("title").strip()
    level = len(num.split("."))
    return num, title, level

def get_num_props(p: Paragraph) -> Optional[Tuple[int, int]]:
    ppr = p._p.pPr
    if ppr is None or ppr.numPr is None:
        return None
    numId_elm = ppr.numPr.numId
    ilvl_elm = ppr.numPr.ilvl
    if numId_elm is None or ilvl_elm is None:
        return None
    try:
        return int(numId_elm.val), int(ilvl_elm.val)
    except Exception:
        return None


@dataclass
class Node:
    number: str            
    title: str
    level: int             

    
    number_text: str = ""
    number_auto: str = ""

    content: List[str] = field(default_factory=list)
    children: List["Node"] = field(default_factory=list)


def build_tree_by_text_or_auto_numbering(docx_path: str) -> List[Dict[str, Any]]:
    doc = Document(docx_path)

    root = Node(number="", title="__root__", level=0)
    stack: List[Node] = [root]

    counters: Dict[int, List[int]] = {}

    def next_auto_number(numId: int, ilvl: int) -> str:
        levels = counters.setdefault(numId, [])
        while len(levels) <= ilvl:
            levels.append(0)

        levels[ilvl] += 1
        for j in range(ilvl + 1, len(levels)):
            levels[j] = 0

        return ".".join(str(levels[i]) for i in range(ilvl + 1))

    def attach(node: Node):
        while stack and stack[-1].level >= node.level:
            stack.pop()
        stack[-1].children.append(node)
        stack.append(node)

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue

        parsed_text = parse_numbered_heading_from_text(text)

        if parsed_text:
            num_text, title, lvl = parsed_text
            node = Node(
                number=num_text,
                title=title,
                level=lvl,
                number_text=num_text,
                number_auto="",
            )
            attach(node)
            continue

        props = get_num_props(p)
        if props is not None:
            numId, ilvl = props
            num_auto = next_auto_number(numId, ilvl)
            lvl = ilvl + 1

            node = Node(
                number=num_auto,
                title=text,
                level=lvl,
                number_text="",
                number_auto=num_auto,
            )
            attach(node)
            continue

        if len(stack) > 1:
            stack[-1].content.append(text)

    def to_dict(n: Node) -> Dict[str, Any]:
        return {
            "number": n.number,
            "title": n.title,
            "level": n.level,
            "number_text": n.number_text,
            "number_auto": n.number_auto,
            "content": n.content,
            "content_text": "\n".join(n.content),
            "children": [to_dict(ch) for ch in n.children],
        }

    return [to_dict(ch) for ch in root.children]


if __name__ == "__main__":
    tree = build_tree_by_text_or_auto_numbering("input.docx")

    def print_tree(nodes, indent=0):
        for n in nodes:
            src = "text" if n["number_text"] else ("auto" if n["number_auto"] else "?")
            print("  " * indent + f"- {n['number']} ({src}) {n['title']}")
            print_tree(n["children"], indent + 1)

    print_tree(tree)

    with open("parsed.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)