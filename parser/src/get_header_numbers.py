from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import json
from docx import Document

# 1 Заголовок
# 1. Заголовок
# 1) Заголовок
# 1.2 Заголовок
# 1.2) Заголовок
# 1.2.3 Заголовок
# 1.2.3. Заголовок
NUM_HEADING_RE = re.compile(
    r"^\s*(?P<num>\d+(?:\.\d+)*)\s*(?:[.)])?\s+(?P<title>.+?)\s*$"
)

def parse_numbered_heading(text: str) -> Optional[tuple[str, str, int]]:
    """
    Возвращает (num, title, level) или None, если это не нумерованный заголовок.
    level = глубина номера: 1.2.3 -> 3
    """
    m = NUM_HEADING_RE.match(text or "")
    if not m:
        return None
    num = m.group("num")
    title = m.group("title").strip()
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
        # Поднимаемся до родителя с меньшим уровнем номера
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
            # Обычный текст — в текущий узел (если уже встретили хоть один заголовок)
            if len(stack) > 1:
                stack[-1].content.append(text)
            # иначе игнорируем "преамбулу" до первого нумерованного заголовка

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

if __name__ == "__main__":
    tree = build_tree_by_numbering("../../input.docx")

    def print_tree(nodes, indent=0):
        for n in nodes:
            print("  " * indent + f"- {n['number']} {n['title']}")
            print_tree(n["children"], indent + 1)

    print_tree(tree)

    with open("../results/parsed.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)