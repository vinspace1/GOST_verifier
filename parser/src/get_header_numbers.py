from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import json
from docx import Document


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

@dataclass
class Node:
    number: str
    title: str
    level: int
    content: List[str] = field(default_factory=list)
    children: List["Node"] = field(default_factory=list)

def build_tree_by_numbering(docx_path: str) -> List[Dict[str, Any]]:
    doc = Document(docx_path)

    root = Node(number="", title="__root__", level=0)
    stack: List[Node] = [root]

    def attach(node: Node):
        while stack and stack[-1].level >= node.level:
            stack.pop()
        stack[-1].children.append(node)
        stack.append(node)

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue

        parsed = parse_numbered_heading(text)
        if parsed:
            num, title, lvl = parsed
            attach(Node(number=num, title=title, level=lvl))
        else:
            if len(stack) > 1:
                stack[-1].content.append(text)

    def to_dict(n: Node) -> Dict[str, Any]:
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
            print("  " * indent + f"- {n['number']} {n['title']}")
            print_tree(n["children"], indent + 1)

def get_results(path):
    tree = build_tree_by_numbering(path)
    print_tree(tree)
    with open("../results/header_numbers.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    get_results("../../input.docx")